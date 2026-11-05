"""Fake-API art for tests, CI and offline rehearsal (FAKE_META=1 only): no API calls, labelled placeholder art.
Never a default for the demo or the seed data: the sample films are real model output (content/samples/).
Also draws the labelled stand-in picture used when Muse Image fails during a live film (verify.placeholder)."""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .. import sample_stories

SAMPLE_TRANSCRIPT = sample_stories.KANCIL_ID

SAMPLE_TRANSCRIPT_JV = sample_stories.KANCIL_JV

SAMPLE_SCRIPT = {
    "title": "Kancil dan Barisan Buaya",
    "language": "id",
    "moral": "Akal yang baik dipakai untuk mencari teman, bukan musuh.",
    "opening": "Kocap kacarita, di tepi hutan yang hijau, hiduplah seekor kancil yang cerdik.",
    "characters": [
        {"id": "kancil", "name": "Si Kancil", "role": "hero", "wayang_archetype": "wayang animal (kancil)",
         "kind": "animal", "sam_phrase": "mouse deer puppet",
         "cultural_note": "Kancil, si pelanduk cerdik, adalah tokoh dongeng Jawa yang menang dengan akal, bukan otot.",
         "visual_description": "small golden-brown mouse deer with big clever eyes, red and gold carved collar"},
        {"id": "buaya", "name": "Raja Buaya", "role": "villain", "wayang_archetype": "gagah wayang animal (buaya)",
         "kind": "animal", "sam_phrase": "crocodile puppet",
         "cultural_note": "Buaya sering muncul di dongeng Nusantara sebagai penjaga sungai yang kuat tapi mudah diakali.",
         "visual_description": "long green-indigo crocodile with gold scale patterns and a small crown"},
    ],
    "scenes": [
        {"n": 1, "setting": "jungle edge by a wide river", "characters": ["kancil"], "mood": "happy", "duration_s": 7,
         "action": "Kancil is hungry and sees a cucumber field across the river.",
         "narration": "Di tepi hutan, Si Kancil yang cerdik merasa lapar. Di seberang sungai, ladang mentimun berkilau.",
         "image_prompt": "jungle edge by a wide river, cucumber field on the far bank",
         "motion_prompt": "kancil hops in from the left and looks across the river",
         "staging": [{"id": "kancil", "position": 0.35, "facing": "right"}]},
        {"n": 2, "setting": "dark river with reeds", "characters": ["kancil", "buaya"], "mood": "tense", "duration_s": 7,
         "action": "The crocodile king rises from the river, hungry.",
         "narration": "Tapi sungai itu dijaga Raja Buaya dan kawan-kawannya yang juga lapar.",
         "image_prompt": "dark river with tall reeds", "motion_prompt": "crocodile glides in from the right, kancil trembles",
         "staging": [{"id": "kancil", "position": 0.25, "facing": "right"}, {"id": "buaya", "position": 0.7, "facing": "left"}]},
        {"n": 3, "setting": "river at golden hour", "characters": ["kancil", "buaya"], "mood": "magical", "duration_s": 8,
         "action": "Kancil says the king wants to count all the crocodiles.",
         "narration": "Kancil berkata, raja ingin menghitung semua buaya. Ayo berbaris dari sini sampai seberang!",
         "image_prompt": "river at golden hour", "motion_prompt": "kancil bows politely, crocodile sways",
         "staging": [{"id": "kancil", "position": 0.3, "facing": "right"}, {"id": "buaya", "position": 0.68, "facing": "left"}]},
        {"n": 4, "setting": "river crossing", "characters": ["buaya", "kancil"], "mood": "happy", "duration_s": 7,
         "action": "Kancil hops across the crocodiles' backs, counting.",
         "narration": "Satu, dua, tiga! Kancil melompat dari punggung ke punggung sampai ke seberang.",
         "image_prompt": "wide calm river crossing", "motion_prompt": "kancil jumps from back to back to the right",
         "staging": [{"id": "buaya", "position": 0.5, "facing": "right"}, {"id": "kancil", "position": 0.3, "facing": "right"}]},
        {"n": 5, "setting": "cucumber field at sunrise", "characters": ["kancil", "buaya"], "mood": "triumphant", "duration_s": 8,
         "action": "Kancil apologises and they become friends.",
         "narration": "Kancil tertawa, lalu meminta maaf. Raja Buaya ikut tertawa, dan sejak itu mereka berteman.",
         "image_prompt": "cucumber field at sunrise", "motion_prompt": "both bow to each other",
         "staging": [{"id": "kancil", "position": 0.32, "facing": "right"}, {"id": "buaya", "position": 0.7, "facing": "left"}]},
    ],
}

