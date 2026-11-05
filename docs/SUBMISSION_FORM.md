# Cerebral Valley submission form: answers ready to paste

The form (read on 2026-10-30 05:55 WIB, not submitted) is a "Submit Project" drawer at
https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit with these fields, in this order.
**I submit it myself.** Deadline: **Wed Nov 4, 9:00 PM ET = Thu Nov 5, 09:00 WIB.** My own target is **Wed Nov 4, 18:00 WIB**, so there's a
night to fix a broken link.

| # | Field (as labelled) | Required | Type | What to enter |
|---|---|---|---|---|
| 1 | Team Name | yes | text | `Dalang AI` |
| 2 | Team Members | no | roster | Already shows me (ragilmalika). Solo, so add no one. |
| 3 | Which track are you submitting to? | yes | radio | **Indie Developer Track** |
| 4 | Which problem statement did you build towards? | yes | radio | **Build for Your World** |
| 5 | If you're competing for the Most Viral Track, please submit your X post link here | no | URL | My X post URL (post it first, see the X section of SUBMISSION.md) |
| 6 | Project Description | yes | long text | Paste **Answer 6** below |
| 7 | Public GitHub Repository | yes | URL | `https://github.com/ragilmalik/dalang-ai` (planned name; it only exists once I create and push it) |
| 8 | 3-Minute Demo Video | yes | URL (not an upload) | YouTube (unlisted is fine) or Loom link to `docs/demo/dalang-ai-demo.mp4` (under 3:00; the current cut was recorded on the fake Meta API with labelled placeholder art and is being re-recorded on the live models) |
| 9 | Describe your use of Meta products to build the submitted project | yes | long text | Paste **Answer 9** |
| 10 | Why are Meta's models important to your solution? | yes | long text | Paste **Answer 10** |
| 11 | Provide feedback from your experience using partner technologies | no | text | Only if I really used Baseten (Muse Spark Open) or Together AI (Muse Glimmer) live. Otherwise leave it empty |
| 12 | How likely are you to build with Meta Model API? | yes | radio | My honest answer |
| 13 | How would you describe your overall opinion of Meta Model API? | yes | radio | My honest answer |
| 14 | Permission checkbox (Meta and Cerebral Valley may use and promote the materials) | no | checkbox | My call; needed if I want them to feature the project |

Before pressing Submit: the repo is public and opens in a private browser window, the video link plays while logged
out, and the video is 3 minutes or less and only shows work from Oct 26-Nov 4.

---

## Answer 6: Project Description

(Based on §4b of deliverables/win-kit/SUBMISSION_REVIEW.md, reworded Nov 2, narration line updated Nov 3. About 2,800
characters; keep it under 3,000. Fill [REAL: ...] only with real facts, or delete it. If the form shows a counter or cuts text, paste the short version from SUBMISSION.md instead.)

**A child tells a story. Dalang AI performs it as wayang kulit.**

In Java, stories were passed on by the dalang, the puppet master who performs all night behind a lamp-lit screen.
Wayang is UNESCO-listed heritage (proclaimed 2003) and Javanese has about 68 million native speakers. Still, a
child today is far more likely to meet a cartoon than a wayang show, and AI video tools are English-first and
culturally generic. I live in Semarang, where wayang is still around, and I built Dalang AI so the child gets to be
the author and the dalang: they tell a story out loud, and it comes back performed in their own tradition and
language.

**How it feels.** A child records up to 90 seconds in Bahasa Indonesia, Basa Jawa or English. A few minutes later the
gunungan sweeps aside, a gong sounds and the dalang's "Kocap kacarita..." opens a 45-90 second film of *their* story:
puppets on a kelir, lamp flicker, gamelan, subtitles, 16:9 and 9:16. After scene 2 the show pauses at the gara-gara
and asks what happens next. The child answers (or the whole class votes from their phones) and the rest is rewritten
and performed. Afterwards they can perform the film by hand in Kelir Live, dragging and tilting their own puppets on a
lamp-lit screen. Their own recording can narrate the film, and the puppets leave the screen as printables, a
storybook and a WhatsApp sticker pack.

**How it works.** One film is 25-40 Meta model calls chained by an agent pipeline that checks its own work: speech to
text, a validated structured script (lakon) with characters mapped to wayang archetypes, one canonical puppet per
character cut out with SAM 3.1 and reused in every scene, backdrops painted three at a time, a vision checker that
rejects any picture that breaks the script and redraws it from its own corrected prompt, then a motion plan per scene
that my renderer performs. While it runs, the pipeline appears as a wayang troupe lit by the live agent trace.

**Trust.** Stories are screened for child safety before anything is drawn. Recordings are deleted after use. Films
stay private until the family shares them. Parents can review the storyboard, edit any line and redo a scene.

**Status.** The app runs on the live Meta Model API. The three sample films in the gallery (stories I wrote for the
project, labelled as samples) were made with it on Nov 5: 91 Meta calls, none failed, about $0.26 to $0.36 per film.
[REAL: "Tested with N families in Semarang, [date]." Only after real sessions.] Meta's API has no text-to-speech, so
narration is Kokoro-82M (English) and edge-tts, picked in a listening test.

