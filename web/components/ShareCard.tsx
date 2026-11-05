"use client";

import { useState } from "react";
import { filmFileName } from "@/lib/share";
import Icon from "@/components/ui/Icon";

interface Props {
  id: string;
  title: string;
  poster: string | null;
  applause?: number;
  sample?: boolean;
  offline?: boolean;
}

function load(src: string): Promise<HTMLImageElement | null> {
  return new Promise((res) => {
    const i = new Image();
    i.onload = () => res(i);
    i.onerror = () => res(null);
    i.src = src;
  });
}

function wrap(ctx: CanvasRenderingContext2D, text: string, maxW: number): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let line = "";
  for (const w of words) {
    const t = line ? `${line} ${w}` : w;
    if (ctx.measureText(t).width > maxW && line) {
      lines.push(line);
      line = w;
    } else line = t;
  }
  if (line) lines.push(line);
  return lines.slice(0, 3);
}

/** Draws a 1080x1350 share card (Instagram/WhatsApp status size) in the browser, then shares or downloads it. */
export async function drawCard(p: Props, origin: string): Promise<Blob | null> {
  const c = document.createElement("canvas");
  c.width = 1080;
  c.height = 1350;
  const g = c.getContext("2d")!;
  const bg = g.createRadialGradient(540, 0, 50, 540, 300, 1300);
  bg.addColorStop(0, "#6a3812");
  bg.addColorStop(0.5, "#1b0f07");
  bg.addColorStop(1, "#0b0603");
  g.fillStyle = bg;
  g.fillRect(0, 0, 1080, 1350);
  // lamp
  const lamp = g.createRadialGradient(540, 90, 4, 540, 90, 140);
  lamp.addColorStop(0, "rgba(255,214,130,1)");
  lamp.addColorStop(1, "rgba(255,190,90,0)");
  g.fillStyle = lamp;
  g.fillRect(380, 0, 320, 260);
  const img = p.poster ? await load(p.poster) : null;
  const top = 200;
  g.save();
  g.beginPath();
  g.roundRect(60, top, 960, 504, 28);
  g.clip();
  if (img) {
    const r = Math.max(960 / img.naturalWidth, 504 / img.naturalHeight);
    g.drawImage(img, 540 - (img.naturalWidth * r) / 2, top + 252 - (img.naturalHeight * r) / 2, img.naturalWidth * r, img.naturalHeight * r);
  } else {
    g.fillStyle = "#2a180b";
    g.fillRect(60, top, 960, 504);
  }
  g.restore();
  g.strokeStyle = "rgba(227,177,79,.7)";
  g.lineWidth = 3;
  g.beginPath();
  g.roundRect(60, top, 960, 504, 28);
  g.stroke();
  g.textAlign = "center";
  g.fillStyle = "#e3b14f";
  g.font = "600 34px Georgia, serif";
  g.fillText("Dalang AI · wayang kulit", 540, 160);
  g.font = "bold 74px Georgia, serif";
  g.fillStyle = "#fbefd5";
  wrap(g, p.title, 940).forEach((l, i) => g.fillText(l, 540, 820 + i * 86));
  g.font = "34px sans-serif";
  g.fillStyle = "rgba(251,239,213,.85)";
  g.fillText("Ceritaku jadi wayang · My story became a shadow-puppet film", 540, 1080);
  if (p.applause) {
    g.fillText(`🙏 Sembah ${p.applause}`, 540, 1135);
  }
  // badge
  g.fillStyle = "rgba(0,0,0,.6)";
  g.beginPath();
  g.roundRect(330, 1170, 420, 64, 32);
  g.fill();
  g.strokeStyle = "#e3b14f";
  g.stroke();
  g.fillStyle = "#fbefd5";
  g.font = "bold 30px sans-serif";
  g.fillText("✦ Made with Meta Muse", 540, 1213);
  g.font = "26px monospace";
  g.fillStyle = "rgba(251,239,213,.7)";
  g.fillText(`${origin.replace(/^https?:\/\//, "")}/watch/${p.id}`, 540, 1290);
  if (p.sample || p.offline) {
    g.font = "bold 24px sans-serif";
    g.fillStyle = "#e3b14f";
    g.textAlign = "left";
    g.fillText(p.offline ? (p.sample ? "CONTOH · SAMPLE · PLACEHOLDER ART" : "PLACEHOLDER ART") : "CONTOH · SAMPLE", 84, top + 44);
  }
  return new Promise((res) => c.toBlob((b) => res(b), "image/png"));
}

/** Button: make the film's share card, share it as an image where the phone allows, else download it. */
export default function ShareCard(p: Props) {
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState<string | null>(null);
  const name = `${filmFileName(p.title, "landscape").replace(/-16x9\.mp4$/, "")}-card.png`;
  async function make() {
    setBusy(true);
    const blob = await drawCard(p, window.location.origin);
    setBusy(false);
    if (!blob) return;
    const file = new File([blob], name, { type: "image/png" });
    const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean };
    if (nav.canShare?.({ files: [file] })) {
      try {
        await navigator.share({ files: [file], title: p.title, text: `${p.title} · Dalang AI` });
        return;
      } catch {
        /* closed the sheet: fall through to the download link */
      }
    }
    setUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return URL.createObjectURL(blob);
    });
  }
  return (
    <span className="inline-flex flex-wrap items-center justify-center gap-2">
      <button type="button" className="btn" onClick={make} disabled={busy} aria-busy={busy || undefined} data-testid="share-card">
        {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="image" />} {busy ? "Membuat… · Making…" : "Kartu · Share card"}
      </button>
      {url && (
        <a className="btn-gold !py-2" href={url} download={name}>
          <Icon name="download" /> Unduh kartu · Download card
        </a>
      )}
    </span>
  );
}
