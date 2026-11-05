# Narrator voices: how I picked them

Meta's Model API has no text-to-speech model, so the narrator's voice comes from somewhere else. Until Nov 2 every
film was read by edge-tts with `id-ID-GadisNeural`, `jv-ID-SitiNeural` and `en-US-AnaNeural`, and the demo video
by `en-US-AndrewNeural`. Listening back, I thought they were genuinely bad: flat, a bit robotic, and the child
stand-in recording sounded like a sped-up cartoon. So on Nov 2 I ran a shoot-out and changed the defaults.

## How I scored them

* Same lines for every voice: the 6 demo voice-over lines, 4 lines from each sample story (Kancil in Indonesian,
  Timun Mas in Javanese, The Golden Snail in English) and the first 4 sentences of the child stand-in story.
* **UTMOS22** (the "strong" model from SpeechMOS) gives each clip a naturalness score from 1 to 5. It was trained
  on English, so for Indonesian and Javanese I treat it as a rough guide.
* **Whisper small** (faster-whisper, int8 on CPU) transcribes each clip, and I compare that with the script: word
  error rate (WER) and character error rate (CER). This catches a voice that sounds nice but mumbles or skips.
* The rule: the voice with the highest UTMOS wins, as long as its WER is no more than 3 points worse than the
  voice it replaces.
* Everything ran on an 8 GB laptop-class CPU box, one model at a time.

## Results (winners in bold)

| Where | Voice | UTMOS | WER | Notes |
|---|---|---|---|---|
| Demo voice-over (EN) | `en-US-AndrewNeural` +4% (old) | 4.40 | 17.4% | |
| | **Kokoro-82M `af_heart`** | **4.54** | **16.8%** | speed 0.92 and 1.0 score the same |
| | edge `en-US-EmmaMultilingualNeural` -4% | 4.46 | 18.2% | |
| | edge `en-GB-RyanNeural` -4% | 4.44 | 10.0% | |
| English narration | `en-US-AnaNeural` -8% (old) | 3.89 | 0.0% | |
| | **Kokoro-82M `af_heart` 0.92** | **4.52** | **0.0%** | needs `requirements-tts.txt` |
| | **edge `en-US-EmmaMultilingualNeural` -6%** | 4.44 | 0.0% | fallback when Kokoro isn't installed |
| Indonesian narration | `id-ID-GadisNeural` -8% (old) | 3.73 | 15.4% | |
| | **edge `en-US-EmmaMultilingualNeural` -6%** | **4.32** | **15.4%** | the multilingual voice reading Indonesian |
| | edge `en-US-AndrewMultilingualNeural` -6% | 4.07 | 1.7% | clearer to Whisper, sounds less natural |
| Javanese narration | `jv-ID-SitiNeural` -8% (old) | 3.94 | can't judge | |
| | **`jv-ID-SitiNeural` -4%, +4 Hz** | **3.96** | can't judge | same voice, small tweak |
| | edge `en-US-AndrewMultilingualNeural` -6% | 4.05 | can't judge | risk of an Indonesian accent |
| Child stand-in (MOCK) | `id-ID-GadisNeural` +35 Hz (old) | 2.52 | 2.8% | full story: 1.95, WER 10.7% |
| | **edge `en-US-EmmaMultilingualNeural` +40 Hz** | **3.59** | **2.8%** | full story: 3.03, WER 8.9% |

The WER on the demo lines is high for every voice because Whisper doesn't know "wayang kulit", "kelir",
"gunungan" or "dalang" and spells them its own way. That hits every voice about equally, so it still works for
comparing them.

The full table, including the voices that lost (Kokoro `am_puck`, `am_fenrir`, `bf_emma`, `af_bella`, edge Ava and
Brian, Meta MMS-TTS), is in the shoot-out notes I kept outside the repo (`work/tts/VOICE_SHOOTOUT.md`).

## What changed

* English: Kokoro-82M `af_heart` (speed 0.92) when it's installed. Without it, edge
  `en-US-EmmaMultilingualNeural` at -6%. Both beat Ana by a wide margin.
* Indonesian: edge `en-US-EmmaMultilingualNeural` at -6%. Whisper made exactly as many mistakes as with Gadis, and
  it sounds much more natural.
* Javanese: still `jv-ID-SitiNeural`, now at -4% and +4 Hz. Whisper can't transcribe Javanese (even Siti scored
  around 100% WER), so I had no way to check whether the multilingual voices actually say the words right, and an
  English-Indonesian voice reading Javanese tends to sound Indonesian. The tweak is within noise on UTMOS; I kept
  it because it scored best of the five Siti settings I tried.
