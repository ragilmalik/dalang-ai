// Kelir Live: the browser shadow stage. Pure drawing + interaction maths, no React.
// The puppets are the film's own SAM 3.1 cut-outs. Each one is pre-rendered once as a black silhouette at a few
// blur levels, so a frame is only a handful of drawImage calls (60 fps on a phone).

export interface PuppetSrc {
  id: string;
  name: string;
  cutout: string;
}

export interface PuppetState {
  id: string;
  name: string;
  x: number; // centre, 0..1 of the stage width
  y: number; // centre, 0..1 of the stage height
  rot: number; // radians
  base: number; // resting distance: 1 = pressed against the kelir (sharp), 0 = right by the lamp (big, soft)
  depth: number; // shown distance, eases toward target()
  lifted: boolean; // held by a finger: pulled a little off the screen
  flip: boolean;
}

export type Art = HTMLImageElement | HTMLCanvasElement;

export interface PuppetArt {
  img: Art;
  levels: HTMLCanvasElement[]; // silhouettes, sharp -> soft
  pad: number; // transparent margin around each level, in level pixels
  mask: { w: number; h: number; a: Uint8Array };
  aspect: number; // width / height
}

export const BLUR_LEVELS = [0, 3, 7, 12, 18]; // px at SIL_H
const SIL_H = 520;

export function loadImage(src: string): Promise<HTMLImageElement | null> {
  return new Promise((res) => {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => res(img);
    img.onerror = () => res(null);
    img.src = src;
  });
}

function canvasFilterWorks(): boolean {
  const c = document.createElement("canvas");
  const ctx = c.getContext("2d");
  return !!ctx && "filter" in ctx && (() => { ctx.filter = "blur(2px)"; return ctx.filter === "blur(2px)"; })();
}

/** Silhouettes at every blur level + a small alpha mask for hit tests. */
export function prepareArt(img: Art): PuppetArt {
  const iw = img instanceof HTMLImageElement ? img.naturalWidth : img.width;
  const ih = img instanceof HTMLImageElement ? img.naturalHeight : img.height;
  const aspect = iw / Math.max(1, ih);
  const h = SIL_H;
  const w = Math.max(8, Math.round(h * aspect));
  const pad = BLUR_LEVELS[BLUR_LEVELS.length - 1] * 2 + 4;
  const sharp = document.createElement("canvas");
  sharp.width = w + pad * 2;
  sharp.height = h + pad * 2;
  const s = sharp.getContext("2d")!;
  s.drawImage(img, pad, pad, w, h);
  s.globalCompositeOperation = "source-in";
  s.fillStyle = "#120a05";
  s.fillRect(0, 0, sharp.width, sharp.height);
  const filter = canvasFilterWorks();
  const levels = BLUR_LEVELS.map((b, i) => {
    if (b === 0) return sharp;
    const c = document.createElement("canvas");
    c.width = sharp.width;
    c.height = sharp.height;
    const ctx = c.getContext("2d")!;
    if (filter) {
      ctx.filter = `blur(${b}px)`;
      ctx.drawImage(sharp, 0, 0);
    } else {
      // Safari without canvas filters: blur by shrinking and stretching back (bilinear)
      const k = 1 / 2 ** i;
      const t = document.createElement("canvas");
      t.width = Math.max(1, Math.round(sharp.width * k));
      t.height = Math.max(1, Math.round(sharp.height * k));
      const tc = t.getContext("2d")!;
      tc.imageSmoothingQuality = "high";
      tc.drawImage(sharp, 0, 0, t.width, t.height);
      ctx.imageSmoothingQuality = "high";
      ctx.drawImage(t, 0, 0, c.width, c.height);
    }
    return c;
  });
  // hit-test mask: 96 px tall alpha map of the cut-out
  const mh = 96;
  const mw = Math.max(4, Math.round(mh * aspect));
  const m = document.createElement("canvas");
  m.width = mw;
  m.height = mh;
  const mc = m.getContext("2d", { willReadFrequently: true })!;
  mc.drawImage(img, 0, 0, mw, mh);
  const data = mc.getImageData(0, 0, mw, mh).data;
  const a = new Uint8Array(mw * mh);
  for (let i = 0; i < a.length; i++) a[i] = data[i * 4 + 3];
  return { img, levels, pad, mask: { w: mw, h: mh, a }, aspect };
}

