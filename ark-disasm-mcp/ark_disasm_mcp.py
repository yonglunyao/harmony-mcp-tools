#!/usr/bin/env python3
"""
Ark Disasm MCP Server.

This server provides tools to disassemble ABC bytecode files to PA (方舟汇编 / Ark Assembly)
text format using the ark_disasm tool.

ABC (Ark Bytecode / 方舟字节码) is the compiled bytecode format for ArkTS/JavaScript.
PA (方舟汇编) is the human-readable assembly representation of ABC bytecode.

This is disassembly (反汇编), NOT decompilation - it converts bytecode to assembly
format, not back to the original source code.

Supports Windows, Linux, and macOS platforms.
"""

import asyncio
import json
import os
import platform
import shutil
import tempfile
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

import base64
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Initialize the MCP server
mcp = FastMCP("ark_disasm_mcp")

# Constants
TEMP_DIR = tempfile.gettempdir()
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
CHARACTER_LIMIT = 25000  # Maximum PA text output size


class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class TruncationMode(str, Enum):
    """How to handle large PA output."""
    FULL = "full"  # Return complete output (may be very large)
    TRUNCATE = "truncate"  # Truncate to CHARACTER_LIMIT
    HEAD = "head"  # Return first N lines
    TAIL = "tail"  # Return last N lines


def get_executable_path() -> str:
    """Get the platform-specific ark_disasm executable path."""
    system = platform.system().lower()

    # First, check if ARK_DISASM_PATH environment variable is set
    env_path = os.environ.get("ARK_DISASM_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Check relative to this script's directory
    script_dir = Path(__file__).parent / "bin"
    if system == "windows":
        exe_path = script_dir / "ark_disasm.exe"
    else:
        exe_path = script_dir / "ark_disasm"

    if exe_path.exists():
        return str(exe_path)

    # Check if ark_disasm is in PATH
    in_path = shutil.which("ark_disasm")
    if in_path:
        return in_path

    raise RuntimeError(
        f"ark_disasm executable not found. Please set ARK_DISASM_PATH environment variable "
        f"or place the binary at: {exe_path}"
    )


# Pydantic Models for Input Validation


class DisassembleInput(BaseModel):
    """Input model for ABC disassembly operations."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    abc_bytes_b64: str = Field(
        ...,
        description="Base64-encoded ABC bytecode to disassemble (e.g., from es2abc output)",
        min_length=1
    )

    output_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

    truncation_mode: TruncationMode = Field(
        default=TruncationMode.TRUNCATE,
        description="How to handle large output: 'full', 'truncate', 'head', or 'tail'"
    )

    lines: Optional[int] = Field(
        default=None,
        description="Number of lines to return when truncation_mode is 'head' or 'tail' (default: 100)",
        ge=1,
        le=10000
    )

    @field_validator('abc_bytes_b64')
    @classmethod
    def validate_abc_bytes(cls, v: str) -> str:
        try:
            decoded = base64.b64decode(v, validate=True)
            if len(decoded) > MAX_FILE_SIZE:
                raise ValueError(f"ABC bytecode exceeds maximum size of {MAX_FILE_SIZE} bytes")
            if len(decoded) < 4:
                raise ValueError("ABC bytecode too small to be valid")
            return v
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {str(e)}")


class DisassembleFileInput(BaseModel):
    """Input model for disassembling an ABC file by path."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    file_path: str = Field(
        ...,
        description="Absolute path to the ABC file to disassemble (e.g., '/path/to/file.abc' or 'C:\\path\\to\\file.abc')",
        min_length=1
    )

    output_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

    truncation_mode: TruncationMode = Field(
        default=TruncationMode.TRUNCATE,
        description="How to handle large output: 'full', 'truncate', 'head', or 'tail'"
    )

    lines: Optional[int] = Field(
        default=None,
        description="Number of lines to return when truncation_mode is 'head' or 'tail' (default: 100)",
        ge=1,
        le=10000
    )

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        path = Path(v.strip())
        if not path.exists():
            raise ValueError(f"File not found: {v}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {v}")
        if not path.suffix.lower() == '.abc':
            raise ValueError(f"File must have .abc extension: {v}")
        if path.stat().st_size > MAX_FILE_SIZE:
            raise ValueError(f"File exceeds maximum size of {MAX_FILE_SIZE} bytes")
        return str(path.resolve())


