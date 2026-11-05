# Dalang AI - Full Product & Technical Spec
Meta Global AI Developer Hackathon (Cerebral Valley) · Indie Developer track · Theme: Build for Your World
Owner: Ragil Artza Rozaksyah ("Malik"), solo. I design and direct it; AI coding tools write most of the code.
Submission deadline: Wed Nov 4, 2026, 9:00 PM ET = Thu Nov 5, 2026, 09:00 WIB

---

## 1. One-liner
Tell a story out loud, get back an animated Javanese wayang kulit short film, narrated in your own language, in about 3 minutes.

## 2. Problem & impact (Impact = 30% of score)
- Indonesian families (esp. Javanese) are losing wayang storytelling; dalang (puppet masters) are aging and performances are rare.
- Kids create stories constantly but have no way to see them; existing AI video tools are English-first and culturally generic.
- Dalang AI lets any child or parent turn a spoken story (Bahasa Indonesia, Javanese, or English) into a culturally authentic wayang film they can keep and share.
- Users: kids 5–12 with a parent, teachers running storytelling class activities, cultural communities, diaspora families.
- Must NOT be framed as an "AI education chatbot" (organizer anti-project). It is a creative, cultural storytelling and film tool. No chat interface as the core product.
- No medical, political, or war content; add content filter (see §9).

## 3. Hard hackathon requirements (all must be met)
| Requirement | How we meet it |
|---|---|
| Use Meta models (Stage 1 pass/fail) | 5+ Meta models in the core pipeline (see §5) |
| Fits a problem statement | "Build for Your World" - cultural storytelling for Indonesian families |
| New work only (built Oct 26 – Nov 4) | Fresh repo; commit history shows dates; README section "Built during the hackathon" |
| Public GitHub repo | Public repo, MIT license |
| 3-minute demo video showing only what was built | Script in §12 |
| Submit on CV platform by deadline | Checklist in §14 |
| Rights to all assets | Only model-generated assets + CC0/self-made fonts/music; list in README |

## 4. User flow (the demo must show this live)
1. Landing page: big "Ceritakan kisahmu" (Tell your story) mic button, language picker (ID / Jawa / EN), style picker (Wayang Kulit classic, Wayang Kulit colorful). 
2. Record up to 90 seconds (or upload audio). Show live waveform.
3. Progress screen with named stages, each with a thumbnail as it completes:
   Listening → Writing the lakon (script) → Casting the puppets → Painting the scenes → Bringing them to life → Narrating → Final cut.
4. Storyboard review (optional, 1 click to skip): 4–6 scene cards with image + narration line; user can tap "redo" on one scene or edit a line.
5. Player: final MP4 (16:9 and 9:16 versions), download, share link (public watch page), "Make another".
6. Gallery of public films (for community-vote prize and demo).

## 5. AI pipeline (Use of Meta AI tooling = 25%)
All calls go through one `meta_client` module. VERIFY every endpoint, model id, request/response format against current docs at dev.meta.ai (Docs: Overview, Quickstart, Model list, Cookbook, API cookbook, Muse code recipes, OSS model cookbook) before coding. Never invent endpoints.

| Stage | Model | Input → Output |
|---|---|---|
| 1. Listen | Muse Voice Transcribe | audio → transcript + detected language |
| 2. Lakon (script) | Muse Spark (API) - and a toggle to run on Muse Spark Open via Baseten (`meta-models/muse-spark-open-1026`) for the open-weights bonus | transcript → structured JSON (§6) |
| 3. Casting | Muse Image | character sheet: one canonical wayang puppet per character on plain background |
| 4. Puppet cut-out | SAM 3.1 | segment each puppet from its sheet → transparent PNG reused in every scene (character consistency) |
| 5. Scenes | Muse Image | per-scene background (kelir screen + blencong lamp glow, gunungan) + composited puppets; or image-to-image with character refs |
| 6. Animate | Muse Wonder | each scene image + motion prompt → 4–8s clip (puppet sway, shadow flicker) |
| 7. Narrate | TTS: use a Meta voice model if Model API offers one; otherwise an open-source TTS (document the choice). Narration in the story's language |
| 8. Verify (agentic) | Muse Spark vision | checks each generated scene against the script (right characters, no text artifacts, culturally appropriate); auto-regenerates failures up to 2x |
| 9. Final cut | ffmpeg | clips + narration + gamelan-style CC0 music + title card "Dalang AI" + subtitles |

"Beyond basic integration" talking points: multi-model orchestration, SAM-based character consistency, self-verifying agent loop, bilingual/Javanese narration, open-weights option.

