# Tutorial: from zero to your first wayang film

Written for someone who has never run code before. Takes about 20 minutes the first time.

## 1. Install two free programs (once)

1. **Python 3.12**: https://www.python.org/downloads/ . On Windows, tick **"Add python.exe to PATH"** on the first screen of the installer.
2. **Node.js 22 LTS**: https://nodejs.org/ . Accept all the defaults.

To check, open a terminal (Windows: press Start, type `cmd`, Enter) and type `python --version` and `node --version`. Both should print a version number.

## 2. Get the code

* From GitHub: click the green **Code** button, then **Download ZIP**, then unzip it (for example to `Documents\dalang-ai`).
* Or with git: `git clone <repo url>`.

## 3. Start it

* **Windows:** open the `dalang-ai` folder and double-click **`start.bat`**.
* **Mac / Linux:** open a terminal in the folder and run `bash start.sh`.

The first start installs everything and takes 3 to 6 minutes. Later starts take seconds. When you see
`Ready` and `http://localhost:3000`, open that address in your browser. Keep the black window open while you use the app.

Before you add a Meta key, the home page says "No Meta key on this server yet" under the buttons. The three sample
films play, but new films can't be made: the server refuses them and says why. To try every screen
without a key, set `FAKE_META=true` in `.env` and start again. That is test mode: the built-in fake Meta API answers,
and every picture is simple placeholder art, labelled as such.

## 4. Make a film (test mode or live)

1. Press **Ceritakan · Tell a story**. Choose the story language: **Bahasa Indonesia**, **Basa Jawa** or **English**.
2. Press the big gold microphone, allow the microphone, tell a story, press it again to stop. (Or use **Unggah** to upload a recording, **Ketik** to type, or tap one of the story starter cards.)
3. Open **Pilihan · Options** if you want another style, then press **Jadikan wayang · Make my wayang**.
4. Watch the troupe on stage: six players, one per job, light up as the film is made, with the stages listed underneath. With "Review storyboard first" ticked, you will see the scene cards: edit a line, press **Redo** on a scene you don't like, then **Bring it to life**.
5. Watch the film, switch 16:9 / 9:16, download it, or press **Bagikan ke galeri · Share to gallery** to get a public link. **Kelir Live** lets you perform the film with its puppets.

## 5. Go live with your Meta key (the only step left for you)

1. Get your key at https://dev.meta.ai (API keys) after claiming the hackathon credits.
2. In the `dalang-ai` folder open **`.env`** with Notepad (it appears after the first start).
3. Find the line `META_API_KEY=` and paste the key right after the `=` with no spaces. Save.
4. In a terminal in the folder run:
   * Windows: `.venv\Scripts\python scripts\check_keys.py`
   * Mac / Linux: `.venv/bin/python scripts/check_keys.py`
5. Every line should say **PASS**. If one says FAIL, it tells you why (usually a typo in the key, or credits not active yet).
6. Close the black window and start the app again. The header now says **Live**.

Optional open-weights bonus: also paste `BASETEN_API_KEY=` and set `USE_OPEN_WEIGHTS=true`, then run the check again.

## 6. Open it on your phone

The app runs on your computer. To open it on your phone or share it with judges:

* **Same Wi-Fi:** find your computer's IP (Windows: `ipconfig`, look for IPv4, e.g. 192.168.1.20) and open `http://192.168.1.20:3000` on the phone. The microphone only works on https or localhost, so use Upload or Type on the phone in this mode.
* **Anywhere, with https (recommended for the demo):** install Cloudflare's free `cloudflared` and run
  `cloudflared tunnel --url http://localhost:3000` . It prints an address like `https://something.trycloudflare.com`. Open it on the phone; the microphone works there. Put that address in `.env` as `PUBLIC_BASE_URL=` so share links use it.
* **Always-on hosting:** the repo has a `Dockerfile` (one container, port 3000). Any Docker host works (Render, Railway, Fly.io, a VPS). Set the same values as in `.env` as the host's secrets/environment variables and mount a disk at `/data`.

## 7. Make the backup demo film (recommended before recording the demo)

`.venv\Scripts\python scripts\demo_seed.py` (Windows) makes one complete film and keeps it. With `DEMO_MODE=true` in `.env`, if a live run ever fails during your demo, the app plays that film instead of showing an error.

## If something goes wrong

| What you see | What to do |
|---|---|
| `python` is not recognized | Reinstall Python and tick "Add python.exe to PATH". |
| The page says the server is not running | The black window was closed; start again. |
| Film has subtitles but no voice | The free voice service was unreachable; check the internet. The film is still fine. |
| check_keys says 401 | The key is wrong or has a space; paste it again. |
| check_keys says 402/429 | Credits not active or rate limit; wait a minute or check billing at dev.meta.ai. |
