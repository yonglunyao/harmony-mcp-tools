# 使用场景示例

本文档展示了 ArkTS API Validator MCP Server 在实际开发中的使用场景。

## 场景 1: 编写鸿蒙应用时验证 API

### 对话示例

```
User: 帮我用 ArkTS 写一个获取辅助功能状态的代码

Claude: 好的，我来帮你编写获取辅助功能状态的代码。

首先，让我检查一下相关的 API 是否存在...

使用工具: validate_arkts_api(api_path="@ohos.accessibility.isOpenAccessibilitySync")

结果:
{
  "valid": true,
  "result": {
    "sdk_type": "openharmony",
    "match_type": "function",
    "module": "ohos.accessibility",
    "display_name": "isOpenAccessibilitySync"
  }
}

API 验证通过！现在我来编写代码：

```typescript
import { accessibility } from '@kit.AccessibilityKit';

// 检查辅助功能是否开启
const isEnabled = accessibility.isOpenAccessibilitySync();
console.log('Accessibility enabled:', isEnabled);
```
```

### 关键点

- Agent 在编写代码前先验证 API
- 避免使用不存在的 API 导致编译错误
- 确保代码可以直接编译通过

---

## 场景 2: API 拼写错误自动纠正

### 对话示例

```
User: 我想使用 accessibilty 模块的功能

Claude: 我注意到你提到的模块名可能有拼写错误。让我搜索一下相关的模块...

使用工具: search_arkts_apis(query="accessibility", limit=5)

结果:
{
  "count": 15,
  "results": [
    {"module": "ohos.accessibility", "match_type": "module"},
    {"name": "isOpenAccessibilitySync", "module": "ohos.accessibility", "match_type": "function"},
    ...
  ]
}

我找到了 `@ohos.accessibility` 模块，这可能是你想要的模块。正确的拼写是 "accessibility"（双写 's'，单写 'i'）。

这个模块提供了以下功能：
- isOpenAccessibilitySync() - 检查辅助功能是否开启
- getAccessibilityExtensionList() - 获取辅助功能列表
- ...
```

### 关键点

- 模糊匹配帮助纠正拼写错误
- 提供相似度评分
- 建议正确的 API 路径

---

## 场景 3: 搜索图像处理相关 API

### 对话示例

```
User: 我需要在鸿蒙应用中处理图像，有什么可用的 API？

Claude: 让我搜索一下鸿蒙 SDK 中图像处理相关的 API...

使用工具: search_arkts_apis(query="Image", sdk_type="openharmony", limit=15)

结果:
{
  "count": 15,
  "results": [
    {
      "module": "ohos.multimedia.image",
      "match_type": "module",
      "name": "ImageSource"
    },
    {
      "module": "ohos.multimedia.image",
      "match_type": "function",
      "name": "createImageSource"
    },
    {
      "module": "ohos.multimedia.image",
      "match_type": "class",
      "name": "PixelMap"
    },
    {
      "module": "ohos.multimedia.image",
      "match_type": "class",
      "name": "ImagePacker"
    },
    ...
  ]
}

鸿蒙提供了丰富的图像处理 API，主要在 `@ohos.multimedia.image` 模块中：

1. **ImageSource** - 图像源类，用于读取和解码图像
2. **PixelMap** - 像素图类，用于图像处理和编辑
3. **ImagePacker** - 图像打包类，用于图像编码
4. **createImageSource()** - 创建图像源的函数

使用示例：

```typescript
import { image } from '@kit.ImageKit';

// 创建图像源
const imageSource = image.createImageSource(buffer);

// 解码为 PixelMap
const pixelMap = await imageSource.createPixelMap();

// 图像处理...
```
```

### 关键点

- 快速发现相关 API
- 按模块分组展示
- 提供使用示例

---

## 场景 4: 使用 HMS AI 能力

### 对话示例

```
User: 我想在鸿蒙应用中添加人脸检测功能，使用 HMS 的能力

Claude: 好的，让我搜索一下 HMS SDK 中的人脸检测 API...

使用工具: search_arkts_apis(query="face", sdk_type="hms", limit=10)

结果:
{
  "count": 8,
  "results": [
    {
      "module": "hms.ai.face.faceDetector",
      "match_type": "module"
    },
    {
      "module": "hms.ai.face.faceDetector",
      "match_type": "class",
      "name": "faceDetector"
    },
    {
      "module": "hms.ai.face.faceComparator",
      "match_type": "module"
    },
    ...
  ]
}

HMS 提供了强大的人脸检测能力！主要 API 在 `@hms.ai.face.faceDetector` 模块中。

让我验证一下具体的使用方式：

使用工具: validate_arkts_api(api_path="@hms.ai.face.faceDetector.VisionInfo")

结果:
{
  "valid": true,
  "result": {
    "sdk_type": "hms",
    "match_type": "interface",
    "name": "VisionInfo",
    "module": "hms.ai.face.faceDetector"
  }
}

API 确认可用！使用示例：

```typescript
import { faceDetector } from '@hms.ai.face.faceDetector';

