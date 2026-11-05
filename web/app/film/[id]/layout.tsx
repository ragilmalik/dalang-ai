import type { Metadata } from "next";

// A family's film page is private until they share it, so search engines are asked to leave it alone.
export const metadata: Metadata = {
  title: "Film · Dalang AI",
  robots: { index: false, follow: false },
};

export default function FilmLayout({ children }: { children: React.ReactNode }) {
  return children;
}
