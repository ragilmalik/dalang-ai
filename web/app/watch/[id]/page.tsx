import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import FeedbackSmiles from "@/components/FeedbackSmiles";
import FilmVideo from "@/components/FilmVideo";
import Sembah from "@/components/Sembah";
import MadeWithMuse from "@/components/MadeWithMuse";
import ShareCard from "@/components/ShareCard";
import ShareBar from "@/components/ShareBar";
import { apiOrigin, type Job } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Bi from "@/components/ui/Bi";
import Icon from "@/components/ui/Icon";
import { buttonClass } from "@/components/ui/Button";

async function getJob(id: string): Promise<Job | null> {
  const r = await fetch(`${apiOrigin()}/api/jobs/${encodeURIComponent(id)}`, { cache: "no-store" }).catch(() => null);
  if (!r || !r.ok) return null;
  const job = (await r.json()) as Job;
  return job.status === "done" && job.public ? job : null; // only films the family chose to share
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const job = await getJob(id);
  if (!job) return { title: "Dalang AI" };
  const title = `${job.title} · a wayang film made with Dalang AI`;
  const description = job.script?.moral
    ? `“${job.script.moral}” A wayang kulit film made from a child's story. Make your own.`
    : "A wayang kulit film made from a child's story. Tell yours and get a film back.";
  const image = job.poster ? [{ url: job.poster, width: 1200, height: 630, alt: `${job.title}: wayang kulit film poster` }] : [];
  return {
    title: `${job.title} · Dalang AI`,
    description,
    alternates: { canonical: `/watch/${job.id}` },
    openGraph: {
      type: "video.other",
      siteName: "Dalang AI",
      url: `/watch/${job.id}`,
      title,
      description,
      images: image,
      videos: job.videos.landscape ? [{ url: job.videos.landscape, width: 1280, height: 720, type: "video/mp4" }] : [],
    },
    twitter: { card: "summary_large_image", title, description, images: image },
  };
}

export default async function Watch({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const job = await getJob(id);
  if (!job) notFound();
  const cast = job.script?.characters ?? [];
  return (
    <div className="mx-auto max-w-4xl space-y-6 pt-8 sm:pt-12">
      <header className="space-y-4 text-center">
        <span className="blencong mx-auto block" aria-hidden="true" />
        <h1 className="t-h1">{job.title}</h1>
        {(job.sample || job.offline) && (
          <p className="flex flex-wrap justify-center gap-2">
            {job.sample && <Badge tone="sample">Contoh · Sample film</Badge>}
            {job.offline && <Badge tone="placeholder">Gambar contoh · Placeholder art (made without the live Meta models)</Badge>}
          </p>
        )}
        {job.script?.opening && (
          <p className="mx-auto max-w-prose font-display text-lg italic text-gold">“{job.script.opening}”</p>
        )}
      </header>
      <FilmVideo src={job.videos.landscape} poster={job.poster || undefined} captions={job.captions} lang={job.language} />
      {job.script?.moral && <p className="mx-auto max-w-prose text-center text-lg text-muted">{job.script.moral}</p>}
      <div className="flex justify-center">
        <MadeWithMuse />
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        <Sembah id={job.id} initial={job.applause ?? 0} />
        <ShareCard id={job.id} title={job.title} poster={job.poster} applause={job.applause} sample={job.sample} offline={job.offline} />
        {job.cast.length > 0 && (
          <Link className={buttonClass()} href={`/kelir/${job.id}`}>
            <Icon name="stage" /> Kelir Live · Perform it
          </Link>
        )}
        <a className={buttonClass()} href={`/api/jobs/${job.id}/puppets.pdf`} download>
          <Icon name="print" /> Cetak wayang · Print the puppets
        </a>
        <a className={buttonClass()} href={`/api/jobs/${job.id}/storybook.pdf`} download>
          <Icon name="book" /> Buku cerita · Storybook (A5)
        </a>
      </div>
      <Link className={buttonClass("primary", "lg", "w-full sm:mx-auto sm:flex sm:w-fit")} href="/">
        <Icon name="mic" /> <Bi wrap id="Buat wayangmu sendiri" en="Make your own" />
      </Link>
      <section className="card">
        <ShareBar id={job.id} title={job.title} vertical={job.videos.vertical} landscape={job.videos.landscape} />
      </section>
      <FeedbackSmiles jobId={job.id} page="watch" />
      {cast.some((c) => c.cultural_note) && (
        <section className="card" aria-labelledby="behind">
          <h2 id="behind" className="t-h3 mb-4">
            <Bi stack id="Di balik wayang" en="Behind the puppets" />
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2">
            {cast.map((c) => (
              <li key={c.id} className="border-l-2 border-gold/40 pl-4 text-sm">
                <span className="font-display text-lg font-semibold text-gold">{c.name}</span>
                <span className="text-muted"> · {c.wayang_archetype}</span>
                {c.cultural_note && <span className="mt-1 block">{c.cultural_note}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
