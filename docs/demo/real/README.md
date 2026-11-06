# My own footage for the demo video

Drop phone clips and voice-over files here with these exact names, then re-render:
`python scripts/make_demo_video.py http://127.0.0.1:3000 --real docs/demo/real` (or `make demo-video`).
Every file is optional. A shot whose file is missing uses the screen recording (or still) and the synthetic
edge-tts voice, so a half-filled folder still renders. The shot list is `deliverables/win-kit/DEMO_VIDEO_REVIEW.md` §3.
Clips can be `.mp4 .mov .m4v .webm`, any orientation (portrait is letterboxed into 1920x1080); voice files `.wav .m4a .mp3 .aac .ogg`.

## Clips (A-E)

| File stem | Shot it replaces | What to film (no child's face or name; parent's consent first) | Used length |
|---|---|---|---|
| `A_child_tells` | `voice` (0:00-0:03 hook) | The child telling the story into the phone: hands, the waveform, maybe the back of the head. Its sound is kept. | up to 8 s |
| `C_garagara_answer` | `garagara` | The puppet asks; the child shouts an answer. Its sound is kept under the voice-over. | up to 12 s |
| `B_family_watching` | `why` | From behind the sofa: screen glow, the film's sound, a laugh or "lagi!". | up to 12 s |
| `E_tap_record` | `landing` | My hand tapping "Ceritakan kisahmu" on the phone. | up to 12 s |
| `D_shadow_play` | `print` | Printed puppets on skewers, a torch, a white sheet, lights off (hands only). | up to 12 s |

## Voice-over (optional, replaces edge-tts per shot)

Record in a quiet room, phone 20 cm from the mouth, one file per shot: `vo_<shot>.wav` (or .m4a/.mp3), where
`<shot>` is one of `film1 garagara why landing progress trace storyboard share print close`. Read the line for
that shot from `docs/demo/voiceover.txt`. For `why` and `close` read the "Malik, first person" line: those
first-person lines are only used with my own recording, never with the synthetic voice. Captions are made
from the same lines, so read them as written.

Nothing in this folder is committed except this README (clips can contain family audio).
