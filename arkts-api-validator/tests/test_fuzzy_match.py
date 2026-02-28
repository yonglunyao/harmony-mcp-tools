#!/usr/bin/env python3
"""Test fuzzy matching suggestions"""

import sys
import os
import json

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from arkts_api_validator import ArktsApiParser, SdkType


def test_fuzzy_matching():
    print("=" * 60)
    print("Testing Fuzzy Matching Suggestions")
    print("=" * 60)

    sdk_path = os.environ.get("HARMONYOS_SDK_PATH", r"C:\Program Files\Huawei\DevEco Studio\sdk\default")
    parser = ArktsApiParser(sdk_path)
    parser.build_index()

    # Test cases with typos
    test_cases = [
        "@ohos.accessibilty",  # Missing 'i' -> accessibility
        "@ohos.accesibility",  # Extra 's'
        "@ohos.accessibility.openAcessibility",  # Typo in function name
        "@ohos.ability.Ability",  # Wrong case
        "@hms.ai.face.facedetector",  # Wrong case
    ]

    for api in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Testing: {api}")
        print('=' * 60)
        result = parser.validate_api(api)

        if result.get("valid"):
            print(f"  [OK] Found: {result['result'].get('display_name', result['result'].get('name', 'module'))}")
        else:
            print(f"  [X] Not found")
            if "suggestions" in result and result["suggestions"]:
                print(f"\n  [?] Did you mean:")
                for sugg in result["suggestions"][:5]:
                    print(f"    - {sugg['suggested_api']} (similarity: {sugg['similarity']})")


if __name__ == "__main__":
    test_fuzzy_matching()
