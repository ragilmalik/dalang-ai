"use client";

import { useState } from "react";
import { savePuppet } from "@/lib/family";
import Icon from "@/components/ui/Icon";

/** "Keep in Kotak Wayang": saves this film's puppet cut-out to the family's puppet box. */
export default function KeepPuppet({ jobId, charId, name }: { jobId: string; charId: string; name: string }) {
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  return (
    <button
      type="button"
      className="btn btn-sm mt-2 !min-h-9 !text-xs"
      disabled={state === "saving" || state === "saved"}
      aria-label={`Keep ${name} in Kotak Wayang`}
      onClick={async () => {
        setState("saving");
        try {
          await savePuppet(jobId, charId);
          setState("saved");
        } catch {
          setState("error");
        }
      }}
    >
      {state === "saving" ? (
        <span className="spinner h-3.5 w-3.5" aria-hidden="true" />
      ) : (
        <Icon name={state === "saved" ? "check" : state === "error" ? "refresh" : "box"} className="h-4 w-4" />
      )}
      {state === "saved" ? "Di Kotak Wayang" : state === "error" ? "Coba lagi · Retry" : "Simpan ke Kotak Wayang"}
    </button>
  );
}
