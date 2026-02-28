"""HarmonyOS Task List Manager MCP Server entry point."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Get the directory containing this file
_server_dir = Path(__file__).parent.absolute()
_src_dir = _server_dir / "src"

# 关键：需要将 _src_dir 添加到 sys.path，这样 "from src.search" 才能工作
# 但是要确保它能作为 "src" 包被导入
if str(_server_dir) not in sys.path:
    sys.path.insert(0, str(_server_dir))

# 添加项目根目录到路径（用于导入 mcp_servers.logging_config 等）
_project_root = _server_dir.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 设置数据文件环境变量（优先使用已存在的环境变量，否则使用默认路径）
# 这样用户可以在 config/mcp_servers.json 的 env 字段中自定义路径
if "HARMONY_DATA_FILE" not in os.environ:
    os.environ["HARMONY_DATA_FILE"] = str(_server_dir / "data" / "tasklist.txt")

if "HARMONY_TITLE_FILE" not in os.environ:
    os.environ["HARMONY_TITLE_FILE"] = str(_server_dir / "data" / "title.txt")

# 日志级别也可以通过环境变量配置
if "HARMONY_LOG_LEVEL" not in os.environ:
    os.environ["HARMONY_LOG_LEVEL"] = "INFO"

# 现在导入 src.main（因为 _server_dir 在 sys.path 中，所以 "from src.xxx" 能正确解析）
from src import main

if __name__ == "__main__":
    log_level = os.environ.get("HARMONY_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main.main())
