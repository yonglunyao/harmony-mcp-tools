# Ark Disasm MCP Server

MCP (Model Context Protocol) server for **disassembling** ABC bytecode files to PA (方舟汇编 / Ark Assembly) text format using the ark_disasm tool. Supports Windows, Linux, and macOS platforms.

## Overview

**ark-disasm-mcp** provides tools to **disassemble** (反汇编) ABC bytecode files to PA text format. PA (方舟字节码汇编格式) is the human-readable assembly representation of ArkTS/ArkCompiler bytecode.

### Python Version Compatibility

**Two implementations available:**

| File | Python Support | Notes |
|------|---------------|-------|
| `ark_disasm_mcp.py` | Python 3.10+ | FastMCP implementation |
| `ark_disasm_mcp_compat.py` | Python 3.8+ | **Recommended for older Python** |

**Use `ark_disasm_mcp_compat.py` if you encounter `SyntaxError` with `match` keyword.**

### What is Disassembly?

- **Disassembly (反汇编)**: Converts bytecode to assembly-like text format
- **ABC**: Ark Bytecode - Compiled ArkTS/JavaScript bytecode
- **PA**: 方舟汇编 - Human-readable Ark assembly format

This is **NOT** decompilation (which would recover high-level source code). Disassembly shows the bytecode instructions in a readable text format.

### Available Tools

| Tool | Description |
|------|-------------|
| `ark_disasm_disassemble` | Disassemble base64-encoded ABC bytecode to PA (方舟汇编) text |
| `ark_disasm_disassemble_file` | Disassemble an ABC file to PA (方舟汇编) text |
| `ark_disasm_get_status` | Get the status and configuration of the ark_disasm tool |

### Terminology

| Term | Chinese | Description |
|------|---------|-------------|
| **ABC** | 方舟字节码 | Ark Bytecode - Compiled ArkTS/JavaScript bytecode |
| **PA** | 方舟汇编 | Ark Assembly - Human-readable assembly format |
| **Disassemble** | 反汇编 | Convert bytecode to assembly text |
| **es2abc** | - | Compile JavaScript/ArkTS to ABC |
| **ark_disasm** | - | Disassemble ABC to PA |

---

## Installation

### Prerequisites

- Python 3.10 or higher
- The ark_disasm binary (included in `bin/`)

### Directory Structure

```
ark-disasm-mcp/
├── bin/
│   ├── ark_disasm.exe   # Windows binary
│   └── ark_disasm       # Linux/macOS binary
├── ark_disasm_mcp.py    # MCP server
├── pyproject.toml
├── requirements.txt
└── README.md
```

### Environment Variable (Optional)

- `ARK_DISASM_PATH`: Path to custom ark_disasm executable (if not using bundled binary)

### Claude Desktop Configuration

Replace `{PATH_TO_MCP_SERVERS}` with your actual path.

**Windows** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "ark_disasm": {
      "command": "python",
      "args": ["{PATH_TO_MCP_SERVERS}\\ark-disasm-mcp\\ark_disasm_mcp.py"]
    }
  }
}
```

**Linux/macOS** (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "ark_disasm": {
      "command": "python3",
      "args": ["{PATH_TO_MCP_SERVERS}/ark-disasm-mcp/ark_disasm_mcp.py"]
    }
  }
}
```

---

# API Reference

## Tool: `ark_disasm_disassemble`

**Disassemble** (反汇编) base64-encoded ABC bytecode to PA (方舟汇编) text format.

This tool converts Ark bytecode (ABC) to its human-readable assembly representation (PA), not back to the original source code.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `abc_bytes_b64` | string | Yes | - | Base64-encoded ABC bytecode |
| `output_format` | string | No | `markdown` | Response format: `markdown` or `json` |
| `truncation_mode` | string | No | `truncate` | How to handle large output: `full`, `truncate`, `head`, `tail` |
| `lines` | integer | No | `100` | Number of lines for head/tail mode (1-10000) |

### Truncation Modes

| Mode | Description |
|------|-------------|
| `full` | Return complete output (may be very large) |
| `truncate` | Truncate to 25,000 characters at natural break point (default) |
| `head` | Return first N lines (controlled by `lines` parameter) |
| `tail` | Return last N lines (controlled by `lines` parameter) |

