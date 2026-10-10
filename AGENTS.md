# Flashduty Documentation — Contributor and AI Agent Guide

This is the single source of truth for working in this repo, for both people and AI agents. `CLAUDE.md` is a symlink to this file, so edit only here (on Windows, clone with `git config core.symlinks true`).

## Project overview

- The official Flashduty docs, built with [Mintlify](https://mintlify.com/).
- Bilingual: `zh/` and `en/` mirror each other. **Chinese is the source of truth**, and English is translated from it.
- Product modules: **On-call** (incident management), **RUM** (real user monitoring), **Monitors** (alert rules), **AI SRE**, and the platform/developer docs.

```
flashduty-docs/
├── zh/ en/              # Docs (mirrored paths)
├── docs.json            # Navigation, tabs, theme, redirects
├── api-reference/       # OpenAPI 3.1 specs (per module, per language) → API Reference tab
├── integration-docs/    # Build-only bundle of integration pages embedded in the product (not published)
├── scripts/             # api_path_redirects.py, lint_openapi.py, upload.sh, review.sh
├── glossary.md          # zh → en terminology
├── .agents/skills/      # Agent skills (mirrored in .claude/skills/)
└── logo/ images/
```

## Commands

Install the CLI first: `npm i -g mint`

```bash
mint dev                                   # local preview
mint broken-links                          # broken links (run after any content change)
mint validate                              # build validation
python3 scripts/api_path_redirects.py --check
python3 scripts/lint_openapi.py
(cd integration-docs && node scripts/build.mjs && node scripts/check.mjs \
  && node --test scripts/build-docs-bundle.test.mjs)
MEILI_ENDPOINT=... MEILI_API_KEY=... MEILI_INDEX=... bash scripts/upload.sh   # Meilisearch upload for the AI Q&A bot
```

`mint broken-links` may report parsing errors from `.cursor/`. These are safe to ignore because `.mintignore` excludes that directory; only fix links in doc files.

## Skills

| Skill | Use it to | Resources |
| --- | --- | --- |
| `translate-zh-to-en` | Translate changed `zh/` pages to `en/`. With no uncommitted changes, it asks for a path. | `glossary.md` |
| `polish-document` | Polish structure and wording to Mintlify standards | `standards.md`, `components.md` (components: Steps, Tabs, callouts, …) |

Both skills live in `.agents/skills/<name>/` and are mirrored in `.claude/skills/<name>/`.

## Workflow

1. Write or edit the Chinese page in `zh/` (`.mdx`). Every page needs frontmatter `title` and `description`.
2. Register the page in `docs.json` under both `zh` and `en` (language → tab → group).
3. Translate it to `en/` at the same path, using `glossary.md`.
4. When you rename or remove a page, add a redirect in `docs.json`.
5. Run the [pre-merge checklist](#pre-merge-checklist).

## Translation rules

- Translate the frontmatter `title`, `description`, and `sidebarTitle`.
- Keep MDX component tags unchanged and translate only the inner text.
- Keep code unchanged and translate only the comments.
- Change internal links from `/zh/` to `/en/`. Keep image paths unchanged.
- zh and en must stay in sync: the same sections in the same order, and the same facts and numbers. If a page diverges, fix it in the same PR.

Terms whose translation isn't obvious (full list in `glossary.md`):

| 中文 | English | 中文 | English |
| --- | --- | --- | --- |
| 协作空间 | channel | 静默策略 | silence rule |
| 故障 | incident | 抑制策略 | inhibit rule |
| 分派策略 | escalation rule | 排除规则 | drop rule |
| 处理人员 | responders | 环节 | level |
| 认领 | acknowledge | 告警聚合 | alert grouping |
| 值班表 | schedule | 规则告警聚合 | pattern alert grouping |
| 新奇故障 | outlier incident | 智能告警聚合 | intelligent alert grouping |

## Writing and page design

These principles are adapted from Steve Krug's *Don't Make Me Think* (usability) and Robin Williams' *The Non-Designer's Design Book* (visual design), restated as concrete rules for these docs.

### Principles → rules

| Principle | What it means | Rule here |
| --- | --- | --- |
| Self-evident pages | A reader should know what a page is for and what to do next without having to think about it. | Open with 1–2 sentences on what the feature does and when to use it. No marketing preamble. |
| Readers scan | People skim headings, the first words of each paragraph, and tables. | Use descriptive H2s, short paragraphs, lists for parallel items, and tables for parameter matrices. |
| Omit needless words | Cut what the reader doesn't need, then cut more. | Delete filler ("强大的", "灵活的"), restated intros, and any FAQ that repeats the body. |
| Task first | Readers arrive with a job to do. | Order the page as: what it is → how to set it up → how it behaves → FAQ → related pages. |
| Consistent names | A link should land on a page that carries the same name. | Link text = the target's title/sidebarTitle. Use one term per concept (see glossary). |
| Persistent navigation | Readers need to know where they are. | Put each page in the nav once. Don't keep orphans or duplicates. Rename only with redirects. |
| Follow conventions | Familiar patterns cost nothing to learn. | Reuse the existing page templates and Mintlify components as intended. |
| Contrast | Make important things clearly different, or don't make them different at all. | Bold only real UI labels and true key terms. One callout per point, used for warnings and prerequisites only. |
| Repetition | Repeating the same pattern ties pages together. | Same section order, heading wording, and callout usage across sibling pages (all integrations, all IM pages). |
| Alignment | Every element should line up with something. | Indent images, code, and tables inside numbered steps (3 spaces) so lists don't break. |
| Proximity | Related things belong together. | Keep a rule next to the step it affects. Put FAQ at the end, not in the middle. |

### Language style

Paraphrased from 阮一峰《[中文技术文档的写作规范](https://github.com/ruanyf/document-style-guide)》 (zh) and the [Google developer documentation style guide](https://developers.google.com/style) (en; the [Microsoft Writing Style Guide](https://learn.microsoft.com/style-guide/welcome/) breaks ties). Read the sources for edge cases. The rules below override them where they differ.

**Both languages**

- Address the reader directly: **您** in zh docs (never 你), **you** in en. (The blog in `flashduty-website` uses impersonal phrasing or 用户 instead. Don't copy blog voice here, or docs voice there.)
- Use active voice and present tense. Prefer affirmative sentences, and never use double negatives ("不是不能" → "可以").
- Keep sentences short: zh about 20 characters per clause, and split anything over 40; en under about 25 words. Put one idea in each sentence and one topic in each paragraph.
- Make every pronoun's referent obvious (该 / 其 / 此 / it / this). If it's ambiguous, repeat the noun.
- Don't stack adjectives before a noun, and drop hype words (see the AI-voice list below).

**中文**

- Titles: no H1 → H3 skips, no lone child heading (a single H3 under an H2), a child heading shouldn't repeat its parent's words, avoid H4, and don't put end punctuation on titles.
- Use a formal register. No colloquialisms (东西、搞、弄、挺、啥、咱们、就行、其实、反正), and no rare, made-up, or classical-Chinese wording.
- Use 的 / 地 / 得 correctly: adjective + 的 + noun, adverb + 地 + verb, verb + 得 + complement.
- Put a half-width space between Chinese and Latin letters or digits (`使用 API`、`5 分钟`). Don't put a space next to full-width punctuation.
- Use full-width punctuation in Chinese sentences (，。：；？（）“”), with `、` between list items and 和 before the last one. Use half-width `:` in times and half-width punctuation in all-English sentences. Avoid ！, and never chain one comma after another to the end of a paragraph.
- On first use, give the English term a Chinese gloss, e.g. 服务等级目标（SLO）, or SLO（服务等级目标）when the English is better known. After that use one form only. Use singular nouns when translating plurals.
- Numbers: use half-width Arabic digits, and add a unit space when the unit is English (`64 KB`). Don't use 等 after a list that ends in ⋯⋯.

**English**

- Use a friendly, direct, and plain tone. Contractions are fine (don't, it's). Avoid "please" in instructions, "simply"/"just"/"easy", and Latin abbreviations (write "for example", not "e.g.").
- Use sentence case for titles and headings. Use the serial (Oxford) comma.
- Write numbers zero to nine as words in prose and 10+ as digits. Always use digits with units, versions, and UI values.
- Spell out an abbreviation on first use unless it's better known than the expansion (API, URL, SSO).
- Link text names the destination (the target page's title), never "click here" or "this page".
- Use UI labels exactly as shown, in bold. Use "select", not "click on".

**AI voice and filler: don't**

- Inflated significance: 标志着、至关重要、深远影响、赋能、助力、打造、全方位、一站式、无缝、强大 / crucial, pivotal, seamless, robust, leverage, empower, unlock, game-changing.
- Vague attribution: 业界普遍认为、越来越多的团队 / "many teams", "experts say", with no named source.
- Formulaic scaffolding: 不仅⋯⋯更⋯⋯、不是⋯⋯而是⋯⋯、值得注意的是、总而言之、a summary line closing every section, padded lists of three, and sentences that end in 从而⋯⋯ / "thereby".
- Dramatic devices: 答案是——、结果呢？ / "The answer?".
- Over-formatting: bold everywhere and "**Term**: explanation" lists where a sentence works.

The blog's Vale rules ([flashduty-website#253](https://github.com/flashcatcloud/flashduty-website/pull/253)) encode most of this list. Docs don't run Vale yet, so check by hand.

### Components

- Prefer Mintlify components where they fit: `<Steps>`, `<Tabs>`, `<Note>`, `<Tip>`, `<Warning>`, `<Frame>`, `<CodeGroup>`, `<Accordion>`. See `.agents/skills/polish-document/components.md`.

### Dos

- **State the rule and its outcome in 1–3 lines**, then add a relative link to the details (`/zh/...`, never an absolute docs URL).
- **Write UI paths with →**, for example **配置中心 → 自定义表单**.
- **Use tables for parameter or option matrices** (field / required / description; mode × capability).
- **Follow the integration page template**: overview → get the push URL in Flashduty (dedicated/shared) → configure in the tool → payload / alert key / severity mapping → verify → FAQ → troubleshooting.
- **sidebarTitle**: use the short product or feature name and drop suffixes such as "集成"/"integration" (`title: "Stripe 告警集成"`, `sidebarTitle: "Stripe"`).
- **Keep one source for each number** (limits, prices, thresholds). Reuse it via a Mintlify snippet or a link, and when two pages conflict, fix both in the same change.
- **Verify facts against product code** (for example the `fc-saas-web` UI and the backend repos) or ask the product owner. Never guess. If you can't confirm something, leave it unchanged and flag it in the PR.
- **Use stable anchors**: add `<span id="..."></span>` before a heading that is linked from elsewhere, instead of guessing CJK slugs.

### Don'ts

- **Don't** write implementation or QA-spec detail: backend limits nobody configures, how direct URL access is guarded, verbatim empty-state/toast copy, lists of every button, internal routes, fields, or constants, or `localhost` links that aren't example config values.
- **Don't** start accordion titles with "展开…" or "Click to expand". The title should be the question or the topic.
- **Don't** put `---` right under a heading, or between sections. Headings already separate them.
- **Don't** stack callouts (Note + Tip + Warning in a row) or bold half a paragraph.
- **Don't** use timestamps or file names as image `alt` text. Describe what the image shows.
- **Don't** use duplicate or competing names for one thing (状态页 vs 状态页面, 控制台 vs 后台, 自定义操作 vs 自定义动作), or keep two pages for one feature (for example the two Go SDK pages, now merged).
- **Don't** let numbers conflict across pages or languages (for example 99% vs 99.5%, or < 1s vs < 500ms).
- **Don't** copy-paste another product's name into an integration page. Check every product name against the page title.
- **Don't** use `<Card>`s without `href` for plain lists. Cards look clickable; use a list instead.
- **Don't** put FAQ in the middle of a page, or number headings ("一、", "2.").
- **Don't** keep orphan pages (in the repo but not in the nav). Merge or delete them, and add redirects.

### Before / after

Status page creation limits (zh):

```diff
- **创建状态页的两条准入规则**：列表页入口与创建页本身都会校验，直接访问创建页也绕不过去。
- - **订阅过期或被停用时不能新建**：列表页的创建按钮被禁用；直接打开创建页会返回一个空状态页，标题为「订阅已过期，暂时无法新建」……主按钮变为 **立即续费**（另有 **返回列表**）。
- - **内部状态页要求专业版及以上**：创建页可被直接访问（`/status-page/create?type=internal`），所以……
+ 以下情况无法新建状态页（已创建的状态页不受影响，仍可编辑和发布事件）：
+ - 订阅过期或被停用：续费后可继续创建。
+ - 内部状态页：需专业版及以上。
+ 详见[订阅过期后会发生什么](/zh/platform/pricing#订阅过期后会发生什么)。
```

Feature intro (zh):

```diff
- 聚合视图提供了一个不同的视角来查看故障，您可以定义不同的聚合维度。聚合维度的本质是实时 Group By，比如按照严重程度来聚合查看。
+ 聚合视图按您定义的维度对故障做实时 Group By，例如按严重程度分组查看。
```

Best-practice cards → list:

```diff
- <CardGroup cols={2}>
-   <Card title="记录 request_id" icon="clipboard-list">保存每次请求返回的 `request_id`……</Card>
- </CardGroup>
+ - **记录 request_id**：保存每次请求返回的 `request_id`，便于排查和技术支持。
```

## Retired features

- The Monitors targets feature and the monit-agent integration are retired. Don't recreate `zh/monitors/targets/*` or `en/monitors/targets/*`, restore their navigation, or describe target lists and per-row AI analysis as available. Residual routes or components in source code are not evidence of a supported feature. Keep the overview URL redirects to the Monitors quickstart.

## Pre-merge checklist

- [ ] `mint broken-links` and `mint validate` pass.
- [ ] `python3 scripts/api_path_redirects.py --check` and `python3 scripts/lint_openapi.py` pass.
- [ ] The integration-docs build/check/test pass when integration pages changed.
- [ ] Headings and anchors diffed before/after: no section lost, and every `#anchor` link still resolves.
- [ ] Renamed or removed pages have redirects in `docs.json`, and new pages are in the nav for both languages.
- [ ] zh and en are updated together, with matching sections and numbers.
- [ ] Changed prose passes the [language style](#language-style) rules: 您/you, no AI-voice words, spaces between Chinese and Latin text, and no clause over 40 characters.
- [ ] Facts and numbers are checked against product code or the owner. Unverified items are listed in the PR description.
- [ ] Commits are pulled with `git pull --rebase` and grouped logically (one area per commit).
