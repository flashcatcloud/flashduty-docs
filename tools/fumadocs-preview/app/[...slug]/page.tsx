import { notFound } from "next/navigation";
import { source, pages } from "@/lib/source";
import { getMDXComponents } from "@/components/mdx";
import { Shell, TableOfContents } from "@/components/shell";
import { APIReference } from "@/components/api-reference";
import { createOpenAPI } from "fumadocs-openapi/server";
import zh from "@/generated/openapi.zh.json";
import en from "@/generated/openapi.en.json";
import type { Document, HttpMethods } from "fumadocs-openapi";

export const dynamicParams = false;
export function generateStaticParams() {
  return pages.map((page) => ({ slug: page.url.slice(1).split("/") }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const { slug } = await params;
  const page = source.getPage(slug);
  return {
    title: `${page?.data.title ?? "Documentation"} - Flashduty Docs`,
    description: page?.data.description,
  };
}

const openapi = createOpenAPI({
  input: { zh: zh as unknown as Document, en: en as unknown as Document },
});

export default async function Page({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const { slug } = await params;
  const page = source.getPage(slug);
  const meta = pages.find((item) => item.url === `/${slug.join("/")}`);
  if (!page || !meta) notFound();
  const Body = page.data.body;
  const content = <Body components={getMDXComponents()} />;
  const isZh = meta.language === "zh";
  return (
    <Shell current={meta.url} language={meta.language} kind={meta.kind}>
      {meta.kind === "api" ? (
        <APIReference
          language={meta.language}
          payload={{
            bundled: (await openapi.getSchema(meta.language)).bundled,
          }}
          operations={[
            {
              path: meta.path!,
              method: meta.method!.toLowerCase() as HttpMethods,
            },
          ]}
          intro={content}
        />
      ) : (
        <div className="docs-grid">
          <article className="doc-article">
            <header className="page-heading">
              <div className="eyebrow">{isZh ? "协作空间" : "Channels"}</div>
              <h1>{page.data.title}</h1>
              <p className="page-description">{page.data.description}</p>
            </header>
            <div className="prose doc-content">{content}</div>
            <footer className="page-footer">
              <a href={`/${meta.language}/on-call/channel/create-edit`}>
                {isZh ? "← 创建与管理" : "← Create and manage"}
              </a>
              <a
                href={`/${meta.language}/api-reference/on-call/dedicated-integrations/channel-integration-read-list`}
              >
                {isZh ? "查询专属集成列表 →" : "List dedicated integrations →"}
              </a>
            </footer>
          </article>
          <TableOfContents items={page.data.toc} language={meta.language} />
        </div>
      )}
    </Shell>
  );
}
