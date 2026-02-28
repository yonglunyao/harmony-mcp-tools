# HarmonyOS Task List Manager - 设计文档

## 1. 概述

HarmonyOS Task List Manager 是一个 MCP (Model Context Protocol) 服务器，用于管理 HarmonyOS 应用安全分析任务列表。该系统提供任务查询、搜索、过滤和统计功能。

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Client (AI Assistant)              │
└────────────────────────────┬────────────────────────────────────┘
                             │ stdio
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastMCP Server (main.py)                     │
├─────────────────────────────────────────────────────────────────┤
│  Tools Layer                                                    │
│  ├── get_all_tasks        ├── filter_tasks                     │
│  ├── search_tasks         ├── get_statistics                   │
│  ├── get_task_by_id       ├── get_server_config                │
│  └── get_field_metadata   └── reload_data                      │
├─────────────────────────────────────────────────────────────────┤
│  Business Logic Layer                                            │
│  ├── DataManager (缓存管理)                                      │
│  ├── TaskSearcher (模糊搜索)                                     │
│  └── AdvancedSearcher (高级过滤)                                 │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                      │
│  ├── Config (配置管理)    ├── parsers.py (数据解析)             │
│  └── models.py (数据模型)                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Data Files                                                     │
│  ├── data/title.txt       (字段定义, 3行, tab分割)               │
│  └── data/tasklist.txt    (任务数据, tab分割)                    │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 数据格式

### 3.1 title.txt 格式

```
responsible_person	app_name	package_name	...
负责分析这个应用的人	应用名	包名	...
责任人	应用名	包名	...
```

- 第 1 行: 英文列名 (用作代码中的字段键)
- 第 2 行: **中文全称描述**（用于 AI 理解字段含义）
- 第 3 行: 中文简称（用于 UI 显示）

### 3.2 tasklist.txt 格式

```
UserA	AppA	com.example.app1	1.1.31	...
UserB	AppB	com.example.app2	96.0.0.119	...
```

- 无表头
- 制表符 (tab) 分割
- 每行代表一个任务

### 3.3 特殊字段处理

#### risk_tags（风险标签）

原始数据用 `/` 分隔的字符串会自动拆分为数组：

```json
{
  "risk_tags": ["机检恶意", "工信部通报", "ACL", "读剪贴板"],
  "risk_tags_original": "机检恶意/工信部通报/ACL/读剪贴板"
}
```

- `risk_tags`: 拆分后的标签数组（便于搜索和统计）
- `risk_tags_original`: 原始字符串（向后兼容）

## 4. MCP 工具列表

### 4.1 get_all_tasks

获取所有任务列表，支持分页。

**参数:**
- `limit` (可选): 返回结果最大数量，默认 100，最大 1000
- `offset` (可选): 分页偏移量，默认 0

**返回:**
```json
{
  "success": true,
  "total": 150,
  "returned": 100,
  "offset": 0,
  "tasks": [...],
  "fields": {
    "responsible_person": {
      "name": "responsible_person",
      "label": "责任人",
      "description": "负责分析这个应用的人"
    }
  }
}
```

### 4.2 search_tasks

多字段模糊搜索，支持列表类型字段（如 risk_tags）。

**参数:**
- `query` (必填): 搜索关键词
- `fields` (可选): 搜索字段列表，默认搜索所有字段
- `case_sensitive` (可选): 是否区分大小写，默认 false
- `limit` (可选): 返回结果最大数量

**返回:**
```json
{
  "success": true,
  "query": "机检恶意",
  "matched_fields": ["risk_tags"],
  "total_matches": 45,
  "returned": 45,
  "tasks": [
    {
      "risk_tags": ["**机检恶意**", "工信部通报", "ACL"],
      "_match_highlights": {
        "risk_tags": ["**机检恶意**"]
      }
    }
  ]
}
```

### 4.3 get_task_by_id

根据任务 ID 获取单个任务。

**参数:**
- `task_id` (必填): 任务 ID

**返回:**
```json
{
  "success": true,
  "task": {...}
}
```

### 4.4 get_field_metadata

获取字段元数据信息，包含字段描述供 AI 理解。

**参数:** 无

**返回:**
```json
{
  "success": true,
  "total_fields": 25,
  "fields": [
    {
      "key": "responsible_person",
      "name": "responsible_person",
      "label": "责任人",
      "description": "负责分析这个应用的人",
      "index": 0
    },
    {
      "key": "risk_tags",
      "name": "risk_tags",
      "label": "风险标签",
      "description": "风险标签",
      "index": 19
    }
  ]
}
```

### 4.5 filter_tasks

根据多个字段条件精确过滤任务，支持列表字段匹配。

**参数:**
- `filters` (必填): 过滤条件对象 `{field: value}`
- `match_mode` (可选): "all" (全部匹配) 或 "any" (任一匹配)，默认 "all"
- `limit` (可选): 返回结果最大数量

