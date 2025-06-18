import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_script_path = "C:\\Users\\katukagloria\\azure-ai-agents-mcp\\Lab03-Intro-to-MCP\\greeting_server.py"  
    # server_script_path = "C:\\Users\\katukagloria\\azure-ai-agents-mcp\\Lab03-Intro-to-MCP\\weather_server.py" - remove before committing 

    server_params = StdioServerParameters(
        command="python",
        args=[server_script_path],
        env=None
    )

    async with AsyncExitStack() as stack:
        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(*stdio_transport))

        await session.initialize()
        result = await session.call_tool("greeting", {"name": "Jane Doe"})
        # result = await session.call_tool("get_weather_info", {"location": "London"}) - remove before committing
        
        # Correctly handle MCP response
        content_item = result.content[0]
        print(content_item.text)

asyncio.run(main())