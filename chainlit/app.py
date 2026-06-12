import os
import asyncio
from contextlib import AsyncExitStack

import chainlit as cl
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession
from mcp.client.sse import sse_client

@cl.on_chat_start
async def on_chat_start():
    # We use an AsyncExitStack to manage the lifecycles of multiple MCP connections
    stack = AsyncExitStack()
    cl.user_session.set("stack", stack)
    
    # Define our MCP SSE server endpoints (matching docker-compose)
    servers = [
        "http://mcp-server:8003/sse",      # Elasticsearch
        "http://mcp-playwright:8002/sse",  # Playwright
        "http://mcp-prometheus:8001/sse"   # Prometheus
    ]
    
    all_tools = []
    
    msg = cl.Message(content="Initializing AI Responder...\nConnecting to MCP Servers (Elasticsearch, Playwright, Prometheus)...")
    await msg.send()
    
    try:
        from langchain_mcp_adapters.tools import load_mcp_tools
        
        for url in servers:
            # Connect via SSE
            sse = await stack.enter_async_context(sse_client(url))
            # Initialize Client Session
            session = await stack.enter_async_context(ClientSession(sse[0], sse[1]))
            await session.initialize()
            
            # Load tools into Langchain format
            tools = await load_mcp_tools(session)
            all_tools.extend(tools)
            
    except ImportError:
        await cl.Message(content="Warning: langchain-mcp-adapters is not installed. Running without tools.").send()
    except Exception as e:
        await cl.Message(content=f"Warning: Could not connect to MCP servers. {str(e)}\nMake sure docker-compose is running.").send()

    # Initialize DeepSeek
    llm = ChatOpenAI(
        model="deepseek-reasoner",
        api_key=os.environ.get("DEEPSEEK_API_KEY", "dummy"),
        base_url="https://api.deepseek.com/v1",
        streaming=True
    )

    if all_tools:
        system_prompt = """You are an elite Site Reliability Engineer (SRE). 
The application is accessible from your Playwright MCP tool at `http://go-app:8080/login`.
you can login using username `admin` and password `password123` to test if login work.
Your goal is to investigate the issue (5xx, latency, DNS errors etc.) and generate a root cause analysis report.
You have access to MCP tools for Playwright (to reproduce the error), Elasticsearch (to search traces), and Prometheus.
Use them to verify issues and extract trace data before writing your report.


CRITICAL ELASTICSEARCH INSTRUCTION:
When searching logs in Elasticsearch, you MUST always query the `filebeat-*` index and filter by `container.name: "go-app"`.
When investigating apm, filter by `service.name:"hello-world-go"` and you MUST alway search over index name `traces-apm*` or `apm-*`. 

CRITICAL PLAYWRIGHT INSTRUCTION: 
Do NOT use selectors like `ref=...`. Always use standard CSS selectors (e.g., `input[name="username"]`) or text selectors (e.g., `text="Login"`) when interacting with elements.
You MUST launch all browsers in HEADLESS mode (headless: true).
"""
        def clean_messages_for_deepseek(state):
            from langchain_core.messages import SystemMessage
            messages = state["messages"]
            cleaned_messages = [SystemMessage(content=system_prompt)]
            for msg in messages:
                if isinstance(msg.content, list):
                    new_content = []
                    for item in msg.content:
                        if isinstance(item, dict):
                            if item.get("type") in ["image_url", "image"]:
                                continue
                        new_content.append(item)
                    if not new_content:
                        new_content = [{"type": "text", "text": "[Image omitted due to DeepSeek API limitation]"}]
                    new_msg = msg.copy(update={"content": new_content})
                    cleaned_messages.append(new_msg)
                else:
                    cleaned_messages.append(msg)
            return cleaned_messages

        agent_executor = create_react_agent(llm, tools=all_tools, prompt=clean_messages_for_deepseek)
    else:
        # Fallback if tools fail
        agent_executor = None

    cl.user_session.set("agent", agent_executor)
    cl.user_session.set("llm", llm)
    cl.user_session.set("tools_loaded", bool(all_tools))
    
    if all_tools:
        msg.content = f"AI Responder Ready! Connected to {len(all_tools)} MCP tools.\nHow can I help you investigate today?"
        await msg.update()
    else:
        msg.content = "AI Responder Ready (Text-only mode). How can I help you?"
        await msg.update()

@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    has_tools = cl.user_session.get("tools_loaded")
    
    if has_tools and agent:
        # Stream the agent's thought process into Chainlit UI
        res = await agent.ainvoke(
            {"messages": [("user", message.content)]},
            config={"callbacks": [cl.AsyncLangchainCallbackHandler(stream_final_answer=True)]}
        )
        final_message = res["messages"][-1]
        elements = []
        if hasattr(final_message, "usage_metadata") and final_message.usage_metadata:
            usage = final_message.usage_metadata
            input_toks = usage.get("input_tokens", 0)
            output_toks = usage.get("output_tokens", 0)
            total_toks = usage.get("total_tokens", 0)
            usage_text = f"**Input Tokens:** {input_toks} | **Output Tokens:** {output_toks} | **Total Tokens:** {total_toks}"
            elements.append(cl.Text(name="Token Usage", content=usage_text, display="inline"))
            
        await cl.Message(content=final_message.content, elements=elements).send()
    else:
        llm = cl.user_session.get("llm")
        res = await llm.ainvoke(message.content)
        
        elements = []
        if hasattr(res, "usage_metadata") and res.usage_metadata:
            usage = res.usage_metadata
            input_toks = usage.get("input_tokens", 0)
            output_toks = usage.get("output_tokens", 0)
            total_toks = usage.get("total_tokens", 0)
            usage_text = f"**Input Tokens:** {input_toks} | **Output Tokens:** {output_toks} | **Total Tokens:** {total_toks}"
            elements.append(cl.Text(name="Token Usage", content=usage_text, display="inline"))
            
        await cl.Message(content=res.content, elements=elements).send()

@cl.on_chat_end
async def on_chat_end():
    stack = cl.user_session.get("stack")
    if stack:
        await stack.aclose()
