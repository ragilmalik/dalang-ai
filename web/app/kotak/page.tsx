"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { deletePuppet, getReturning, listKotak, setReturning, type KotakPuppet } from "@/lib/family";
import Bi from "@/components/ui/Bi";
import Gunungan from "@/components/ui/Gunungan";
import Icon from "@/components/ui/Icon";
import { buttonClass } from "@/components/ui/Button";

/** Kotak Wayang: the family's own puppets, kept in this browser, ready to come back in the next story. */
export default function Kotak() {
  const [puppets, setPuppets] = useState<KotakPuppet[] | null>(null);
  const [chosen, setChosen] = useState<string[]>([]);

  useEffect(() => {
    listKotak().then((list) => {
      setPuppets(list);
      setChosen(getReturning());
    });
  }, []);

  function toggle(id: string) {
    const next = chosen.includes(id) ? chosen.filter((x) => x !== id) : [...chosen, id].slice(-3);
    setChosen(next);
    setReturning(next);
  }

  async function remove(id: string) {
    await deletePuppet(id);
    setPuppets((p) => (p ?? []).filter((x) => x.id !== id));
    const next = chosen.filter((x) => x !== id);
    setChosen(next);
    setReturning(next);
  }

  return (
    <div className="space-y-8 pt-8 sm:pt-12">
      <header className="space-y-3">
        <h1 className="t-display flex items-center gap-3">
          <Icon name="box" className="h-12 w-12 text-gold sm:h-16 sm:w-16" strokeWidth={1.4} /> Kotak Wayang
        </h1>
        <p className="t-lead max-w-prose text-muted">
          Wayang milik keluargamu, siap tampil lagi di cerita berikutnya · Your family&apos;s puppets, ready for the next
          story
        </p>
        <p className="t-small text-muted">
          Disimpan untuk browser ini saja, tanpa akun · Kept for this browser only, no account.
        </p>
      </header>
      {puppets === null && (
        <div className="grid min-h-[30vh] place-items-center" role="status">
          <div className="space-y-3 text-center">
            <Gunungan className="kayon-sway mx-auto h-14 w-10 text-gold" />
            <p className="text-muted">Memuat · Loading…</p>
          </div>
        </div>
      )}
      {puppets?.length === 0 && (
        <div className="kawung card mx-auto max-w-xl space-y-4 py-12 text-center">
          <Gunungan className="mx-auto h-16 w-12 text-gold" />
          <p className="t-h3">
            <Bi stack id="Kotak masih kosong" en="The box is empty" />
          </p>
          <p className="text-muted">
            Setelah membuat film, tekan “Simpan ke Kotak Wayang” di bawah wayangnya · After making a film, tap “Keep in
            Kotak Wayang” under a puppet.
          </p>
          <Link href="/" className={buttonClass("primary")}>
            <Icon name="mic" /> Buat cerita · Tell a story
          </Link>
        </div>
      )}
      {puppets && puppets.length > 0 && (
        <>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Puppets in the box">
            {puppets.map((p) => {
              const on = chosen.includes(p.id);
              return (
                <li
                  key={p.id}
                  className={`flex gap-4 rounded-xl border bg-surface/80 p-4 shadow-1 transition-[border-color,box-shadow] duration-kenong ${on ? "border-prada shadow-lamp" : "border-gold/15"}`}
                >
                  <span className="kelir grid h-36 w-28 shrink-0 place-items-center rounded-lg" style={{ boxShadow: "none" }}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={p.cutout} alt={`Wayang puppet of ${p.name}`} className="h-32 w-24 object-contain" />
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
                    <p className="font-display text-xl font-semibold text-gold">{p.name}</p>
                    <p className="text-muted">{p.archetype}</p>
                    {p.note && <p>{p.note}</p>}
                    <div className="mt-auto flex flex-wrap gap-2 pt-2">
                      <button type="button" className={on ? "btn-gold btn-sm" : "btn btn-sm"} aria-pressed={on} onClick={() => toggle(p.id)}>
                        {on ? "✓ Ikut cerita berikutnya" : "↩ Bawa kembali · Bring back"}
                      </button>
                      <button type="button" className="btn btn-sm !px-3" onClick={() => remove(p.id)} aria-label={`Remove ${p.name}`}>
                        <Icon name="trash" className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="space-y-2 text-center">
            <Link href="/" className={buttonClass("primary", "lg")}>
              <Icon name="mic" /> Cerita baru {chosen.length > 0 ? `dengan ${chosen.length} wayang` : ""} · New story
            </Link>
            <p className="t-small text-muted">Maks. 3 wayang kembali per cerita · Up to 3 returning puppets per story</p>
          </div>
        </>
      )}
    </div>
  );
}
