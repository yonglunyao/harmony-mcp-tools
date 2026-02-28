# ArkTS API Validator MCP Server

> 为 Claude Code 提供 HarmonyOS ArkTS API 校验能力的 MCP 服务器

一个用于校验 HarmonyOS ArkTS API 是否可用的 MCP (Model Context Protocol) 服务器。通过解析 HarmonyOS SDK 中的 `.d.ts` 和 `.d.ets` 声明文件，帮助 Claude Code 在编写 ArkTS 代码时避免使用不存在的 API，防止编译错误。

## 功能特性

| 功能 | 说明 |
|------|------|
| **API 校验** | 验证完整的 API 路径是否存在于 SDK 中 |
| **API 搜索** | 根据关键词搜索可用的 API |
| **模块列表** | 列出所有可用的模块 |
| **双 SDK 支持** | 同时支持 HMS SDK 和 OpenHarmony SDK |
| **命名空间支持** | 完整解析命名空间内的函数、接口等声明 |
| **智能建议** | 当 API 不存在时，自动提供相似的 API 建议（模糊匹配） |

## 索引覆盖

- **OpenHarmony SDK**: 664 个模块，6,164 个 API 声明
- **HMS SDK**: 164 个模块，2,365 个 API 声明
- **总计**: 828 个模块，8,529 个 API 声明

## 快速开始

### 1. 安装

```bash
cd D:\mcp-servers\arkts-api-validator
pip install -e .
```

### 2. 配置 Claude Code

编辑 Claude Code 配置文件：

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

添加以下配置：

```json
{
  "mcpServers": {
    "arkts-api-validator": {
      "command": "python",
      "args": ["-m", "arkts_api_validator"],
      "cwd": "D:\\mcp-servers\\arkts-api-validator",
      "env": {
        "PYTHONPATH": "D:\\mcp-servers\\arkts-api-validator\\src",
        "HARMONYOS_SDK_PATH": "C:\\Program Files\\Huawei\\DevEco Studio\\sdk\\default"
      }
    }
  }
}
```

> **重要**:
> - 请将 `D:\\mcp-servers\\arkts-api-validator` 替换为你的实际项目路径
> - `PYTHONPATH` 必须指向 `src` 目录
> - 完整配置示例请参考 `examples/claude_desktop_config.json`

### 3. 重启 Claude Code

配置完成后，重启 Claude Code 即可使用。

## 使用示例

### 场景 1: 校验 API 是否存在

```
User: 检查 @ohos.multimedia.image.ImageSource 是否存在

Claude: 让我使用 validate_arkts_api 工具检查...

工具调用: validate_arkts_api(api_path="@ohos.multimedia.image.ImageSource")

结果: API 存在，位于 @ohos.multimedia.image 模块中，类型为 class
```

### 场景 2: API 拼写错误时的智能建议

```
User: 使用 @ohos.accessibilty.isOpenAccessibility (拼写错误)

Claude: 我注意到 API 路径可能有拼写错误。让我检查...

工具调用: validate_arkts_api(api_path="@ohos.accessibilty.isOpenAccessibility")

结果:
{
  "valid": false,
  "suggestions": [
    {"suggested_api": "@ohos.accessibility", "similarity": 0.96},
    {"suggested_api": "@ohos.accessibility.isOpenAccessibility", "similarity": 0.91}
  ]
}

建议: 您可能想使用 @ohos.accessibility.isOpenAccessibility
```

### 场景 3: 搜索相关 API

```
User: 我需要一个图像处理相关的 API

Claude: 让我搜索图像相关的 API...

工具调用: search_arkts_apis(query="Image", limit=10)

结果: 找到了多个图像相关的 API：
- @ohos.multimedia.image.ImageSource (class)
- @ohos.multimedia.image.createImageSource (function)
- @ohos.multimedia.image.PixelMap (class)
- @ohos.multimedia.image.ImagePacker (class)
...
```

## API 参考

### validate_arkts_api

校验 API 是否存在于 SDK 中。

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `api_path` | string | 是 | 完整的 API 路径，以 `@` 开头 |

**示例**:
```typescript
validate_arkts_api(api_path="@ohos.accessibility.isOpenAccessibility")
validate_arkts_api(api_path="@hms.ai.face.faceDetector.VisionInfo")
validate_arkts_api(api_path="@ohos.ability.ability")
```

**响应格式**:
```json
{
  "valid": true,
  "api": "@ohos.accessibility.isOpenAccessibility",
  "result": {
    "sdk_type": "openharmony",
    "match_type": "function",
    "module": "ohos.accessibility",
    "display_name": "isOpenAccessibility",
    "kind": "function",
    "file": "C:\\...\\@ohos.accessibility.d.ts"
  }
}
```

### search_arkts_apis

搜索可用的 API。

**参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | 是 | - | 搜索关键词 |
| `sdk_type` | string | 否 | "all" | SDK 类型: "hms", "openharmony", "all" |
| `limit` | number | 否 | 50 | 最大返回结果数 (1-100) |

**示例**:
```typescript
search_arkts_apis(query="Image", sdk_type="all", limit=20)
search_arkts_apis(query="create")
search_arkts_apis(query="Detector", sdk_type="hms")
```

### list_arkts_modules

列出所有可用的模块。

**参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `sdk_type` | string | 否 | "all" | SDK 类型: "hms", "openharmony", "all" |

