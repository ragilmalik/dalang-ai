"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Recorder from "@/components/Recorder";
import StoryStarters, { STARTERS, starterText } from "@/components/StoryStarters";
import ShareQR from "@/components/ShareQR";
import HeroFilm from "@/components/HeroFilm";
import { TROUPE, WayangFigure } from "@/components/PipelineTheatre";
import { familyId, getReturning, listKotak, setReturning, type KotakPuppet } from "@/lib/family";
import { readDraft, readRecording, saveDraft, saveRecording } from "@/lib/draft";
import { LANGS, T, modelLabel, sendError, sendForm, type Health, type Job } from "@/lib/api";
import Bi from "@/components/ui/Bi";
import Button from "@/components/ui/Button";
import Icon, { type IconName } from "@/components/ui/Icon";
import Gunungan from "@/components/ui/Gunungan";

type Mode = "mic" | "upload" | "type";

const MODES: { key: Mode; id: string; en: string; icon: IconName }[] = [
  { key: "mic", id: "Rekam", en: "Record", icon: "mic" },
  { key: "upload", id: "Unggah", en: "Upload", icon: "upload" },
  { key: "type", id: "Ketik", en: "Type", icon: "type" },
];

const STEPS: [string, string][] = [
  ["Ceritakan", "Tell it out loud, up to 90 seconds"],
  ["Para model Meta memainkannya", "Six Meta models write, draw, cut out and move the puppets"],
  ["Tonton, simpan, mainkan sendiri", "Watch it, keep it, then perform it yourself on Kelir Live"],
];

const MAX_BYTES = 25 * 1024 * 1024; // same limit as the API (api/main.py MAX_UPLOAD)
const MAX_CHARS = 2000; // same as MAX_STORY_CHARS


