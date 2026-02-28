"""
threat-intel MCP Server

提供威胁情报查询能力，用于恶意软件分析和家族识别。

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

logger = logging.getLogger(__name__)

# 创建 Server 实例
server = Server("threat-intel")

# 全局状态
_threat_db: dict = {}
_ioc_db: dict = {}


def get_threat_db_path() -> str:
    """获取威胁情报数据库路径"""
    db_dir = Path(__file__).parent.parent.parent / "data" / "threat_intel"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir)


def load_threat_intel():
    """加载威胁情报数据库"""
    global _threat_db, _ioc_db

    db_path = get_threat_db_path()

    # 加载恶意软件家族数据库
    families_file = os.path.join(db_path, "families.json")
    if os.path.exists(families_file):
        try:
            with open(families_file, 'r', encoding='utf-8') as f:
                _threat_db = json.load(f)
            logger.info(f"Loaded {len(_threat_db)} malware families")
        except Exception as e:
            logger.error(f"Failed to load families: {e}")
            _threat_db = {}
    else:
        # 创建默认数据库
        _threat_db = {
            "HarmonyStealer": {
                "family": "HarmonyStealer",
                "type": "stealer",
                "description": "窃取用户隐私数据的恶意软件",
                "first_seen": "2024-01-15",
                "risk_level": "high",
                "behaviors": ["read_contacts", "read_sms", "data_exfiltration"],
                "iocs": {
                    "domains": ["c2.example.com"],
                    "ips": ["192.168.1.100"],
                    "certs": ["A1:B2:C3:D4:E5:F6"]
                }
            },
            "HarmonyRAT": {
                "family": "HarmonyRAT",
                "type": "rat",
                "description": "远程控制木马",
                "first_seen": "2024-02-01",
                "risk_level": "critical",
                "behaviors": ["remote_command", "persistence", "c2_communication"],
                "iocs": {
                    "domains": ["rat.evil.com"],
                    "ips": [],
                    "certs": []
                }
            }
        }
        _save_families()

    # 加载IOC数据库
    ioc_file = os.path.join(db_path, "ioc_index.json")
    if os.path.exists(ioc_file):
        try:
            with open(ioc_file, 'r', encoding='utf-8') as f:
                _ioc_db = json.load(f)
            logger.info(f"Loaded IOC index with {len(_ioc_db)} entries")
        except Exception as e:
            logger.error(f"Failed to load IOC index: {e}")
            _ioc_db = _build_ioc_index()
    else:
        _ioc_db = _build_ioc_index()


def _save_families():
    """保存家族数据库"""
    families_file = os.path.join(get_threat_db_path(), "families.json")
    try:
        with open(families_file, 'w', encoding='utf-8') as f:
            json.dump(_threat_db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save families: {e}")


def _build_ioc_index() -> dict:
    """构建IOC索引"""
    index = {
        "domains": {},
        "ips": {},
        "certs": {},
        "files": {},
        "mutexes": {}
    }

    for family_name, family_data in _threat_db.items():
        iocs = family_data.get("iocs", {})

        for domain in iocs.get("domains", []):
            index["domains"][domain] = family_name

        for ip in iocs.get("ips", []):
            index["ips"][ip] = family_name

        for cert in iocs.get("certs", []):
            index["certs"][cert] = family_name

    # 保存索引
    ioc_file = os.path.join(get_threat_db_path(), "ioc_index.json")
    try:
        with open(ioc_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save IOC index: {e}")

    return index


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="query_ioc",
            description="Query threat intelligence for an Indicator of Compromise (IoC)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ioc": {"type": "string", "description": "IOC value (domain, IP, cert hash, etc.)"},
                    "ioc_type": {
                        "type": "string",
                        "enum": ["domain", "ip", "cert", "file", "mutex", "auto"],
                        "default": "auto",
                        "description": "IoC type"
                    }
                },
                "required": ["ioc"]
            }
        ),
        Tool(
            name="get_family_info",
            description="Get detailed information about a malware family",
            inputSchema={
                "type": "object",
                "properties": {
                    "family": {"type": "string", "description": "Malware family name"}
                },
                "required": ["family"]
            }
        ),
        Tool(
            name="list_families",
            description="List all known malware families",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["stealer", "rat", "ransomware", "adware", "spyware", "banker", "all"],
                        "default": "all",
                        "description": "Filter by malware type"
                    }
                }
            }
        ),
        Tool(
            name="add_ioc",
            description="Add a new IoC to the threat intelligence database",
            inputSchema={
                "type": "object",
                "properties": {
                    "family": {"type": "string", "description": "Associated malware family"},
                    "ioc_type": {
                        "type": "string",
                        "enum": ["domain", "ip", "cert", "file", "mutex"],
                        "description": "IoC type"
                    },
                    "ioc_value": {"type": "string", "description": "IOC value"},
                    "description": {"type": "string", "description": "IOC description"},
                    "source": {"type": "string", "description": "Threat intelligence source"}
                },
                "required": ["family", "ioc_type", "ioc_value"]
            }
        ),
        Tool(
            name="check_sample_reputation",
            description="Check reputation of a sample based on multiple indicators",
            inputSchema={
                "type": "object",
                "properties": {
                    "domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of domains found"
                    },
                    "ips": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of IP addresses found"
                    },
                    "permissions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of permissions requested"
                    },
                    "behaviors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of suspicious behaviors"
                    }
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用"""
    load_threat_intel()

    try:
        if name == "query_ioc":
            return await _query_ioc(arguments)
        elif name == "get_family_info":
            return await _get_family_info(arguments)
        elif name == "list_families":
            return await _list_families(arguments)
        elif name == "add_ioc":
            return await _add_ioc(arguments)
        elif name == "check_sample_reputation":
            return await _check_sample_reputation(arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False))]
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


