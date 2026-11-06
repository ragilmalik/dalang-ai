"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Gunungan from "@/components/ui/Gunungan";
import Icon, { type IconName } from "@/components/ui/Icon";
import Sheet from "@/components/ui/Sheet";
import Bi from "@/components/ui/Bi";

const NAV: { href: string; id: string; en?: string; icon: IconName }[] = [
  { href: "/pentas", id: "Pentas", en: "Showcase", icon: "stage" },
  { href: "/gallery", id: "Galeri", en: "Gallery", icon: "grid" },
  { href: "/kotak", id: "Kotak Wayang", icon: "box" },
  { href: "/guru", id: "Guru", en: "Teachers", icon: "teacher" },
  { href: "/judge", id: "Juri", en: "Judges", icon: "judge" },
];

/** Slim sticky top bar. Phones get the logo, one "tell a story" button and a menu sheet. */
export default function SiteHeader() {
  const path = usePathname() || "/";
  const [open, setOpen] = useState(false);
  const here = (href: string) => path === href || path.startsWith(`${href}/`);
  return (
    <header
      className="sticky top-0 z-40 border-b border-gold/10 bg-bg/80 backdrop-blur-md supports-[backdrop-filter]:bg-bg/65"
      style={{ viewTransitionName: "site-header" }}
    >
      <a
        href="#isi"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-full focus:bg-prada focus:px-4 focus:py-2 focus:font-semibold focus:text-on-prada"
      >
        Lewati ke isi · Skip to content
      </a>
      <nav className="mx-auto flex h-16 max-w-stage items-center gap-3 px-4 sm:px-6" aria-label="Utama · Main">
        <Link href="/" className="group mr-auto flex min-h-11 items-center gap-2.5 rounded-full py-1 pr-2" aria-label="Dalang AI, beranda · home">
          <Gunungan solid className="h-8 w-6 transition-transform duration-kenong ease-sabet group-hover:-rotate-6" />
          <span className="font-display text-xl font-semibold tracking-tight text-fg">
            Dalang <span className="text-gold">AI</span>
          </span>
        </Link>
        <ul className="hidden items-center gap-1 lg:flex">
          {NAV.map((n) => (
            <li key={n.href}>
              <Link
                href={n.href}
                aria-current={here(n.href) ? "page" : undefined}
                className={`inline-flex min-h-11 items-center rounded-full px-3.5 text-sm font-semibold transition-colors duration-ketuk ${
                  here(n.href) ? "bg-fg/10 text-fg" : "text-muted hover:bg-fg/5 hover:text-fg"
                }`}
              >
                {n.en ? <Bi id={n.id} en={n.en} /> : n.id}
              </Link>
            </li>
          ))}
        </ul>
        {path !== "/" && (
          <Link href="/#cerita" className="btn-gold btn-sm !py-0">
            <Icon name="mic" className="h-4 w-4" />
            <span>Ceritakan</span>
          </Link>
        )}
        <button
          type="button"
          className="btn-ghost !min-h-11 !px-3 lg:hidden"
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          <Icon name="menu" />
          <span className="sr-only">Menu</span>
        </button>
      </nav>
      <Sheet open={open} onClose={() => setOpen(false)} title="Menu">
        <ul className="grid gap-1">
          {NAV.map((n) => (
            <li key={n.href}>
              <Link
                href={n.href}
                onClick={() => setOpen(false)}
                aria-current={here(n.href) ? "page" : undefined}
                className={`flex min-h-12 items-center gap-3 rounded-md px-3 text-base font-semibold ${
                  here(n.href) ? "bg-fg/10 text-fg" : "text-fg hover:bg-fg/5"
                }`}
              >
                <Icon name={n.icon} className="h-5 w-5 text-gold" />
                {n.en ? <Bi id={n.id} en={n.en} /> : n.id}
              </Link>
            </li>
          ))}
        </ul>
      </Sheet>
    </header>
  );
}
