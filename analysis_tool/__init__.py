"""
analysis-tool MCP Server

提供 HAP 包分析工具能力。

使用官方 MCP SDK 实现 stdio 协议。
"""
import asyncio
import json
import logging
import os
import re
import zipfile
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入MCP日志配置
from mcp_servers.logging_config import get_analysis_tool_logger

logger = get_analysis_tool_logger()

# 创建 Server 实例
server = Server("analysis-tool")

# 全局状态
_temp_dir: str = None


def get_temp_dir() -> str:
    """获取临时目录"""
    global _temp_dir
    if _temp_dir is None:
        temp_dir = Path(__file__).parent.parent.parent / "temp" / "analysis"
        temp_dir.mkdir(parents=True, exist_ok=True)
        _temp_dir = str(temp_dir)
    return _temp_dir


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="decompile_hap",
            description="Decompile HAP package to extract source code",
            inputSchema={
                "type": "object",
                "properties": {
                    "hap_path": {"type": "string", "description": "Path to HAP file"},
                    "output_dir": {"type": "string", "description": "Output directory (optional)"}
                },
                "required": ["hap_path"]
            }
        ),
        Tool(
            name="analyze_permissions",
            description="Analyze app permissions from module.json5",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_path": {"type": "string", "description": "Path to extracted package"}
                },
                "required": ["package_path"]
            }
        ),
        Tool(
            name="search_code",
            description="Search code pattern in decompiled source",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_dir": {"type": "string"},
                    "pattern": {"type": "string"},
                    "file_pattern": {"type": "string", "default": "*.ets"},
                    "context_lines": {"type": "integer", "default": 3}
                },
                "required": ["source_dir", "pattern"]
            }
        ),
        Tool(
            name="analyze_apis",
            description="Analyze API calls in source code",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_dir": {"type": "string"},
                    "api_categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "API categories (location, contact, sms, network, storage)"
                    }
                },
                "required": ["source_dir"]
            }
        ),
        Tool(
            name="extract_manifest",
            description="Extract and parse manifest information from HAP",
            inputSchema={
                "type": "object",
                "properties": {"hap_path": {"type": "string"}},
                "required": ["hap_path"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用"""
    try:
        if name == "decompile_hap":
            return await _decompile_hap(arguments)
        elif name == "analyze_permissions":
            return await _analyze_permissions(arguments)
        elif name == "search_code":
            return await _search_code(arguments)
        elif name == "analyze_apis":
            return await _analyze_apis(arguments)
        elif name == "extract_manifest":
            return await _extract_manifest(arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False))]
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def _decompile_hap(args: dict) -> list[TextContent]:
    """反编译 HAP 包"""
    hap_path = args["hap_path"]
    output_dir = args.get("output_dir")

    if not os.path.exists(hap_path):
        return [TextContent(type="text", text=json.dumps({"error": f"HAP file not found: {hap_path}"}, ensure_ascii=False))]

    if not output_dir:
        package_name = Path(hap_path).stem
        output_dir = os.path.join(get_temp_dir(), package_name)

    os.makedirs(output_dir, exist_ok=True)

    try:
        with ZipFile(hap_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)

        results = {"output_dir": output_dir, "files": [], "abilities": []}

        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, output_dir)
                results["files"].append(rel_path)

                if "Ability" in file or file.endswith(".ets"):
                    results["abilities"].append(rel_path)

        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Decompilation failed: {e}"}, ensure_ascii=False))]


async def _analyze_permissions(args: dict) -> list[TextContent]:
    """分析应用权限"""
    package_path = args["package_path"]
    module_json = os.path.join(package_path, "module.json5")

    if not os.path.exists(module_json):
        return [TextContent(type="text", text=json.dumps({"error": f"module.json5 not found in: {package_path}"}, ensure_ascii=False))]

    try:
        with open(module_json, 'r', encoding='utf-8') as f:
            content = f.read()

        permissions = list(set(re.findall(r'ohos\.permission\.[\w.]+', content)))

        sensitive_permissions = {
            "ohos.permission.LOCATION": "位置信息",
            "ohos.permission.APPROXIMATELY_LOCATION": "近似位置",
            "ohos.permission.LOCATION_IN_BACKGROUND": "后台位置",
            "ohos.permission.READ_CONTACTS": "读取通讯录",
            "ohos.permission.WRITE_CONTACTS": "写入通讯录",
            "ohos.permission.READ_MESSAGES": "读取短信",
            "ohos.permission.SEND_MESSAGES": "发送短信",
            "ohos.permission.INTERNET": "网络访问",
            "ohos.permission.CAMERA": "相机",
            "ohos.permission.READ_IMAGEVIDEO": "读写图片视频",
            "ohos.permission.MICROPHONE": "麦克风",
            "ohos.permission.READ_CALL_LOG": "读取通话记录",
            "ohos.permission.CALL_PHONE": "拨打电话",
        }

        sensitive = []
        for perm in permissions:
            if perm in sensitive_permissions:
                sensitive.append({
                    "permission": perm,
                    "description": sensitive_permissions[perm],
                    "risk_level": "high" if "BACKGROUND" in perm or "CONTACTS" in perm or "MESSAGES" in perm else "medium"
                })

        result = {
            "total_permissions": len(permissions),
            "permissions": permissions,
            "sensitive_permissions": sensitive,
            "risk_count": len(sensitive)
        }

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Permission analysis failed: {e}"}, ensure_ascii=False))]


async def _search_code(args: dict) -> list[TextContent]:
    """搜索代码模式"""
    source_dir = args["source_dir"]
    pattern = args.get("pattern", "")
    context_lines = args.get("context_lines", 3)

    if not os.path.exists(source_dir):
        return [TextContent(type="text", text=json.dumps({"error": f"Source directory not found: {source_dir}"}, ensure_ascii=False))]

    try:
        results = []
        regex = re.compile(pattern, re.IGNORECASE)

        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".ets") or file.endswith(".ts") or file.endswith(".js"):
                    file_path = os.path.join(root, file)

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()

                        for i, line in enumerate(lines):
                            if regex.search(line):
                                start = max(0, i - context_lines)
                                end = min(len(lines), i + context_lines + 1)

                                results.append({
                                    "file": os.path.relpath(file_path, source_dir),
                                    "line": i + 1,
                                    "content": line.strip(),
                                    "context": "".join(lines[start:end])
                                })
                    except Exception:
                        continue

        result = {
            "pattern": pattern,
            "matches": len(results),
            "results": results[:50]
        }

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Code search failed: {e}"}, ensure_ascii=False))]


async def _analyze_apis(args: dict) -> list[TextContent]:
    """分析 API 调用"""
    source_dir = args["source_dir"]
    api_categories = args.get("api_categories", ["location", "contact", "sms", "network"])

    api_patterns = {
        "location": [r"@ohos\.geolocation", r"geoLocationManager", r"getLocation", r"on\(['\"]location"],
        "contact": [r"@ohos\.contact", r"queryContacts", r"getContact"],
        "sms": [r"@ohos\.sms", r"sendSms", r"createMessage"],
        "network": [r"@ohos\.net\.http", r"fetch\(", r"http\.request"],
        "storage": [r"@ohos\.file\.fs", r"readText", r"writeText"],
    }

    results = {}

    try:
        for category in api_categories:
            if category not in api_patterns:
                continue

            patterns = api_patterns[category]
            combined_pattern = "|".join(f"({p})" for p in patterns)

            search_result = await _search_code({
                "source_dir": source_dir,
                "pattern": combined_pattern,
                "file_pattern": "*.ets",
                "context_lines": 2
            })

            result_data = json.loads(search_result[0].text)
            results[category] = {
                "matches": result_data["matches"],
                "files_affected": len(set(r["file"] for r in result_data.get("results", [])))
            }

        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"API analysis failed: {e}"}, ensure_ascii=False))]


async def _extract_manifest(args: dict) -> list[TextContent]:
    """提取 manifest 信息"""
    hap_path = args["hap_path"]

    if not os.path.exists(hap_path):
        return [TextContent(type="text", text=json.dumps({"error": f"HAP file not found: {hap_path}"}, ensure_ascii=False))]

    try:
        with ZipFile(hap_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()

            manifest_files = [f for f in file_list if "module.json" in f.lower() or "config.json" in f.lower()]

            results = {
                "package": hap_path,
                "total_files": len(file_list),
                "manifest_files": manifest_files
            }

            for manifest_file in manifest_files:
                try:
                    content = zip_ref.read(manifest_file).decode('utf-8')
                    results[manifest_file] = content[:2000]
                except:
                    pass

        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Manifest extraction failed: {e}"}, ensure_ascii=False))]


async def main():
    """启动 analysis-tool MCP Server"""
    logger.info("Starting analysis-tool MCP server")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