/** Size of a puppet on a stage of w x h CSS px: fits a box 40% of the width and 52% of the height. */
export function puppetSize(aspect: number, w: number, h: number, scale = 1): { pw: number; ph: number } {
  let ph = h * 0.52 * scale;
  let pw = ph * aspect;
  if (pw > w * 0.4 * scale) {
    pw = w * 0.4 * scale;
    ph = pw / aspect;
  }
  return { pw, ph };
}

export function target(p: PuppetState): number {
  return p.lifted ? Math.max(0, p.base - 0.3) : p.base;
}

/** Is stage point (sx, sy) on the puppet's leather (alpha), with a few pixels of finger tolerance? */
export function hitPuppet(p: PuppetState, art: PuppetArt, sx: number, sy: number, w: number, h: number, scale = 1): boolean {
  const { pw, ph } = puppetSize(art.aspect, w, h, scale);
  const dx = sx - p.x * w;
  const dy = sy - p.y * h;
  const c = Math.cos(-p.rot);
  const s = Math.sin(-p.rot);
  let lx = dx * c - dy * s;
  const ly = dx * s + dy * c;
  if (p.flip) lx = -lx;
  const u = (lx / pw + 0.5) * art.mask.w;
  const v = (ly / ph + 0.5) * art.mask.h;
  const r = 4; // mask px of tolerance: thin sticks and horns are still grabbable
  for (let yy = Math.floor(v - r); yy <= v + r; yy++) {
    for (let xx = Math.floor(u - r); xx <= u + r; xx++) {
      if (xx < 0 || yy < 0 || xx >= art.mask.w || yy >= art.mask.h) continue;
      if (art.mask.a[yy * art.mask.w + xx] > 40) return true;
    }
  }
  return false;
}

export interface Lamp {
  x: number; // 0..1
  y: number; // 0..1 (negative = above the stage)
  glow: number; // 0.85..1, flickers
}

