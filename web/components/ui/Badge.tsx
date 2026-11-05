import type { ReactNode } from "react";

type Tone = "sample" | "placeholder" | "warn" | "ok" | "quiet";

// full class names (not built from the tone) so Tailwind keeps them in the CSS
const TONE: Record<Tone, string> = {
  sample: "badge badge-sample",
  placeholder: "badge badge-placeholder",
  warn: "badge badge-warn",
  ok: "badge badge-ok",
  quiet: "badge badge-quiet",
};

/** Small status label. Sample/placeholder labels must stay visible on every film made with placeholder art. */
export default function Badge({ tone = "quiet", children, className = "" }: { tone?: Tone; children: ReactNode; className?: string }) {
  return <span className={`${TONE[tone]} ${className}`}>{children}</span>;
}
