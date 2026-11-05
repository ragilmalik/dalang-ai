# TODO

Status legend: [x] done · [ ] open · [!] waiting on me

## Product (SPEC §4)
- [x] Home: "Ceritakan · Tell a story" opens the "Ceritakan kisahmu" mic composer, language picker ID/Jawa/EN, style picker classic/colourful
- [x] Record up to 90 s with live waveform; upload; type
- [x] Progress screen with the seven named stages and thumbnails (SSE + polling fallback)
- [x] Storyboard review: edit a line, redo a scene, approve; optional (checkbox)
- [x] Player: 16:9 and 9:16, download, share link (public watch page with OG tags), make another
- [x] Public gallery (opt-in sharing only)

## Pipeline (SPEC §5)
- [x] Listen: Muse Voice Transcribe; Javanese via Muse Spark 1.2 audio; audio deleted after
- [x] Safety screen (Muse Spark structured output)
- [x] Lakon: Muse Spark 1.3 json_schema + Pydantic validation + one retry; transcript-hash cache
- [x] Open-weights toggle: Muse Spark Open on Baseten (`USE_OPEN_WEIGHTS`)
- [x] Casting: Muse Image puppet sheets; SAM 3.1 cut-outs reused everywhere
- [x] Scenes: Muse Image backdrops + composited storyboard stills
- [x] Verify agent: Muse Spark vision, redraw up to 2x with corrected prompt
- [x] Animate: Muse Wonder keyframe motion plan per scene + kelir engine
- [x] Narrate: a voice per language picked by listening test (Kokoro-82M English when installed, edge-tts Emma Multilingual Indonesian, edge-tts Siti Javanese; see VOICES.md); subtitles-only fallback
- [x] Final cut: title card, gunungan wipes, subtitles, synthesised gamelan, 16:9 + 9:16
- [x] Cost guard per film, DEMO_MODE replay, fake Meta API when no key

## Quality
- [x] pytest suite on the fake API (unit, pipeline behaviour, full HTTP end-to-end, real-server SSE); count in TEST_REPORT.md
- [x] ruff + mypy clean; web eslint + tsc + next build clean
- [x] scripts/check_keys.py (self-test passes against the fake API)
- [!] Live run with real keys: `python scripts/check_keys.py`, then one real film (needs META_API_KEY)
- [!] Phone test on a public https URL (needs my machine + cloudflared, or a host)

## Repo, CI and deploy readiness
- [x] git repository with dated commits (not pushed)
- [x] GitHub Actions CI: ruff, mypy, pytest, key self-test; web eslint/tsc/build; Docker build + smoke test
- [x] render.yaml (backend, Docker, disk, /api/health) + web/vercel.json + click-by-click guide
- [!] Docker image built and smoke-tested locally: docker is not available in the sandbox; the CI docker job does it on first push

## Publishing (my call; see MALIK_CHECKLIST.md)
- [!] Public GitHub repo
- [x] Demo video generated from the working app (`docs/demo/dalang-ai-demo.mp4`, fake-API art)
- [!] Re-render demo video with real art: `python scripts/go_live.py` (needs key); Cerebral Valley submission, X post

## Performance
- [x] Final cut: 16:9 and 9:16 in parallel + rotated-puppet cache (148 s -> 60 s for a 65 s film on a shared 2 vCPU sandbox)

## Ten upgrades (2026-10-31)
- [x] `scripts/go_live.py`: key check -> demo film -> clips -> screenshots -> demo video -> storyboard -> kit; `--dry-run` on the fake API
- [x] MOCK sample story recording (`assets/sample-story/sample_story_synthetic.mp3`, synthetic voice) + `--audio` everywhere
- [!] Real child's recording swapped in (with consent): `python scripts/go_live.py --audio story.m4a`
- [x] Live link + QR (`PUBLIC_BASE_URL`; labelled placeholder `https://dalang-ai.example` until deployed)
- [x] Gara-gara interactive branching (pause, question, voice/tap answer, validated rewrite, re-render only new scenes)
- [x] Child's own voice as narrator (turn timestamps, recording kept only until the film is made, TTS fallback)
- [x] Muse Glimmer (open weights): documented Together AI route, safety screen + title/moral polish; [!] needs a Together key or GPU server to run live
- [x] Kotak Wayang puppet box (anonymous family id, reuse cut-outs)
- [x] Family testing kit (feedback widget, USER_TESTING.md, CULTURAL_REVIEW.md); [!] real sessions and review, mine to do
- [!] Replace the 10 PLACEHOLDER testimonials in `content/testimonials.json` with real ones (placeholder=false)
- [x] Printable puppets PDF
- [x] X launch kit (plan Nov 1-8, posts, #DalangCilik, alt text, 3 clips); [!] posting is mine to do
- [x] Submission kit script + rebuilt kit, demo video re-cut with the new features
- [x] Abandoned recordings: `runner.sweep_recordings` deletes any story.wav/upload.* older than RECORDING_TTL_HOURS (6 h) on start and on each new film; a swept film falls back to the narrator voice
- [ ] Known limit: child's-voice narration splits the child's speech turns evenly over the scenes; it does not
      align words to the rewritten narration (Muse Voice Transcribe has turn-level, not word-level, timestamps)

## Nice to have (only if time remains)
- [ ] Javanese narration voice choice (male dalang voice) when edge-tts adds one
- [x] Share poster (1200x630, first scene + title + gunungan) used for Open Graph previews
- [x] Gamelan music bed under the scenes, ducked while narration plays
- [x] README screenshots + demo GIF (scripts/screenshots.py)
- [x] Site redesign as a night wayang show (DESIGN_SYSTEM.md), every page re-shot (web/e2e/ui_shots.py)
- [x] Narrator voices chosen by a UTMOS listening test (VOICES.md); demo re-recorded on the new site
