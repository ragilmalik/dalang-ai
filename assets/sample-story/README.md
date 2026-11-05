# Sample story recording (synthetic sample voice)

`sample_story_synthetic.mp3` is a **synthetic sample voice made for this project**. It is not a real child and not
Malik. It is the sample kancil story (written for this project) read by the edge-tts voice `id-ID-GadisNeural` at its
normal pitch, made by `scripts/make_sample_story.py`. It shows the voice path: upload a recording, Muse Voice
Transcribe hears it. On the live Meta API (2026-11-05) Muse Voice Transcribe transcribed it; see
`docs/VERIFICATION_REPORT.md`.

To use a real recording instead (with a parent's consent, no names spoken):

    python scripts/go_live.py --audio path/to/real_story.m4a
    python scripts/demo_seed.py --audio path/to/real_story.m4a

Any format a phone records (m4a, webm, mp3, ogg, wav) works; keep it under 90 seconds.
