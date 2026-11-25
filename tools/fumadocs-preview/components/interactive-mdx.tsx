"use client";

import {
  Children,
  isValidElement,
  useId,
  useState,
  type ReactNode,
  type ReactElement,
} from "react";
import { Icon } from "./icons";

export function Tab({ children }: { children: ReactNode; title: string }) {
  return <>{children}</>;
}
export function Tabs({ children }: { children: ReactNode }) {
  const tabs = Children.toArray(children).filter(
    isValidElement,
  ) as ReactElement<{ title: string; children: ReactNode }>[];
  const [selected, setSelected] = useState(0);
  const id = useId();
  return (
    <div className="mint-tabs">
      <div role="tablist">
        {tabs.map((tab, index) => (
          <button
            key={index}
            type="button"
            id={`${id}-tab-${index}`}
            role="tab"
            aria-selected={selected === index}
            aria-controls={`${id}-panel-${index}`}
            tabIndex={selected === index ? 0 : -1}
            onClick={() => setSelected(index)}
            onKeyDown={(event) => {
              let next = selected;
              if (event.key === "ArrowRight")
                next = (selected + 1) % tabs.length;
              else if (event.key === "ArrowLeft")
                next = (selected + tabs.length - 1) % tabs.length;
              else if (event.key === "Home") next = 0;
              else if (event.key === "End") next = tabs.length - 1;
              else return;
              event.preventDefault();
              setSelected(next);
              document.getElementById(`${id}-tab-${next}`)?.focus();
            }}
          >
            {tab.props.title}
          </button>
        ))}
      </div>
      {tabs.map((tab, index) => (
        <div
          key={index}
          id={`${id}-panel-${index}`}
          role="tabpanel"
          aria-labelledby={`${id}-tab-${index}`}
          hidden={selected !== index}
          tabIndex={0}
        >
          {tab.props.children}
        </div>
      ))}
    </div>
  );
}
export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  function legacyCopy() {
    const previous = document.activeElement;
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("aria-hidden", "true");
    area.style.cssText = "position:fixed;top:0;left:0;opacity:0;";
    document.body.append(area);
    area.select();
    let success = false;
    try {
      success = document.execCommand("copy");
    } finally {
      area.remove();
      if (previous instanceof HTMLElement) previous.focus();
    }
    return success;
  }
  return (
    <button
      className="copy-button icon-button"
      aria-label={
        copied
          ? "Copied"
          : failed
            ? "Select the code and copy manually"
            : "Copy code"
      }
      title={
        copied
          ? "Copied"
          : failed
            ? "Select the code and copy manually"
            : "Copy code"
      }
      onClick={async () => {
        try {
          if (navigator.clipboard) {
            await navigator.clipboard.writeText(text);
            setCopied(true);
          } else {
            const success = legacyCopy();
            setCopied(success);
            setFailed(!success);
          }
        } catch {
          const success = legacyCopy();
          setCopied(success);
          setFailed(!success);
        }
      }}
      onBlur={() => setCopied(false)}
    >
      <Icon name={copied ? "check" : "copy"} />
      {failed && (
        <span className="sr-only" role="status">
          Select the code and copy manually.
        </span>
      )}
    </button>
  );
}
