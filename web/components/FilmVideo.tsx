"use client";

import { useRef, ViewTransition } from "react";
import ReadAlong from "@/components/ReadAlong";

/** A film player with its captions track and the read-along karaoke captions under it. */
/** `id`: the film id. With it, the gallery or Pentas poster you tapped morphs into this player (shared view transition). */
export default function FilmVideo({ id, src, poster, captions, lang }: { id?: string; src?: string; poster?: string; captions?: string; lang: string }) {
  const vid = useRef<HTMLVideoElement>(null);
  return (
    <div className="space-y-4">
      <ViewTransition name={id ? `film-${id}` : undefined} share="morph" default="none">
        <div className="frame">
          <video ref={vid} src={src} poster={poster} controls playsInline width={1280} height={720} className="block aspect-video w-full bg-black">
            {captions && <track kind="captions" src={captions} srcLang={lang} label="Subtitles" />}
          </video>
        </div>
      </ViewTransition>
      <ReadAlong video={vid} src={captions} lang={lang} />
    </div>
  );
}