# Two more fake-API fixtures so the sample gallery shows different stories, languages and styles. They are
# hand-written stand-ins for what Muse Spark writes from a real recording; the fake API picks one by keyword.
SAMPLE_TRANSCRIPT_TIMUN_JV = sample_stories.TIMUN_MAS_JV

SAMPLE_TRANSCRIPT_SNAIL_EN = sample_stories.GOLDEN_SNAIL_EN

SAMPLE_SCRIPT_TIMUN = {
    "title": "Timun Mas lan Buto Ijo",
    "language": "jv",
    "moral": "Wani lan akal sing becik bisa ngalahake rasa wedi.",
    "opening": "Kocap kacarita, ing sawijining desa ana mbok rondho sing urip dhewekan.",
    "characters": [
        {"id": "timun", "name": "Timun Mas", "role": "hero", "wayang_archetype": "putri alus (refined girl)",
         "kind": "human", "sam_phrase": "girl puppet",
         "cultural_note": "Timun Mas iku dongeng Jawa Tengah; jenenge tegese 'timun emas'.",
         "visual_description": "young girl with a golden kemben, long black hair in a bun, carved gold flowers"},
        {"id": "buto", "name": "Buto Ijo", "role": "villain", "wayang_archetype": "buta (giant, gagah)",
         "kind": "creature", "sam_phrase": "giant puppet",
         "cultural_note": "Buta ing wayang iku raseksa gedhe, simbol hawa nepsu sing kudu dikalahake.",
         "visual_description": "huge green giant with round bulging eyes, fangs, red and gold crown"},
        {"id": "mbok", "name": "Mbok Rondho", "role": "elder", "wayang_archetype": "biyung (elder woman)",
         "kind": "human", "sam_phrase": "old woman puppet",
         "cultural_note": "Mbok rondho ing dongeng Jawa iku simbol katresnan ibu.",
         "visual_description": "kind old woman in a brown batik kain, white hair, holding a small basket"},
    ],
    "scenes": [
        {"n": 1, "setting": "village house at the edge of a forest", "characters": ["mbok", "timun"], "mood": "calm",
         "duration_s": 7, "action": "Mbok Rondho raises Timun Mas, born from a golden cucumber.",
         "narration": "Mbok Rondho nggedhekake Timun Mas, bocah wadon sing lair saka timun emas.",
         "image_prompt": "small bamboo village house at the edge of a forest", "motion_prompt": "the old woman sways gently",
         "staging": [{"id": "mbok", "position": 0.32, "facing": "right"}, {"id": "timun", "position": 0.66, "facing": "left"}]},
        {"n": 2, "setting": "forest at night", "characters": ["buto", "timun"], "mood": "night", "duration_s": 7,
         "action": "Buto Ijo comes to take Timun Mas.",
         "narration": "Ing sawijining wengi, Buto Ijo teka arep njupuk Timun Mas.",
         "image_prompt": "dark forest at night with a full moon", "motion_prompt": "giant stomps in from the right",
         "staging": [{"id": "timun", "position": 0.28, "facing": "right"}, {"id": "buto", "position": 0.7, "facing": "left"}]},
        {"n": 3, "setting": "bamboo forest", "characters": ["timun", "buto"], "mood": "tense", "duration_s": 7,
         "action": "Timun Mas throws cucumber seeds and needles; a forest of bamboo grows.",
         "narration": "Timun Mas nyebar wiji timun lan jarum. Dumadakan thukul alas pring sing kandel.",
         "image_prompt": "thick bamboo forest", "motion_prompt": "girl runs left, giant trembles",
         "staging": [{"id": "timun", "position": 0.25, "facing": "left"}, {"id": "buto", "position": 0.72, "facing": "left"}]},
        {"n": 4, "setting": "mud sea under stormy sky", "characters": ["buto", "timun"], "mood": "magical", "duration_s": 8,
         "action": "The last pouch of terasi becomes a sea of mud and the giant sinks.",
         "narration": "Terasi pungkasan dadi segara lendhut, lan Buto Ijo kecemplung.",
         "image_prompt": "wide mud sea under a stormy sky", "motion_prompt": "giant sinks slowly, girl watches",
         "staging": [{"id": "timun", "position": 0.25, "facing": "right"}, {"id": "buto", "position": 0.68, "facing": "left"}]},
        {"n": 5, "setting": "village house at sunrise", "characters": ["timun", "mbok"], "mood": "triumphant", "duration_s": 8,
         "action": "Timun Mas comes home safe.",
         "narration": "Timun Mas slamet bali, lan Mbok Rondho ngrangkul anake kanthi bungah.",
         "image_prompt": "village house at sunrise", "motion_prompt": "both bow to each other",
         "staging": [{"id": "timun", "position": 0.36, "facing": "right"}, {"id": "mbok", "position": 0.64, "facing": "left"}]},
    ],
}

