# B-roll for the demo video

These four pictures are AI-generated scenes, made on 2026-11-06 with a general image model (not Meta's Muse Image,
which makes the art inside the app). They show the kind of people Dalang AI is for. Nobody in them is real, and the
video shows the label "AI-generated scene" the whole time each one is on screen.

Where a screen shows the app, the picture on it is a real screenshot of Dalang AI, put into the scene afterwards
with a perspective warp (`work/media2/broll/comp.py` in my working folder). The generator never drew any app UI.

| File | Used in | What it shows | Real screen inside |
|---|---|---|---|
| `child-tells-story.jpg` | 0:00 hook, under the child's stand-in voice | A girl of about 7 telling a story on a terrazzo floor while her mother records on a phone | the home page (`docs/screenshots/readme/home-phone.png`) |
| `family-watching.jpg` | "Every child can be a dalang" shot | Grandmother, father and two kids on a mat watching a film on a laptop | none (screen faces away) |
| `classroom-vote.jpg` | first 3.6 s of the gara-gara shot | A primary-school class voting on shared phones, the vote on the projector | the classroom vote (`docs/screenshots/r5/classroom-vote.png`) |
| `shadow-play.jpg` | first 3.8 s of the print shot | Three kids behind a bedsheet with a torch and paper puppets | none |

Prompts (shortened): "A candid documentary photo, 16:9 wide, of ..." plus the scene, "Semarang kampung house,
terrazzo floor, green-painted wall", "35mm lens, f/2.8, slight film grain, true-to-life skin texture, unretouched",
and "no text, no logos, no watermark, no famous faces". I painted out a small logo the model put on the laptop lid.

`DEMO_BROLL=0 python scripts/make_demo_video.py` makes the video without them. A real phone clip in `docs/demo/real/`
for the same shot always replaces the B-roll.
