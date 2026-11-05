"""Stage 1 - Listen: Muse Voice Transcribe (Muse Spark 1.2 audio for Javanese), then a safety screen."""
from __future__ import annotations

from pathlib import Path

from .. import meta_client, prompts
from ..config import settings
from ..jobs import Job
from ..schemas import Moderation
from . import media


class Blocked(Exception):
    """The story was screened out; message is a kind sentence for the child."""


KEYWORDS = ["kancil", "buaya", "Semar", "Gareng", "Petruk", "Bagong", "Arjuna", "Bima", "gunungan", "wayang",
            "raksasa", "Timun Mas", "Malin Kundang", "Bawang Merah", "Bawang Putih"]


def screen(job: Job, text: str, fallback: str) -> None:
    """Child-safety screen. Runs on Muse Glimmer when USE_OPEN_WEIGHTS=true, else Muse Spark."""
    lang = job.s["language"]
    glimmer = settings.glimmer_active
    m = Moderation(**meta_client.chat_json(
        [{"role": "system", "content": prompts.MODERATION_SYSTEM},
         {"role": "user", "content": f"Story language: {lang}\nStory:\n{text}"}],
        prompts.MODERATION_SCHEMA, "moderation", model=settings.lakon_model, reasoning_effort="low", glimmer=glimmer))
    job.used(settings.glimmer_model if glimmer else settings.lakon_model)
    if not m.allowed:
        raise Blocked(m.message_to_user or fallback)


def run(job: Job, audio: Path | None, typed_text: str | None) -> str:
    """Stage 1, listen: the recording becomes a transcript (Muse Voice Transcribe; Muse Spark 1.2 audio understanding for Basa Jawa), or the typed story is used as is. Then the child-safety screen; raises Blocked with a kind message."""
    lang = job.s["language"]
    job.stage("listen", "running", "Listening to your story...")
    if typed_text and typed_text.strip():
        transcript = typed_text.strip()
    else:
        if audio is None:
            raise Blocked("Rekam atau ketik ceritanya dulu, ya! · Record or type a story first.")
        try:
            wav = media.to_wav(audio, job.dir / "story.wav", max_seconds=settings.max_audio_seconds)
        except RuntimeError as e:  # ffmpeg could not read it: not audio, or a broken file
            Path(audio).unlink(missing_ok=True)
            raise Blocked("Rekamannya tidak bisa dibuka. Coba file mp3, m4a, wav atau webm, ya! \u00b7 "
                          "We couldn't open that recording. Try an mp3, m4a, wav or webm file.") from e
        secs = media.wav_seconds(wav)
        child_voice = job.s.get("narration_voice") == "child"
        keep = False
        if lang == "jv":  # Muse Spark audio returns text only (no timestamps), so Javanese narration stays TTS
            transcript = meta_client.transcribe_with_spark_audio(wav, prompts.LANG_NAMES["jv"])
            job.used(settings.audio_model)
        else:
            transcript, turns = meta_client.transcribe_turns(wav, secs, prompts.ASR_BIAS.get(lang), KEYWORDS)
            job.used(settings.asr_model)
            if child_voice and turns:
                keep = True  # kept ONLY until the film is made, then deleted (runner.forget_recording)
                job.set(voice_turns=turns)
        if child_voice and not keep:
            job.set(voice_note="Child's voice needs speech timestamps; this film uses the narrator voice instead.")
        if not keep:
            wav.unlink(missing_ok=True)  # privacy (spec §9): audio is deleted right after transcription
    if audio is not None:
        Path(audio).unlink(missing_ok=True)
    if len(transcript.split()) < 4:
        raise Blocked({"id": "Ceritanya belum terdengar. Coba ceritakan lagi lebih panjang, ya!",
                       "jv": "Critane durung keprungu. Coba dicritakake maneh sing luwih dawa, ya!",
                       "en": "We couldn't hear a story yet. Try telling it again, a little longer!"}.get(lang))
    job.set(transcript=transcript)

    # Safety screen (spec §9) - Muse Spark structured output, or Muse Glimmer (open weights) when enabled
    job.stage("listen", detail="Checking the story is right for a children's film..."
              + (" (Muse Glimmer, open weights)" if settings.glimmer_active else ""))
    screen(job, transcript, "Let's tell a different story!")
    job.stage("listen", "done", f"\u201c{transcript[:140]}{'...' if len(transcript) > 140 else ''}\u201d")
    return transcript
