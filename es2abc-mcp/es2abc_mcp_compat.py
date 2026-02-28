#!/usr/bin/env python3
"""
ES2ABC MCP Server - Compatible implementation.

This server provides tools to compile JavaScript to ABC bytecode using es2abc.
Compatible with older Python versions (3.8+).
"""

import asyncio
import base64
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

# Server info
SERVER_NAME = "es2abc_mcp"
SERVER_VERSION = "1.0.0"

# Constants
TEMP_DIR = tempfile.gettempdir()
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_executable_path():
    """Get the platform-specific es2abc executable path."""
    system = platform.system().lower()

    # Check environment variable
    env_path = os.environ.get("ES2ABC_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Check relative to script
    script_dir = Path(__file__).parent / "bin"
    if system == "windows":
        exe_path = script_dir / "es2abc.exe"
    else:
        exe_path = script_dir / "es2abc"

    if exe_path.exists():
        return str(exe_path)

    # Check PATH
    in_path = shutil.which("es2abc")
    if in_path:
        return in_path

    raise RuntimeError(f"es2abc executable not found. Expected at: {exe_path}")


async def compile_js_to_abc(js_code, source_name="input.js"):
    """Compile JavaScript to ABC bytecode."""
    exe_path = get_executable_path()

    # Create temp directory
    temp_dir = Path(TEMP_DIR) / f"es2abc_mcp_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    js_path = temp_dir / f"{uuid.uuid4().hex}.js"
    abc_path = temp_dir / f"{uuid.uuid4().hex}.abc"

    try:
        # Write JS file
        js_path.write_text(js_code, encoding='utf-8')

        # Build command
        cmd = [exe_path, "--module", str(js_path), "--output", str(abc_path)]

        # Execute
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=temp_dir
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode('utf-8', errors='replace') or stdout.decode('utf-8', errors='replace')
            raise RuntimeError(f"es2abc compilation failed:\n{error_output}")

        # Read result
        if not abc_path.exists():
            raise RuntimeError(f"Compilation completed but output file not created: {abc_path}")

        abc_bytes = abc_path.read_bytes()

        metadata = {
            "success": True,
            "input_size": len(js_code.encode('utf-8')),
            "output_size": len(abc_bytes),
            "compression_ratio": round(len(abc_bytes) / len(js_code.encode('utf-8')), 2) if js_code else 0,
            "compiler": "es2abc",
            "platform": platform.system()
        }

        return abc_bytes, metadata

    finally:
        # Cleanup
        for p in [js_path, abc_path, temp_dir]:
            try:
                if p.exists():
                    if p.is_dir():
                        p.rmdir()
                    else:
                        p.unlink()
            except:
                pass


# Tool handlers
async def handle_es2abc_compile(params):
    """Handle es2abc_compile tool call."""
    js_code = params.get("js_code", "")
    output_format = params.get("output_format", "markdown")
    return_binary = params.get("return_binary", False)

    # Validation
    if not js_code or not js_code.strip():
        return "Error: JavaScript code cannot be empty"

    if len(js_code.encode('utf-8')) > MAX_FILE_SIZE:
        return f"Error: JavaScript code exceeds maximum size of {MAX_FILE_SIZE} bytes"

    try:
        abc_bytes, metadata = await compile_js_to_abc(js_code, "inline.js")

        if return_binary:
            metadata["base64_data"] = base64.b64encode(abc_bytes).decode('ascii')

        if output_format == "json":
            return json.dumps(metadata, indent=2)

        # Markdown format
        lines = [
            "# ES2ABC Compilation Result",
            "",
            "## Metadata",
            f"- **Input Size**: {metadata['input_size']:,} bytes",
            f"- **Output Size**: {metadata['output_size']:,} bytes",
            f"- **Compression Ratio**: {metadata['compression_ratio']:.2f}x",
            f"- **Compiler**: {metadata['compiler']}",
            f"- **Platform**: {metadata['platform']}",
        ]

        if return_binary:
            lines.extend([
                "",
                "## Binary Data",
                f"```\n{metadata['base64_data'][:100]}...\n```",
                f"*(Base64 encoded, {metadata['output_size']} bytes total)*"
            ])
        else:
            lines.extend([
                "",
                "## Output",
                f"ABC bytecode generated successfully ({metadata['output_size']:,} bytes).",
                "Use `return_binary=true` to get the base64-encoded binary data."
            ])

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {str(e)}"


async def handle_es2abc_compile_file(params):
    """Handle es2abc_compile_file tool call."""
    file_path = params.get("file_path", "")
    output_format = params.get("output_format", "markdown")
    return_binary = params.get("return_binary", False)

    # Validation
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    if not path.is_file():
        return f"Error: Path is not a file: {file_path}"

    if not path.suffix.lower() == '.js':
        return f"Error: File must have .js extension: {file_path}"

    if path.stat().st_size > MAX_FILE_SIZE:
        return f"Error: File exceeds maximum size of {MAX_FILE_SIZE} bytes"

    try:
        js_code = path.read_text(encoding='utf-8')
        abc_bytes, metadata = await compile_js_to_abc(js_code, path.name)
        metadata["source_file"] = str(path.resolve())

        if return_binary:
            metadata["base64_data"] = base64.b64encode(abc_bytes).decode('ascii')

        if output_format == "json":
            return json.dumps(metadata, indent=2)

        # Markdown format
        lines = [
            "# ES2ABC Compilation Result",
            "",
            "## Metadata",
            f"- **Source File**: {metadata['source_file']}",
            f"- **Input Size**: {metadata['input_size']:,} bytes",
            f"- **Output Size**: {metadata['output_size']:,} bytes",
            f"- **Compression Ratio**: {metadata['compression_ratio']:.2f}x",
            f"- **Compiler**: {metadata['compiler']}",
            f"- **Platform**: {metadata['platform']}",
        ]

        if return_binary:
            lines.extend([
                "",
                "## Binary Data",
                f"```\n{metadata['base64_data'][:100]}...\n```",
                f"*(Base64 encoded, {metadata['output_size']} bytes total)*"
            ])

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {str(e)}"


async def handle_es2abc_get_status(params):
    """Handle es2abc_get_status tool call."""
    try:
        exe_path = get_executable_path()

        status = {
            "available": True,
            "executable_path": exe_path,
            "platform": platform.system(),
            "architecture": platform.machine(),
            "max_file_size": MAX_FILE_SIZE,
            "temp_directory": TEMP_DIR
        }

        return json.dumps(status, indent=2)

    except RuntimeError as e:
        status = {
            "available": False,
            "error": str(e),
            "platform": platform.system(),
            "architecture": platform.machine(),
            "suggestion": "Set ES2ABC_PATH environment variable to the es2abc executable"
        }
        return json.dumps(status, indent=2)


# Main MCP protocol handler
class MCPServer:
    """Simple MCP server implementation for older Python versions."""

    def __init__(self):
        self.tools = {
            "es2abc_compile": {
                "name": "es2abc_compile",
                "description": "Compile JavaScript source code to ABC bytecode using es2abc.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "js_code": {
                            "type": "string",
                            "description": "JavaScript source code to compile (max 10MB)"
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Response format: 'markdown' or 'json'"
                        },
                        "return_binary": {
                            "type": "boolean",
                            "description": "If true, return base64-encoded ABC binary"
                        }
                    },
                    "required": ["js_code"]
                }
            },
            "es2abc_compile_file": {
                "name": "es2abc_compile_file",
                "description": "Compile a JavaScript file to ABC bytecode.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to the JavaScript file"
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Response format"
                        },
                        "return_binary": {
                            "type": "boolean",
                            "description": "If true, return base64-encoded ABC binary"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            "es2abc_get_status": {
                "name": "es2abc_get_status",
                "description": "Get the status and configuration of the es2abc compiler.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        }

        self.handlers = {
            "es2abc_compile": handle_es2abc_compile,
            "es2abc_compile_file": handle_es2abc_compile_file,
            "es2abc_get_status": handle_es2abc_get_status
        }

    async def handle_request(self, request):
        """Handle an MCP request."""
        method = request.get("method")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": list(self.tools.values())
                }
            }

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name in self.handlers:
                try:
                    result = await self.handlers[tool_name](arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result
                                }
                            ]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32000,
                            "message": str(e)
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

    async def run(self):
        """Run the MCP server using stdio."""
        print(f"Starting {SERVER_NAME} v{SERVER_VERSION}", file=sys.stderr)

        while True:
            try:
                # Read request from stdin
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line)

                # Handle request
                response = await self.handle_request(request)

                # Write response to stdout
                print(json.dumps(response))
                sys.stdout.flush()

            except json.JSONDecodeError:
                print(f"Error: Invalid JSON", file=sys.stderr)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    server = MCPServer()
    asyncio.run(server.run())
