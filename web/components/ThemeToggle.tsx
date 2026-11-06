"use client";

import { useSyncExternalStore } from "react";
import Icon from "@/components/ui/Icon";

const KEY = "dalang-theme";
const listeners = new Set<() => void>();
function subscribe(f: () => void) {
  listeners.add(f);
  return () => listeners.delete(f);
}
// The browser bar colour (meta theme-color) follows the theme, so day mode has no dark strip on top on phones.
const BAR = { dark: "#0C0A1E", light: "#FAF4E8" } as const;
const paintBar = (t: keyof typeof BAR) =>
  document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.setAttribute("content", BAR[t]));
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
        paintBar(next);
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
export const THEME_SCRIPT = `try{if(localStorage.getItem("${KEY}")==="light"){document.documentElement.dataset.theme="light";addEventListener("DOMContentLoaded",function(){document.querySelectorAll('meta[name="theme-color"]').forEach(function(m){m.setAttribute("content","${BAR.light}")})})}}catch(e){}`;
