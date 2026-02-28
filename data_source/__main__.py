"""data-source MCP Server entry point"""
from mcp_servers.data_source import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
