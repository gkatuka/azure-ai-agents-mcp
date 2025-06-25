import os, time
import jsonref
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder, MessageRole
from azure.ai.agents.models import FunctionTool
from functions import user_functions
from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails

from dotenv import load_dotenv

load_dotenv()

#Connect to Azure AI Project using the deployed model
model=os.getenv("MODEL_DEPLOYMENT_NAME")

project_client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=os.getenv("PROJECT_ENDPOINT"),
)

# create a FunctionTool with the user-defined functions
function = FunctionTool(functions=user_functions)

# Uncomment the following  to use OpenAPI tools
# with open("./weather_openapi.json", "r") as f:
#     openapi_spec = jsonref.loads(f.read()) # read the OpenAPI specs from a file

# auth = OpenApiAnonymousAuthDetails() # create auth for OpenAPI tool
# openapi = OpenApiTool( # initialize OpenApiTool with the spec and auth
#     name="get_weather", 
#     spec=openapi_spec, 
#     description="Retrieve weather information for a location", 
#     auth=auth
# ) 

# Create a new agent 
with project_client:

    agent = project_client.agents.create_agent( 
        model=model,
        name="my-assistant-tools",
        instructions="You are a helpful assistant. "
                     "When tool calls are required, ALWAYS use the provided tools. ",
        tools= function.definitions
        # tools = openapi.definitions  # Uncomment to use OpenAPI tool
    )
    
    project_client.agents.enable_auto_function_calls(tools=function)

    print(f"Created agent, agent ID: {agent.id}")

    ## Uncomment to use an existing agent 
    # agent = project_client.agents.get_agent(agent_id="")
    # print(f"Using existing agent, agent ID: {agent.id}")

    # Create a new thread to track the session
    thread = project_client.agents.threads.create()
    print(f"Created thread, thread ID: {thread.id}")

    # Create a message with a prompt that is send to the agent 
    user_prompt : str =""
    while user_prompt.lower() != "exit":
        query = input("Enter your prompt (type 'exit' to quit): ")
        message = project_client.agents.messages.create(
            thread_id=thread.id, 
            role="user", 
            content=query
        )
        print(f"Created message, message ID: {message.id}")

        # Run the agent to process the message in the thread
        run = project_client.agents.runs.create_and_process(
            thread_id=thread.id, 
            agent_id=agent.id)
        print(f"Run finished with status: {run.status}")

        # Check if the run failed
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")

        # Poll the run as long as run status is queued or in progress
        while run.status in ["queued", "in_progress", "requires_action"]:
            # Wait for a second
            time.sleep(1)

            run = project_client.agents.run(thread_id=thread.id, run_id=run.id)
            print(f"Run status: {run.status}")

        # Get the messages in the thread
        messages = project_client.agents.messages.list(thread_id=thread.id)
        for message in messages:
            # if message.role == MessageRole.agent:
            print(f"{message.role}: {message.content[0].text.value}")
            
        user_prompt = input("Type 'exit' to quit or press Enter to continue: ")

    # Delete the agent once done
    # project_client.agents.delete_agent(agent.id)
    # print("Deleted agent")