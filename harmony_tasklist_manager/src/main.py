"""HarmonyOS Task List Manager MCP Server.

使用官方 MCP SDK 实现 stdio 协议，兼容低版本 Python。
"""

import asyncio
import json
import logging
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 获取服务器根目录（包含 data/ 和 src/ 的目录）
_server_root = Path(__file__).parent.parent.absolute()
src_dir = _server_root / "src"
sys.path.insert(0, str(src_dir))

# 设置数据文件的环境变量（使用绝对路径，避免并发时的竞争条件）
os.environ["HARMONY_DATA_FILE"] = str(_server_root / "data" / "tasklist.txt")
os.environ["HARMONY_TITLE_FILE"] = str(_server_root / "data" / "title.txt")

# 添加项目根目录到路径（用于导入mcp_servers.logging_config）
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from src.config import Config
from src.search import DataManager
from src.models import error_response, ValidationError

# 导入MCP日志配置
from mcp_servers.logging_config import get_harmony_tasklist_logger

logger = get_harmony_tasklist_logger()

# Initialize configuration
config = Config()
# 从配置文件读取日志级别（可选）
config_log_level = config.get("server", "log_level")
if config_log_level:
    logger.setLevel(getattr(logging, config_log_level.upper(), logging.INFO))

# Initialize data manager
data_manager = DataManager(
    title_file_path=config.title_file_path,
    data_file_path=config.data_file_path,
    cache_ttl=config.cache_ttl,
)

# Create MCP server
server = Server("harmony-tasklist-manager")


# Helper functions
def validate_limit(limit: Optional[int], max_limit: int, default: int) -> int:
    """Validate and normalize limit parameter."""
    if limit is None:
        return default
    if limit < 0:
        raise ValidationError("limit cannot be negative")
    if limit > max_limit:
        raise ValidationError(f"limit cannot exceed {max_limit}")
    return limit


def validate_offset(offset: Optional[int]) -> int:
    """Validate and normalize offset parameter."""
    if offset is None:
        return 0
    if offset < 0:
        raise ValidationError("offset cannot be negative")
    return offset


def to_json_response(data: Any) -> list[TextContent]:
    """Convert dict to JSON TextContent response."""
    return [TextContent(
        type="text",
        text=json.dumps(data, ensure_ascii=False, indent=2)
    )]


def handle_error(error: Exception, context: str) -> list[TextContent]:
    """Handle error and return error response."""
    logger.exception(f"Error in {context}")
    if isinstance(error, ValidationError):
        return to_json_response(error_response("ValidationError", str(error)))
    return to_json_response(error_response("InternalError", str(error)))


