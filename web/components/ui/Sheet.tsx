"use client";

import { useEffect, useRef, type ReactNode } from "react";
import Icon from "@/components/ui/Icon";

/**
 * Bottom sheet on phones, centred dialog on wider screens. Built on <dialog>.showModal(), so focus is trapped,
 * Escape closes it, the page behind is inert, and focus goes back to the button that opened it.
 */
export default function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      className="sheet"
      aria-labelledby="sheet-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose(); // a tap on the backdrop
      }}
    >
      <div className="rounded-t-xl border border-gold/20 bg-surface p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] shadow-2 sm:rounded-xl">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 id="sheet-title" className="t-h3">
            {title}
          </h2>
          <button type="button" className="btn-ghost !min-h-11 !px-3" onClick={onClose} aria-label="Tutup · Close">
            <Icon name="close" />
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