/** The blencong-lit screen: warm centre, burnt edges, the scene backdrop as a faint print on the cloth. */
export function drawKelir(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  lamp: Lamp,
  backdrop: HTMLImageElement | null,
  backdropAlpha: number,
) {
  const lx = lamp.x * w;
  const ly = lamp.y * h;
  ctx.fillStyle = "#1b0f07";
  ctx.fillRect(0, 0, w, h);
  const g = ctx.createRadialGradient(lx, ly + h * 0.25, 0, lx, ly + h * 0.35, Math.max(w, h) * 0.95);
  const k = lamp.glow;
  g.addColorStop(0, `rgba(255, ${Math.round(226 * k)}, ${Math.round(160 * k)}, 1)`);
  g.addColorStop(0.45, `rgba(${Math.round(236 * k)}, ${Math.round(176 * k)}, 96, 1)`);
  g.addColorStop(1, "rgba(70, 32, 10, 1)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
  if (backdrop && backdropAlpha > 0) {
    // cover-fit, multiplied in like dye on the cloth
    const r = Math.max(w / backdrop.naturalWidth, h / backdrop.naturalHeight);
    const bw = backdrop.naturalWidth * r;
    const bh = backdrop.naturalHeight * r;
    ctx.save();
    ctx.globalAlpha = backdropAlpha;
    ctx.globalCompositeOperation = "multiply";
    ctx.drawImage(backdrop, (w - bw) / 2, (h - bh) / 2, bw, bh);
    ctx.restore();
  }
}

export function drawVignette(ctx: CanvasRenderingContext2D, w: number, h: number) {
  const v = ctx.createRadialGradient(w / 2, h * 0.45, Math.min(w, h) * 0.35, w / 2, h * 0.5, Math.max(w, h) * 0.78);
  v.addColorStop(0, "rgba(0,0,0,0)");
  v.addColorStop(1, "rgba(15,6,2,0.72)");
  ctx.fillStyle = v;
  ctx.fillRect(0, 0, w, h);
}

/**
 * One puppet's shadow. Near the kelir (depth 1) it is small, sharp and dark; pulled toward the lamp it grows,
 * softens, fades and slides away from the light, like real leather between a flame and a cloth.
 */
export function drawShadow(
  ctx: CanvasRenderingContext2D,
  art: PuppetArt,
  p: PuppetState,
  w: number,
  h: number,
  lamp: Lamp,
  opts: { color: boolean; scale?: number; jitter?: number },
) {
  const far = 1 - Math.min(1, Math.max(0, p.depth));
  const grow = 1 + far * 0.45;
  const { pw, ph } = puppetSize(art.aspect, w, h, opts.scale ?? 1);
  const cx = p.x * w + (p.x - lamp.x) * w * far * 0.18 + (opts.jitter ?? 0);
  const cy = p.y * h + (p.y - lamp.y) * h * far * 0.08;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(p.rot);
  if (p.flip) ctx.scale(-1, 1);
  if (opts.color) {
    // dalang's side: the painted leather itself, with a soft shadow behind it
    ctx.globalAlpha = 0.35;
    const lv = art.levels[2];
    const k = pw / (lv.width - art.pad * 2);
    ctx.drawImage(lv, -lv.width * k / 2 + 6, -lv.height * k / 2 + 8, lv.width * k, lv.height * k);
    ctx.globalAlpha = 1;
    ctx.drawImage(art.img, -pw / 2, -ph / 2, pw, ph);
    ctx.restore();
    return;
  }
  // pick the two blur levels around this distance and cross-fade them
  const f = far * (art.levels.length - 1);
  const i0 = Math.floor(f);
  const i1 = Math.min(art.levels.length - 1, i0 + 1);
  const t = f - i0;
  const alpha = 0.95 - far * 0.45;
  const sw = pw * grow;
  const draw = (lv: HTMLCanvasElement, a: number) => {
    if (a <= 0.01) return;
    const k = sw / (lv.width - art.pad * 2);
    ctx.globalAlpha = a;
    ctx.drawImage(lv, (-lv.width * k) / 2, (-lv.height * k) / 2, lv.width * k, lv.height * k);
  };
  draw(art.levels[i0], alpha * (1 - t));
  if (i1 !== i0) draw(art.levels[i1], alpha * t);
  ctx.restore();
}

/** A drawn gunungan (kayon) for films whose own gunungan cut-out is missing. */
export function gununganFallback(): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = 200;
  c.height = 520;
  const g = c.getContext("2d")!;
  g.fillStyle = "#7a2418";
  g.beginPath();
  g.moveTo(100, 6);
  g.bezierCurveTo(170, 80, 196, 220, 190, 360);
  g.lineTo(10, 360);
  g.bezierCurveTo(4, 220, 30, 80, 100, 6);
  g.fill();
  g.strokeStyle = "#e3b14f";
  g.lineWidth = 5;
  for (let y = 60; y < 350; y += 26) {
    g.beginPath();
    g.moveTo(40, y + 14);
    g.lineTo(100, y);
    g.lineTo(160, y + 14);
    g.stroke();
  }
  g.fillStyle = "#5a3a20";
  g.fillRect(96, 360, 8, 160);
  return c;
}

/** Ease for the gunungan sweep between scenes. */
export function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
}

/** A keprak / cempala knock (the dalang's wooden mallet on the puppet box), synthesised. */
export function knock(ac: AudioContext, out: AudioNode, loud = 0.6) {
  const t = ac.currentTime;
  const len = Math.floor(ac.sampleRate * 0.08);
  const buf = ac.createBuffer(1, len, ac.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len) ** 6;
  const src = ac.createBufferSource();
  src.buffer = buf;
  const bp = ac.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.value = 1800;
  bp.Q.value = 3;
  const g = ac.createGain();
  g.gain.setValueAtTime(loud, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
  src.connect(bp).connect(g).connect(out);
  src.start(t);
}

/** The gong at a scene change. */
export function gong(ac: AudioContext, out: AudioNode) {
  const t = ac.currentTime;
  [[98, 0.5], [196.5, 0.18], [293, 0.08]].forEach(([f, a]) => {
    const o = ac.createOscillator();
    o.frequency.value = f;
    const g = ac.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(a, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 3.2);
    o.connect(g).connect(out);
    o.start(t);
    o.stop(t + 3.3);
  });
}

export function pickRecorderType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  const types = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"];
  return types.find((t) => MediaRecorder.isTypeSupported(t));
}
