#!/usr/bin/env python3
"""
ES2ABC MCP Server.

This server provides tools to compile JavaScript files to ABC bytecode
using the es2abc compiler. Supports Windows and Linux platforms.
"""

import asyncio
import json
import os
import platform
import shutil
import subprocess
import tempfile
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Initialize the MCP server
mcp = FastMCP("es2abc_mcp")

# Constants
TEMP_DIR = tempfile.gettempdir()
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


def get_executable_path() -> str:
    """Get the platform-specific es2abc executable path."""
    system = platform.system().lower()
    arch = platform.machine().lower()

    # First, check if ES2ABC_PATH environment variable is set
    env_path = os.environ.get("ES2ABC_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Check relative to this script's directory
    script_dir = Path(__file__).parent / "bin"
    if system == "windows":
        exe_path = script_dir / "es2abc.exe"
    else:
        exe_path = script_dir / "es2abc"

    if exe_path.exists():
        return str(exe_path)

    # Check if es2abc is in PATH
    in_path = shutil.which("es2abc")
    if in_path:
        return in_path

    raise RuntimeError(
        f"es2abc executable not found. Please set ES2ABC_PATH environment variable "
        f"or place the binary at: {exe_path}"
    )


# Pydantic Models for Input Validation


class CompileInput(BaseModel):
    """Input model for JavaScript compilation operations."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    js_code: str = Field(
        ...,
        description="JavaScript source code to compile to ABC bytecode (e.g., 'function hello() { return \"world\" }')",
        min_length=1,
        max_length=MAX_FILE_SIZE
    )

    output_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

    return_binary: bool = Field(
        default=False,
        description="If true, return the ABC binary file as base64-encoded data"
    )

    @field_validator('js_code')
    @classmethod
    def validate_js_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("JavaScript code cannot be empty")
        # Check file size
        if len(v.encode('utf-8')) > MAX_FILE_SIZE:
            raise ValueError(f"JavaScript code exceeds maximum size of {MAX_FILE_SIZE} bytes")
        return v


class CompileFileInput(BaseModel):
    """Input model for compiling a JavaScript file by path."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    file_path: str = Field(
        ...,
        description="Absolute path to the JavaScript file to compile (e.g., '/path/to/file.js' or 'C:\\path\\to\\file.js')",
        min_length=1
    )

    output_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

    return_binary: bool = Field(
        default=False,
        description="If true, return the ABC binary file as base64-encoded data"
    )

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        path = Path(v.strip())
        if not path.exists():
            raise ValueError(f"File not found: {v}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {v}")
        if not path.suffix.lower() == '.js':
            raise ValueError(f"File must have .js extension: {v}")
        if path.stat().st_size > MAX_FILE_SIZE:
            raise ValueError(f"File exceeds maximum size of {MAX_FILE_SIZE} bytes")
        return str(path.resolve())


# Shared utility functions


def _handle_process_error(error: subprocess.CalledProcessError, context: str) -> str:
    """Consistent error formatting for process execution failures."""
    error_info = {
        "error": "Compilation failed",
        "context": context,
        "exit_code": error.returncode,
        "stdout": error.stdout if error.stdout else "",
        "stderr": error.stderr if error.stderr else ""
    }
    return json.dumps(error_info, indent=2)


