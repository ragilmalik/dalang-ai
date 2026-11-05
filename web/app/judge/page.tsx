import type { Metadata } from "next";
import Link from "next/link";
import AgentTrace from "@/components/AgentTrace";
import FilmVideo from "@/components/FilmVideo";
import ModelsReceipt from "@/components/ModelsReceipt";
import { apiOrigin, modelLabel, type Health, type Job } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Bi from "@/components/ui/Bi";
import { buttonClass } from "@/components/ui/Button";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Dalang AI · Judge mode: the whole project in 60 seconds",
  description: "A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film.",
};

const STEPS: [string, string][] = [
  ["0-10 s", "Watch the film below: a child's story performed as wayang kulit (gunungan, Kocap kacarita opening, captions, gamelan). Turn on Read along."],
  ["10-25 s", "Open “Penjaga Budaya” and the consistency score: a Muse Spark agent checked every scene against the cultural rules built into the app before anything was drawn, and SAM 3.1 cut-outs keep each puppet identical in every scene."],
  ["25-40 s", "Read the Meta models receipt: every model, what it did, calls, tokens and the estimated cost of this one film."],
  ["40-55 s", "Open “Di balik kelir · Behind the screen”: every Meta call and agent decision, including the checker rejecting a picture and the redraw that passed."],
  ["55-60 s", "Make your own: go home, tap a Story Starter (Kancil, Timun Mas…), press Make my wayang. Or try Gara-gara mode."],
];

async function sample(): Promise<Job | null> {
  const items: { id: string; sample?: boolean }[] = await fetch(`${apiOrigin()}/api/gallery`, { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : []))
    .catch(() => []);
  const pick = items.find((i) => i.sample) || items[0];
  if (!pick) return null;
  return fetch(`${apiOrigin()}/api/jobs/${pick.id}`, { cache: "no-store" })
    .then((r) => (r.ok ? (r.json() as Promise<Job>) : null))
    .catch(() => null);
}

async function health(): Promise<Health | null> {
  return fetch(`${apiOrigin()}/api/health`, { cache: "no-store" })
    .then((r) => (r.ok ? (r.json() as Promise<Health>) : null))
    .catch(() => null);
}

export default async function Judge() {
  const [job, h] = await Promise.all([sample(), health()]);
  return (
    <div className="mx-auto max-w-4xl space-y-8 pt-8 sm:pt-12">
      <header className="space-y-3">
        <h1 className="t-display">
          <Bi stack id="Judge mode" en="60 seconds" />
        </h1>
        <p className="t-lead max-w-prose text-muted">
          A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film.
        </p>
        {h && (
          <p className="text-sm text-muted" data-testid="judge-mode">
            {h.mode === "not_configured"
              ? "This server has no Meta key yet, so it can't make new films. The sample films below were made with the live Meta models."
              : h.offline
                ? "This server runs the built-in fake Meta API (test mode): placeholder art, same request and parsing code as live."
                : `This server is live on the Meta Model API: ${[...new Set(Object.values(h.models))].map(modelLabel).join(", ")}.`}
          </p>
        )}
      </header>
      <section className="card" aria-labelledby="what-to-click">
        <h2 id="what-to-click" className="t-h2">What to click</h2>
        <ol className="mt-5 space-y-4">
          {STEPS.map(([t, s]) => (
            <li key={t} className="flex flex-col items-start gap-1 sm:flex-row sm:gap-4">
              <span className="tabular w-fit shrink-0 rounded-full border border-gold/40 bg-bg-2 px-3 py-1 text-sm font-bold text-gold sm:w-24 sm:text-center">
                {t}
              </span>
              <span className="sm:pt-1">{s}</span>
            </li>
          ))}
        </ol>
      </section>
      {job && job.videos?.landscape ? (
        <section className="space-y-6" aria-label="Sample film">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="t-h2">{job.title}</h2>
            {job.offline ? (
              <Badge tone="placeholder">Placeholder art from the built-in fake Meta API (test mode)</Badge>
            ) : (
              job.sample && (
                <Badge tone="sample">Contoh · Sample story written for this project, made with the live Meta models</Badge>
              )
            )}
          </div>
          <FilmVideo src={job.videos.landscape} poster={job.poster || undefined} captions={job.captions} lang={job.language} />
          <ModelsReceipt job={job} />
          <AgentTrace job={job} />
          <p className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
            <Link className="link" href={`/watch/${job.id}`}>Open this film&apos;s page</Link>
            <a className="link" href={`/api/jobs/${job.id}/receipt`}>receipt JSON</a>
            <a className="link" href={`/api/jobs/${job.id}/trace`}>trace JSON</a>
            <a className="link" href={`/api/jobs/${job.id}/storybook.pdf`}>storybook PDF</a>
          </p>
        </section>
      ) : (
        <section className="card space-y-4 text-center" data-testid="judge-no-sample">
          <p className="t-h3">There is no sample film on this server yet.</p>
          <p className="mx-auto max-w-prose text-muted">
            Make one yourself: tap a Story Starter on the home page and press Make my wayang. The film page shows the
            same receipt and behind-the-screen trace as the steps above.
          </p>
          <Link href="/" className={buttonClass("primary")}>Make a film</Link>
          <p className="text-xs text-muted">
            Running this yourself? The three sample films ship in content/samples/ and load on start (BUNDLED_SAMPLES=1).
          </p>
        </section>
      )}
      <section className="card text-sm" aria-labelledby="more">
        <h2 id="more" className="t-h3">More</h2>
        <ul className="mt-3 space-y-2">
          <li><Link className="link" href="/">Make a film</Link> (Story Starters, voice, upload or type; Bahasa Indonesia, Basa Jawa, English)</li>
          <li><Link className="link" href="/guru">Teachers: a 30-minute wayang session</Link></li>
          <li><Link className="link" href="/gallery">Gallery</Link> and <Link className="link" href="/kotak">Kotak Wayang</Link></li>
          <li><a className="link" href="/api/docs">API docs (OpenAPI)</a></li>
        </ul>
      </section>
    </div>
  );
}
