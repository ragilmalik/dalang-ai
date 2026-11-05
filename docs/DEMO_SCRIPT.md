# 3-minute demo video: script and shot list

There's a finished cut already: `docs/demo/dalang-ai-demo.mp4` (<!-- facts:demo_length -->2:58<!-- /facts -->, 1920x1080, voice-over + captions, loudness -16.8 LUFS). I re-recorded it on Nov 4
on the current site, with the voice-over read by Kokoro-82M `af_heart` (see [VOICES.md](VOICES.md)). It's rendered
from a real browser session of the working app by `python scripts/make_demo_video.py <web url>` (in one go on the
fake API with `bash scripts/demo_local.sh`, or as part of `python scripts/go_live.py`). The shot list with stills is
`docs/demo/STORYBOARD.md` and the voice-over text is `docs/demo/voiceover.txt`. Two cuts for X come from the same render and open on Kelir Live:
`docs/demo/teaser_60s.mp4` (16:9: the Kelir Live shot, the film's opening and first scenes, the classroom vote, the
close card) and `docs/demo/teaser_vertical.mp4` (9:16: Kelir Live recorded on a phone-sized screen, then the vertical
film and an end card).

It was recorded on the fake Meta API, so the puppets are placeholder art (labelled in the app, the film and the
teasers). The first 3 s use `assets/sample-story/sample_story_synthetic.mp3`, a synthetic stand-in voice that's labelled
on screen (not a real child). The three classroom "phones" in the vote shot are API calls made by the recording
script, not real people.

Shot order (the current cut keeps the v3 order): the child's voice over black (0:00-0:03) -> the film's opening (gong, gunungan, "Kocap kacarita")
-> film part 1 -> Gara-gara classroom vote (QR, three votes arrive, the teacher closes it) -> film part 2 -> Kelir
Live (the child drags a puppet across the lamp-lit screen, turns another, taps the gunungan, flips to the colour
side) -> why (Semarang, every child a dalang) -> home hero + one-tap Story Starter -> pipeline theatre (six models as
a wayang troupe; Dalang Director and gamelan named) -> Penjaga Budaya + receipt + agent trace -> player with
read-along, share to Pentas, sticker pack + GIF -> print puppets + storybook -> end card (tagline, model list, link
text; a QR only once a real link exists). To make it fit I cut two shots from v2, the storyboard (parents in control)
and the Kotak Wayang moment. The close card now holds 2.5 s with no caption over its lines.

My own footage and voice: put phone clips A-E and per-shot voice-over files in `docs/demo/real/` (file names are in
`docs/demo/real/README.md`) and re-render. Each file replaces that shot's recording or synthetic voice. The
first-person lines ("I'm Malik, from Semarang...") are only used with my own recording.

The table below is the longer shot list, for recording it by hand (phone shots, a child's real voice).

Only show what was built during the hackathon. Record the screen at 1080p (OBS Studio is free) and the phone shots
with the phone's own screen recorder. Record a live run with real keys and keep the `DEMO_MODE` film ready as a
backup. Target 2:50.

| Time | Shot (screen) | Voice-over (me, English; Indonesian subtitles optional) |
|---|---|---|
| 0:00-0:12 | Black screen, a gong sound, then the finished film's title card *"Kancil dan Barisan Buaya"* with the gunungan | "In Java, children grew up watching the dalang bring leather puppets to life. Today, almost none of them have seen a wayang show." |
| 0:12-0:25 | Phone in hand, home page, tap *Ceritakan · Tell a story* (the composer *"Ceritakan kisahmu"* opens) | "Dalang AI lets any child tell a story out loud, in Indonesian, Javanese or English, and get it back as their own wayang kulit film." |
| 0:25-0:45 | A child's voice (or mine) recording 20-30 s; live waveform moving; tap *Make my wayang* | "Up to ninety seconds. You just talk. Nothing to type." |
| 0:45-1:25 | Film page: the pipeline theatre (six troupe members, each on a lit kelir) and the stage timeline with thumbnails: transcript appears, lakon title, puppet cut-outs, backdrops, the checker line *"Checker sent scene 2 back… redrawing"* | "Muse Voice Transcribe hears the story. Muse Spark writes the lakon as structured JSON, with characters mapped to wayang archetypes and four to six scenes. Muse Image carves each puppet once and SAM 3.1 cuts it out, so the same puppet shows up in every scene. A verify agent on Muse Spark vision checks every picture and sends the bad ones back to be redrawn." |
| 1:25-1:45 | Storyboard: edit one narration line, tap *Redo* on a scene, open *Di balik kelir · Behind the screen*, then *Bring it to life* | "Parents can change a line or repaint a scene. Under the storyboard, an agent trace lists every Meta call and every decision." |
| 1:45-2:00 | Stage 6 thumbnails moving | "Muse Wonder is the dalang's hands. It looks at each storyboard frame and plans the puppets and camera as keyframes, and my kelir engine performs them." |
| 2:00-2:30 | The finished film full screen with sound (15-20 s), then switch to 9:16 on the phone | "Narration in the child's language, subtitles, gamelan, gunungan between scenes. Landscape for the TV, vertical for Stories." |
| 2:30-2:42 | Under *Simpan dan bagikan · Keep and share*, copy the link, open the watch page on a second phone, then /pentas | "Films stay private until the family shares them. Recordings are deleted right after transcription." |
| 2:42-2:55 | Architecture image (`docs/architecture.png`) and repo | "Six Meta models in one pipeline, two open-weight options (Muse Spark Open, Muse Glimmer), MIT licensed, built this week. Dalang AI: every child can be a dalang." |

Shot checklist: home (phone), recording with waveform, every stage with thumbnails, the checker redraw line,
storyboard edit and redo, finished film with sound, 9:16 on phone, share link opened on a second device, Pentas,
architecture slide, repo page. Don't show API keys, `.env`, or a terminal with keys in it.
