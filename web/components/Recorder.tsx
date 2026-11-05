"use client";

import { useEffect, useRef, useState } from "react";
import Icon from "@/components/ui/Icon";

const MAX_SECONDS = 90;

function clock(s: number): string {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** What went wrong with the microphone, in words a parent can act on. */
export function micProblem(e: unknown): string {
  const name = (e as { name?: string } | null)?.name || "";
  if (name === "NotAllowedError" || name === "SecurityError")
    return "Izin mikrofon ditolak. Ketuk ikon gembok di samping alamat situs, izinkan Mikrofon, lalu coba lagi. Bisa juga pakai Unggah atau Ketik. · The microphone is blocked. Tap the lock icon next to the address, allow Microphone, then try again. Or use Upload or Type.";
  if (name === "NotFoundError" || name === "OverconstrainedError")
    return "Mikrofon tidak ditemukan di perangkat ini. Pakai Unggah atau Ketik, ya. · No microphone was found on this device. Use Upload or Type instead.";
  if (name === "NotReadableError" || name === "AbortError")
    return "Mikrofon sedang dipakai aplikasi lain. Tutup aplikasi itu lalu coba lagi. · Another app is using the microphone. Close it and try again.";
  if (name === "insecure")
    return "Browser hanya mengizinkan mikrofon di alamat https. Pakai Unggah atau Ketik, ya. · The browser only allows the microphone on an https address. Use Upload or Type instead.";
  if (name === "unsupported")
    return "Browser ini belum bisa merekam suara. Coba Chrome atau Safari terbaru, atau pakai Unggah atau Ketik. · This browser can't record sound yet. Try a recent Chrome or Safari, or use Upload or Type.";
  return "Mikrofon belum bisa dipakai. Coba lagi, atau pakai Unggah atau Ketik. · The microphone isn't working right now. Try again, or use Upload or Type.";
}

const MIN_SECONDS = 3;

/** Mic recorder with a live waveform, capped at 90 seconds (spec §4.2). */
export default function Recorder({ label, onDone }: { label: string; onDone: (b: Blob | null) => void }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const raf = useRef<number>(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const live = useRef<{ stream: MediaStream; ctx: AudioContext } | null>(null);

  // leaving the page while recording turns the microphone off (the red dot in the tab goes away)
  useEffect(
    () => () => {
      cancelAnimationFrame(raf.current);
      if (timer.current) clearInterval(timer.current);
      if (rec.current && rec.current.state !== "inactive") {
        rec.current.onstop = null;
        rec.current.stop();
      }
      live.current?.stream.getTracks().forEach((t) => t.stop());
      void live.current?.ctx.close().catch(() => {});
    },
    [],
  );

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  async function start() {
    setError(null);
    if (typeof window !== "undefined" && !window.isSecureContext) return setError(micProblem({ name: "insecure" }));
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined")
      return setError(micProblem({ name: "unsupported" }));
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      const ctx = new AudioContext();
      live.current = { stream, ctx };
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const data = new Uint8Array(analyser.fftSize);
      const draw = () => {
        const c = canvas.current;
        if (c) {
          const g = c.getContext("2d")!;
          analyser.getByteTimeDomainData(data);
          g.clearRect(0, 0, c.width, c.height);
          // mirrored bars, like the shadow of the voice on the screen
          const bars = 48;
          const step = Math.floor(data.length / bars);
          const w = c.width / bars;
          g.fillStyle = "#ECBA54";
          for (let i = 0; i < bars; i++) {
            let peak = 0;
            for (let k = 0; k < step; k++) peak = Math.max(peak, Math.abs(data[i * step + k] - 128));
            const h = Math.max(4, (peak / 128) * c.height * 1.6);
            g.globalAlpha = 0.45 + Math.min(0.55, peak / 90);
            g.beginPath();
            g.roundRect(i * w + w * 0.2, (c.height - h) / 2, w * 0.6, Math.min(c.height, h), w * 0.3);
            g.fill();
          }
        }
        raf.current = requestAnimationFrame(draw);
      };
      draw();

      const chunks: BlobPart[] = [];
      const t0 = Date.now();
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = (e) => chunks.push(e.data);
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        cancelAnimationFrame(raf.current);
        void ctx.close();
        if (timer.current) clearInterval(timer.current);
        live.current = null;
        setRecording(false);
        const blob = new Blob(chunks, { type: mr.mimeType || "audio/webm" });
        if ((Date.now() - t0) / 1000 < MIN_SECONDS || blob.size < 1000) {
          setError("Rekamannya pendek sekali. Tekan tombolnya, ceritakan, lalu tekan Selesai. · That was very short. Press the button, tell the story, then press Stop.");
          onDone(null);
          return;
        }
        setPreview(URL.createObjectURL(blob));
        onDone(blob);
      };
      rec.current = mr;
      mr.start();
      setRecording(true);
      setPreview(null);
      onDone(null);
      setSeconds(0);
      timer.current = setInterval(() => {
        const s = Math.floor((Date.now() - t0) / 1000);
        setSeconds(s);
        if (s >= MAX_SECONDS) mr.stop();
      }, 250);
    } catch (e) {
      live.current?.stream.getTracks().forEach((t) => t.stop());
      void live.current?.ctx.close().catch(() => {});
      live.current = null;
      cancelAnimationFrame(raf.current);
      setError(micProblem(e));
    }
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative grid place-items-center">
        {/* the lamp halo behind the button */}
        <span
          aria-hidden="true"
          className={`pointer-events-none absolute h-56 w-56 rounded-full bg-[radial-gradient(circle,rgb(255_196_100/.35),transparent_65%)] transition-opacity duration-gong ${recording ? "opacity-100" : "opacity-60"}`}
        />
        <button
          type="button"
          onClick={() => (recording ? rec.current?.stop() : start())}
          className={`relative flex h-44 w-44 flex-col items-center justify-center gap-1 rounded-full text-center font-semibold transition-[transform,background-color] duration-ketuk ease-sabet active:scale-95 ${
            recording
              ? "pulse-rec bg-sindur text-white shadow-[0_6px_0_0_#84261a]"
              : "bg-prada text-on-prada shadow-[0_6px_0_0_#a8741f,0_20px_50px_-12px_rgb(236_186_84/.7)] hover:bg-prada-hi"
          }`}
          aria-label={recording ? "Stop recording" : label}
        >
          <Icon name={recording ? "stop" : "mic"} className="h-12 w-12" strokeWidth={1.6} />
          <span className="px-4 text-sm leading-tight">{recording ? "Selesai · Stop" : label}</span>
        </button>
      </div>
      {recording && <canvas ref={canvas} width={600} height={80} aria-hidden="true" className="h-14 w-full max-w-md" />}
      <p className={`tabular min-h-5 text-sm ${recording ? "text-fg" : "text-muted"}`} aria-live="off">
        {recording ? (
          <>
            <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-sindur align-middle" aria-hidden="true" />
            {clock(seconds)} / 1:30
          </>
        ) : preview ? (
          "Dengarkan lagi, atau rekam ulang · Listen back, or record again"
        ) : null}
      </p>
      {preview && <audio src={preview} controls className="w-full max-w-md" />}
      {error && (
        <p role="alert" className="max-w-md text-center text-sm text-err">
          {error}
        </p>
      )}
    </div>
  );
}
