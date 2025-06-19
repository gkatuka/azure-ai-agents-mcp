import asyncio
from typing import Any
import json
import requests 
from mcp.server.fastmcp import FastMCP 

# Initialize FastMCP server
mcp = FastMCP("Weather")

#defining constants
weather_api_base = "https://wttr.in"

