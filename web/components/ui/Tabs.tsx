"use client";

import { useRef, type ReactNode } from "react";

export interface TabItem<K extends string> {
  key: K;
  label: ReactNode;
}

/**
 * Segmented tabs (WAI-ARIA tabs pattern): arrow keys move between tabs, Home/End jump, the selected tab is the
 * only one in the tab order. The panel is rendered by the caller with id `${idBase}-panel`.
 */
export default function Tabs<K extends string>({
  items,
  value,
  onChange,
  label,
  idBase,
  className = "",
}: {
  items: TabItem<K>[];
  value: K;
  onChange: (k: K) => void;
  label: string;
  idBase: string;
  className?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  function move(i: number) {
    const k = (i + items.length) % items.length;
    onChange(items[k].key);
    refs.current[k]?.focus();
  }
  return (
    <div
      role="tablist"
      aria-label={label}
      className={`seg ${className}`}
      style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
    >
      {items.map((t, i) => {
        const on = t.key === value;
        return (
          <button
            key={t.key}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`${idBase}-tab-${t.key}`}
            aria-selected={on}
            aria-controls={`${idBase}-panel`}
            tabIndex={on ? 0 : -1}
            onClick={() => onChange(t.key)}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight") move(i + 1);
              else if (e.key === "ArrowLeft") move(i - 1);
              else if (e.key === "Home") move(0);
              else if (e.key === "End") move(items.length - 1);
              else return;
              e.preventDefault();
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