# Shared utility functions


def _truncate_pa_content(pa_text: str, mode: TruncationMode,
                        lines: Optional[int] = None) -> tuple[str, dict]:
    """
    Truncate PA content based on the specified mode.

    Returns:
        Tuple of (truncated_text, truncation_info)
    """
    pa_lines = pa_text.split('\n')
    total_lines = len(pa_lines)
    total_chars = len(pa_text)

    if mode == TruncationMode.FULL:
        return pa_text, {
            "truncated": False,
            "total_lines": total_lines,
            "total_chars": total_chars
        }

    if mode == TruncationMode.TRUNCATE:
        if len(pa_text) <= CHARACTER_LIMIT:
            return pa_text, {
                "truncated": False,
                "total_lines": total_lines,
                "total_chars": total_chars
            }
        # Find a good truncation point
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

    if mode == TruncationMode.HEAD:
        n = lines or 100
        truncated = '\n'.join(pa_lines[:n])
        return truncated, {
            "truncated": total_lines > n,
            "total_lines": total_lines,
            "returned_lines": min(n, total_lines),
            "total_chars": total_chars,
            "truncation_mode": "head"
        }

    if mode == TruncationMode.TAIL:
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


async def _disassemble_abc_to_pa(abc_bytes: bytes) -> tuple[str, dict]:
    """
    Execute ark_disasm to disassemble ABC bytecode to PA (方舟汇编) text format.

    This is disassembly (反汇编), NOT decompilation. It converts bytecode
    to its assembly representation.

    Args:
        abc_bytes: ABC bytecode (方舟字节码)

    Returns:
        Tuple of (pa_text, metadata_dict) where pa_text is 方舟汇编 format
    """
    exe_path = get_executable_path()

    # Create temporary files for disassembly
    temp_dir = Path(TEMP_DIR) / f"ark_disasm_mcp_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    abc_path = temp_dir / f"{uuid.uuid4().hex}.abc"
    pa_path = temp_dir / f"{uuid.uuid4().hex}.pa"

    try:
        # Write ABC bytecode to temporary file
        abc_path.write_bytes(abc_bytes)

        # Build command: ark_disasm input.abc output.pa
        cmd = [
            exe_path,
            str(abc_path),
            str(pa_path)
        ]

        # Execute disassembler
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

        # Read the disassembled PA file
        if not pa_path.exists():
            raise RuntimeError("Disassembly completed but output file not created")

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
        # Clean up temporary files
        try:
            if abc_path.exists():
                abc_path.unlink()
            if pa_path.exists():
                pa_path.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()
        except Exception:
            pass  # Best effort cleanup