## 6. Script JSON schema (Muse Spark structured output)
```json
{
  "title": "string",
  "language": "id|jv|en",
  "moral": "string",
  "characters": [{"id":"c1","name":"string","role":"hero|villain|helper|elder","wayang_archetype":"e.g. alus (refined) / gagah (strong) / punakawan (clown)","visual_description":"string"}],
  "scenes": [{"n":1,"setting":"string","characters":["c1"],"action":"string","narration":"1-2 sentences in story language","image_prompt":"string","motion_prompt":"string","duration_s":6}]
}
```
4–6 scenes, total narration ≤ 90 s. Validate with pydantic; retry once on invalid JSON.

## 7. Style guide (prompt constants)
Javanese wayang kulit: flat side-profile leather puppets, intricate perforated (tatahan) patterns, gold and deep red/indigo colors (sunggingan), long thin arms with control rods (cempurit), backlit cotton screen (kelir) with warm oil-lamp glow, gunungan (tree-of-life) used as scene transition. Negative: no 3D render, no anime, no text, no modern objects unless story requires.

## 8. Architecture
- Frontend: Next.js (App Router) + Tailwind, mobile-first. Deployed on Vercel (free).
- Backend: Python FastAPI worker (pipeline, ffmpeg). Deploy on Modal or Render (he has Render credits HTHON codes; Modal $100 if granted). Job queue: simple in-process background tasks + Redis optional; keep it simple: Postgres/SQLite row per job with status.
- Storage: Cloudflare R2 (he has Cloudflare) or local disk for demo; public watch URLs.
- Real-time progress: Server-Sent Events from FastAPI.
- Config via `.env`: META_API_KEY, META_API_BASE, BASETEN_API_KEY (optional), USE_OPEN_WEIGHTS=true/false, STORAGE_*, PUBLIC_BASE_URL.
- Cost guard: per-job budget counter; max 6 scenes; cache by transcript hash; DEMO_MODE replays a pre-generated film if APIs fail on stage.

## 9. Safety
- Run transcript through Muse Spark moderation prompt: block violence-graphic, sexual, political, war, medical content; friendly message to retell.
- No accounts, no child PII stored; audio deleted after transcription; films public only if user ticks "Share to gallery".

## 10. Repo layout
```
dalang-ai/
  README.md            (pitch, demo GIF, architecture diagram, "Built during the hackathon", Meta models used, setup)
  LICENSE (MIT)
  .env.example
  web/                 Next.js app
  api/                 FastAPI app
    pipeline/ listen.py lakon.py casting.py segment.py scenes.py animate.py narrate.py verify.py cut.py
    meta_client.py
    schemas.py
  assets/ music/ fonts/ (CC0 only, with sources)
  scripts/ demo_seed.py
  docs/ architecture.png, prompts.md
```

## 11. Build plan (fit around my shifts)
- Day 1: verify Meta API docs, keys, "hello world" call per model; script stage end-to-end.
- Day 2: casting + SAM cut-outs + scenes; character consistency working.
- Day 3: Muse Wonder animation + narration + ffmpeg final cut (CLI end-to-end).
- Day 4: web UI, progress SSE, player, share page, gallery.
- Day 5: verify agent loop, open-weights toggle, polish, safety, README.
- Day 6: record demo, post on X, submit. Buffer before Nov 5 09:00 WIB.
Cut list if behind: storyboard edit, gallery, 9:16 version.

## 12. 3-minute demo video script
0:00–0:15 Hook: a Semarang kid tells a 40-second story in Javanese/Bahasa.
0:15–0:35 Problem: wayang is fading; kids can't see their stories.
0:35–1:50 Live run: record → progress stages with thumbnails → final film plays (show 30 s of it).
1:50–2:30 Under the hood: diagram of 5+ Meta models, SAM consistency before/after, verify-agent regenerating a bad scene, open-weights toggle.
2:30–2:50 Impact: languages, families, teachers; gallery.
2:50–3:00 Close: "Dalang AI - every child is a dalang." Repo + link.
Only show work built during the event.

## 13. Bonus prizes targeted
Best Creative Build ($5K: Muse Image/Wonder), Most Viral on X ($20K: post demo clip, engagement until Nov 8 EOD, submit post link), Community Vote ($10K), Best Open Weight build ($10K: Muse Spark Open via Baseten).

## 14. Submission checklist
- [ ] $150 Meta Model API credits claimed + card on Meta billing + spend limit set
- [ ] Repo public, README complete, license
- [ ] Live URL works on phone
- [ ] 3-min video uploaded (YouTube unlisted/public), link accessible
- [ ] Submission text: title, tagline, description, Meta models used, what was built during event
- [ ] X post published, link submitted
- [ ] Submitted on Cerebral Valley (account ragilmalika) before Nov 5 09:00 WIB

