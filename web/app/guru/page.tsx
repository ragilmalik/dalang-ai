import type { Metadata } from "next";
import Link from "next/link";
import Bi from "@/components/ui/Bi";
import Icon from "@/components/ui/Icon";
import { buttonClass } from "@/components/ui/Button";

export const metadata: Metadata = {
  title: "Dalang AI · Untuk guru · For teachers: a 30-minute wayang session",
  description: "How to run a 30-minute class where children tell a story and see it performed as wayang kulit.",
};

const PLAN: { min: string; id: string; en: string }[] = [
  { min: "0-5", id: "Pembuka: tunjukkan satu film contoh dari Galeri. Tanya: siapa pernah menonton wayang?",
    en: "Opening: play one sample film from the Gallery. Ask: who has seen a wayang show?" },
  { min: "5-10", id: "Kenalan wayang: gunungan, kelir, blencong (lampu), dalang. Tunjukkan catatan budaya di bawah tiap wayang.",
    en: "Meet wayang: the gunungan, the kelir (screen), the blencong (lamp), the dalang. Show the cultural note under each puppet." },
  { min: "10-18", id: "Bercerita: kelompok 3-4 anak memilih Story Starter atau mengarang sendiri, lalu satu anak bercerita ke HP (maks. 90 detik). Aktifkan Gara-gara agar kelas memilih lanjutannya.",
    en: "Tell: groups of 3-4 pick a Story Starter or invent one; one child tells it into the phone (max 90 s). Turn on Gara-gara so the class chooses what happens next." },
  { min: "18-24", id: "Tonton bersama dengan Baca bersama (kata disorot). Anak membaca keras mengikuti sorotan.",
    en: "Watch together with Read along on (words light up). Children read aloud with the highlight." },
  { min: "24-30", id: "Lepas layar: cetak wayang (A4) dan buku cerita (A5), gunting dengan pendampingan, main bayangan dengan senter dan kain.",
    en: "Off the screen: print the puppets (A4) and the storybook (A5), cut out with an adult, play shadows with a torch and a sheet." },
];

export default function Guru() {
  return (
    <div className="mx-auto max-w-4xl space-y-8 pt-8 sm:pt-12">
      <header className="space-y-3">
        <h1 className="t-display">
          <Bi stack id="Untuk guru" en="For teachers" />
        </h1>
        <p className="t-lead max-w-prose text-muted">
          Sesi wayang 30 menit · A 30-minute wayang session (ages 5-12, one phone or laptop, a projector if you have one)
        </p>
      </header>
      <section className="card" aria-labelledby="rencana">
        <h2 id="rencana" className="t-h2">
          <Bi stack id="Rencana" en="Plan" />
        </h2>
        <ol className="mt-6 space-y-0">
          {PLAN.map((p, i) => (
            <li key={p.min} className="relative flex gap-4 pb-6 last:pb-0">
              {i < PLAN.length - 1 && <span aria-hidden="true" className="absolute left-[2.1rem] top-10 h-[calc(100%-2.5rem)] w-px bg-gold/20" />}
              <span className="tabular grid h-10 w-[4.25rem] shrink-0 place-items-center rounded-full border border-gold/40 bg-bg-2 text-sm font-bold text-gold">
                {p.min}′
              </span>
              <span className="pt-1.5">
                <span className="block font-semibold" lang="id">{p.id}</span>
                <span className="mt-1 block text-sm text-muted" lang="en">{p.en}</span>
              </span>
            </li>
          ))}
        </ol>
      </section>
      <div className="grid gap-6 md:grid-cols-2">
        <section className="card space-y-3 text-sm" aria-labelledby="siapkan">
          <h2 id="siapkan" className="t-h3 flex items-start gap-2">
            <Icon name="scissors" className="mt-0.5 h-5 w-5 text-gold" /> <Bi stack id="Siapkan" en="Prepare" />
          </h2>
          <ul className="space-y-2">
            <li className="flex gap-2"><Icon name="check" className="mt-0.5 h-4 w-4 text-gold" /><span>Kertas tebal, gunting, selotip, tusuk sate (tumpulkan), senter, kain putih · Thick paper, scissors, tape, blunted skewers, a torch, a white sheet.</span></li>
            <li className="flex gap-2"><Icon name="check" className="mt-0.5 h-4 w-4 text-gold" /><span>Izin orang tua bila suara anak direkam; rekaman dihapus setelah film jadi · Parents&apos; consent for recording; recordings are deleted once the film is made.</span></li>
            <li className="flex gap-2"><Icon name="check" className="mt-0.5 h-4 w-4 text-gold" /><span>Film tetap pribadi sampai Anda membagikannya · Films stay private until you share them.</span></li>
          </ul>
        </section>
        <section className="card space-y-3 text-sm" aria-labelledby="catatan">
          <h2 id="catatan" className="t-h3 flex items-start gap-2">
            <Icon name="shield" className="mt-0.5 h-5 w-5 text-gold" /> <Bi stack id="Catatan budaya" en="Cultural care" />
          </h2>
          <p>
            Setiap cerita diperiksa Penjaga Budaya (aturan budaya yang kami kurasi, belum ditinjau dalang). Ajak anak
            bertanya ke orang tua atau sanggar setempat · Every story is checked by Penjaga Budaya (cultural rules we
            curated, not yet reviewed by a dalang). Encourage children to ask parents or a local sanggar.
          </p>
        </section>
      </div>
      <p className="text-center">
        <Link href="/" className={buttonClass("primary", "lg")}>
          <Icon name="mic" /> Mulai · Start
        </Link>
      </p>
    </div>
  );
}
