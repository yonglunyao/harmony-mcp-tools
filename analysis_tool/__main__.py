"""analysis-tool MCP Server entry point"""
from mcp_servers.analysis_tool import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
