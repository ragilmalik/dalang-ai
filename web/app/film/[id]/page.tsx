"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import AgentTrace from "@/components/AgentTrace";
import ModelsReceipt from "@/components/ModelsReceipt";
import PipelineTheatre from "@/components/PipelineTheatre";
import ReadAlong from "@/components/ReadAlong";
import FeedbackSmiles from "@/components/FeedbackSmiles";
import GaraGaraChoice from "@/components/GaraGaraChoice";
import ClassroomVote from "@/components/ClassroomVote";
import RemixButtons from "@/components/RemixButtons";
import ViralExtras from "@/components/ViralExtras";
import KeepPuppet from "@/components/KeepPuppet";
import ShareBar from "@/components/ShareBar";
import ShareQR from "@/components/ShareQR";
import { filmFileName } from "@/lib/share";
import { STAGE_ID, modelLabel, postJSON, type Job, type SceneCard } from "@/lib/api";
import Bi from "@/components/ui/Bi";
import Badge from "@/components/ui/Badge";
import Button, { buttonClass } from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import Gunungan from "@/components/ui/Gunungan";
import { useToast } from "@/components/ui/Toast";
import { clearDraft, readDraft, readRecording } from "@/lib/draft";

const ICON: Record<string, string> = { pending: "○", running: "◐", done: "✓", skipped: "-", failed: "✕" };
const STAGE_TONE: Record<string, string> = {
  pending: "border-gold/20 text-muted",
  running: "border-prada bg-prada/15 text-gold",
  done: "border-ok/50 bg-ok/10 text-ok",
  skipped: "border-gold/20 text-muted",
  failed: "border-err/60 bg-err/10 text-err",
};

/** Keeps the job fresh: Server-Sent Events first, polling if the stream drops. */
function useJob(id: string) {
  const [job, setJob] = useState<Job | null>(null);
  const [problem, setProblem] = useState<"lost" | "missing" | null>(null);
  useEffect(() => {
    let es: EventSource | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;
    let gone = false; // 404: no such film, so stop asking (no request every 2 s on a mistyped link)
    const missing = () => {
      gone = true;
      es?.close();
      if (poll) clearInterval(poll);
      poll = null;
      setProblem("missing");
    };
    const startPolling = () => {
      if (poll || gone) return;
      poll = setInterval(async () => {
        const r = await fetch(`/api/jobs/${id}`).catch(() => null);
        if (!r) return setProblem("lost"); // keeps polling, so the page recovers by itself when the server is back
        if (r.status === 404) return missing();
        if (r.ok) {
          setProblem(null);
          const j = (await r.json()) as Job;
          setJob(j);
          // a finished film does not change any more: stop asking (saves data on a phone plan)
          if (["done", "failed", "blocked"].includes(j.status) && poll) {
            clearInterval(poll);
            poll = null;
          }
        }
      }, 2000);
    };
    fetch(`/api/jobs/${id}`)
      .then((r) => {
        if (r.status === 404) missing();
        else if (!r.ok) {
          setProblem("lost");
          startPolling();
        }
        return r.ok ? r.json() : null;
      })
      .then((j) => j && setJob(j))
      .catch(() => {
        setProblem("lost");
        startPolling();
      });
    try {
      es = new EventSource(`/api/jobs/${id}/events`);
      es.onmessage = (e) => {
        const j = JSON.parse(e.data) as Job;
        setJob(j);
        if (["done", "failed", "blocked"].includes(j.status)) es?.close();
      };
      es.onerror = () => {
        es?.close();
        startPolling();
      };
    } catch {
      startPolling();
    }
    return () => {
      es?.close();
      if (poll) clearInterval(poll);
    };
  }, [id]);
  return [job, setJob, problem] as const;
}

