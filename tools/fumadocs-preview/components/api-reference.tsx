"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import { createOpenAPIRenderer, useOpenAPI } from "fumadocs-openapi";
import type { OpenAPIPageProps } from "fumadocs-openapi/ui";
import {
  OperationProvider,
  useOperation,
  useCodeUsage,
  useResponseExamples,
  type PageOperationProps,
} from "fumadocs-openapi/operation";
import {
  createCodeUsageGeneratorRegistry,
  type CodeUsageGenerator,
} from "fumadocs-openapi/requests/generators";
import { curl } from "fumadocs-openapi/requests/generators/curl";
import { javascript } from "fumadocs-openapi/requests/generators/javascript";
import { python } from "fumadocs-openapi/requests/generators/python";
import { CopyButton } from "./interactive-mdx";
import { Icon } from "./icons";

type Schema = {
  type?: string | string[];
  format?: string;
  description?: string;
  properties?: Record<string, Schema>;
  required?: string[];
  items?: Schema;
  allOf?: Schema[];
  oneOf?: Schema[];
  anyOf?: Schema[];
  enum?: unknown[];
  default?: unknown;
  minimum?: number;
  maximum?: number;
};
const Content = createContext<{ language: string; intro: ReactNode }>({
  language: "zh",
  intro: null,
});
const codeUsages = createCodeUsageGeneratorRegistry();
function withAppKey(generator: CodeUsageGenerator): CodeUsageGenerator {
  return {
    ...generator,
    generate: (data, context) =>
      generator.generate(
        {
          ...data,
          header: { ...data.header, "Fd-App-Key": { value: "<APP_KEY>" } },
        },
        context,
      ),
  };
}
codeUsages.add("curl", {
  ...curl,
  generate(data, context) {
    const code = withAppKey(curl).generate(data, context);
    return code
      .replace(/^curl -X (\w+) /, "curl --request $1 \\\n  --url ")
      .replace(/\n  -H /g, "\n  --header ")
      .replace(/\n  -d '/, "\n  --data '\n")
      .replace(/}'$/, "}\n'");
  },
});
codeUsages.add("javascript", withAppKey(javascript));
codeUsages.add("python", withAppKey(python));

function Operation(props: PageOperationProps) {
  return (
    <OperationProvider {...props}>
      <OperationContent />
    </OperationProvider>
  );
}
const Renderer = createOpenAPIRenderer({
  components: { Operation, SchemaUI: () => null },
  codeUsages,
  generateTypeScriptDefinitions: false,
});

export function APIReference({
  language,
  intro,
  ...props
}: OpenAPIPageProps & { language: string; intro: ReactNode }) {
  return (
    <Content.Provider value={{ language, intro }}>
      <Renderer {...props} />
    </Content.Provider>
  );
}

function Inline({ text }: { text: string }) {
  return (
    <>
      {text
        .split(/(`[^`]+`|\*\*[^*]+\*\*)/g)
        .map((part, index) =>
          part.startsWith("`") ? (
            <code key={index}>{part.slice(1, -1)}</code>
          ) : part.startsWith("**") ? (
            <strong key={index}>{part.slice(2, -2)}</strong>
          ) : (
            part
          ),
        )}
    </>
  );
}

