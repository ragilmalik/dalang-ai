// Types and helpers shared by the Dalang AI pages. All calls go to /api on the same origin
// (next.config.mjs proxies /api and /media to the Python backend).

export type StageStatus = "pending" | "running" | "done" | "failed" | "skipped";

export interface Stage {
  key: string;
  label: string;
  status: StageStatus;
  detail: string;
  thumbs: string[];
  seconds?: number;
}

export interface Rejection {
  rejected: string;
  issue: string;
}

export interface SceneCard {
  n: number;
  narration: string;
  setting: string;
  still: string;
  backdrop: string;
  attempts: number;
  rejections: Rejection[];
  placeholder?: boolean; // r5: Muse Image failed after retries, labelled placeholder backdrop
}

export interface CastMember {
  id: string;
  name: string;
  sheet: string;
  cutout: string;
  rejections: Rejection[];
  returning?: boolean;
}

export type JobStatus = "queued" | "running" | "review" | "choice" | "rendering" | "done" | "failed" | "blocked";

export interface GaraGara {
  enabled: boolean;
  status: "off" | "pending" | "waiting" | "answered";
  after?: number;
  speaker?: string;
  speaker_name?: string;
  speaker_cutout?: string | null;
  question?: string;
  options?: string[];
  question_audio?: string | null;
  answer?: string | null;
}

export interface Job {
  id: string;
  status: JobStatus;
  title: string;
  language: "id" | "jv" | "en";
  style: "classic" | "colorful";
  review: boolean;
  public: boolean;
  transcript: string;
  stages: Stage[];
  scenes: SceneCard[];
  cast: CastMember[];
  videos: { landscape?: string; vertical?: string };
  poster: string | null;
  duration_s?: number;
  cost_usd: number;
  error: string | null;
  message: string | null;
  demo_replay: boolean;
  sample?: boolean;
  models: string[];
  offline: boolean;
  script: {
    title: string;
    moral: string;
    language: string;
    opening?: string;
    characters?: { id: string; name: string; wayang_archetype: string; cultural_note?: string }[];
  } | null;
  captions?: string;
  applause?: number;
  gara_gara?: GaraGara;
  part1?: string | null;
  trace?: TraceEntry[];
  trace_summary?: TraceSummary;
  receipt?: Receipt;
  cultural_review?: CulturalReview;
  consistency?: Consistency;
  // remix, fallbacks, aksara title: optional, absent on older films
  remix_of?: string;
  remix?: { language: "id" | "jv" | "en"; pov: "original" | "villain"; villain: string | null };
  remixes?: string[];
  fallbacks?: { stage: string; label: string; what: string; placeholder: boolean }[];
  title_aksara?: string;
  created?: number;
}

/** Gara-gara audience vote (classroom mode). */
export interface VoteState {
  status: "open" | "closed" | "off";
  options: string[];
  question: string;
  tally: number[];
  total: number;
  winner: 0 | 1 | null;
  closes_at: number | null;
}

/** Sticker pack + GIF loop of a film. */
export interface Stickers {
  stickers: { id: string; name: string; url: string; w: number; h: number }[];
  zip: string;
  gif: string;
}

