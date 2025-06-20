import os
import asyncio
import logging
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionTool
from dotenv import load_dotenv

from mcp_functions_handler import discover_mcp_functions  

load_dotenv()

# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
# )

async def setup_agent():
    # gets the MCP tool functions
    mcp_functions = await discover_mcp_functions("mcp_config.json")
    # Wrap functions in FunctionTool
    functions = FunctionTool(functions=mcp_functions)

    # Step 3: Connect to Azure AI Project
    project_client = AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=os.getenv("PROJECT_ENDPOINT"),
    )

    # Create a new agent
    agent = project_client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="mcp-powered-agent",
        instructions=(
            "You are a helpful assistant. "
            "When tool calls are required, ALWAYS use the provided tools."
            "if you use a tool to answer a question, return the name of the tool in the following format: "
            "Return the answer in the following format: "
            "`<tool_name>`: response from the tool. "  
            
        ),
        tools=functions.definitions,
    )
    logging.info("Agent ready (id=%s)", agent.id)

    # (optional)Register function handlers
    project_client.agents.enable_auto_function_calls(tools=functions)
 

    thread = project_client.agents.threads.create()
    project_client.agents.messages.create(
        thread_id=thread.id, role="user", content="what is the current time in London?"
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
