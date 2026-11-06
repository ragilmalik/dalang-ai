import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "./globals.css";
import ServiceWorker from "@/components/ServiceWorker";
import SiteHeader from "@/components/SiteHeader";
import ThemeToggle, { THEME_SCRIPT } from "@/components/ThemeToggle";
import Gunungan from "@/components/ui/Gunungan";
import { ToastProvider } from "@/components/ui/Toast";

// Both fonts are SIL OFL 1.1 (app/fonts/OFL-*.txt), bundled so the build works offline. Latin subset only.
const display = localFont({
  src: "./fonts/Fraunces-SOFT100-opsz-wght500-700.latin.woff2",
  variable: "--font-display",
  weight: "500 700",
  display: "swap",
  adjustFontFallback: "Times New Roman",
});
const text = localFont({
  src: "./fonts/PlusJakartaSans-wght300-800.latin.woff2",
  variable: "--font-text",
  weight: "300 800",
  display: "swap",
  adjustFontFallback: "Arial",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.PUBLIC_BASE_URL || "http://localhost:3000"),
  title: "Dalang AI · Ceritamu jadi wayang",
  description: "A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film.",
  applicationName: "Dalang AI",
  // the share card itself is app/opengraph-image.png + app/twitter-image.png (scripts/make_web_assets.py)
  openGraph: {
    type: "website",
    siteName: "Dalang AI",
    title: "Dalang AI · Ceritamu jadi wayang · Your story becomes a wayang film",
    description: "A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film. In Bahasa Indonesia, Javanese or English.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Dalang AI · Your story becomes a wayang film",
    description: "A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film.",
  },
  appleWebApp: { capable: true, title: "Dalang AI", statusBarStyle: "black-translucent" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0C0A1E",
};

const FOOT: [string, string][] = [
  ["/", "Ceritakan · Tell a story"],
  ["/pentas", "Pentas · Showcase"],
  ["/gallery", "Galeri · Gallery"],
  ["/kotak", "Kotak Wayang"],
  ["/guru", "Guru · Teachers"],
  ["/judge", "Juri · Judges"],
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className={`${display.variable} ${text.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <ToastProvider>
          <SiteHeader />
          <ServiceWorker />
          <main id="isi" tabIndex={-1} className="mx-auto min-h-[calc(100svh-4rem)] max-w-stage px-4 pb-20 outline-none sm:px-6">
            {children}
          </main>
          <footer className="kawung border-t border-gold/10">
            <div className="mx-auto grid max-w-stage gap-8 px-4 py-12 sm:px-6 md:grid-cols-[1.4fr_1fr]">
              <div className="space-y-3">
                <p className="flex items-center gap-2.5 font-display text-2xl font-semibold">
                  <Gunungan solid className="h-9 w-7" />
                  Dalang AI
                </p>
                <p className="max-w-prose text-muted">
                  Saya membuatnya sendiri di Semarang, supaya anak-anak bisa melihat cerita mereka sendiri di kelir. ·{" "}
                  <span lang="en">I built it solo in Semarang so kids can see their own stories on the kelir.</span>
                </p>
                <p className="t-tiny text-muted">
                  Built for the Meta Global AI Developer Hackathon · Muse Voice Transcribe · Muse Spark · Muse Image · SAM
                  3.1 · Muse Wonder
                </p>
                <p className="t-tiny text-muted">
                  Gamelan in the films: court musicians of the Kraton Ngayogyakarta, recorded by{" "}
                  <a
                    href="https://freesound.org/people/RTB45/sounds/255544/"
                    className="underline decoration-gold/40 underline-offset-2 hover:text-fg"
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    RTB45
                  </a>
                  ,{" "}
                  <a
                    href="https://creativecommons.org/licenses/by/4.0/"
                    className="underline decoration-gold/40 underline-offset-2 hover:text-fg"
                    rel="noopener noreferrer license"
                    target="_blank"
                  >
                    CC BY 4.0
                  </a>
                  . Narration voices are synthetic.
                </p>
              </div>
              <div className="flex flex-col items-start gap-4 md:items-end">
                <ul className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
                  {FOOT.map(([href, label]) => (
                    <li key={href}>
                      <Link href={href} className="inline-flex min-h-11 items-center text-muted hover:text-fg">
                        {label}
                      </Link>
                    </li>
                  ))}
                </ul>
                <ThemeToggle />
              </div>
            </div>
          </footer>
        </ToastProvider>
      </body>
    </html>
  );
}
