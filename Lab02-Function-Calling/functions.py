import requests
from typing import Any, Callable, Set, Dict, List, Optional
import json
import os
from dotenv import load_dotenv
load_dotenv()


def get_weather(location: str) -> str:
    """
    Fetches the weather information for the specified location.

    :param location: The location to fetch weather for.
    :return: Weather information as a JSON string.
    """
    weather_api_base = "https://wttr.in"
    url = f"{weather_api_base}/{location}?format=j1"
    
    response = requests.get(url)
    
    return str(response.json())

def get_user_info(user_id: int) -> str:
    """Retrieves user information based on user ID.
    :param user_id (int): ID of the user.
    :rtype: int
    :return: User information as a JSON string.
    :rtype: str
    """
    mock_users = {
        1: {"name": "Alice", "email": "alice@example.com"},
        2: {"name": "Bob", "email": "bob@example.com"},
        3: {"name": "Charlie", "email": "charlie@example.com"},
    }
    user_info = mock_users.get(user_id, {"error": "User not found."})
    return json.dumps({"user_info": user_info})

# Define user functions
user_functions: Set[Callable[..., Any]] = {
    get_weather,
    get_user_info
}