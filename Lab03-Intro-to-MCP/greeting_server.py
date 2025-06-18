from mcp.server.fastmcp import FastMCP

mcp = FastMCP("greeting")

@mcp.tool() #python decorator to register the function as a tool
async def greeting(name: str) -> str:
    """
    Returns a greeting message.

    Parameters:
    name (str): The name to greet.

    Returns:
    str: A greeting message.
    """
    return f"Hello, {name}! This is a simple MCP server response."

if __name__ == "__main__":
    mcp.run(transport='stdio')
    # print("MCP server is running on port 8000.")