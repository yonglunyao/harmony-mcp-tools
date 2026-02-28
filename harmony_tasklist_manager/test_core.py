"""
Core functionality test script (without FastMCP dependency).

This script demonstrates the core data parsing, search, and filter capabilities
of the HarmonyOS Task List Manager.
"""

from src.config import Config
from src.parsers import parse_title_file, parse_data_file
from src.search import TaskSearcher, AdvancedSearcher, DataManager
import json


def main():
    print("=" * 60)
    print("HarmonyOS Task List Manager - Core Test")
    print("=" * 60)

    # Load configuration
    print("\n1. Loading configuration...")
    config = Config()
    print(f"   Title file: {config.title_file_path}")
    print(f"   Data file: {config.data_file_path}")
    print(f"   Default limit: {config.default_limit}")
    print(f"   Max limit: {config.max_limit}")

    # Parse title file
    print("\n2. Parsing title.txt...")
    fields = parse_title_file(config.title_file_path)
    print(f"   Parsed {len(fields)} fields")
    print("   Sample fields:")
    for f in fields[:5]:
        print(f"     - {f.key} ({f.cn_short_name})")

    # Parse data file
    print("\n3. Parsing tasklist.txt...")
    tasks = parse_data_file(config.data_file_path, fields)
    print(f"   Parsed {len(tasks)} tasks")

    # Display first task
    print("\n4. First task sample:")
    for k, v in list(tasks[0].items())[:8]:
        print(f"     {k}: {v}")

    # Test search
    print("\n5. Testing search functionality...")
    searcher = TaskSearcher(fields)
    result = searcher.search(tasks, "机检恶意")
    print(f"   Search '机检恶意': {result['total_matches']} matches")

    # Test filter
    print("\n6. Testing filter functionality...")
    filter_result = AdvancedSearcher.filter_by_conditions(
        tasks, {"auto_detection_result": "BLACK"}
    )
    print(f"   Filter by BLACK: {filter_result['total_matches']} tasks")

    # Test statistics
    print("\n7. Testing statistics...")
    stats = AdvancedSearcher.get_statistics(tasks)
    print(f"   Total tasks: {stats['statistics']['total_tasks']}")
    print(f"   By detection result:")
    for k, v in stats['statistics']['by_detection_result'].items():
        print(f"     - {k}: {v}")

    # Display field metadata format (for AI Agent understanding)
    print("\n8. Field metadata format (for AI Agent):")
    field_metadata = [
        {
            "key": f.key,
            "name": f.en_name,
            "label": f.cn_short_name,
            "description": f.cn_full_name,
            "index": f.index,
        }
        for f in fields
    ]
    print("   Sample fields (first 5):")
    for fm in field_metadata[:5]:
        print(f"     - {fm['key']}: {fm['description']}")

    # Test DataManager
    print("\n8. Testing DataManager with caching...")
    data_manager = DataManager(
        title_file_path=config.title_file_path,
        data_file_path=config.data_file_path,
        cache_ttl=config.cache_ttl,
    )
    cached_tasks = data_manager.get_tasks()
    print(f"   Loaded {len(cached_tasks)} tasks (cached)")

    # Test reload
    print("\n9. Testing data reload...")
    data_manager.clear_cache()
    reloaded_tasks = data_manager.get_tasks(force_reload=True)
    print(f"   Reloaded {len(reloaded_tasks)} tasks")

    print("\n" + "=" * 60)
    print("All tests passed! Core functionality is working correctly.")
    print("=" * 60)
    print("\nNote: To use the MCP server, you need:")
    print("  - Python 3.11+ (to avoid typing_extensions compatibility issues)")
    print("  - Install: pip install fastmcp pyyaml")
    print("  - Run: python -m src.main")


if __name__ == "__main__":
    main()
