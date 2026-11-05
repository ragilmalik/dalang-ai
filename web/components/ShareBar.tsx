"use client";

import { useState, useSyncExternalStore } from "react";
import { filmFileName, shareText, SHARE_HASHTAGS, xIntent } from "@/lib/share";
import ViralExtras from "@/components/ViralExtras";
import Icon from "@/components/ui/Icon";

const noop = () => () => {};

interface Props {
  id: string;
  title: string;
  vertical?: string | null;
  landscape?: string | null;
}

/**
 * Share a public film. Phones get the system share sheet (Web Share API: WhatsApp, Instagram, X…);
 * everywhere else the link is copied, with a manual fallback when the clipboard is blocked.
 */
export default function ShareBar({ id, title, vertical, landscape }: Props) {
  // browser-only values: empty on the server render, filled in on the phone without an extra effect
  const origin = useSyncExternalStore(noop, () => window.location.origin, () => "");
  const canShare = useSyncExternalStore(noop, () => typeof navigator.share === "function", () => false);
  const [note, setNote] = useState("");
  const url = `${origin}/watch/${id}`;
  const text = shareText(title);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${text} ${SHARE_HASHTAGS.map((h) => `#${h}`).join(" ")} ${url}`);
      setNote("✓ Tautan tersalin · Link copied");
    } catch {
      setNote(`Salin manual · Copy this: ${url}`);
    }
  };
  const share = async () => {
    try {
      await navigator.share({ title: `${title} · Dalang AI`, text, url });
    } catch (e) {
      if ((e as Error)?.name !== "AbortError") await copy(); // closing the sheet is not an error
    }
  };
  return (
    <div className="space-y-3" aria-label="Bagikan film · Share this film">
      <div className="grid gap-2 sm:flex sm:flex-wrap">
        {canShare && (
          <button type="button" className="btn-gold" onClick={share}>
            <Icon name="share" /> Bagikan · Share
          </button>
        )}
        <button type="button" className="btn justify-start sm:justify-center" onClick={copy}>
          <Icon name="link" /> Salin tautan · Copy link
        </button>
        <a className="btn justify-start sm:justify-center" target="_blank" rel="noopener noreferrer" href={xIntent(title, url)}>
          <span aria-hidden="true" className="w-5 text-center font-bold">𝕏</span> Post
        </a>
        {vertical && (
          <a className="btn justify-start sm:justify-center" href={vertical} download={filmFileName(title, "vertical")}>
            <Icon name="phone" /> Unduh 9:16 · Reels/TikTok/Shorts
          </a>
        )}
        {landscape && (
          <a className="btn justify-start sm:justify-center" href={landscape} download={filmFileName(title, "landscape")}>
            <Icon name="download" /> Unduh 16:9 · Download 16:9
          </a>
        )}
      </div>
      <p className="min-h-5 text-sm text-ok empty:min-h-0" role="status" aria-live="polite">
        {note}
      </p>
      <ViralExtras id={id} title={title} />
    </div>
  );
}
