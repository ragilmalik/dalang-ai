"use client";

import { useState } from "react";
import Recorder from "@/components/Recorder";
import Icon from "@/components/ui/Icon";
import type { Job } from "@/lib/api";

/** Gara-gara: part one of the film plays, a puppet asks what happens next, the child taps or says the answer. */
export default function GaraGaraChoice({ job, onSent }: { job: Job; onSent: (j: Job) => void }) {
  const g = job.gara_gara;
  const [voice, setVoice] = useState<Blob | null>(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!g?.question) return null;

  async function send(answer: { text?: string; audio?: Blob }) {
    setBusy(true);
    setError(null);
    const fd = new FormData();
    if (answer.text) fd.append("text", answer.text);
    if (answer.audio) fd.append("audio", answer.audio, answer.audio.type.includes("mp4") ? "answer.m4a" : "answer.webm");
    try {
      const r = await fetch(`/api/jobs/${job.id}/choice`, { method: "POST", body: fd });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      onSent((await r.json()) as Job);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <section className="card space-y-5" aria-labelledby="gara-title">
      <h2 id="gara-title" className="t-h1 flex items-center justify-center gap-3 text-center text-gold">
        <Icon name="wind" className="h-9 w-9" /> Gara-gara!
      </h2>
      {job.part1 && (
        <div className="frame">
          <video src={job.part1} controls autoPlay playsInline className="block aspect-video w-full bg-black" />
        </div>
      )}
      <div className="flex items-end gap-3 sm:gap-4">
        {g.speaker_cutout && (
          <span className="kelir grid h-32 w-24 shrink-0 place-items-center rounded-lg" style={{ boxShadow: "none" }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={g.speaker_cutout} alt={`Wayang puppet of ${g.speaker_name}`} className="h-28 w-20 object-contain" />
          </span>
        )}
        {/* speech bubble, tail pointing at the puppet */}
        <div className="relative flex-1 rounded-xl rounded-bl-sm bg-kelir p-4 text-on-kelir shadow-lamp sm:p-5">
          <p className="text-sm font-bold">{g.speaker_name}:</p>
          <p className="font-display text-xl font-medium leading-snug sm:text-2xl">{g.question}</p>
          {g.question_audio && <audio src={g.question_audio} controls className="mt-3 w-full" />}
        </div>
      </div>
      {job.message && <p className="text-center text-gold">{job.message}</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        {(g.options ?? []).map((o, i) => (
          <button key={o} type="button" className="btn-gold btn-lg min-h-20 text-lg" disabled={busy} onClick={() => send({ text: o })}>
            <span aria-hidden="true" className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-on-prada/15 font-display">
              {i === 0 ? "A" : "B"}
            </span>
            {o}
          </button>
        ))}
      </div>
      <div className="space-y-4 rounded-lg border border-gold/15 bg-bg-2/60 p-4">
        <p className="text-center text-sm font-semibold text-muted">Atau jawab dengan suaramu · Or say your own answer</p>
        <Recorder label="Jawab · Answer" onDone={setVoice} />
        <button type="button" className="btn w-full" disabled={!voice || busy} onClick={() => voice && send({ audio: voice })}>
          <Icon name="mic" /> Kirim jawaban suara · Send my voice answer
        </button>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="…atau ketik · …or type"
            aria-label="Type your own answer"
            className="field min-w-0 flex-1"
          />
          <button type="button" className="btn shrink-0" disabled={busy || typed.trim().length < 2} onClick={() => send({ text: typed })}>
            Kirim · Send
          </button>
        </div>
      </div>
      {busy && (
        <p className="flex items-center justify-center gap-2 text-center text-sm text-muted" role="status">
          <span className="spinner" aria-hidden="true" /> Ki Dalang sedang menulis ulang cerita · rewriting the story…
        </p>
      )}
      {error && (
        <p role="alert" className="text-center text-err">
          {error}
        </p>
      )}
    </section>
  );
}
