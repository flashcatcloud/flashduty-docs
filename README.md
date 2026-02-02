# Flashduty 文档

[English](README.en.md) | 中文

[Flashduty](https://flashcat.cloud/) 官方文档，基于 [Mintlify](https://mintlify.com/) 构建。

## 目录结构

```
flashduty-docs/
├── zh/                    # 中文文档
│   ├── on-call/           # On-call 故障管理
│   ├── rum/               # 真实用户监控
│   ├── monitors/          # 告警规则配置
│   ├── platform/          # 平台配置
│   ├── openapi/           # API 文档
│   ├── compliance/        # 安全合规
│   └── changelog/         # 更新日志
├── en/                    # 英文文档（与 zh/ 结构一致）
├── logo/                  # Logo 资源
├── docs.json              # Mintlify 配置
└── .cursor/skills/        # AI Agent Skills
```

## 产品模块

| 模块 | 描述 |
|------|------|
| **On-call** | 故障管理、告警路由、分派策略、值班管理 |
| **RUM** | 真实用户监控，前端性能和异常追踪 |
| **Monitors** | 多数据源告警规则配置 |

## 本地开发

### 环境准备

```bash
npm i -g mint
```

### 常用命令

```bash
# 本地预览
mint dev

# 检查断链
mint broken-links
```

## 新增文档

### 1. 创建文档

在对应目录创建 `.mdx` 文件：

```yaml
---
title: "清晰、具体的标题"
description: "简洁说明页面目的"
---
```

### 2. 更新导航

在 `docs.json` 中添加页面路径：

```json
{
  "group": "快速开始",
  "pages": ["zh/on-call/quickstart/quickstart"]
}
```

### 3. 多语言同步

- 中英文文档保持结构一致
- 英文文档放在 `en/` 目录，路径与 `zh/` 对应
- 使用 `translate-zh-to-en` Skill 进行翻译

## 写作规范

### 语言风格

- 使用第二人称（"您"）
- 使用主动语态
- 保持简洁直接

### 常用组件

| 组件 | 用途 |
|------|------|
| `<Steps>` | 流程步骤 |
| `<Tabs>` | 平台差异 |
| `<CodeGroup>` | 多语言代码 |
| `<Note>` / `<Tip>` / `<Warning>` | 提示信息 |
| `<Frame>` | 图片容器 |

### 代码示例

- 提供完整、可运行的示例
- 指定语言和文件名
- 不包含真实 API 密钥

## AI 辅助

本项目提供两个 AI Skills：

| Skill | 用途 |
|-------|------|
| `translate-zh-to-en` | 将中文文档翻译为英文 |
| `polish-document` | 按规范润色优化文档 |

详见 [AGENTS.md](AGENTS.md)

## 相关链接

- [Flashduty 控制台](https://console.flashcat.cloud/)
- [Flashduty 官网](https://flashcat.cloud/)
- [Mintlify 文档](https://mintlify.com/docs)
