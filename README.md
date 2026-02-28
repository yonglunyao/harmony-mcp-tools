# HarmonyOS MCP 工具集

> 用于 HarmonyOS 开发与分析的 Model Context Protocol (MCP) 服务器集合

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)

## 简介

本仓库包含一系列 MCP (Model Context Protocol) 服务器，旨在增强 Claude Code 在 HarmonyOS 开发、安全分析和工作流自动化方面的能力。

## MCP 服务器

| 服务器 | 描述 | 工具 |
|--------|-------------|-------|
| **[arkts-api-validator](arkts-api-validator/)** | 校验 HarmonyOS ArkTS API 是否存在于 SDK 中 | API 校验、搜索、模块列表 |
| **[ark-disasm-mcp](ark-disasm-mcp/)** | 将 ABC 字节码反汇编为 PA 汇编格式 | ABC 反汇编、文件检查 |
| **[es2abc-mcp](es2abc-mcp/)** | 将 JavaScript 编译为 ABC 字节码 | JS 编译、文件编译 |
| **[harmony-build-mcp](harmony-build-mcp/)** | 构建 HarmonyOS 项目 (HAP/HAR/HSP) | 构建、清理、项目信息 |
| **[harmony-tasklist-manager](harmony_tasklist_manager/)** | 管理安全分析任务列表 | 查询、搜索、过滤任务 |

## 支持模块

| 模块 | 描述 |
|--------|-------------|
| `analysis_tool` | 安全分析工具 |
| `data_source` | 数据源连接器 |
| `knowledge_manager` | 知识库管理 (v1) |
| `knowledge_manager_v2` | 知识库管理 (v2) |
| `report_generator` | 自动化报告生成 |
| `threat_intel` | 威胁情报集成 |
| `vector_search` | 向量搜索能力 |

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yonglunyao/harmony-mcp-tools.git
cd harmony-mcp-tools
```

### 2. 配置 Claude Desktop

编辑 Claude Desktop 配置文件：

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 3. 添加 MCP 服务器

```json
{
  "mcpServers": {
    "arkts-api-validator": {
      "command": "python",
      "args": ["-m", "arkts_api_validator"],
      "cwd": "{PROJECT_PATH}/arkts-api-validator",
      "env": {
        "PYTHONPATH": "{PROJECT_PATH}/arkts-api-validator/src",
        "HARMONYOS_SDK_PATH": "{DEV_ECO_SDK_PATH}"
      }
    },
    "ark_disasm": {
      "command": "python",
      "args": ["{PROJECT_PATH}/ark-disasm-mcp/ark_disasm_mcp.py"]
    },
    "es2abc": {
      "command": "python",
      "args": ["{PROJECT_PATH}/es2abc-mcp/es2abc_mcp.py"]
    },
    "harmony-build": {
      "command": "python",
      "args": ["{PROJECT_PATH}/harmony-build-mcp/harmony_build_mcp.py"]
    },
    "harmony-tasklist": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "{PROJECT_PATH}/harmony-tasklist-manager"
    }
  }
}
```

> **配置说明**:
> - `{PROJECT_PATH}`: 替换为本仓库的实际路径
> - `{DEV_ECO_SDK_PATH}`: 替换为 DevEco Studio SDK 路径（通常为 `C:\Program Files\Huawei\DevEco Studio\sdk\default`）

### 4. 重启 Claude Desktop

配置完成后，重启 Claude Desktop 以加载 MCP 服务器。

## 工作流示例

### ArkTS 代码校验

```
User: 检查 @ohos.multimedia.image.ImageSource 是否存在于 SDK 中
```

### 字节码分析

```
User: 将以下 JavaScript 编译为 ABC 并反汇编：
function calculate(a, b) { return a + b; }
```

### HarmonyOS 构建

```
User: 用 release 模式构建我的 HarmonyOS 项目
```

### 任务管理

```
User: 查找所有 risk_tags 包含 "机检恶意" 的任务
```

## 项目结构

```
harmony-mcp-tools/
├── ark-disasm-mcp/              # ABC 字节码反汇编器
├── arkts-api-validator/         # ArkTS API 校验器
├── es2abc-mcp/                  # JavaScript 转 ABC 编译器
├── harmony-build-mcp/           # HarmonyOS 构建工具
├── harmony_tasklist_manager/    # 任务列表管理器
├── analysis_tool/               # 分析工具
├── data_source/                 # 数据连接器
├── knowledge_manager/           # 知识库 (v1)
├── knowledge_manager_v2/        # 知识库 (v2)
├── report_generator/            # 报告生成器
├── threat_intel/                # 威胁情报
├── vector_search/               # 向量搜索
├── .gitignore
└── README.md
```

## 系统要求

- **Python**: 3.10 或更高版本
- **操作系统**: Windows、Linux 或 macOS
- **Claude Desktop**: 支持 MCP 的最新版本
- **DevEco Studio**: 用于访问 HarmonyOS SDK (arkts-api-validator)

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎贡献！请随时提交 Pull Request。

## 相关链接

- [MCP 协议规范](https://modelcontextprotocol.io)
- [HarmonyOS 开发者文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5)
- [Claude Code 文档](https://claude.ai/claude-code)
