"""threat-intel MCP Server entry point"""
from mcp_servers.threat_intel import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
