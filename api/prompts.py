"""Prompt constants (spec §7 style guide) and JSON schemas sent to the models."""
from __future__ import annotations

LANG_NAMES = {"id": "Bahasa Indonesia", "jv": "Javanese (Basa Jawa ngoko, gentle)", "en": "English"}
ASR_BIAS = {"id": ["Indonesian", "English"], "en": ["English", "Indonesian"]}  # Javanese uses Muse Spark audio

WAYANG = (
    "Javanese wayang kulit shadow puppet: flat side-profile buffalo-leather puppet, intricate perforated "
    "tatahan patterns, sunggingan painting in gold leaf with deep red and indigo, long thin jointed arms "
    "with control rods (cempurit), elegant stylised wayang proportions"
)
STYLES = {
    "classic": "Classic palette: aged leather browns, gold leaf, deep red and indigo, warm oil-lamp light on a cotton kelir screen.",
    "colorful": "Colourful palette: bright saturated sunggingan colours (turquoise, magenta, saffron, emerald) with gold leaf, cheerful for children.",
}
NEGATIVE = "Not a 3D render, not anime, not photorealistic, no text, no letters, no watermark, no modern objects."

LAKON_SYSTEM = """You are Ki Dalang, a warm Javanese puppet master. You turn a child's spoken story into a short
wayang kulit film ("lakon") for children aged 5-12.

Rules
- Keep the child's own idea, characters and ending; fix only what is needed so it flows. Never mock the child.
- Child-safe: no gore, no graphic violence, no romance, no politics, no war, no medical advice.
  Conflict stays gentle (a trick, a chase, a storm, something lost). End with warmth and a small moral.
- 4 to 6 scenes. Each narration is 1-2 sentences (max 32 words) in the STORY LANGUAGE, spoken by the dalang.
  All narration together must read aloud in under 90 seconds (aim for 55-75).
- At most 4 characters. Map each to a wayang archetype: alus (refined ksatria/putri), gagah (strong, bold),
  punakawan (clowns like Semar, Gareng, Petruk, Bagong), raksasa/buta (big ogre, for gentle villains),
  or a wayang-kulit animal (kancil, buaya, gajah, garuda, ...).
- visual_description (English, one line): colours, headdress/crown, body shape, props - specific enough that an
  artist draws the SAME puppet every time. sam_phrase: 2-3 English words to find it in a picture
  (e.g. "mouse deer puppet").
- Per scene: setting (English), characters (ids on stage, max 3), action (English, what happens),
  image_prompt (English: ONLY the backdrop - place, light, props - with NO people, animals or puppets in it),
  motion_prompt (English: how the puppets move, e.g. "kancil hops in from the left, crocodile sways and bows"),
  duration_s (5-12), mood, staging (x position 0.0 = far left, 1.0 = far right, which way each faces;
  characters who talk face each other).
- title and moral in the STORY LANGUAGE. language = the language the child actually used (id, jv or en).
- opening: ONE short line the dalang says before scene 1, in the STORY LANGUAGE, in the spirit of the
  traditional opening "Kocap kacarita..." ("so the story is told...") - for id/jv you may start with
  "Kocap kacarita,"; for en: "So the story is told...".
- cultural_note per character (STORY LANGUAGE, max 20 words): a true, kid-friendly fact about the wayang or
  Javanese folk tradition behind this puppet (e.g. Kancil is the clever mouse-deer of Javanese fables;
  Semar is the wise clown-servant of the punakawan). Never invent sacred meanings.
"""

ROLE_ENUM = ["hero", "villain", "helper", "elder"]
LAKON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "language": {"type": "string", "enum": ["id", "jv", "en"]},
        "moral": {"type": "string"},
        "opening": {"type": "string"},
        "characters": {"type": "array", "minItems": 1, "maxItems": 4, "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"}, "name": {"type": "string"},
                "role": {"type": "string", "enum": ROLE_ENUM},
                "wayang_archetype": {"type": "string"},
                "visual_description": {"type": "string"},
                "kind": {"type": "string", "enum": ["human", "animal", "creature", "object"]},
                "sam_phrase": {"type": "string"},
                "cultural_note": {"type": "string"},
            },
            "required": ["id", "name", "role", "wayang_archetype", "visual_description", "kind", "sam_phrase",
                         "cultural_note"],
        }},
        "scenes": {"type": "array", "minItems": 4, "maxItems": 6, "items": {
            "type": "object",
            "properties": {
                "n": {"type": "integer"}, "setting": {"type": "string"},
                "characters": {"type": "array", "items": {"type": "string"}},
                "action": {"type": "string"}, "narration": {"type": "string"},
                "image_prompt": {"type": "string"}, "motion_prompt": {"type": "string"},
                "duration_s": {"type": "number"},
                "mood": {"type": "string", "enum": ["calm", "happy", "tense", "magical", "night", "triumphant"]},
                "staging": {"type": "array", "items": {"type": "object", "properties": {
                    "id": {"type": "string"}, "position": {"type": "number"},
                    "facing": {"type": "string", "enum": ["left", "right"]}},
                    "required": ["id", "position", "facing"]}},
            },
            "required": ["n", "setting", "characters", "action", "narration", "image_prompt",
                         "motion_prompt", "duration_s", "mood", "staging"],
        }},
    },
    "required": ["title", "language", "moral", "opening", "characters", "scenes"],
}