SAMPLE_SCRIPT_SNAIL = {
    "title": "The Golden Snail",
    "language": "en",
    "moral": "Kindness opens doors that no spell can keep shut.",
    "opening": "Long ago, in a village by a clear river, there lived a kind old woman.",
    "characters": [
        {"id": "keong", "name": "Princess Candra Kirana", "role": "hero", "wayang_archetype": "putri alus (refined princess)",
         "kind": "human", "sam_phrase": "princess puppet",
         "cultural_note": "Keong Mas comes from the Javanese Panji tales; Candra Kirana is Panji's beloved princess.",
         "visual_description": "graceful princess with a golden crown, green and gold kain, holding a golden snail shell"},
        {"id": "nenek", "name": "Mbok Rondo Dadapan", "role": "elder", "wayang_archetype": "biyung (elder woman)",
         "kind": "human", "sam_phrase": "old woman puppet",
         "cultural_note": "The kind old widow is a classic helper in Javanese folk tales.",
         "visual_description": "old woman with a fishing basket, brown batik kain, white hair in a bun"},
    ],
    "scenes": [
        {"n": 1, "setting": "clear river with stones", "characters": ["nenek"], "mood": "calm", "duration_s": 7,
         "action": "The old woman finds a golden snail while fishing.",
         "narration": "One morning the old woman went fishing and found a shining golden snail.",
         "image_prompt": "clear shallow river with smooth stones", "motion_prompt": "old woman bends down slowly",
         "staging": [{"id": "nenek", "position": 0.45, "facing": "right"}]},
        {"n": 2, "setting": "simple village kitchen", "characters": ["nenek"], "mood": "magical", "duration_s": 7,
         "action": "Every morning the house is clean and food is ready.",
         "narration": "Every day she came home to a clean house and warm rice on the table. Who could it be?",
         "image_prompt": "simple village kitchen with a clay stove", "motion_prompt": "old woman looks around, puzzled",
         "staging": [{"id": "nenek", "position": 0.4, "facing": "right"}]},
        {"n": 3, "setting": "kitchen at dawn", "characters": ["nenek", "keong"], "mood": "happy", "duration_s": 8,
         "action": "She hides and sees a princess step out of the shell.",
         "narration": "So she hid behind the door, and saw a princess step out of the golden shell.",
         "image_prompt": "kitchen at dawn, soft light", "motion_prompt": "princess rises gracefully",
         "staging": [{"id": "nenek", "position": 0.25, "facing": "right"}, {"id": "keong", "position": 0.66, "facing": "left"}]},
        {"n": 4, "setting": "village yard at sunrise", "characters": ["keong", "nenek"], "mood": "triumphant", "duration_s": 8,
         "action": "The spell breaks and they become a family.",
         "narration": "The spell was broken, and the princess and the old woman lived together as a family.",
         "image_prompt": "village yard at sunrise with banana trees", "motion_prompt": "both bow to each other",
         "staging": [{"id": "keong", "position": 0.36, "facing": "right"}, {"id": "nenek", "position": 0.64, "facing": "left"}]},
    ],
}

# Fixture for the fake API's gara-gara question (Muse Spark writes the real one from the story).
GARA_QUESTION = {
    "id": {"speaker": "buaya", "question": "Hei, Kancil! Apa yang harus kulakukan sekarang?",
           "options": ["Buaya ikut menghitung", "Buaya mengajak Kancil menyeberang"]},
    "jv": {"speaker": "buaya", "question": "He, Kancil! Aku kudu piye saiki?",
           "options": ["Baya melu ngitung", "Baya ngajak Kancil nyabrang"]},
    "en": {"speaker": "buaya", "question": "Hey, Kancil! What should I do now?",
           "options": ["The crocodile counts too", "The crocodile carries Kancil across"]},
}

PALETTES = {
    "happy": [(250, 200, 110), (120, 160, 90)], "tense": [(120, 60, 70), (40, 50, 70)],
    "magical": [(240, 170, 90), (120, 80, 140)], "triumphant": [(255, 210, 120), (200, 120, 60)],
    "night": [(30, 40, 90), (10, 15, 40)], "calm": [(230, 200, 150), (140, 120, 90)],
}


