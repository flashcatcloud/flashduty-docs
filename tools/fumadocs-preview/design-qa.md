# Fumadocs 样例视觉与交互验证

final result: passed

## 对照基准

- Mintlify 原站静态导出的“分派策略”和“查询专属集成列表”。
- 原站与实现均为 Chromium、浅色主题、页面顶部、1440 × 1080 CSS px，deviceScaleFactor 为 1。截图像素与 CSS 尺寸一致，无额外密度归一化。
- 证据目录：`/Users/a1/.codex/visualizations/2026/11/25/01a2119c-52d0-7f10-8e16-cc048a5bb2c3/fumadocs-preview/`。
- 原站：`reference-doc.png`、`reference-api.png`。
- 实现：`final-doc.png`、`final-api.png`。
- 同屏并排全图：`comparison-doc.png`、`comparison-api.png`，每幅 2880 × 1080，左为原站、右为实现。
- 同位置局部对照：`comparison-doc-focus.png`、`comparison-api-focus.png`，每幅 1400 × 650，正文区域保持 1:1 CSS 尺寸。
- 其他状态：`preview-doc-tabs.png`、`preview-doc-steps.png`、`preview-api-schema.png`、`preview-doc-dark.png`、`preview-doc-mobile.png`、`preview-api-mobile.png`。

## 视觉检查

- 字体：Inter 随静态包提供，中文使用相同系统字体回退；正文 16/28，标题 36/40，字重与换行接近原站。
- 布局：1440 宽度下正文左边界 363.1875 px，与原站一致。产品文档为正文加目录，API 为正文加示例栏；页面顶部和主要栏宽已对照。
- 颜色：紫色主题、浅紫选中态、正文和辅助文字颜色已核对；深色模式可切换并保留选择。
- 图片：复用原站 Logo 与文档截图，不以占位图替换。12 张正文图片在构建时缓存，部署后从本站读取。
- 内容：4 篇产品文档保留完整正文与组件；8 个 API 复用原有使用说明，并从 OpenAPI 显示请求、响应字段。中英文共 24 页。
- 手机：390 × 844 下正文无横向溢出，导航抽屉、搜索和 API 示例可用。

## 比较迭代

1. 首轮发现 API 表格默认灰底、外边框和行高改变了正文密度，标题链接也带额外下划线（P2）。替换为普通表格与标题组件，按原站调整间距、列宽和行高。修正后的全图与正文局部截图已复核。
2. 首轮请求代码面板高度明显小于原站（P2）。统一多行 cURL 排版，重新截图核对。最终样例额外展示 `Fd-App-Key: <APP_KEY>`，这是与页面私有化说明一致的内容调整。
3. 手机宽度最初缺少可见搜索入口（P2）。将搜索按钮放入移动版页头，浏览器验证搜索 API 路径有结果且页面无溢出。

没有剩余 P0/P1/P2。少数图标字形、内联代码边框、细小垂直间距以及响应 JSON 的排版仍有 P3 差异；本次未宣称全站逐像素一致。

## 功能与离线验证

- 24 个静态路径的标题、加载和桌面溢出检查通过。
- 标签页、提示框、折叠项、步骤、截图、目录锚点通过。
- API 子字段、响应状态切换、cURL/JavaScript/Python 示例及复制通过。
- 中英文路由保持、刷新、正文/字段/路径搜索、空结果、键盘快捷键通过。
- 未包含的页面显示样例范围，避免点击进入不存在的本地页面。
- 深色主题、移动导航、移动搜索通过。
- 浏览器阻断外网后检查通过，未发现外部资源请求、失败请求或脚本异常。
- 另用普通 HTTP 测试域名验证：`isSecureContext=false`、Clipboard API 不存在，复制回退仍成功；实际剪贴板内容已读取核对。
- `browser-report.json` 和 `private-http-report.json` 保存验证结果。
- `npm run build`（含 TypeScript）、OpenAPI lint、API 路径重定向检查通过。

## 范围

这是替代方案的样例，不是全站迁移验收。未包含的页面、全部 Mintlify 组件及全站搜索性能尚未验证；AI 问答不在本次范围。
