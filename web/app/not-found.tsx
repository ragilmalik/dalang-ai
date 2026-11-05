import Link from "next/link";
import Gunungan from "@/components/ui/Gunungan";
import Icon from "@/components/ui/Icon";
import { buttonClass } from "@/components/ui/Button";

/** 404: an empty kelir with only the gunungan standing in the middle, the way a stage looks before the show. */
export default function NotFound() {
  return (
    <div className="mx-auto max-w-2xl space-y-8 py-12 text-center sm:py-20">
      <div className="kelir relative mx-auto grid aspect-[16/9] max-w-lg place-items-center overflow-hidden rounded-xl">
        <Gunungan className="h-40 w-32 text-on-kelir sm:h-48 sm:w-36" />
        <span className="tabular absolute bottom-3 right-4 font-display text-lg font-semibold opacity-60">404</span>
      </div>
      <div className="space-y-3">
        <h1 className="t-h1">Lakon ini tidak dimainkan malam ini</h1>
        <p className="t-lead text-muted" lang="en">
          This page is not on tonight&apos;s programme. The link may be mistyped, or the film was made private.
        </p>
      </div>
      <div className="flex flex-col justify-center gap-3 sm:flex-row">
        <Link href="/" className={buttonClass("primary", "lg")}>
          <Icon name="mic" /> Ceritakan · Tell a story
        </Link>
        <Link href="/pentas" className={buttonClass("secondary", "lg")}>
          <Icon name="stage" /> Pentas · Showcase
        </Link>
      </div>
    </div>
  );
}
