"""Data parsers for title.txt and tasklist files."""

import logging
from pathlib import Path
from typing import Optional

from .models import FieldMetadata, DataFileError, ParseError, error_response

logger = logging.getLogger(__name__)


def safe_read_file(file_path: str) -> tuple[bool, str, Optional[list[str]]]:
    """
    Safely read a file.

    Returns:
        (success, message, content)
    """
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {file_path}", None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.readlines()
        return True, "OK", content
    except UnicodeDecodeError:
        # Try other encodings
        try:
            with open(file_path, "r", encoding="gbk") as f:
                content = f.readlines()
            return True, "OK (GBK encoding)", content
        except Exception as e:
            return False, f"Encoding error: {str(e)}", None
    except PermissionError:
        return False, f"Permission denied, cannot read file: {file_path}", None
    except Exception as e:
        return False, f"Failed to read file: {str(e)}", None


def parse_title_file(file_path: str) -> list[FieldMetadata]:
    """
    Parse title.txt file.

    The file should contain 3 lines (tab-separated):
    1. English column names
    2. Chinese full names
    3. Chinese short names

    Args:
        file_path: Path to title.txt

    Returns:
        List of FieldMetadata objects

    Raises:
        DataFileError: If file cannot be read
        ParseError: If file format is invalid
    """
    success, message, lines = safe_read_file(file_path)
    if not success:
        raise DataFileError(message)

    # Remove trailing newlines
    lines = [line.strip() for line in lines if line.strip()]

    if len(lines) < 3:
        raise ParseError(
            f"title.txt must have at least 3 lines, got {len(lines)}"
        )

    # Split by tabs
    en_names = lines[0].split("\t")  # English column names
    cn_full = lines[1].split("\t")  # Chinese full names
    cn_short = lines[2].split("\t")  # Chinese short names

    # Validate column counts
    if not (len(en_names) == len(cn_full) == len(cn_short)):
        raise ParseError(
            f"Column count mismatch: en={len(en_names)}, "
            f"cn_full={len(cn_full)}, cn_short={len(cn_short)}"
        )

    # Build field metadata
    fields = []
    for i, (en, full, short) in enumerate(zip(en_names, cn_full, cn_short)):
        fields.append(
            FieldMetadata(
                key=en,
                en_name=en,
                cn_full_name=full,
                cn_short_name=short,
                index=i,
            )
        )

    logger.info(f"Parsed {len(fields)} fields from {file_path}")
    return fields


def parse_data_file(
    file_path: str, fields: list[FieldMetadata]
) -> list[dict]:
    """
    Parse data file (no header, tab-separated).

    Args:
        file_path: Path to data file
        fields: Field metadata list

    Returns:
        List of task dictionaries

    Raises:
        DataFileError: If file cannot be read
    """
    tasks = []

    success, message, lines = safe_read_file(file_path)
    if not success:
        raise DataFileError(message)

    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:  # Skip empty lines
            continue

        values = line.split("\t")

        # Build task dictionary
        task = {}
        for field in fields:
            value = values[field.index] if field.index < len(values) else ""

            # Special handling for risk_tags: split by "/"
            if field.key == "risk_tags" and value:
                # Split by "/" and filter out empty strings
                tags = [tag.strip() for tag in value.split("/") if tag.strip()]
                task[field.key] = tags
                # Also keep the original string
                task[field.key + "_original"] = value
            else:
                task[field.key] = value

        tasks.append(task)

    logger.info(f"Parsed {len(tasks)} tasks from {file_path}")
    return tasks
