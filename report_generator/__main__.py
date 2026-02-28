"""report-generator MCP Server entry point"""
from mcp_servers.report_generator import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
