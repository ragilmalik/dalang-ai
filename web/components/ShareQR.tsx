"use client";

import { useEffect, useState } from "react";

interface ShareInfo {
  url: string;
  public: boolean;
}

/** QR code for the app (or one page of it). Before PUBLIC_BASE_URL is set it points at the address this page was
 *  opened on, so it is a real link for anyone on the same network, never a made-up one. */
export default function ShareQR({ path = "", caption }: { path?: string; caption: string }) {
  const [info, setInfo] = useState<ShareInfo | null>(null);
  useEffect(() => {
    fetch("/api/share-info")
      .then((r) => (r.ok ? r.json() : null))
      .then(setInfo)
      .catch(() => setInfo(null));
  }, []);
  if (!info) return null;
  const target = info.url + path;
  return (
    <figure className="mx-auto flex w-fit max-w-full items-center gap-4 rounded-lg border border-gold/15 bg-surface/60 p-3 pr-5 text-left">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/qr.png${path ? `?path=${encodeURIComponent(path)}` : ""}`}
        alt={`QR code linking to ${target}`}
        width={112}
        height={112}
        className="h-28 w-28 shrink-0 rounded-md bg-[#F5ECDE] p-1"
      />
      <figcaption className="min-w-0 space-y-1 text-sm">
        <span className="block font-semibold">{caption}</span>
        <span className="block break-all font-mono text-xs text-muted">{target}</span>
        {!info.public && <span className="block text-xs text-muted">Alamat server ini · This server&apos;s address</span>}
      </figcaption>
    </figure>
  );
}