### Returns (Markdown format)
```markdown
# Ark Disasm Result

## Metadata
- **Input Size**: 456 bytes
- **Output Length**: 12,345 characters
- **Output Lines**: 234
- **Disassembler**: ark_disasm
- **Platform**: Windows

## PA Output (方舟汇编)
```pa
.record ArkJSAsyncFunctionModuleInfo ...
...
```

### Returns (JSON format)
```json
{
  "success": true,
  "metadata": {
    "input_size": 456,
    "output_length": 12345,
    "output_lines": 234,
    "disassembler": "ark_disasm",
    "platform": "Windows"
  },
  "pa_content": ".record ArkJSAsyncFunctionModuleInfo ...",
  "truncated": false
}
```

### Example
```
User: Disassemble this ABC bytecode: [base64 from es2abc compilation]
```

---

## Tool: `ark_disasm_disassemble_file`

**Disassemble** (反汇编) an ABC file to PA (方舟汇编) text format.

Reads an ABC bytecode file and outputs its assembly representation in PA format.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | string | Yes | - | Absolute path to .abc file |
| `output_format` | string | No | `markdown` | Response format: `markdown` or `json` |
| `truncation_mode` | string | No | `truncate` | How to handle large output |
| `lines` | integer | No | `100` | Number of lines for head/tail mode |

### Returns

Same as `ark_disasm_disassemble`, plus `source_file` field.

### Example
```
User: Show me the PA assembly of main.abc
```

---

## Tool: `ark_disasm_get_status`

Get the status and configuration of the ark_disasm tool.

### Parameters
None

### Returns (JSON)
```json
{
  "available": true,
  "executable_path": "{server_path}/bin/ark_disasm",
  "platform": "Windows",
  "architecture": "AMD64",
  "max_file_size": 10485760,
  "character_limit": 25000,
  "temp_directory": "{temp_dir}"
}
```

---

# Usage Examples

## Complete Workflow: Compile → Disassemble

```
User: I want to see the PA assembly of this JavaScript:
function calculate(a, b) { return a + b; }
```

The workflow is:
1. **Compile**: Use `es2abc_compile` (es2abc-mcp) to compile JavaScript → ABC bytecode
2. **Disassemble**: Use `ark_disasm_disassemble` (ark-disasm-mcp) to disassemble ABC → PA text

```
JavaScript (Source)
    ↓ es2abc_compile
ABC (Ark Bytecode)
    ↓ ark_disasm_disassemble
PA (方舟汇编 / Ark Assembly)
```

**Note**: This is **disassembly** (bytecode → assembly), NOT **decompilation** (bytecode → source code).

## Disassemble ABC Bytecode

```
User: Disassemble this ABC bytecode I got from es2abc
```

Use the base64-encoded ABC bytecode from `es2abc_compile` with `return_binary=true`.

```
User: Show me the first 50 lines of the ABC disassembly
```

Use `truncation_mode="head"` and `lines=50`.

```
User: Show me the last 100 lines of the ABC disassembly
```

Use `truncation_mode="tail"` and `lines=100`.

## Inspect ABC File

```
User: What's in this ABC file output.abc?
```

Use `ark_disasm_disassemble_file` to disassemble directly from file.

---

# Platform Support

| Platform | Binary Extension | Path Example |
|----------|-----------------|--------------|
| Windows | `.exe` | `C:\project\file.abc` |
| Linux | (none) | `/home/user/project/file.abc` |
| macOS | (none) | `/Users/user/project/file.abc` |

---

# Limitations

| Limit | Value |
|-------|-------|
| Maximum file size | 10 MB |
| PA output character limit | 25,000 (configurable via truncation_mode) |
| Max lines for head/tail | 10,000 |

---

# Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `ark_disasm executable not found` | Binary not in bin/ | Check binary location or set ARK_DISASM_PATH |
| `File not found` | Invalid file path | Verify the file exists |
| `File must have .abc extension` | Wrong file type | Use .abc file |
| `File exceeds maximum size` | File too large | File must be under 10 MB |
| `Invalid base64 encoding` | Corrupted base64 data | Check the base64 string |
| `ABC bytecode too small to be valid` | Input too small | Provide valid ABC bytecode |

---

# Development

Run the server directly for testing:

```bash
cd ark-disasm-mcp
python ark_disasm_mcp.py
```

## License

MIT
