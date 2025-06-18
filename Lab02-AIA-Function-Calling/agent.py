import os, time
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
# from azure.ai.projects.models import MessageTextContent
from azure.ai.agents.models import FunctionTool, ToolSet, CodeInterpreterTool
from functions import user_functions, get_weather, get_user_info,fetch_weather
from dotenv import load_dotenv


load_dotenv()
# [START create_project_client]
project_client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=os.getenv("PROJECT_ENDPOINT"),
    # api_version="latest",
)

model=os.getenv("MODEL_DEPLOYMENT_NAME")


with project_client:
    # Initialize agent toolset with user functions and code interpreter
    # [START create_agent_toolset]
    functions = FunctionTool(functions=user_functions)
    # functions =FunctionTool(functions=["get_weather", "get_user_info"])

    # toolset = ToolSet()
    # toolset.add(functions)

    agent = project_client.agents.create_agent(  #add get_agent(assistant_id="") for using already created agent
        model=model,
        name="my-assistant",
        instructions="You are helpful assistant",
        # toolset=toolset,
        tools = functions.definitions
        # tools="Add tools here"
    )
    project_client.agents.enable_auto_function_calls(tools=functions)
    # [END create_agent]
    print(f"Created agent, agent ID: {agent.id}")
    # [START create_thread] - thread for communication
    thread = project_client.agents.threads.create()  #add get_thread(thread_id="") for using already created thread
    # [END create_thread]
    print(f"Created thread, thread ID: {thread.id}")

     # Create message to thread
    message = project_client.agents.messages.create(
            thread_id=thread.id, 
            role="user", 
            content="Hello can you please fetch the information for user with user id 1 and also the weather information in london?")
        # [END create_message]
    print(f"Created message, message ID: {message.id}")

    # Create and process agent run in thread with tools
    # [START create_and_process_run] 
    run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    # if run.status == "requires_action":
    #     tool_calls = run.required_action.submit_tool_outputs.tool_calls
    #     tool_outputs = []
    #     for tool_call in tool_calls:
    #         if tool_call.name == "fetch_weather":
    #             output = fetch_weather("New York")
    #             tool_outputs.append({"tool_call_id": tool_call.id, "output": output})
    #     project_client.agents.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs)
     # [END create_and_process_run]
    print(f"Run finished with status: {run.status}")

    # Check if the run failed
    if run.status == "failed":
        print(f"Run failed: {run.last_error}")

    #Fetch and log messages

    messages = project_client.agents.messages.list(thread_id=thread.id)
    for message in messages:
        # if message.role == "MessageRole.AGENT":
            print(f"{message.role}: {message.text_messages[-1].text.value}") #Print assitant response
    # [END create_run]


    # Delete the agent when done
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")
    # [END list_messages]