"use client";

import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type MouseEvent,
} from "react";
import { useTheme } from "fumadocs-ui/provider/base";
import { Icon } from "./icons";
import pages from "@/generated/pages.json";
import navigation from "@/generated/navigation.json";
import type { TOCItemType } from "fumadocs-core/toc";

type NavNode = {
  url?: string;
  title?: string;
  group?: string;
  icon?: string;
  pages?: NavNode[];
};
const apiSlug =
  "api-reference/on-call/dedicated-integrations/channel-integration-read-list";
const docSlug = "on-call/channel/escalation-rule";

export function Landing() {
  useEffect(() => {
    window.location.replace(`/zh/${docSlug}/`);
  }, []);
  return (
    <p className="landing">
      <a href={`/zh/${docSlug}/`}>Flashduty Docs →</a>
    </p>
  );
}

export function Shell({
  children,
  current,
  language,
  kind,
}: {
  children: ReactNode;
  current: string;
  language: string;
  kind: string;
}) {
  const zh = language === "zh";
  const { resolvedTheme, setTheme } = useTheme();
  const [mobile, setMobile] = useState(false);
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState("");
  const search = useRef<HTMLDialogElement>(null);
  const scopeDialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const localPages = pages.filter((page) => page.language === language);
  const results = localPages
    .filter(
      (page) =>
        !query ||
        `${page.title} ${page.description} ${page.search}`
          .toLowerCase()
          .includes(query.toLowerCase()),
    )
    .slice(0, 12);
  function openSearch() {
    search.current?.showModal();
    input.current?.focus();
  }
  function showScope(title: string) {
    setScope(title);
    scopeDialog.current?.showModal();
  }
  useEffect(() => {
    document.documentElement.lang = zh ? "zh-CN" : "en";
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openSearch();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zh]);
  function checkLink(event: MouseEvent) {
    if (!(event.target instanceof Element)) return;
    const link = event.target.closest("a");
    const href = link?.getAttribute("href");
    if (!href?.startsWith("/") || href.startsWith("//")) return;
    const path = href.split(/[?#]/)[0].replace(/\/$/, "");
    if (pages.some((page) => page.url === path) || path.startsWith("/assets/"))
      return;
    event.preventDefault();
    showScope(link?.textContent?.trim() ?? href);
  }
  function renderNav(node: NavNode, index: number, nested = false): ReactNode {
    if (node.url) {
      const available = pages.some((page) => page.url === node.url);
      return (
        <a
          key={node.url}
          href={node.url}
          aria-current={current === node.url ? "page" : undefined}
          title={
            available
              ? undefined
              : zh
                ? "未包含在本次样例中"
                : "Outside this preview"
          }
          className={`side-link ${nested ? "nested" : ""} ${current === node.url ? "selected" : ""}`}
        >
          {node.title}
        </a>
      );
    }
    return (
      <section className="side-group" key={`${node.group}-${index}`}>
        <h2>
          <Icon name={node.icon ?? "book"} />
          {node.group}
        </h2>
        {node.pages?.map((child, i) =>
          child.group ? (
            <details key={child.group}>
              <summary>
                {child.group}
                <Icon name="right" />
              </summary>
              {child.pages?.map((item, j) => renderNav(item, j, true))}
            </details>
          ) : (
            renderNav(child, i)
          ),
        )}
      </section>
    );
  }
  return (
    <div onClickCapture={checkLink}>
      <header className="site-header">
        <div className="header-row">
          <div className="brand-group">
            <button
              className="icon-button mobile-menu"
              aria-label={zh ? "打开导航" : "Open navigation"}
              onClick={() => setMobile(!mobile)}
            >
              <Icon name={mobile ? "close" : "menu"} />
            </button>
            <a
              className="brand"
              href={`/${language}/${docSlug}`}
              aria-label="Flashduty Docs"
            >
              <img
                className="logo-light"
                src="/saas-logo.svg"
                alt="Flashduty"
              />
              <img
                className="logo-dark"
                src="/saas-logo-white.svg"
                alt="Flashduty"
              />
            </a>
            <details className="language-menu">
              <summary>
                {zh ? "简体中文" : "English"}
                <Icon name="down" />
              </summary>
              <div className="language-options">
                <a href={current.replace(/^\/(zh|en)/, "/zh")}>简体中文</a>
                <a href={current.replace(/^\/(zh|en)/, "/en")}>English</a>
              </div>
            </details>
          </div>
          <button className="search-trigger" onClick={openSearch}>
            <Icon name="search" />
            <span>{zh ? "搜索..." : "Search..."}</span>
            <kbd>⌘K</kbd>
          </button>
          <div className="header-actions">
            <button
              className="mobile-search icon-button"
              aria-label={zh ? "搜索" : "Search"}
              onClick={openSearch}
            >
              <Icon name="search" />
            </button>
            <a href={`/${language}/${apiSlug}`}>
              <Icon name="terminal" />
              {zh ? "API 参考" : "API Reference"}
            </a>
            <button
              className="console-link"
              onClick={() => showScope(zh ? "控制台" : "Console")}
            >
              {zh ? "控制台" : "Console"}
              <Icon name="right" />
            </button>
            <button
              className="icon-button"
              aria-label={zh ? "切换明暗主题" : "Toggle theme"}
              onClick={() =>
                setTheme(resolvedTheme === "dark" ? "light" : "dark")
              }
            >
              <Icon name={resolvedTheme === "dark" ? "moon" : "sun"} />
            </button>
          </div>
        </div>
        <nav className="top-tabs" aria-label={zh ? "产品导航" : "Products"}>
          {[
            [zh ? "首页" : "Home", "home"],
            ["AI SRE", "sparkles"],
            ["On-call", "bell"],
            ["RUM", "chart"],
            [zh ? "API 参考" : "API Reference", "terminal"],
          ].map(([title, icon], index) => {
            const active = kind === "api" ? index === 4 : index === 2;
            const href =
              index === 4
                ? `/${language}/${apiSlug}`
                : index === 2
                  ? `/${language}/${docSlug}`
                  : undefined;
            return href ? (
              <a
                key={title}
                href={href}
                aria-current={active ? "page" : undefined}
                className={active ? "active" : ""}
              >
                <Icon name={icon} />
                {title}
              </a>
            ) : (
              <button key={title} onClick={() => showScope(title)}>
                <Icon name={icon} />
                {title}
              </button>
            );
          })}
        </nav>
      </header>
      {mobile && (
        <button
          className="sidebar-backdrop"
          aria-label={zh ? "关闭导航" : "Close navigation"}
          onClick={() => setMobile(false)}
        />
      )}
      <aside
        className={`sidebar ${mobile ? "mobile-open" : ""}`}
        aria-label={zh ? "文档导航" : "Documentation navigation"}
      >
        {kind === "doc" ? (
          navigation
            .find((item) => item.language === language)
            ?.groups.map((node, i) => renderNav(node as NavNode, i))
        ) : (
          <>
            <section className="side-group">
              <h2>
                <Icon name="book" />
                {zh ? "开发指南" : "Developer guides"}
              </h2>
              {(zh
                ? ["快速入门", "API 目录", "关于分页", "使用限制与错误码"]
                : [
                    "Quick start",
                    "API catalog",
                    "Pagination",
                    "Limits and errors",
                  ]
              ).map((title) => (
                <button
                  className="side-link"
                  key={title}
                  onClick={() => showScope(title)}
                >
                  {title}
                </button>
              ))}
            </section>
            <section className="side-group">
              <h2>
                <Icon name="bell" />
                On-call
              </h2>
              {(zh
                ? [
                    "协作空间",
                    "集成中心",
                    "标签增强",
                    "状态页",
                    "故障管理",
                    "分析看板",
                    "告警管理",
                    "日历管理",
                    "值班排班",
                    "通知模板",
                    "变更管理",
                    "IM 集成",
                    "许可管理",
                  ]
                : [
                    "Channels",
                    "Integrations",
                    "Label enrichment",
                    "Status pages",
                    "Incidents",
                    "Analytics",
                    "Alerts",
                    "Calendars",
                    "Schedules",
                    "Templates",
                    "Changes",
                    "IM integrations",
                    "License",
                  ]
              ).map((title) => (
                <button
                  key={title}
                  className="side-link api-group-link"
                  onClick={() => showScope(title)}
                >
                  On-call/{title}
                  <Icon name="right" />
                </button>
              ))}
              <details open className="api-nav-group">
                <summary>
                  On-call/{zh ? "专属集成" : "Dedicated integrations"}
                  <Icon name="down" />
                </summary>
                {localPages
                  .filter((page) => page.kind === "api")
                  .map((page) => (
                    <a
                      key={page.url}
                      className={`side-link api-link ${page.url === current ? "selected" : ""}`}
                      href={page.url}
                      aria-current={page.url === current ? "page" : undefined}
                    >
                      <span className="method-label">{page.method}</span>
                      {page.title}
                    </a>
                  ))}
              </details>
            </section>
          </>
        )}
      </aside>
      <main
        className={`main-area ${kind === "api" ? "api-area" : ""}`}
        key={current}
      >
        {children}
      </main>
      <dialog
        ref={search}
        className="search-dialog"
        aria-label={zh ? "搜索文档" : "Search documentation"}
        onClick={(event) => {
          if (event.target === event.currentTarget) search.current?.close();
        }}
      >
        <form method="dialog" className="search-input-row">
          <Icon name="search" />
          <input
            ref={input}
            aria-label={zh ? "搜索文档" : "Search documentation"}
            placeholder={zh ? "搜索文档和 API..." : "Search docs and APIs..."}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && results[0]) {
                event.preventDefault();
                window.location.assign(results[0].url);
              }
            }}
          />
          <button aria-label={zh ? "关闭搜索" : "Close search"}>
            <kbd>Esc</kbd>
          </button>
        </form>
        <div className="search-results">
          {results.map((page) => (
            <a key={page.url} href={page.url}>
              <Icon name={page.kind === "api" ? "terminal" : "book"} />
              <div>
                <strong>{page.title}</strong>
                <p>{page.description}</p>
              </div>
              <Icon name="right" />
            </a>
          ))}
          {!results.length && (
            <p className="search-empty">
              {zh ? "没有找到匹配结果" : "No matching results"}
            </p>
          )}
        </div>
        <footer>
          {zh
            ? "搜索此预览中的产品文档和 API"
            : "Search the product docs and APIs in this preview"}
        </footer>
      </dialog>
      <dialog
        ref={scopeDialog}
        className="scope-dialog"
        aria-label={zh ? "样例范围" : "Preview scope"}
      >
        <form method="dialog">
          <button className="icon-button" aria-label={zh ? "关闭" : "Close"}>
            <Icon name="close" />
          </button>
        </form>
        <h2>{scope}</h2>
        <p>
          {zh
            ? "该页面未包含在本次预览中。你可以查看协作空间的 4 篇产品文档，以及 8 个专属集成 API。"
            : "This page is outside this preview. Explore four channel guides and eight dedicated integration APIs."}
        </p>
        <a className="preview-cta" href={`/${language}/${docSlug}`}>
          {zh ? "查看产品文档" : "Explore product docs"}
        </a>
        <a className="preview-cta" href={`/${language}/${apiSlug}`}>
          {zh ? "查看 API" : "Explore APIs"}
        </a>
      </dialog>
    </div>
  );
}

export function TableOfContents({
  items,
  language,
}: {
  items: TOCItemType[];
  language: string;
}) {
  const [active, setActive] = useState(items[0]?.url ?? "");
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries)
          if (entry.isIntersecting) setActive(`#${entry.target.id}`);
      },
      { rootMargin: "-120px 0px -65% 0px" },
    );
    items.forEach((item) => {
      const heading = document.getElementById(
        decodeURIComponent(item.url.slice(1)),
      );
      if (heading) observer.observe(heading);
    });
    return () => observer.disconnect();
  }, [items]);
  return (
    <nav
      className="toc"
      aria-label={language === "zh" ? "在此页面" : "On this page"}
    >
      <h2>
        <Icon name="list" />
        {language === "zh" ? "在此页面" : "On this page"}
      </h2>
      {items.map((item) => (
        <a
          href={item.url}
          key={item.url}
          className={`${item.depth > 2 ? "subheading" : ""} ${active === item.url ? "active" : ""}`}
          onClick={() => setActive(item.url)}
        >
          {item.title}
        </a>
      ))}
    </nav>
  );
}
