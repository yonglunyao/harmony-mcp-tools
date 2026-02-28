# 配置说明

## pip 安装方式（推荐）

使用 `pip install -e .` 安装后，配置非常简单：

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

**优点**:
- ✅ 无需硬编码项目路径
- ✅ 移动项目无需修改配置
- ✅ Python 自动定位模块

---

## 绝对路径方式（不推荐）

如果不方便使用 pip 安装，可以使用绝对路径：

```json
{
  "mcpServers": {
    "arkts-api-validator": {
      "command": "python",
      "args": ["-m", "arkts_api_validator"],
      "cwd": "{PROJECT_PATH}/arkts-api-validator",
      "env": {
        "PYTHONPATH": "{PROJECT_PATH}/arkts-api-validator/src",
        "HARMONYOS_SDK_PATH": "{DEV_ECO_SDK_PATH}"
      }
    }
  }
}
```

**缺点**:
- ❌ 硬编码了绝对路径
- ❌ 移动项目需要更新配置

> **注意**: 请将 `{PROJECT_PATH}` 替换为你的实际项目路径，将 `{DEV_ECO_SDK_PATH}` 替换为 DevEco Studio SDK 路径。

---

## SDK 路径配置

`HARMONYOS_SDK_PATH` 默认值为 `C:\Program Files\Huawei\DevEco Studio\sdk\default`。

如果你的 SDK 安装在其他位置，需要修改此路径，或者使用环境变量：

**Windows PowerShell**:
```powershell
[System.Environment]::SetEnvironmentVariable("HARMONYOS_SDK_PATH", "你的SDK路径", "User")
```

**配置文件**:
```json
{
  "env": {
    "HARMONYOS_SDK_PATH": "${HARMONYOS_SDK_PATH}"
  }
}
```

---

## 配置文件位置

| 操作系统 | 配置文件位置 |
|----------|--------------|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |
