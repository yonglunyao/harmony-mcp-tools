# HarmonyOS Build MCP Server

MCP (Model Context Protocol) server for building HarmonyOS projects (HAP applications and HAR static libraries) using the hvigorw build system. Supports Windows, Linux, and macOS platforms.

## Overview

**harmony-build-mcp** provides tools to build HarmonyOS projects using the DevEco Studio build system (hvigorw). It supports building:

- **HAP** (HarmonyOS Ability Package) - Applications
- **HAR** (HarmonyOS Archive) - Static libraries
- **HSP** (HarmonyOS Shared Package) - Shared libraries

### Available Tools

| Tool | Description |
|------|-------------|
| `harmony_build` | Build a HarmonyOS project with configurable target and mode |
| `harmony_build_module` | Build a specific module within a project |
| `harmony_clean` | Clean build output from a project |
| `harmony_get_project_info` | Get information about project structure and modules |
| `harmony_build_get_status` | Get build environment status |

---

## Installation

### Prerequisites

- Python 3.10 or higher
- DevEco Studio installed (for hvigorw build system)
- A valid HarmonyOS project

### Environment Requirements

The HarmonyOS project must have:
- `hvigorw` or `hvigorw.bat` build script
- `build-profile.json5` configuration file
- Standard DevEco Studio project structure

### Directory Structure

```
harmony-build-mcp/
├── harmony_build_mcp.py  # MCP server
├── pyproject.toml
├── requirements.txt
└── README.md
```

### Claude Desktop Configuration

Replace `{PATH_TO_MCP_SERVERS}` with your actual path.

**Windows** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "harmony-build": {
      "command": "python",
      "args": ["{PATH_TO_MCP_SERVERS}\\harmony-build-mcp\\harmony_build_mcp.py"]
    }
  }
}
```

**Linux/macOS** (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "harmony-build": {
      "command": "python3",
      "args": ["{PATH_TO_MCP_SERVERS}/harmony-build-mcp/harmony_build_mcp.py"]
    }
  }
}
```

---

# API Reference

## Tool: `harmony_build`

Build a HarmonyOS project using hvigorw.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Path to the HarmonyOS project directory |
| `target` | string | No | `hap` | Build target: `hap`, `har`, or `hsp` |
| `mode` | string | No | `debug` | Build mode: `debug` or `release` |
| `module` | string | No | `null` | Specific module to build (e.g., 'entry') |
| `clean` | boolean | No | `false` | Clean build output before building |
| `output_format` | string | No | `markdown` | Response format: `markdown` or `json` |

### Returns (Markdown format)
```markdown
# HarmonyOS Build Result

## Summary
- **Status**: ✅ Success
- **Project**: `MyHarmonyApp`
- **Target**: HAP
- **Mode**: debug
- **Platform**: Windows
- **Duration**: 45.23s

## Output Artifacts
- `D:/project/entry/build/default/outputs/default/entry-default-signed.hap`

## Build Log
```
> Task :entry:compileDebugArkTS
> Task :entry:bundleDebug
BUILD SUCCESSFUL
```
```

### Returns (JSON format)
```json
{
  "success": true,
  "project_name": "MyHarmonyApp",
  "target": "hap",
  "mode": "debug",
  "output_paths": ["path/to/output.hap"],
  "build_log": "...",
  "duration": 45.23
}
```

### Example
```
User: Build my HarmonyOS project at D:/MyProject in release mode
```

---

## Tool: `harmony_build_module`

Build a specific module within a HarmonyOS project.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Path to the HarmonyOS project directory |
| `module_name` | string | Yes | - | Name of the module to build |
| `mode` | string | No | `debug` | Build mode: `debug` or `release` |
| `clean` | boolean | No | `false` | Clean before building |
| `output_format` | string | No | `markdown` | Response format |

### Example
```
User: Build the entry module in debug mode
```

---

## Tool: `harmony_clean`

Clean build output from a HarmonyOS project.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Path to the HarmonyOS project |
| `output_format` | string | No | `markdown` | Response format |

### Example
```
User: Clean the build output from my project
```

---

## Tool: `harmony_get_project_info`

Get information about a HarmonyOS project structure.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Path to the HarmonyOS project |
| `output_format` | string | No | `markdown` | Response format |

### Returns (Markdown format)
```markdown
# HarmonyOS Project Information

**Project Name**: MyHarmonyApp
**Project Root**: `D:/MyProject`
**Platform**: Windows
**Has AppScope**: Yes

## Modules
- `entry`
- `mylibrary`

## Build System
**hvigorw**: `D:/MyProject/hvigorw.bat`
```

### Example
```
User: What modules are in this project?
```

---

## Tool: `harmony_build_get_status`

Get the status of the HarmonyOS build environment.

### Parameters
None

### Returns (JSON)
```json
{
  "available": true,
  "platform": "Windows",
  "architecture": "AMD64",
  "python_version": "3.11.0",
  "supported_targets": ["hap", "har", "hsp"],
  "supported_modes": ["debug", "release"],
  "common_installation_paths_found": true
}
```

---

# Usage Examples

## Basic Build

```
User: Build my HarmonyOS project

[Agent calls harmony_build with project_path]
```

## Release Build

```
User: Build my project in release mode

[Agent calls harmony_build with mode="release"]
```

## Clean Build

```
User: Do a clean build of my HarmonyOS app

[Agent calls harmony_build with clean=true]
```

## Build Specific Module

```
User: Build only the entry module

[Agent calls harmony_build_module with module_name="entry"]
```

## Build HAR Library

```
User: Build this project as a HAR library

[Agent calls harmony_build with target="har"]
```

## Project Information

```
User: Tell me about this HarmonyOS project structure

[Agent calls harmony_get_project_info]
```

---

# Platform Support

| Platform | Build Script | Path Example |
|----------|-------------|--------------|
| Windows | `hvigorw.bat` | `D:\project\MyApp` |
| Linux | `hvigorw` | `/home/user/project/MyApp` |
| macOS | `hvigorw` | `/Users/user/project/MyApp` |

---

# HarmonyOS Project Structure

The MCP server expects a standard DevEco Studio project structure:

```
MyProject/
├── hvigorw              # Build script (Linux/macOS)
├── hvigorw.bat          # Build script (Windows)
├── build-profile.json5  # Build configuration
├── oh-package.json5     # Package configuration
├── AppScope/            # Application-level resources
├── entry/               # Default entry module
│   └── build/
│       └── default/
│           └── outputs/
│               └── default/
│                   └── entry-*.hap
└── [other modules]/
```

---

# Build Targets

| Target | Description | Output Extension |
|--------|-------------|------------------|
| `hap` | HarmonyOS Ability Package (Application) | `.hap` |
| `har` | HarmonyOS Archive (Static Library) | `.har` |
| `hsp` | HarmonyOS Shared Package (Shared Library) | `.hsp` |

---

# Build Modes

| Mode | Description |
|------|-------------|
| `debug` | Debug build with symbols and logging |
| `release` | Optimized release build |

---

# Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Project path does not exist` | Invalid path | Verify the project path is correct |
| `hvigorw executable not found` | Build script missing | Ensure DevEco Studio project structure |
| `Module not found` | Invalid module name | Check available modules with `harmony_get_project_info` |
| `Build failed with exit code` | Compilation error | Check build logs for details |

---

# Development

Run the server directly for testing:

```bash
cd harmony-build-mcp
python harmony_build_mcp.py
```

## Requirements

- mcp >= 1.0.0
- pydantic >= 2.0.0

## License

MIT