/** A stable random id per device, so one phone = one vote (re-voting changes it). */
export function deviceId(): string {
  const k = "dalang:device";
  let v = localStorage.getItem(k);
  if (!v) {
    v = `d_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
    localStorage.setItem(k, v);
  }
  return v;
}

/** "Meta models used" receipt: per model its job, calls, tokens, images and estimated cost. */
export interface Receipt {
  models: {
    model: string;
    role: string;
    calls: number;
    tokens_in: number;
    tokens_out: number;
    images: number;
    usd: number;
    open_weights: boolean;
  }[];
  calls: number;
  tokens_in: number;
  tokens_out: number;
  usd: number;
  decisions: number;
  estimate: boolean;
  pricing: string;
  fake: boolean;
  note: string;
}

/** Penjaga Budaya: the cultural-review agent's report on the lakon. */
export interface CulturalReview {
  model: string | null;
  rules: string[];
  rules_status: string;
  scenes: { n: number; passed_first: boolean; passed_after: boolean; rules: string[] }[];
  characters: { id: string; name: string; passed_first: boolean; rules: string[] }[];
  fixes: number;
  pass_rate_first: number;
  pass_rate_after: number;
  note: string;
}

/** Character consistency from the SAM 3.1 cut-outs, the checker agent and same-pixel reuse. */
export interface Consistency {
  score: number;
  appearances: number;
  method: string;
  puppets: {
    id: string;
    name: string;
    source: "sam" | "kotak" | "background";
    fill: number;
    soft_edges: number;
    checker_redraws: number;
    same_pixels: boolean;
    scenes: number[];
    score: number;
  }[];
}

/** One line of the agent trace: a Meta model call, or an agent decision (redraw, retry, cache hit, fallback). */
export type TraceEntry =
  | {
      kind: "call";
      model: string;
      endpoint: string;
      purpose: string;
      ms: number;
      attempts: number;
      ok: boolean;
      error?: string;
      stage?: string | null;
      t: number;
    }
  | { kind: "decision"; agent: string; text: string; stage?: string | null; t: number };

export interface TraceSummary {
  calls: number;
  decisions: number;
  models: { model: string; calls: number; failed: number; retries: number; ms: number; usd: number }[];
}

export interface Health {
  ok: boolean;
  /** live: real Meta Model API · fake: FAKE_META=1 (tests/offline, labelled placeholder art) · not_configured: no key */
  mode?: "live" | "fake" | "not_configured";
  live?: boolean;
  offline: boolean;
  open_weights: boolean;
  demo_mode: boolean;
  models: Record<string, string>;
  open_weights_models?: string[];
}

/** Bahasa names for the pipeline stages (the API sends the English label). */
export const STAGE_ID: Record<string, string> = {
  listen: "Mendengar",
  lakon: "Menulis lakon",
  casting: "Menatah wayang",
  scenes: "Melukis adegan",
  animate: "Menghidupkan wayang",
  narrate: "Membacakan cerita",
  cut: "Merangkai film",
};

/** Open-weight models get an "(open weights)" label wherever model names are shown. */
export function modelLabel(m: string): string {
  return /glimmer|spark-open/i.test(m) ? `${m} (open weights)` : m;
}

export const LANGS = [
  { code: "id", label: "Bahasa Indonesia" },
  { code: "jv", label: "Basa Jawa" },
  { code: "en", label: "English" },
] as const;

export const T = {
  id: { tell: "Ceritakan kisahmu", hint: "Tekan tombol, lalu ceritakan dongengmu (maks. 90 detik)" },
  jv: { tell: "Critakna kisahmu", hint: "Pencet tombol, banjur critakna dongengmu (maks. 90 detik)" },
  en: { tell: "Tell your story", hint: "Press the button and tell your story (up to 90 seconds)" },
} as const;

/** Server-side fetches (watch page, gallery) talk to the backend directly. */
export function apiOrigin(): string {
  return process.env.API_ORIGIN || "http://127.0.0.1:8000";
}

export async function postJSON<R>(url: string, body: unknown): Promise<R> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json() as Promise<R>;
}

/** A readable, bilingual message for every way sending a story can fail. */
/**
 * POST a form with upload progress (fetch has none). A recording on a slow phone connection can take a minute
 * to send; the button shows how far it got. status 0 = no connection.
 */
export function sendForm(
  url: string,
  body: FormData,
  onProgress?: (pct: number) => void,
): Promise<{ status: number; data: { detail?: string } & Record<string, unknown> }> {
  return new Promise((resolve) => {
    const x = new XMLHttpRequest();
    x.open("POST", url);
    x.responseType = "text";
    if (onProgress)
      x.upload.onprogress = (e) => {
        if (e.lengthComputable && e.total > 0) onProgress(Math.min(100, Math.round((e.loaded / e.total) * 100)));
      };
    x.onload = () => {
      let data = {};
      try {
        data = JSON.parse(x.responseText || "{}");
      } catch {
        /* not JSON (a proxy error page): the status says enough */
      }
      resolve({ status: x.status, data });
    };
    x.onerror = () => resolve({ status: 0, data: {} });
    x.ontimeout = () => resolve({ status: 0, data: {} });
    x.send(body);
  });
}

export function sendError(status: number, detail?: string): string {
  if (detail && status !== 500) return detail;
  if (status === 413) return "Rekamannya terlalu besar (maks. 25 MB) · The recording is too large (max 25 MB).";
  if (status === 429) return "Sang dalang sedang sibuk. Coba lagi sebentar lagi · The dalang is busy, try again in a minute.";
  if (status === 0 && typeof navigator !== "undefined" && !navigator.onLine)
    return "Sedang offline. Ceritanya masih di sini, kirim lagi setelah tersambung · You are offline. Your story is still here, send it again once you are connected.";
  if (status === 0) return "Tidak tersambung ke server · Can't reach the Dalang AI server. Check the connection.";
  if (status === 415) return "File itu bukan rekaman suara · That file is not a sound recording. Try mp3, m4a, wav or webm.";
  if (status === 503)
    return "Server ini belum bisa membuat film baru. Contoh film tetap bisa ditonton · This server can't make new films right now. The sample films still play.";
  return "Ada masalah di server · Something went wrong on the server. Please try again.";
}
