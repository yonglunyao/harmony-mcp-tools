"""knowledge-manager MCP Server entry point"""
from mcp_servers.knowledge_manager import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
