# Fumadocs 私有化文档预览

验证使用 Fumadocs 替代 Mintlify，并定制成现有 Flashduty 文档的样式。

样例包括中文和英文的 4 篇协作空间产品文档（创建与管理、集成数据、分派策略、告警降噪）和 8 个专属集成 API，共 24 个页面。文档正文、API 参数、响应、使用限制均从本仓库读取，不维护第二份内容。

## 本地运行

需要 Node.js 24 和 npm。在当前目录执行：

```bash
npm ci
npm run build
npm run preview
```

打开 <http://127.0.0.1:3341/zh/on-call/channel/escalation-rule/>。也可运行 `npm run dev` 开发预览。

- 产品文档：`/zh/on-call/channel/escalation-rule/`
- API：`/zh/api-reference/on-call/dedicated-integrations/channel-integration-read-list/`
- 英文路径将 `/zh/` 替换为 `/en/`，页面语言菜单也可切换。

本地服务器只监听回环地址。设置 `PORT=其他端口 npm run preview` 可更改端口。

## 内网部署

`npm run build` 生成 `out/`，部署时仅需将该目录交给 Nginx 等静态 HTTP 服务。阅读不需要 Node.js、Mintlify、许可证服务或外部网络。初次安装依赖及构建缓存图片需要联网，图片、字体、搜索数据、脚本、样式均随构建产物提供。

保留 `out/` 的完整目录结构，包括 `_next/`。站点部署在域名根路径，Nginx 使用 `try_files $uri $uri/ =404`；修改子路径需另行配置构建路径。不要直接用 `file://` 打开。

## 实现与范围

- 使用 Fumadocs MDX 编译现有 MDX，并适配步骤、标签页、提示、折叠项、卡片和图片。
- 使用 `fumadocs-openapi` 的解析、引用解析、Operation Provider、请求代码生成和响应样例功能，定制 API 页面布局；API 原有的 `x-mint.content` 和路由继续使用。
- 现有 URL 保持不变；导航、主题、中英文切换和页面内容搜索可用。
- 截图来自原文的 CDN 地址，只缓存到被忽略的构建目录，不修改原文，也不提交图片副本。
- 未迁移的导航和文内链接会提示样例范围。此预览没有全站迁移，也没有接入 AI 问答。
- API 页面用于阅读和复制示例，使用 `https://api.example.com` 占位地址，不提供发送请求按钮。
- 搜索覆盖这些样例的完整文本；这不是全站搜索性能评估。

`npm run build` 包含 TypeScript 检查。生成目录和依赖均已排除出 Git，现有 Mintlify 构建通过 `.mintignore` 排除此预览目录。
