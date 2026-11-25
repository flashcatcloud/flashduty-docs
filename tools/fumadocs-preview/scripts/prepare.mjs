import {
  mkdir,
  readFile,
  writeFile,
  copyFile,
  access,
  rm,
} from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve, dirname, extname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repo = resolve(root, "../..");
const docs = [
  "create-edit",
  "integrate-data",
  "escalation-rule",
  "noise-reduction",
];
const pages = [];
const assets = new Set();
await rm(resolve(root, "content"), { recursive: true, force: true });
await mkdir(resolve(root, "public/assets"), { recursive: true });
await mkdir(resolve(root, "generated"), { recursive: true });
for (const file of [
  "saas-logo.svg",
  "saas-logo-white.svg",
  "saas-favicon.png",
]) {
  await copyFile(resolve(repo, "logo", file), resolve(root, "public", file));
}

async function localize(text) {
  const urls = [
    ...new Set(
      text.match(
        /https:\/\/(?:docs-cdn|download)\.flashcat\.cloud\/[^\s)"<>]+/g,
      ) ?? [],
    ),
  ];
  for (const url of urls) {
    const name =
      createHash("sha256").update(url).digest("hex").slice(0, 20) +
      extname(new URL(url).pathname);
    const target = resolve(root, "public/assets", name);
    try {
      await access(target);
    } catch {
      const response = await fetch(url, {
        signal: AbortSignal.timeout(45000),
        headers: {
          "User-Agent": "Mozilla/5.0",
          Referer: "https://docs.flashcat.cloud/",
        },
      });
      if (!response.ok) throw new Error(`Asset ${url}: ${response.status}`);
      await writeFile(target, Buffer.from(await response.arrayBuffer()));
    }
    assets.add(url);
    text = text.replaceAll(url, `/assets/${name}`);
  }
  return text;
}

async function savePage(path, text, extra, searchTerms = "") {
  const target = resolve(root, "content", `${path}.mdx`);
  await mkdir(dirname(target), { recursive: true });
  text = await localize(text);
  await writeFile(target, text);
  const title = text.match(/^title:\s*["']?(.+?)["']?\s*$/m)?.[1] ?? path;
  const description =
    text.match(/^description:\s*["']?(.+?)["']?\s*$/m)?.[1] ?? "";
  pages.push({
    url: `/${path}`,
    title,
    description,
    language: path.split("/")[0],
    ...extra,
    search: `${text
      .replace(/^---[\s\S]*?---/, "")
      .replace(/<[^>]*>|[#*`]/g, " ")
      .replace(/\s+/g, " ")
      .trim()} ${searchTerms}`.trim(),
  });
}

for (const lang of ["zh", "en"]) {
  for (const doc of docs) {
    const path = `${lang}/on-call/channel/${doc}`;
    await savePage(path, await readFile(resolve(repo, `${path}.mdx`), "utf8"), {
      kind: "doc",
    });
  }
  const spec = JSON.parse(
    await readFile(
      resolve(repo, `api-reference/on-call.openapi.${lang}.json`),
      "utf8",
    ),
  );
  const subset = {
    ...spec,
    servers: [{ url: "https://api.example.com" }],
    paths: {},
  };
  const tag =
    lang === "zh" ? "On-call/专属集成" : "On-call/Dedicated integrations";
  function operationSearch(operation) {
    const seen = new Set();
    const words = [];
    function visit(value) {
      if (typeof value === "string" || typeof value === "number") {
        words.push(value);
        return;
      }
      if (!value || typeof value !== "object") return;
      if (value.$ref && !seen.has(value.$ref)) {
        seen.add(value.$ref);
        const [, , section, key] = value.$ref
          .split("/")
          .map(decodeURIComponent);
        visit(spec.components[section]?.[key]);
      }
      for (const [key, child] of Object.entries(value)) {
        if (key === "$ref" || key === "x-mint") continue;
        words.push(key);
        visit(child);
      }
    }
    visit(operation);
    return words.join(" ");
  }
  for (const [path, item] of Object.entries(spec.paths)) {
    for (const [method, op] of Object.entries(item)) {
      if (!op.tags?.includes(tag)) continue;
      subset.paths[path] = { ...subset.paths[path], [method]: op };
      const href = op["x-mint"].href.slice(1);
      const intro =
        lang === "zh"
          ? "将示例中的 `https://api.example.com` 替换为私有化部署的 API 地址，通过 `Fd-App-Key` 请求头传递 App Key。"
          : "Replace `https://api.example.com` with your private API address. Pass your App Key in the `Fd-App-Key` request header.";
      await savePage(
        href,
        `---\ntitle: ${JSON.stringify(op.summary)}\ndescription: ${JSON.stringify(op.description ?? "")}\n---\n\n${intro}\n\n${op["x-mint"].content ?? ""}\n`,
        {
          kind: "api",
          method: method.toUpperCase(),
          path,
        },
        `${method.toUpperCase()} ${path} ${operationSearch(op)}`,
      );
    }
  }
  const components = { securitySchemes: spec.components.securitySchemes };
  const refs = new Set();
  function collectRefs(value) {
    if (!value || typeof value !== "object") return;
    if (typeof value.$ref === "string" && !refs.has(value.$ref)) {
      refs.add(value.$ref);
      const [, category, section, key] = value.$ref
        .split("/")
        .map(decodeURIComponent);
      if (category !== "components" || !spec.components[section]?.[key])
        throw new Error(`Unsupported reference: ${value.$ref}`);
      components[section] ??= {};
      components[section][key] = spec.components[section][key];
      collectRefs(components[section][key]);
    }
    for (const item of Object.values(value)) collectRefs(item);
  }
  collectRefs(subset.paths);
  subset.components = components;
  subset.tags = spec.tags.filter((item) => item.name === tag);
  await writeFile(
    resolve(root, `generated/openapi.${lang}.json`),
    JSON.stringify(subset),
  );
}
await writeFile(resolve(root, "generated/pages.json"), JSON.stringify(pages));
const config = JSON.parse(await readFile(resolve(repo, "docs.json"), "utf8"));
async function navTitles(node) {
  if (typeof node === "string") {
    try {
      const text = await readFile(resolve(repo, `${node}.mdx`), "utf8");
      return {
        url: `/${node}`,
        title:
          text.match(/^sidebarTitle:\s*["']?(.+?)["']?\s*$/m)?.[1] ??
          text.match(/^title:\s*["']?(.+?)["']?\s*$/m)?.[1] ??
          node.split("/").at(-1),
      };
    } catch {
      return { url: `/${node}`, title: node.split("/").at(-1) };
    }
  }
  return {
    ...node,
    pages: await Promise.all((node.pages ?? []).map(navTitles)),
  };
}
await writeFile(
  resolve(root, "generated/navigation.json"),
  JSON.stringify(
    await Promise.all(
      config.navigation.languages.map(async ({ language, tabs }) => ({
        language,
        groups: await Promise.all(
          tabs.find((tab) => tab.tab === "On-call").groups.map(navTitles),
        ),
      })),
    ),
  ),
);
console.log(
  `Prepared ${pages.length} bilingual sample pages; cached ${assets.size} images for offline reading.`,
);
