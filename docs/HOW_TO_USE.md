# How to use Dalang AI

## For families and teachers

1. Press **Ceritakan · Tell a story**, then **pick the language** the story will be told in: Bahasa Indonesia, Basa Jawa or English. Narration and subtitles come back in the same language.
2. **Tell the story** (up to 90 seconds). Speak close to the phone. Short stories with 1 to 4 characters and a clear ending work best, for example *"Kancil wants cucumbers but the river is full of crocodiles…"*. You can also upload a recording, type the story, or tap a story starter card.
3. **Pick a style** under *Pilihan · Options*: *classic* (gold, deep red and indigo, like a real leather puppet) or *colourful* (bright, for little ones).
4. **Storyboard review** (optional): you see each scene with its narration. Change a word, or press *Redo* to repaint a scene. Press *Bring it to life* when you're happy with it. Untick the box on the first page to skip this.
5. **Watch and share**: play the film, switch between 16:9 (TV, YouTube) and 9:16 (phone, Stories, TikTok), download the MP4. Press *Bagikan ke galeri · Share to gallery* to make it public and get a link; *Sembunyikan dari galeri · Hide from gallery* hides it again. Open *Kelir Live* to perform the film yourself with its puppets.

What gets declined: stories about war, weapons, real politics, medicine, or graphic violence. Ordinary fairy-tale trouble (an ogre, a storm, a trick) is fine.

Privacy: recordings are deleted right after transcription; films are private unless you press Share.

## For whoever runs it

| Task | How |
|---|---|
| Start | `start.bat` (Windows) or `bash start.sh`; open http://localhost:3000 |
| Go live | paste `META_API_KEY` in `.env`, run `python scripts/check_keys.py`, restart |
| Free rehearsal with a key set | `FAKE_META=true` in `.env` |
| Safety net for the live demo | run `python scripts/demo_seed.py` once, set `DEMO_MODE=true` |
| Spending cap per film | `JOB_BUDGET_USD` (default 1.50) |
| Open-weights script step | `BASETEN_API_KEY=...`, `USE_OPEN_WEIGHTS=true` |
| Faster renders | `MAKE_VERTICAL=false` (skips 9:16), `VIDEO_FPS=20` |
| Public link on phone | `cloudflared tunnel --url http://localhost:3000`, then set `PUBLIC_BASE_URL` |
| Where films are | `data/jobs/<id>/dalang_landscape.mp4` and `dalang_vertical.mp4` |

## API (for developers)

| Method | Path | Body / notes |
|---|---|---|
| GET | `/api/health` | mode, models in use |
| POST | `/api/jobs` | multipart: `audio` file or `text`, `language` id/jv/en, `style` classic/colorful, `review` true/false |
| GET | `/api/jobs/{id}` | full job state |
| GET | `/api/jobs/{id}/events` | Server-Sent Events: job state on every change; ends at review/done/failed/blocked |
| POST | `/api/jobs/{id}/scenes/{n}` | JSON `{"narration": "...", "repaint": true}` (review only) |
| POST | `/api/jobs/{id}/approve` | start animation, narration and final cut |
| POST | `/api/jobs/{id}/share` | JSON `{"public": true}` |
| GET | `/api/gallery` | public films |
| GET | `/media/{id}/{file}` | images and videos |