def _detect_ioc_type(ioc: str) -> str:
    """自动检测IoC类型"""
    if "/" in ioc and ":" in ioc:
        return "ip"
    elif "." in ioc:
        parts = ioc.split(".")
        if len(parts) >= 2 and parts[-1].isalpha():
            return "domain"
        if parts[-1].isdigit():
            return "ip"
    elif ":" in ioc and len(ioc.split(":")) == 6:
        return "cert"
    elif "\\" in ioc or "/" in ioc:
        return "file"
    return "unknown"


async def _query_ioc(args: dict) -> list[TextContent]:
    """查询IoC"""
    ioc = args["ioc"]
    ioc_type = args.get("ioc_type", "auto")

    if ioc_type == "auto":
        ioc_type = _detect_ioc_type(ioc)

    result = {
        "ioc": ioc,
        "ioc_type": ioc_type,
        "found": False,
        "families": []
    }

    if ioc_type in _ioc_db:
        if ioc in _ioc_db[ioc_type]:
            family_name = _ioc_db[ioc_type][ioc]
            result["found"] = True
            result["families"].append(family_name)
            if family_name in _threat_db:
                result["family_info"] = _threat_db[family_name]

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _get_family_info(args: dict) -> list[TextContent]:
    """获取家族信息"""
    family = args["family"]

    if family not in _threat_db:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Family {family} not found",
            "available_families": list(_threat_db.keys())
        }, ensure_ascii=False))]

    return [TextContent(type="text", text=json.dumps(_threat_db[family], ensure_ascii=False, indent=2))]


async def _list_families(args: dict) -> list[TextContent]:
    """列出所有家族"""
    mal_type = args.get("type", "all")

    families = []
    for family_name, family_data in _threat_db.items():
        if mal_type != "all" and family_data.get("type") != mal_type:
            continue
        families.append({
            "name": family_name,
            "type": family_data.get("type"),
            "description": family_data.get("description"),
            "first_seen": family_data.get("first_seen"),
            "risk_level": family_data.get("risk_level")
        })

    families.sort(key=lambda x: x["name"])

    return [TextContent(type="text", text=json.dumps({
        "total": len(families),
        "families": families
    }, ensure_ascii=False, indent=2))]


