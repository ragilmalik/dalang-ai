"""Story Starters: 8+ public-domain Nusantara tales, three languages, short enough to read aloud, and every one
passes the Penjaga Budaya word scan and the story length limit."""
import json
from pathlib import Path

from api.config import settings
from api.pipeline import penjaga

DATA = json.loads((Path(__file__).resolve().parents[1] / "web" / "lib" / "starters.json").read_text(encoding="utf-8"))


def test_eight_or_more_tales_in_three_languages():
    items = DATA["items"]
    assert len(items) >= 8 and len({i["id"] for i in items}) == len(items)
    names = {i["title"] for i in items}
    assert {"Kancil dan Buaya", "Timun Mas", "Malin Kundang", "Keong Mas", "Roro Jonggrang", "Lutung Kasarung"} <= names
    for i in items:
        for key in ("id_text", "jv", "en"):
            words = len(i[key].split())
            assert 15 <= words <= 45, (i["id"], key, words)  # a child can read it aloud in well under 90 s
            assert len(i[key]) < settings.max_story_chars


def test_every_starter_passes_the_cultural_word_scan():
    for i in DATA["items"]:
        for key in ("id_text", "jv", "en"):
            script = {"scenes": [{"n": 1, "narration": i[key], "action": "", "image_prompt": ""}], "characters": []}
            assert penjaga.scan(script) == [], (i["id"], key, penjaga.scan(script))
