
import os
import json
import asyncio
import shutil
import logging
import re
from contextlib import AsyncExitStack
from typing import Any, Callable, Dict, List, Set

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)

class MCPServer:
    """Async wrapper to manage an MCP server and communicate with its tools."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self._config = config
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self):
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        cmd = shutil.which("npx") if self._config["command"] == "npx" else self._config["command"]
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
        logging.info("%s: server initialized", self.name)
        return self

    async def __aexit__(self, *exc_info):
        if self._stack:
            await self._stack.aclose()
        self._session = None
        logging.info("%s: server cleaned up", self.name)

    async def list_tools(self) -> List[MCPTool]:
        if not self._session:
            raise RuntimeError("Server not initialized")
        return (await self._session.list_tools()).tools

    async def call(self, tool_name: str, **kwargs) -> Any:
        if not self._session:
            raise RuntimeError("Server not initialized")
        return await self._session.call_tool(tool_name, arguments=kwargs)


def _make_tool_func(
    server_name: str, tool: MCPTool, call_coro: Callable[..., Any]
) -> Callable[..., str]:
    """Creates a synchronous wrapper for an async MCP tool call."""

    def sanitize(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]", "_", name)

    def _func(**kwargs):
        """Proxy function for tool: {tool.name} on server: {server_name}"""
        return asyncio.run(call_coro(tool.name, **kwargs))

    safe_name = f"{sanitize(server_name)}__{sanitize(tool.name)}"
    _func.__name__ = safe_name
    return _func


async def discover_mcp_functions(config_path: str) -> Set[Callable[..., Any]]:
    """Loads MCP server config and returns all tool functions from all servers."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    all_funcs: Set[Callable[..., Any]] = set()
    async with AsyncExitStack() as stack:
        for name, server_cfg in cfg["servers"].items():
            server = await stack.enter_async_context(MCPServer(name, server_cfg))
            for tool in await server.list_tools():
                fn = _make_tool_func(server.name, tool, server.call)
                all_funcs.add(fn)

    logging.info("Discovered %d MCP tools across %d servers", len(all_funcs), len(cfg["servers"]))
    return all_funcs