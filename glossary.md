# Flashduty Terminology Glossary

Chinese-English terminology mapping. Maintain consistency during translation.

## Core Concepts

| Chinese | English | Notes |
|---------|---------|-------|
| 协作空间 | channel | Team workspace |
| 故障 | incident | Event requiring response |
| 告警 / 报警 | alert | Monitoring system notification |
| 集成来源 / 数据源 | integration | Alert data source |

## Incident Management

| Chinese | English |
|---------|---------|
| 分派 | assign |
| 分派策略 | escalation rule |
| 故障升级 | escalation |
| 认领 | acknowledge |
| 解决故障 | resolve the incident |
| 关闭故障 | close the incident |
| 新奇故障 | outlier incident |

## Alert Processing

| Chinese | English |
|---------|---------|
| 告警风暴 | alert storm |
| 告警聚合 | alert grouping |
| 规则告警聚合 | pattern alert grouping |
| 智能告警聚合 | intelligent alert grouping |
| 静默策略 | silence rule |
| 抑制策略 | inhibit rule |
| 排除规则 | drop rule |
| 快速静默 | quick silence |
| 降噪 | reduce noise |
| 抖动 | flapping |
| 错误聚合 | error grouping |
| 指纹 | fingerprint |

## Schedule & On-call

| Chinese | English |
|---------|---------|
| 值班表 | schedule |
| 值班 | schedule |
| 值班轮换 | On-call rotation / On-call shift |
| 处理人员 / 响应人员 / 分派人员 / 值班人员 | responders |

## Severity Levels

| Chinese | English |
|---------|---------|
| 严重程度 / 等级 | severity |
| 严重 | critical |
| 一般 | warning |
| 轻微 | info |

## Incident Status

| Chinese | English |
|---------|---------|
| 待处理 | triggered |
| 处理中 | processing |
| 未关闭 | open |
| 已关闭 | closed |

## Time & Notifications

| Chinese | English |
|---------|---------|
| 暂缓 | snooze |
| 取消暂缓 | unsnooze |
| 触发 / 发生 | trigger |
| 发生时间 / 触发时间 | triggered at |
| 结束时间 | ended at |
| 循环通知 | loop notification |
| 中断次数 | interruption |
| 通知次数 | notifications |
| 时间段 | hours |
| 工作时间 | work |
| 睡眠时间 | sleep |
| 休息时间 | rest |
| 响应投入 | response effort |

## Subscription & Plans

| Chinese | English |
|---------|---------|
| 订阅 | plan |
| 专业版 | Pro |
| 标准版 | Standard |
| 免费版 | Free |
| 订阅升级 | plan upgrade |
| 赠送金 | bonus |

## Account & Team

| Chinese | English |
|---------|---------|
| 主体 / 主体账号 | owner |
| 成员 / 成员账号 | member |
| 管理团队 | Team |
| 登录 | sign in |
| 登出 | sign out |
| 注册 | sign up |

## UI & Labels

| Chinese | English |
|---------|---------|
| 属性 | attribute |
| 标签 | label |
| 详情 | details |
| 告警列表 | Alerts |
| 告警标题 | Title |
| 分析看板 | insights |
| 故障数量 | incidents |
| 常见问题 | FAQ |
| 视频教学 | watch videos |
| 解决办法 | resolution |
| 推送地址 | push URL |
| 跳转链接 | jump link |

## Actions

| Chinese | English |
|---------|---------|
| 启用 / 开启 | Enable |
| 禁用 | Disable |
| 删除 | Delete |
| 修改 | change |
| 回复 | reply |
| 聚合 | group |
| 关联 | associated |

## Third-party Integrations

| Chinese | English |
|---------|---------|
| 企业微信 / 微信 | WeCom |
| 飞书 | Feishu/Lark |
| 钉钉 | Dingtalk |

## Technical Terms

| Chinese | English |
|---------|---------|
| IP段匹配 | CIDR matching |
| 相同项 | equal item |
| 组合规则 | composition rule |
| 中文对照 | alias |
| 环节 | level |
| 输入不能为空 | the field is required |
| 用户未关联 | user not linked |
| 应用未关联 | app not linked |

## Regional

| Chinese | English |
|---------|---------|
| 国内 | mainland China |
| 手机号 | phone |
| 邮箱 | email |
| 北京快猫星云科技有限公司 | Beijing Flashcat Cloud Technology Co.,Ltd. |

