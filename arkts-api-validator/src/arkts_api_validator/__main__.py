"""
Main entry point for the ArkTS API Validator MCP Server.

Run with: python -m arkts_api_validator
"""

from .server import mcp

if __name__ == "__main__":
    mcp.run()
