"""Data models for the HarmonyOS Task List Manager."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FieldMetadata:
    """Field metadata from title.txt."""

    key: str  # Field identifier (used as key in code)
    en_name: str  # English column name
    cn_full_name: str  # Chinese full name
    cn_short_name: str  # Chinese short name
    index: int  # Column index (0-24)


# Exception classes
class HarmonyTaskListError(Exception):
    """Base exception class."""

    pass


class ConfigError(HarmonyTaskListError):
    """Configuration error."""

    pass


class DataFileError(HarmonyTaskListError):
    """Data file error."""

    pass


class ParseError(HarmonyTaskListError):
    """Data parsing error."""

    pass


class SearchError(HarmonyTaskListError):
    """Search error."""

    pass


class ValidationError(HarmonyTaskListError):
    """Parameter validation error."""

    pass


def error_response(
    error_type: str, message: str, details: Optional[dict] = None
) -> dict:
    """Unified error response format."""
    response = {
        "success": False,
        "error": {"type": error_type, "message": message},
    }
    if details:
        response["error"]["details"] = details
    return response
