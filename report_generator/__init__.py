"""
report-generator MCP Server

提供分析报告生成能力，支持多种格式和模板。

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
server = Server("report-generator")

# 全局状态
_reports_dir: str = None
_templates: dict = {}


def get_reports_dir() -> str:
    """获取报告目录"""
    global _reports_dir
    if _reports_dir is None:
        reports_dir = Path(__file__).parent.parent.parent / "data" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        _reports_dir = str(reports_dir)
    return _reports_dir


def load_templates():
    """加载报告模板"""
    global _templates

    template_dir = Path(__file__).parent.parent.parent / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)

    # 默认模板
    _templates = {
        "standard": {
            "name": "标准分析报告",
            "description": "适用于常规恶意软件分析",
            "sections": [
                "基本信息",
                "分析概要",
                "权限分析",
                "网络行为",
                "隐私合规",
                "家族识别",
                "结论与建议",
            ],
        },
        "quick": {
            "name": "快速扫描报告",
            "description": "适用于批量快速扫描",
            "sections": ["基本信息", "风险评级", "主要发现", "处理建议"],
        },
        "detailed": {
            "name": "详细分析报告",
            "description": "适用于深度分析",
            "sections": [
                "执行摘要",
                "样本基本信息",
                "静态分析",
                "动态分析",
                "网络行为分析",
                "权限分析",
                "隐私合规评估",
                "恶意软件家族识别",
                "IoC清单",
                "附录",
            ],
        },
    }


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="generate_report",
            description="Generate a malware analysis report",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Application name"},
                    "package_name": {"type": "string", "description": "Package name"},
                    "analysis_data": {
                        "type": "object",
                        "description": "Analysis results data",
                    },
                    "template": {
                        "type": "string",
                        "enum": ["standard", "quick", "detailed"],
                        "default": "standard",
                        "description": "Report template",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["markdown", "json", "html"],
                        "default": "markdown",
                        "description": "Output format",
                    },
                    "save": {
                        "type": "boolean",
                        "default": true,
                        "description": "Save report to file",
                    },
                },
                "required": ["app_name", "package_name", "analysis_data"],
            },
        ),
        Tool(
            name="list_templates",
            description="List available report templates",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_report",
            description="Get a previously generated report",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_id": {
                        "type": "string",
                        "description": "Report ID or filename",
                    }
                },
                "required": ["report_id"],
            },
        ),
        Tool(
            name="list_reports",
            description="List all generated reports",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 20},
                    "app_name": {"type": "string", "description": "Filter by app name"},
                },
            },
        ),
        Tool(
            name="export_iocs",
            description="Export IoCs from analysis data",
            inputSchema={
                "type": "object",
                "properties": {
                    "analysis_data": {
                        "type": "object",
                        "description": "Analysis results",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "csv", "stix", "txt"],
                        "default": "json",
                    },
                },
                "required": ["analysis_data"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用"""
    load_templates()

    try:
        if name == "generate_report":
            return await _generate_report(arguments)
        elif name == "list_templates":
            return await _list_templates(arguments)
        elif name == "get_report":
            return await _get_report(arguments)
        elif name == "list_reports":
            return await _list_reports(arguments)
        elif name == "export_iocs":
            return await _export_iocs(arguments)
        else:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": f"Unknown tool: {name}"}, ensure_ascii=False
                    ),
                )
            ]
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return [
            TextContent(
                type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False)
            )
        ]


def _calculate_risk_score(data: dict) -> tuple[int, str]:
    """计算风险评分"""
    score = 0

    # 权限风险
    permissions = data.get("permissions", {})
    high_risk = permissions.get("high_risk", [])
    score += len(high_risk) * 15

    # 网络风险
    network = data.get("network", {})
    if network.get("suspicious_connections"):
        score += 30
    if network.get("background_connections"):
        score += 20

    # 隐私风险
    privacy = data.get("privacy", {})
    if privacy.get("data_collection"):
        score += 25
    if privacy.get("excessive_permissions"):
        score += 15

    # 家族匹配
    family = data.get("family", {})
    if family.get("matched"):
        score += 40

    # 确定风险等级
    if score >= 80:
        level = "critical"
    elif score >= 60:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"

    return min(score, 100), level


