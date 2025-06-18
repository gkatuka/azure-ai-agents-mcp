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

# Define user functions
# user_functions = {fetch_weather}
user_functions: Set[Callable[..., Any]] = {
    get_weather,

}