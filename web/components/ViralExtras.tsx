"use client";

import { useEffect, useRef, useState } from "react";
import { filmFileName } from "@/lib/share";
import type { Stickers } from "@/lib/api";
import Icon from "@/components/ui/Icon";

/**
 * WhatsApp sticker pack (the film's puppets, WebP 512) and a looping GIF of the film, for the share bar.
 * Hidden when the API has no sticker route (404) or the puppets are not cut out yet (409).
 * The pack is made on its first request (a few seconds of image work on the API), so it is asked for only when the
 * share bar comes near the screen, not on page load.
 */
export default function ViralExtras({ id, title }: { id: string; title: string }) {
  const [s, setS] = useState<Stickers | null>(null);
  const [gif, setGif] = useState(false);
  const near = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let alive = true;
    const load = () =>
      fetch(`/api/jobs/${id}/stickers`)
        .then((r) => (r.ok ? r.json() : null))
        .then((d: Stickers | null) => alive && setS(d))
        .catch(() => {});
    const el = near.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      load();
      return () => {
        alive = false;
      };
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          io.disconnect();
          load();
        }
      },
      { rootMargin: "800px 0px" },
    );
    io.observe(el);
    return () => {
      alive = false;
      io.disconnect();
    };
  }, [id]);
  if (!s || !s.stickers.length) return <div ref={near} aria-hidden="true" className="!m-0 h-0" />;
  const base = filmFileName(title, "landscape").replace(/-16x9\.mp4$/, "");
  return (
    <div className="space-y-3 rounded-lg border border-gold/15 bg-bg-2/60 p-4" data-testid="viral-extras">
      <p className="flex items-center gap-2 font-semibold">
        <Icon name="sticker" className="h-5 w-5 text-gold" /> Stiker WhatsApp & GIF · Stickers and a GIF to share
      </p>
      <ul className="flex flex-wrap gap-2">
        {s.stickers.slice(0, 6).map((st) => (
          <li key={st.id} className="grid h-20 w-20 place-items-center rounded-md bg-fg/5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={st.url} alt={`Sticker: ${st.name}`} width={64} height={64} loading="lazy" className="h-16 w-16 object-contain" />
          </li>
        ))}
      </ul>
      <div className="grid gap-2 sm:flex sm:flex-wrap">
        <a className="btn btn-sm justify-start sm:justify-center" href={s.zip} download={`${base}-stickers.zip`}>
          <Icon name="download" className="h-4 w-4" /> Unduh stiker · Sticker pack (.zip)
        </a>
        <a className="btn btn-sm justify-start sm:justify-center" href={s.gif} download={`${base}.gif`}>
          <Icon name="film" className="h-4 w-4" /> Unduh GIF · Download GIF
        </a>
        {!gif && (
          <button type="button" className="btn btn-sm justify-start sm:justify-center" onClick={() => setGif(true)}>
            <Icon name="eye" className="h-4 w-4" /> Lihat GIF · Preview
          </button>
        )}
      </div>
      {gif && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={s.gif} alt={`Looping GIF of ${title}`} className="max-h-60 rounded-md" />
      )}
    </div>
  );
}
