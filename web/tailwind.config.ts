import type { Config } from "tailwindcss";

/**
 * Dalang AI design tokens. Every colour is a CSS variable (app/globals.css) holding "R G B", so Tailwind's
 * opacity modifiers work (bg-surface/80) and the light theme only swaps the variables. Names come from the
 * shadow theatre: malam = night, nila = indigo, kelir = the lit screen, prada = the gold leaf on a puppet,
 * soga = the brown of batik soga dye, sindur = vermilion, kembang = flower (the second vote colour).
 * See docs/DESIGN_SYSTEM.md.
 */
const v = (name: string) => `rgb(var(--c-${name}) / <alpha-value>)`;

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v("bg"),
        "bg-2": v("bg-2"),
        surface: v("surface"),
        "surface-2": v("surface-2"),
        fg: v("fg"),
        muted: v("muted"),
        gold: v("gold"),
        prada: v("prada"),
        "prada-hi": v("prada-hi"),
        "on-prada": v("on-prada"),
        kelir: v("kelir"),
        "on-kelir": v("on-kelir"),
        soga: v("soga"),
        sindur: v("sindur"),
        kembang: v("kembang"),
        ok: v("ok"),
        err: v("err"),
        // older names still used in a few places
        cream: v("fg"),
        ink: v("on-prada"),
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        serif: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-text)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "DejaVu Sans Mono", "Liberation Mono", "monospace"],
      },
      borderRadius: {
        sm: "var(--r-sm)",
        md: "var(--r-md)",
        lg: "var(--r-lg)",
        xl: "var(--r-xl)",
        "2xl": "var(--r-xl)",
      },
      boxShadow: {
        1: "var(--sh-1)",
        2: "var(--sh-2)",
        lamp: "var(--glow-lamp)",
      },
      transitionDuration: {
        ketuk: "var(--dur-ketuk)",
        kenong: "var(--dur-kenong)",
        gong: "var(--dur-gong)",
      },
      transitionTimingFunction: {
        sabet: "var(--ease-sabet)",
        gong: "var(--ease-gong)",
      },
      maxWidth: {
        prose: "40rem",
        stage: "72rem",
      },
    },
  },
  plugins: [],
};
export default config;
