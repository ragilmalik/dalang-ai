import Gunungan from "@/components/ui/Gunungan";

/**
 * What the gallery and the Pentas wall show for the moment the server is fetching films: the page's own heading and a
 * grid of card-shaped placeholders, so the layout doesn't jump when the films arrive. The gunungan sways the way a
 * dalang flutters it between scenes. Screen readers hear one short "loading" line instead of empty boxes.
 */
export default function CardsSkeleton({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="space-y-8 pt-8 sm:pt-12" aria-busy="true">
      <header className="space-y-3">
        <h1 className="t-display">
          {title}
          <span className="t-lead block text-muted">{subtitle}</span>
        </h1>
        <p className="flex items-center gap-2 text-muted" role="status">
          <Gunungan className="kayon-sway h-6 w-5 text-gold" />
          Memuat film… · Loading films…
        </p>
      </header>
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <div key={i} className="overflow-hidden rounded-xl border border-gold/15 bg-surface/80 shadow-1">
            <div className="skeleton aspect-[40/21] w-full bg-bg-2" style={{ animationDelay: `${i * 120}ms` }} />
            <div className="space-y-2 p-4">
              <div className="skeleton h-5 w-3/4 rounded bg-fg/10" style={{ animationDelay: `${i * 120 + 60}ms` }} />
              <div className="skeleton h-4 w-1/3 rounded bg-fg/10" style={{ animationDelay: `${i * 120 + 120}ms` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
