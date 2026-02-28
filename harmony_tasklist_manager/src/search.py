"""Search functionality for task list."""

import re
import logging
from typing import Optional
from datetime import datetime

from .models import FieldMetadata

logger = logging.getLogger(__name__)


class DataManager:
    """Data manager with caching and hot reload."""

    def __init__(self, title_file_path: str, data_file_path: str, cache_ttl):
        self.title_file_path = title_file_path
        self.data_file_path = data_file_path
        self._cache_ttl = cache_ttl
        self._fields_cache = None
        self._tasks_cache = None
        self._last_loaded = None

    def get_fields(self):
        """Get field metadata (with caching)."""
        if self._fields_cache is None:
            from .parsers import parse_title_file

            self._fields_cache = parse_title_file(self.title_file_path)
        return self._fields_cache

    def get_tasks(self, force_reload: bool = False):
        """Get task list (with caching)."""
        now = datetime.now()

        # Check if cache is expired
        if (
            force_reload
            or self._tasks_cache is None
            or self._last_loaded is None
            or now - self._last_loaded > self._cache_ttl
        ):
            from .parsers import parse_data_file

            fields = self.get_fields()
            self._tasks_cache = parse_data_file(self.data_file_path, fields)
            self._last_loaded = now

        return self._tasks_cache

    def clear_cache(self):
        """Clear cache."""
        self._fields_cache = None
        self._tasks_cache = None
        self._last_loaded = None


class TaskSearcher:
    """Task searcher."""

    def __init__(self, fields: list[FieldMetadata]):
        self.fields = fields
        self.field_keys = [f.key for f in fields]

    def search(
        self,
        tasks: list[dict],
        query: str,
        search_fields: Optional[list[str]] = None,
        case_sensitive: bool = False,
    ) -> dict:
        """
        Multi-field fuzzy search.

        Args:
            tasks: Task list
            query: Search keyword
            search_fields: Fields to search (None means all fields)
            case_sensitive: Whether to distinguish case

        Returns:
            Search result
        """
        if not query:
            return {
                "success": True,
                "query": query,
                "matched_fields": [],
                "total_matches": len(tasks),
                "returned": len(tasks),
                "tasks": tasks,
            }

        # Determine search fields
        fields_to_search = search_fields if search_fields else self.field_keys

        # Compile regex
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(re.escape(query), flags)
        except re.error:
            # If regex fails, use simple substring search
            pattern = None

        results = []
        matched_field_set = set()

        for task in tasks:
            match_highlights = {}
            is_match = False

            for field_key in fields_to_search:
                value = task.get(field_key, "")
                if not value:
                    continue

                # Handle list values (e.g., risk_tags)
                if isinstance(value, list):
                    # Search within list elements
                    is_field_match = False
                    matched_elements = []
                    for item in value:
                        if isinstance(item, str):
                            if pattern:
                                item_match = pattern.search(item) is not None
                            else:
                                if case_sensitive:
                                    item_match = query in item
                                else:
                                    item_match = query.lower() in item.lower()

                            if item_match:
                                is_field_match = True
                                matched_elements.append(
                                    self._highlight_matches(item, query, case_sensitive)
                                )

                    if is_field_match:
                        is_match = True
                        matched_field_set.add(field_key)
                        match_highlights[field_key] = matched_elements
                    continue

                # Check match for string values
                if pattern:
                    is_field_match = pattern.search(value) is not None
                else:
                    if case_sensitive:
                        is_field_match = query in value
                    else:
                        is_field_match = query.lower() in value.lower()

                if is_field_match:
                    is_match = True
                    matched_field_set.add(field_key)
                    # Highlight matches
                    match_highlights[field_key] = self._highlight_matches(
                        value, query, case_sensitive
                    )

            if is_match:
                task_copy = task.copy()
                task_copy["_match_highlights"] = match_highlights
                results.append(task_copy)

        return {
            "success": True,
            "query": query,
            "matched_fields": list(matched_field_set),
            "total_matches": len(results),
            "returned": len(results),
            "tasks": results,
        }

    def _highlight_matches(
        self, text: str, query: str, case_sensitive: bool
    ) -> str:
        """Highlight matches in text."""
        if case_sensitive:
            return text.replace(query, f"**{query}**")
        else:
            # Case-insensitive highlight
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            return pattern.sub(lambda m: f"**{m.group()}**", text)


class AdvancedSearcher:
    """Advanced searcher with filtering capabilities."""

    @staticmethod
    def filter_by_conditions(
        tasks: list[dict], filters: dict, match_mode: str = "all"
    ) -> dict:
        """
        Filter tasks by multiple conditions.

        Args:
            tasks: Task list
            filters: Filter conditions {field: value}
            match_mode: "all"=all match, "any"=any match
        """
        results = []

        def value_matches(task_value: any, filter_value: any) -> bool:
            """Check if task value matches filter value."""
            # Handle list values (e.g., risk_tags)
            if isinstance(task_value, list):
                return str(filter_value) in [str(v) for v in task_value]
            # Handle string/other values
            return str(task_value) == str(filter_value)

        for task in tasks:
            if match_mode == "all":
                # All conditions must be satisfied
                if all(
                    value_matches(task.get(field), value)
                    for field, value in filters.items()
                ):
                    results.append(task)
            else:  # "any"
                # Any condition satisfied
                if any(
                    value_matches(task.get(field), value)
                    for field, value in filters.items()
                ):
                    results.append(task)

        return {
            "success": True,
            "filters": filters,
            "match_mode": match_mode,
            "total_matches": len(results),
            "tasks": results,
        }

    @staticmethod
    def get_statistics(tasks: list[dict], group_by: Optional[str] = None) -> dict:
        """Get task statistics."""
        total = len(tasks)
        stats = {"total_tasks": total}

        if group_by:
            # Group by field
            group_counts = {}
            for task in tasks:
                value = task.get(group_by, "") or "(empty)"
                group_counts[value] = group_counts.get(value, 0) + 1
            stats[f"by_{group_by}"] = group_counts

        # Default statistics for common fields
        # Risk detection result
        detection_counts = {}
        for task in tasks:
            value = task.get("auto_detection_result", "") or "(empty)"
            detection_counts[value] = detection_counts.get(value, 0) + 1
        stats["by_detection_result"] = detection_counts

        # Manual conclusion
        conclusion_counts = {}
        for task in tasks:
            value = task.get("manual_analysis_conclusion", "") or "(empty)"
            conclusion_counts[value] = conclusion_counts.get(value, 0) + 1
        stats["by_manual_conclusion"] = conclusion_counts

        return {"success": True, "statistics": stats}
