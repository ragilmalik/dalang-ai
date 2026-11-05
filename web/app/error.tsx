"use client";

import Link from "next/link";
import Gunungan from "@/components/ui/Gunungan";
import Icon from "@/components/ui/Icon";
import { buttonClass } from "@/components/ui/Button";

/** Something broke while drawing a page: the lamp went out. Try again, or go back home. */
export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl space-y-6 py-16 text-center" role="alert">
      <Gunungan className="mx-auto h-20 w-16 text-gold/70" />
      <h1 className="t-h1">Blencongnya padam sebentar</h1>
      <p className="t-lead text-muted" lang="en">
        The lamp went out for a moment: this page hit an error. Try again, or go back home.
      </p>
      <div className="flex flex-col justify-center gap-3 sm:flex-row">
        <button type="button" className={buttonClass("primary", "lg")} onClick={reset}>
          <Icon name="refresh" /> Coba lagi · Try again
        </button>
        <Link href="/" className={buttonClass("secondary", "lg")}>
          Beranda · Home
        </Link>
      </div>
    </div>
  );
}
