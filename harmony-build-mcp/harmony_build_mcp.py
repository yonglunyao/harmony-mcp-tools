#!/usr/bin/env python3
"""
HarmonyOS Build MCP Server.

This server provides tools to build HarmonyOS projects (HAP applications and HAR static libraries)
using the hvigorw build system. Supports Windows, Linux, and macOS platforms.
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
from typing import Optional, List

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Initialize the MCP server
mcp = FastMCP("harmony_build_mcp")

# Constants
TEMP_DIR = tempfile.gettempdir()
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB for log output


class BuildTarget(str, Enum):
    """Build target types for HarmonyOS projects."""
    HAP = "hap"          # HarmonyOS Ability Package (Application)
    HAR = "har"          # HarmonyOS Archive (Static Library)
    HSP = "hsp"          # HarmonyOS Shared Package (Shared Library)


class BuildMode(str, Enum):
    """Build mode for compilation."""
    DEBUG = "debug"
    RELEASE = "release"


class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


def get_hvigorw_path(project_path: Path) -> Path:
    """
    Get the hvigorw executable path for the given project.

    Args:
        project_path: Path to the HarmonyOS project

    Returns:
        Path to the hvigorw executable
    """
    system = platform.system().lower()

    if system == "windows":
        hvigorw_name = "hvigorw.bat"
    else:
        hvigorw_name = "hvigorw"

    # Check in project root
    hvigorw_path = project_path / hvigorw_name
    if hvigorw_path.exists():
        return hvigorw_path

    # Check in standard DevEco Studio project structure
    for parent in [project_path, project_path.parent]:
        for name in [hvigorw_name, f"{hvigorw_name}.exe"]:
            path = parent / name
            if path.exists():
                return path

    # Check if hvigorw is in PATH
    in_path = shutil.which(hvigorw_name)
    if in_path:
        return Path(in_path)

    raise RuntimeError(
        f"hvigorw executable not found for project: {project_path}. "
        f"Please ensure this is a valid HarmonyOS project with hvigorw build script."
    )


def find_project_root(start_path: Path) -> Path:
    """
    Find the HarmonyOS project root by looking for build profile files.

    Args:
        start_path: Starting path to search from

    Returns:
        Path to the project root directory
    """
    current = start_path.resolve()

    # Look for project markers
    markers = [
        "build-profile.json5",
        "hvigorfile.ts",
        "oh-package.json5",
        "AppScope",
    ]

    # Search up to 5 levels
    for _ in range(5):
        for marker in markers:
            if (current / marker).exists():
                return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    # If start_path is a file, start from its parent
    if start_path.is_file():
        return find_project_root(start_path.parent)

    return start_path


def get_module_info(project_path: Path) -> dict:
    """
    Extract module information from the HarmonyOS project.

    Args:
        project_path: Path to the project

    Returns:
        Dictionary containing module information
    """
    info = {
        "modules": [],
        "project_name": project_path.name,
        "has_app_scope": (project_path / "AppScope").exists(),
    }

    # Find build-profile.json5 for module list
    build_profile = project_path / "build-profile.json5"
    if build_profile.exists():
        try:
            content = build_profile.read_text(encoding='utf-8')
            # Simple parsing for modules (basic implementation)
            import re
            module_matches = re.findall(r'"name"\s*:\s*"([^"]+)"', content)
            info["modules"] = list(set(module_matches))
        except Exception:
            pass

    # Check for entry module
    entry_path = project_path / "entry"
    if entry_path.exists():
        if "entry" not in info["modules"]:
            info["modules"].append("entry")

    return info


# Pydantic Models for Input Validation


class BuildInput(BaseModel):
    """Input model for HarmonyOS build operations."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Path to the HarmonyOS project directory (absolute or relative)",
        min_length=1
    )

    target: BuildTarget = Field(
        default=BuildTarget.HAP,
        description="Build target type: 'hap' for application, 'har' for static library, 'hsp' for shared package"
    )

    mode: BuildMode = Field(
        default=BuildMode.DEBUG,
        description="Build mode: 'debug' or 'release'"
    )

    module: Optional[str] = Field(
        default=None,
        description="Specific module to build (e.g., 'entry'). If not specified, builds all modules"
    )

    clean: bool = Field(
        default=False,
        description="Clean build output before building (perform a clean build)"
    )

    output_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        path = Path(v.strip()).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Project path does not exist: {v}")
        return str(path)


