"""
data-source MCP Server

提供检测任务数据访问能力。

使用官方 MCP SDK 实现 stdio 协议。
"""
import asyncio
import json
import logging
import os
import sqlite3
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
from mcp_servers.logging_config import get_data_source_logger

logger = get_data_source_logger()

# 创建 Server 实例
server = Server("data-source")

# 全局状态
_db_path: str = None


def get_db_path() -> str:
    """获取数据库路径"""
    global _db_path
    if _db_path is None:
        data_dir = Path(__file__).parent.parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        _db_path = str(data_dir / "tasks.db")
    return _db_path


def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    # 创建任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            package_name TEXT NOT NULL,
            package_version TEXT,
            developer TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'normal',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建检测结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detection_results (
            task_id TEXT PRIMARY KEY,
            machine_score REAL,
            risk_level TEXT,
            risk_tags TEXT,
            detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    # 创建分析报告表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_reports (
            task_id TEXT PRIMARY KEY,
            conclusion TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    conn.commit()
    conn.close()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="get_tasks",
            description="Get detection tasks from database",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "Filter by task status"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 100,
                        "description": "Maximum number of tasks to return"
                    }
                }
            }
        ),
        Tool(
            name="get_detection_result",
            description="Get machine detection result for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task identifier"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="update_task_status",
            description="Update task status and optionally add conclusion",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"]
                    },
                    "conclusion": {"type": "string"}
                },
                "required": ["task_id", "status"]
            }
        ),
        Tool(
            name="import_tasks_from_csv",
            description="Import tasks from CSV file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "batch_size": {"type": "integer", "default": 100}
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="create_task",
            description="Create a new analysis task",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {"type": "string"},
                    "package_version": {"type": "string"},
                    "developer": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"]
                    }
                },
                "required": ["package_name"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用"""
    init_database()
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if name == "get_tasks":
            status = arguments.get("status")
            limit = arguments.get("limit", 100)

            if status:
                cursor.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )

            rows = cursor.fetchall()
            tasks = [dict(row) for row in rows]

            return [TextContent(
                type="text",
                text=json.dumps({"tasks": tasks, "count": len(tasks)}, ensure_ascii=False, indent=2)
            )]

        elif name == "get_detection_result":
            task_id = arguments["task_id"]

            cursor.execute(
                "SELECT * FROM detection_results WHERE task_id = ?",
                (task_id,)
            )
            row = cursor.fetchone()

            if row:
                result = dict(row)
                if result.get("risk_tags"):
                    try:
                        result["risk_tags"] = json.loads(result["risk_tags"])
                    except:
                        pass
                return [TextContent(
                    type="text",
                    text=json.dumps(result, ensure_ascii=False, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"No detection result for task: {task_id}"}, ensure_ascii=False)
                )]

        elif name == "update_task_status":
            task_id = arguments["task_id"]
            status = arguments["status"]
            conclusion = arguments.get("conclusion")

            cursor.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now().isoformat(), task_id)
            )

            if conclusion:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO analysis_reports (task_id, conclusion, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (task_id, conclusion, datetime.now().isoformat())
                )

            conn.commit()

            changes = cursor.execute("SELECT changes()").fetchone()[0]

            if changes > 0:
                return [TextContent(
                    type="text",
                    text=json.dumps({"success": True, "task_id": task_id, "status": status}, ensure_ascii=False)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Task not found: {task_id}"}, ensure_ascii=False)
                )]

        elif name == "import_tasks_from_csv":
            file_path = arguments["file_path"]
            batch_size = arguments.get("batch_size", 100)

            if not os.path.exists(file_path):
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"File not found: {file_path}"}, ensure_ascii=False)
                )]

            import csv

            imported = 0
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    task_id = f"TASK_{datetime.now().strftime('%Y%m%d%H%M%S')}_{imported}"

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO tasks (id, package_name, package_version, developer, status)
                        VALUES (?, ?, ?, ?, 'pending')
                        """,
                        (task_id, row.get("package_name", ""), row.get("version", ""), row.get("developer", ""))
                    )

                    imported += 1
                    if imported >= batch_size:
                        break

            conn.commit()

            return [TextContent(
                type="text",
                text=json.dumps({"success": True, "imported": imported}, ensure_ascii=False)
            )]

        elif name == "create_task":
            package_name = arguments["package_name"]
            package_version = arguments.get("package_version", "1.0.0")
            developer = arguments.get("developer", "unknown")
            priority = arguments.get("priority", "normal")

            task_id = f"TASK_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(package_name) % 10000:04d}"

            cursor.execute(
                """
                INSERT INTO tasks (id, package_name, package_version, developer, priority, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (task_id, package_name, package_version, developer, priority)
            )
            conn.commit()

            return [TextContent(
                type="text",
                text=json.dumps({"success": True, "task_id": task_id}, ensure_ascii=False)
            )]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
            )]

    finally:
        conn.close()


async def main():
    """启动 data-source MCP Server"""
    logger.info("Starting data-source MCP server")
    # 初始化数据库
    init_database()
    logger.info(f"Database initialized at {get_db_path()}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
