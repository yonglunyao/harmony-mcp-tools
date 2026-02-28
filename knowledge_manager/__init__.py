"""
knowledge-manager MCP Server

提供知识检索和存储能力。

使用官方 MCP SDK 实现 stdio 协议。
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入MCP日志配置
from mcp_servers.logging_config import get_knowledge_manager_logger

logger = get_knowledge_manager_logger()

# 创建 Server 实例
server = Server("knowledge-manager")

# 全局状态
_knowledge_dir: str = None
_experiences: list[dict] = []
_knowledge_base: list[dict] = []


def get_knowledge_dir() -> str:
    """获取知识目录"""
    global _knowledge_dir
    if _knowledge_dir is None:
        knowledge_dir = Path(__file__).parent.parent.parent / "data" / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        _knowledge_dir = str(knowledge_dir)
    return _knowledge_dir


def load_knowledge():
    """加载知识库"""
    global _experiences, _knowledge_base

    experiences_file = os.path.join(get_knowledge_dir(), "experiences.json")
    if os.path.exists(experiences_file):
        try:
            with open(experiences_file, 'r', encoding='utf-8') as f:
                _experiences = json.load(f)
            logger.info(f"Loaded {len(_experiences)} experiences")
        except Exception as e:
            logger.error(f"Failed to load experiences: {e}")

    knowledge_file = os.path.join(get_knowledge_dir(), "knowledge_base.json")
    if os.path.exists(knowledge_file):
        try:
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                _knowledge_base = json.load(f)
            logger.info(f"Loaded {len(_knowledge_base)} knowledge entries")
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")


def save_experiences():
    """保存经验到文件"""
    experiences_file = os.path.join(get_knowledge_dir(), "experiences.json")
    try:
        with open(experiences_file, 'w', encoding='utf-8') as f:
            json.dump(_experiences, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save experiences: {e}")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="search_experience",
            description="Search historical analysis experiences",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "default": 5, "description": "Number of results"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="save_experience",
            description="Save analysis experience for future reference",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "malware_family": {"type": "string"},
                    "risk_level": {"type": "string"}
                },
                "required": ["title", "content"]
            }
        ),
        Tool(
            name="get_similar_cases",
            description="Find similar historical cases",
            inputSchema={
                "type": "object",
                "properties": {
                    "malware_family": {"type": "string"},
                    "behavior_pattern": {"type": "string"},
                    "limit": {"type": "integer", "default": 5}
                }
            }
        ),
        Tool(
            name="search_knowledge",
            description="Search knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["permissions", "apis", "patterns", "all"],
                        "default": "all"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_experiences",
            description="List all saved experiences",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用"""
    load_knowledge()

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
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False))]
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def _search_experience(args: dict) -> list[TextContent]:
    """搜索历史分析经验"""
    query = args["query"].lower()
    top_k = args.get("top_k", 5)

    results = []
    for exp in _experiences:
        score = 0
        if query in exp.get("title", "").lower():
            score += 10
        if query in exp.get("content", "").lower():
            score += 5
        for tag in exp.get("tags", []):
            if query in tag.lower():
                score += 3

        if score > 0:
            results.append({**exp, "relevance_score": score})

    results.sort(key=lambda x: x["relevance_score"], reverse=True)

    return [TextContent(type="text", text=json.dumps(results[:top_k], ensure_ascii=False, indent=2))]


async def _save_experience(args: dict) -> list[TextContent]:
    """保存分析经验"""
    title = args["title"]
    content = args["content"]
    tags = args.get("tags", [])
    malware_family = args.get("malware_family", "")
    risk_level = args.get("risk_level", "")

    experience = {
        "id": f"EXP_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "title": title,
        "content": content,
        "tags": tags,
        "malware_family": malware_family,
        "risk_level": risk_level,
        "created_at": datetime.now().isoformat()
    }

    _experiences.append(experience)
    save_experiences()

    return [TextContent(type="text", text=json.dumps({"success": True, "experience_id": experience["id"]}, ensure_ascii=False))]


async def _get_similar_cases(args: dict) -> list[TextContent]:
    """获取相似案例"""
    malware_family = args.get("malware_family", "")
    behavior_pattern = args.get("behavior_pattern", "")
    limit = args.get("limit", 5)

    results = []
    for exp in _experiences:
        score = 0

        if malware_family and exp.get("malware_family") == malware_family:
            score += 10

        if behavior_pattern:
            pattern_lower = behavior_pattern.lower()
            if pattern_lower in exp.get("content", "").lower():
                score += 5
            if pattern_lower in exp.get("title", "").lower():
                score += 3

        if score > 0:
            results.append({**exp, "similarity_score": score})

    results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return [TextContent(type="text", text=json.dumps(results[:limit], ensure_ascii=False, indent=2))]


async def _search_knowledge(args: dict) -> list[TextContent]:
    """搜索知识库"""
    query = args["query"].lower()
    category = args.get("category", "all")

    results = []

    for entry in _knowledge_base:
        if category != "all" and entry.get("category") != category:
            continue

        score = 0
        if query in entry.get("title", "").lower():
            score += 10
        if query in entry.get("description", "").lower():
            score += 5
        if query in entry.get("content", "").lower():
            score += 3

        if score > 0:
            results.append({**entry, "relevance_score": score})

    results.sort(key=lambda x: x["relevance_score"], reverse=True)

    return [TextContent(type="text", text=json.dumps(results[:20], ensure_ascii=False, indent=2))]


async def _list_experiences(args: dict) -> list[TextContent]:
    """列出所有经验"""
    tags_filter = args.get("tags", [])
    limit = args.get("limit", 20)

    results = _experiences

    if tags_filter:
        results = [
            exp for exp in _experiences
            if any(tag in exp.get("tags", []) for tag in tags_filter)
        ]

    return [TextContent(type="text", text=json.dumps(results[:limit], ensure_ascii=False, indent=2))]


async def main():
    """启动 knowledge-manager MCP Server"""
    logger.info("Starting knowledge-manager MCP server")
    load_knowledge()
    logger.info(f"Knowledge loaded: {len(_experiences)} experiences, {len(_knowledge_base)} knowledge items")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
