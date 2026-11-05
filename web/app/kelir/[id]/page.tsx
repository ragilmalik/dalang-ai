import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import KelirLive from "@/components/KelirLive";
import MadeWithMuse from "@/components/MadeWithMuse";
import { filmFileName } from "@/lib/share";
import { apiOrigin, type Job } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Bi from "@/components/ui/Bi";
import Icon from "@/components/ui/Icon";
import { buttonClass } from "@/components/ui/Button";

export const dynamic = "force-dynamic";

async function getJob(id: string): Promise<Job | null> {
  const r = await fetch(`${apiOrigin()}/api/jobs/${encodeURIComponent(id)}`, { cache: "no-store" }).catch(() => null);
  return r && r.ok ? ((await r.json()) as Job) : null;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const job = await getJob(id);
  return {
    title: job ? `Kelir Live · ${job.title} · Dalang AI` : "Kelir Live · Dalang AI",
    description: "Perform your own wayang film: the film's puppets as shadows on a lamp-lit screen, moved with your fingers.",
    robots: { index: false }, // a family's own stage; the public page is /watch/[id]
  };
}

/** Kelir Live: after the film, the child performs it with the same puppets, as shadows, in the browser. */
export default async function KelirPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const job = await getJob(id);
  if (!job) notFound();
  const cast = job.cast.map((c) => ({ id: c.id, name: c.name, cutout: c.cutout }));
  const scenes = job.scenes.map((s) => ({ n: s.n, narration: s.narration, backdrop: s.backdrop || s.still }));

  return (
    <div className="mx-auto max-w-5xl space-y-5 pt-6">
      <header className="space-y-2 text-center">
        <p className="flex items-center justify-center gap-2 text-sm font-semibold text-gold">
          <span className="blencong" aria-hidden="true" /> Kelir Live
        </p>
        <h1 className="t-h1">
          <Bi stack id="Jadilah dalangnya" en="You be the dalang" />
        </h1>
        <p className="text-muted">
          {job.title}: mainkan sendiri wayangmu di balik kelir · perform your own film with its puppets.
        </p>
        <p className="flex flex-wrap items-center justify-center gap-2 pt-1">
          <MadeWithMuse />
          {job.offline && <Badge tone="placeholder">Gambar contoh · Placeholder art</Badge>}
        </p>
      </header>
      {cast.length ? (
        <KelirLive
          title={job.title}
          cast={cast}
          scenes={scenes}
          gunungan={`/media/${job.id}/puppets/gunungan.png`}
          fileName={`${filmFileName(job.title, "landscape").replace(/-16x9\.mp4$/, "")}-kelir-live`}
        />
      ) : (
        <p className="card text-center">Wayangnya belum siap · The puppets are not ready yet.</p>
      )}
      <div className="flex flex-wrap justify-center gap-2">
        <Link href={job.public ? `/watch/${job.id}` : `/film/${job.id}`} className={buttonClass()}>
          <Icon name="back" /> Film
        </Link>
        <Link href="/" className={buttonClass()}>
          <Icon name="mic" /> Cerita baru · New story
        </Link>
      </div>
    </div>
  );
}