async def _compile_js_to_abc(js_code: str, source_name: str = "input.js") -> tuple[bytes, dict]:
    """
    Execute es2abc compiler to convert JavaScript to ABC bytecode.

    Args:
        js_code: JavaScript source code
        source_name: Original filename for error reporting

    Returns:
        Tuple of (abc_bytes, metadata_dict)
    """
    exe_path = get_executable_path()

    # Create temporary files for compilation
    temp_dir = Path(TEMP_DIR) / f"es2abc_mcp_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    js_path = temp_dir / f"{uuid.uuid4().hex}.js"
    abc_path = temp_dir / f"{uuid.uuid4().hex}.abc"

    try:
        # Write JavaScript source to temporary file
        js_path.write_text(js_code, encoding='utf-8')

        # Build command: es2abc --module input.js --output output.abc
        cmd = [
            exe_path,
            "--module",
            str(js_path),
            "--output",
            str(abc_path)
        ]

        # Execute compiler
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

        # Read the compiled ABC file
        if not abc_path.exists():
            raise RuntimeError("Compilation completed but output file not created")

        abc_bytes = abc_path.read_bytes()

        metadata = {
            "input_size": len(js_code.encode('utf-8')),
            "output_size": len(abc_bytes),
            "compression_ratio": round(len(abc_bytes) / len(js_code.encode('utf-8')), 2) if js_code else 0,
            "compiler": "es2abc",
            "platform": platform.system()
        }

        return abc_bytes, metadata

    finally:
        # Clean up temporary files
        try:
            if js_path.exists():
                js_path.unlink()
            if abc_path.exists():
                abc_path.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()
        except Exception:
            pass  # Best effort cleanup


def _format_compile_result(abc_bytes: bytes, metadata: dict, format: ResponseFormat,
                           return_binary: bool) -> str:
    """Format compilation result based on requested format."""
    if return_binary:
        import base64
        metadata["base64_data"] = base64.b64encode(abc_bytes).decode('ascii')
        metadata["binary_size"] = len(abc_bytes)

    if format == ResponseFormat.JSON:
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
            f"*(Base64 encoded, {metadata['binary_size']} bytes total)*"
        ])
    else:
        lines.extend([
            "",
            "## Output",
            f"ABC bytecode generated successfully ({metadata['output_size']:,} bytes).",
            "Use `return_binary=true` to get the base64-encoded binary data."
        ])

    return "\n".join(lines)


# Tool definitions