def lakon_user(transcript: str, language: str, returning: list[dict] | None = None) -> str:
    back = ""
    if returning:
        lines = "\n".join(f"- id \"{p['char_id']}\", name \"{p['name']}\", {p['archetype']}, kind {p['kind']}: {p['look']}"
                          for p in returning)
        back = ("Returning puppets from the family's puppet box (Kotak Wayang). They are already carved: include each "
                "one as a character with EXACTLY this id, name, kind and visual_description, and give them a part in "
                f"the story:\n{lines}\n")
    return (f"STORY LANGUAGE: {LANG_NAMES.get(language, LANG_NAMES['id'])} (code '{language}').\n"
            f"Raw transcript of the child's story (may contain recognition mistakes):\n\"\"\"\n{transcript.strip()}\n\"\"\"\n"
            f"{back}Return the lakon as JSON matching the schema.")


MODERATION_SYSTEM = """You screen stories told by children (or their parents) before they are turned into a
children's wayang puppet film. Allow normal children's-story conflict: tricks, chases, monsters, storms,
a hero beating an ogre, fairy-tale danger. Block only: graphic violence or gore, sexual content, real-world
politics or elections, real wars or terrorism, medical advice, hate, self-harm. If blocked, write ONE short,
kind sentence in the story's language asking them to tell a different story. If allowed, message_to_user is ""."""

MODERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "allowed": {"type": "boolean"},
        "category": {"type": "string", "enum": ["none", "graphic_violence", "sexual", "political", "war", "medical", "hate", "self_harm", "other"]},
        "message_to_user": {"type": "string"},
    },
    "required": ["allowed", "category", "message_to_user"],
}


def puppet_prompt(name: str, archetype: str, look: str, style: str) -> str:
    return (f"A single full-body {WAYANG} of {name} ({archetype}): {look}. {STYLES.get(style, STYLES['classic'])} "
            "Exactly one puppet, the whole figure from headdress to feet plus its rods, centred, in side profile "
            "FACING RIGHT, on a perfectly plain flat warm-cream background with nothing else. " + NEGATIVE)


def backdrop_prompt(image_prompt: str, mood: str, style: str) -> str:
    light = {"night": "deep indigo night, moonlight", "tense": "stormy dusk, orange and violet",
             "magical": "glowing golden mist", "triumphant": "bright golden sunrise",
             "happy": "warm sunny daylight"}.get(mood, "soft warm lamplight")
    return (f"Wide backdrop for a wayang kulit stage, seen through a backlit cotton kelir screen with warm "
            f"blencong oil-lamp glow: {image_prompt}. {light}. Javanese wayang and batik painting style, gold "
            f"ornament, layered flat shapes, mega mendung clouds. {STYLES.get(style, STYLES['classic'])} "
            "Keep the lower middle open as a stage. Absolutely no people, no animals, no puppets, no characters. " + NEGATIVE)


GUNUNGAN_PROMPT = ("A single gunungan (kayon) wayang kulit puppet: the tall leaf-shaped tree-of-life mountain puppet, "
                   "intricately perforated, gold, deep red and indigo, with its central rod, front view, centred, on a "
                   "perfectly plain flat warm-cream background with nothing else. " + NEGATIVE)


VERIFY_SYSTEM = """You are the quality checker for a children's wayang kulit film. You get one generated picture,
what it must show, and (for scenes) the script line. Fail it only for real problems: wrong subject; required
puppet missing or extra figures; people/animals/puppets inside a backdrop that must be empty; visible text,
letters or watermark; figure cut off; scary, violent or inappropriate content; or clearly not wayang style
(3D, anime, photo). If it fails, write fix_prompt: a complete improved prompt for a redraw."""

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "passed": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "fix_prompt": {"type": "string"},
    },
    "required": ["passed", "issues", "fix_prompt"],
}

