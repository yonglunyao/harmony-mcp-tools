#!/usr/bin/env python3
"""
ArkTS API Validator Core Parser

This module contains the core parsing logic for ArkTS .d.ts and .d.ets files.
"""

import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_SDK_PATH = r"C:\Program Files\Huawei\DevEco Studio\sdk\default"
SDK_PATH_ENV = "HARMONYOS_SDK_PATH"

# SDK types
class SdkType(str, Enum):
    '''HarmonyOS SDK type.'''
    HMS = "hms"
    OPENHARMONY = "openharmony"
    ALL = "all"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ApiDeclaration:
    """Represents an ArkTS API declaration."""
    name: str
    kind: str  # 'namespace', 'interface', 'class', 'function', 'type', 'enum', 'export_type'
    file_path: str
    sdk_type: SdkType
    module: str
    line_number: int = 0
    export_name: Optional[str] = None  # For export type alias


@dataclass
class ModuleIndex:
    """Index of APIs for a single module."""
    module_name: str
    sdk_type: SdkType
    file_path: str
    namespaces: Dict[str, ApiDeclaration] = field(default_factory=dict)
    interfaces: Dict[str, ApiDeclaration] = field(default_factory=dict)
    classes: Dict[str, ApiDeclaration] = field(default_factory=dict)
    functions: Dict[str, ApiDeclaration] = field(default_factory=dict)
    types: Dict[str, ApiDeclaration] = field(default_factory=dict)
    enums: Dict[str, ApiDeclaration] = field(default_factory=dict)
    export_types: Dict[str, ApiDeclaration] = field(default_factory=dict)


# ============================================================================
# API Parser
# ============================================================================

