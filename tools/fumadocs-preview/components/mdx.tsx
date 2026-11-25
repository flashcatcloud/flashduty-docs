import defaultMdxComponents from "fumadocs-ui/mdx";
import type { MDXComponents } from "mdx/types";
import type { ReactNode } from "react";
import { Icon } from "./icons";
import { Tab, Tabs } from "./interactive-mdx";

function Callout({ children, type }: { children: ReactNode; type: string }) {
  return (
    <aside className={`mint-callout ${type}`}>
      <Icon
        name={type === "tip" ? "tip" : type === "warning" ? "warning" : "info"}
      />
      <div>{children}</div>
    </aside>
  );
}
function Accordion({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: string;
  children: ReactNode;
}) {
  return (
    <details className="mint-accordion">
      <summary>
        {icon && <Icon name={icon} />}
        <span>{title}</span>
        <Icon name="down" />
      </summary>
      <div>{children}</div>
    </details>
  );
}
function Card({
  title,
  icon,
  href,
  children,
}: {
  title: string;
  icon?: string;
  href?: string;
  children: ReactNode;
}) {
  return (
    <a className="mint-card" href={href}>
      {icon && <Icon name={icon} />}
      <h3>{title}</h3>
      <div>{children}</div>
    </a>
  );
}
export function getMDXComponents(): MDXComponents {
  return {
    ...defaultMdxComponents,
    a: (props) => <a {...props} />,
    h2: ({ id, children }) => (
      <h2 id={id}>
        <a className="heading-link" href={`#${id}`}>
          {children}
        </a>
      </h2>
    ),
    h3: ({ id, children }) => (
      <h3 id={id}>
        <a className="heading-link" href={`#${id}`}>
          {children}
        </a>
      </h3>
    ),
    table: ({ children }) => (
      <div className="table-scroll">
        <table>{children}</table>
      </div>
    ),
    th: (props) => <th {...props} />,
    td: (props) => <td {...props} />,
    tr: (props) => <tr {...props} />,
    Tabs,
    Tab,
    Note: ({ children }) => <Callout type="note">{children}</Callout>,
    Info: ({ children }) => <Callout type="info">{children}</Callout>,
    Tip: ({ children }) => <Callout type="tip">{children}</Callout>,
    Warning: ({ children }) => <Callout type="warning">{children}</Callout>,
    Accordion,
    AccordionGroup: ({ children }) => (
      <div className="mint-accordion-group">{children}</div>
    ),
    Frame: ({ children, caption }) => (
      <figure className="mint-frame">
        <div>{children}</div>
        {caption && <figcaption>{caption}</figcaption>}
      </figure>
    ),
    Steps: ({ children }) => <ol className="mint-steps">{children}</ol>,
    Step: ({ title, children }) => (
      <li>
        <h3>{title}</h3>
        <div>{children}</div>
      </li>
    ),
    Card,
    CardGroup: ({ children, cols = 2 }) => (
      <div
        className="mint-cards"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
      >
        {children}
      </div>
    ),
  };
}