**示例**:
```typescript
list_arkts_modules(sdk_type="all")
list_arkts_modules(sdk_type="openharmony")
```

## API 路径格式

```
@{sdk}.{module}[.{declaration}[.{nested_declaration}]]

组成部分:
├── sdk: ohos (OpenHarmony) 或 hms (HMS)
├── module: 模块名 (如: accessibility, multimedia.image)
└── declaration: 声明名 (可选，如: isOpenAccessibility, ImageSource)
```

**常用路径示例**:

| 路径 | 说明 | SDK 类型 |
|------|------|----------|
| `@ohos.accessibility` | accessibility 模块 | OpenHarmony |
| `@ohos.accessibility.isOpenAccessibility` | 模块函数 | OpenHarmony |
| `@ohos.accessibility.AccessibilityAbilityInfo` | 模块接口 | OpenHarmony |
| `@ohos.multimedia.image.ImageSource` | 嵌套模块中的类 | OpenHarmony |
| `@hms.ai.face.faceDetector` | HMS AI 模块 | HMS |
| `@hms.ai.face.faceDetector.VisionInfo` | HMS 模块接口 | HMS |

## 环境配置

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HARMONYOS_SDK_PATH` | HarmonyOS SDK 路径 | `C:\Program Files\Huawei\DevEco Studio\sdk\default` |

### SDK 目录要求

```
{HARMONYOS_SDK_PATH}/
├── openharmony/
│   └── ets/
│       └── api/
│           ├── @ohos.ability.ability.d.ts
│           ├── @ohos.accessibility.d.ts
│           └── ...
└── hms/
    └── ets/
        └── api/
            ├── @hms.ai.face.faceDetector.d.ts
            └── ...
```

## 开发指南

### 项目结构

```
arkts-api-validator/
├── src/
│   └── arkts_api_validator/
│       ├── __init__.py           # 包导出
│       ├── __main__.py           # 入口点
│       ├── core.py               # 核心解析器
│       └── server.py             # MCP 服务器
├── tests/
│   ├── test_validator.py         # 功能测试
│   └── test_fuzzy_match.py      # 模糊匹配测试
├── examples/
│   └── claude_desktop_config.json  # 配置示例
├── README.md
├── pyproject.toml
└── requirements.txt
```

### 运行测试

```bash
# 验证器测试
python tests/test_validator.py

# 模糊匹配测试
python tests/test_fuzzy_match.py

# MCP Inspector 测试
npx @modelcontextprotocol/inspector "python -m arkts_api_validator"
```

### 作为模块使用

```python
from arkts_api_validator import ArktsApiParser, SdkType

# 创建解析器
parser = ArktsApiParser("path/to/sdk")

# 构建索引
parser.build_index()

# 校验 API
result = parser.validate_api("@ohos.accessibility.isOpenAccessibility")

# 搜索 API
results = parser.search_apis("Image", sdk_type=SdkType.ALL)

# 列出模块
modules = parser.list_modules(SdkType.OPENHARMONY)
```

## 故障排除

### SDK 目录未找到

**症状**: `Warning: API directory not found: ...`

**解决方案**:
1. 确认 SDK 路径正确
2. 检查 `openharmony/ets/api` 和 `hms/ets/api` 目录是否存在
3. 确认环境变量 `HARMONYOS_SDK_PATH` 已设置

### Claude Code 无法连接

**症状**: MCP 服务器未出现在 Claude Code 中

**解决方案**:
1. 确认 Python 已安装并在 PATH 中
2. 检查配置文件路径是否正确
3. 确认 `cwd` 参数指向项目根目录
4. 查看 Claude Code 日志: `帮助 > 打开日志文件夹`

### API 校验结果不准确

**可能原因**:
1. SDK 版本差异
2. 声明文件格式特殊

**解决方案**:
1. 确认 SDK 版本与声明文件匹配
2. 提交 Issue 并附上具体的 API 路径和错误信息

## 解析能力说明

### 支持的声明类型

| 类型 | 关键字 | 示例 |
|------|--------|------|
| 命名空间 | `declare namespace` | `namespace accessibility { ... }` |
| 接口 | `interface` | `interface VisionInfo { ... }` |
| 类 | `class` | `class ImageSource { ... }` |
| 函数 | `function` | `function isOpenAccessibility(): boolean` |
| 类型别名 | `type` | `type AbilityType = string` |
| 枚举 | `enum` | `enum FaceBlock { ... }` |
| 导出类型 | `export type` | `export type DataAbilityHelper` |

### 智能建议

- **算法**: 基于 Python `difflib.SequenceMatcher`
- **相似度阈值**: 0.5 (50%)
- **返回数量**: 最多 5 个建议
- **匹配范围**: 模块名和声明名

## 性能指标

| 指标 | 数值 |
|------|------|
| 首次索引时间 | ~3-5 秒 |
| 内存占用 | ~50 MB |
| 查询响应时间 | <10 ms |
| 索引文件数 | 1,470 个 (.d.ts + .d.ets) |

## 版本历史

- **v1.1.0**: 添加命名空间内函数支持、模糊匹配建议
- **v1.0.0**: 初始版本

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 相关链接

- [MCP 协议规范](https://modelcontextprotocol.io)
- [HarmonyOS 官方文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5)
- [DevEco Studio 下载](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/ide-download-V5)
