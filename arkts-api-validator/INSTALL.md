# 安装配置指南

本文档提供了配置 ArkTS API Validator MCP Server 的方式。

## 安装

```bash
cd D:\mcp-servers\arkts-api-validator
pip install -e .
```

## 配置 Claude Code

编辑配置文件：

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
      "env": {
        "HARMONYOS_SDK_PATH": "C:\\Program Files\\Huawei\\DevEco Studio\\sdk\\default"
      }
    }
  }
}
```

> **说明**: 使用 `pip install -e .` 安装后，不需要配置 `cwd` 和 `PYTHONPATH`，Python 会自动找到模块。

## SDK 路径配置

`HARMONYOS_SDK_PATH` 可以使用环境变量：

**Windows**:
```powershell
[System.Environment]::SetEnvironmentVariable("HARMONYOS_SDK_PATH", "C:\Program Files\Huawei\DevEco Studio\sdk\default", "User")
```

**配置文件**:
```json
{
  "env": {
    "HARMONYOS_SDK_PATH": "${HARMONYOS_SDK_PATH}"
  }
}
```

## 验证安装

### 1. 测试模块导入

```bash
python -c "from arkts_api_validator import ArktsApiParser; print('OK')"
```

### 2. 测试 MCP 服务器

```bash
# 使用 MCP Inspector 测试
npx @modelcontextprotocol/inspector "python -m arkts_api_validator"
```

### 3. 在 Claude Code 中验证

1. 重启 Claude Code
2. 测试工具是否可用

## 卸载

```bash
pip uninstall arkts-api-validator
```
