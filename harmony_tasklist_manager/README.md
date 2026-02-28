# HarmonyOS Task List Manager

一个用于管理 HarmonyOS 应用安全分析任务列表的 MCP 服务器。

## 功能特性

- 查询所有任务列表（支持分页）
- 多字段模糊搜索（支持列表字段如 risk_tags）
- 按任务ID精确查询
- 获取字段元数据（含中文描述）
- 多条件精确过滤
- 统计数据
- 可配置的数据文件路径
- 动态字段扩展（通过 title.txt）

## 系统要求

- **Python 3.11+** (推荐 3.11 或更高版本以避免依赖兼容性问题)
- pip

## 安装

```bash
pip install -r requirements.txt
```

## 配置

### 配置文件 (config.yaml)

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

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `HARMONY_TASKLIST_CONFIG` | 配置文件路径 | `./config.yaml` |
| `HARMONY_DATA_FILE` | 数据文件路径 | `data/tasklist.txt` |
| `HARMONY_TITLE_FILE` | 标题文件路径 | `data/title.txt` |
| `HARMONY_LOG_LEVEL` | 日志级别 | `INFO` |

参考 `.env.example` 创建环境变量文件。

## 数据格式

### title.txt（3行，tab 分割）

```
responsible_person	app_name	package_name	...
负责分析这个应用的人	应用名	包名	...
责任人	应用名	包名	...
```

- 第 1 行: 英文列名（代码中的字段键）
- 第 2 行: 中文全称（AI 理解用）
- 第 3 行: 中文简称（UI 显示用）

### tasklist.txt（无表头，tab 分割）

```
UserA	AppA	com.example.app1	1.1.31	...
UserB	AppB	com.example.app2	96.0.0.119	...
```

### 特殊字段处理

**risk_tags** 会自动拆分为数组：

```json
{
  "risk_tags": ["机检恶意", "工信部通报", "ACL"],
  "risk_tags_original": "机检恶意/工信部通报/ACL"
}
```

## 运行

### 启动 MCP 服务器

```bash
python -m src.main
```

### 测试核心功能

```bash
python test_core.py
```

## MCP 工具

| 工具名 | 描述 |
|--------|------|
| `get_all_tasks` | 获取所有任务列表 |
| `search_tasks` | 多字段模糊搜索 |
| `get_task_by_id` | 根据任务ID获取单个任务 |
| `get_field_metadata` | 获取字段元数据 |
| `filter_tasks` | 多条件精确过滤 |
| `get_statistics` | 获取统计数据 |
| `get_server_config` | 获取服务器配置 |
| `reload_data` | 强制重新加载数据 |

### 使用示例

```python
# 获取所有任务
get_all_tasks(limit=10, offset=0)

# 搜索任务
search_tasks(query="机检恶意", limit=5)

# 过滤任务
filter_tasks(filters={"auto_detection_result": "BLACK"})

# 获取字段元数据
get_field_metadata()
```

## Claude Desktop 配置

在 Claude Desktop 配置文件中添加：

```json
{
  "mcpServers": {
    "harmony-tasklist": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "D:\\mcp-servers\\harmony-tasklist-manager"
    }
  }
}
```

## 项目结构

```
harmony-tasklist-manager/
├── src/
│   ├── __init__.py
│   ├── main.py                 # MCP 服务器入口
│   ├── config.py               # 配置管理
│   ├── models.py               # 数据模型
│   ├── parsers.py              # 数据解析器
│   ├── search.py               # 搜索功能
│   └── tools/
│       ├── __init__.py
│       ├── query_tools.py      # 查询类工具
│       └── config_tools.py     # 配置类工具
├── data/
│   ├── title.txt               # 字段定义 (3行)
│   └── tasklist.txt            # 任务数据
├── docs/
│   └── design.md               # 设计文档
├── tests/
│   └── fixtures/
├── pyproject.toml
├── config.yaml
├── requirements.txt
├── README.md
├── .env.example
└── test_core.py                # 核心功能测试
```

## 扩展字段

新增字段时只需修改数据文件，无需改代码：

1. 在 `title.txt` 中添加新列（3 行都要添加）
2. 在 `tasklist.txt` 中为每条数据添加对应值

## 文档

详细设计文档请查看 [docs/design.md](docs/design.md)