---

## 15. v2 Winning Improvements (added 2026-10-30 06:00 WIB)

Sources re-read on 2026-10-30: the official rules text in the event waiver (judging criteria and prize
structure), the event page (tracks and themes) and the live Cerebral Valley submission form (fields).
The rules weight: **Impact 30% · Use of Meta AI tooling 25% · Demo 25% · Technical depth & execution 20%**;
Stage 1 is pass/fail on fitting a problem statement and genuinely using Meta models; the top 5 per track
go to a live final on the same rubric. Indie track: "creativity, technical ambition, and whether it works".
Prize categories: Indie track $150K / $100K / $75K / $50K / $25K; bonus prizes up to $50K total, categories
set by the organisers (the rules name a community vote and a most-viral award as examples; the form has
one opt-in, an X post link for the **Most Viral Track**). The form does not describe Best Creative Build,
Community Vote or Best Open Weight; we still build for them because they were announced to participants.
Correction kept from v1: Muse Wonder has no video output and Meta has no TTS model (dev.meta.ai, 2026-10-30).

| Criterion / prize | What judges look for | v2 feature or polish (status) | Evidence |
|---|---|---|---|
| Stage 1 gate | Fits a problem statement; really uses Meta models | "Build for Your World": Indonesian families' own culture; 6 Meta models in the core loop (done) | README model table; `docs/VERIFICATION_REPORT.md` |
| Impact 30% | Who benefits, how much, would people use it | Bahasa Indonesia, Javanese and English; works from a 90 s voice note; phone-first UI; private by default; **cultural notes** on every puppet ("Behind the puppets") so families learn real wayang tradition (done) | Screenshots; watch page; tests for privacy and sharing |
| Use of Meta AI tooling 25% | Creative, beyond basic integration, unexpected capabilities | SAM 3.1 cut-outs reused across scenes for character consistency; **Muse Spark vision checker** that sends bad pictures back with a corrected prompt (rejected images shown in the storyboard); **Muse Wonder as the dalang's hands** (multimodal keyframe choreography from the storyboard frame); Javanese via Muse Spark 1.2 audio; open-weights toggle (done) | Storyboard "checker redrew" thumbnails; `tests/test_pipeline.py`; motion JSON per scene |
| Technical depth 20% | Sound engineering, craft | Pydantic-validated schemas with one retry; per-film cost guard shared across worker threads; **parallel scene painting** (3 at once); transcript and image caches; SSE with polling fallback; stage timings; fake Meta API that mirrors documented request validation; 40+ tests, CI (lint, types, tests, web build, Docker smoke) (done) | `docs/TEST_REPORT.md`; `.github/workflows/ci.yml` |
| Demo 25% | Working, impressive, holds up live, video quality | **Standout moment**: the film opens like a real wayang show, the gunungan sweeps, a gong sounds and the dalang speaks the traditional opening *"Kocap kacarita…"* before the child's story begins; DEMO_MODE replay if the network fails; 2-3 min demo video generated from the working app with voice-over and captions (done) | `docs/demo/` video, script, storyboard, captions |
| Most Viral on X | Engagement | 9:16 export, 1200x630 share poster with title, X intent button, watch page with Open Graph tags; X post drafts (done) | `docs/SUBMISSION.md` X section |
| Community Vote | Votes from the public | Public gallery with a **"Sembah"** (Javanese bow of thanks) vote on each shared film (done) | `/gallery`, `/watch/[id]`, test `test_applause_*` |
| Best Creative Build | Creative use of Muse Image / Muse Wonder | Wayang style guide, two palettes, gunungan transitions, lamp flicker and shadows, ducked gamelan bed (done) | demo GIF, poster |
| Best Open Weight | Use of open-weight models | `USE_OPEN_WEIGHTS=true` runs the script step on Muse Spark Open (Baseten, `meta-models/muse-spark-open`); UI shows "(open weights)" (done; needs Malik's Baseten key to run live) | `scripts/check_keys.py` open-weights check |
| Accessibility | Usable by kids, parents, low-vision users | Burned-in subtitles plus a **WebVTT captions track**; `aria-live` progress; visible focus rings; `prefers-reduced-motion`; alt text on puppets; large tap targets (done) | `captions.vtt` per film; screenshots |
| Reliability | Holds up live | Retries with backoff, graceful fallbacks (SAM colour-key, rule-based motion, subtitles-only), DEMO_MODE, health check, `check_keys.py` (done) | tests for each fallback |

Out of scope for v2 (would need me or money): live hosting (configs ready, not deployed), real-key film
quality pass (one command after the key is added).
