import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Kotak Wayang · Your puppet box · Dalang AI",
  description: "The puppets your family kept, ready to come back in the next story.",
  robots: { index: false, follow: true },
};

export default function KotakLayout({ children }: { children: React.ReactNode }) {
  return children;
}