def _format_disasm_result(pa_text: str, metadata: dict, truncation_info: dict,
                         format: ResponseFormat) -> str:
    """Format disassembly result based on requested format."""
    metadata.update(truncation_info)

    if format == ResponseFormat.JSON:
        # For JSON, include full PA content in the response
        result = {
            "success": True,
            "metadata": metadata,
            "pa_content": pa_text
        }
        return json.dumps(result, indent=2)

    # Markdown format
    lines = [
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
        lines.extend([
            "",
            "## ⚠️ Output Truncated",
            f"- **Total Lines**: {truncation_info.get('total_lines', 'N/A'):,}",
        ])
        if "returned_lines" in truncation_info:
            lines.append(f"- **Returned Lines**: {truncation_info['returned_lines']:,}")
        if "returned_chars" in truncation_info:
            lines.append(f"- **Returned Characters**: {truncation_info['returned_chars']:,}")
        if truncation_info.get("truncation_mode") == "character_limit":
            lines.append(f"- **Character Limit**: {CHARACTER_LIMIT:,}")

        mode = truncation_info.get("truncation_mode")
        if mode == "head":
            lines.append("- **Mode**: First N lines shown")
        elif mode == "tail":
            lines.append("- **Mode**: Last N lines shown")
        elif mode == "character_limit":
            lines.append("- **Mode**: Truncated at character limit")
        lines.append("")
    else:
        lines.append("")

    lines.extend([
        "## PA Output (方舟汇编)",
        "",
        "```pa",
        pa_text,
        "```"
    ])

    return "\n".join(lines)


# Tool definitions


@mcp.tool(
    name="ark_disasm_disassemble",
    annotations={
        "title": "Disassemble ABC Bytecode to PA Text",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def ark_disasm_disassemble(params: DisassembleInput) -> str:
    """Disassemble ABC bytecode to PA (方舟汇编 / Ark Assembly) text format.

    This tool performs disassembly (反汇编) of ABC bytecode - it converts
    bytecode to human-readable PA assembly format, NOT back to source code.

    ABC (Ark Bytecode / 方舟字节码) is the compiled bytecode for ArkTS/JavaScript.
    PA (方舟汇编 / Ark Assembly) is the assembly representation of ABC bytecode.
    the bytecode structure, instructions, and metadata in a readable form.

    The tool supports both Windows and Linux platforms and automatically
    detects the correct ark_disasm binary.

    Args:
        params (DisassembleInput): Validated input parameters containing:
            - abc_bytes_b64 (str): Base64-encoded ABC bytecode
            - output_format (Optional[ResponseFormat]): Response format (markdown/json)
            - truncation_mode (Optional[TruncationMode]): How to handle large output
            - lines (Optional[int]): Lines for head/tail mode (default: 100)

    Returns:
        str: Formatted disassembly result containing:
            - success: Whether disassembly succeeded
            - metadata: Input/output size, line count, platform info
            - pa_content: The disassembled PA text (may be truncated)
            - truncation_info: Information about output truncation if applicable

    Examples:
        - Use when: "Disassemble this ABC bytecode" with abc_bytes_b64 from es2abc output
        - Use when: "Convert ABC to PA format for inspection"
        - Use when: "Show me the first 50 lines of the ABC disassembly" with truncation_mode="head", lines=50
        - Don't use when: You have an ABC file path (use ark_disasm_disassemble_file instead)
        - Don't use when: You need to compile JS to ABC (use es2abc_compile instead)

    Error Handling:
        - Returns "Error: ark_disasm executable not found" if binary is not available
        - Returns "Error: Invalid base64 encoding" if input is malformed
        - Returns "Error: ABC bytecode too small" if input is too small
        - Returns disassembly errors from ark_disasm if bytecode is invalid

    Platform Support:
        - Windows: Uses ark_disasm.exe from bin/ directory or ARK_DISASM_PATH environment variable
        - Linux: Uses ark_disasm from bin/ directory or ARK_DISASM_PATH environment variable
        - macOS: Uses ark_disasm from bin/ directory or ARK_DISASM_PATH environment variable

    Truncation Modes:
        - full: Return complete output (may be very large, use with caution)
        - truncate (default): Truncate to CHARACTER_LIMIT at a natural break point
        - head: Return first N lines (controlled by 'lines' parameter)
        - tail: Return last N lines (controlled by 'lines' parameter)
    """
    try:
        # Decode base64 ABC bytecode
        abc_bytes = base64.b64decode(params.abc_bytes_b64, validate=True)

        # Perform disassembly
        pa_text, metadata = await _disassemble_abc_to_pa(abc_bytes)

        # Apply truncation
        truncated_pa, truncation_info = _truncate_pa_content(
            pa_text,
            params.truncation_mode,
            params.lines
        )

        return _format_disasm_result(truncated_pa, metadata, truncation_info, params.output_format)

    except ValueError as e:
        return f"Error: {str(e)}"
    except RuntimeError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error during disassembly: {type(e).__name__}: {str(e)}"


@mcp.tool(
    name="ark_disasm_disassemble_file",
    annotations={
        "title": "Disassemble ABC File to PA Text",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def ark_disasm_disassemble_file(params: DisassembleFileInput) -> str:
    """Disassemble an ABC bytecode file to PA (方舟汇编) text format using ark_disasm.

    This tool performs disassembly (反汇编) of ABC bytecode files. It reads an ABC
    file and converts it to PA assembly format - NOT back to source code.

    ABC (Ark Bytecode / 方舟字节码) is the compiled bytecode for ArkTS/JavaScript.
    PA (方舟汇编 / Ark Assembly) is the assembly representation of ABC bytecode.

    The tool supports both Windows and Linux platforms and automatically
    handles platform-specific paths.

    Args:
        params (DisassembleFileInput): Validated input parameters containing:
            - file_path (str): Absolute path to the ABC file
            - output_format (Optional[ResponseFormat]): Response format (markdown/json)
            - truncation_mode (Optional[TruncationMode]): How to handle large output
            - lines (Optional[int]): Lines for head/tail mode (default: 100)

    Returns:
        str: Formatted disassembly result containing:
            - success: Whether disassembly succeeded
            - metadata: Input/output size, line count, platform info
            - pa_content: The disassembled PA text (may be truncated)
            - truncation_info: Information about output truncation if applicable

    Examples:
        - Use when: "Disassemble the file /home/user/app.abc to PA" with file_path="/home/user/app.abc"
        - Use when: "Show me the last 100 lines of C:\\project\\main.abc" with file_path="C:\\project\\main.abc", truncation_mode="tail"
        - Don't use when: You have base64-encoded ABC bytes (use ark_disasm_disassemble instead)
        - Don't use when: You need to compile JS to ABC (use es2abc_compile instead)

    Error Handling:
        - Returns "Error: File not found" if the file doesn't exist
        - Returns "Error: File must have .abc extension" if not an ABC file
        - Returns "Error: File exceeds maximum size" if file is too large
        - Returns disassembly errors from ark_disasm if bytecode is invalid

    Platform Support:
        - Windows: Supports paths like "C:\\path\\to\\file.abc"
        - Linux: Supports paths like "/home/user/file.abc"
        - macOS: Supports paths like "/Users/user/file.abc"

    Truncation Modes:
        - full: Return complete output (may be very large, use with caution)
        - truncate (default): Truncate to CHARACTER_LIMIT at a natural break point
        - head: Return first N lines (controlled by 'lines' parameter)
        - tail: Return last N lines (controlled by 'lines' parameter)
    """
    try:
        # Read the ABC file
        file_path = Path(params.file_path)
        abc_bytes = file_path.read_bytes()

        # Perform disassembly
        pa_text, metadata = await _disassemble_abc_to_pa(abc_bytes)
        metadata["source_file"] = str(file_path)

        # Apply truncation
        truncated_pa, truncation_info = _truncate_pa_content(
            pa_text,
            params.truncation_mode,
            params.lines
        )

        return _format_disasm_result(truncated_pa, metadata, truncation_info, params.output_format)

    except FileNotFoundError:
        return f"Error: File not found: {params.file_path}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except RuntimeError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error during disassembly: {type(e).__name__}: {str(e)}"


@mcp.tool(
    name="ark_disasm_get_status",
    annotations={
        "title": "Get Ark Disasm Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def ark_disasm_get_status() -> str:
    """Get the status and configuration of the ark_disasm tool.

    This tool checks if the ark_disasm disassembler is available and provides
    information about its configuration and platform support.

    Returns:
        str: JSON formatted status information containing:
            - available: Whether the disassembler is found
            - executable_path: Path to the ark_disasm binary
            - platform: Current operating system
            - architecture: System architecture
            - max_file_size: Maximum supported file size
            - temp_directory: Temporary directory used for processing

    Examples:
        - Use when: Checking if the disassembler is properly configured
        - Use when: Debugging disassembly issues
        - Use when: Verifying platform support

    Error Handling:
        - Returns status with available=false if disassembler not found
        - Includes helpful error message about setting ARK_DISASM_PATH
    """
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


if __name__ == "__main__":
    mcp.run()
