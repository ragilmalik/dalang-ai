# Write-up

**Title:** Dalang AI

**Tagline:** A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film.

## Problem
Wayang kulit, Javanese shadow-puppet theatre (UNESCO Masterpiece of the Oral and Intangible Heritage
of Humanity, 2003), is how generations of Indonesian children met their stories. From what I see around me, few kids
today ever watch a live show, and they mostly meet stories through English-first, culturally generic apps. They still
make up stories every day, though, and have no way to see them.

## Solution
A phone-first web app. A child or parent records a story of up to 90 seconds in Bahasa Indonesia,
Basa Jawa or English. Dalang AI performs it as a wayang film: the gunungan sweeps, a gong sounds, the
dalang opens with "Kocap kacarita…", and the child's own characters play out their story as leather
puppets on a lamp-lit kelir, narrated and subtitled in the child's language, ending with a moral.
Parents can review a storyboard first. Each puppet comes with a short, true note on the tradition behind
it. Films are private until shared; shared films appear in a gallery where visitors give a "sembah".

Five things make it the child's own:
- **Gara-gara mode.** After scene 2 the film pauses at the gara-gara, the turning point of a real wayang
  night. A puppet asks the child a question; the child answers by voice or taps one of two suggestions; Muse
  Spark rewrites the rest of the lakon and only the new scenes are made.
- **My own voice.** The child can narrate their own film: each scene is cut from the original recording using
  Muse Voice Transcribe's speech-turn timestamps (deleted as soon as the film is made; Ki Dalang's voice is the
  fallback).
- **Kotak Wayang.** A family keeps its puppets in a puppet box (no account) and brings them back next time.
- **Off the screen.** One tap prints the puppets as an A4 PDF with cut lines and instructions for a shadow play
  with a skewer, a torch and a white sheet. A QR code on the end card brings the next family in.
- **Kelir Live.** After the film, the child performs it in the browser with the film's own puppets on a lamp-lit
  screen: drag, tilt, turn, tap the gunungan for the next scene. At the gara-gara a whole class can vote from their
  phones.

No family sessions or cultural review have happened yet, so there are no quotes here.

## How Meta models are used
See docs/SUBMISSION_FORM.md, Answer 9 (six Meta models plus two open-weight options: Muse Spark Open for
the script and Muse Glimmer for the safety screen and title/moral polish, see docs/OPEN_WEIGHTS.md). The two agentic
loops are what takes it past basic integration: the Muse Spark vision checker that sends
bad pictures back with a corrected prompt, and Muse Wonder choreographing each scene from what is
actually in the storyboard frame. SAM 3.1 cut-outs give character consistency across scenes.
Every call and every agent decision is logged per film and shown in the app ("Di balik kelir · Behind the
screen"); [docs/META_MODELS.md](META_MODELS.md) walks through the prompts, schemas, the redraw loop and a real trace.

## Tech stack
Python 3.12, FastAPI, Pydantic v2, httpx, Pillow + NumPy (kelir renderer), ffmpeg (H.264/AAC, 16:9 +
9:16), SQLite, Server-Sent Events; Next.js 16 App Router, React 19, Tailwind with my own design system (Fraunces + Plus Jakarta Sans); Kokoro-82M and edge-tts for narration
(Meta has no TTS model); pytest, ruff, mypy, ESLint, GitHub Actions; Docker, Render and Vercel configs.

## Challenges
- **No Meta video or voice model.** I checked the docs first. Muse Wonder outputs text, so it became the
  choreographer and I wrote my own renderer. Narration uses free voices that I picked with a listening test scored by UTMOS (docs/VOICES.md).
- **Javanese.** Javanese isn't among Voice Transcribe's 25 languages, so Javanese audio goes to Muse Spark 1.2
  audio understanding.
- **Character consistency.** Generating each scene from scratch changes the puppets; drawing each puppet
  once and cutting it out with SAM 3.1 keeps them identical.
- **Reliability for a live demo.** Every stage has a fallback (colour-key cut-out, rule-based motion,
  subtitles-only), a per-film budget, caches, and a DEMO_MODE replay.
- **Building without keys.** A fake Meta API that answers the same documented requests let the whole app,
  tests and this demo run before credits arrived; going live is pasting one key.

## What's next
Real family tests with the kit in docs/USER_TESTING.md and a cultural review by a dalang or sanggar
(docs/CULTURAL_REVIEW.md, not done yet); classroom mode for teachers (a class anthology); more languages
(Sundanese, Balinese) and wayang styles (wayang golek); a male dalang narration voice.

## Links
Repo: https://github.com/ragilmalik/dalang-ai · Demo video: (my YouTube link) · Live app: (once it's hosted; until then the QR in the app points at whatever address you opened it on)
