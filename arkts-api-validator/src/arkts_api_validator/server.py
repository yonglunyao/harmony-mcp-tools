"""
MCP Server definition for ArkTS API Validator.
"""

import json
import os
from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, field_validator, ConfigDict

from .core import (
    ArktsApiParser,
    SdkType,
    get_parser,
    DEFAULT_SDK_PATH,
    SDK_PATH_ENV
)

# Initialize the MCP server
mcp = FastMCP("arkts_api_validator_mcp")


# ============================================================================
# Input Models
# ============================================================================

class ValidateApiInput(BaseModel):
    """Input model for API validation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    api_path: str = Field(
        ...,
        description="Full API path to validate. Examples: '@ohos.accessibility.isOpenAccessibility', '@hms.ai.face.faceDetector.VisionInfo', '@ohos.ability.ability'",
        min_length=3
    )

    @field_validator('api_path')
    @classmethod
    def validate_api_path(cls, v: str) -> str:
        if not v.startswith('@'):
            raise ValueError("API path must start with '@'")
        if len(v.split('.')) < 2:
            raise ValueError("API path must contain at least '@sdk.module'")
        return v


class SearchApisInput(BaseModel):
    """Input model for API search."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    query: str = Field(
        ...,
        description="Search query for API names. Examples: 'Image', 'create', 'Detector'",
        min_length=1
    )
    sdk_type: SdkType = Field(
        default=SdkType.ALL,
        description="SDK type to search: 'hms', 'openharmony', or 'all' (default)"
    )
    limit: int = Field(
        default=50,
        description="Maximum number of results to return (1-100)",
        ge=1,
        le=100
    )


class ListModulesInput(BaseModel):
    """Input model for listing modules."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    sdk_type: SdkType = Field(
        default=SdkType.ALL,
        description="SDK type to list: 'hms', 'openharmony', or 'all' (default)"
    )


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool(
    name="validate_arkts_api",
    annotations={
        "title": "Validate ArkTS API",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def validate_arkts_api(params: ValidateApiInput, ctx: Context) -> str:
    '''
    Validate if an ArkTS API exists in the HarmonyOS SDK.

    This tool checks whether a given API path is available in the HarmonyOS SDK
    by searching through all .d.ts and .d.ets declaration files. It helps prevent
    compilation errors caused by using non-existent APIs.

    Args:
        params (ValidateApiInput): Validated input parameters containing:
            - api_path (str): Full API path to validate. Must start with '@' and contain
              at least '@sdk.module'. Examples:
              - '@ohos.accessibility' - module only
              - '@ohos.accessibility.isOpenAccessibility' - module + function
              - '@hms.ai.face.faceDetector.VisionInfo' - module + interface
              - '@ohos.ability.ability.DataAbilityHelper' - module + namespace + type

    Returns:
        str: JSON-formatted validation result.

    Examples:
        - Validate a function: api_path='@ohos.accessibility.isOpenAccessibility'
        - Validate an interface: api_path='@hms.ai.face.faceDetector.VisionInfo'
        - Validate a module: api_path='@ohos.ability.ability'
    '''
    try:
        parser = get_parser()
        result = parser.validate_api(params.api_path)

        await ctx.log_info(f"Validated API: {params.api_path}", {"valid": result.get("valid", False)})

        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        error_result = {
            "valid": False,
            "api": params.api_path,
            "error": str(e)
        }
        return json.dumps(error_result, indent=2, ensure_ascii=False)


@mcp.tool(
    name="search_arkts_apis",
    annotations={
        "title": "Search ArkTS APIs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def search_arkts_apis(params: SearchApisInput, ctx: Context) -> str:
    '''
    Search for ArkTS APIs in the HarmonyOS SDK.

    This tool searches through all indexed API declarations to find matching
    APIs based on a query string. Useful for discovering available APIs when
    you're not sure of the exact path.

    Args:
        params (SearchApisInput): Validated input parameters containing:
            - query (str): Search query for API names (min 1 character)
            - sdk_type (SdkType): SDK type to search - 'hms', 'openharmony', or 'all' (default: 'all')
            - limit (int): Maximum results to return, 1-100 (default: 50)

    Returns:
        str: JSON-formatted search results.

    Examples:
        - Search for image APIs: query='Image', sdk_type='all'
        - Search for create functions: query='create'
        - Search in HMS only: query='Detector', sdk_type='hms'
    '''
    try:
        parser = get_parser()
        results = parser.search_apis(
            query=params.query,
            sdk_type=params.sdk_type,
            limit=params.limit
        )

        response = {
            "query": params.query,
            "sdk_type": params.sdk_type.value,
            "count": len(results),
            "results": results
        }

        await ctx.log_info(f"API search: '{params.query}' returned {len(results)} results")

        return json.dumps(response, indent=2, ensure_ascii=False)

    except Exception as e:
        error_result = {
            "query": params.query,
            "error": str(e)
        }
        return json.dumps(error_result, indent=2, ensure_ascii=False)


@mcp.tool(
    name="list_arkts_modules",
    annotations={
        "title": "List ArkTS Modules",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_arkts_modules(params: ListModulesInput, ctx: Context) -> str:
    '''
    List all available ArkTS modules in the HarmonyOS SDK.

    This tool returns a list of all indexed module names, which can be used
    to understand what SDK modules are available for import.

    Args:
        params (ListModulesInput): Validated input parameters containing:
            - sdk_type (SdkType): SDK type to list - 'hms', 'openharmony', or 'all' (default: 'all')

    Returns:
        str: JSON-formatted list of modules.

    Examples:
        - List all modules: sdk_type='all'
        - List OpenHarmony only: sdk_type='openharmony'
        - List HMS only: sdk_type='hms'
    '''
    try:
        parser = get_parser()
        modules = parser.list_modules(sdk_type=params.sdk_type)

        response = {
            "sdk_type": params.sdk_type.value,
            "count": len(modules),
            "modules": modules
        }

        await ctx.log_info(f"Listed {len(modules)} modules for {params.sdk_type.value}")

        return json.dumps(response, indent=2, ensure_ascii=False)

    except Exception as e:
        error_result = {
            "sdk_type": params.sdk_type.value,
            "error": str(e)
        }
        return json.dumps(error_result, indent=2, ensure_ascii=False)


@mcp.resource("config://sdk-path")
async def get_sdk_path() -> str:
    '''Get the current SDK path configuration.'''
    sdk_path = os.environ.get(SDK_PATH_ENV, DEFAULT_SDK_PATH)
    return json.dumps({
        "env_var": SDK_PATH_ENV,
        "current_path": sdk_path,
        "default_path": DEFAULT_SDK_PATH
    }, indent=2)
