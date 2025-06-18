# Hands-on labs for Azure AI Foundry Agents and MCP Supports

## Prerequisites

* Azure AI Foundry resource with an AI Hub and AI Project
* Deploy a gpt-4o or later model
* (Optional)create a Bing Grounding Tool and coonect it to your project (link)[https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding]

## Setup

1. **Install dependencies**:
    ```sh
    pip install -r requirements.txt
    ```
2. **Configure environment variables** in a `.env` file:
    ```
    PROJECT_ENDPOINT=your-your-azure-ai-foundry-project-endpoint
    MODEL_DEPLOYMENT_NAME=your-azure-ai-foundry-model
    (optional) BING_CONNECTION_NAME= your-bing-tool-connection-name - If you created a bing grounding tool and connected it to your project...
    ```

## Hands-on Labs

These Labs introduces you to Azure AI Agents and MCP. They include: 
* Setting up an AI Agent
* Connecting tools to your agents using function calling   
* connecting tools to your agents using MCP

### Lab 1 - Intro to Agent
Lab 2 introduces you to AI agents in Azure. You will learn how to build a simple AI agent that ...

### Lab 2 - Function Calling 
Lab 2 introduces you to connecting tools via function calling. This includes: 
* Function calling using python code
* Function calling using Bing Tool (optional)

### Lab 3 - Function Calling 
Lab 3 introduces you to connecting tools via MCP. This includes: 
* Introduction to MCP servers 
* Connecting MCP servers to VSCode 
* Building MCP servers for APIs 
