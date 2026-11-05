/**
 * The app's icon set: drawn for Dalang AI on a 24 px grid, 1.75 px round strokes, one style everywhere.
 * Icons are decoration next to a text label, so they are aria-hidden; an icon-only button gets an aria-label.
 */
const P: Record<string, string> = {
  mic: "M12 3.5a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0v-5a3 3 0 0 1 3-3Z M5.5 11a6.5 6.5 0 0 0 13 0 M12 17.5V21 M8.5 21h7",
  stop: "M7 7h10v10H7z",
  upload: "M12 15V4 M7.5 8.5 12 4l4.5 4.5 M4.5 15v3.5a1.5 1.5 0 0 0 1.5 1.5h12a1.5 1.5 0 0 0 1.5-1.5V15",
  type: "M3.5 7.5h17v10h-17z M7 11h.01 M10.5 11h.01 M14 11h.01 M17 11h.01 M8 14.5h8",
  play: "M8 5.5v13l10.5-6.5z",
  download: "M12 4v11 M7.5 10.5 12 15l4.5-4.5 M4.5 19.5h15",
  share: "M12 15V4 M8 7.5 12 3.5l4 4 M6 11H5v9.5h14V11h-1",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  print: "M7 9V4h10v5 M7 17H5a1.5 1.5 0 0 1-1.5-1.5v-5A1.5 1.5 0 0 1 5 9h14a1.5 1.5 0 0 1 1.5 1.5v5A1.5 1.5 0 0 1 19 17h-2 M7 14h10v6H7z",
  book: "M12 6.5C10.5 5 8 4.5 4 4.5v13c4 0 6.5.5 8 2 1.5-1.5 4-2 8-2v-13c-4 0-6.5.5-8 2Z M12 6.5v13",
  refresh: "M19.5 12a7.5 7.5 0 1 1-2.2-5.3 M19.5 4.5v4h-4",
  box: "M3.5 8 12 4l8.5 4v8.5L12 20.5 3.5 16.5z M3.5 8 12 12l8.5-4 M12 12v8.5",
  grid: "M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z",
  stage: "M3.5 5h17 M5 5v12.5 M19 5v12.5 M3.5 17.5h17 M8 5c0 2.5 1.5 4 4 4s4-1.5 4-4 M12 13v4.5",
  teacher: "M12 4 2.5 8.5 12 13l9.5-4.5z M6.5 10.5V15c1.5 1.5 3.5 2.2 5.5 2.2s4-.7 5.5-2.2v-4.5 M21.5 8.5V14",
  judge: "M12 3.5 14.4 8.4l5.4.8-3.9 3.8.9 5.4L12 15.9l-4.8 2.5.9-5.4-3.9-3.8 5.4-.8z",
  back: "M15 5.5 8.5 12l6.5 6.5",
  close: "M6 6l12 12 M18 6 6 18",
  check: "M5 12.5 10 17.5 19 7",
  globe: "M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Z M3.5 12h17 M12 3.5c2.4 2.4 3.5 5.2 3.5 8.5s-1.1 6.1-3.5 8.5c-2.4-2.4-3.5-5.2-3.5-8.5S9.6 5.9 12 3.5Z",
  sun: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z M12 2.5v2 M12 19.5v2 M4.6 4.6 6 6 M18 18l1.4 1.4 M2.5 12h2 M19.5 12h2 M4.6 19.4 6 18 M18 6l1.4-1.4",
  moon: "M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10Z",
  menu: "M4 7h16 M4 12h16 M4 17h10",
  eye: "M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z M12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z",
  shield: "M12 3.5 19 6v5.5c0 4.2-2.9 7.6-7 9-4.1-1.4-7-4.8-7-9V6z M9 12l2 2 4-4",
  receipt: "M6 3.5h12v17l-2-1.3-2 1.3-2-1.3-2 1.3-2-1.3-2 1.3z M9 8h6 M9 11.5h6 M9 15h3.5",
  palette: "M12 3.5a8.5 8.5 0 0 0 0 17c1.4 0 2-1 1.6-2.1-.5-1.4.4-2.4 1.8-2.4h1.7a3.4 3.4 0 0 0 3.4-3.4C20.5 7.3 16.7 3.5 12 3.5Z M7.5 11h.01 M10 7.5h.01 M14.5 7.5h.01",
  image: "M4 5h16v14H4z M4 15.5 9 11l4 4 2.5-2.5L20 17 M15.5 8.5h.01",
  sound: "M4.5 9.5h3.5L12.5 6v12L8 14.5H4.5z M16 9a4 4 0 0 1 0 6 M18.5 6.5a7.5 7.5 0 0 1 0 11",
  mute: "M4.5 9.5h3.5L12.5 6v12L8 14.5H4.5z M16.5 9.5l5 5 M21.5 9.5l-5 5",
  record: "M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Z",
  flip: "M7 7.5h12 M15.5 4 19 7.5 15.5 11 M17 16.5H5 M8.5 13 5 16.5 8.5 20",
  sembah: "M9.5 20.5V13l2-6.5c.3-1 1.7-1 2 0l.5 1.6 M14.5 20.5V13l-1-3.2 M9.5 13 7 10.5c-.7-.7-1.9 0-1.6 1l1.6 5 2.5 4 M14.5 13l2.5-2.5c.7-.7 1.9 0 1.6 1l-1.6 5-2.5 4",
  ballot: "M5 9.5h14v10H5z M8 9.5 10.5 4l5.5 2-1.6 3.5 M9 14h6",
  trash: "M4.5 7h15 M9.5 7V4.5h5V7 M6.5 7l1 13h9l1-13 M10 11v5.5 M14 11v5.5",
  chevron: "M6.5 9.5 12 15l5.5-5.5",
  clock: "M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Z M12 7.5V12l3 2",
  lifebuoy: "M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Z M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z M6 6l3.5 3.5 M18 6l-3.5 3.5 M6 18l3.5-3.5 M18 18l-3.5-3.5",
  info: "M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Z M12 11v5 M12 8h.01",
  alert: "M12 4 21 19.5H3z M12 10v4 M12 17h.01",
  film: "M4 5h16v14H4z M8 5v14 M16 5v14 M4 9h4 M4 15h4 M16 9h4 M16 15h4",
  sticker: "M5 4.5h14v8.5L13 19.5H5z M13 19.5V13h6",
  phone: "M8 3h8a1.5 1.5 0 0 1 1.5 1.5v15A1.5 1.5 0 0 1 16 21H8a1.5 1.5 0 0 1-1.5-1.5v-15A1.5 1.5 0 0 1 8 3Z M11 18h2",
  monitor: "M3.5 5h17v11h-17z M9 20h6 M12 16v4",
  remix: "M4 7.5h11.5a4 4 0 0 1 0 8H10 M7.5 4 4 7.5 7.5 11 M13 12.5 10 15.5l3 3",
  qr: "M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h2.5v2.5H14z M17.5 17.5H20V20h-2.5z M6.5 6.5h1 M16.5 6.5h1 M6.5 16.5h1",
  wind: "M3.5 9h10.5a2.75 2.75 0 1 0-2.7-3.3 M3.5 13h15a2.75 2.75 0 1 1-2.7 3.3 M3.5 17h7",
  gamelan: "M12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12Z M12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z M12 3v3",
  plus: "M12 5v14 M5 12h14",
  scissors: "M6.5 4.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z M6.5 14.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z M8.5 8.5 20 18 M8.5 15.5 20 6",
  brush: "M18.5 3.5 10 12l2 2 8.5-8.5a1.4 1.4 0 0 0-2-2Z M10 12c-2.5 0-4.5 1.5-4.5 4 0 1.5-1 2.5-2 3 3.5 1 8 0 8.5-5",
  ear: "M7 9.5a5 5 0 0 1 10 0c0 3-3 3.5-3 6.5a2.5 2.5 0 0 1-4.5 1.5 M10 9.5a2 2 0 0 1 4 0c0 1-1 1.5-1.5 2",
  scroll: "M7 4.5h10.5a2 2 0 0 1 2 2V8H17 M7 4.5a2 2 0 0 0-2 2V17a2.5 2.5 0 0 0 2.5 2.5H16a2 2 0 0 0 2-2V8 M9 9.5h6 M9 13h6",
  sparkline: "M3.5 16 8.5 11l3.5 3.5L20.5 6",
};

export type IconName = keyof typeof P;

export default function Icon({ name, className = "h-5 w-5", strokeWidth = 1.75 }: { name: IconName; className?: string; strokeWidth?: number }) {
  const filled = name === "play" || name === "stop" || name === "record";
  return (
    <svg
      viewBox="0 0 24 24"
      className={`shrink-0 ${className}`}
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={P[name]} />
    </svg>
  );
}
