# HarmonyOS MCP Tools

> A collection of Model Context Protocol (MCP) servers for HarmonyOS development and analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)

## Overview

This repository contains a suite of MCP (Model Context Protocol) servers designed to enhance Claude Code's capabilities for HarmonyOS development, security analysis, and workflow automation.

## Available MCP Servers

| Server | Description | Tools |
|--------|-------------|-------|
| **[arkts-api-validator](arkts-api-validator/)** | Validates HarmonyOS ArkTS APIs against SDK | API validation, search, module listing |
| **[ark-disasm-mcp](ark-disasm-mcp/)** | Disassembles ABC bytecode to PA assembly | ABC disassembly, file inspection |
| **[es2abc-mcp](es2abc-mcp/)** | Compiles JavaScript to ABC bytecode | JS compilation, file compilation |
| **[harmony-build-mcp](harmony-build-mcp/)** | Builds HarmonyOS projects (HAP/HAR/HSP) | Build, clean, project info |
| **[harmony-tasklist-manager](harmony_tasklist_manager/)** | Manages security analysis task lists | Query, search, filter tasks |

## Supporting Modules

| Module | Description |
|--------|-------------|
| `analysis_tool` | Security analysis utilities |
| `data_source` | Data source connectors |
| `knowledge_manager` | Knowledge base management (v1) |
| `knowledge_manager_v2` | Knowledge base management (v2) |
| `report_generator` | Automated report generation |
| `threat_intel` | Threat intelligence integration |
| `vector_search` | Vector-based search capabilities |

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yonglunyao/harmony-mcp-tools.git
cd harmony-mcp-tools
```

### 2. Configure Claude Desktop

Edit your Claude Desktop configuration file:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 3. Add MCP Servers

```json
{
  "mcpServers": {
    "arkts-api-validator": {
      "command": "python",
      "args": ["-m", "arkts_api_validator"],
      "cwd": "D:\\mcp-servers\\arkts-api-validator",
      "env": {
        "PYTHONPATH": "D:\\mcp-servers\\arkts-api-validator\\src",
        "HARMONYOS_SDK_PATH": "C:\\Program Files\\Huawei\\DevEco Studio\\sdk\\default"
      }
    },
    "ark_disasm": {
      "command": "python",
      "args": ["D:\\mcp-servers\\ark-disasm-mcp\\ark_disasm_mcp.py"]
    },
    "es2abc": {
      "command": "python",
      "args": ["D:\\mcp-servers\\es2abc-mcp\\es2abc_mcp.py"]
    },
    "harmony-build": {
      "command": "python",
      "args": ["D:\\mcp-servers\\harmony-build-mcp\\harmony_build_mcp.py"]
    },
    "harmony-tasklist": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "D:\\mcp-servers\\harmony-tasklist-manager"
    }
  }
}
```

Replace `D:\\mcp-servers` with your actual path.

### 4. Restart Claude Desktop

After configuration, restart Claude Desktop to load the MCP servers.

## Workflow Examples

### ArkTS Code Validation

```
User: Check if @ohos.multimedia.image.ImageSource exists in the SDK
```

### Bytecode Analysis

```
User: Compile this JavaScript to ABC and disassemble it:
function calculate(a, b) { return a + b; }
```

### HarmonyOS Build

```
User: Build my HarmonyOS project in release mode
```

### Task Management

```
User: Find all tasks with risk_tags containing "机检恶意"
```

## Project Structure

```
harmony-mcp-tools/
├── ark-disasm-mcp/              # ABC bytecode disassembler
├── arkts-api-validator/         # ArkTS API validator
├── es2abc-mcp/                  # JavaScript to ABC compiler
├── harmony-build-mcp/           # HarmonyOS build tool
├── harmony_tasklist_manager/    # Task list manager
├── analysis_tool/               # Analysis utilities
├── data_source/                 # Data connectors
├── knowledge_manager/           # Knowledge base (v1)
├── knowledge_manager_v2/        # Knowledge base (v2)
├── report_generator/            # Report generator
├── threat_intel/                # Threat intelligence
├── vector_search/               # Vector search
├── .gitignore
└── README.md
```

## System Requirements

- **Python**: 3.10 or higher
- **OS**: Windows, Linux, or macOS
- **Claude Desktop**: Latest version with MCP support
- **DevEco Studio**: For HarmonyOS SDK access (arkts-api-validator)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Related Links

- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [HarmonyOS Developer Documentation](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5)
- [Claude Code Documentation](https://claude.ai/claude-code)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yonglunyao/harmony-mcp-tools&type=Date)](https://star-history.com/#yonglunyao/harmony-mcp-tools&Date)
