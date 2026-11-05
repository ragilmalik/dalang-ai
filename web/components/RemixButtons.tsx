"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { LANGS, postJSON, type Job } from "@/lib/api";
import Icon from "@/components/ui/Icon";

/**
 * Remix a finished film with the same drawn puppets: told in another language, or from the villain's view.
 * Only Muse Spark re-writes the lakon; pictures and puppets are reused. Shown once the film is finished.
 */
export default function RemixButtons({ job }: { job: Job }) {
  const router = useRouter();
  const ok = job.status === "done";
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function remix(language: string, pov: "original" | "villain") {
    setBusy(true);
    setErr("");
    try {
      const r = await postJSON<{ id: string }>(`/api/jobs/${job.id}/remix`, { language, pov });
      router.push(`/film/${r.id}`);
    } catch (e) {
      setErr((e as Error).message);
      setBusy(false);
    }
  }

  const origin = job.remix_of && (
    <p className="text-sm text-muted">
      <Icon name="remix" className="mr-1 inline h-4 w-4 text-gold" /> Remix dari · remixed from{" "}
      <Link className="link" href={`/film/${job.remix_of}`}>
        film asli · the original
      </Link>
      {job.remix?.pov === "villain" && job.remix.villain && ` · dari sisi ${job.remix.villain} · ${job.remix.villain}'s view`}
    </p>
  );
  if (!ok) return origin || null;
  const others = LANGS.filter((l) => l.code !== job.language);
  return (
    <section className="card space-y-4" data-testid="remix" aria-label="Remix">
      {origin}
      <div>
        <h2 className="t-h3 flex items-center gap-2">
          <Icon name="remix" className="h-5 w-5 text-gold" />
          Remix
        </h2>
        <p className="t-small mt-1 text-muted">Wayang yang sama, cerita baru · same puppets, a new telling</p>
      </div>
      <div className="grid gap-2 sm:flex sm:flex-wrap">
        {others.map((l) => (
          <button key={l.code} type="button" className="btn justify-start sm:justify-center" disabled={busy} onClick={() => remix(l.code, "original")}>
            <Icon name="globe" /> {l.label}
          </button>
        ))}
        <button type="button" className="btn justify-start sm:justify-center" disabled={busy} onClick={() => remix(job.language, "villain")}>
          <span aria-hidden="true" className="w-5 text-center">😈</span> Dari sisi si jahat · Villain&apos;s view
        </button>
      </div>
      {busy && (
        <p className="flex items-center gap-2 text-sm text-muted" role="status">
          <span className="spinner" aria-hidden="true" /> Ki Dalang menulis ulang · rewriting…
        </p>
      )}
      {err && (
        <p role="alert" className="text-sm text-err">
          {err}
        </p>
      )}
    </section>
  );
}
