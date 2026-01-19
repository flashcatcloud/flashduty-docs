# Flashduty 文档

本仓库是 [Flashduty](https://flashcat.cloud/) 的官方文档，基于 [Mintlify](https://mintlify.com/) 构建。

## 目录结构

```
docs/
├── zh/                    # 中文文档
│   ├── home.mdx           # 首页
│   ├── on-call/           # On-call 产品文档
│   ├── rum/               # RUM 产品文档
│   ├── monitors/          # Monitors 产品文档
│   ├── platform/          # 平台配置
│   ├── openapi/           # API 文档
│   ├── compliance/        # 安全合规
│   └── changelog/         # 更新日志
├── en/                    # 英文文档（与 zh/ 结构一致）
├── logo/                  # Logo 资源
├── docs.json              # Mintlify 配置文件
└── .cursor/rules/         # 写作规范
    ├── rule.md            # Mintlify 技术写作规范
    └── term.md            # 翻译术语表
```

## 产品模块

- **On-call**：故障管理、告警路由、分派策略、值班管理
- **RUM**：真实用户监控，前端性能和异常追踪
- **Monitors**：多数据源告警规则配置

## 本地开发

### 环境准备

安装 [Mintlify CLI](https://www.npmjs.com/package/mint)：

```bash
npm i -g mint
```

### 本地预览

在仓库根目录运行：

```bash
mint dev
```

访问 `http://localhost:3000` 查看本地预览。

### 检查错误

```bash
mint broken-links
```

## 新增文档

### 1. 创建文档文件

在对应目录下创建 `.mdx` 文件，文件必须以 YAML frontmatter 开头：

```yaml
---
title: "清晰、具体的标题"
description: "简洁说明页面目的和价值"
keywords: ["关键词1", "关键词2", "关键词3"]
---
```

### 2. 更新导航配置

在 `docs.json` 中添加新页面路径。找到对应的 `tab` 和 `group`，将文件路径添加到 `pages` 数组中：

```json
{
  "group": "快速开始",
  "pages": [
    "zh/on-call/quickstart/quickstart",
    "zh/on-call/quickstart/your-new-page"  // 新增页面
  ]
}
```

### 3. 使用规范优化文档

根据 `.cursor/rules/rule.md` 规范，使用 AI 进行文档优化，主要包括：

#### 页面结构规范

- 以最重要的信息开头（倒金字塔结构）
- 使用渐进式披露：基本概念在高级概念之前
- 将复杂程序分解为编号步骤
- 使用描述性、关键词丰富的标题

#### 常用组件

| 组件 | 用途 |
|------|------|
| `<Steps>` | 流程和顺序说明 |
| `<Tabs>` | 平台特定内容或替代方法 |
| `<CodeGroup>` | 多语言代码示例 |
| `<Accordion>` | 可折叠的补充信息 |
| `<Note>` / `<Tip>` / `<Warning>` | 标注提示信息 |
| `<Frame>` | 图片容器 |
| `<CardGroup>` | 相关链接卡片组 |

#### 示例：分步说明

````mdx
<Steps>
<Step title="安装依赖">
  运行安装命令：
  ```bash
  npm install
  ```
</Step>

<Step title="配置环境">
  创建配置文件并填写参数。
</Step>
</Steps>
````

#### 示例：多语言代码

````mdx
<Tabs>
<Tab title="Swift">
```swift
let config = Config()
```
</Tab>

<Tab title="Objective-C">
```objc
Config *config = [[Config alloc] init];
```
</Tab>
</Tabs>
````

### 4. 多语言同步

- 中英文文档需保持结构一致
- 翻译时参考 `.cursor/rules/term.md` 术语表
- 英文文档放在 `en/` 目录，路径与 `zh/` 对应

## 写作规范速查

### 语言风格

- 使用清晰、直接的语言
- 在说明中使用第二人称（"您"）
- 使用主动语态
- 避免术语，必要时首次使用时定义

### 代码示例要求

- 提供完整、可运行的示例
- 指定语言并包含文件名
- 为复杂逻辑添加注释
- 永远不要包含真实的 API 密钥


## 相关资源

- [Flashduty 控制台](https://console.flashcat.cloud/)
- [Flashduty 官网](https://flashcat.cloud/)
- [Mintlify 文档](https://mintlify.com/docs)
