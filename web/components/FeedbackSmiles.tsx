"use client";

import { useState } from "react";
import Bi from "@/components/ui/Bi";

const FACES = ["😢", "🙁", "😐", "🙂", "😄"];

/** Family-testing widget: 1-5 smiles and an optional comment. No names or contact details. */
export default function FeedbackSmiles({ jobId, page }: { jobId: string; page: "film" | "watch" }) {
  const key = `feedback:${page}:${jobId}`;
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(() => typeof window !== "undefined" && localStorage.getItem(key) === "1");
  const [error, setError] = useState(false);

  async function send() {
    const r = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, rating, comment, page }),
    }).catch(() => null);
    if (r?.ok) {
      setSent(true);
      localStorage.setItem(key, "1");
    } else setError(true);
  }

  if (sent) return <p className="text-center text-sm text-muted" role="status">Terima kasih! · Thank you for the feedback!</p>;
  return (
    <section className="card space-y-2 text-center" aria-labelledby={`fb-${page}`}>
      <h3 id={`fb-${page}`} className="t-h3">
        <Bi stack id="Suka filmnya?" en="Did you like the film?" />
      </h3>
      <div className="flex justify-center gap-1 sm:gap-2" role="radiogroup" aria-label="Rating, 1 to 5 smiles">
        {FACES.map((f, i) => (
          <button
            key={f}
            type="button"
            role="radio"
            aria-checked={rating === i + 1}
            aria-label={`${i + 1} of 5`}
            onClick={() => setRating(i + 1)}
            className={`grid h-14 w-14 place-items-center rounded-full text-3xl transition-[transform,background-color,opacity] duration-kenong ease-sabet active:scale-90 ${rating === i + 1 ? "scale-110 bg-prada/30 ring-2 ring-prada" : "opacity-75 hover:opacity-100"}`}
          >
            <span className="emoji" aria-hidden="true">
              {f}
            </span>
          </button>
        ))}
      </div>
      {rating > 0 && (
        <>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value.slice(0, 300))}
            rows={2}
            placeholder="Ceritakan sedikit (opsional, tanpa nama) · A few words (optional, no names)"
            aria-label="Optional comment"
            className="field text-sm"
          />
          <button type="button" className="btn-gold" onClick={send}>
            Kirim · Send
          </button>
        </>
      )}
      {error && <p role="alert" className="text-sm text-err">Belum terkirim, coba lagi · Not sent, try again.</p>}
    </section>
  );
}