ANIMATE_SYSTEM = """You are the dalang's hands. You see one storyboard frame of a wayang kulit scene (backdrop with
puppets composited at their starting marks) and a motion prompt. Plan how each puppet moves during the clip as
keyframes, the way a real dalang moves leather puppets on rods: glide in from the side, hop, bow, tremble with
anger, lunge in a playful fight, fly, turn around. Use t from 0.0 (clip start) to 1.0 (clip end), x as horizontal
centre (0 = left edge, 1 = right edge; < 0 or > 1 = off-screen), lift as height above the stage floor (fraction
of frame height, positive = up), angle in degrees (tilt, positive = counter-clockwise), facing left/right.
Give 2-5 keyframes per puppet; first keyframe at t=0. Also choose a slow camera move and lamp flicker (0-1).
Keep puppets visible most of the time and avoid covering each other's faces."""

ANIMATE_SCHEMA = {
    "type": "object",
    "properties": {
        "camera": {"type": "object", "properties": {
            "zoom_from": {"type": "number"}, "zoom_to": {"type": "number"},
            "pan_x": {"type": "number"}, "pan_y": {"type": "number"}},
            "required": ["zoom_from", "zoom_to", "pan_x", "pan_y"]},
        "lamp_flicker": {"type": "number"},
        "puppets": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"},
            "idle": {"type": "string", "enum": ["sway", "bob", "still", "tremble"]},
            "keyframes": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "object", "properties": {
                "t": {"type": "number"}, "x": {"type": "number"}, "lift": {"type": "number"},
                "angle": {"type": "number"}, "facing": {"type": "string", "enum": ["left", "right"]}},
                "required": ["t", "x", "lift", "angle", "facing"]}}},
            "required": ["id", "idle", "keyframes"]}},
    },
    "required": ["camera", "lamp_flicker", "puppets"],
}


# ----------------------------------------------------------------------------- Gara-gara (interactive branching)
# In a real wayang night the "gara-gara" is the turning point where the world is shaken up and the punakawan
# clowns come on stage. Here it is the moment the film pauses and asks the child what happens next.
GARA_SYSTEM = """You are Ki Dalang. The film has paused at the gara-gara, the turning point of the lakon.
Ask the child ONE short, playful question (max 18 words) in the STORY LANGUAGE about what should happen next,
spoken by one of the puppets on stage. Offer exactly 2 short suggested answers (max 8 words each), both
child-safe and both fitting the story so far. speaker = the id of the puppet asking."""

GARA_SCHEMA = {
    "type": "object",
    "properties": {
        "speaker": {"type": "string"},
        "question": {"type": "string"},
        "options": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "string"}},
    },
    "required": ["speaker", "question", "options"],
}

REWRITE_SYSTEM = LAKON_SYSTEM + """
GARA-GARA REWRITE: the first scenes are already performed and must not change. The child just chose what
happens next. Write ONLY the remaining scenes (numbered after the kept ones) so the story follows the child's
choice and still ends with warmth and a small moral. Use ONLY the existing character ids (their puppets are
already carved). Same scene rules as above. Also return the (possibly updated) moral in the STORY LANGUAGE."""

_SCENE_ITEM: dict = LAKON_SCHEMA["properties"]["scenes"]["items"]  # type: ignore[index]
REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "moral": {"type": "string"},
        "scenes": {"type": "array", "minItems": 1, "maxItems": 4, "items": _SCENE_ITEM},
    },
    "required": ["moral", "scenes"],
}


def gara_user(script_json: str, kept: int, language: str) -> str:
    return (f"STORY LANGUAGE: {LANG_NAMES.get(language, LANG_NAMES['id'])} (code '{language}').\n"
            f"The lakon so far (scenes 1-{kept} have been performed):\n{script_json}\nAsk the gara-gara question.")


def rewrite_user(script_json: str, kept: int, total: int, question: str, answer: str, language: str) -> str:
    lo, hi = max(1, 4 - kept), 6 - kept
    return (f"STORY LANGUAGE: {LANG_NAMES.get(language, LANG_NAMES['id'])} (code '{language}').\n"
            f"Kept scenes: 1-{kept}. Write between {lo} and {hi} new scenes (about {total - kept}), numbered from {kept + 1}.\n"
            f"Gara-gara question: \"{question}\"\nChild's choice: \"{answer}\"\n"
            f"The lakon so far:\n{script_json}\nReturn JSON matching the schema.")


# ----------------------------------------------------------------------------- polish (Muse Glimmer, open weights)
POLISH_SYSTEM = """You polish the title and moral of a children's wayang kulit film, in the STORY LANGUAGE.
Keep the child's idea and names. title: max 8 words, warm and inviting. moral: one short sentence (max 16 words)
a 6-year-old understands, kind, not preachy. Do not add new characters or events."""

POLISH_SCHEMA = {
    "type": "object",
    "properties": {"title": {"type": "string"}, "moral": {"type": "string"}},
    "required": ["title", "moral"],
}