function SchemaFields({
  schema,
  depth = 0,
}: {
  schema: Schema;
  depth?: number;
}) {
  const { doc } = useOpenAPI();
  const { language } = useContext(Content);
  const zh = language === "zh";
  function resolveSchema(raw: Schema): Schema {
    const resolved = doc.resolve(raw);
    if (!resolved.allOf) return resolved;
    const parts = resolved.allOf.map(resolveSchema);
    return {
      ...resolved,
      properties: Object.assign(
        {},
        ...parts.map((part) => part.properties ?? {}),
        resolved.properties,
      ),
      required: [
        ...new Set([
          ...parts.flatMap((part) => part.required ?? []),
          ...(resolved.required ?? []),
        ]),
      ],
    };
  }
  function hasFields(raw: Schema, level = 0): boolean {
    if (level > 6) return false;
    const value = resolveSchema(raw);
    return (
      !!value.properties ||
      !!(value.items && hasFields(value.items, level + 1)) ||
      (value.oneOf ?? value.anyOf ?? []).some((item) =>
        hasFields(item, level + 1),
      )
    );
  }
  const resolved = resolveSchema(schema);
  const alternatives = resolved.oneOf ?? resolved.anyOf;
  if (alternatives?.some((branch) => hasFields(branch)))
    return (
      <div className="schema-alternatives">
        {alternatives.map((branch, index) => (
          <details key={index}>
            <summary>
              {resolved.oneOf ? "oneOf" : "anyOf"} · {index + 1}
            </summary>
            <SchemaFields schema={branch} depth={depth + 1} />
          </details>
        ))}
      </div>
    );
  if (resolved.type === "array" && resolved.items)
    return <SchemaFields schema={resolved.items} depth={depth} />;
  const fields = Object.entries(resolved.properties ?? {});
  if (!fields.length)
    return resolved.description ? (
      <p className="schema-description">
        <Inline text={resolved.description} />
      </p>
    ) : null;
  return (
    <div className="schema-fields">
      {fields.map(([name, raw]) => {
        const property = resolveSchema(raw);
        const item = property.items ? resolveSchema(property.items) : undefined;
        const nested = hasFields(property);
        const type = Array.isArray(property.type)
          ? property.type.join(" | ")
          : (property.type ?? (property.properties ? "object" : "any"));
        return (
          <section className="schema-field" key={name}>
            <header>
              <code>{name}</code>
              <span className="field-type">
                {type}
                {item ? ` · ${item.type ?? "object"}` : ""}
                {property.format ? ` · ${property.format}` : ""}
              </span>
              {resolved.required?.includes(name) && (
                <span className="required">{zh ? "必填" : "required"}</span>
              )}
            </header>
            {property.description && (
              <p>
                <Inline text={property.description} />
              </p>
            )}
            {property.default !== undefined && (
              <p className="field-meta">
                {zh ? "默认值" : "Default"}:{" "}
                <code>{JSON.stringify(property.default)}</code>
              </p>
            )}
            {property.enum && (
              <p className="field-meta">
                {zh ? "可选值" : "Allowed values"}:{" "}
                {property.enum.map((value, index) => (
                  <code key={index}>{JSON.stringify(value)}</code>
                ))}
              </p>
            )}
            {(property.minimum !== undefined ||
              property.maximum !== undefined) && (
              <p className="field-meta">
                {zh ? "范围" : "Range"}: {property.minimum ?? "−∞"} –{" "}
                {property.maximum ?? "∞"}
              </p>
            )}
            {nested && depth < 6 && (
              <details className="nested-schema">
                <summary>
                  <Icon name="right" />
                  {zh ? "显示子字段" : "Show child attributes"}
                </summary>
                <SchemaFields schema={item ?? property} depth={depth + 1} />
              </details>
            )}
          </section>
        );
      })}
    </div>
  );
}

function HighlightedCode({
  code,
  json = false,
}: {
  code: string;
  json?: boolean;
}) {
  const tokens = code.split(
    /("(?:\\.|[^"\\])*"|'[^']*'|\b\d+(?:\.\d+)?\b|\b(?:true|false|null)\b|--[\w-]+)/g,
  );
  return (
    <pre>
      <code>
        {tokens.map((part, index) => {
          const isString = part.startsWith('"') || part.startsWith("'");
          const isKey =
            json && isString && tokens[index + 1]?.trimStart().startsWith(":");
          const cls = isKey
            ? "code-key"
            : isString
              ? "code-string"
              : /^(\d|true|false|null)/.test(part)
                ? "code-value"
                : part.startsWith("--")
                  ? "code-flag"
                  : undefined;
          return cls ? (
            <span className={cls} key={index}>
              {part}
            </span>
          ) : (
            part
          );
        })}
      </code>
    </pre>
  );
}

