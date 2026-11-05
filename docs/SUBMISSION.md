# Submission kit

These texts started from section 4 of the submission review (deliverables/win-kit/SUBMISSION_REVIEW.md, Nov 1).
Lines marked [REAL: ...] get filled in by me with real facts only. As of Nov 5 the app runs on the live Meta Model API.

## Title
Dalang AI: a child tells a story, Meta's models perform it as wayang kulit

(Team Name field: `Dalang AI`.)

## Tagline (under 100 characters)
A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film.

## Description
Dalang AI turns a child's spoken story into a Javanese wayang kulit film. The child tells a story out loud for up to
90 seconds in Bahasa Indonesia, Basa Jawa or English. A few minutes later it comes back performed on a lamp-lit
kelir, opening with the dalang's traditional "Kocap kacarita...", narrated in the child's language (or in the child's
own voice), with gamelan and subtitles, in 16:9 and 9:16. Six Meta models run as one agent pipeline. Muse Voice
Transcribe and Muse Spark 1.2 audio listen. Muse Spark 1.3 writes the lakon as validated structured JSON. Muse Image
carves the puppets and SAM 3.1 cuts them out, so each puppet is identical in every scene. A Muse Spark vision agent
rejects and redraws bad pictures, and Muse Wonder choreographs each scene as keyframes that my kelir engine performs.
Halfway through, Gara-gara mode pauses the show and the child decides what happens next.

Long version: Answer 6 in [SUBMISSION_FORM.md](SUBMISSION_FORM.md).

No family sessions have happened yet, so there are no quotes from families anywhere in the submission.

## Meta models used
Six Meta models in the live loop (seven roles):
* Muse Voice Transcribe (`muse-voice-transcribe-1.0`): story transcription (Indonesian, English), speech-turn timestamps
* Muse Spark 1.2 (`muse-spark-1.2`): Javanese audio understanding
* Muse Spark 1.3 (`muse-spark-1.3`): structured lakon, safety screen, Penjaga Budaya cultural review, Gara-gara rewrite
* Muse Spark 1.3 vision: the verify (redraw) agent
* Muse Image (`muse-image-1.0`): puppet sheets, backdrops, gunungan
* SAM 3.1 (`sam-3.1`): puppet cut-outs for character consistency (scored per film)
* Muse Wonder (`muse-wonder-1.0`): per-scene motion planning (keyframes)

Open weights are separate and not called live yet: Muse Spark Open (Baseten) for the script step, Muse Glimmer
(Together AI or self-hosted) for the safety screen and title/moral polish. Both are wired and tested on the fake API.

Added Nov 1 (paste if there's room): **Penjaga Budaya**, a cultural-review agent on Muse Spark 1.3, checks every scene and puppet against a curated rules file (gentle conflict, no politics, respect for wayang figures, character canon) and writes its fixes into the script before Muse Image draws anything. Each film also shows a character-consistency score from its SAM 3.1 cut-outs and a receipt of every Meta model, call and token used.

Added Nov 2 (paste if there's room): after the film, the child performs it in **Kelir Live**, dragging and tilting the film's own puppets on a lamp-lit kelir. At the gara-gara a **whole class can vote** from their phones. A **Dalang Director** agent on Muse Spark 1.3 plans camera moves, entrances, gunungan transitions and gamelan cues. **Remix** re-tells the film in another language or from the villain's side with the same puppets, and every film comes with a WhatsApp **sticker pack** made from its SAM 3.1 cut-outs. The gamelan score, aksara Jawa title, stickers and Kelir Live are my own code, not Meta models.

Added Nov 2, later (paste if there's room): I redesigned the whole site as a night wayang show (night indigo, a lit
cream kelir for whatever matters, gold buttons, Fraunces and Plus Jakarta Sans, bilingual headings, 0 axe violations
on <!-- facts:a11y -->22<!-- /facts --> page checks), and I picked new narrator voices with a listening test scored by UTMOS: Kokoro-82M
for English (3.89 to 4.52) and edge-tts Emma Multilingual for Indonesian (3.73 to 4.32). Narration isn't a Meta model;
Meta's Model API has no text-to-speech.

## What was built during the event (Oct 26 - Nov 4, 2026)
All of it, starting from an empty repository: the FastAPI backend and nine-stage agent pipeline; the Meta client, SAM
mask handling, verify (redraw) agent and Muse Wonder motion planner; the kelir animation engine (keyframes, lamp
flicker, shadows, gunungan transitions, captions, gamelan bed); the narrator voice picker; Gara-gara branching, own-voice narration, Kotak
Wayang and the printable puppets; a fake Meta API that mirrors the documented endpoints, <!-- facts:tests -->520<!-- /facts --> tests and CI; the
Next.js app and its design system (recording, live progress as a pipeline theatre, storyboard review, player, Kelir Live, classroom vote,
remix, share cards, stickers, /pentas, gallery, agent trace); and all the docs in English and Bahasa Indonesia. The
git history starts Oct 29, 2026 UTC (Oct 30, 05:01 WIB). No code, art or models from before the event are in it.

## Links
* Repo: filled in after pushing
* Live app: not deployed yet (filled in after deploying)
* Demo video: filled in after the live re-record is uploaded

---

# X post drafts (for Most Viral on X)

The launch kit is in `docs/X_LAUNCH.md`: a day-by-day plan for Nov 1-8, three post variants with replies, the
#DalangCilik challenge in Bahasa and English, alt text, and three captioned 9:16 clips in `docs/launch/`.
Nothing has been posted.
