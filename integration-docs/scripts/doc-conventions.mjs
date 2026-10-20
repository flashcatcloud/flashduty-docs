// Conventions the console relies on when it renders a bundled integration doc.
//
// Steps: a doc with steps carries `### 步骤 N：title` (zh) or `### Step N: title`
// (en) headings numbered 1..N, which the console turns into a numbered layout.
// Placeholders: code blocks use `{integration_url}` (the full push URL including
// the key) and `{integration_key}`, which the console fills in per integration.

export const STEP_HEADING = /^### (?:步骤 (\d+)：|Step (\d+): )/;

const STEP_LABEL_FORMS = [
  // Hand-written heading: `#### 步骤 1：title`, `### Step 2: title`, `#### 步骤 3 title`.
  /^#{2,6}[ \t]*(?:步骤|Step)[ \t]*(\d+)[ \t]*[：:、]?[ \t]*(.*?)[ \t]*$/,
  // Bold line standing in for a heading: `**步骤 1：title**`.
  /^\*\*(?:步骤|Step)[ \t]*(\d+)[ \t]*[：:、]?[ \t]*(.*?)\*\*[ \t]*$/,
];

// Steps form one sequence only when they sit in a single <Steps> block. Several
// blocks are separate flows or sections (alternatives, per-section setup), so the
// page keeps plain `### <title>` headings instead of one numbered run.
export function countStepBlocks(mdx) {
  return (mdx.match(/<Steps\b/g) || []).length;
}

export function formatStepHeading(locale, number, title) {
  return locale === 'zh' ? `### 步骤 ${number}：${title}` : `### Step ${number}: ${title}`;
}

function forEachLineOutsideFences(markdown, visit) {
  let inFence = false;
  markdown.split('\n').forEach((line, index) => {
    if (line.trimStart().startsWith('```')) {
      inFence = !inFence;
      return;
    }
    if (!inFence) visit(line, index);
  });
}

function parseStepLabel(line) {
  for (const form of STEP_LABEL_FORMS) {
    const match = line.match(form);
    if (match) return { number: Number(match[1]), title: match[2] };
  }
  return null;
}

// Rewrites hand-written step headings and bold step labels to the canonical
// heading, but only when they number 1..N in order. Docs that repeat numbers
// (one flow per deployment type) are alternatives, not a sequence, and stay as
// written.
export function normalizeStepHeadings(markdown, locale) {
  const labels = new Map();
  forEachLineOutsideFences(markdown, (line, index) => {
    const label = parseStepLabel(line);
    if (label) labels.set(index, label);
  });
  const numbers = [...labels.values()].map((label) => label.number);
  if (numbers.length === 0 || numbers.some((number, i) => number !== i + 1)) return markdown;

  return markdown
    .split('\n')
    .map((line, index) => {
      const label = labels.get(index);
      return label ? formatStepHeading(locale, label.number, label.title) : line;
    })
    .join('\n');
}

export function findStepErrors(markdown, stepBlocks = 1) {
  const numbers = [];
  const strays = [];
  forEachLineOutsideFences(markdown, (line, index) => {
    const canonical = line.match(STEP_HEADING);
    if (canonical) {
      numbers.push(Number(canonical[1] ?? canonical[2]));
    } else if (parseStepLabel(line)) {
      strays.push(index + 1);
    }
  });
  if (numbers.length === 0) return [];

  const errors = [];
  if (stepBlocks > 1) {
    errors.push(`${stepBlocks} <Steps> blocks are separate flows and must not be numbered as one sequence`);
  }
  if (numbers.some((number, i) => number !== i + 1)) {
    errors.push(`step headings are numbered ${numbers.join(', ')}, expected 1..${numbers.length}`);
  }
  if (strays.length > 0) {
    errors.push(`step labels not in the "### Step N" form at lines ${strays.slice(0, 5).join(', ')}`);
  }
  return errors;
}

// The console replaces every occurrence of a token, so `${integration_key}` would
// become `$<key>` and be expanded by the shell.
const SHELL_EXPANSION_OF_TOKEN = /\$\{(?:integration_url|integration_key|api_host)\}/;

const CANONICAL_PLACEHOLDERS = new Set(['{integration_url}', '{integration_key}']);

// Spellings of the two placeholders that predate the canonical tokens.
const NON_CANONICAL_PLACEHOLDERS = [
  /<[^<>\n]*(?:push[ _-]?url|推送地址|integration[ _-]?key|集成密钥)[^<>\n]*>/i,
  /\bYOUR_(?:INTEGRATION_)?KEY\b|\bYOUR_FLASHDUTY_PUSH_URL\b/,
  /(?<![{$])\{(?!\{)[^{}\n]*(?:integration[ _-]?(?:key|url)|push[ _-]?url|推送地址)[^{}\n]*\}(?!\})/i,
  // A push URL written out against the SaaS host instead of `{integration_url}`.
  /https?:\/\/api\.flashcat\.cloud\/(?:event\/push|push)\//,
];

export function findPlaceholderErrors(markdown) {
  const errors = [];
  let inFence = false;
  markdown.split('\n').forEach((line, index) => {
    if (line.trimStart().startsWith('```')) {
      inFence = !inFence;
      return;
    }
    const shellExpansion = line.match(SHELL_EXPANSION_OF_TOKEN);
    if (shellExpansion) {
      errors.push(`line ${index + 1} uses "${shellExpansion[0]}", which the console rewrites to "$<value>"; rename the shell variable`);
    }
    if (!inFence) return;
    for (const pattern of NON_CANONICAL_PLACEHOLDERS) {
      for (const match of line.matchAll(new RegExp(pattern, `g${pattern.flags}`))) {
        if (!CANONICAL_PLACEHOLDERS.has(match[0])) {
          errors.push(`line ${index + 1} uses "${match[0]}" instead of {integration_url} / {integration_key}`);
        }
      }
    }
  });
  return errors;
}

// remark-gfm reads a pair of single `~` as strikethrough, so a version or number
// range such as `5.x~6.x` must use an en dash outside code.
export function findTildeErrors(markdown) {
  const errors = [];
  let inFence = false;
  markdown.split('\n').forEach((line, index) => {
    if (/^\s*(?:```|~~~)/.test(line)) {
      inFence = !inFence;
      return;
    }
    if (inFence) return;
    const prose = line.replace(/`[^`\n]*`/g, '');
    const match = prose.match(/\S~\S/);
    if (match) errors.push(`line ${index + 1} has "${match[0]}" between non-space characters; use an en dash for ranges`);
  });
  return errors;
}

// The build strips <span> tags, so a push URL given only through this span would
// reach the console as the bare words "push URL". Write {integration_url} instead.
export function findIntegrationUrlSpans(mdx) {
  return mdx
    .split('\n')
    .flatMap((line, index) => (/class=["']integration_url["']/.test(line) ? [index + 1] : []));
}