class BuildModuleInput(BaseModel):
    """Input model for building a specific module."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Path to the HarmonyOS project directory",
        min_length=1
    )

    module_name: str = Field(
        ...,
        description="Name of the module to build (e.g., 'entry', 'mylibrary')",
        min_length=1
    )

    mode: BuildMode = Field(
        default=BuildMode.DEBUG,
        description="Build mode: 'debug' or 'release'"
    )

    clean: bool = Field(
        default=False,
        description="Clean build output before building"
    )

    output_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'"
    )

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        path = Path(v.strip()).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Project path does not exist: {v}")
        return str(path)


# Shared utility functions


def _format_build_result(result: dict, format: ResponseFormat) -> str:
    """Format build result based on requested format."""
    if format == ResponseFormat.JSON:
        return json.dumps(result, indent=2, ensure_ascii=False)

    # Markdown format
    lines = [
        "# HarmonyOS Build Result",
        "",
        "## Summary",
        f"- **Status**: {'✅ Success' if result.get('success') else '❌ Failed'}",
        f"- **Project**: `{result.get('project_name', 'N/A')}`",
        f"- **Target**: {result.get('target', 'N/A').upper()}",
        f"- **Mode**: {result.get('mode', 'N/A')}",
        f"- **Platform**: {result.get('platform', 'N/A')}",
    ]

    if result.get('module'):
        lines.append(f"- **Module**: {result['module']}")

    if result.get('duration'):
        lines.append(f"- **Duration**: {result['duration']:.2f}s")

    # Output paths
    if result.get('output_paths'):
        lines.extend([
            "",
            "## Output Artifacts"
        ])
        for path in result['output_paths']:
            lines.append(f"- `{path}`")

    # Build log
    if result.get('build_log'):
        log = result['build_log']
        if len(log) > 2000:
            log = log[:2000] + "\n... (truncated)"
        lines.extend([
            "",
            "## Build Log",
            "```",
            log,
            "```"
        ])

    # Error information
    if not result.get('success') and result.get('error'):
        lines.extend([
            "",
            "## Error",
            f"```\n{result['error']}\n```"
        ])

    return "\n".join(lines)


async def _execute_build(
    project_path: Path,
    target: BuildTarget,
    mode: BuildMode,
    module: Optional[str] = None,
    clean: bool = False
) -> dict:
    """
    Execute the HarmonyOS build process.

    Args:
        project_path: Path to the project
        target: Build target type
        mode: Build mode
        module: Specific module to build
        clean: Whether to clean before build

    Returns:
        Dictionary containing build results
    """
    import time
    start_time = time.time()

    result = {
        "success": False,
        "project_path": str(project_path),
        "project_name": project_path.name,
        "target": target.value,
        "mode": mode.value,
        "module": module,
        "platform": platform.system(),
        "output_paths": [],
        "build_log": "",
        "error": None
    }

    try:
        # Find project root and hvigorw
        project_root = find_project_root(project_path)
        result["project_root"] = str(project_root)
        hvigorw_path = get_hvigorw_path(project_root)

        # Get module info
        module_info = get_module_info(project_root)
        result["available_modules"] = module_info["modules"]

        # Build command
        cmd = [str(hvigorw_path)]

        # Add module if specified
        if module:
            cmd.append(f":{module}:assemble{mode.value}")
        else:
            # Build all modules
            cmd.append(f"assemble{mode.value}")

        # Add target-specific options
        if target == BuildTarget.HAR:
            cmd.append("--publish-har")

        # Execute clean if requested
        if clean:
            clean_cmd = [str(hvigorw_path)]
            if module:
                clean_cmd.append(f":{module}:clean")
            else:
                clean_cmd.append("clean")

            try:
                clean_process = await asyncio.create_subprocess_exec(
                    *clean_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=project_root
                )
                await clean_process.communicate()
            except Exception:
                pass  # Clean failure is not critical

        # Execute build
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=project_root
        )

        stdout, _ = await process.communicate()
        build_log = stdout.decode('utf-8', errors='replace')

        # Truncate log if too large
        if len(build_log) > MAX_LOG_SIZE:
            build_log = build_log[:MAX_LOG_SIZE] + "\n... (log truncated)"

        result["build_log"] = build_log
        result["exit_code"] = process.returncode

        # Find output files
        output_dir = project_root
        if module:
            output_dir = project_root / module
        else:
            # Find entry module default
            entry_path = project_root / "entry"
            if entry_path.exists():
                output_dir = entry_path

        # Look for output in standard locations
        search_paths = [
            output_dir / "build" / "default" / "outputs" / "default",
            output_dir / "build" / mode.value / "output",
            project_root / "build" / "outputs" / "default",
        ]

        for search_path in search_paths:
            if search_path.exists():
                for ext in ['*.hap', '*.har', '*.hsp', '*.app']:
                    for file in search_path.rglob(ext):
                        result["output_paths"].append(str(file))

        result["success"] = process.returncode == 0

        if not result["success"]:
            result["error"] = f"Build failed with exit code {process.returncode}"

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["success"] = False

    result["duration"] = time.time() - start_time
    return result


# Tool definitions


@mcp.tool(
    name="harmony_build",
    annotations={
        "title": "Build HarmonyOS Project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def harmony_build(params: BuildInput) -> str:
    """Build a HarmonyOS project using hvigorw.

    This tool builds HarmonyOS projects (HAP applications, HAR static libraries,
    or HSP shared packages) using the hvigorw build system.

    The tool supports Windows, Linux, and macOS platforms and automatically
    detects the project structure and build configuration.

    Args:
        params (BuildInput): Validated input parameters containing:
            - project_path (str): Path to the HarmonyOS project directory
            - target (BuildTarget): Build target type (hap/har/hsp)
            - mode (BuildMode): Build mode (debug/release)
            - module (Optional[str]): Specific module to build
            - clean (bool): Whether to clean before building
            - output_format (ResponseFormat): Response format (markdown/json)

    Returns:
        str: Formatted build result containing:
            - success: Whether build succeeded
            - project_name: Name of the project
            - target: Build target type
            - mode: Build mode
            - output_paths: List of generated artifact paths
            - build_log: Build output log
            - duration: Build time in seconds

    Examples:
        - Use when: "Build my HarmonyOS project" with project_path="/path/to/project"
        - Use when: "Build in release mode" with mode="release"
        - Use when: "Build the entry module" with module="entry"
        - Use when: "Do a clean build" with clean=true

    Error Handling:
        - Returns error if project path does not exist
        - Returns error if hvigorw is not found
        - Returns build logs and exit code on build failure

    Platform Support:
        - Windows: Uses hvigorw.bat
        - Linux/macOS: Uses hvigorw
    """
    try:
        project_path = Path(params.project_path)
        result = await _execute_build(
            project_path,
            params.target,
            params.mode,
            params.module,
            params.clean
        )
        return _format_build_result(result, params.output_format)

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error during build: {type(e).__name__}: {str(e)}"


@mcp.tool(
    name="harmony_build_module",
    annotations={
        "title": "Build HarmonyOS Module",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def harmony_build_module(params: BuildModuleInput) -> str:
    """Build a specific module in a HarmonyOS project.

    This tool builds a specific module (e.g., 'entry', 'mylibrary') within
    a HarmonyOS project using the hvigorw build system.

    Args:
        params (BuildModuleInput): Validated input parameters containing:
            - project_path (str): Path to the HarmonyOS project directory
            - module_name (str): Name of the module to build
            - mode (BuildMode): Build mode (debug/release)
            - clean (bool): Whether to clean before building
            - output_format (ResponseFormat): Response format (markdown/json)

    Returns:
        str: Formatted build result with module-specific information

    Examples:
        - Use when: "Build the entry module" with module_name="entry"
        - Use when: "Build mylibrary in release mode"

    Error Handling:
        - Returns error if module is not found
        - Returns build logs on failure
    """
    try:
        project_path = Path(params.project_path)

        # Verify module exists
        project_root = find_project_root(project_path)
        module_path = project_root / params.module_name
        if not module_path.exists():
            return f"Error: Module '{params.module_name}' not found in project"

        result = await _execute_build(
            project_path,
            BuildTarget.HAP,  # Default to HAP for modules
            params.mode,
            params.module_name,
            params.clean
        )
        return _format_build_result(result, params.output_format)

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error during build: {type(e).__name__}: {str(e)}"


@mcp.tool(
    name="harmony_clean",
    annotations={
        "title": "Clean HarmonyOS Build Output",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def harmony_clean(project_path: str, output_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """Clean build output from a HarmonyOS project.

    This tool removes all build artifacts and temporary files from a
    HarmonyOS project using the hvigorw clean task.

    Args:
        project_path (str): Path to the HarmonyOS project directory
        output_format (ResponseFormat): Response format (markdown/json)

    Returns:
        str: Formatted clean result

    Examples:
        - Use when: "Clean my HarmonyOS project"
        - Use when: "Remove build artifacts"
    """
    try:
        path = Path(project_path).expanduser().resolve()
        if not path.exists():
            return f"Error: Project path does not exist: {project_path}"

        project_root = find_project_root(path)
        hvigorw_path = get_hvigorw_path(project_root)

        cmd = [str(hvigorw_path), "clean"]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=project_root
        )

        stdout, _ = await process.communicate()
        log = stdout.decode('utf-8', errors='replace')

        result = {
            "success": process.returncode == 0,
            "project_path": str(project_root),
            "action": "clean",
            "exit_code": process.returncode,
            "log": log[:5000] if len(log) > 5000 else log
        }

        if output_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2, ensure_ascii=False)

        lines = [
            "# HarmonyOS Clean Result",
            "",
            f"**Status**: {'✅ Success' if result['success'] else '❌ Failed'}",
            f"**Project**: `{result['project_path']}`",
            "",
            "## Build Log",
            "```",
            result['log'],
            "```"
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"


@mcp.tool(
    name="harmony_get_project_info",
    annotations={
        "title": "Get HarmonyOS Project Information",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def harmony_get_project_info(project_path: str, output_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """Get information about a HarmonyOS project.

    This tool analyzes a HarmonyOS project and returns information about
    its structure, modules, and build configuration.

    Args:
        project_path (str): Path to the HarmonyOS project directory
        output_format (ResponseFormat): Response format (markdown/json)

    Returns:
        str: Formatted project information

    Examples:
        - Use when: "Tell me about this HarmonyOS project"
        - Use when: "What modules are in this project?"
    """
    try:
        path = Path(project_path).expanduser().resolve()
        if not path.exists():
            return f"Error: Project path does not exist: {project_path}"

        project_root = find_project_root(path)
        module_info = get_module_info(project_root)

        # Try to get hvigorw info
        hvigorw_path = None
        try:
            hvigorw_path = str(get_hvigorw_path(project_root))
        except Exception:
            pass

        result = {
            "project_root": str(project_root),
            "project_name": project_root.name,
            "has_app_scope": module_info["has_app_scope"],
            "modules": module_info["modules"],
            "hvigorw_path": hvigorw_path,
            "platform": platform.system()
        }

        if output_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2, ensure_ascii=False)

        lines = [
            "# HarmonyOS Project Information",
            "",
            f"**Project Name**: {result['project_name']}",
            f"**Project Root**: `{result['project_root']}`",
            f"**Platform**: {result['platform']}",
            f"**Has AppScope**: {'Yes' if result['has_app_scope'] else 'No'}",
            "",
            "## Modules"
        ]

        if result['modules']:
            for module in result['modules']:
                lines.append(f"- `{module}`")
        else:
            lines.append("*No modules found*")

        if result['hvigorw_path']:
            lines.extend([
                "",
                "## Build System",
                f"**hvigorw**: `{result['hvigorw_path']}`"
            ])

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"


@mcp.tool(
    name="harmony_build_get_status",
    annotations={
        "title": "Get HarmonyOS Build Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def harmony_build_get_status() -> str:
    """Get the status of the HarmonyOS build environment.

    This tool checks if the HarmonyOS build tools are available and
    provides information about the build environment.

    Returns:
        str: JSON formatted status information

    Examples:
        - Use when: Checking if the build environment is properly configured
        - Use when: Debugging build issues
    """
    status = {
        "available": True,
        "platform": platform.system(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "supported_targets": [t.value for t in BuildTarget],
        "supported_modes": [m.value for m in BuildMode]
    }

    # Try to find DevEco Studio or hvigorw in common locations
    common_paths = []
    system = platform.system().lower()

    if system == "windows":
        possible_roots = [
            Path("C:/DevecoStudio"),
            Path(os.path.expanduser("~/AppData/Local/DevecoStudio")),
        ]
    elif system == "darwin":
        possible_roots = [
            Path("/Applications/DevEco-Studio.app"),
        ]
    else:
        possible_roots = [
            Path("~/DevecoStudio").expanduser(),
            Path("/opt/devecostudio"),
        ]

    for root in possible_roots:
        if root.exists():
            common_paths.append(str(root))

    status["common_installation_paths"] = common_paths
    status["common_installation_paths_found"] = len(common_paths) > 0

    return json.dumps(status, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
