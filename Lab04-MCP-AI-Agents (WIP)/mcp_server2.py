# mcp_to_azure_agent.py
# ---------------------------------------------------------------
# Requirements (PyPI):
#   pip install mcp-client aiohttp azure-ai-projects azure-identity

import os
import json
import asyncio
import shutil
import logging
import re
from contextlib import AsyncExitStack
from typing import Any, Callable, Dict, List, Set

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionTool, ToolSet

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool

from dotenv import load_dotenv


load_dotenv()


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)


# MCP ↔ Azure-Agent glue
class MCPServer:
    """Thin async wrapper around an MCP server process."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self._config = config
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    # ---------- lifecycle ----------------------------------------------------
    async def __aenter__(self):
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        cmd = shutil.which("npx") if self._config["command"] == "npx" else self._config[
            "command"
        ]
        if not cmd:
            raise ValueError(f"{self.name}: command not found: {self._config['command']}")

        params = StdioServerParameters(
            command=cmd,
            args=self._config["args"],
            env=self._config.get("env"),
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        logging.info("%s: server initialised", self.name)
        return self

    async def __aexit__(self, *exc_info):
        try:
            if self._stack:
                await self._stack.aclose()
        finally:
            self._session = None
            logging.info("%s: server cleaned up", self.name)

    # ---------- MCP helpers ---------------------------------------------------
    async def list_tools(self) -> List[MCPTool]:
        if not self._session:
            raise RuntimeError("Server not initialised")
        return (await self._session.list_tools()).tools

    async def call(self, tool_name: str, **kwargs) -> Any:
        if not self._session:
            raise RuntimeError("Server not initialised")
        return await self._session.call_tool(tool_name, arguments=kwargs)


def _make_tool_func(
    server_name: str, tool: MCPTool, call_coro: Callable[..., Any]
) -> Callable[..., str]:
    """
    Create a synchronous Python function stub that, when called by
    Azure AI Agent Service, hops into an event loop and executes the
    underlying MCP tool.
    """

    def sanitize(name: str) -> str:
        # Only allow a-z, A-Z, 0-9, _, -
        return re.sub(r"[^a-zA-Z0-9_-]", "_", name)

    def _func(**kwargs):
        """Proxy to MCP tool **{tool.name}** on server **{server_name}**."""
        # We *must* run the async call inside a fresh event loop because
        # the Azure runtime is synchronous at tool-invocation time.
        return asyncio.run(call_coro(tool.name, **kwargs))

    safe_name = f"{sanitize(server_name)}__{sanitize(tool.name)}"
    _func.__name__ = safe_name
    return _func


async def discover_mcp_functions(config_path: str) -> Set[Callable[..., Any]]:
    """
    Reads *mcp_config.json*, spins up each server, and returns a set
    of *callable* Python functions — one per MCP tool discovered.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    all_funcs: Set[Callable[..., Any]] = set()
    async with AsyncExitStack() as stack:
        for name, server_cfg in cfg["servers"].items():
            server = await stack.enter_async_context(MCPServer(name, server_cfg))
            for tool in await server.list_tools():
                fn = _make_tool_func(server.name, tool, server.call)
                all_funcs.add(fn)  # type: ignore[arg-type]

    logging.info("Discovered %d MCP tools across %d servers", len(all_funcs), len(cfg["servers"]))
    return all_funcs


# Main entry-point: create / update an Agent with MCP tools
async def setup_agent():
    # 1) Fetch MCP-backed tool functions
    mcp_functions = await discover_mcp_functions("mcp_config.json")

    # 2) Wrap them in a FunctionTool and ToolSet
    functions= FunctionTool(functions=mcp_functions)
    # toolset = ToolSet()
    # toolset.add(mcp_function_tool)

    # 3) Connect to your Azure AI Project
    project_client = AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=os.getenv("PROJECT_ENDPOINT"),
    )

    # 4) *Create* (or update) the Agent
    AGENT_NAME = os.environ.get("AGENT_NAME", "mcp-powered-agent")
    agent = project_client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],  # e.g. "gpt-4o"
        name=AGENT_NAME,
        instructions=(
            "You are a helpful assistant. "
            "When tool calls are required, ALWAYS use the provided tools."
            "if you use a tool to answer a question, return the name of the tool in the following format: "
            "`<tool_name>`: response from the tool. "  
        ),
        tools=functions.definitions,
    )
    # If the agent already exists, switch to .update_agent(...)
    logging.info("Agent ready (id=%s)", agent.id)

    # 5) Let Agent Service auto-invoke our functions
    project_client.agents.enable_auto_function_calls(tools=functions)

    # (Optional) basic smoke-test
    thread = project_client.agents.threads.create()
    project_client.agents.messages.create(
        thread_id=thread.id, role="user", content="What is current time in London?"
    )
    run = project_client.agents.runs.create_and_process(
        thread_id=thread.id, agent_id=agent.id
    )
    print(f"Run status: {run.status}")
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for message in messages:
        # if message.role == "MessageRole.AGENT":
            print(f"{message.role}: {message.text_messages[-1].text.value}")
    # print(f"Response:\n{run.steps[-1].outputs[0].value if run.steps else '—'}")


if __name__ == "__main__":
    asyncio.run(setup_agent())