async def _generate_report(args: dict) -> list[TextContent]:
    """生成报告"""
    app_name = args["app_name"]
    package_name = args["package_name"]
    analysis_data = args["analysis_data"]
    template = args.get("template", "standard")
    output_format = args.get("output_format", "markdown")
    save = args.get("save", True)

    # 计算风险评分
    risk_score, risk_level = _calculate_risk_score(analysis_data)

    # 生成报告ID
    report_id = f"{package_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 根据格式生成内容
    if output_format == "markdown":
        content = _generate_markdown_report(
            report_id,
            app_name,
            package_name,
            analysis_data,
            risk_score,
            risk_level,
            template,
        )
    elif output_format == "json":
        content = json.dumps(
            {
                "report_id": report_id,
                "app_name": app_name,
                "package_name": package_name,
                "generated_at": datetime.now().isoformat(),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "template": template,
                "data": analysis_data,
            },
            ensure_ascii=False,
            indent=2,
        )
    else:  # html
        content = _generate_html_report(
            report_id,
            app_name,
            package_name,
            analysis_data,
            risk_score,
            risk_level,
            template,
        )

    # 保存报告
    file_path = None
    if save:
        ext = {"markdown": ".md", "json": ".json", "html": ".html"}[output_format]
        file_path = os.path.join(get_reports_dir(), f"{report_id}{ext}")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return [
        TextContent(
            type="text",
            text=json.dumps(
                {
                    "success": True,
                    "report_id": report_id,
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "file_path": file_path,
                    "content": content if not save else f"Report saved to {file_path}",
                },
                ensure_ascii=False,
            ),
        )
    ]