# Tool definitions
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_all_tasks",
            description="Get all tasks from the task list with pagination support",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (default: 100, max: 1000)"
                    },
                    "offset": {
                        "type": "number",
                        "description": "Pagination offset (default: 0)"
                    }
                }
            }
        ),
        Tool(
            name="search_tasks",
            description="Search tasks by keyword across multiple fields",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"},
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of fields to search (default: all fields)"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether to distinguish case (default: false)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (default: 100)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_task_by_id",
            description="Get a single task by task_id",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The task ID to search for"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="get_field_metadata",
            description="Get field metadata information with descriptions",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="filter_tasks",
            description="Filter tasks by multiple field conditions",
            inputSchema={
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Dictionary of {field: value} conditions"
                    },
                    "match_mode": {
                        "type": "string",
                        "enum": ["all", "any"],
                        "description": "'all' (all conditions must match) or 'any' (any condition matches)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (default: 100)"
                    }
                },
                "required": ["filters"]
            }
        ),
        Tool(
            name="get_statistics",
            description="Get task statistics, optionally grouped by a field",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_by": {
                        "type": "string",
                        "description": "Field name to group statistics by (optional)"
                    }
                }
            }
        ),
        Tool(
            name="get_server_config",
            description="Get current server configuration",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="reload_data",
            description="Force reload data from files (clear cache)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_all_tasks":
            limit = validate_limit(
                arguments.get("limit"),
                config.max_limit,
                config.default_limit
            )
            offset = validate_offset(arguments.get("offset"))

            tasks = data_manager.get_tasks()
            fields = data_manager.get_fields()

            total = len(tasks)
            start = offset
            end = start + limit
            paginated_tasks = tasks[start:end]

            fields_metadata = {
                f.key: {
                    "name": f.en_name,
                    "label": f.cn_short_name,
                    "description": f.cn_full_name,
                }
                for f in fields
            }

            return to_json_response({
                "success": True,
                "total": total,
                "returned": len(paginated_tasks),
                "offset": offset,
                "tasks": paginated_tasks,
                "fields": fields_metadata,
            })

        elif name == "search_tasks":
            query = arguments["query"]
            fields = arguments.get("fields")
            case_sensitive = arguments.get("case_sensitive", False)
            limit = validate_limit(
                arguments.get("limit"),
                config.max_limit,
                config.default_limit
            )

            tasks = data_manager.get_tasks()
            field_list = data_manager.get_fields()

            from src.search import TaskSearcher
            searcher = TaskSearcher(field_list)
            result = searcher.search(tasks, query, fields, case_sensitive)

            result["tasks"] = result["tasks"][:limit]
            result["returned"] = len(result["tasks"])

            return to_json_response(result)

        elif name == "get_task_by_id":
            task_id = arguments["task_id"]
            tasks = data_manager.get_tasks()

            for task in tasks:
                if task.get("task_id") == task_id:
                    return to_json_response({"success": True, "task": task})

            return to_json_response({"success": False, "error": f"Task not found: {task_id}"})

        elif name == "get_field_metadata":
            fields = data_manager.get_fields()

            field_list = [
                {
                    "key": f.key,
                    "name": f.en_name,
                    "label": f.cn_short_name,
                    "description": f.cn_full_name,
                    "index": f.index,
                }
                for f in fields
            ]

            return to_json_response({
                "success": True,
                "fields": field_list,
                "total_fields": len(field_list)
            })

        elif name == "filter_tasks":
            filters = arguments["filters"]
            match_mode = arguments.get("match_mode", "all")
            limit = validate_limit(
                arguments.get("limit"),
                config.max_limit,
                config.default_limit
            )

            if match_mode not in ("all", "any"):
                raise ValidationError('match_mode must be "all" or "any"')

            tasks = data_manager.get_tasks()

            from src.search import AdvancedSearcher
            result = AdvancedSearcher.filter_by_conditions(tasks, filters, match_mode)

            result["tasks"] = result["tasks"][:limit]
            result["returned"] = len(result["tasks"])

            return to_json_response(result)

        elif name == "get_statistics":
            group_by = arguments.get("group_by")
            tasks = data_manager.get_tasks()

            from src.search import AdvancedSearcher
            result = AdvancedSearcher.get_statistics(tasks, group_by)

            return to_json_response(result)

        elif name == "get_server_config":
            title_exists = Path(config.title_file_path).exists()
            data_exists = Path(config.data_file_path).exists()

            return to_json_response({
                "success": True,
                "config": {
                    "data_file_path": config.data_file_path,
                    "data_file_exists": data_exists,
                    "title_file_path": config.title_file_path,
                    "title_file_exists": title_exists,
                    "encoding": "utf-8",
                    "default_limit": config.default_limit,
                    "max_limit": config.max_limit,
                    "cache_ttl_minutes": config.get("query", "cache_ttl_minutes"),
                },
            })

        elif name == "reload_data":
            data_manager.clear_cache()
            tasks = data_manager.get_tasks(force_reload=True)
            fields = data_manager.get_fields()

            return to_json_response({
                "success": True,
                "message": "Data reloaded successfully",
                "tasks_loaded": len(tasks),
                "fields_loaded": len(fields),
            })

        else:
            return to_json_response({"error": f"Unknown tool: {name}"})

    except Exception as e:
        return handle_error(e, name)


async def main():
    """Start the MCP server."""
    logger.info(f"Starting harmony-tasklist-manager v1.0.0")
    logger.info(f"Data file: {config.data_file_path}")
    logger.info(f"Title file: {config.title_file_path}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