class ArktsApiParser:
    """Parser for ArkTS .d.ts and .d.ets declaration files."""

    # Patterns for matching declarations
    NAMESPACE_PATTERN = re.compile(r'^declare\s+namespace\s+(\w+)\s*\{', re.MULTILINE)
    INTERFACE_PATTERN = re.compile(r'(?:export\s+)?interface\s+(\w+)', re.MULTILINE)
    CLASS_PATTERN = re.compile(r'(?:export\s+)?class\s+(\w+)', re.MULTILINE)
    FUNCTION_PATTERN = re.compile(r'function\s+(\w+)\s*\(', re.MULTILINE)
    TYPE_PATTERN = re.compile(r'(?:export\s+)?type\s+(\w+)\s*=', re.MULTILINE)
    ENUM_PATTERN = re.compile(r'(?:export\s+)?enum\s+(\w+)', re.MULTILINE)
    EXPORT_TYPE_PATTERN = re.compile(r'export\s+type\s+(\w+)\s*=', re.MULTILINE)
    EXPORT_TYPE_TYPEDEF = re.compile(r'@typedef\s+\{\s*(\w+)\s*\}', re.MULTILINE)

    def __init__(self, sdk_path: str):
        self.sdk_path = Path(sdk_path)
        self.index: Dict[str, Dict[str, ModuleIndex]] = {
            SdkType.HMS: {},
            SdkType.OPENHARMONY: {}
        }
        self._indexed = False

    def _extract_module_from_filename(self, filename: str) -> str:
        """Extract module name from .d.ts filename."""
        # Remove @ prefix and .d.ts/.d.ets extension
        name = filename.lstrip('@')
        if name.endswith('.d.ts'):
            name = name[:-5]
        elif name.endswith('.d.ets'):
            name = name[:-6]
        return name

    def _find_declarations(self, content: str, file_path: str, sdk_type: SdkType, module: str) -> List[ApiDeclaration]:
        """Find all API declarations in a file."""
        declarations = []
        lines = content.split('\n')

        # Track current namespace for nested declarations
        current_namespace = None
        # Track namespace depth for proper nesting handling
        namespace_depth = 0
        brace_depth = 0

        for line_num, line in enumerate(lines, 1):
            # Track brace depth for namespace nesting
            brace_depth += line.count('{') - line.count('}')

            # Check for namespace declaration
            ns_match = self.NAMESPACE_PATTERN.search(line)
            if ns_match:
                ns_name = ns_match.group(1)
                declarations.append(ApiDeclaration(
                    name=ns_name,
                    kind='namespace',
                    file_path=file_path,
                    sdk_type=sdk_type,
                    module=module,
                    line_number=line_num
                ))
                current_namespace = ns_name
                namespace_depth = brace_depth
                continue

            # Check if we exited the namespace
            if current_namespace is not None and brace_depth <= namespace_depth:
                current_namespace = None
                namespace_depth = 0

            # Find interfaces
            for match in self.INTERFACE_PATTERN.finditer(line):
                name = match.group(1)
                # Skip common JSDoc type references
                if name not in ('Object', 'Array', 'Function', 'Promise', 'Callback', 'AsyncCallback'):
                    # Store with namespace prefix if inside a namespace
                    full_name = f"{current_namespace}.{name}" if current_namespace else name
                    declarations.append(ApiDeclaration(
                        name=full_name,
                        kind='interface',
                        file_path=file_path,
                        sdk_type=sdk_type,
                        module=module,
                        line_number=line_num,
                        export_name=name  # Store the actual name without prefix
                    ))

            # Find classes
            for match in self.CLASS_PATTERN.finditer(line):
                name = match.group(1)
                full_name = f"{current_namespace}.{name}" if current_namespace else name
                declarations.append(ApiDeclaration(
                    name=full_name,
                    kind='class',
                    file_path=file_path,
                    sdk_type=sdk_type,
                    module=module,
                    line_number=line_num,
                    export_name=name
                ))

            # Find functions (both module level and namespace level)
            for match in self.FUNCTION_PATTERN.finditer(line):
                name = match.group(1)
                full_name = f"{current_namespace}.{name}" if current_namespace else name
                declarations.append(ApiDeclaration(
                    name=full_name,
                    kind='function',
                    file_path=file_path,
                    sdk_type=sdk_type,
                    module=module,
                    line_number=line_num,
                    export_name=name
                ))

            # Find type aliases
            for match in self.TYPE_PATTERN.finditer(line):
                name = match.group(1)
                full_name = f"{current_namespace}.{name}" if current_namespace else name
                declarations.append(ApiDeclaration(
                    name=full_name,
                    kind='type',
                    file_path=file_path,
                    sdk_type=sdk_type,
                    module=module,
                    line_number=line_num,
                    export_name=name
                ))

            # Find enums
            for match in self.ENUM_PATTERN.finditer(line):
                name = match.group(1)
                full_name = f"{current_namespace}.{name}" if current_namespace else name
                declarations.append(ApiDeclaration(
                    name=full_name,
                    kind='enum',
                    file_path=file_path,
                    sdk_type=sdk_type,
                    module=module,
                    line_number=line_num,
                    export_name=name
                ))

            # Find export type declarations
            for match in self.EXPORT_TYPE_PATTERN.finditer(line):
                name = match.group(1)
                full_name = f"{current_namespace}.{name}" if current_namespace else name
                declarations.append(ApiDeclaration(
                    name=full_name,
                    kind='export_type',
                    file_path=file_path,
                    sdk_type=sdk_type,
                    module=module,
                    line_number=line_num,
                    export_name=name
                ))

        return declarations

    def _index_file(self, file_path: Path, sdk_type: SdkType):
        """Index a single declaration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            module_name = self._extract_module_from_filename(file_path.name)

            # Find all declarations
            declarations = self._find_declarations(
                content,
                str(file_path),
                sdk_type,
                module_name
            )

            # Create module index
            module_index = ModuleIndex(
                module_name=module_name,
                sdk_type=sdk_type,
                file_path=str(file_path)
            )

            # Categorize declarations
            for decl in declarations:
                if decl.kind == 'namespace':
                    module_index.namespaces[decl.name] = decl
                elif decl.kind == 'interface':
                    module_index.interfaces[decl.name] = decl
                elif decl.kind == 'class':
                    module_index.classes[decl.name] = decl
                elif decl.kind == 'function':
                    module_index.functions[decl.name] = decl
                elif decl.kind == 'type':
                    module_index.types[decl.name] = decl
                elif decl.kind == 'enum':
                    module_index.enums[decl.name] = decl
                elif decl.kind == 'export_type':
                    module_index.export_types[decl.name] = decl

            self.index[sdk_type][module_name] = module_index

        except Exception as e:
            print(f"Warning: Failed to index {file_path}: {e}")

    def _index_directory(self, sdk_type: SdkType):
        """Index all declaration files in an SDK directory."""
        api_dir = self.sdk_path / sdk_type.value / "ets" / "api"

        if not api_dir.exists():
            print(f"Warning: API directory not found: {api_dir}")
            return

        # Find all .d.ts and .d.ets files
        declaration_files = []
        for pattern in ('*.d.ts', '*.d.ets'):
            declaration_files.extend(api_dir.glob(f'**/{pattern}'))

        # Also check root level files
        for pattern in ('*.d.ts', '*.d.ets'):
            declaration_files.extend(api_dir.glob(pattern))

        print(f"Found {len(declaration_files)} declaration files in {sdk_type.value} SDK")

        # Index files in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            for file_path in declaration_files:
                executor.submit(self._index_file, file_path, sdk_type)

    def build_index(self) -> Dict[str, Any]:
        """Build the complete API index from SDK."""
        if self._indexed:
            return self._get_index_stats()

        print(f"Building API index from: {self.sdk_path}")

        # Index both SDK types
        self._index_directory(SdkType.OPENHARMONY)
        self._index_directory(SdkType.HMS)

        self._indexed = True
        return self._get_index_stats()

    def _get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        stats = {
            "indexed": self._indexed,
            "sdk_path": str(self.sdk_path),
            "sdks": {}
        }

        for sdk_type in [SdkType.OPENHARMONY, SdkType.HMS]:
            modules = self.index[sdk_type]
            total_decls = sum(
                len(m.interfaces) + len(m.classes) + len(m.functions) +
                len(m.types) + len(m.enums) + len(m.export_types)
                for m in modules.values()
            )
            stats["sdks"][sdk_type.value] = {
                "modules": len(modules),
                "total_declarations": total_decls
            }

        return stats

    def validate_api(self, api_path: str, sdk_type: Optional[SdkType] = None) -> Dict[str, Any]:
        """
        Validate if an API exists in the SDK.

        Args:
            api_path: API path like '@ohos.accessibility.isOpenAccessibility'
                     or '@hms.ai.face.faceDetector.VisionInfo'
            sdk_type: Specific SDK to check, or None to check both

        Returns:
            Dict with validation result
        """
        if not self._indexed:
            self.build_index()

        # Parse API path
        # Expected formats:
        # - @ohos.module
        # - @ohos.module.Name
        # - @ohos.module.namespace.Name
        # - @hms.module.Name

        if not api_path.startswith('@'):
            return {
                "valid": False,
                "error": "API path must start with '@' (e.g., '@ohos.accessibility')"
            }

        # Remove @ prefix and split
        path_parts = api_path[1:].split('.')

        if len(path_parts) < 2:
            return {
                "valid": False,
                "error": "Invalid API path format. Expected: '@sdk.module[.name]'"
            }

        # Determine SDK type from path
        path_sdk = path_parts[0]  # 'ohos' or 'hms'
        if path_sdk == 'ohos':
            sdk_types = [SdkType.OPENHARMONY]
        elif path_sdk == 'hms':
            sdk_types = [SdkType.HMS]
        else:
            return {
                "valid": False,
                "error": f"Unknown SDK prefix: '{path_sdk}'. Use 'ohos' or 'hms'"
            }

        # Override if specific SDK type requested
        if sdk_type and sdk_type != SdkType.ALL:
            if sdk_type in sdk_types:
                sdk_types = [sdk_type]
            else:
                sdk_types.append(sdk_type)

        # Try to find the module by trying different splits
        # The module could be: sdk.module, sdk.module.submodule, etc.
        results = []

        for sdk_t in sdk_types:
            matched = False

            # Try different module name lengths
            for module_parts_count in range(1, len(path_parts)):
                # Build module name from parts after SDK prefix
                module_name = ".".join(path_parts[:module_parts_count + 1])  # Include SDK prefix

                if module_name not in self.index[sdk_t]:
                    continue

                module = self.index[sdk_t][module_name]
                name_parts = path_parts[module_parts_count + 1:]

                # If no name parts, just validate module exists
                if not name_parts:
                    results.append({
                        "sdk_type": sdk_t.value,
                        "found": True,
                        "match_type": "module",
                        "module": module.module_name,
                        "file": module.file_path
                    })
                    matched = True
                    break

                # Check for specific declaration
                for decl_type, decls in [
                    ('interfaces', module.interfaces),
                    ('classes', module.classes),
                    ('functions', module.functions),
                    ('types', module.types),
                    ('enums', module.enums),
                    ('export_types', module.export_types)
                ]:
                    for decl_name, decl in decls.items():
                        # Check both full name (with namespace prefix) and export name (without prefix)
                        if self._match_name_path(decl_name, name_parts) or \
                           (decl.export_name and self._match_name_path(decl.export_name, name_parts)):
                            results.append({
                                "sdk_type": sdk_t.value,
                                "found": True,
                                "match_type": decl_type.rstrip('s'),  # Remove plural 's'
                                "module": module.module_name,
                                "name": decl_name,
                                "display_name": decl.export_name or decl_name,  # Use export name for display
                                "kind": decl.kind,
                                "file": module.file_path
                            })
                            matched = True
                            break
                    if matched:
                        break

                if matched:
                    break

            if not matched:
                results.append({
                    "sdk_type": sdk_t.value,
                    "found": False,
                    "reason": f"API '{api_path}' not found in {sdk_t.value} SDK"
                })

        # Return the first positive result or all negative results
        for result in results:
            if result["found"]:
                return {
                    "valid": True,
                    "api": api_path,
                    "result": result
                }

        # If no match found, try to find similar APIs as suggestions
        suggestions = self._find_similar_apis(api_path, sdk_types, limit=5)

        return {
            "valid": False,
            "api": api_path,
            "results": results,
            "suggestions": suggestions if suggestions else []
        }

    def _match_name_path(self, name: str, parts: List[str]) -> bool:
        """Check if a name matches the path parts (supports nested names)."""
        name_path = name.split('.')
        return name_path == parts or (len(parts) == 1 and parts[0] == name)

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using SequenceMatcher (0-1 range)."""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def _find_similar_apis(self, api_path: str, sdk_types: List[SdkType], limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar APIs when exact match is not found."""
        if not self._indexed:
            self.build_index()

        # Parse the API path to get the last part (likely the API name)
        path_parts = api_path[1:].split('.')
        search_name = path_parts[-1] if len(path_parts) > 1 else path_parts[0]

        suggestions = []
        seen = set()

        for sdk_t in sdk_types:
            for module_name, module in self.index[sdk_t].items():
                # Check module names
                similarity = self._calculate_similarity(module_name.split('.')[-1], search_name)
                if similarity >= 0.5:  # 50% similarity threshold
                    key = f"{sdk_t.value}:{module_name}"
                    if key not in seen:
                        suggestions.append({
                            "sdk_type": sdk_t.value,
                            "module": module_name,
                            "match_type": "module",
                            "similarity": round(similarity, 2),
                            "suggested_api": f"@{module_name}"
                        })
                        seen.add(key)

                # Check declarations
                for decl_type, decls in [
                    ('interfaces', module.interfaces),
                    ('classes', module.classes),
                    ('functions', module.functions),
                    ('types', module.types),
                    ('enums', module.enums)
                ]:
                    for decl_name, decl in decls.items():
                        # Use export_name if available (the actual name without namespace prefix)
                        compare_name = decl.export_name if decl.export_name else decl_name.split('.')[-1]
                        similarity = self._calculate_similarity(compare_name, search_name)

                        if similarity >= 0.5:
                            # Build the suggested API path
                            if '.' in decl_name:
                                # It's a namespaced declaration
                                parts = decl_name.split('.')
                                suggested_api = f"@{module_name}.{parts[-1]}"
                            else:
                                suggested_api = f"@{module_name}.{decl_name}"

                            key = f"{sdk_t.value}:{suggested_api}"
                            if key not in seen:
                                suggestions.append({
                                    "sdk_type": sdk_t.value,
                                    "module": module_name,
                                    "match_type": decl_type.rstrip('s'),
                                    "name": decl.export_name or decl_name,
                                    "similarity": round(similarity, 2),
                                    "suggested_api": suggested_api
                                })
                                seen.add(key)

        # Sort by similarity and return top matches
        suggestions.sort(key=lambda x: x["similarity"], reverse=True)
        return suggestions[:limit]

    def search_apis(self, query: str, sdk_type: SdkType = SdkType.ALL, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for APIs matching a query."""
        if not self._indexed:
            self.build_index()

        results = []
        query_lower = query.lower()

        sdk_types = [SdkType.OPENHARMONY, SdkType.HMS] if sdk_type == SdkType.ALL else [sdk_type]

        for sdk_t in sdk_types:
            for module_name, module in self.index[sdk_t].items():
                # Search in module name
                if query_lower in module_name.lower():
                    results.append({
                        "sdk_type": sdk_t.value,
                        "module": module_name,
                        "match_type": "module",
                        "file": module.file_path
                    })
                    continue

                # Search in declarations
                for decl_type, decls in [
                    ('interfaces', module.interfaces),
                    ('classes', module.classes),
                    ('functions', module.functions),
                    ('types', module.types),
                    ('enums', module.enums),
                    ('export_types', module.export_types)
                ]:
                    for decl_name, decl in decls.items():
                        if query_lower in decl_name.lower():
                            results.append({
                                "sdk_type": sdk_t.value,
                                "module": module_name,
                                "match_type": decl_type.rstrip('s'),
                                "name": decl_name,
                                "kind": decl.kind,
                                "file": module.file_path
                            })

                            if len(results) >= limit:
                                return results

        return results[:limit]

    def list_modules(self, sdk_type: SdkType = SdkType.ALL) -> List[str]:
        """List all available modules."""
        if not self._indexed:
            self.build_index()

        modules = []
        sdk_types = [SdkType.OPENHARMONY, SdkType.HMS] if sdk_type == SdkType.ALL else [sdk_type]

        for sdk_t in sdk_types:
            for module_name in self.index[sdk_t].keys():
                prefix = 'ohos' if sdk_t == SdkType.OPENHARMONY else 'hms'
                modules.append(f"@{prefix}.{module_name}")

        return sorted(modules)


# ============================================================================
# Global Parser Instance
# ============================================================================

_parser: Optional[ArktsApiParser] = None


def get_parser() -> ArktsApiParser:
    """Get or create the global parser instance."""
    global _parser

    if _parser is None:
        sdk_path = os.environ.get(SDK_PATH_ENV, DEFAULT_SDK_PATH)
        _parser = ArktsApiParser(sdk_path)

    return _parser

