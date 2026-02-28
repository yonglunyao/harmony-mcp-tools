#!/usr/bin/env python3
"""
Simple test script for ArkTS API Validator
"""

import sys
import os
import json

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from arkts_api_validator import ArktsApiParser, SdkType


def test_parser():
    """Test the parser functionality."""
    print("=" * 60)
    print("ArkTS API Validator - Test")
    print("=" * 60)

    # Get SDK path from environment or use default
    sdk_path = os.environ.get("HARMONYOS_SDK_PATH", r"C:\Program Files\Huawei\DevEco Studio\sdk\default")
    print(f"\nSDK Path: {sdk_path}")
    print(f"SDK exists: {os.path.exists(sdk_path)}")

    # Initialize parser
    parser = ArktsApiParser(sdk_path)

    # Build index
    print("\nBuilding API index...")
    stats = parser.build_index()
    print(json.dumps(stats, indent=2))

    # Test API validation
    print("\n" + "=" * 60)
    print("Testing API Validation")
    print("=" * 60)

    test_apis = [
        "@ohos.accessibility",
        "@ohos.accessibility.isOpenAccessibility",
        "@ohos.accessibility.AccessibilityAbilityInfo",
        "@ohos.ability.ability",
        "@hms.ai.face.faceDetector",
        "@hms.ai.face.faceDetector.VisionInfo",
        "@ohos.nonexistent.module",
        "@ohos.accessibility.fakeFunction"
    ]

    for api in test_apis:
        print(f"\nValidating: {api}")
        result = parser.validate_api(api)
        if result.get("valid"):
            print(f"  [OK] Found in {result['result']['sdk_type']}: {result['result'].get('match_type', 'module')}")
        else:
            print(f"  [X] Not found")
            if "results" in result:
                for r in result["results"]:
                    print(f"    - {r.get('reason', r.get('sdk_type'))}")

    # Test search
    print("\n" + "=" * 60)
    print("Testing API Search")
    print("=" * 60)

    search_queries = ["Image", "create", "Detector"]

    for query in search_queries:
        print(f"\nSearching for: '{query}'")
        results = parser.search_apis(query, limit=5)
        print(f"  Found {len(results)} results (showing first 5):")
        for r in results[:5]:
            if r.get("match_type") == "module":
                print(f"    - Module: {r['module']}")
            else:
                print(f"    - {r['sdk_type']}.{r['module']}.{r['name']} ({r['match_type']})")

    # Test list modules
    print("\n" + "=" * 60)
    print("Testing List Modules")
    print("=" * 60)

    modules = parser.list_modules(SdkType.OPENHARMONY)
    print(f"\nOpenHarmony modules (first 10 of {len(modules)}):")
    for m in modules[:10]:
        print(f"  - {m}")

    hms_modules = parser.list_modules(SdkType.HMS)
    print(f"\nHMS modules (first 10 of {len(hms_modules)}):")
    for m in hms_modules[:10]:
        print(f"  - {m}")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_parser()
