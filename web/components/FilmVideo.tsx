"use client";

import { useRef } from "react";
import ReadAlong from "@/components/ReadAlong";

/** A film player with its captions track and the read-along karaoke captions under it. */
export default function FilmVideo({ src, poster, captions, lang }: { src?: string; poster?: string; captions?: string; lang: string }) {
  const vid = useRef<HTMLVideoElement>(null);
  return (
    <div className="space-y-4">
      <div className="frame">
        <video ref={vid} src={src} poster={poster} controls playsInline width={1280} height={720} className="block aspect-video w-full bg-black">
          {captions && <track kind="captions" src={captions} srcLang={lang} label="Subtitles" />}
        </video>
      </div>
      <ReadAlong video={vid} src={captions} lang={lang} />
    </div>
  );
}