## API documentation

Used by the `api-review` skill when generating `api-reference/openapi.{en,zh}.json`. Stay consistent with these terms across operation summaries, descriptions, and field labels so the reference reads uniformly.

### Operation verbs (summary prefix)

| Chinese | English (openapi summary) | Notes |
|---------|----------|-------|
| 查看 xxx 详情 | Get xxx detail | Single-item fetch by ID |
| 查看 xxx 列表 / 获取 xxx 列表 | List xxx | Paginated list |
| 查询 xxx | Query xxx | Filter-based list |
| 创建 xxx | Create an xxx | |
| 新建 xxx | Create an xxx | Same as above — keep English uniform |
| 变更 xxx 信息 / 修改 xxx / 更新 xxx | Update an xxx | |
| 删除 xxx | Delete an xxx | Soft-delete unless noted |
| 启用 xxx | Enable an xxx | |
| 禁用 xxx | Disable an xxx | |
| 预览 xxx | Preview an xxx | |
| 导出 xxx | Export xxx | |
| 导入 xxx | Import xxx | |
| 批量 yyy | Bulk yyy / Batch yyy | Use "bulk" for user-facing, "batch" for technical |
| xxx 操作记录 / 审计记录 | xxx audit log | |

### Reference / structural terms

| Chinese | English |
|---------|---------|
| 速率限制 | rate limits |
| 限流 | rate limiting |
| 超过限制 | exceed the limit |
| 账户维度 | account-scoped |
| 账户下 | under the same account |
| 全局限流 | global rate limit |
| 权限要求 | permissions |
| 权限点 | permission |
| 数据权限 | data permission |
| 接口鉴权 | API authentication |
| 需要鉴权 | requires authentication |
| 鉴权失败 | authentication failed |
| 请求头 | request header |
| 查询参数 | query parameter |
| 请求体 / 请求参数 | request body |
| 响应体 / 响应参数 | response body |
| 响应结构 / 响应格式 | response envelope |
| 错误码 | error code |
| 请求 ID | request ID |
| 返回值 | return value |
| 分页 | pagination |
| 分页大小 | page size |
| 排序字段 | sort field |
| 升序 / 降序 | ascending / descending |
| 必填 | required |
| 选填 / 可选 | optional |
| 默认值 | default value |
| 枚举值 | enum values |
| 取值范围 | value range |
| 示例 | example |
| 示例代码 | code sample |
| 软删除 | soft delete |
| 幂等 | idempotent |
| 向后兼容 | backward compatible |
| 废弃 / 已废弃 | deprecated |
| 审计日志 | audit log |
| 高危操作 | high-risk operation |
| 二次验证 | second-factor verification |

### Permission class names

Permission classes come from `fc-pgy/logic/permission/permission_test.go` — use the `classEn` field there as the authoritative English label. Common ones:

| Chinese (`class`) | English (`classEn`) |
|---------|---------|
| 组织管理 | Organization |
| 配置中心 | Configuration |
| 协作空间 | Channel |
| 故障管理 | Incident |
| 告警管理 | Alert |
| 集成中心 | Integration |
| 分析看板 | Insight |
| 状态页 | Status Page |
| RUM | RUM |
| Monitors | Monitors |

When a permission's `classEn` is set in `permission_test.go`, trust it over any guess. The Flashduty product team manages those labels and keeps them consistent with the console UI.

### Notes for the generator

- **Prefer frontend labels over translation.** If the frontend console uses a specific English label for a concept (e.g., "Notification template" vs "Message template"), use the frontend label. Check `fc-foundation-app/src/Packages/saas/pages/...` i18n files as the source of truth for user-facing labels.
- **Don't translate product names.** "On-call", "RUM", "Monitors", "Flashduty" stay English in both languages.
- **Don't translate wire values.** Enum values like `"enabled"`, `"InvalidParameter"`, `"updated_at"` are wire-format identifiers and must appear identically in both EN and ZH specs. Only their descriptions get localized.
- **Verb tense** — English uses imperative ("Create a template", "Delete an incident"), Chinese uses short noun phrases ("创建模板", "删除故障"). Don't prefix Chinese summaries with verbs like "创建一个" when "创建" alone reads naturally.
