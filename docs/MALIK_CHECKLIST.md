# My checklist (things only I can do)

Status on Nov 6, 2026, 03:00 WIB. The app runs on the live Meta Model API (preflight 6/6 PASS, per-model results in
`docs/VERIFICATION_REPORT.md`). The three sample films in the gallery, the home page loop, the share poster, the
README gif, the demo video, its teasers, the launch clips, the thumbnail and every screenshot were made with the live
models. What is still not real, and why:
- the demo's narrator: a synthetic voice (Kokoro-82M `af_heart`), not me. My own voice-over can replace it any time
  (`docs/demo/real/README.md`)
- the story recording in the demo (`assets/sample-story/sample_story_synthetic.mp3`): a synthetic voice, labelled
  as one -> step 4 if I get a real recording with a parent's consent
- no live link or QR yet: the app isn't deployed -> deploying, below
- no family tests and no cultural review yet (`docs/USER_TESTING.md` says "Real sessions: 0") -> later

Deployment details come first; **the list that ends this file is everything left for you.**

## Deploying online (only after you say yes; may cost about $7/month on Render)

The app has two parts: the **backend** (Python, makes the films) and the **website** (what people open).
Blueprints are ready in the repo: `render.yaml` (backend) and `web/vercel.json` (website).

### Backend on Render
1. Go to https://render.com and sign in with GitHub (the repo must be pushed first).
2. Click **New +** (top right) → **Blueprint**.
3. Pick the **dalang-ai** repository → Render reads `render.yaml` and shows one service, `dalang-ai-api`, with a 5 GB disk.
4. It asks for the secret values: paste your Meta key into **META_API_KEY**; leave BASETEN_API_KEY empty unless you use open weights; leave PUBLIC_BASE_URL empty for now.
5. Click **Apply**. The plan is **Starter** (the disk needs a paid plan, about $7 a month); confirm only if you agree to the cost.
6. (Optional) The narrator is edge-tts out of the box. If you want the Kokoro English voice online too, follow
   [GO_LIVE.md, "Narrator voice when deployed"](GO_LIVE.md#narrator-voice-when-deployed-optional-kokoro) before Apply.
7. Wait until the service shows **Live** (5-10 minutes). Copy its address, e.g. `https://dalang-ai-api.onrender.com`. Open `<address>/api/health`: you should see `"ok": true` and `"fake_meta": false`.

### Website on Vercel
1. Go to https://vercel.com and sign in with GitHub.
2. Click **Add New…** → **Project** → **Import** the dalang-ai repository.
3. Set **Root Directory** to `web` (click Edit next to it).
4. Open **Environment Variables** and add `API_ORIGIN` = the Render address from step 7 (no slash at the end). Add `PUBLIC_BASE_URL` = the address Vercel will give you (you can add it after the first deploy and redeploy).
5. Click **Deploy**. When it finishes, open the `https://….vercel.app` address on your phone; the microphone works because it is https.
6. Back in Render, set `PUBLIC_BASE_URL` to the Vercel address and click **Save, rebuild and deploy**.
7. Put the same `PUBLIC_BASE_URL=` in your local `.env`, then run `python scripts/make_qr.py` (README QR) and
   `python scripts/go_live.py --steps seed,shots,video,storyboard,kit` so the film end cards, the demo video's
   close shot and the kit carry the real QR. Until `PUBLIC_BASE_URL` is set there is no QR in the repo, and the site
   uses the visitor's own address for it.

Important: `API_ORIGIN` is read when Vercel **builds** the site. If you change it, click **Redeploy** in Vercel.

Free alternative (no accounts, no cost): run `start.bat` on your laptop and `cloudflared tunnel --url http://localhost:3000`; the printed https address works on any phone while your laptop is on.

## The only things left for me, in order (Nov 5 night)

The original form deadline was Thu Nov 5, 09:00 WIB. Everything below is about the repo and the links being right;
check the Cerebral Valley page for what can still be changed on the submission.

1. [x] Demo video and screenshots re-recorded on the live models (Nov 6). Watch `docs/demo/dalang-ai-demo.mp4`
   once yourself before you upload it.
2. [x] Repo pushed to https://github.com/ragilmalik/dalang-ai (public, MIT, no `.env`). Open it once in a private
   window to be sure.
3. **Upload the new demo video to YouTube as unlisted** with `docs/demo/dalang-ai-demo.srt` as captions, and check
   the link while logged out.
4. **Only with a parent's consent: a real child's recording** (no names spoken), up to 90 seconds:
   `python scripts/go_live.py --audio path/to/story.m4a`. Until then the demo says the voice is synthetic.
5. **A native Javanese check** of the Basa Jawa Story Starters (`web/lib/starters.json`), the Timun Mas sample film
   and `docs/CULTURAL_REVIEW.md`. Until then the docs say the Javanese hasn't been checked by a native speaker.
6. **Fill in the final links** in `docs/HANDOFF.md`, `docs/SUBMISSION.md` (Links) and `docs/SUBMISSION_FORM.md`.

Later: deploy (above), Post B and the #DalangCilik challenge (`docs/X_LAUNCH.md`), family tests with
`docs/USER_TESTING.md`. Testimonials go on the site only after real, consented family sessions.