**返回:**
```json
{
  "success": true,
  "filters": {"auto_detection_result": "BLACK"},
  "match_mode": "all",
  "total_matches": 12,
  "tasks": [...]
}
```

**列表字段过滤示例:**
- `{"risk_tags": "ACL"}` - 匹配包含 "ACL" 标签的任务

### 4.6 get_statistics

获取任务统计数据。

**参数:**
- `group_by` (可选): 分组字段名

**返回:**
```json
{
  "success": true,
  "statistics": {
    "total_tasks": 150,
    "by_detection_result": {"BLACK": 45, "WHITE": 60, "待定": 45},
    "by_manual_conclusion": {...}
  }
}
```

### 4.7 get_server_config

获取服务器配置信息。

**参数:** 无

**返回:**
```json
{
  "success": true,
  "config": {
    "data_file_path": "data/tasklist.txt",
    "data_file_exists": true,
    "title_file_path": "data/title.txt",
    "title_file_exists": true,
    "encoding": "utf-8",
    "default_limit": 100,
    "max_limit": 1000,
    "cache_ttl_minutes": 5
  }
}
```

### 4.8 reload_data

强制重新加载数据文件（清除缓存）。

**参数:** 无

**返回:**
```json
{
  "success": true,
  "message": "Data reloaded successfully",
  "tasks_loaded": 5,
  "fields_loaded": 25
}
```

## 5. 配置管理

### 5.1 配置文件 (config.yaml)

```yaml
data_files:
  title_file: "data/title.txt"
  data_file: "data/tasklist.txt"

server:
  name: "harmony-tasklist-manager"
  version: "1.0.0"
  log_level: "INFO"

query:
  default_limit: 100
  max_limit: 1000
  cache_ttl_minutes: 5
```

### 5.2 环境变量

| 环境变量 | 描述 |
|----------|------|
| `HARMONY_TASKLIST_CONFIG` | 配置文件路径 |
| `HARMONY_DATA_FILE` | 数据文件路径 |
| `HARMONY_TITLE_FILE` | 标题文件路径 |
| `HARMONY_LOG_LEVEL` | 日志级别 |

### 5.3 配置优先级

1. 环境变量 (最高优先级)
2. 用户配置文件 (config.yaml)
3. 默认配置

## 6. 扩展性设计

### 6.1 动态字段扩展

当需要新增字段时：

1. 在 `title.txt` 中添加新列（**3 行都需要添加**）
2. 在 `tasklist.txt` 中为每条数据添加对应的新列值
3. 无需修改任何代码

**示例：**

```txt
# title.txt 新增列
...	old_field	new_field
...	旧字段	新字段描述
...	旧字段	新字段
```

### 6.2 添加新工具

在 `src/tools/` 下创建新文件并注册工具：

```python
@mcp.tool()
def new_tool(param: str) -> dict:
    """Tool description for AI."""
    # Implementation
    return result
```

## 7. 错误处理

所有错误响应遵循统一格式：

```json
{
  "success": false,
  "error": {
    "type": "ErrorType",
    "message": "Error description",
    "details": {...}
  }
}
```

错误类型：
- `ValidationError`: 参数验证错误
- `DataFileError`: 数据文件错误
- `ParseError`: 数据解析错误
- `InternalError`: 内部服务器错误

## 8. 性能优化

### 8.1 缓存机制

- 字段元数据缓存：启动时加载，永不失效
- 任务数据缓存：默认 5 分钟 TTL
- 可通过 `reload_data` 工具强制刷新

### 8.2 查询优化

- 惰性加载：只在需要时加载数据
- 分页支持：减少大数据集的传输开销
- 限制保护：默认最大返回 1000 条记录

## 9. 安全考虑

- 只读操作：所有工具都是只读的，不会修改数据文件
- 路径验证：检查文件是否存在再读取
- 参数验证：严格验证所有输入参数

## 10. 使用示例

### Python 调用示例

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["-m", "src.main"],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # Initialize
        await session.initialize()

        # Get all tasks
        result = await session.call_tool("get_all_tasks", {"limit": 10})
        print(result)

        # Search tasks
        result = await session.call_tool(
            "search_tasks",
            {"query": "机检恶意", "limit": 5}
        )
        print(result)
```

### Claude Desktop 配置

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "harmony-tasklist": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "{PROJECT_PATH}/harmony-tasklist-manager"
    }
  }
}
```

> 请将 `{PROJECT_PATH}` 替换为你的实际项目路径。

## 11. 数据类型

MCP 工具返回的数据类型为 JSON 可序列化类型：

| 类型 | 说明 | 示例 |
|------|------|------|
| `dict` | 字典/对象 | `{"key": "value"}` |
| `list` | 列表/数组 | `[1, 2, 3]` 或 `["tag1", "tag2"]` |
| `str` | 字符串 | `"hello"` |
| `int` | 整数 | `42` |
| `float` | 浮点数 | `3.14` |
| `bool` | 布尔值 | `true`, `false` |
| `None` | 空值 | `null` |

**注意：** 从文本文件解析的数字通常以字符串形式存储。
