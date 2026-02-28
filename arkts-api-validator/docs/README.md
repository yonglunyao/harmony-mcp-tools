# ArkTS API Validator 文档

欢迎来到 ArkTS API Validator MCP Server 文档中心！

## 文档目录

### 快速开始
- [README.md](../README.md) - 项目介绍、安装和基本使用

### 详细文档
- [使用场景示例](./USAGE_SCENARIOS.md) - 实际开发中的使用场景和对话示例
- [API 参考文档](./API_REFERENCE.md) - 完整的 API 接口说明和数据模型
- [故障排除指南](./TROUBLESHOOTING.md) - 常见问题和解决方案

## 按需查找

### 我想...

- **安装和配置** → [README.md - 快速开始](../README.md#快速开始)
- **了解 API 工具** → [API 参考文档](./API_REFERENCE.md)
- **查看使用示例** → [使用场景示例](./USAGE_SCENARIOS.md)
- **解决配置问题** → [故障排除指南 - 配置问题](./TROUBLESHOOTING.md#配置问题)
- **解决 API 校验问题** → [故障排除指南 - API 校验问题](./TROUBLESHOOTING.md#api-校验问题)

## 核心概念

### API 路径格式

```
@{sdk}.{module}[.{declaration}[.{nested_declaration}]]

示例:
- @ohos.accessibility              ← 模块
- @ohos.accessibility.isOpenAccessibility  ← 函数
- @hms.ai.face.faceDetector.VisionInfo    ← 接口
```

### SDK 类型

| 类型 | 前缀 | 说明 |
|------|------|------|
| OpenHarmony | `@ohos.*` | 开源鸿蒙 SDK |
| HMS | `@hms.*` | 华为 HMS SDK |

### 工具能力

| 工具 | 功能 | 典型用法 |
|------|------|----------|
| `validate_arkts_api` | 校验 API | 编写代码前验证 API 存在性 |
| `search_arkts_apis` | 搜索 API | 发现相关的 API |
| `list_arkts_modules` | 列出模块 | 了解可用的模块 |

## 学习路径

1. **初学者**: [README.md](../README.md) → [使用场景示例](./USAGE_SCENARIOS.md)
2. **API 用户**: [API 参考文档](./API_REFERENCE.md) → [使用场景示例](./USAGE_SCENARIOS.md)
3. **问题排查**: [故障排除指南](./TROUBLESHOOTING.md)

## 版本信息

- **当前版本**: v1.1.0
- **索引覆盖**: 828 模块, 8,529 API 声明
- **支持 SDK**: HarmonyOS NEXT (API 12+)

## 获取帮助

- 提交 [GitHub Issue](https://github.com/anthropics/claude-code/issues)
- 查阅 [MCP 协议文档](https://modelcontextprotocol.io)
- 参考 [HarmonyOS 官方文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5)
