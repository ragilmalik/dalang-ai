"use client";

import data from "@/lib/starters.json";
import Bi from "@/components/ui/Bi";
import Icon from "@/components/ui/Icon";

export interface Starter {
  id: string;
  emoji: string;
  title: string;
  region: string;
  id_text: string;
  jv: string;
  en: string;
}

export const STARTERS: Starter[] = data.items;

export function starterText(s: Starter, lang: "id" | "jv" | "en"): string {
  return lang === "id" ? s.id_text : lang === "jv" ? s.jv : s.en;
}

/** One-tap Story Starters: public-domain Nusantara folk tales, short enough for a child to read aloud. */
export default function StoryStarters({
  lang,
  picked,
  onPick,
}: {
  lang: "id" | "jv" | "en";
  picked: string | null;
  onPick: (s: Starter) => void;
}) {
  return (
    <div className="space-y-3" data-testid="story-starters">
      <div>
        <h3 className="t-h3">
          <Bi stack id="Mulai dari dongeng" en="Story starters" />
        </h3>
        <p className="t-small mt-2 text-muted">
          <Bi id="Ketuk satu, lalu bacakan keras-keras atau ubah sesukamu" en="Tap one, then read it aloud or change it your way" />
        </p>
      </div>
      <ul className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {STARTERS.map((s) => {
          const on = picked === s.id;
          return (
            <li key={s.id}>
              <button
                type="button"
                className={`group relative block w-full overflow-hidden rounded-lg border text-left transition-[border-color,box-shadow,transform] duration-kenong ease-sabet active:scale-[0.98] ${
                  on ? "border-prada shadow-lamp" : "border-gold/20 hover:border-gold/60"
                }`}
                aria-pressed={on}
                onClick={() => onPick(s)}
              >
                {/* the tale's emoji cast as a shadow on a little lamp-lit kelir */}
                <span className="starter-kelir relative grid aspect-[16/10] place-items-center" aria-hidden="true">
                  <span className="shadow-emoji text-5xl transition-transform duration-gong ease-sabet group-hover:-rotate-3 group-hover:scale-110">
                    {s.emoji}
                  </span>
                  {on && (
                    <span className="absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-full bg-prada text-on-prada shadow-1">
                      <Icon name="check" className="h-4 w-4" strokeWidth={2.4} />
                    </span>
                  )}
                </span>
                <span className={`block px-3 py-2 ${on ? "bg-prada text-on-prada" : "bg-bg-2"}`}>
                  <span className="block text-sm font-bold leading-tight">{s.title}</span>
                  <span className={`block text-xs ${on ? "text-on-prada/80" : "text-muted"}`}>{s.region}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {picked && (
        <p
          className="kelir rise rounded-lg p-4 text-center font-display text-xl font-medium leading-relaxed sm:p-5 sm:text-2xl"
          lang={lang}
          data-testid="starter-read-aloud"
        >
          {starterText(STARTERS.find((s) => s.id === picked) as Starter, lang)}
        </p>
      )}
    </div>
  );
}
