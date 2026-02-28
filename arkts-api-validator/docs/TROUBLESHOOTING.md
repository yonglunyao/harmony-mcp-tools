# 故障排除指南

本文档提供了 ArkTS API Validator MCP Server 的常见问题和解决方案。

## 目录

- [安装问题](#安装问题)
- [配置问题](#配置问题)
- [运行问题](#运行问题)
- [API 校验问题](#api-校验问题)
- [性能问题](#性能问题)

---

## 安装问题

### 依赖安装失败

**症状**:
```
ERROR: Could not find a version that satisfies the requirement mcp
```

**解决方案**:
```bash
# 升级 pip
python -m pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### Python 版本不兼容

**症状**:
```
SyntaxError: invalid syntax (Python 2.x)
```

**解决方案**:
- 确保使用 Python 3.10 或更高版本
- 检查 Python 版本: `python --version`

---

## 配置问题

### Claude Code 无法识别 MCP 服务器

**症状**: 配置后 Claude Code 中看不到 MCP 服务器

**检查步骤**:

1. **验证配置文件位置**:
   ```bash
   # Windows
   echo %APPDATA%\Claude\claude_desktop_config.json

   # macOS
   echo ~/Library/Application Support/Claude/claude_desktop_config.json

   # Linux
   echo ~/.config/Claude/claude_desktop_config.json
   ```

2. **验证 JSON 格式**:
   ```bash
   # 使用 Python 验证 JSON
   python -m json.tool %APPDATA%\Claude\claude_desktop_config.json
   ```

3. **验证 Python 路径**:
   ```bash
   # 检查 Python 是否在 PATH 中
   where python

   # 如果不在，添加到 PATH 或使用完整路径
   "command": "C:\\Python311\\python.exe"
   ```

4. **验证工作目录**:
   - 确保 `cwd` 指向项目根目录
   - 路径使用双反斜杠 `\\` 或正斜杠 `/`

---

### SDK 路径未找到

**症状**:
```
Warning: API directory not found: C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\ets\api
```

**解决方案**:

1. **确认 SDK 安装路径**:
   ```bash
   # Windows 默认路径
   C:\Program Files\Huawei\DevEco Studio\sdk\default

   # 检查目录是否存在
   dir "C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\ets\api"
   dir "C:\Program Files\Huawei\DevEco Studio\sdk\default\hms\ets\api"
   ```

2. **设置正确的环境变量**:
   ```powershell
   # PowerShell
   $env:HARMONYOS_SDK_PATH = "C:\Program Files\Huawei\DevEco Studio\sdk\default"

   # CMD
   set HARMONYOS_SDK_PATH=C:\Program Files\Huawei\DevEco Studio\sdk\default
   ```

3. **在配置文件中设置**:
   ```json
   {
     "env": {
       "HARMONYOS_SDK_PATH": "你的SDK路径"
     }
   }
   ```

---

## 运行问题

### 模块导入错误

**症状**:
```
ModuleNotFoundError: No module named 'arkts_api_validator'
```

**解决方案**:
```bash
# 方法 1: 从项目根目录运行
cd D:\mcp-servers\arkts-api-validator
python -m arkts_api_validator

# 方法 2: 添加 src 到 PYTHONPATH
set PYTHONPATH=D:\mcp-servers\arkts-api-validator\src;%PYTHONPATH%

# 方法 3: 使用完整路径
python D:\mcp-servers\arkts-api-validator\src\arkts_api_validator\__main__.py
```

---

### MCP Inspector 连接失败

**症状**:
```
Error: Failed to connect to MCP server
```

**解决方案**:
```bash
# 方法 1: 直接运行测试
python -m arkts_api_validator

# 方法 2: 使用 Inspector 测试
npx @modelcontextprotocol/inspector "python -m arkts_api_validator"

# 方法 3: 检查端口占用
netstat -an | findstr LISTENING
```

---

## API 校验问题

### API 校验结果不准确

**症状**: 存在的 API 显示为不存在，或不存在的 API 显示为存在

**可能原因**:
1. SDK 版本不匹配
2. 索引未正确构建
3. 声明文件格式特殊

**解决方案**:

1. **重新构建索引**:
   ```bash
   # 删除缓存后重启
   del %TEMP%\arkts_cache*
   ```

2. **验证声明文件**:
   ```bash
   # 检查文件是否存在
   dir "C:\...\openharmony\ets\api\@ohos.accessibility.d.ts"
   ```

3. **提交 Issue**:
   - 提供 API 路径
   - 提供 SDK 版本信息
   - 提供错误日志

---

### 命名空间内的 API 未找到

**症状**:
```
@ohos.accessibility.isOpenAccessibility 显示不存在
```

**状态**: v1.1.0+ 已支持命名空间内函数

**解决方案**:
- 确保使用最新版本
- 检查 API 路径格式是否正确

---

## 性能问题

### 首次调用缓慢

**症状**: 第一次调用工具需要 3-5 秒

**原因**: 需要构建 API 索引

**状态**: 正常行为，后续调用会很快

### 内存占用较高

**症状**: 进程占用约 50-100 MB 内存

**原因**: 保存了完整的 API 索引

**状态**: 正常行为，索引数据缓存在内存中

---

## 日志调试

### 启用详细日志

```bash
# 设置环境变量
set ARKTS_DEBUG=1

# 运行服务器
python -m arkts_api_validator
```

### 查看 Claude Code 日志

```
帮助 > 打开日志文件夹 > mcp-server-logs
```

---

## 常见错误消息

| 错误消息 | 原因 | 解决方案 |
|----------|------|----------|
| `API path must start with '@'` | 路径缺少 `@` 前缀 | 添加 `@` 前缀 |
| `Invalid API path format` | 路径格式错误 | 确保格式为 `@{sdk}.{module}` |
| `Unknown SDK prefix: 'xxx'` | SDK 前缀无效 | 使用 `ohos` 或 `hms` |
| `Module not found` | 模块不存在 | 使用 search_arkts_apis 搜索 |
| `Python not found` | Python 未安装或不在 PATH | 安装 Python 或使用完整路径 |

---

## 获取帮助

### 检查系统信息

```bash
# 收集诊断信息
python --version
pip list | findstr mcp
pip list | findstr pydantic
echo %HARMONYOS_SDK_PATH%
```

### 提交 Issue

提交 Issue 时请包含:

1. **系统信息**:
   - 操作系统版本
   - Python 版本
   - Claude Code 版本

2. **错误信息**:
   - 完整的错误消息
   - 复现步骤
   - 预期行为 vs 实际行为

3. **配置信息**:
   - SDK 路径
   - MCP 配置（脱敏后）
   - 环境变量

### 有用的资源

- [MCP 协议文档](https://modelcontextprotocol.io)
- [HarmonyOS 开发者文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5)
- [GitHub Issues](https://github.com/anthropics/claude-code/issues)
