#!/usr/bin/env python3
"""
Ark Disasm MCP Server - Compatible implementation.

This server provides tools to disassemble ABC bytecode to PA (方舟汇编) format.
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
SERVER_NAME = "ark_disasm_mcp"
SERVER_VERSION = "1.0.0"

# Constants
TEMP_DIR = tempfile.gettempdir()
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
CHARACTER_LIMIT = 25000


def get_executable_path():
    """Get the platform-specific ark_disasm executable path."""
    system = platform.system().lower()

    # Check environment variable
    env_path = os.environ.get("ARK_DISASM_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Check relative to script
    script_dir = Path(__file__).parent / "bin"
    if system == "windows":
        exe_path = script_dir / "ark_disasm.exe"
    else:
        exe_path = script_dir / "ark_disasm"

    if exe_path.exists():
        return str(exe_path)

    # Check PATH
    in_path = shutil.which("ark_disasm")
    if in_path:
        return in_path

    raise RuntimeError(f"ark_disasm executable not found. Expected at: {exe_path}")


def truncate_pa_content(pa_text, mode, lines=None):
    """Truncate PA content based on mode."""
    pa_lines = pa_text.split('\n')
    total_lines = len(pa_lines)
    total_chars = len(pa_text)

    if mode == "full":
        return pa_text, {
            "truncated": False,
            "total_lines": total_lines,
            "total_chars": total_chars
        }

    if mode == "truncate":
        if len(pa_text) <= CHARACTER_LIMIT:
            return pa_text, {
                "truncated": False,
                "total_lines": total_lines,
                "total_chars": total_chars
            }

        # Find truncation point at natural break
        truncation_point = CHARACTER_LIMIT
        for i in range(CHARACTER_LIMIT, max(0, CHARACTER_LIMIT - 1000), -1):
            if i < len(pa_text) and pa_text[i] in '\n;{}':
                truncation_point = i + 1
                break

        truncated = pa_text[:truncation_point]
        return truncated, {
            "truncated": True,
            "total_lines": total_lines,
            "total_chars": total_chars,
            "returned_chars": len(truncated),
            "truncation_mode": "character_limit"
        }

    if mode == "head":
        n = lines or 100
        truncated = '\n'.join(pa_lines[:n])
        return truncated, {
            "truncated": total_lines > n,
            "total_lines": total_lines,
            "returned_lines": min(n, total_lines),
            "total_chars": total_chars,
            "truncation_mode": "head"
        }

    if mode == "tail":
        n = lines or 100
        truncated = '\n'.join(pa_lines[-n:])
        return truncated, {
            "truncated": total_lines > n,
            "total_lines": total_lines,
            "returned_lines": min(n, total_lines),
            "total_chars": total_chars,
            "truncation_mode": "tail"
        }

    return pa_text, {"truncated": False}


async def disassemble_abc_to_pa(abc_bytes):
    """Disassemble ABC bytecode to PA text format."""
    exe_path = get_executable_path()

    # Create temp directory
    temp_dir = Path(TEMP_DIR) / f"ark_disasm_mcp_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    abc_path = temp_dir / f"{uuid.uuid4().hex}.abc"
    pa_path = temp_dir / f"{uuid.uuid4().hex}.pa"

    try:
        # Write ABC file
        abc_path.write_bytes(abc_bytes)

        # Build command
        cmd = [exe_path, str(abc_path), str(pa_path)]

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
            raise RuntimeError(f"ark_disasm failed:\n{error_output}")

        # Read result
        if not pa_path.exists():
            raise RuntimeError(f"Disassembly completed but output file not created: {pa_path}")

        pa_text = pa_path.read_text(encoding='utf-8', errors='replace')

        metadata = {
            "input_size": len(abc_bytes),
            "output_length": len(pa_text),
            "output_lines": len(pa_text.split('\n')),
            "disassembler": "ark_disasm",
            "platform": platform.system()
        }

        return pa_text, metadata

    finally:
        # Cleanup
        for p in [abc_path, pa_path, temp_dir]:
            try:
                if p.exists():
                    if p.is_dir():
                        p.rmdir()
                    else:
                        p.unlink()
            except:
                pass


# Tool handlers
async def handle_ark_disasm_disassemble(params):
    """Handle ark_disasm_disassemble tool call."""
    abc_bytes_b64 = params.get("abc_bytes_b64", "")
    output_format = params.get("output_format", "markdown")
    truncation_mode = params.get("truncation_mode", "truncate")
    lines = params.get("lines", 100)

    # Validation
    try:
        abc_bytes = base64.b64decode(abc_bytes_b64, validate=True)
    except Exception as e:
        return f"Error: Invalid base64 encoding: {str(e)}"

    if len(abc_bytes) > MAX_FILE_SIZE:
        return f"Error: ABC bytecode exceeds maximum size of {MAX_FILE_SIZE} bytes"

    if len(abc_bytes) < 4:
        return "Error: ABC bytecode too small to be valid"

    try:
        # Disassemble
        pa_text, metadata = await disassemble_abc_to_pa(abc_bytes)

        # Apply truncation
        truncated_pa, truncation_info = truncate_pa_content(pa_text, truncation_mode, lines)
        metadata.update(truncation_info)

        if output_format == "json":
            return json.dumps({
                "success": True,
                "metadata": metadata,
                "pa_content": truncated_pa
            }, indent=2)

        # Markdown format
        lines_md = [
            "# Ark Disasm Result",
            "",
            "## Metadata",
            f"- **Input Size**: {metadata['input_size']:,} bytes",
            f"- **Output Length**: {metadata['output_length']:,} characters",
            f"- **Output Lines**: {metadata['output_lines']:,}",
            f"- **Disassembler**: {metadata['disassembler']}",
            f"- **Platform**: {metadata['platform']}",
        ]

        if truncation_info.get("truncated"):
            lines_md.extend([
                "",
                "## ⚠️ Output Truncated",
                f"- **Total Lines**: {truncation_info.get('total_lines', 'N/A'):,}",
            ])
            if "returned_lines" in truncation_info:
                lines_md.append(f"- **Returned Lines**: {truncation_info['returned_lines']:,}")
            if "returned_chars" in truncation_info:
                lines_md.append(f"- **Returned Characters**: {truncation_info['returned_chars']:,}")
            lines_md.append("")

        lines_md.extend([
            "## PA Output (方舟汇编)",
            "",
            "```pa",
            truncated_pa,
            "```"
        ])

        return "\n".join(lines_md)

    except Exception as e:
        return f"Error: {str(e)}"


async def handle_ark_disasm_disassemble_file(params):
    """Handle ark_disasm_disassemble_file tool call."""
    file_path = params.get("file_path", "")
    output_format = params.get("output_format", "markdown")
    truncation_mode = params.get("truncation_mode", "truncate")
    lines = params.get("lines", 100)

    # Validation
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    if not path.is_file():
        return f"Error: Path is not a file: {file_path}"

    if not path.suffix.lower() == '.abc':
        return f"Error: File must have .abc extension: {file_path}"

    if path.stat().st_size > MAX_FILE_SIZE:
        return f"Error: File exceeds maximum size of {MAX_FILE_SIZE} bytes"

    try:
        # Read ABC file
        abc_bytes = path.read_bytes()

        # Disassemble
        pa_text, metadata = await disassemble_abc_to_pa(abc_bytes)
        metadata["source_file"] = str(path.resolve())

        # Apply truncation
        truncated_pa, truncation_info = truncate_pa_content(pa_text, truncation_mode, lines)
        metadata.update(truncation_info)

        if output_format == "json":
            return json.dumps({
                "success": True,
                "metadata": metadata,
                "pa_content": truncated_pa
            }, indent=2)

        # Markdown format
        lines_md = [
            "# Ark Disasm Result",
            "",
            "## Metadata",
            f"- **Source File**: {metadata['source_file']}",
            f"- **Input Size**: {metadata['input_size']:,} bytes",
            f"- **Output Length**: {metadata['output_length']:,} characters",
            f"- **Output Lines**: {metadata['output_lines']:,}",
            f"- **Disassembler**: {metadata['disassembler']}",
            f"- **Platform**: {metadata['platform']}",
        ]

        if truncation_info.get("truncated"):
            lines_md.extend([
                "",
                "## ⚠️ Output Truncated",
                f"- **Total Lines**: {truncation_info.get('total_lines', 'N/A'):,}",
            ])
            if "returned_lines" in truncation_info:
                lines_md.append(f"- **Returned Lines**: {truncation_info['returned_lines']:,}")

        lines_md.extend([
            "",
            "## PA Output (方舟汇编)",
            "",
            "```pa",
            truncated_pa,
            "```"
        ])

        return "\n".join(lines_md)

    except Exception as e:
        return f"Error: {str(e)}"


async def handle_ark_disasm_get_status(params):
    """Handle ark_disasm_get_status tool call."""
    try:
        exe_path = get_executable_path()

        status = {
            "available": True,
            "executable_path": exe_path,
            "platform": platform.system(),
            "architecture": platform.machine(),
            "max_file_size": MAX_FILE_SIZE,
            "character_limit": CHARACTER_LIMIT,
            "temp_directory": TEMP_DIR
        }

        return json.dumps(status, indent=2)

    except RuntimeError as e:
        status = {
            "available": False,
            "error": str(e),
            "platform": platform.system(),
            "architecture": platform.machine(),
            "suggestion": "Set ARK_DISASM_PATH environment variable to the ark_disasm executable"
        }
        return json.dumps(status, indent=2)


# Main MCP protocol handler
class MCPServer:
    """Simple MCP server implementation for older Python versions."""

    def __init__(self):
        self.tools = {
            "ark_disasm_disassemble": {
                "name": "ark_disasm_disassemble",
                "description": "Disassemble (反汇编) ABC bytecode to PA (方舟汇编) text format using ark_disasm.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "abc_bytes_b64": {
                            "type": "string",
                            "description": "Base64-encoded ABC bytecode"
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Response format"
                        },
                        "truncation_mode": {
                            "type": "string",
                            "enum": ["full", "truncate", "head", "tail"],
                            "description": "How to handle large output"
                        },
                        "lines": {
                            "type": "integer",
                            "description": "Number of lines for head/tail mode (1-10000)"
                        }
                    },
                    "required": ["abc_bytes_b64"]
                }
            },
            "ark_disasm_disassemble_file": {
                "name": "ark_disasm_disassemble_file",
                "description": "Disassemble (反汇编) an ABC file to PA (方舟汇编) text format.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to the ABC file"
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Response format"
                        },
                        "truncation_mode": {
                            "type": "string",
                            "enum": ["full", "truncate", "head", "tail"],
                            "description": "How to handle large output"
                        },
                        "lines": {
                            "type": "integer",
                            "description": "Number of lines for head/tail mode"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            "ark_disasm_get_status": {
                "name": "ark_disasm_get_status",
                "description": "Get the status and configuration of the ark_disasm tool.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        }

        self.handlers = {
            "ark_disasm_disassemble": handle_ark_disasm_disassemble,
            "ark_disasm_disassemble_file": handle_ark_disasm_disassemble_file,
            "ark_disasm_get_status": handle_ark_disasm_get_status
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
