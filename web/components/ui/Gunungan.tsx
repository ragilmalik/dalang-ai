/**
 * The gunungan (kayon): the mountain-and-tree puppet that opens a wayang performance, marks each change of scene
 * and closes the night. Drawn for Dalang AI as a simple leaf with the tree of life and the gate at its foot.
 * `solid` is the logo mark; the outline version sits on dividers, loaders and empty states.
 */
export default function Gunungan({
  className = "h-8 w-6",
  solid = false,
  title,
}: {
  className?: string;
  solid?: boolean;
  title?: string;
}) {
  const leaf = "M50 4C63 22 93 50 93 88c0 24-17 38-43 40C24 126 7 112 7 88 7 50 37 22 50 4Z";
  const tree =
    "M50 108V34 M50 92C42 84 32 82 22 86 M50 92c8-8 18-10 28-6 M50 74c-7-7-15-9-23-6 M50 74c7-7 15-9 23-6 M50 57c-5-5-11-7-17-5 M50 57c5-5 11-7 17-5 M50 44c-3-3-7-4-10-3 M50 44c3-3 7-4 10-3";
  const gate = "M39 128v-16c0-6 5-10 11-10s11 4 11 10v16";
  return (
    <svg
      viewBox="0 0 100 132"
      className={className}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      focusable="false"
    >
      {solid ? (
        <>
          <path d={leaf} fill="rgb(var(--c-prada))" />
          <path d={tree} fill="none" stroke="rgb(var(--c-on-prada))" strokeWidth="4" strokeLinecap="round" />
          <path d={gate} fill="rgb(var(--c-on-prada))" />
        </>
      ) : (
        <g fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
          <path d={leaf} strokeWidth="4" />
          <path d={tree} strokeWidth="3" />
          <path d={gate} strokeWidth="3" />
        </g>
      )}
    </svg>
  );
}