async def _add_ioc(args: dict) -> list[TextContent]:
    """添加IoC"""
    family = args["family"]
    ioc_type = args["ioc_type"]
    ioc_value = args["ioc_value"]
    description = args.get("description", "")
    source = args.get("source", "manual")

    # 确保家族存在
    if family not in _threat_db:
        _threat_db[family] = {
            "family": family,
            "type": "unknown",
            "description": description,
            "first_seen": datetime.now().strftime("%Y-%m-%d"),
            "risk_level": "medium",
            "behaviors": [],
            "iocs": {"domains": [], "ips": [], "certs": []},
            "sources": [source]
        }

    # 添加IoC
    ioc_key = f"{ioc_type}s"
    if ioc_key not in _threat_db[family]["iocs"]:
        _threat_db[family]["iocs"][ioc_key] = []

    if ioc_value not in _threat_db[family]["iocs"][ioc_key]:
        _threat_db[family]["iocs"][ioc_key].append(ioc_value)

        # 更新索引
        if ioc_type not in _ioc_db:
            _ioc_db[ioc_type] = {}
        _ioc_db[ioc_type][ioc_value] = family

    # 保存
    _save_families()
    _build_ioc_index()

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        "family": family,
        "ioc": ioc_value,
        "ioc_type": ioc_type
    }, ensure_ascii=False))]


async def _check_sample_reputation(args: dict) -> list[TextContent]:
    """检查样本信誉"""
    domains = args.get("domains", [])
    ips = args.get("ips", [])
    permissions = args.get("permissions", [])
    behaviors = args.get("behaviors", [])

    score = 100  # 从100开始，扣分
    findings = []
    matched_families = set()

    # 检查域名
    for domain in domains:
        for family_name, family_data in _threat_db.items():
            if domain in family_data.get("iocs", {}).get("domains", []):
                score -= 30
                findings.append({
                    "severity": "high",
                    "type": "malicious_domain",
                    "value": domain,
                    "family": family_name
                })
                matched_families.add(family_name)

    # 检查IP
    for ip in ips:
        for family_name, family_data in _threat_db.items():
            if ip in family_data.get("iocs", {}).get("ips", []):
                score -= 30
                findings.append({
                    "severity": "high",
                    "type": "malicious_ip",
                    "value": ip,
                    "family": family_name
                })
                matched_families.add(family_name)

    # 检查高危权限
    high_risk_permissions = [
        "ohos.permission.READ_CONTACTS",
        "ohos.permission.READ_SMS",
        "ohos.permission.SEND_SMS",
        "ohos.permission.ACCESS_LOCATION"
    ]
    for perm in permissions:
        if perm in high_risk_permissions:
            score -= 5
            findings.append({
                "severity": "medium",
                "type": "high_risk_permission",
                "value": perm
            })

    # 检查可疑行为
    suspicious_behaviors = [
        "data_exfiltration",
        "c2_communication",
        "persistence",
        "stealth_mode",
        "privilege_escalation"
    ]
    for behavior in behaviors:
        if behavior in suspicious_behaviors:
            score -= 15
            findings.append({
                "severity": "high",
                "type": "suspicious_behavior",
                "value": behavior
            })

    # 确定风险等级
    if score >= 70:
        risk_level = "low"
    elif score >= 40:
        risk_level = "medium"
    elif score >= 20:
        risk_level = "high"
    else:
        risk_level = "critical"

    return [TextContent(type="text", text=json.dumps({
        "reputation_score": max(0, score),
        "risk_level": risk_level,
        "findings": findings,
        "matched_families": list(matched_families),
        "recommendation": _get_recommendation(risk_level, matched_families)
    }, ensure_ascii=False, indent=2))]


def _get_recommendation(risk_level: str, families: set) -> str:
    """获取建议"""
    if risk_level == "critical":
        return "立即隔离该样本，进行全面深入分析。"
    elif risk_level == "high":
        return "高度可疑，建议深入分析其行为。"
    elif risk_level == "medium":
        return "存在一定风险，建议进一步检查。"
    else:
        return "风险较低，但仍需保持警惕。"


async def main():
    """启动 threat-intel MCP Server"""
    load_threat_intel()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
