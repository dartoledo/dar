import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def get_tools(url):
    try:
        async with sse_client(url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [t.name for t in tools.tools]
    except Exception as e:
        return [f"Error: {e}"]

async def main():
    servers = {
        "Elasticsearch": "http://mcp-server:8003/sse",
        "Prometheus": "http://mcp-prometheus:8001/sse",
        "Playwright": "http://mcp-playwright:8002/sse"
    }
    for name, url in servers.items():
        tools = await get_tools(url)
        print(f"\n{name} ({len(tools)} tools):")
        for t in tools:
            print(f"  - {t}")

asyncio.run(main())
