"""
knowledge-manager-v2 MCP Server

Multi-knowledge base aware version of the knowledge manager.
Provides knowledge retrieval and storage with KB isolation.

Uses the official MCP SDK for stdio protocol.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.knowledge.registry import get_registry, KnowledgeBaseRegistry
from src.knowledge.manager import KnowledgeBaseManager

logger = logging.getLogger(__name__)

# Create Server instance
server = Server("knowledge-manager-v2")

# Global state
_registry: KnowledgeBaseRegistry | None = None
_manager: KnowledgeBaseManager | None = None


def get_registry() -> KnowledgeBaseRegistry:
    """Get or create the KB registry."""
    global _registry
    if _registry is None:
        _registry = get_registry()
    return _registry


def get_manager() -> KnowledgeBaseManager:
    """Get or create the KB manager."""
    global _manager
    if _manager is None:
        _manager = KnowledgeBaseManager(get_registry())
    return _manager


def _resolve_kb_id(kb_name: str | None) -> str:
    """Resolve KB name, using default if not provided.

    Args:
        kb_name: KB name or None

    Returns:
        Resolved KB ID
    """
    if not kb_name:
        return get_registry().default_kb
    return kb_name


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    registry = get_registry()
    kb_list = [kb.kb_id for kb in registry.list_kbs()]
    default_kb = registry.default_kb

    # Create kb_name enum with all KBs
    kb_enum = kb_list if kb_list else [default_kb]

    return [
        # Search experiences in a specific KB
        Tool(
            name="search_experience",
            description="Search historical analysis experiences in a knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of results"
                    },
                    "kb_name": {
                        "type": "string",
                        "description": f"Knowledge base name (default: {default_kb})",
                        "default": default_kb,
                        "enum": kb_enum,
                    }
                },
                "required": ["query"]
            }
        ),

        # Save experience to a specific KB
        Tool(
            name="save_experience",
            description="Save analysis experience to a knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "malware_family": {"type": "string"},
                    "risk_level": {"type": "string"},
                    "kb_name": {
                        "type": "string",
                        "description": f"Knowledge base name (default: {default_kb})",
                        "default": default_kb,
                        "enum": kb_enum,
                    }
                },
                "required": ["title", "content"]
            }
        ),

        # Get similar cases from a specific KB
        Tool(
            name="get_similar_cases",
            description="Find similar historical cases in a knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "malware_family": {"type": "string"},
                    "behavior_pattern": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                    "kb_name": {
                        "type": "string",
                        "description": f"Knowledge base name (default: {default_kb})",
                        "default": default_kb,
                        "enum": kb_enum,
                    }
                }
            }
        ),

        # Search knowledge base
        Tool(
            name="search_knowledge",
            description="Search knowledge base entries",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["permissions", "apis", "patterns", "all"],
                        "default": "all"
                    },
                    "kb_name": {
                        "type": "string",
                        "description": f"Knowledge base name (default: {default_kb})",
                        "default": default_kb,
                        "enum": kb_enum,
                    }
                },
                "required": ["query"]
            }
        ),

        # List experiences in a KB
        Tool(
            name="list_experiences",
            description="List experiences in a knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "limit": {"type": "integer", "default": 20},
                    "kb_name": {
                        "type": "string",
                        "description": f"Knowledge base name (default: {default_kb})",
                        "default": default_kb,
                        "enum": kb_enum,
                    }
                }
            }
        ),

        # NEW: List all knowledge bases
        Tool(
            name="list_kbs",
            description="List all available knowledge bases",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        # NEW: Get KB statistics
        Tool(
            name="kb_stats",
            description="Get statistics for a knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "kb_name": {
                        "type": "string",
                        "description": f"Knowledge base name (default: {default_kb})",
                        "default": default_kb,
                        "enum": kb_enum,
                    }
                },
                "required": []
            }
        ),

        # NEW: Search across all KBs
        Tool(
            name="search_all_kbs",
            description="Search across all knowledge bases",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search_experience":
            return await _search_experience(arguments)
        elif name == "save_experience":
            return await _save_experience(arguments)
        elif name == "get_similar_cases":
            return await _get_similar_cases(arguments)
        elif name == "search_knowledge":
            return await _search_knowledge(arguments)
        elif name == "list_experiences":
            return await _list_experiences(arguments)
        elif name == "list_kbs":
            return await _list_kbs(arguments)
        elif name == "kb_stats":
            return await _kb_stats(arguments)
        elif name == "search_all_kbs":
            return await _search_all_kbs(arguments)
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
            )]
    except Exception as e:
        logger.error(f"Tool {name} error: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, ensure_ascii=False)
        )]


async def _search_experience(args: dict) -> list[TextContent]:
    """Search historical analysis experiences."""
    manager = get_manager()
    query = args["query"]
    top_k = args.get("top_k", 5)
    kb_name = args.get("kb_name")

    kb_id = _resolve_kb_id(kb_name)
    results = manager.search_experiences(kb_id, query, top_k)

    return [TextContent(
        type="text",
        text=json.dumps({
            "kb_id": kb_id,
            "query": query,
            "results": results,
            "count": len(results)
        }, ensure_ascii=False, indent=2)
    )]


async def _save_experience(args: dict) -> list[TextContent]:
    """Save analysis experience."""
    manager = get_manager()
    title = args["title"]
    content = args["content"]
    tags = args.get("tags", [])
    malware_family = args.get("malware_family", "")
    risk_level = args.get("risk_level", "")
    kb_name = args.get("kb_name")

    kb_id = _resolve_kb_id(kb_name)
    experience_id = manager.save_experience(
        kb_id, title, content, tags, malware_family, risk_level
    )

    return [TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "kb_id": kb_id,
            "experience_id": experience_id
        }, ensure_ascii=False)
    )]


async def _get_similar_cases(args: dict) -> list[TextContent]:
    """Get similar historical cases."""
    manager = get_manager()
    malware_family = args.get("malware_family", "")
    behavior_pattern = args.get("behavior_pattern", "")
    limit = args.get("limit", 5)
    kb_name = args.get("kb_name")

    kb_id = _resolve_kb_id(kb_name)
    results = manager.get_similar_cases(kb_id, malware_family, behavior_pattern, limit)

    return [TextContent(
        type="text",
        text=json.dumps({
            "kb_id": kb_id,
            "results": results,
            "count": len(results)
        }, ensure_ascii=False, indent=2)
    )]


async def _search_knowledge(args: dict) -> list[TextContent]:
    """Search knowledge base entries."""
    manager = get_manager()
    query = args["query"]
    category = args.get("category", "all")
    kb_name = args.get("kb_name")

    kb_id = _resolve_kb_id(kb_name)
    results = manager.search_knowledge(kb_id, query, category)

    return [TextContent(
        type="text",
        text=json.dumps({
            "kb_id": kb_id,
            "query": query,
            "results": results,
            "count": len(results)
        }, ensure_ascii=False, indent=2)
    )]


async def _list_experiences(args: dict) -> list[TextContent]:
    """List experiences in a KB."""
    manager = get_manager()
    tags_filter = args.get("tags", [])
    limit = args.get("limit", 20)
    kb_name = args.get("kb_name")

    kb_id = _resolve_kb_id(kb_name)
    results = manager.list_experiences(kb_id, tags_filter, limit)

    return [TextContent(
        type="text",
        text=json.dumps({
            "kb_id": kb_id,
            "experiences": results,
            "count": len(results)
        }, ensure_ascii=False, indent=2)
    )]


async def _list_kbs(args: dict) -> list[TextContent]:
    """List all available knowledge bases."""
    registry = get_registry()
    manager = get_manager()

    kbs = []
    for kb in registry.list_kbs():
        stats = manager.get_kb_stats(kb.kb_id)
        kbs.append({
            "id": kb.kb_id,
            "name": kb.name,
            "description": kb.description,
            "language": kb.language,
            "tags": kb.tags,
            "associated_skills": kb.associated_skills,
            "experience_count": stats.get("experience_count", 0),
            "knowledge_count": stats.get("knowledge_count", 0),
        })

    return [TextContent(
        type="text",
        text=json.dumps({
            "knowledge_bases": kbs,
            "default_kb": registry.default_kb,
            "total_count": len(kbs)
        }, ensure_ascii=False, indent=2)
    )]


async def _kb_stats(args: dict) -> list[TextContent]:
    """Get statistics for a KB."""
    manager = get_manager()
    kb_name = args.get("kb_name")

    kb_id = _resolve_kb_id(kb_name)
    stats = manager.get_kb_stats(kb_id)

    return [TextContent(
        type="text",
        text=json.dumps(stats, ensure_ascii=False, indent=2)
    )]


async def _search_all_kbs(args: dict) -> list[TextContent]:
    """Search across all knowledge bases."""
    manager = get_manager()
    query = args["query"]
    top_k = args.get("top_k", 5)

    results = manager.search_all_kbs(query, top_k)

    # Add KB names to results
    formatted = {}
    total_results = 0
    for kb_id, kb_results in results.items():
        kb_config = get_registry().get_kb(kb_id)
        formatted[kb_id] = {
            "kb_name": kb_config.name if kb_config else kb_id,
            "results": kb_results,
            "count": len(kb_results)
        }
        total_results += len(kb_results)

    return [TextContent(
        type="text",
        text=json.dumps({
            "query": query,
            "results_by_kb": formatted,
            "total_results": total_results,
            "kbs_searched": len(results)
        }, ensure_ascii=False, indent=2)
    )]


async def main():
    """Start knowledge-manager-v2 MCP Server."""
    # Initialize registry and manager
    get_registry()
    get_manager()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
