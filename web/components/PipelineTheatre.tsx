"use client";

import { STAGE_ID, type Job, type TraceEntry } from "@/lib/api";
import Bi from "@/components/ui/Bi";
import Icon, { type IconName } from "@/components/ui/Icon";
import Progress from "@/components/ui/Progress";

/** The Meta models as the troupe of a wayang performance. Each one lights up when its real trace events arrive. */
export interface Player {
  key: string;
  model: string;
  name: string;
  role: string;
  prop: IconName;
  hue: string;
  stages: string[];
  match: (t: TraceEntry) => boolean;
}

const isCall = (t: TraceEntry, re: RegExp) => t.kind === "call" && re.test(t.model);
const isAgent = (t: TraceEntry, re: RegExp) => t.kind === "decision" && re.test(t.agent);

export const TROUPE: Player[] = [
  {
    key: "listener",
    model: "Muse Voice",
    name: "Si Pendengar",
    role: "the listener · hears the child's story",
    prop: "ear",
    hue: "#7fb4d8",
    stages: ["listen"],
    match: (t) => isCall(t, /voice|transcribe|whisper/i),
  },
  {
    key: "dalang",
    model: "Muse Spark",
    name: "Ki Dalang",
    role: "the dalang · writes the lakon, checks every picture",
    prop: "scroll",
    hue: "#e3b14f",
    stages: ["lakon", "narrate", "cut"],
    match: (t) => isCall(t, /spark/i),
  },
  {
    key: "guardian",
    model: "Spark agent",
    name: "Penjaga Budaya",
    role: "the culture guardian · keeps it kind and true to wayang",
    prop: "shield",
    hue: "#c58bd8",
    stages: ["lakon"],
    match: (t) => isAgent(t, /penjaga|budaya|cultur/i) || (t.kind === "call" && /cultur|penjaga/i.test(t.purpose)),
  },
  {
    key: "painter",
    model: "Muse Image",
    name: "Sang Pelukis",
    role: "the painter · draws puppets and scenes",
    prop: "brush",
    hue: "#e07a5f",
    stages: ["casting", "scenes"],
    match: (t) => isCall(t, /image|glimmer/i) || isAgent(t, /verify/i),
  },
  {
    key: "carver",
    model: "SAM 3.1",
    name: "Sang Penatah",
    role: "the leather carver · cuts each puppet out",
    prop: "scissors",
    hue: "#9fd39a",
    stages: ["casting"],
    match: (t) => isCall(t, /sam/i) || isAgent(t, /consisten/i),
  },
  {
    key: "puppeteer",
    model: "Muse Wonder",
    name: "Sang Penggerak",
    role: "the puppeteer · makes them move",
    prop: "stage",
    hue: "#f2c14e",
    stages: ["animate"],
    match: (t) => isCall(t, /wonder/i),
  },
];

/**
 * A small wayang figure as its shadow on the kelir: crown, long-nosed profile, kain, the central rod and the arm
 * stick. The rods stay brown, as they do on a real screen.
 */
export function WayangFigure({ hue, active, prop }: { hue: string; active: boolean; prop: IconName }) {
  return (
    <span className={`relative inline-block ${active ? "theatre-bob" : ""}`} aria-hidden="true">
      <svg viewBox="0 0 60 110" className="h-24 w-[3.25rem]">
        <g fill="rgb(var(--c-on-kelir))">
          <path d="M29 3l4 6 4-3-1 7 4 3-4 3 1 5-5 2 6 3-3 2-6-1-1 5h-5l1-6-5-3 3-4-3-5 4-3-2-6 5 1z" />
          <path d="M21 34h17l5 33-6 7H22l-6-7z" />
          <path d="M23 74l-4 18h6l4-14 3 14h6l-4-18z" />
          <path d="M38 38q11 7 14 22" fill="none" stroke="rgb(var(--c-on-kelir))" strokeWidth="3" />
        </g>
        <line x1="30" y1="72" x2="30" y2="108" stroke="#8a5a2e" strokeWidth="2" />
        <line x1="52" y1="60" x2="57" y2="106" stroke="#8a5a2e" strokeWidth="1.5" />
      </svg>
      <span
        className="absolute -right-3 top-6 grid h-7 w-7 place-items-center rounded-full text-on-kelir shadow-1"
        style={{ background: hue }}
      >
        <Icon name={prop} className="h-4 w-4" strokeWidth={2} />
      </span>
    </span>
  );
}

function short(t: TraceEntry): string {
  const s = t.kind === "call" ? t.purpose : t.text;
  return s.length > 90 ? `${s.slice(0, 88)}…` : s;
}

/**
 * The live "pipeline theatre": while the film is being made, each Meta model appears as a member of the wayang
 * troupe, standing as a shadow on its own small kelir. The one at work is lit and sways; its latest real trace line
 * (streamed over SSE with the job) is its speech bubble.
 */