@mcp.tool(
    name="es2abc_compile",
    annotations={
        "title": "Compile JavaScript to ABC Bytecode",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def es2abc_compile(params: CompileInput) -> str:
    """Compile JavaScript source code to ABC bytecode using es2abc.

    This tool takes JavaScript source code as a string and compiles it to
    ABC bytecode format using the es2abc compiler. The ABC format is a
    compact bytecode representation used for efficient execution.

    The tool supports both Windows and Linux platforms and automatically
    detects the correct es2abc binary.

    Args:
        params (CompileInput): Validated input parameters containing:
            - js_code (str): JavaScript source code to compile
            - output_format (Optional[ResponseFormat]): Response format (markdown/json)
            - return_binary (Optional[bool]): Return base64-encoded binary data

    Returns:
        str: Formatted compilation result containing:
            - success: Whether compilation succeeded
            - metadata: Input/output size, compression ratio, platform info
            - base64_data: Base64-encoded ABC bytecode (if return_binary=true)

    Examples:
        - Use when: "Compile this JavaScript to ABC bytecode" with js_code="function hello() {}"
        - Use when: "Convert this JS to ABC" with js_code="const x = 42;"
        - Don't use when: You need to compile from a file (use es2abc_compile_file instead)
        - Don't use when: You need to disassemble ABC to PA (use ark_disasm_disassemble instead)

    Error Handling:
        - Returns "Error: es2abc executable not found" if binary is not available
        - Returns "Error: JavaScript code cannot be empty" if input is empty
        - Returns "Error: File exceeds maximum size" if input is too large
        - Returns compilation errors from es2abc if JavaScript has syntax errors

    Platform Support:
        - Windows: Uses es2abc.exe from bin/ directory or ES2ABC_PATH environment variable
        - Linux: Uses es2abc from bin/ directory or ES2ABC_PATH environment variable
        - macOS: Uses es2abc from bin/ directory or ES2ABC_PATH environment variable
    """
    try:
        abc_bytes, metadata = await _compile_js_to_abc(params.js_code, "inline.js")
        metadata["success"] = True
        return _format_compile_result(abc_bytes, metadata, params.output_format, params.return_binary)

    except RuntimeError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error during compilation: {type(e).__name__}: {str(e)}"


@mcp.tool(
    name="es2abc_compile_file",
    annotations={
        "title": "Compile JavaScript File to ABC Bytecode",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def es2abc_compile_file(params: CompileFileInput) -> str:
    """Compile a JavaScript file to ABC bytecode using es2abc.

    This tool reads a JavaScript file from the filesystem and compiles it
    to ABC bytecode format using the es2abc compiler. Use this when you
    have a .js file that needs to be compiled.

    The tool supports both Windows and Linux platforms and automatically
    handles platform-specific paths.

    Args:
        params (CompileFileInput): Validated input parameters containing:
            - file_path (str): Absolute path to the JavaScript file
            - output_format (Optional[ResponseFormat]): Response format (markdown/json)
            - return_binary (Optional[bool]): Return base64-encoded binary data

    Returns:
        str: Formatted compilation result containing:
            - success: Whether compilation succeeded
            - metadata: Input/output size, compression ratio, platform info
            - base64_data: Base64-encoded ABC bytecode (if return_binary=true)

    Examples:
        - Use when: "Compile the file /home/user/app.js to ABC" with file_path="/home/user/app.js"
        - Use when: "Convert C:\\project\\main.js to bytecode" with file_path="C:\\project\\main.js"
        - Don't use when: You have inline JavaScript code (use es2abc_compile instead)
        - Don't use when: You need to disassemble ABC to PA (use ark_disasm_disassemble instead)

    Error Handling:
        - Returns "Error: File not found" if the file doesn't exist
        - Returns "Error: File must have .js extension" if not a JavaScript file
        - Returns "Error: File exceeds maximum size" if file is too large
        - Returns compilation errors from es2abc if JavaScript has syntax errors

    Platform Support:
        - Windows: Supports paths like "C:\\path\\to\\file.js"
        - Linux: Supports paths like "/home/user/file.js"
        - macOS: Supports paths like "/Users/user/file.js"
    """
    try:
        # Read the JavaScript file
        file_path = Path(params.file_path)
        js_code = file_path.read_text(encoding='utf-8')

        abc_bytes, metadata = await _compile_js_to_abc(js_code, file_path.name)
        metadata["source_file"] = str(file_path)
        metadata["success"] = True

        return _format_compile_result(abc_bytes, metadata, params.output_format, params.return_binary)

    except FileNotFoundError:
        return f"Error: File not found: {params.file_path}"
    except RuntimeError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error during compilation: {type(e).__name__}: {str(e)}"


@mcp.tool(
    name="es2abc_get_status",
    annotations={
        "title": "Get ES2ABC Compiler Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def es2abc_get_status() -> str:
    """Get the status and configuration of the es2abc compiler.

    This tool checks if the es2abc compiler is available and provides
    information about its configuration and platform support.

    Returns:
        str: JSON or Markdown formatted status information containing:
            - available: Whether the compiler is found
            - executable_path: Path to the es2abc binary
            - platform: Current operating system
            - architecture: System architecture
            - version_info: Version information if available

    Examples:
        - Use when: Checking if the compiler is properly configured
        - Use when: Debugging compilation issues
        - Use when: Verifying platform support

    Error Handling:
        - Returns status with available=false if compiler not found
        - Includes helpful error message about setting ES2ABC_PATH
    """
    try:
        exe_path = get_executable_path()

        # Try to get version by running the compiler
        version_info = "unknown"
        try:
            process = await asyncio.create_subprocess_exec(
                exe_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            version_output = (stdout or stderr).decode('utf-8', errors='replace').strip()
            if version_output:
                version_info = version_output.split('\n')[0]
        except Exception:
            pass  # Version detection not critical

        status = {
            "available": True,
            "executable_path": exe_path,
            "platform": platform.system(),
            "architecture": platform.machine(),
            "version": version_info,
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


if __name__ == "__main__":
    mcp.run()
