"""vector-search MCP Server entry point"""
from mcp_servers.vector_search import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
