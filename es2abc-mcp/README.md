# ES2ABC MCP Server

MCP (Model Context Protocol) server for compiling JavaScript source code to ABC bytecode using the es2abc compiler. Supports Windows, Linux, and macOS platforms.

## Python Version Compatibility

**Two implementations available:**

| File | Python Support | Notes |
|------|---------------|-------|
| `es2abc_mcp.py` | Python 3.10+ | FastMCP implementation |
| `es2abc_mcp_compat.py` | Python 3.8+ | **Recommended for older Python** |

**Use `es2abc_mcp_compat.py` if you encounter `SyntaxError` with `match` keyword.**

## Overview

**es2abc-mcp** provides tools to compile JavaScript code to ABC bytecode format. ABC (方舟字节码) is a compact bytecode representation used for efficient execution.

### Available Tools

| Tool | Description |
|------|-------------|
| `es2abc_compile` | Compile JavaScript source code string to ABC bytecode |
| `es2abc_compile_file` | Compile a JavaScript file to ABC bytecode |
| `es2abc_get_status` | Get the status and configuration of the es2abc compiler |

---

## Installation

### Prerequisites

- Python 3.10 or higher
- The es2abc binary (included in `bin/`)

### Directory Structure

```
es2abc-mcp/
├── bin/
│   ├── es2abc.exe       # Windows binary
│   └── es2abc           # Linux/macOS binary
├── es2abc_mcp.py        # MCP server
├── pyproject.toml
├── requirements.txt
└── README.md
```

### Environment Variable (Optional)

- `ES2ABC_PATH`: Path to custom es2abc executable (if not using bundled binary)

### Claude Desktop Configuration

Replace `{PATH_TO_MCP_SERVERS}` with your actual path.

**Windows** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "es2abc": {
      "command": "python",
      "args": ["{PATH_TO_MCP_SERVERS}\\es2abc-mcp\\es2abc_mcp.py"]
    }
  }
}
```

**Linux/macOS** (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "es2abc": {
      "command": "python3",
      "args": ["{PATH_TO_MCP_SERVERS}/es2abc-mcp/es2abc_mcp.py"]
    }
  }
}
```

---

# API Reference

## Tool: `es2abc_compile`

Compile JavaScript source code string to ABC bytecode.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `js_code` | string | Yes | - | JavaScript source code to compile (max 10MB) |
| `output_format` | string | No | `markdown` | Response format: `markdown` or `json` |
| `return_binary` | boolean | No | `false` | If true, return base64-encoded ABC binary |

### Returns (Markdown format)
```markdown
# ES2ABC Compilation Result

## Metadata
- **Input Size**: 123 bytes
- **Output Size**: 456 bytes
- **Compression Ratio**: 3.71x
- **Compiler**: es2abc
- **Platform**: Windows
```

### Returns (JSON format)
```json
{
  "success": true,
  "input_size": 123,
  "output_size": 456,
  "compression_ratio": 3.71,
  "compiler": "es2abc",
  "platform": "Windows",
  "base64_data": "ABC...xyz"
}
```

### Example
```
User: Compile this JavaScript to ABC:
function hello() { return "world"; }
```

---

## Tool: `es2abc_compile_file`

Compile a JavaScript file to ABC bytecode.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | string | Yes | - | Absolute path to .js file |
| `output_format` | string | No | `markdown` | Response format: `markdown` or `json` |
| `return_binary` | boolean | No | `false` | If true, return base64-encoded ABC binary |

### Returns

Same as `es2abc_compile`, plus `source_file` field.

### Example
```
User: Compile the file at /home/user/app.js to ABC
```

---

## Tool: `es2abc_get_status`

Get the status and configuration of the es2abc compiler.

### Parameters
None

### Returns (JSON)
```json
{
  "available": true,
  "executable_path": "{server_path}/bin/es2abc",
  "platform": "Windows",
  "architecture": "AMD64",
  "version": "unknown",
  "max_file_size": 10485760,
  "temp_directory": "{temp_dir}"
}
```

---

# Usage Examples

## Compile JavaScript Code

```
User: Compile this JavaScript to ABC bytecode:
function calculateSum(a, b) {
    return a + b;
}
```

## Compile with Binary Output

```
User: Compile this JS and return the ABC binary data:
const x = 42;
```

Use `return_binary=true` to get base64-encoded ABC bytecode for further processing (e.g., disassembly).

## Compile File

```
User: Compile the file main.js to ABC
```

---

# Platform Support

| Platform | Binary Extension | Path Example |
|----------|-----------------|--------------|
| Windows | `.exe` | `C:\project\file.js` |
| Linux | (none) | `/home/user/project/file.js` |
| macOS | (none) | `/Users/user/project/file.js` |

---

# Limitations

| Limit | Value |
|-------|-------|
| Maximum file size | 10 MB |
| Maximum input code size | 10 MB |

---

# Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `es2abc executable not found` | Binary not in bin/ | Check binary location or set ES2ABC_PATH |
| `File not found` | Invalid file path | Verify the file exists |
| `File must have .js extension` | Wrong file type | Use .js file |
| `File exceeds maximum size` | File too large | File must be under 10 MB |
| `JavaScript code cannot be empty` | Empty input | Provide non-empty JavaScript code |

---

# Development

Run the server directly for testing:

```bash
cd es2abc-mcp
python es2abc_mcp.py
```

## License

MIT
