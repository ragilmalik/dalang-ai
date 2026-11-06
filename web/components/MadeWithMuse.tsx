/** "Made with Meta Muse" badge: which models made this, for share cards, the watch page and the public wall. */
export default function MadeWithMuse({ size = "sm" }: { size?: "sm" | "lg" }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-gold/40 bg-bg-2/80 font-semibold text-fg ${
        size === "lg" ? "px-4 py-1.5 text-sm" : "px-3 py-1 text-xs"
      }`}
      title="Muse Voice Transcribe · Muse Spark · Muse Image · SAM 3.1 · Muse Wonder"
      data-testid="made-with-muse"
    >
      <span aria-hidden="true" className="text-gold">
        ✦
      </span>
      Made with Meta Muse
    </span>
  );
}