export default function FilmPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [job, setJob, problem] = useJob(id);
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const title = job?.title;
  useEffect(() => {
    if (title) document.title = `${title} · Dalang AI`;
  }, [title]);
  const finished = job?.status === "done";
  useEffect(() => {
    if (finished) clearDraft(); // the story became a film: the next visit to home starts empty
  }, [finished]);

  if (problem === "missing")
    return (
      <div className="card mx-auto mt-12 max-w-lg space-y-4 text-center" role="alert">
        <Gunungan className="mx-auto h-16 w-12 text-gold" />
        <p className="t-h3">Film ini tidak ditemukan · This film was not found.</p>
        <p className="text-muted">
          <Bi id="Mungkin tautannya salah ketik, atau filmnya sudah dihapus" en="The link may be mistyped, or the film was deleted" />
        </p>
        <Link href="/" className={buttonClass("primary")}>
          Cerita baru · Tell a new story
        </Link>
      </div>
    );
  const lostBanner = problem === "lost" && (
    <p role="status" className="flex items-center justify-center gap-2 rounded-lg border border-err/40 bg-err/10 p-3 text-center text-sm text-fg">
      <span className="spinner text-err" aria-hidden="true" />
      Koneksi ke server terputus, mencoba lagi… · Lost the connection to the server, retrying…
    </p>
  );
  if (!job)
    return (
      lostBanner || (
        <div className="grid min-h-[50vh] place-items-center" role="status">
          <div className="space-y-3 text-center">
            <Gunungan className="kayon-sway mx-auto h-16 w-12 text-gold" />
            <p className="text-muted">Memuat · Loading…</p>
          </div>
        </div>
      )
    );
  const working = ["queued", "running", "rendering"].includes(job.status);

  async function act(fn: () => Promise<Job>) {
    setBusy(true);
    try {
      setJob(await fn());
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 pt-6 sm:pt-10">
      {lostBanner}
      <header className="space-y-3 text-center">
        {working && <Gunungan className="kayon-sway mx-auto h-12 w-9 text-gold" />}
        <h1 className="t-h1">{job.title || "Sang dalang sedang bekerja…"}</h1>
        {working && (
          <p className="text-muted">
            <Bi id="Biasanya 2 sampai 4 menit. Halaman ini boleh ditinggal, filmnya tetap dibuat" en="Usually 2 to 4 minutes. You can leave this page, the film keeps being made" />
          </p>
        )}
      </header>

      {job.status === "blocked" && (
        <div className="card mx-auto max-w-xl space-y-4 text-center">
          <Icon name="shield" className="mx-auto h-10 w-10 text-gold" />
          <p className="text-lg">{job.message}</p>
          <Link href="/" className={buttonClass("primary")}>
            Cerita lain · Tell another story
          </Link>
        </div>
      )}

      {job.status === "choice" && <GaraGaraChoice job={job} onSent={setJob} />}
      {job.status === "choice" && (
        <ClassroomVote
          job={job}
          onClosed={() =>
            fetch(`/api/jobs/${job.id}`)
              .then((r) => r.json())
              .then(setJob)
              .catch(() => {})
          }
        />
      )}

      {job.status === "review" && <Storyboard job={job} busy={busy} act={act} />}
      {job.status === "review" && <ModelsReceipt job={job} />}
      {job.status === "review" && <AgentTrace job={job} />}

      {working && <PipelineTheatre job={job} />}
      {job.status !== "done" && job.status !== "blocked" && job.status !== "choice" && <Stages job={job} />}

      {job.status === "failed" && (
        <div className="card mx-auto max-w-xl space-y-3 text-center" role="alert">
          <Icon name="alert" className="mx-auto h-10 w-10 text-err" />
          <p className="t-h3">Maaf, ada masalah · Sorry, something went wrong:</p>
          <p className="text-sm text-muted">{job.error}</p>
          <KeptStory />
          <Link href="/" className={buttonClass("primary", "md", "mt-2")}>
            Coba lagi · Try again
          </Link>
        </div>
      )}

      {job.status === "done" && <Player job={job} act={act} busy={busy} />}
    </div>
  );
}

/** After a failed film: say the story is still there (typed text in this tab, or the recording on this device). */
function KeptStory() {
  const [kept, setKept] = useState<"text" | "recording" | null>(null);
  useEffect(() => {
    let stop = false;
    if (readDraft()) Promise.resolve().then(() => !stop && setKept("text"));
    else readRecording().then((r) => !stop && r && setKept("recording"));
    return () => {
      stop = true;
    };
  }, []);
  if (!kept) return null;
  return (
    <p className="text-sm" data-testid="kept-story">
      {kept === "text" ? (
        <Bi id="Ceritamu masih tersimpan di kotak cerita" en="Your story is still in the story box" />
      ) : (
        <Bi id="Rekamanmu masih tersimpan di perangkat ini, tidak perlu merekam ulang" en="Your recording is still on this device, no need to record it again" />
      )}
    </p>
  );
}