def _generate_markdown_report(
    report_id: str,
    app_name: str,
    package_name: str,
    data: dict,
    risk_score: int,
    risk_level: str,
    template: str,
) -> str:
    """生成Markdown格式报告"""
    lines = []

    # 标题
    lines.append(f"# {app_name} 分析报告")
    lines.append("")
    lines.append(f"**报告ID**: {report_id}")
    lines.append(f"**包名**: {package_name}")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**风险评分**: {risk_score}/100")
    lines.append(f"**风险等级**: {risk_level.upper()}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 执行摘要
    lines.append("## 执行摘要")
    lines.append("")
    lines.append(f"对 `{app_name}` ({package_name}) 进行了全面的安全分析。")

    if risk_level == "critical":
        lines.append("**检测结果：该应用存在严重安全风险，疑似恶意软件。**")
    elif risk_level == "high":
        lines.append("**检测结果：该应用存在高危行为，建议谨慎使用。**")
    elif risk_level == "medium":
        lines.append("**检测结果：该应用存在一定风险，需要进一步检查。**")
    else:
        lines.append("**检测结果：该应用风险较低，未发现明显恶意行为。**")
    lines.append("")

    # 权限分析
    lines.append("## 权限分析")
    lines.append("")
    permissions = data.get("permissions", {})
    lines.append(f"- 申请权限总数: {permissions.get('total', 0)}")
    lines.append(f"- 高风险权限: {len(permissions.get('high_risk', []))}")
    lines.append(f"- 中风险权限: {len(permissions.get('medium_risk', []))}")
    lines.append("")

    if permissions.get("high_risk"):
        lines.append("### 高风险权限")
        lines.append("")
        for perm in permissions["high_risk"]:
            lines.append(f"- `{perm}`")
        lines.append("")

    # 网络行为
    lines.append("## 网络行为")
    lines.append("")
    network = data.get("network", {})
    lines.append(
        f"- 可疑连接: {['是' if network.get('suspicious_connections') else '否'][0]}"
    )
    lines.append(
        f"- 后台连接: {['是' if network.get('background_connections') else '否'][0]}"
    )
    lines.append("")

    if network.get("domains"):
        lines.append("### 发现的域名")
        lines.append("")
        for domain in network["domains"]:
            lines.append(f"- {domain}")
        lines.append("")

    # 隐私合规
    lines.append("## 隐私合规")
    lines.append("")
    privacy = data.get("privacy", {})
    lines.append(f"- 数据收集: {['是' if privacy.get('data_collection') else '否'][0]}")
    lines.append(
        f"- 过度权限: {['是' if privacy.get('excessive_permissions') else '否'][0]}"
    )
    lines.append(f"- 隐私声明: {['有' if privacy.get('privacy_policy') else '无'][0]}")
    lines.append("")

    # 家族识别
    lines.append("## 家族识别")
    lines.append("")
    family = data.get("family", {})
    if family.get("matched"):
        lines.append(f"**匹配家族**: {family.get('family_name', 'Unknown')}")
        lines.append(f"**置信度**: {family.get('confidence', 0)}%")
        lines.append("")
        if family.get("description"):
            lines.append(f"家族描述: {family['description']}")
    else:
        lines.append("未匹配到已知恶意软件家族。")
    lines.append("")

    # IoC清单
    lines.append("## IoC 清单")
    lines.append("")
    iocs = data.get("iocs", {})
    if iocs.get("domains"):
        lines.append("### 域名")
        for domain in iocs["domains"]:
            lines.append(f"- {domain}")
        lines.append("")

    if iocs.get("ips"):
        lines.append("### IP地址")
        for ip in iocs["ips"]:
            lines.append(f"- {ip}")
        lines.append("")

    # 结论与建议
    lines.append("## 结论与建议")
    lines.append("")

    if risk_level in ["critical", "high"]:
        lines.append("### 处理建议")
        lines.append("")
        lines.append("1. **立即隔离**: 将该应用移至隔离环境进行进一步分析")
        lines.append("2. **撤销权限**: 撤销应用已获得的所有敏感权限")
        lines.append("3. **数据检查**: 检查是否有数据泄露")
        lines.append("4. **上报**: 向相关安全机构上报该恶意软件")
    elif risk_level == "medium":
        lines.append("### 处理建议")
        lines.append("")
        lines.append("1. **权限审查**: 仔细审查应用权限申请")
        lines.append("2. **监控使用**: 监控应用的网络和数据访问行为")
        lines.append("3. **用户告知**: 向用户说明潜在风险")
    else:
        lines.append("### 处理建议")
        lines.append("")
        lines.append("1. **定期复查**: 定期重新评估应用安全性")
        lines.append("2. **关注更新**: 关注应用更新日志")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*本报告由 HarmonyOS Malware Analysis Agent 自动生成*")
    lines.append(f"*生成时间: {datetime.now().isoformat()}*")

    return "\n".join(lines)


def _generate_html_report(
    report_id: str,
    app_name: str,
    package_name: str,
    data: dict,
    risk_score: int,
    risk_level: str,
    template: str,
) -> str:
    """生成HTML格式报告"""
    risk_colors = {
        "critical": "#dc3545",
        "high": "#fd7e14",
        "medium": "#ffc107",
        "low": "#28a745",
    }
    color = risk_colors.get(risk_level, "#6c757d")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{app_name} 分析报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid {color}; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; border-left: 4px solid {color}; padding-left: 10px; }}
        .meta {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .risk-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; background: {color}; font-weight: bold; }}
        .section {{ margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        .ioc {{ background: #fff3cd; padding: 10px; border-radius: 5px; font-family: monospace; }}
        .footer {{ text-align: center; margin-top: 40px; color: #888; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{app_name} 安全分析报告</h1>

        <div class="meta">
            <p><strong>报告ID:</strong> {report_id}</p>
            <p><strong>包名:</strong> {package_name}</p>
            <p><strong>生成时间:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><strong>风险评分:</strong> {risk_score}/100 <span class="risk-badge">{risk_level.upper()}</span></p>
        </div>

        <h2>执行摘要</h2>
        <div class="section">
            <p>对 <strong>{app_name}</strong> ({package_name}) 进行了全面的安全分析。</p>
"""

    if risk_level == "critical":
        html += f'            <p style="color: {color}; font-weight: bold;">检测结果：该应用存在严重安全风险，疑似恶意软件。</p>'
    elif risk_level == "high":
        html += f'            <p style="color: {color}; font-weight: bold;">检测结果：该应用存在高危行为，建议谨慎使用。</p>'
    else:
        html += f"            <p>检测结果：该应用风险等级为 {risk_level}。</p>"

    html += """
        </div>

        <h2>权限分析</h2>
        <div class="section">
"""

    permissions = data.get("permissions", {})
    if permissions.get("high_risk"):
        html += "            <h3>高风险权限</h3>\n            <ul>\n"
        for perm in permissions["high_risk"]:
            html += f"                <li><code>{perm}</code></li>\n"
        html += "            </ul>\n"

    html += """
        </div>

        <h2>网络行为</h2>
        <div class="section">
"""

    network = data.get("network", {})
    html += f"            <p>可疑连接: {'是' if network.get('suspicious_connections') else '否'}</p>\n"

    if network.get("domains"):
        html += "            <h3>发现的域名</h3>\n            <ul>\n"
        for domain in network["domains"]:
            html += f"                <li class='ioc'>{domain}</li>\n"
        html += "            </ul>\n"

    html += """
        </div>

        <h2>家族识别</h2>
        <div class="section">
"""

    family = data.get("family", {})
    if family.get("matched"):
        html += f"            <p><strong>匹配家族:</strong> {family.get('family_name', 'Unknown')}</p>\n"
        html += f"            <p><strong>置信度:</strong> {family.get('confidence', 0)}%</p>\n"
    else:
        html += "            <p>未匹配到已知恶意软件家族。</p>\n"

    html += """
        </div>

        <div class="footer">
            <p>本报告由 HarmonyOS Malware Analysis Agent 自动生成</p>
        </div>
    </div>
</body>
</html>"""

    return html


async def _list_templates(args: dict) -> list[TextContent]:
    """列出模板"""
    templates = []
    for key, template in _templates.items():
        templates.append(
            {
                "id": key,
                "name": template["name"],
                "description": template["description"],
                "sections": template["sections"],
            }
        )

    return [
        TextContent(
            type="text", text=json.dumps(templates, ensure_ascii=False, indent=2)
        )
    ]


async def _get_report(args: dict) -> list[TextContent]:
    """获取报告"""
    report_id = args["report_id"]

    # 尝试查找报告文件
    for ext in [".md", ".json", ".html"]:
        file_path = os.path.join(get_reports_dir(), f"{report_id}{ext}")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return [TextContent(type="text", text=content)]

    # 尝试按文件名查找
    for filename in os.listdir(get_reports_dir()):
        if report_id in filename:
            file_path = os.path.join(get_reports_dir(), filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return [TextContent(type="text", text=content)]

    return [
        TextContent(
            type="text",
            text=json.dumps(
                {"error": f"Report {report_id} not found"}, ensure_ascii=False
            ),
        )
    ]


async def _list_reports(args: dict) -> list[TextContent]:
    """列出报告"""
    limit = args.get("limit", 20)
    app_name = args.get("app_name")

    reports = []

    for filename in os.listdir(get_reports_dir()):
        if app_name and app_name not in filename:
            continue

        file_path = os.path.join(get_reports_dir(), filename)
        stat = os.stat(file_path)

        reports.append(
            {
                "filename": filename,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )

    reports.sort(key=lambda x: x["modified"], reverse=True)

    return [
        TextContent(
            type="text", text=json.dumps(reports[:limit], ensure_ascii=False, indent=2)
        )
    ]


async def _export_iocs(args: dict) -> list[TextContent]:
    """导出IoC"""
    data = args["analysis_data"]
    format_type = args.get("format", "json")

    iocs = data.get("iocs", {})
    family = data.get("family", {})

    if format_type == "json":
        output = json.dumps(iocs, ensure_ascii=False, indent=2)
    elif format_type == "csv":
        lines = ["type,value,description"]
        for domain in iocs.get("domains", []):
            lines.append(f"domain,{domain},")
        for ip in iocs.get("ips", []):
            lines.append(f"ip,{ip},")
        output = "\n".join(lines)
    elif format_type == "stix":
        output = json.dumps(
            {
                "type": "bundle",
                "id": "bundle--" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "objects": [
                    {
                        "type": "indicator",
                        "pattern": f"[domain-name:value = '{d}']"
                        if iocs.get("domains")
                        else "",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    else:  # txt
        lines = ["# IoC Export"]
        lines.append(f"# Generated: {datetime.now().isoformat()}")
        lines.append(f"# Family: {family.get('family_name', 'Unknown')}")
        lines.append("")
        lines.append("# Domains")
        for domain in iocs.get("domains", []):
            lines.append(domain)
        lines.append("")
        lines.append("# IPs")
        for ip in iocs.get("ips", []):
            lines.append(ip)
        output = "\n".join(lines)

    return [TextContent(type="text", text=output)]


async def main():
    """启动 report-generator MCP Server"""
    load_templates()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
