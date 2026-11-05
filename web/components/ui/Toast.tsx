"use client";

import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import Icon from "@/components/ui/Icon";

type Tone = "info" | "error" | "ok";
interface Item {
  id: number;
  text: string;
  tone: Tone;
}

const Ctx = createContext<(text: string, tone?: Tone) => void>(() => {});

/** toast("Saved", "ok"): a short message at the bottom of the screen, read out politely, gone after 5 s. */
export function useToast() {
  return useContext(Ctx);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Item[]>([]);
  const n = useRef(0);
  const show = useCallback((text: string, tone: Tone = "info") => {
    const id = ++n.current;
    setItems((xs) => [...xs.slice(-2), { id, text, tone }]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 5000);
  }, []);
  return (
    <Ctx.Provider value={show}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 pb-[max(1rem,env(safe-area-inset-bottom))]"
        role="status"
        aria-live="polite"
      >
        {items.map((t) => (
          <div
            key={t.id}
            className={`toast-in pointer-events-auto flex max-w-md items-start gap-3 rounded-lg border px-4 py-3 text-sm shadow-2 ${
              t.tone === "error"
                ? "border-err/40 bg-surface text-fg"
                : t.tone === "ok"
                  ? "border-ok/40 bg-surface text-fg"
                  : "border-gold/30 bg-surface text-fg"
            }`}
          >
            <Icon
              name={t.tone === "error" ? "alert" : t.tone === "ok" ? "check" : "info"}
              className={`mt-0.5 h-5 w-5 ${t.tone === "error" ? "text-err" : t.tone === "ok" ? "text-ok" : "text-gold"}`}
            />
            <p>{t.text}</p>
            <button
              type="button"
              className="-my-1 -mr-2 ml-auto grid h-8 w-8 shrink-0 place-items-center rounded-full hover:bg-fg/10"
              onClick={() => setItems((xs) => xs.filter((x) => x.id !== t.id))}
              aria-label="Tutup · Dismiss"
            >
              <Icon name="close" className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
