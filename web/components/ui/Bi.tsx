import type { ReactNode } from "react";

/**
 * A bilingual pair: Bahasa Indonesia (or Javanese) first, English second. The text stays "id · en" exactly, so
 * screen readers, tests and copy-paste get the same words; only the look changes. `stack` (for headings) puts
 * English under it as a small sans-serif subtitle and hides the dot visually (it is still in the text). `wrap` does the same only below 480 px.
 */
export default function Bi({
  id,
  en,
  stack = false,
  wrap = false,
}: {
  id: ReactNode;
  en: ReactNode;
  stack?: boolean;
  /** on narrow phones, English drops to its own smaller line (for long button labels) */
  wrap?: boolean;
}) {
  return (
    <span className={wrap ? "bi-wrap" : undefined}>
      {id}
      <span className={stack ? "sr-only" : "bi-sep"}> · </span>
      <span lang="en" className={stack ? "bi-sub" : "bi-en"}>
        {en}
      </span>
    </span>
  );
}