function OperationContent() {
  const { language, intro } = useContext(Content);
  const zh = language === "zh";
  const {
    path,
    method,
    title,
    description,
    requestBody,
    parameters,
    security,
    responses,
  } = useOperation();
  const responseExamples = useResponseExamples();
  const [status, setStatus] = useState(responses[0]?.status ?? "200");
  const [codeLanguage, setCodeLanguage] = useState("curl");
  const generatedCode = useCodeUsage(codeLanguage) ?? "";
  const response =
    responses.find((item) => item.status === status) ?? responses[0];
  const example = responseExamples.find((item) => item.code === status)
    ?.examples?.[0]?.sample;
  const responseCode =
    example === undefined ? "" : JSON.stringify(example, null, 2);
  const responseSchema = response?.content["application/json"]?.schema;
  const bodySchema = requestBody?.content["application/json"]?.schema;
  return (
    <div className="api-grid">
      <article className="api-article">
        <header className="page-heading">
          <div className="eyebrow">
            On-call/{zh ? "专属集成" : "Dedicated integrations"}
          </div>
          <h1>{title}</h1>
          <p className="page-description">{description}</p>
        </header>
        <div className="endpoint-bar">
          <span className="method-label">{method.toUpperCase()}</span>
          <code>{path}</code>
        </div>
        <div className="prose api-intro">{intro}</div>
        <div className="api-schema-content">
          {!!security.length && (
            <section>
              <h2 id="authorization">{zh ? "授权" : "Authorizations"}</h2>
              {security[0].map(({ key, scheme }) => (
                <div className="schema-field" key={key}>
                  <header>
                    <code>{scheme?.type === "apiKey" ? scheme.name : key}</code>
                    <span className="field-type">
                      {scheme?.type === "apiKey"
                        ? `${scheme.in} · string`
                        : scheme?.type}
                    </span>
                    <span className="required">{zh ? "必填" : "required"}</span>
                  </header>
                  <p>
                    <Inline text={scheme?.description ?? ""} />
                  </p>
                </div>
              ))}
            </section>
          )}
          {parameters.map((group) => (
            <section key={group.in}>
              <h2>
                {group.in} {zh ? "参数" : "parameters"}
              </h2>
              {group.items.map((parameter) => (
                <div className="schema-field" key={parameter.name}>
                  <header>
                    <code>{parameter.name}</code>
                    {parameter.required && (
                      <span className="required">
                        {zh ? "必填" : "required"}
                      </span>
                    )}
                  </header>
                  <p>{parameter.description}</p>
                </div>
              ))}
            </section>
          ))}
          {bodySchema && (
            <section>
              <h2 id="request-body">
                {zh ? "请求体" : "Body"}
                <span className="media-type">application/json</span>
              </h2>
              <SchemaFields schema={bodySchema as Schema} />
            </section>
          )}
          {response && (
            <section>
              <h2 id="response">
                {zh ? "响应" : "Response"}
                <select
                  aria-label={zh ? "响应结构状态码" : "Response schema status"}
                  value={status}
                  onChange={(event) => setStatus(event.target.value)}
                >
                  {responses.map((item) => (
                    <option key={item.status}>{item.status}</option>
                  ))}
                </select>
              </h2>
              <p className="schema-description">
                {response.response.description}
              </p>
              {responseSchema && (
                <SchemaFields key={status} schema={responseSchema as Schema} />
              )}
            </section>
          )}
        </div>
      </article>
      <aside
        className="api-examples"
        aria-label={zh ? "请求与响应示例" : "Request and response examples"}
      >
        <div className="example-card request-example">
          <div className="example-toolbar">
            <strong>{title}</strong>
            <label>
              <Icon name="terminal" />
              <select
                aria-label={zh ? "示例代码语言" : "Code example language"}
                value={codeLanguage}
                onChange={(event) => setCodeLanguage(event.target.value)}
              >
                <option value="curl">cURL</option>
                <option value="javascript">JavaScript</option>
                <option value="python">Python</option>
              </select>
            </label>
            <CopyButton text={generatedCode} />
          </div>
          <HighlightedCode code={generatedCode} />
        </div>
        <div className="example-card response-example">
          <div
            className="example-toolbar response-tabs"
            role="tablist"
            aria-label={zh ? "响应状态码" : "Response status"}
          >
            {responses.map((item) => (
              <button
                key={item.status}
                type="button"
                role="tab"
                aria-selected={status === item.status}
                aria-controls={`example-${item.status}`}
                id={`status-${item.status}`}
                tabIndex={status === item.status ? 0 : -1}
                onKeyDown={(event) => {
                  if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
                  event.preventDefault();
                  const index = responses.findIndex((r) => r.status === status);
                  const next =
                    responses[
                      (index +
                        (event.key === "ArrowRight"
                          ? 1
                          : responses.length - 1)) %
                        responses.length
                    ].status;
                  setStatus(next);
                  document.getElementById(`status-${next}`)?.focus();
                }}
                onClick={() => setStatus(item.status)}
              >
                {item.status}
              </button>
            ))}
            <CopyButton text={responseCode} />
          </div>
          <div
            role="tabpanel"
            id={`example-${status}`}
            aria-labelledby={`status-${status}`}
          >
            <HighlightedCode
              code={responseCode || (zh ? "无响应体" : "No response body")}
              json
            />
          </div>
        </div>
      </aside>
    </div>
  );
}
