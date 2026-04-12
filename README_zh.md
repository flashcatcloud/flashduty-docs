# Flashduty 文档

[English](README.md) | 中文

[![Mintlify](https://img.shields.io/badge/Built_with-Mintlify-8B5CF6?style=flat-square)](https://mintlify.com/)
[![Docs](https://img.shields.io/badge/Live-docs.flashcat.cloud-blue?style=flat-square)](https://docs.flashcat.cloud)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[Flashduty](https://flashcat.cloud/) 官方文档站，中英双语，基于 [Mintlify](https://mintlify.com/) 构建。覆盖 On-call 故障管理、RUM 真实用户监控、Monitors 告警规则三大产品模块，共 **390+** 页文档。

---

## 产品模块

| 模块 | 描述 | 文档路径 |
|------|------|----------|
| **On-call** | 故障管理、告警路由、分派策略、值班管理 | `*/on-call/` |
| **RUM** | 真实用户监控，前端性能和异常追踪 | `*/rum/` |
| **Monitors** | 多数据源告警规则配置 | `*/monitors/` |
| **Platform** | 账户管理、SSO、权限、API 密钥 | `*/platform/` |
| **OpenAPI** | REST API 参考文档 | `*/openapi/` |

---

## 快速开始

### 环境准备

```bash
npm i -g mint
```

### 本地预览

```bash
mint dev
```

浏览器访问 `http://localhost:3000` 查看文档。

### 检查断链

```bash
mint broken-links
```

> 每次修改内容后建议运行，确保没有引入死链。

---

## 参与贡献

我们欢迎社区贡献！无论是修复错别字、改进描述还是新增文档，都非常感谢。

### 新增/编辑文档

1. **编辑中文文档** — 在 `zh/` 目录下创建或编辑 `.mdx` 文件，中文为源语言
2. **更新导航** — 在 `docs.json` 中为中文和英文分别添加页面路径
3. **翻译为英文** — 在 `en/` 目录创建对应文件，保持路径结构一致
4. **验证链接** — 运行 `mint broken-links` 确认无断链

### Frontmatter 格式

每个 `.mdx` 文件必须包含：

```yaml
---
title: "清晰、具体的标题"
description: "简洁说明页面目的"
---
```

### 写作规范

- 使用第二人称（"您"）
- 使用主动语态、现在时
- 英文标题使用 sentence case（仅首字母大写）
- 善用 Mintlify 组件：`<Steps>`、`<Tabs>`、`<Note>`、`<Tip>`、`<Warning>`、`<Frame>`、`<CodeGroup>`

---

## 目录结构

```
flashduty-docs/
├── zh/                    # 中文文档（源语言）
│   ├── on-call/           # On-call 故障管理
│   ├── rum/               # 真实用户监控
│   ├── monitors/          # 告警规则配置
│   ├── platform/          # 平台配置
│   ├── openapi/           # API 文档
│   ├── compliance/        # 安全合规
│   └── changelog/         # 更新日志
├── en/                    # 英文文档（与 zh/ 结构一致）
├── api-reference/         # OpenAPI 3.1 规范文件（按模块和语言拆分）
├── glossary.md            # 中英术语对照表
├── docs.json              # Mintlify 配置与导航
└── logo/                  # Logo 资源
```

---

## 多语言翻译

中文为源语言，英文从中文翻译而来。翻译时需注意：

- 翻译 frontmatter 中的 `title` 和 `description`
- MDX 组件标签保持不变，仅翻译内部文本
- 代码块保持不变，仅翻译注释
- 内部链接路径从 `zh/` 改为 `en/`
- 图片路径保持不变

### 关键术语对照

| 中文 | English |
|------|---------|
| 协作空间 | channel |
| 故障 | incident |
| 分派策略 | escalation rule |
| 值班表 | schedule |
| 认领 | acknowledge |
| 静默策略 | silence rule |
| 抑制策略 | inhibit rule |
| 排除规则 | drop rule |

完整术语表见 [`glossary.md`](glossary.md)。

---

## 相关资源

| 资源 | 链接 |
|------|------|
| Flashduty 文档站 | [docs.flashcat.cloud](https://docs.flashcat.cloud) |
| Flashduty 控制台 | [console.flashcat.cloud](https://console.flashcat.cloud/) |
| Flashduty 官网 | [flashcat.cloud](https://flashcat.cloud/) |
| MCP Server | [flashduty-mcp-server](https://github.com/flashcatcloud/flashduty-mcp-server) |
| Terraform Provider | [terraform-provider-flashduty](https://github.com/flashcatcloud/terraform-provider-flashduty) |
| Mintlify 文档 | [mintlify.com/docs](https://mintlify.com/docs) |

---

## License

本项目采用 MIT 协议，详见 [LICENSE](LICENSE)。
