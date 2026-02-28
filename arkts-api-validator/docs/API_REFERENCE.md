# API 参考文档

本文档提供了 ArkTS API Validator MCP Server 的完整 API 参考。

## 目录

- [工具 (Tools)](#工具-tools)
  - [validate_arkts_api](#validate_arkts_api)
  - [search_arkts_apis](#search_arkts_apis)
  - [list_arkts_modules](#list_arkts_modules)
- [资源 (Resources)](#资源-resources)
- [数据模型 (Data Models)](#数据模型-data-models)

---

## 工具 (Tools)

### validate_arkts_api

校验 ArkTS API 是否存在于 HarmonyOS SDK 中。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| `api_path` | string | 是 | - | 最小长度 3 | 完整的 API 路径，必须以 `@` 开头 |

#### 参数验证规则

- 必须以 `@` 字符开头
- 必须包含至少一个 `.` 分隔符
- 格式: `@{sdk}.{module}[.{declaration}]`
- SDK 必须是 `ohos` 或 `hms`

#### 返回值

**成功响应** (API 存在):

```typescript
{
  valid: true,
  api: string,                    // 验证的 API 路径
  result: {
    sdk_type: "hms" | "openharmony",
    found: true,
    match_type: "module" | "interface" | "class" | "function" | "type" | "enum",
    module: string,              // 模块名 (如: "ohos.accessibility")
    name?: string,               // 声明完整名称 (如: "accessibility.isOpenAccessibility")
    display_name?: string,       // 显示名称 (如: "isOpenAccessibility")
    kind: string,                // 声明类型
    file: string                 // 源文件路径
  }
}
```

**失败响应** (API 不存在):

```typescript
{
  valid: false,
  api: string,                   // 查询的 API 路径
  results: Array<{
    sdk_type: "hms" | "openharmony",
    found: false,
    reason: string              // 未找到的原因
  }>,
  suggestions?: Array<{         // 相似 API 建议（最多 5 个）
    sdk_type: string,
    module: string,
    match_type: string,
    name?: string,
    similarity: number,         // 相似度 (0-1)
    suggested_api: string       // 建议的 API 路径
  }>
}
```

**错误响应**:

```typescript
{
  valid: false,
  api: string,
  error: string                 // 错误信息
}
```

#### 使用示例

```typescript
// 校验模块
validate_arkts_api({ api_path: "@ohos.accessibility" })
// { valid: true, result: { match_type: "module", ... } }

// 校验函数
validate_arkts_api({ api_path: "@ohos.accessibility.isOpenAccessibility" })
// { valid: true, result: { match_type: "function", ... } }

// 校验接口
validate_arkts_api({ api_path: "@hms.ai.face.faceDetector.VisionInfo" })
// { valid: true, result: { match_type: "interface", ... } }

// 不存在的 API（带建议）
validate_arkts_api({ api_path: "@ohos.accessibilty" })
// { valid: false, suggestions: [{ suggested_api: "@ohos.accessibility", similarity: 0.96 }] }
```

#### 注解

```typescript
{
  title: "Validate ArkTS API",
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false
}
```

---

### search_arkts_apis

在 HarmonyOS SDK 中搜索匹配的 ArkTS API。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| `query` | string | 是 | - | 最小长度 1 | 搜索关键词 |
| `sdk_type` | string | 否 | "all" | 枚举值 | SDK 类型: "hms", "openharmony", "all" |
| `limit` | number | 否 | 50 | 1-100 | 最大返回结果数 |

#### 返回值

```typescript
{
  query: string,                 // 搜索关键词
  sdk_type: string,              // 使用的 SDK 类型
  count: number,                 // 结果数量
  results: Array<{
    sdk_type: string,
    module: string,              // 模块名
    match_type: string,          // 匹配类型
    name?: string,               // 声明名称
    kind: string,                // 声明类型
    file: string                 // 源文件路径
  }>
}
```

#### 使用示例

```typescript
// 搜索所有图像相关 API
search_arkts_apis({ query: "Image", sdk_type: "all", limit: 20 })

// 仅在 HMS 中搜索
search_arkts_apis({ query: "Detector", sdk_type: "hms" })

// 搜索包含 "create" 的函数
search_arkts_apis({ query: "create" })
```

#### 注解

```typescript
{
  title: "Search ArkTS APIs",
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false
}
```

---

### list_arkts_modules

列出 HarmonyOS SDK 中所有可用的模块。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| `sdk_type` | string | 否 | "all" | 枚举值 | SDK 类型: "hms", "openharmony", "all" |

#### 返回值

```typescript
{
  sdk_type: string,              // "hms", "openharmony", 或 "all"
  count: number,                 // 模块总数
  modules: string[]              // 模块列表 (按字母排序)
}
```

#### 使用示例

```typescript
// 列出所有模块
list_arkts_modules({ sdk_type: "all" })
// { count: 828, modules: ["@hms.ai.AICaption", "@ohos.AbilityDelegator", ...] }

// 仅列出 OpenHarmony 模块
list_arkts_modules({ sdk_type: "openharmony" })
// { count: 664, modules: ["@ohos.AbilityDelegator", "@ohos.AbilityInfo", ...] }

// 仅列出 HMS 模块
list_arkts_modules({ sdk_type: "hms" })
// { count: 164, modules: ["@hms.hms.ai.AICaption", ...] }
```

#### 注解

```typescript
{
  title: "List ArkTS Modules",
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false
}
```

---

## 资源 (Resources)

### config://sdk-path

获取当前 SDK 路径配置。

#### 返回值

```typescript
{
  env_var: string,                // 环境变量名
  current_path: string,           // 当前配置的路径
  default_path: string            // 默认路径
}
```

#### 使用示例

```typescript
// 获取 SDK 配置
// 返回: { env_var: "HARMONYOS_SDK_PATH", current_path: "C:\\...", default_path: "C:\\..." }
```

---

## 数据模型 (Data Models)

### SdkType

HarmonyOS SDK 类型枚举。

| 值 | 说明 |
|-----|------|
| `hms` | 华为 HMS SDK |
| `openharmony` | OpenHarmony SDK |
| `all` | 所有 SDK (用于搜索/列表操作) |

### MatchType

API 声明类型。

| 值 | 说明 | 示例 |
|-----|------|------|
| `module` | 模块 | `@ohos.accessibility` |
| `namespace` | 命名空间 | `accessibility` |
| `interface` | 接口 | `VisionInfo` |
| `class` | 类 | `ImageSource` |
| `function` | 函数 | `isOpenAccessibilitySync` |
| `type` | 类型别名 | `AbilityType` |
| `enum` | 枚举 | `FaceBlock` |

### 相似度阈值

模糊匹配功能使用的相似度阈值：

| 阈值 | 说明 |
|------|------|
| `≥ 0.9` | 极高相似度（可能是大小写错误） |
| `≥ 0.7` | 高相似度（可能是轻微拼写错误） |
| `≥ 0.5` | 中等相似度（可能是部分匹配） |
| `< 0.5` | 低相似度（不作为建议返回） |

---

## 错误码

| 错误 | 说明 | 解决方案 |
|------|------|----------|
| `API path must start with '@'` | API 路径必须以 `@` 开头 | 添加 `@` 前缀 |
| `Invalid API path format` | API 路径格式无效 | 确保格式为 `@{sdk}.{module}` |
| `Unknown SDK prefix` | 未知的 SDK 前缀 | 使用 `ohos` 或 `hms` |
| `SDK directory not found` | SDK 目录未找到 | 检查 `HARMONYOS_SDK_PATH` 环境变量 |

---

## 性能说明

| 操作 | 首次调用 | 后续调用 |
|------|----------|----------|
| validate_arkts_api | ~3-5 秒 (索引构建) | <10 ms |
| search_arkts_apis | ~3-5 秒 (索引构建) | <50 ms |
| list_arkts_modules | ~3-5 秒 (索引构建) | <20 ms |

> 注：索引在首次调用时构建，后续调用使用缓存的索引。

---

## 版本兼容性

| SDK 版本 | 支持状态 | 说明 |
|----------|----------|------|
| HarmonyOS NEXT (API 12+) | ✅ 完全支持 | 声明格式标准 |
| HarmonyOS 4.0 (API 10-11) | ✅ 完全支持 | 声明格式标准 |
| HarmonyOS 3.x (API 9) | ⚠️ 部分支持 | 某些新特性可能不支持 |
| 更早版本 | ⚠️ 可能不支持 | 声明格式可能有差异 |
