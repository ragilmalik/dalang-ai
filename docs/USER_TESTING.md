# Family testing kit

How to run a short, safe test of Dalang AI with real families, and how to record what happened. No sessions have
been run yet, so the log below is empty.

## 1. Consent note for parents (read aloud or hand over before starting)

**Bahasa Indonesia**
> Terima kasih sudah mau mencoba Dalang AI. Anak Anda akan menceritakan sebuah dongeng (maks. 90 detik) dan
> aplikasi mengubahnya menjadi film wayang kulit. Rekaman suara dihapus setelah ditranskripsi (atau, jika memilih
> "suaraku sendiri", setelah film selesai). Kami **tidak** merekam wajah anak, **tidak** mencatat nama anak, dan
> **tidak** mengambil foto. Kami hanya mencatat apa yang terjadi selama sesi dan penilaian 1-5 senyum. Film tetap
> pribadi kecuali Anda memilih membagikannya. Anda boleh berhenti kapan saja. Jika Anda bersedia kutipan Anda
> dipakai (nama depan + kota saja), centang kotak di bawah.
>
> [ ] Saya setuju anak saya ikut sesi ini.   [ ] Kutipan saya boleh dipakai (nama depan + kota).
> Tanggal: ________  Tanda tangan orang tua/wali: ______________

**English**
> Thank you for trying Dalang AI. Your child will tell a story (up to 90 seconds) and the app turns it into a
> wayang kulit film. The recording is deleted after transcription (or, with "my own voice", after the film is
> made). We do **not** film your child's face, do **not** write down your child's name and do **not** take photos.
> We only note what happens during the session and a 1-5 smiles rating. The film stays private unless you choose
> to share it. You can stop at any time. Tick the box if we may quote you (first name + city only).
>
> [ ] I agree to my child taking part.   [ ] You may quote me (first name + city).
> Date: ________  Parent/guardian signature: ______________

## 2. Session script (15 minutes, one family at a time)

| Step | Bahasa Indonesia | English | Observe |
|---|---|---|---|
| 1 | "Halo! Kamu suka dongeng apa?" | "Hi! What stories do you like?" | Warm-up; no recording yet |
| 2 | "Tekan tombol merah, lalu ceritakan dongengmu. Boleh cerita apa saja." | "Press the red button and tell your story. Any story is fine." | Does the child find the button? Hesitation? |
| 3 | (Optional) "Mau suaramu sendiri yang jadi narator?" | "Would you like your own voice to be the narrator?" | Choice of narrator voice |
| 4 | (Optional) Turn on **Gara-gara**. "Nanti wayangnya akan bertanya, kamu yang jawab ya." | "The puppet will ask you a question, and you answer." | Does the child answer by voice or tap? |
| 5 | Watch the storyboard together. "Ada yang mau diganti?" | "Anything you want to change?" | Parent edits? |
| 6 | Watch the film. Say nothing; note reactions. | | Laughs, pointing, replay requests, boredom |
| 7 | "Mau simpan wayangnya di Kotak Wayang?" / print the puppets (PDF) | "Keep the puppets in the puppet box?" / print | Interest in reuse and offline play |
| 8 | Ask the child to tap the smiles widget (1-5) under the film. | | Rating (stored without names) |
| 9 | Parent questions: "Apakah Anda akan memakainya lagi di rumah? Kenapa?" | "Would you use it again at home? Why?" | Quote (only with the box ticked) |

Rules: never ask for or write down the child's name; no photos or video of the child; the session notes describe
what happened, not who it happened to. Use the in-app widget for ratings: `GET /api/feedback/summary` returns the
counts (no comments, no names).

## 3. Session log

| # | Date | Child age band | Language | Mode (mic/upload/type) | Gara-gara | Narrator | Rating | What happened | Quote OK? |
|---|---|---|---|---|---|---|---|---|---|

Real sessions: 0 so far.

## 4. Quotes

There are no testimonials in the app. An earlier version had a testimonials section filled with sample text; it was
removed on 2026-11-05 so nothing invented can be mistaken for a real family. Quotes from real sessions (consent box
ticked, first name and city only) can go in the write-up later.
