# setup_agent.py
# ---------------------------------------------------------------
# Creates or updates an Azure AI Agent with MCP tools

import os
import asyncio
import logging
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionTool
from dotenv import load_dotenv

from mcp_server import discover_mcp_functions  # <-- imported from other file

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)


async def setup_agent():
    # Step 1: Discover MCP tool functions
    mcp_functions = await discover_mcp_functions("mcp_config.json")

    # Step 2: Wrap functions in FunctionTool
    functions = FunctionTool(functions=mcp_functions)

    # Step 3: Connect to Azure AI Project
    project_client = AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=os.getenv("PROJECT_ENDPOINT"),
    )

    # Step 4: Create or update agent
    AGENT_NAME = os.getenv("AGENT_NAME", "mcp-powered-agent")
    agent = project_client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name=AGENT_NAME,
        instructions=(
            "You are a helpful assistant. "
            "When tool calls are required, ALWAYS use the provided tools."
            "if you use a tool to answer a question, return the name of the tool in the following format: "
            "`<tool_name>`: response from the tool. "  
            
        ),
        tools=functions.definitions,
    )
    logging.info("Agent ready (id=%s)", agent.id)

    # Step 5: Register function handlers
    project_client.agents.enable_auto_function_calls(tools=functions)

    # Optional: Smoke test run
    thread = project_client.agents.threads.create()
    project_client.agents.messages.create(
        thread_id=thread.id, role="user", content="What is cuurent time in London?"
    )
    run = project_client.agents.runs.create_and_process(
        thread_id=thread.id, agent_id=agent.id
    )
    print(f"Run status: {run.status}")
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for message in messages:
        print(f"{message.role}: {message.text_messages[-1].text.value}")


if __name__ == "__main__":
    asyncio.run(setup_agent())
