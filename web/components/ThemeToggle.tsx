"use client";

import { useSyncExternalStore } from "react";
import Icon from "@/components/ui/Icon";

const KEY = "dalang-theme";
const listeners = new Set<() => void>();
function subscribe(f: () => void) {
  listeners.add(f);
  return () => listeners.delete(f);
}
const read = () => (document.documentElement.dataset.theme === "light" ? "light" : "dark");

/** Night (default, the audience side of the kelir) or day. Remembered on this device. */
export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, read, () => "dark");
  const light = theme === "light";
  return (
    <button
      type="button"
      className="btn btn-sm"
      aria-pressed={light}
      onClick={() => {
        const next = light ? "dark" : "light";
        if (next === "light") document.documentElement.dataset.theme = "light";
        else delete document.documentElement.dataset.theme;
        try {
          localStorage.setItem(KEY, next);
        } catch {
          /* private mode: the choice lasts until the tab closes */
        }
        listeners.forEach((f) => f());
      }}
    >
      <Icon name="sun" className="h-4 w-4" />
      Mode siang · Day mode
    </button>
  );
}

/** Runs before the first paint (inline in <head>) so a saved day theme never flashes dark. */
export const THEME_SCRIPT = `try{if(localStorage.getItem("${KEY}")==="light")document.documentElement.dataset.theme="light"}catch(e){}`;
