import type { Metadata } from "next";
import Link from "next/link";
import { ViewTransition } from "react";
import { apiOrigin } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Bi from "@/components/ui/Bi";
import Gunungan from "@/components/ui/Gunungan";
import { buttonClass } from "@/components/ui/Button";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Galeri · Gallery · Dalang AI",
  description: "Wayang kulit films that families chose to share, made from children's stories.",
};

interface Item {
  id: string;
  title: string;
  poster: string | null;
  poster_card?: string | null; // 800 px WebP made by api/thumbs.py; absent on older APIs
  language: string;
  duration_s?: number;
  applause?: number;
  sample?: boolean;
  offline?: boolean;
}

const LANG: Record<string, string> = { id: "Bahasa Indonesia", jv: "Basa Jawa", en: "English" };

export default async function Gallery() {
  const items: Item[] = await fetch(`${apiOrigin()}/api/gallery`, { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : []))
    .catch(() => []);
  return (
    <div className="space-y-8 pt-8 sm:pt-12">
      <header className="space-y-3">
        <h1 className="t-display">
          <Bi stack id="Galeri" en="Gallery" />
        </h1>
        <p className="t-lead max-w-prose text-muted">
          Film yang dibagikan keluarga. Tekan 🙏 Sembah untuk film favoritmu. · Films families chose to share. Bow 🙏 to
          your favourite.
        </p>
      </header>
      {items.length === 0 ? (
        <div className="kawung card space-y-4 py-12 text-center">
          <Gunungan className="mx-auto h-16 w-12 text-gold" />
          <p className="t-h3">Belum ada film yang dibagikan · No shared films yet.</p>
          <Link href="/" className={buttonClass("primary")}>
            Jadilah yang pertama · Be the first!
          </Link>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((it) => (
            <Link
              key={it.id}
              href={`/watch/${it.id}`}
              className="group relative block overflow-hidden rounded-xl border border-gold/15 bg-surface/80 shadow-1 transition-[border-color,box-shadow] duration-kenong hover:border-gold/45 hover:shadow-2"
            >
              <span className="block overflow-hidden bg-bg-2">
                {it.poster && (
                  // the poster morphs into the player on the watch page (shared view transition)
                  <ViewTransition name={`film-${it.id}`} share="morph" default="none">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={it.poster_card || it.poster}
                      srcSet={it.poster_card ? `${it.poster_card} 800w, ${it.poster} 1200w` : undefined}
                      sizes="(min-width: 1024px) 380px, (min-width: 640px) 50vw, 100vw"
                      alt={`${it.title}: film poster`}
                      width={1200}
                      height={630}
                      loading="lazy"
                      decoding="async"
                      className="aspect-[40/21] w-full object-cover transition-transform duration-gong ease-sabet group-hover:scale-[1.03]"
                    />
                  </ViewTransition>
                )}
              </span>
              {(it.sample || it.offline) && (
                <span className="absolute left-3 top-3 flex flex-wrap items-start gap-1.5">
                  {it.sample && <Badge tone="sample">Contoh · Sample</Badge>}
                  {it.offline && <Badge tone="placeholder">Placeholder art</Badge>}
                </span>
              )}
              <span className="block p-4">
                <span className="block font-display text-xl font-semibold leading-tight">{it.title}</span>
                <span className="tabular mt-1 block text-sm text-muted">
                  {LANG[it.language] ?? it.language.toUpperCase()}
                  {it.duration_s ? ` · ${Math.round(it.duration_s)} s` : ""} · <span aria-hidden="true">🙏</span>
                  <span className="sr-only">Sembah votes:</span> {it.applause ?? 0}
                </span>
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
