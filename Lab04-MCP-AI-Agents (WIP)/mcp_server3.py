# setup_agent.py
import os
import asyncio
import logging
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionTool

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)


async def discover_mcp_functions_with_session(session: ClientSession):
    """
    Discovers tool functions from the MCP server session.
    Wraps them as async callables so Azure Agent can invoke them.
    """
    tools = await session.list_tools()

    wrapped_functions = []

    for tool in tools:
        async def tool_wrapper(args, tool_name=tool.name):  # default to bind name
            return await session.call_tool(tool_name, args)

        # Add metadata to help FunctionTool name them
        tool_wrapper.__name__ = tool.name
        tool_wrapper.__doc__ = tool.description or ""
        wrapped_functions.append(tool_wrapper)

    return wrapped_functions


async def setup_agent():
    # Step 1: Start MCP server and create session
    server_script_path = "C:\\Users\\katukagloria\\azure-ai-agents-mcp\\Lab03-Intro-to-MCP\\greeting_server.py"

    server_params = StdioServerParameters(
        command="python",
        args=[server_script_path],
        env=None
    )

    async with AsyncExitStack() as stack:
        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(*stdio_transport))

        await session.initialize()

        # Step 2: Discover tool functions from MCP and wrap them
        mcp_functions = await discover_mcp_functions_with_session(session)
        functions = FunctionTool(functions=mcp_functions)

        # Step 3: Connect to Azure AI Project
        project_client = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=os.getenv("PROJECT_ENDPOINT"),
        )

        # Step 4: Create or update agent
        AGENT_NAME = os.getenv("AGENT_NAME", "mcp-powered-agent3")
        agent = project_client.agents.create_agent(
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            name=AGENT_NAME,
            instructions=(
                "You are a helpful assistant. "
                "When tool calls are required, ALWAYS use the provided tools. "
                "If you use a tool to answer a question, return the name of the tool in this format: "
                "`<tool_name>`: response from the tool."
            ),
            tools=functions.definitions,
        )
        logging.info("✅ Agent created (id=%s)", agent.id)

        # Step 5: Register tool invocation handlers
        await project_client.agents.enable_auto_function_calls(tools=functions.definitions)

        # Step 6: Optional test run
        thread = await project_client.agents.threads.create()
        await project_client.agents.messages.create(
            thread_id=thread.id, role="user", content="Hello, what can you do?"
        )
        run = await project_client.agents.runs.create_and_process(
            thread_id=thread.id, agent_id=agent.id
        )
        logging.info(f"Run status: {run.status}")

        messages = project_client.agents.messages.list(thread_id=thread.id)
        async for message in messages:
            if message.text_messages:
                print(f"{message.role}: {message.text_messages[-1].text.value}")

        # Session will be closed by AsyncExitStack cleanup


if __name__ == "__main__":
    asyncio.run(setup_agent())
