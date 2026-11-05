import type { Metadata } from "next";
import Link from "next/link";
import MadeWithMuse from "@/components/MadeWithMuse";
import Sembah from "@/components/Sembah";
import ShareCard from "@/components/ShareCard";
import { apiOrigin } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Bi from "@/components/ui/Bi";
import Icon from "@/components/ui/Icon";
import Gunungan from "@/components/ui/Gunungan";
import { buttonClass } from "@/components/ui/Button";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Pentas · The showcase wall · Dalang AI",
  description:
    "Wayang kulit films made from children's stories, shared by their families. Bow 🙏 Sembah to your favourite, then tell your own.",
  alternates: { canonical: "/pentas" },
  openGraph: {
    type: "website",
    siteName: "Dalang AI",
    url: "/pentas",
    title: "Pentas · Children's wayang films · Dalang AI",
    description: "Children tell stories out loud; Meta Muse models perform them as Javanese shadow-puppet films.",
    images: [{ url: "/opengraph-image.png", width: 1200, height: 630, alt: "Dalang AI: your story becomes a wayang film" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Pentas · Children's wayang films · Dalang AI",
    description: "Children tell stories out loud; Meta Muse models perform them as Javanese shadow-puppet films.",
    images: ["/twitter-image.png"],
  },
};

interface Item {
  id: string;
  title: string;
  poster: string | null;
  language: string;
  duration_s?: number;
  applause?: number;
  created?: number;
  sample?: boolean;
  offline?: boolean;
}

const LANG: Record<string, string> = { id: "Bahasa Indonesia", jv: "Basa Jawa", en: "English" };

/** /pentas: the public showcase wall. Newest first, or most "Sembah" (the Javanese bow of thanks) first. */
export default async function Pentas({ searchParams }: { searchParams: Promise<{ urut?: string }> }) {
  const { urut } = await searchParams;
  const top = urut === "sembah";
  const items: Item[] = await fetch(`${apiOrigin()}/api/gallery`, { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : []))
    .catch(() => []);
  // families' own films first in both orders; labelled samples after them
  const sorted = [...items].sort(
    (a, b) =>
      Number(!!a.sample) - Number(!!b.sample) ||
      (top ? (b.applause ?? 0) - (a.applause ?? 0) : 0) ||
      (b.created ?? 0) - (a.created ?? 0),
  );
  const total = items.reduce((n, it) => n + (it.applause ?? 0), 0);
  return (
    <div className="space-y-8 pt-8 sm:pt-12">
      <header className="grid items-end gap-6 md:grid-cols-[1fr_auto]">
        <div className="space-y-3">
          <span className="blencong block" aria-hidden="true" />
          <h1 className="t-display">
            <Bi stack id="Pentas" en="The showcase" />
          </h1>
          <p className="t-lead max-w-prose text-muted">
            Film wayang dari cerita anak-anak. Beri 🙏 Sembah untuk favoritmu · Wayang films from children&apos;s stories. Bow
            🙏 to your favourite.
          </p>
        </div>
        <div className="flex flex-col items-start gap-3 md:items-end">
          <p className="tabular font-display text-2xl font-semibold" data-testid="pentas-stats">
            {items.length} film · {total} sembah
          </p>
          <MadeWithMuse size="lg" />
        </div>
      </header>
      <nav className="seg w-full max-w-xl grid-cols-2" aria-label="Urutkan · Sort">
        <Link href="/pentas" aria-current={!top ? "page" : undefined} className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-3 text-center text-sm font-semibold leading-tight transition-colors sm:whitespace-nowrap duration-kenong ${!top ? "bg-surface-2 text-fg shadow-1" : "text-muted hover:text-fg"}`}>
          <Icon name="clock" className="h-4 w-4 shrink-0" /> <Bi wrap id="Terbaru" en="Newest" />
        </Link>
        <Link
          href="/pentas?urut=sembah"
          aria-current={top ? "page" : undefined}
          className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-3 text-center text-sm font-semibold leading-tight transition-colors sm:whitespace-nowrap duration-kenong ${top ? "bg-surface-2 text-fg shadow-1" : "text-muted hover:text-fg"}`}
        >
          <span aria-hidden="true">🙏</span> <Bi wrap id="Paling disembah" en="Most applauded" />
        </Link>
      </nav>
      {sorted.length === 0 ? (
        <div className="kawung card space-y-4 py-12 text-center">
          <Gunungan className="mx-auto h-16 w-12 text-gold" />
          <p className="t-h3">Belum ada film di panggung · No films on the stage yet.</p>
          <Link href="/" className={buttonClass("primary")}>
            Jadilah yang pertama · Be the first!
          </Link>
        </div>
      ) : (
        <ol className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" data-testid="pentas-wall">
          {sorted.map((it, i) => (
            <li
              key={it.id}
              className="group relative flex flex-col overflow-hidden rounded-xl border border-gold/15 bg-surface/80 shadow-1 transition-[border-color,box-shadow] duration-kenong hover:border-gold/45 hover:shadow-2"
              data-applause={it.applause ?? 0}
            >
              <Link href={`/watch/${it.id}`} className="block focus-visible:outline-offset-[-3px]">
                <span className="block overflow-hidden bg-bg-2">
                  {it.poster && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={it.poster}
                      alt={`${it.title}: film poster`}
                      width={1200}
                      height={630}
                      loading={i < 2 ? "eager" : "lazy"}
                      decoding="async"
                      className="aspect-[40/21] w-full object-cover transition-transform duration-gong ease-sabet group-hover:scale-[1.03]"
                    />
                  )}
                </span>
                <span className="block px-4 pt-3 font-display text-xl font-semibold leading-tight">{it.title}</span>
              </Link>
              <span className="absolute left-3 top-3 flex flex-wrap items-start gap-1.5">
                {top && !it.sample && i < 3 && (
                  <span className="badge bg-[#F5ECDE] text-[#1C122E]">
                    {["🥇", "🥈", "🥉"][i]} #{i + 1}
                  </span>
                )}
                {it.sample && <Badge tone="sample">Contoh · Sample</Badge>}
                {it.offline && <Badge tone="placeholder">Placeholder art</Badge>}
              </span>
              <p className="px-4 pt-1 text-sm text-muted">
                {LANG[it.language] ?? it.language.toUpperCase()}
                {it.duration_s ? ` · ${Math.round(it.duration_s)} s` : ""}
              </p>
              <div className="mt-auto flex flex-wrap items-center gap-2 p-4 pt-3">
                <Sembah id={it.id} initial={it.applause ?? 0} />
                <ShareCard
                  id={it.id}
                  title={it.title}
                  poster={it.poster}
                  applause={it.applause}
                  sample={it.sample}
                  offline={it.offline}
                />
              </div>
            </li>
          ))}
        </ol>
      )}
      <p className="text-center">
        <Link href="/" className={buttonClass("primary", "lg")}>
          <Icon name="mic" /> Ceritakan kisahmu · Tell your story
        </Link>
      </p>
    </div>
  );
}
