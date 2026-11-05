import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pilih jalan cerita · Vote · Dalang AI",
  robots: { index: false, follow: false },
};

export default function VoteLayout({ children }: { children: React.ReactNode }) {
  return children;
}