// 配置检测参数
const visionInfo: faceDetector.VisionInfo = {
  pixelMap: pixelMap
};

// 创建检测器
const detector = new faceDetector.FaceDetector();

// 进行人脸检测
const result = await detector.detect(visionInfo);
console.log('Detected faces:', result.faces);
```
```

### 关键点

- 区分 HMS 和 OpenHarmony SDK
- 验证 API 可用性
- 提供完整的使用示例

---

## 场景 5: 列出所有可用模块

### 对话示例

```
User: 有哪些可用的鸿蒙 API 模块？

Claude: 让我列出所有可用的模块...

使用工具: list_arkts_modules(sdk_type="openharmony")

结果:
{
  "count": 664,
  "modules": [
    "@ohos.ability.ability",
    "@ohos.accessibility",
    "@ohos.account.appAccount",
    "@ohos.ability.featureAbility",
    "@ohos.ability.particleAbility",
    "@ohos.annotation.modifyAnnotation",
    "@ohos.app.ability.Ability",
    "@ohos.app.ability.UIAbility",
    "@ohos.application.AbilityStageContext",
    ...
  ]
}

鸿蒙 SDK 提供了 664 个 OpenHarmony 模块！主要分类包括：

- **能力相关** (@ohos.ability.*)
- **账户管理** (@ohos.account.*)
- **辅助功能** (@ohos.accessibility)
- **应用生命周期** (@ohos.app.ability.*)
- **多媒体** (@ohos.multimedia.*)
- **网络** (@ohos.net.*)
- **数据存储** (@ohos.data.*)
- **UI 组件** (@ohos.arkui.*)
- ...

你想要查看哪个模块的详细 API？

使用工具: list_arkts_modules(sdk_type="hms")

结果:
{
  "count": 164,
  "modules": [
    "@hms.ai.AICaption",
    "@hms.ai.AgentFramework",
    "@hms.ai.face.faceComparator",
    "@hms.ai.face.faceDetector",
    "@hms.ai.insightIntent",
    ...
  ]
}

HMS SDK 提供了 164 个模块！主要分类包括：

- **AI 能力** (@hms.ai.*)
- **计算机视觉** (@hms.ai.vision.*)
- **语音服务** (@hms.speech.*)
- ...
```

### 关键点

- 了解完整的模块列表
- 按类别分组展示
- 方便发现新功能

---

## 场景 6: 验证嵌套模块中的 API

### 对话示例

```
User: 怎么使用 ability 模块中的 DataAbilityHelper？

Claude: 让我检查一下这个 API 的位置...

使用工具: validate_arkts_api(api_path="@ohos.ability.ability.DataAbilityHelper")

结果:
{
  "valid": true,
  "result": {
    "sdk_type": "openharmony",
    "match_type": "interface",
    "module": "ohos.ability.ability",
    "name": "ability.DataAbilityHelper",
    "display_name": "DataAbilityHelper"
  }
}

找到了！`DataAbilityHelper` 位于 `@ohos.ability.ability` 模块的命名空间中。

使用示例：

```typescript
import { ability } from '@kit.AbilityKit';
import { Want } from '@kit.AbilityKit';

// 获取 DataAbilityHelper
const helper = ability.DataAbilityHelper.getDataAbilityHelper(context);

// 插入数据
const values = {
  'name': 'John',
  'age': 30
};
await helper.insert(uri, values);

// 查询数据
const predicates = new dataSharePredicates.DataSharePredicates();
const result = await helper.query(uri, predicates);
```

注意：`DataAbilityHelper` 是在 `ability` 命名空间内导出的类型，完整路径是 `@ohos.ability.ability.DataAbilityHelper`。
```

### 关键点

- 正确处理嵌套模块路径
- 解释命名空间结构
- 提供导入和使用示例

---

## 最佳实践

### 1. 编写代码前先验证 API

```
User: 使用 @ohos.some.unknown.function

Claude: [先调用 validate_arkts_api 验证]
      如果 API 不存在，告知用户并提供建议
      如果 API 存在，再编写代码
```

### 2. 拼写不确定时使用搜索

```
User: 我想用 Image 相关的 API，但不确定具体名称

Claude: [调用 search_arkts_apis]
      展示搜索结果
      让用户选择具体 API
```

### 3. 发现新功能时列出模块

```
User: 鸿蒙有哪些网络相关的 API？

Claude: [调用 list_arkts_modules 或 search_arkts_apis]
      按类别展示
      提供简要说明
```

---

## 注意事项

1. **API 路径必须以 `@` 开头**
2. **模块名区分大小写**
3. **HMS 和 OpenHarmony API 前缀不同** (`@hms.*` vs `@ohos.*`)
4. **某些 API 可能有系统能力要求** (syscap)
5. **某些 API 可能有版本要求** (@since N)