def background(out: Path, mood: str, seed: int) -> Path:
    rnd = random.Random(seed)
    W, H = 1536, 1024
    top, bot = PALETTES.get(mood, PALETTES["calm"])
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] * (1 - k) + bot[i] * k) for i in range(3)))
    for layer in range(3):
        col = tuple(max(0, int(c * (0.55 + 0.12 * layer))) for c in bot)
        pts = [(0, H)]
        for x in range(0, W + 64, 64):
            pts.append((x, int(H * (0.55 + 0.1 * layer) + 60 * math.sin(x / 140 + seed + layer) + rnd.randint(-15, 15))))
        pts.append((W, H))
        d.polygon(pts, fill=col)
    for _ in range(6):  # mega mendung style clouds
        cx, cy, r = rnd.randint(0, W), rnd.randint(40, int(H * 0.35)), rnd.randint(60, 110)
        for k in range(4):
            d.ellipse([cx - r + k * 12, cy - r // 2 + k * 6, cx + r - k * 12, cy + r // 2 - k * 6],
                      outline=(255, 240, 210), width=5)
    im.filter(ImageFilter.SMOOTH).save(out)
    return out


def puppet(out: Path, name: str, kind: str, seed: int) -> Path:
    rnd = random.Random(seed)
    W, H = 1024, 1536
    im = Image.new("RGB", (W, H), (242, 232, 210))
    d = ImageDraw.Draw(im)
    main = (rnd.randint(120, 200), rnd.randint(40, 110), rnd.randint(20, 60))
    gold = (214, 170, 60)
    if kind == "animal" and any(w in name.lower() for w in ("buaya", "baya", "croc")):
        d.ellipse([90, 800, 900, 1000], fill=(60, 110, 90), outline=gold, width=10)  # long body
        d.polygon([(860, 840), (1010, 880), (1010, 930), (860, 960)], fill=(60, 110, 90), outline=gold)  # snout
        d.polygon([(90, 880), (10, 900), (90, 930)], fill=(60, 110, 90))  # tail
        for x in (220, 380, 600, 760):
            d.rectangle([x, 980, x + 36, 1120], fill=(60, 110, 90), outline=gold, width=5)
        for k in range(12):
            d.polygon([(160 + k * 60, 810), (185 + k * 60, 760), (210 + k * 60, 810)], fill=gold)
        d.ellipse([820, 830, 850, 860], fill=(242, 232, 210))
        d.line([(512, 1000), (512, 1480)], fill=(90, 60, 30), width=14)
        im.save(out)
        return out
    if kind == "animal":
        d.ellipse([200, 650, 820, 1000], fill=main, outline=gold, width=10)  # body
        d.ellipse([700, 520, 930, 720], fill=main, outline=gold, width=8)  # head (facing right)
        d.polygon([(760, 540), (790, 380), (820, 540)], fill=gold)  # ear
        for x in (300, 420, 600, 700):
            d.rectangle([x, 960, x + 40, 1240], fill=main, outline=gold, width=5)
        for k in range(10):
            d.ellipse([260 + k * 52, 760, 290 + k * 52, 790], fill=(242, 232, 210))
    else:
        d.ellipse([430, 180, 640, 400], fill=main, outline=gold, width=8)
        d.polygon([(450, 190), (535, 40), (620, 190)], fill=gold)
        d.polygon([(400, 400), (660, 400), (720, 1150), (340, 1150)], fill=main, outline=gold, width=10)
        d.line([(660, 450), (900, 820)], fill=main, width=36)
        d.line([(400, 450), (220, 820)], fill=main, width=36)
        for k in range(12):
            d.ellipse([450 + (k % 4) * 45, 520 + (k // 4) * 120, 480 + (k % 4) * 45, 550 + (k // 4) * 120], fill=(242, 232, 210))
    d.line([(512, 1150), (512, 1480)], fill=(90, 60, 30), width=14)  # control rod
    im.save(out)
    return out


def gunungan(out: Path) -> Path:
    W, H = 1024, 1536
    im = Image.new("RGB", (W, H), (242, 232, 210))
    d = ImageDraw.Draw(im)
    pts = []
    for k in range(0, 181, 6):
        a = math.radians(k)
        r = 1 - abs(math.cos(a)) ** 0.6
        pts.append((512 + 430 * math.cos(a) * (0.4 + 0.6 * r), 1250 - 1150 * math.sin(a) ** 0.7))
    d.polygon(pts, fill=(150, 40, 30), outline=(214, 170, 60))
    for i in range(14):
        y = 300 + i * 65
        d.line([(512, y), (512 - 180 + i * 6, y - 60)], fill=(214, 170, 60), width=8)
        d.line([(512, y), (512 + 180 - i * 6, y - 60)], fill=(214, 170, 60), width=8)
    d.line([(512, 1250), (512, 1500)], fill=(90, 60, 30), width=16)
    im.save(out)
    return out