export default function Home() {
  const router = useRouter();
  const [lang, setLang] = useState<"id" | "jv" | "en">("id");
  const [style, setStyle] = useState<"classic" | "colorful">("classic");
  const [review, setReview] = useState(true);
  const [gara, setGara] = useState(false);
  const [voice, setVoice] = useState<"tts" | "child">("tts");
  const [back, setBack] = useState<KotakPuppet[]>([]);
  const [mode, setMode] = useState<Mode>("mic");
  const [blob, setBlob] = useState<Blob | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [starter, setStarter] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<number | null>(null); // upload progress of a recording, in percent
  const [error, setError] = useState<string | null>(null);
  const [kept, setKept] = useState(false); // the recording came back from a film that failed (lib/draft.ts)
  const [health, setHealth] = useState<Health | null>(null);
  const composer = useRef<HTMLElement>(null);

  function startTelling() {
    setMode("mic");
    const el = composer.current;
    if (!el) return;
    const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
    el.focus({ preventScroll: true });
  }

  useEffect(() => {
    const ids = getReturning();
    if (ids.length) listKotak().then((all) => setBack(all.filter((p) => ids.includes(p.id))));
  }, []);

  useEffect(() => {
    // back from a film that failed or was stopped: the typed story is still here (lib/draft.ts)
    const d = readDraft();
    if (d) {
      Promise.resolve().then(() => {
        setText(d.text);
        setLang(d.lang);
        setMode("type");
      });
      return;
    }
    // or the recording, kept on this device, so it can be sent again without telling the story again
    let stop = false;
    readRecording().then((r) => {
      if (stop || !r) return;
      setFile(new File([r.blob], r.name, { type: r.blob.type }));
      setLang(r.lang);
      setMode("upload");
      setKept(true);
    });
    return () => {
      stop = true;
    };
  }, []);

  useEffect(() => {
    // A server that is restarting or waking up answers late: ask again a few times (2, 4, 8, 15, 15 s) before
    // saying it is not running, and clear the note by itself once it answers.
    let stop = false;
    let tries = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const check = () =>
      fetch("/api/health")
        .then((r) => {
          if (!r.ok) throw new Error(String(r.status));
          return r.json() as Promise<Health>;
        })
        .then((h) => {
          if (stop) return;
          setHealth(h);
          setError((e) => (e && e.startsWith("Server Dalang AI") ? null : e));
        })
        .catch(() => {
          if (stop) return;
          tries += 1;
          const last = tries > 5;
          setError(
            typeof navigator !== "undefined" && !navigator.onLine
              ? "Sedang offline. Sambungkan internet dulu, lalu muat ulang · You are offline. Connect to the internet, then reload."
              : last
                ? "Server Dalang AI belum menyala · the Dalang AI server is not running."
                : "Server Dalang AI belum menjawab, mencoba lagi… · The Dalang AI server is not answering yet, trying again…",
          );
          if (!last) timer = setTimeout(check, Math.min(15000, 1000 * 2 ** tries));
        });
    check();
    // back online: clear the offline note so the family can press the button again
    const online = () => {
      setError((e) => (e && e.startsWith("Sedang offline") ? null : e));
      if (tries > 5) {
        tries = 0;
        check();
      }
    };
    window.addEventListener("online", online);
    return () => {
      stop = true;
      clearTimeout(timer);
      window.removeEventListener("online", online);
    };
  }, []);

  const filePreview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => { if (filePreview) URL.revokeObjectURL(filePreview); }, [filePreview]);

  const ready =
    (mode === "mic" && !!blob) || (mode === "upload" && !!file) || (mode === "type" && text.trim().length > 15);

  function pickFile(f: File | null) {
    setError(null);
    setKept(false);
    if (f && f.size > MAX_BYTES) {
      setFile(null);
      setError(sendError(413));
      return;
    }
    if (f && !(f.type.startsWith("audio/") || f.type.startsWith("video/") || /\.(mp3|m4a|wav|webm|ogg|aac|mp4)$/i.test(f.name))) {
      setFile(null);
      setError("Pilih file suara (mp3, m4a, wav, webm) · Please choose an audio file (mp3, m4a, wav, webm).");
      return;
    }
    setFile(f);
  }

  async function submit() {
    setBusy(true);
    setError(null);
    const fd = new FormData();
    fd.append("language", lang);
    fd.append("style", style);
    fd.append("review", String(review));
    fd.append("gara_gara", String(gara));
    fd.append("narration_voice", mode === "type" ? "tts" : voice);
    if (back.length) {
      fd.append("family_id", familyId());
      fd.append("returning", back.map((p) => p.id).join(","));
    }
    if (mode === "mic" && blob) fd.append("audio", blob, blob.type.includes("mp4") ? "story.m4a" : "story.webm");
    if (mode === "upload" && file) fd.append("audio", file);
    if (mode === "type") fd.append("text", text);
    const withAudio = mode !== "type";
    setSent(withAudio ? 0 : null);
    const r = await sendForm("/api/jobs", fd, withAudio ? setSent : undefined);
    if (r.status >= 200 && r.status < 300 && typeof r.data.id === "string") {
      if (mode === "type") saveDraft({ text, lang });
      else if (mode === "mic" && blob) await saveRecording({ blob, name: blob.type.includes("mp4") ? "story.m4a" : "story.webm", lang });
      else if (mode === "upload" && file) await saveRecording({ blob: file, name: file.name, lang });
      router.push(`/film/${(r.data as unknown as Job).id}`);
      return;
    }
    setError(sendError(r.status, typeof r.data.detail === "string" ? r.data.detail : undefined));
    setBusy(false);
    setSent(null);
  }

  return (
    <div>
      {/* ---------- hero: the lamp lights the screen; one thing to press ---------- */}
      <header className="grid items-center gap-8 pb-10 pt-6 sm:pt-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:gap-14 lg:pb-16 lg:pt-16">
        <div className="space-y-6 lg:order-2">
          <HeroFilm />
        </div>
        <div className="space-y-6 lg:order-1">
          <p className="flex items-center gap-3 text-sm font-semibold text-gold">
            <span className="blencong" aria-hidden="true" />
            <span>Ceritamu jadi wayang · Your story becomes a wayang film</span>
          </p>
          <h1 className="t-hero text-fg">
            <span lang="en" className="block">
              A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film.
            </span>
          </h1>
          <p className="t-lead max-w-prose text-muted">
            Anak bercerita lantang, para model Meta memainkannya jadi film wayang kulit.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button type="button" onClick={startTelling} className="btn-gold btn-xl w-full whitespace-nowrap sm:w-auto" data-testid="hero-tell">
              <Icon name="mic" className="h-7 w-7" /> Ceritakan · Tell a story
            </button>
            <Link href="/pentas" className="btn-ghost btn-lg w-full justify-center whitespace-nowrap sm:w-auto">
              <Icon name="play" className="h-4 w-4" /> <Bi id="Tonton film" en="Watch films" />
            </Link>
          </div>
          <p className="min-h-10 text-sm text-muted">
            {health && (health.mode === "not_configured"
                ? "Server ini belum punya kunci API Meta: contoh film bisa ditonton, film baru belum bisa dibuat · No Meta key on this server yet: the sample films play, new films can't be made"
                : health.offline
                  ? "Mode uji: API Meta palsu, gambar contoh · Test mode (fake Meta API), placeholder art"
                  : `Live · ${modelLabel(health.models.lakon)}`)}
            {health?.open_weights_models && health.open_weights_models.length > 0 && (
              <span className="block">Open weights: {health.open_weights_models.map(modelLabel).join(", ")}</span>
            )}
          </p>
        </div>
      </header>

      <ol className="mb-12 grid gap-3 sm:grid-cols-3" aria-label="Cara kerjanya · How it works">
        {STEPS.map(([id, en], i) => (
          <li key={id} className="flex items-start gap-3 rounded-lg border border-gold/10 bg-surface/40 p-4">
            <span className="tabular grid h-8 w-8 shrink-0 place-items-center rounded-full border border-gold/40 font-display text-lg font-semibold text-gold">
              {i + 1}
            </span>
            <span className="text-sm">
              <span className="block font-semibold">{id}</span>
              <span lang="en" className="block text-muted">{en}</span>
            </span>
          </li>
        ))}
      </ol>

      {/* ---------- the composer ---------- */}
      <section
        ref={composer}
        id="cerita"
        tabIndex={-1}
        className="card mx-auto max-w-3xl scroll-mt-20 space-y-7 outline-none sm:p-8"
        aria-labelledby="cerita-h"
      >
        <div className="space-y-2 text-center">
          <Gunungan className="mx-auto h-10 w-8 text-gold" />
          <h2 id="cerita-h" className="t-h1">
            {T[lang].tell}
          </h2>
          <p className="text-muted">Ceritamu jadi wayang kulit · Your story becomes a wayang film</p>
        </div>

        <div className="space-y-2">
          <p className="t-small text-center font-semibold text-muted" id="lang-label">
            <Bi id="Bahasa cerita" en="Story language" />
          </p>
          <div className="flex flex-wrap justify-center gap-2" role="radiogroup" aria-label="Story language">
            {LANGS.map((l) => (
              <button
                key={l.code}
                type="button"
                onClick={() => {
                  setLang(l.code);
                  const st = STARTERS.find((x) => x.id === starter);
                  if (st) setText(starterText(st, l.code));
                }}
                className="chip"
                aria-pressed={lang === l.code}
              >
                {lang === l.code && <Icon name="check" className="h-4 w-4" strokeWidth={2.4} />}
                {l.label}
              </button>
            ))}
          </div>
        </div>

        <StoryStarters
          lang={lang}
          picked={starter}
          onPick={(st) => {
            setStarter(st.id);
            setText(starterText(st, lang));
            setMode("type");
          }}
        />

        <div className="divider-gunungan t-small font-semibold">
          <span className="text-center">
            <Bi id="atau ceritamu sendiri" en="or your own story" wrap />
          </span>
        </div>

        <div className="seg mx-auto grid max-w-md grid-cols-3" aria-label="Cara bercerita · How to tell it">
          {MODES.map((m) => (
            <button key={m.key} type="button" onClick={() => setMode(m.key)} aria-pressed={mode === m.key}>
              <Icon name={m.icon} className="h-4 w-4" />
              {m.id}
            </button>
          ))}
        </div>

        {mode === "mic" && <Recorder label={T[lang].tell} onDone={setBlob} />}
        {mode === "upload" && (
          <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-gold/30 bg-bg-2/60 p-6 text-center transition-colors duration-ketuk hover:border-gold/60">
            <Icon name="upload" className="h-8 w-8 text-gold" />
            <span className="font-semibold">
              <Bi id="Pilih rekaman" en="Choose a recording" />
            </span>
            <span className="t-small text-muted">mp3, m4a, wav, webm · maks. 25 MB</span>
            <input
              type="file"
              accept="audio/*,video/mp4"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
              className="field mt-2 max-w-sm cursor-pointer text-sm file:mr-3 file:rounded-full file:border-0 file:bg-prada file:px-3 file:py-1.5 file:font-semibold file:text-on-prada"
              aria-label="Story recording file"
            />
          </label>
        )}
        {mode === "upload" && filePreview && (
          <div className="space-y-2 text-center">
            <p className="t-small inline-flex items-center gap-2">
              <Icon name="sound" className="h-4 w-4 text-gold" /> {file?.name}
            </p>
            <audio src={filePreview} controls className="mx-auto w-full max-w-md" />
            {kept && (
              <p className="t-small text-muted" data-testid="kept-recording">
                <Bi
                  id="Rekamanmu tadi masih ada di perangkat ini, tinggal tekan Jadikan wayang lagi"
                  en="Your recording is still on this device: just press Make my wayang again"
                />
              </p>
            )}
          </div>
        )}
        {mode === "type" && (
          <div className="space-y-1">
            <textarea
              rows={6}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Dulu ada kancil yang pintar…"
              maxLength={MAX_CHARS}
              className="field leading-relaxed"
              aria-label="Tulis ceritamu · Type your story"
              aria-describedby="story-count"
            />
            <p id="story-count" className="tabular text-right text-xs text-muted" aria-live="polite">
              {text.length}/{MAX_CHARS}
            </p>
          </div>
        )}
        <p className="text-center text-sm text-muted">{T[lang].hint}</p>
        {back.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-2 text-sm" aria-label="Returning puppets">
            <span className="text-muted">↩ Kembali dari Kotak Wayang · Coming back:</span>
            {back.map((p) => (
              <button
                key={p.id}
                type="button"
                className="chip !min-h-10 !pl-1.5"
                onClick={() => {
                  const rest = back.filter((x) => x.id !== p.id);
                  setBack(rest);
                  setReturning(rest.map((x) => x.id));
                }}
                aria-label={`Do not bring back ${p.name}`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.cutout} alt="" className="h-8 w-6 object-contain" />
                {p.name} ✕
              </button>
            ))}
          </div>
        )}

        <details className="group rounded-lg border border-gold/15 bg-bg-2/40 open:bg-bg-2/60">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 font-semibold [&::-webkit-details-marker]:hidden">
            <span>
              <Bi id="Pilihan" en="Options" />
              <span className="t-small block font-normal text-muted">
                {style === "classic" ? "Klasik" : "Warna-warni"}
                {review ? ", storyboard dulu" : ""}
                {gara ? ", gara-gara" : ""}
              </span>
            </span>
            <Icon name="chevron" className="h-5 w-5 text-gold transition-transform duration-kenong group-open:rotate-180" />
          </summary>
          <div className="grid gap-3 px-4 pb-4 sm:grid-cols-2">
            <fieldset className="space-y-2 sm:col-span-2">
              <legend className="t-small mb-2 font-semibold text-muted">Gaya · Style</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {(["classic", "colorful"] as const).map((s) => (
                  <label key={s} className="option">
                    <input type="radio" name="style" checked={style === s} onChange={() => setStyle(s)} />
                    <span>{s === "classic" ? "Wayang Kulit klasik" : "Wayang Kulit warna-warni"}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="option sm:col-span-2">
              <input type="checkbox" checked={review} onChange={(e) => setReview(e.target.checked)} />
              <span>Lihat storyboard dulu · Review storyboard first</span>
            </label>
            {mode !== "type" && (
              <fieldset className="space-y-2 sm:col-span-2">
                <legend className="t-small mb-2 font-semibold text-muted">Suara narator · Narrator voice</legend>
                <div className="grid gap-2 sm:grid-cols-2">
                  <label className="option">
                    <input type="radio" name="voice" checked={voice === "tts"} onChange={() => setVoice("tts")} />
                    <span>Ki Dalang (suara komputer · computer voice)</span>
                  </label>
                  <label className="option">
                    <input type="radio" name="voice" checked={voice === "child"} onChange={() => setVoice("child")} />
                    <span>Suaraku sendiri · My own voice</span>
                  </label>
                </div>
                {voice === "child" && (
                  <p className="t-tiny text-muted">
                    Rekaman disimpan hanya sampai film selesai, lalu dihapus · The recording is kept only until the film
                    is made, then deleted.
                  </p>
                )}
              </fieldset>
            )}
            <label className="option sm:col-span-2">
              <input type="checkbox" checked={gara} onChange={(e) => setGara(e.target.checked)} />
              <span>
                <span className="font-semibold">Mode Gara-gara:</span> wayang berhenti dan bertanya, kamu yang menentukan
                kelanjutannya · Gara-gara mode: the film pauses and you choose what happens next
              </span>
            </label>
          </div>
        </details>

        <Button
          variant="primary"
          size="lg"
          className="w-full"
          disabled={!ready}
          loading={busy}
          icon="play"
          onClick={submit}
        >
          {busy ? (
            sent !== null && sent < 100 ? (
              <Bi wrap id={`Mengirim ${sent}%…`} en={`Sending ${sent}%…`} />
            ) : (
              <Bi wrap id="Mengirim…" en="Sending…" />
            )
          ) : (
            <Bi wrap id="Jadikan wayang" en="Make my wayang" />
          )}
        </Button>
        {error && (
          <div role="alert" className="space-y-3 rounded-lg border border-err/40 bg-err/10 p-4 text-center">
            <p className="text-fg">{error}</p>
            {ready && !busy && (
              <Button icon="refresh" onClick={submit}>
                Coba lagi · Try again
              </Button>
            )}
          </div>
        )}
        <p className="t-tiny text-center text-muted">
          Rekaman suara dihapus dari server setelah ditranskripsi; salinannya hanya tersimpan di perangkat ini sampai filmnya
          jadi. Film hanya tampil di galeri jika kamu memilih membagikannya. · Recordings are deleted from the server after
          transcription; a copy stays only on this device until the film is done. Films go public only if you choose to share.
        </p>
      </section>

      {/* ---------- the troupe ---------- */}
      <section className="section" aria-labelledby="troupe-h">
        <div className="mb-6 max-w-prose space-y-2">
          <h2 id="troupe-h" className="t-h1">
            <Bi stack id="Para pemain" en="The troupe" />
          </h2>
          <p className="text-muted">
            Setiap model Meta punya peran dalam pertunjukan · Every Meta model has a part in the show
          </p>
        </div>
        <ul className="kelir grid grid-cols-3 gap-x-2 gap-y-6 rounded-xl px-3 py-6 sm:grid-cols-6 sm:px-6">
          {TROUPE.map((p) => (
            <li key={p.key} className="flex flex-col items-center text-center">
              <WayangFigure hue={p.hue} active={false} prop={p.prop} />
              <span className="mt-1 text-xs font-bold">{p.model}</span>
              <span className="text-xs opacity-80">{p.name}</span>
            </li>
          ))}
        </ul>
      </section>
      <div className="mt-6">
        <ShareQR caption="Pindai untuk membuka Dalang AI di HP · Scan to open Dalang AI on a phone" />
      </div>
    </div>
  );
}
