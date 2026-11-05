"use client";

import { useEffect, useState, type RefObject } from "react";
import Icon from "@/components/ui/Icon";

export interface Cue {
  start: number;
  end: number;
  text: string;
}

function secs(stamp: string): number {
  const [h, m, s] = stamp.trim().replace(",", ".").split(":");
  return Number(h) * 3600 + Number(m) * 60 + Number(s);
}

/** Parse the film's WebVTT captions into cues. */
export function parseVtt(vtt: string): Cue[] {
  const cues: Cue[] = [];
  for (const block of vtt.replace(/\r/g, "").split(/\n\s*\n/)) {
    const lines = block.split("\n");
    const i = lines.findIndex((l) => l.includes("-->"));
    if (i < 0) continue;
    const [a, b] = lines[i].split("-->");
    const text = lines.slice(i + 1).join(" ").trim();
    if (text) cues.push({ start: secs(a), end: secs(b), text });
  }
  return cues;
}

/** Which word is being spoken at time t: the cue's time is shared out by word length (an estimate; Meta's
 *  speech API gives turn-level timestamps only, and the edge-tts narration gives none). */
export function wordAt(cue: Cue, t: number): number {
  const words = cue.text.split(/\s+/);
  const total = words.reduce((n, w) => n + w.length + 1, 0);
  const p = Math.min(0.999, Math.max(0, (t - cue.start) / Math.max(0.1, cue.end - cue.start)));
  let acc = 0;
  for (let k = 0; k < words.length; k++) {
    acc += words[k].length + 1;
    if (acc / total > p) return k;
  }
  return words.length - 1;
}

/** "Baca bersama · Read along": karaoke captions under the player, the spoken word highlighted, big type. */
export default function ReadAlong({ video, src, lang }: { video: RefObject<HTMLVideoElement | null>; src?: string; lang: string }) {
  const [cues, setCues] = useState<Cue[]>([]);
  const [t, setT] = useState(0);
  const [on, setOn] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!src) return;
    fetch(src)
      .then((r) => (r.ok ? r.text() : ""))
      .then((v) => {
        const c = parseVtt(v);
        setCues(c);
        setFailed(!c.length);
      })
      .catch(() => setFailed(true));
  }, [src]);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      if (video.current) setT(video.current.currentTime);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [video]);

  // while the captions load, the same block is drawn (with "…"), so nothing below jumps when they arrive
  if (!src || failed) return null;
  const cue = cues.find((c) => t >= c.start && t < c.end);
  const k = cue ? wordAt(cue, t) : -1;
  return (
    <div className="space-y-2" data-testid={cues.length ? "read-along" : undefined}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <button type="button" className="chip" aria-pressed={on} onClick={() => setOn(!on)}>
          <Icon name="book" className="h-4 w-4" /> Baca bersama · Read along {on ? "✓" : ""}
        </button>
        {on && (
          <p className="t-tiny max-w-sm text-muted">
            Kata disorot mengikuti suara (perkiraan) · Words light up with the voice (estimated timing). Teks juga
            tertanam di video · Captions are also burned into the video.
          </p>
        )}
      </div>
      {on && (
        <p
          className="kelir grid min-h-[5.5rem] place-items-center rounded-lg px-4 py-3 text-center font-display text-2xl font-medium leading-snug sm:text-3xl"
          style={{ boxShadow: "inset 0 -20px 40px -24px rgb(110 60 20 / .5)" }}
          lang={lang}
          aria-hidden="true"
        >
          <span>
            {cue
              ? cue.text.split(/\s+/).map((w, i) => (
                  <span
                    key={i}
                    className={
                      i === k
                        ? "rounded-md bg-on-kelir px-1 text-kelir"
                        : i < k
                          ? "text-on-kelir"
                          : "text-on-kelir/45"
                    }
                  >
                    {w}{" "}
                  </span>
                ))
              : <span className="text-lg font-normal text-on-kelir/60">{cues.length && t > 0 ? "…" : "Putar filmnya, kata-katanya menyala di sini · Play the film and the words light up here"}</span>}
          </span>
        </p>
      )}
    </div>
  );
}
