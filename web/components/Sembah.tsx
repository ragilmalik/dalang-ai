"use client";

import { useState, useSyncExternalStore } from "react";

const noop = () => () => {};

/** Community vote: a "Sembah" (the Javanese bow of thanks) instead of a like. One tap per visitor. */
export default function Sembah({ id, initial }: { id: string; initial: number }) {
  const key = `sembah:${id}`;
  const [count, setCount] = useState(initial);
  const [justGave, setJustGave] = useState(false);
  // remembered on this device; read after hydration so the server and the phone render the same first frame
  const stored = useSyncExternalStore(noop, () => localStorage.getItem(key) === "1", () => false);
  const given = justGave || stored;

  async function give() {
    if (given) return;
    const r = await fetch(`/api/jobs/${id}/applause`, { method: "POST" });
    if (r.ok) {
      setCount((await r.json()).applause);
      setJustGave(true);
      localStorage.setItem(key, "1");
    }
  }

  return (
    <button
      type="button"
      className={`btn tabular ${given ? "!cursor-default !border-prada !bg-prada/15 !opacity-100" : ""}`}
      onClick={give}
      disabled={given}
      aria-pressed={given}
      aria-label={`Sembah, ${count} so far`}
    >
      <span aria-hidden="true">🙏</span> Sembah · {count}
    </button>
  );
}