export default function PipelineTheatre({ job }: { job: Job }) {
  const trace = job.trace ?? [];
  const latest = trace[trace.length - 1];
  const running = job.stages.find((s) => s.status === "running");
  const working = ["queued", "running", "rendering"].includes(job.status);
  const done = job.stages.filter((s) => s.status === "done" || s.status === "skipped").length;
  // Live trace lines when the API streams them; otherwise the running stage says who is on (and its detail
  // line is the speech bubble), so the theatre works with either.
  const byTrace =
    latest !== undefined && !!running && latest.stage === running.key && TROUPE.some((p) => p.match(latest));
  const rows = TROUPE.map((p) => {
    const mine = trace.filter(p.match);
    const last = mine[mine.length - 1];
    const own = job.stages.filter((s) => p.stages.includes(s.key));
    const stageDone = own.length > 0 && own.every((s) => s.status === "done" || s.status === "skipped");
    const lastStage = [...own].reverse().find((s) => s.status !== "pending" && s.detail);
    const active =
      working &&
      (byTrace && latest
        ? p.match(latest)
        : !!running && p.stages.includes(running.key));
    const bubble = last ? short(last) : lastStage ? lastStage.detail : "";
    return { p, calls: mine.filter((t) => t.kind === "call").length, notes: mine.length, bubble, active, done: stageDone };
  });
  const recent = trace.slice(-4).reverse();
  return (
    <section className="card space-y-5 overflow-hidden" aria-labelledby="theatre-h" data-testid="pipeline-theatre">
      <div className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
          <h2 id="theatre-h" className="t-h2">
            <Bi stack id="Di balik kelir" en="Behind the screen" />
          </h2>
          <p className="tabular t-small text-muted">
            {done}/{job.stages.length} <Bi id="tahap selesai" en="stages done" />
          </p>
        </div>
        <Progress value={done} max={job.stages.length} label="Progress · Kemajuan" />
        <p className="t-small text-muted" aria-live="polite">
          {running ? (
            <Bi id={`${STAGE_ID[running.key] ?? running.label}…`} en={`${running.label}…`} />
          ) : job.status === "queued" ? (
            <Bi id="Antre sebentar" en="Waiting in line…" />
          ) : working ? (
            <Bi id="Bersiap" en="Getting ready…" />
          ) : (
            <Bi id="Selesai" en="Done" />
          )}
        </p>
      </div>
      <ul className="grid grid-cols-1 gap-3 min-[480px]:grid-cols-2 sm:grid-cols-3">
        {rows.map(({ p, calls, notes, bubble, active, done: finished }) => (
          <li
            key={p.key}
            className={`relative flex flex-row overflow-hidden rounded-lg border min-[480px]:flex-col transition-[border-color,box-shadow] duration-gong ${
              active ? "border-prada shadow-lamp" : "border-gold/15"
            }`}
            data-active={active ? "1" : "0"}
            data-player={p.key}
          >
            <div
              className={`kelir relative grid w-28 shrink-0 place-items-end justify-center pb-1 min-[480px]:h-32 min-[480px]:w-auto transition-[filter] duration-gong ${
                active ? "" : finished ? "brightness-[.85] saturate-[.8]" : "brightness-[.45] saturate-[.6]"
              }`}
              style={{ boxShadow: "none" }}
            >
              <WayangFigure hue={p.hue} active={active} prop={p.prop} />
              {finished && !active && (
                <span className="absolute left-2 top-2 grid h-6 w-6 place-items-center rounded-full bg-on-kelir text-kelir">
                  <Icon name="check" className="h-3.5 w-3.5" strokeWidth={2.6} />
                </span>
              )}
            </div>
            <div className="flex flex-1 flex-col gap-0.5 bg-bg-2/80 p-3">
              <p className="font-serif text-lg font-semibold leading-tight text-gold">{p.name}</p>
              <p className="text-xs font-bold">{p.model}</p>
              <p className="text-xs leading-snug text-muted">{p.role}</p>
              <p className="tabular mt-1 text-xs">
                {active ? (
                  <span className="font-semibold text-gold">● bekerja · working</span>
                ) : finished ? (
                  <span className="text-ok">✓ selesai · done</span>
                ) : (
                  <span className="text-muted">○ menunggu · waiting</span>
                )}
                <span className="text-muted">
                  {calls > 0 && ` · ${calls} call${calls === 1 ? "" : "s"}`}
                  {notes > calls && ` · ${notes - calls} decision${notes - calls === 1 ? "" : "s"}`}
                </span>
              </p>
              {bubble && (
                <p className={`mt-2 rounded-md bg-fg/[0.06] px-2 py-1.5 text-xs leading-snug ${active ? "text-fg" : "text-muted"}`}>
                  {bubble.length > 110 ? `${bubble.slice(0, 108)}…` : bubble}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
      {recent.length > 0 && (
        <div className="rounded-md border border-gold/10 bg-fg/[0.04] p-3 font-mono text-[11px] leading-relaxed [overflow-wrap:anywhere] sm:text-xs" aria-label="Latest trace events">
          {recent.map((t, i) => (
            <p key={`${t.t}-${i}`} className={i ? "text-muted" : ""}>
              {t.kind === "call" ? `▸ ${t.model} · ${short(t)}${t.ms ? ` · ${Math.round(t.ms)} ms` : ""}` : `◆ ${t.agent}: ${short(t)}`}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