function Stages({ job }: { job: Job }) {
  return (
    <section className="card" aria-labelledby="stages-h">
      <h2 id="stages-h" className="t-h3 mb-3">
        <Bi stack id="Tahapan" en="Stages" />
      </h2>
      <ol className="relative space-y-0" aria-live="polite" aria-label="Progress">
        {job.stages.map((s, i) => (
          <li key={s.key} className="relative flex gap-3 pb-4 last:pb-0">
            {i < job.stages.length - 1 && (
              <span aria-hidden="true" className={`absolute left-4 top-9 h-[calc(100%-2.25rem)] w-px ${s.status === "done" ? "bg-ok/40" : "bg-gold/15"}`} />
            )}
            <span
              className={`tabular grid h-8 w-8 shrink-0 place-items-center rounded-full border text-sm font-bold ${STAGE_TONE[s.status] || STAGE_TONE.pending}`}
            >
              <span className={s.status === "running" ? "animate-spin" : ""} aria-hidden="true">
                {ICON[s.status]}
              </span>
              <span className="sr-only">{s.status}</span>
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <div className="flex items-baseline gap-3">
                <span className={`font-semibold ${s.status === "pending" ? "text-muted" : ""}`}>
                  {STAGE_ID[s.key] ? <Bi id={STAGE_ID[s.key]} en={s.label} /> : s.label}
                </span>
                {s.seconds !== undefined && <span className="tabular ml-auto text-xs text-muted">{s.seconds}s</span>}
              </div>
              {s.detail && <p className="t-small mt-0.5 text-muted">{s.detail}</p>}
              {s.thumbs.length > 0 && (
                <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                  {s.thumbs.map((t) =>
                    t.includes(".mp4") ? (
                      <video key={t} src={t} autoPlay muted loop playsInline preload="metadata" className="aspect-video h-20 rounded-md bg-fg/5" />
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img key={t} src={t} alt="" className="h-20 rounded-md bg-fg/5" />
                    ),
                  )}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Storyboard({ job, busy, act }: { job: Job; busy: boolean; act: (fn: () => Promise<Job>) => void }) {
  const approve = (
    <Button
      variant="primary"
      size="lg"
      loading={busy}
      icon="play"
      onClick={() => act(() => postJSON<Job>(`/api/jobs/${job.id}/approve`, {}))}
    >
      <Bi wrap id="Hidupkan wayangnya" en="Bring it to life" />
    </Button>
  );
  return (
    <section className="card space-y-6" aria-labelledby="sb-h">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="sb-h" className="t-h2">Storyboard</h2>
          <p className="t-small mt-1 text-muted">
            <Bi id="Ubah kalimat atau minta gambar ulang, lalu hidupkan" en="Change a line or ask for a new picture, then bring it to life" />
          </p>
        </div>
        <div className="hidden sm:block">{approve}</div>
      </div>
      {job.cast.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {job.cast.map((c) => {
            const info = job.script?.characters?.find((x) => x.id === c.id);
            return (
              <figure key={c.id} className="flex items-start gap-4 rounded-lg border border-gold/15 bg-bg-2/60 p-3">
                <span className="kelir grid h-24 w-20 shrink-0 place-items-center rounded-md" style={{ boxShadow: "none" }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={c.cutout} alt={`Wayang puppet of ${c.name}`} width={64} height={80} className="h-20 w-16 object-contain" />
                </span>
                <figcaption className="min-w-0 text-sm">
                  <span className="font-serif text-lg font-semibold text-gold">{c.name}</span>
                  {info?.wayang_archetype && <span className="text-muted"> · {info.wayang_archetype}</span>}
                  {info?.cultural_note && <span className="mt-1 block text-muted">{info.cultural_note}</span>}
                  {c.returning ? (
                    <span className="mt-2 block text-xs font-semibold text-gold">↩ dari Kotak Wayang · back from the puppet box</span>
                  ) : (
                    <KeepPuppet jobId={job.id} charId={c.id} name={c.name} />
                  )}
                </figcaption>
              </figure>
            );
          })}
        </div>
      )}
      <ol className="grid gap-4 sm:grid-cols-2">
        {job.scenes.map((sc) => (
          <li key={`${sc.n}-${sc.narration}-${sc.still}`}>
            <SceneEditor jobId={job.id} sc={sc} busy={busy} act={act} />
          </li>
        ))}
      </ol>
      <div className="sticky bottom-3 z-10 sm:static">
        <div className="[&>button]:w-full sm:[&>button]:w-auto sm:flex sm:justify-end">{approve}</div>
      </div>
    </section>
  );
}

function SceneEditor({
  jobId,
  sc,
  busy,
  act,
}: {
  jobId: string;
  sc: SceneCard;
  busy: boolean;
  act: (fn: () => Promise<Job>) => void;
}) {
  // keyed by narration in the parent, so a saved/redone line resets this editor
  const [line, setLine] = useState(sc.narration);
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-gold/15 bg-bg-2/60">
      <div className="relative">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={sc.still} alt={`Scene ${sc.n}`} className="aspect-video w-full object-cover" />
        <span className="badge absolute bottom-2 left-2 bg-black/70 font-display text-sm text-[#F5ECDE]">
          <span className="sr-only">Adegan · Scene </span>
          {sc.n}
        </span>
        {sc.placeholder && (
          <Badge tone="placeholder" className="absolute left-2 top-2">
            Adegan cadangan · Placeholder scene
          </Badge>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-2 p-3">
        {sc.rejections.length > 0 && (
          <div className="flex gap-2" aria-label="Pictures the checker sent back">
            {sc.rejections.map((r) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={r.rejected} src={r.rejected} alt={`Rejected: ${r.issue}`} title={r.issue}
                className="h-12 rounded border border-err/60 opacity-70" />
            ))}
          </div>
        )}
        {sc.rejections.length > 0 && (
          <p className="text-xs text-muted">
            ✓ Diperiksa ulang {sc.rejections.length}× · checker redrew it: {sc.rejections[0].issue}
          </p>
        )}
        <textarea
          value={line}
          onChange={(e) => setLine(e.target.value)}
          rows={3}
          className="field text-sm"
          aria-label={`Narration for scene ${sc.n}`}
        />
        <div className="mt-auto flex flex-wrap gap-2">
          <Button
            size="sm"
            icon="check"
            disabled={busy || line === sc.narration}
            onClick={() => act(() => postJSON<Job>(`/api/jobs/${jobId}/scenes/${sc.n}`, { narration: line }))}
          >
            Simpan · Save line
          </Button>
          <Button
            size="sm"
            icon="refresh"
            disabled={busy}
            onClick={() =>
              act(() => postJSON<Job>(`/api/jobs/${jobId}/scenes/${sc.n}`, { narration: line, repaint: true }))
            }
          >
            Gambar ulang · Redo
          </Button>
        </div>
      </div>
    </div>
  );
}

function Player({ job, act, busy }: { job: Job; act: (fn: () => Promise<Job>) => void; busy: boolean }) {
  const [shape, setShape] = useState<"landscape" | "vertical">("landscape");
  const src = job.videos[shape] || job.videos.landscape;
  const vid = useRef<HTMLVideoElement>(null);
  return (
    <div className="space-y-6">
      <section className="space-y-4" aria-label="Film">
        {job.script?.opening && (
          <p className="mx-auto max-w-prose text-center font-display text-lg italic text-gold">“{job.script.opening}”</p>
        )}
        <div className={`frame mx-auto ${shape === "vertical" ? "w-fit" : ""}`}>
          <video
            ref={vid}
            key={src}
            src={src}
            poster={job.poster || undefined}
            controls
            playsInline
            className={`block bg-black ${shape === "vertical" ? "max-h-[75vh]" : "aspect-video w-full"}`}
          >
            {job.captions && <track kind="captions" src={job.captions} srcLang={job.language} label="Subtitles" />}
          </video>
        </div>
        {(job.offline || job.message) && (
          <div className="flex flex-wrap items-center justify-center gap-2 text-sm text-muted">
            {job.offline && <Badge tone="placeholder">Placeholder art</Badge>}
            {job.message && <p>{job.message}</p>}
          </div>
        )}
        <ReadAlong video={vid} src={job.captions} lang={job.language} />
      </section>

      {job.cast.length > 0 && (
        <Link
          href={`/kelir/${job.id}`}
          className="kelir group flex items-center gap-4 rounded-xl p-4 transition-transform duration-kenong ease-sabet hover:-translate-y-0.5 sm:p-5"
        >
          <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-on-kelir text-kelir">
            <Gunungan className="h-9 w-7" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block font-display text-xl font-semibold leading-tight">
              Kelir Live: mainkan sendiri · Perform it yourself
            </span>
            <span className="t-small mt-1 block opacity-80">
              Wayang yang sama, digerakkan jarimu · The same puppets, moved with your fingers
            </span>
          </span>
          <Icon name="play" className="h-6 w-6 shrink-0 transition-transform duration-kenong group-hover:translate-x-1" />
        </Link>
      )}

      <section className="card space-y-4" aria-labelledby="keep-h">
        <h2 id="keep-h" className="t-h3">
          <Bi stack id="Simpan dan bagikan" en="Keep and share" />
        </h2>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 [&>*]:justify-start [&>*]:text-left">
          {job.videos.vertical && (
            <Button icon={shape === "landscape" ? "phone" : "monitor"} onClick={() => setShape(shape === "landscape" ? "vertical" : "landscape")}>
              {shape === "landscape" ? "Tonton 9:16 · Watch 9:16" : "Tonton 16:9 · Watch 16:9"}
            </Button>
          )}
          <a className={buttonClass()} href={src} download={filmFileName(job.title, shape)}>
            <Icon name="download" /> Unduh · Download
          </a>
          <Button
            icon={job.public ? "eye" : "globe"}
            loading={busy}
            onClick={() => act(() => postJSON<Job>(`/api/jobs/${job.id}/share`, { public: !job.public }))}
          >
            {job.public ? "Sembunyikan dari galeri · Hide from gallery" : "Bagikan ke galeri · Share to gallery"}
          </Button>
          <a className={buttonClass()} href={`/api/jobs/${job.id}/puppets.pdf`} download>
            <Icon name="print" /> Cetak wayang · Print the puppets
          </a>
          <a className={buttonClass()} href={`/api/jobs/${job.id}/storybook.pdf`} download>
            <Icon name="book" /> Buku cerita · Storybook (A5)
          </a>
          <Link href="/" className={buttonClass()}>
            <Icon name="mic" /> Buat lagi · Make another
          </Link>
        </div>
        {job.public ? (
          <div className="border-t border-gold/10 pt-4">
            <ShareBar id={job.id} title={job.title} vertical={job.videos.vertical} landscape={job.videos.landscape} />
          </div>
        ) : (
          <ViralExtras id={job.id} title={job.title} />
        )}
      </section>

      <RemixButtons job={job} />

      {job.fallbacks && job.fallbacks.length > 0 && (
        <p className="flex items-start gap-2 rounded-lg border border-gold/25 bg-bg-2/60 p-3 text-sm" data-testid="fallbacks">
          <Icon name="lifebuoy" className="mt-0.5 h-5 w-5 text-gold" />
          <span>
            Cadangan dipakai · Fallbacks used: {job.fallbacks.map((f) => `${f.label}: ${f.what}`).join(" · ")}
          </span>
        </p>
      )}
      {job.cast.length > 0 && (
        <section className="space-y-3" aria-label="Puppets in this film">
          <h3 className="t-h3">
            <Bi stack id="Wayang di film ini" en="The puppets" />
          </h3>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {job.cast.map((c) => (
              <li key={c.id}>
                <figure className="flex h-full flex-col items-center gap-2 rounded-lg border border-gold/15 bg-bg-2/60 p-3 text-center">
                  <span className="kelir grid h-28 w-full place-items-center rounded-md" style={{ boxShadow: "none" }}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={c.cutout} alt={`Wayang puppet of ${c.name}`} width={80} height={96} className="h-24 w-20 object-contain" />
                  </span>
                  <figcaption className="text-sm">
                    <span className="block font-semibold">{c.name}</span>
                    {c.returning ? (
                      <span className="text-xs text-gold">↩ Kotak Wayang</span>
                    ) : (
                      <KeepPuppet jobId={job.id} charId={c.id} name={c.name} />
                    )}
                  </figcaption>
                </figure>
              </li>
            ))}
          </ul>
        </section>
      )}
      <ModelsReceipt job={job} />
      <AgentTrace job={job} />
      <FeedbackSmiles jobId={job.id} page="film" />
      {job.public && <ShareQR path={`/watch/${job.id}`} caption="Pindai untuk menonton · Scan to watch this film" />}
      <p className="text-center text-xs text-muted">
        {job.models.length ? `Models: ${job.models.map(modelLabel).join(", ")}` : "Demo mode (no Meta API calls)"}
        {job.cost_usd ? ` · cost $${job.cost_usd.toFixed(3)}` : ""}
      </p>
    </div>
  );
}
