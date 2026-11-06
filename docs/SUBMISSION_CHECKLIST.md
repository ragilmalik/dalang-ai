# Submission checklist (Meta Global AI Developer Hackathon)

Deadline: **Nov 4, 21:00 ET = Nov 5, 2026, 09:00 WIB**. Status as of 2026-11-06, 10:00 WIB.

**The form is closed and the project was not submitted.** On Nov 6 the event page showed "Event Finished" and
"That's time! All submissions are due now.", and the participant guide says late submissions won't be considered.
The repo, video and answers below stay ready in case the organisers accept a late entry.
Legend: [x] ready in the repo · [!] needs me (account, key, money or a public post)

## Deliverables in the repo
- [x] Working app: FastAPI backend + Next.js web, live with `META_API_KEY` (preflight 6/6 PASS on Nov 5), test mode on the fake Meta API (`FAKE_META=1`)
- [x] Three sample films made with the live Meta models, shipped in `content/samples/` and loaded on first start
      (stories written for the project, labelled "contoh cerita / a sample story"); per-model results in `docs/VERIFICATION_REPORT.md`
- [x] Demo video, under 3:00 (<!-- facts:demo_length -->2:58<!-- /facts -->; exact length in `docs/demo/timeline.json`), 1920x1080 H.264/AAC, voice-over + burned-in
      captions: `docs/demo/dalang-ai-demo.mp4`, re-recorded on Nov 6 on the live Meta Model API with a Pocket TTS voice-over (synthetic, not me), -16.8 LUFS.
      Shows the voice (a synthetic sample voice, labelled), the film, the classroom vote at the gara-gara, Kelir Live, the home
      page and story starters, the pipeline theatre, Penjaga Budaya + receipt + trace, read-along, Pentas, stickers,
      printable puppets and storybook. Teasers: `teaser_60s.mp4` (16:9) and `teaser_vertical.mp4` (9:16).
      Captions `.srt`/`.vtt`, voice-over text, thumbnail, storyboard (`docs/demo/STORYBOARD.md`, `storyboard.jpg`).
      Rendered from a real browser session of the live app by `scripts/make_demo_video.py` (`work/live/demo_live.sh`).
- [x] Screenshots + GIF: every page of the current site on a phone and a desktop in `docs/screenshots/ui/after/`
      (the old design in `ui/before/`), README crops in `docs/screenshots/readme/`, plus the older
      `docs/screenshots/*.png` (Kotak Wayang, printable puppet, agent trace), demo.gif and poster.jpg
- [x] X launch kit: `docs/X_LAUNCH.md` + 3 captioned 9:16 clips in `docs/launch/` (nothing posted)
- [x] Family-testing and cultural-review kits: `docs/USER_TESTING.md`, `docs/CULTURAL_REVIEW.md` (no real sessions yet)
- [x] Submission kit: `python scripts/make_submission_kit.py` -> `../deliverables/submission-kit/` + `.zip`
- [x] Write-up: `docs/WRITEUP.md`; paste-ready form answers: `docs/SUBMISSION_FORM.md`; short kit + X drafts: `docs/SUBMISSION.md`
- [x] Architecture diagram: `docs/architecture.png`
- [x] Meta API usage verified against the docs and against the live API: `docs/VERIFICATION_REPORT.md`
- [x] Tests and CI: `pytest -q`, `ruff`, `mypy`, web `lint`/`typecheck`/`build`; `.github/workflows/ci.yml`
- [x] MIT licence, README with run instructions, `.env.example` (no keys committed)

## Only I can do these
The full, ordered list is at the end of `docs/MALIK_CHECKLIST.md`: re-record the demo on the live models, push
the repo, upload the video, optionally a real child's recording (`--audio`, with consent), a native Javanese check,
deployment, family tests + cultural review, post on X.

## Re-rendering everything with real keys
```bash
python scripts/go_live.py                 # key check, demo film, clips, screenshots, demo video, storyboard, kit
python scripts/go_live.py --dry-run       # the same on the free fake API
python scripts/go_live.py --audio story.m4a --steps seed,clips,shots,video,storyboard,kit
```

## Before pressing Submit
- [ ] Video plays without sign-in, under 3 minutes, sound on
- [ ] Repo is public and the README's first screen explains the project
- [ ] Form names all Meta models used (see `docs/SUBMISSION_FORM.md`, Answer 9)
- [ ] No `.env`, keys or children's personal data anywhere in the repo or video
- [ ] No quote, number or claim in the form that didn't really happen (no family tests yet)
