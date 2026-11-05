"use client";

import { useEffect, useRef } from "react";
import Badge from "@/components/ui/Badge";

/**
 * The sample film, muted, on loop, in a wooden kelir frame: the first thing a visitor sees. The poster is the LCP
 * image (tiny WebP, fixed aspect so nothing shifts). The "lights up" dimmer is an overlay that fades, so the poster
 * itself paints at once. With prefers-reduced-motion, Data Saver or a slow connection the loop never starts and the
 * poster stays.
 */
export default function HeroFilm() {
  const v = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const el = v.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    // Data Saver or a 2G/3G connection: the poster stays and the clip is never downloaded
    const net = (navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } }).connection;
    if (net?.saveData || /(^|-)(2g|3g)$/.test(net?.effectiveType || "")) return;
    el.muted = true;
    // start the loop after the page has painted, so the clip never competes with the first paint (LCP)
    const start = () => el.play().catch(() => {});
    const ric = (window as Window & { requestIdleCallback?: (f: () => void, o?: { timeout: number }) => number })
      .requestIdleCallback;
    const go = () => (ric ? ric(start, { timeout: 1200 }) : setTimeout(start, 300));
    if (document.readyState === "complete") go();
    else window.addEventListener("load", go, { once: true });
    return () => window.removeEventListener("load", go);
  }, []);
  return (
    <figure className="frame">
      <div className="lights-up relative aspect-[640/288] w-full overflow-hidden bg-[#1a0f07]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/hero/sample-poster.webp"
          alt=""
          width={640}
          height={288}
          fetchPriority="high"
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <video
          ref={v}
          muted
          loop
          playsInline
          preload="none"
          poster="/hero/sample-poster.webp"
          width={640}
          height={288}
          className="absolute inset-0 h-full w-full object-cover"
          aria-label="Contoh cerita: Kancil yang Cerdik dan Buaya Sungai · Sample story film clip, made with the live Meta models (no sound)"
        >
          <source src="/hero/sample-loop.webm" type="video/webm" />
          <source src="/hero/sample-loop.mp4" type="video/mp4" />
        </video>
      </div>
      <figcaption className="absolute left-4 top-4 z-10 flex flex-wrap items-start gap-1.5">
        <Badge tone="sample">Contoh cerita · Sample story, live Meta models</Badge>
      </figcaption>
    </figure>
  );
}