Stack: FastAPI + Python pipeline, Pillow/NumPy kelir renderer, ffmpeg, SQLite, SSE; Next.js + Tailwind. MIT
licensed, <!-- facts:tests -->520<!-- /facts --> automated tests (<!-- facts:coverage -->96%<!-- /facts --> line coverage), full-stack e2e test, CI. README in English and Bahasa Indonesia.


## Answer 9: Describe your use of Meta products

Six Meta models (seven roles) run in the live loop, all through the Meta Model API from one client module
(`api/meta_client.py`), with every endpoint checked against dev.meta.ai:
1. Muse Voice Transcribe (`muse-voice-transcribe-1.0`): Indonesian and English stories, with language bias, wayang
   keyword hints, and speech-turn timestamps that cut the child's own voice into per-scene narration.
2. Muse Spark 1.2 audio understanding: Javanese stories (Voice Transcribe doesn't list Javanese).
3. Muse Spark 1.3 structured output (`json_schema`): the child-safety screen; the lakon (title, moral, characters
   mapped to wayang archetypes with cultural notes, 4-6 scenes with narration, backdrop, staging and motion prompts),
   parsed into Pydantic and retried once with the validation error; the Gara-gara question and the rewrite of the
   remaining scenes.
4. Muse Image (`muse-image-1.0`): one canonical puppet sheet per character, every backdrop, the gunungan.
5. SAM 3.1 (`sam-3.1`, streamed, parsed with meta-sam-parser): cuts each puppet out from a phrase the script writes,
   so the same puppet appears in every scene, in the print-out and in the next story (Kotak Wayang).
6. Muse Spark 1.3 vision as a verify agent: checks every puppet and backdrop against the script and returns
   `{passed, issues, fix_prompt}`. Failures go back to Muse Image with the checker's own prompt, up to twice.
7. Muse Wonder (`muse-wonder-1.0`): looks at each storyboard frame and returns a keyframe plan for every puppet and
   the camera. My kelir engine performs it (Wonder plans, it doesn't render video).

Every call and decision goes into an agent trace shown under each film (model, purpose, latency, retries,
rejections, cache hits, fallbacks) and served at `/api/jobs/{id}/trace`. My test film: 27 calls across four models,
about $0.18 at Meta's list prices. A per-film budget guard stops at $1.50.

Open weights (separate, not called live yet): the lakon step can run on Muse Spark Open via Baseten, and the safety
screen plus title polish on Muse Glimmer. Both are wired and tested against my fake API.

Added Nov 1 (paste if there's room): Penjaga Budaya, a cultural-review agent on Muse Spark 1.3, checks every scene and puppet against a curated rules file (gentle conflict, no politics, respect for wayang figures, character canon) and writes its fixes into the script before Muse Image draws anything. Each film also shows a character-consistency score from its SAM 3.1 cut-outs and a receipt of every Meta model, call and token used.

(If a live open-weights call works before I submit, change "not called live yet" to "called live on [date]".)

## Answer 10: Why are Meta's models important

A child's story only becomes a film if four hard things happen together, and each one maps to a Meta model. Hearing
a child in Indonesian or Javanese (Voice Transcribe, plus Muse Spark 1.2 audio for Javanese). Turning a rambling
story into a culturally coherent script the renderer can trust (Muse Spark 1.3 structured output, then my
validation). Drawing puppets that look like wayang and stay identical across scenes (Muse Image plus SAM 3.1
cut-outs, so consistency comes from segmentation, with no fine-tuning). Directing motion from what's actually in the
frame (Muse Wonder's multimodal planning). Muse Spark vision closes the loop as a checker, so the pipeline fixes its
own mistakes before a child ever sees a broken scene. One model family behind one API keeps a film at roughly
$0.15-0.30, and the open-weights Muse Spark Open route means a school or sanggar could later run the script step on
its own hardware.

## What was built during the event (if asked; also in SUBMISSION.md)

All of it, from an empty repository: the FastAPI backend and nine-stage agent pipeline; the Meta client, SAM
mask handling, verify (redraw) agent and Muse Wonder motion planner; the kelir animation engine (keyframes, lamp
flicker, shadows, gunungan transitions, captions, gamelan bed); Gara-gara branching, own-voice narration, Kotak
Wayang and the printable puppets; a fake Meta API that mirrors the documented endpoints, <!-- facts:tests -->520<!-- /facts --> tests and CI; the
Next.js app and its design system (recording, live progress, storyboard review, player, Kelir Live, classroom vote,
share cards, gallery, agent trace); the narrator voice picker; and all the
docs in English and Bahasa Indonesia. The git history starts Oct 29, 2026 UTC. No code, art or models from before the
event are in it.

Check before pasting: `git log --reverse --format=%ad --date=short | head -1` must show 2026-10-29 or later.
