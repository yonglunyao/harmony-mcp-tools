"""
ArkTS API Validator MCP Server

A Model Context Protocol server for validating HarmonyOS ArkTS APIs
against SDK declarations.
"""

__version__ = "1.1.0"
__author__ = "Claude Code"

from .core import ArktsApiParser, SdkType

__all__ = ["ArktsApiParser", "SdkType", "__version__"]