* Child stand-in (`assets/sample-story/sample_story_synthetic.mp3`): edge `en-US-EmmaMultilingualNeural` at +40 Hz.
  It's still a synthetic voice and still labelled MOCK everywhere.
* Demo video stand-in narrator (`scripts/make_demo_video.py`): Kokoro `af_heart` at speed 1.0, each sentence
  spoken separately with a 0.25 s pause between them. At 0.92 with a 0.35 s pause the cut came to 3:01, so I took
  the normal speed, which scored the same. With 1.0 and 0.25 s the plan is 2:57.8. `python scripts/make_demo_video.py --plan` prints how long each shot
  will run with the current voice, without recording anything.

## What I tried and dropped

* **Chatterbox** (Resemble AI, MIT). Too slow on CPU for this: about 140 seconds for one demo line, so the full set
  would have taken over half an hour. I stopped it without scores.
* **Meta MMS-TTS** (`facebook/mms-tts-ind`, `mms-tts-jav`). Scored lower than every edge voice (UTMOS 3.1 to 3.5)
  and the licence is CC-BY-NC-4.0, non-commercial only. It's still there behind `TTS_ENGINE=mms` for anyone who
  wants an open Meta model and accepts that licence, but it's never the default.
* **EQ and de-essing** after loudness normalisation. See below.

### EQ and de-essing: off

I tried a de-esser, and a de-esser plus a little warmth (+1.5 dB at 200 Hz, -2 dB at 7 kHz), after the -16 LUFS
loudness pass. They did cut the hiss (energy at 5-9 kHz roughly halved), but UTMOS went down for every winner, so
the app only normalises loudness.

| Voice | loudnorm only | + de-ess | + de-ess + warm |
|---|---|---|---|
| Kokoro `af_heart` | 4.53 | 4.51 | 4.51 |
| edge Emma Multilingual | 4.41 | 4.35 | 4.35 |
| edge Siti -4% +4 Hz | 3.95 | 3.88 | 3.89 |
| edge Emma +40 Hz (child stand-in) | 3.55 | 3.48 | 3.45 |

## How to switch voices

All of this lives in `api/tts.py`.

| Setting | What it does |
|---|---|
| `TTS_ENGINE=auto` (default) | The winners above. English uses Kokoro if it can be imported, else edge. |
| `TTS_ENGINE=edge` | edge-tts only, for every language (the old behaviour, with the new edge voices). |
| `TTS_ENGINE=kokoro` | Kokoro wherever it can speak (English); edge for the rest. |
| `TTS_ENGINE=mms` | Meta MMS-TTS for Indonesian and Javanese. CC-BY-NC-4.0: non-commercial use only. |
| `TTS_VOICE_EN=kokoro:am_michael@0.95` | Override one language (`TTS_VOICE_ID`, `TTS_VOICE_JV` too). `edge:<voice>@-5` sets the edge rate. |
| `TTS_PYTHON=/path/to/venv/bin/python` | Run Kokoro or MMS in a separate venv, so the app's own stays small. |
| `DEMO_VOICE`, `DEMO_SENTENCE_GAP` | The demo video's stand-in narrator and the pause between sentences. |

Whatever is picked, a missing package, missing weights or any synthesis error falls back to the edge-tts voice for
that language, and every line is normalised to -16 LUFS before it's mixed under the gamelan.

To install Kokoro (optional, about 1 GB with torch and the weights):

    pip install torch --index-url https://download.pytorch.org/whl/cpu
    pip install -r requirements-tts.txt
    # plus espeak-ng: apt install espeak-ng  /  brew install espeak-ng

Deploying with Kokoro: [GO_LIVE.md](GO_LIVE.md#narrator-voice-when-deployed-optional-kokoro).

## Licences

| Voice | Licence |
|---|---|
| edge-tts | The client is LGPL-3.0 (used as a library). The voices are Microsoft's online read-aloud service: free, no key, their terms apply, and it needs internet. |
| Kokoro-82M (hexgrad) | Apache-2.0, code and weights. Runs offline on a CPU. Weights download on first use; nothing is in the repo. |
| Meta MMS-TTS | CC-BY-NC-4.0 (non-commercial). Opt-in only with `TTS_ENGINE=mms`. |
| Chatterbox | MIT. Tried and dropped (too slow on CPU). |

## Known gaps

* No synthetic voice here says "dalang", "kelir" or "gunungan" quite like a Javanese speaker would. Kokoro says
  something like "dalling". For the demo the real fix is my own voice-over (`docs/demo/real/`).
* UTMOS is an English-trained score, so the Indonesian and Javanese numbers are a rough guide. The old-vs-new
  pairs in `deliverables/voice-samples/` are there so a person can check by ear.
