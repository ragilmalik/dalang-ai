/** A slim progress bar. `label` names it for screen readers; the visible text lives next to it. */
export default function Progress({ value, max = 100, label }: { value: number; max?: number; label: string }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value * 100) / max)) : 0;
  return (
    <div className="progress" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}