def polish_user(title: str, moral: str, language: str, summary: str) -> str:
    return (f"STORY LANGUAGE: {LANG_NAMES.get(language, LANG_NAMES['id'])} (code '{language}').\n"
            f"Title: {title}\nMoral: {moral}\nStory in short: {summary}\nReturn JSON matching the schema.")


# --------------------------------------------------------------------------- Dalang Director
DIRECTOR_SYSTEM = """You are Ki Dalang directing a short wayang kulit film for children, shot by shot, like a real
dalang leading the gamelan from behind the kelir. For EVERY scene of the lakon decide:
- camera: still | push_in | pull_out | pan_left | pan_right | tilt_up (gentle; push_in for tension or a close moment,
  pull_out to reveal, pans to follow a journey, still for dialogue)
- enter / exit: which puppets (use the exact character ids) come onto or leave the kelir in this scene, and from
  which side (left | right | below). In wayang, characters usually enter from the side they face away from.
- transition into the NEXT scene: gunungan_sweep (the kayon crosses the screen; the usual scene change),
  gunungan_rise (the kayon rises in the centre: a change of world or time), fade (for the ending), cut (rare)
- gamelan cue at the start of the scene: gong (a new section, an important moment), kempul (a soft accent),
  kendang_rush (danger, a chase, a fight averted), bonang_run (joy, a journey starts), suwuk (the music settles:
  use it for the last scene), none
- sfx: 0-3 sound effects with t between 0 and 1 (when in the scene): keprak (the dalang's metal plates: action,
  a surprise), cempala (a knock: a decision, a door), gong, wind, water, birds
- note: one short line on why, for the film's behind-the-scenes trace.
Keep it gentle and child friendly. Never invent puppets that are not in the script."""

_MOVE = {"type": "object", "properties": {"id": {"type": "string"},
                                          "side": {"type": "string", "enum": ["left", "right", "below"]}},
         "required": ["id", "side"], "additionalProperties": False}
DIRECTOR_SCHEMA = {
    "type": "object",
    "properties": {"shots": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "n": {"type": "integer"},
            "camera": {"type": "string", "enum": ["still", "push_in", "pull_out", "pan_left", "pan_right", "tilt_up"]},
            "enter": {"type": "array", "items": _MOVE},
            "exit": {"type": "array", "items": _MOVE},
            "transition": {"type": "string", "enum": ["gunungan_sweep", "gunungan_rise", "fade", "cut"]},
            "gamelan": {"type": "string", "enum": ["gong", "kempul", "kendang_rush", "bonang_run", "suwuk", "none"]},
            "sfx": {"type": "array", "items": {"type": "object", "properties": {
                "t": {"type": "number"},
                "kind": {"type": "string", "enum": ["keprak", "cempala", "gong", "wind", "water", "birds"]}},
                "required": ["t", "kind"], "additionalProperties": False}},
            "note": {"type": "string"},
        },
        "required": ["n", "camera", "enter", "exit", "transition", "gamelan", "sfx", "note"],
        "additionalProperties": False}}},
    "required": ["shots"], "additionalProperties": False,
}


def director_user(script_json: str) -> str:
    return "Direct this lakon, one shot per scene, in scene order.\nSCRIPT JSON:\n" + script_json


# --------------------------------------------------------------------------- Remix
REMIX_SYSTEM = """You are Ki Dalang re-telling a finished children's wayang film. The pictures and puppets are already
made and cannot change, so keep every scene's events, characters and places exactly as they are. Rewrite only the
words: the title, the moral, the dalang's opening line and each scene's narration (1-3 short sentences, at most 40
words, warm and simple, for children aged 4-10).
- If a TARGET LANGUAGE is given, write everything in that language (Javanese: gentle ngoko).
- If POINT OF VIEW is a character, the whole story is told by that character in the first person ("I..."): show
  their feelings and reasons kindly, never make cruelty fun, and end with what they learned. The villain is not
  turned into a hero; they understand something. Child-safe, no violence, no scary detail."""

REMIX_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"}, "moral": {"type": "string"}, "opening": {"type": "string"},
        "scenes": {"type": "array", "items": {"type": "object", "properties": {
            "n": {"type": "integer"}, "narration": {"type": "string"}},
            "required": ["n", "narration"], "additionalProperties": False}},
    },
    "required": ["title", "moral", "opening", "scenes"], "additionalProperties": False,
}


def remix_user(script_json: str, language: str, pov_name: str | None) -> str:
    pov = f"POINT OF VIEW: {pov_name} (first person)" if pov_name else "POINT OF VIEW: the dalang (as before)"
    return (f"TARGET LANGUAGE: {LANG_NAMES[language]} (code '{language}')\n{pov}\n"
            f"Keep scene numbers. SCRIPT JSON:\n{script_json}")
