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

export function findStepErrors(markdown) {
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
  if (numbers.some((number, i) => number !== i + 1)) {
    errors.push(`step headings are numbered ${numbers.join(', ')}, expected 1..${numbers.length}`);
  }
  if (strays.length > 0) {
    errors.push(`step labels not in the "### Step N" form at lines ${strays.slice(0, 5).join(', ')}`);
  }
  return errors;
}

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
