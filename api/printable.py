"""Printable puppets: an A4 PDF with every SAM 3.1 cut-out of a film, large, with a dashed cut line around the
silhouette, its name and cultural note, and "shadow play at home" instructions in Bahasa Indonesia and English.
Page 1 is the how-to; then one page per puppet; the gunungan comes last as a bonus."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from fpdf import FPDF
from PIL import Image, ImageFilter

FONT_DIRS = [Path(__file__).resolve().parents[1] / "assets" / "fonts", Path("/usr/share/fonts/truetype/dejavu"),
             Path("C:/Windows/Fonts"), Path("/System/Library/Fonts/Supplemental"), Path("/Library/Fonts")]
FONT_FILES = {"": ["DejaVuSans.ttf", "arial.ttf", "Arial.ttf"], "B": ["DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"]}

HOWTO_ID = [
    "1. Cetak halaman ini di kertas tebal (atau tempel ke karton bekas).",
    "2. Gunting wayang mengikuti garis putus-putus. Minta bantuan orang dewasa untuk gunting.",
    "3. Tempel tusuk sate atau bilah bambu di belakang wayang dengan selotip (ujung runcing di bawah, tumpulkan dulu).",
    "4. Gantung kain putih atau seprai, matikan lampu, dan nyalakan senter dari belakang kain.",
    "5. Gerakkan wayang di antara senter dan kain. Jadilah dalang dan ceritakan kisahmu!",
]
HOWTO_EN = [
    "1. Print on thick paper (or glue the page onto old cardboard).",
    "2. Cut out each puppet along the dashed line. Ask a grown-up to help with the scissors.",
    "3. Tape a bamboo skewer to the back of each puppet (blunt the sharp tip first, point it down).",
    "4. Hang a white sheet, turn off the lights and shine a torch from behind the sheet.",
    "5. Move the puppets between the torch and the sheet. Be the dalang and tell your story!",
]


def cut_sheet(cutout: Path, out: Path, pad: int = 28, dash: int = 9) -> Path:
    """The puppet on white with a dashed cut line a little outside its silhouette (and around its rods)."""
    im = Image.open(cutout).convert("RGBA")
    W, H = im.width + 2 * pad, im.height + 2 * pad
    alpha = Image.new("L", (W, H), 0)
    alpha.paste(im.split()[-1].point(lambda v: 255 if v > 40 else 0), (pad, pad))
    grown = alpha.filter(ImageFilter.MaxFilter(2 * (pad // 2) + 1)).filter(ImageFilter.GaussianBlur(2))
    a = (np.asarray(grown) > 100).astype(np.uint8)
    edge = a ^ (np.asarray(Image.fromarray(a * 255).filter(ImageFilter.MinFilter(5))) > 127).astype(np.uint8)
    ys, xs = np.nonzero(edge)
    keep = ((xs + ys) // dash) % 2 == 0  # cheap dashes along the outline
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    canvas.paste(im, (pad, pad), im)
    px = np.asarray(canvas).copy()
    px[ys[keep], xs[keep]] = (40, 40, 40)
    Image.fromarray(px).save(out)
    return out


class _PDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=12)
        self.set_margins(14, 12, 14)
        self.family = "Helvetica"
        self.unicode = False
        self.dejavu = False
        for style, names in FONT_FILES.items():
            path = next((d / n for d in FONT_DIRS for n in names if (d / n).exists()), None)
            if path is None:
                break
            self.add_font("Body", style, str(path))
            self.family, self.unicode = "Body", True
            self.dejavu = "DejaVu" in path.name

    def t(self, text: str) -> str:
        if self.unicode:
            return text
        return (text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'").replace("\u00b7", "-")
                .encode("latin-1", "replace").decode("latin-1"))

    def para(self, text: str, size: float = 11, style: str = "", h: float = 5.5) -> None:
        self.set_font(self.family, style, size)
        self.multi_cell(0, h, self.t(text), align="L", new_x="LMARGIN", new_y="NEXT")


def build(job: dict[str, Any], job_dir: Path, out: Path) -> Path:
    script = job.get("script") or {}
    chars = {c["id"]: c for c in script.get("characters", [])}
    cast = [c for c in job.get("cast", []) if (job_dir / "puppets" / f"{c['id']}.png").exists()]
    pdf = _PDF()
    pdf.set_title(f"{script.get('title') or 'Dalang AI'} - wayang to print")
    pdf.set_author("Dalang AI")

    pdf.add_page()
    pdf.para("Dalang AI", 12, "B")
    pdf.para(script.get("title") or job.get("title") or "Wayang", 24, "B", 11)
    pdf.ln(2)
    pdf.para("Wayang untuk dicetak  \u00b7  Puppets to print", 14, "B", 7)
    pdf.ln(3)
    pdf.para("Main wayang bayangan di rumah", 13, "B", 7)
    for line in HOWTO_ID:
        pdf.para(line)
    pdf.ln(3)
    pdf.para("Shadow play at home", 13, "B", 7)
    for line in HOWTO_EN:
        pdf.para(line)
    pdf.ln(4)
    names = ", ".join(c["name"] for c in cast) or "-"
    pdf.para(f"Wayang di cerita ini \u00b7 Puppets in this story: {names}", 11, "B")
    if script.get("moral"):
        pdf.ln(2)
        pdf.para(f"\u201c{script['moral']}\u201d", 11, "I" if not pdf.unicode else "")
    pdf.ln(6)
    pdf.para("Gunting hanya dengan pendampingan orang dewasa \u00b7 Scissors only with a grown-up.", 9)
    pdf.para("Gambar wayang dibuat dengan Meta Muse Image dan dipotong dengan SAM 3.1 \u00b7 Puppets drawn with Meta "
             "Muse Image and cut out with SAM 3.1." + (" (Placeholder art: no Meta key yet.)" if job.get("offline") else ""), 9)

    pages = [(c["id"], c["name"]) for c in cast]
    if (job_dir / "puppets" / "gunungan.png").exists():
        pages.append(("gunungan", "Gunungan (kayon)"))
    with tempfile.TemporaryDirectory() as tmp:
        for pid, name in pages:
            info = chars.get(pid, {})
            sheet = cut_sheet(job_dir / "puppets" / f"{pid}.png", Path(tmp) / f"{pid}.png")
            pdf.add_page()
            pdf.para(name, 20, "B", 9)
            if info.get("wayang_archetype"):
                pdf.para(info["wayang_archetype"], 10)
            elif pid == "gunungan":
                pdf.para("Pembuka dan penutup cerita \u00b7 opens and closes the story, and sweeps between scenes", 10)
            top = pdf.get_y() + 2
            note = info.get("cultural_note", "")
            box_w, box_h = 182.0, 297 - top - (40 if note else 26)
            w_px, h_px = Image.open(sheet).size
            scale = min(box_w / w_px, box_h / h_px)
            w, h = w_px * scale, h_px * scale
            pdf.image(str(sheet), x=14 + (box_w - w) / 2, y=top, w=w, h=h)
            pdf.set_y(top + h + 3)
            pdf.para("\u2702  Gunting di garis putus-putus \u00b7 Cut along the dashed line" if pdf.dejavu
                     else "Gunting di garis putus-putus - Cut along the dashed line", 9)
            if note:
                pdf.para(note, 10)
    pdf.output(str(out))
    return out


class _A5(_PDF):
    def __init__(self) -> None:
        FPDF.__init__(self, orientation="P", unit="mm", format="A5")
        self.set_auto_page_break(auto=True, margin=10)
        self.set_margins(12, 12, 12)
        self.family, self.unicode, self.dejavu = "Helvetica", False, False
        for style, names in FONT_FILES.items():
            path = next((d / n for d in FONT_DIRS for n in names if (d / n).exists()), None)
            if path is None:
                break
            self.add_font("Body", style, str(path))
            self.family, self.unicode = "Body", True
            self.dejavu = "DejaVu" in path.name


def _picture(pdf: FPDF, path: Path, top: float, max_h: float) -> float:
    """Place a picture full width under `top`; returns the y below it."""
    w_px, h_px = Image.open(path).size
    w = 124.0
    h = min(max_h, w * h_px / w_px)
    w = h * w_px / h_px
    pdf.image(str(path), x=12 + (124 - w) / 2, y=top, w=w, h=h)
    return top + h + 4


def build_storybook(job: dict[str, Any], job_dir: Path, out: Path) -> Path:
    """Storybook (A5): a cover with the poster, then one page per scene with its storyboard picture and the
    narration in big type for reading together, then the moral. Same words as the film's captions."""
    script = job.get("script") or {}
    pdf = _A5()
    pdf.set_title(f"{script.get('title') or 'Dalang AI'} - storybook")
    pdf.set_author("Dalang AI")
    pdf.add_page()
    pdf.para("Dalang AI \u00b7 Buku cerita \u00b7 Storybook", 10, "B")
    pdf.para(script.get("title") or job.get("title") or "Wayang", 22, "B", 10)
    y = pdf.get_y() + 2
    poster = next((p for p in (job_dir / "poster.jpg", job_dir / "still_1.jpg") if p.exists()), job_dir / "poster.jpg")
    if poster.exists():
        y = _picture(pdf, poster, y, 95)
        pdf.set_y(y)
    if script.get("opening"):
        pdf.para(f"\u201c{script['opening']}\u201d", 13, "", 7)
    pdf.ln(2)
    pdf.para("Bacakan bersama: satu halaman satu adegan \u00b7 Read it together: one page per scene.", 9)
    lines = job.get("child_lines") or {}
    for sc in script.get("scenes", []):
        pdf.add_page()
        pdf.para(f"Adegan {sc['n']} \u00b7 Scene {sc['n']}", 10, "B")
        pic = next((p for p in (job_dir / f"still_{sc['n']}.jpg", job_dir / f"bg_{sc['n']}.png") if p.exists()), None)
        if pic:
            pdf.set_y(_picture(pdf, pic, pdf.get_y() + 1, 88))
        pdf.para(lines.get(str(sc["n"])) or sc.get("narration", ""), 16, "", 8.5)
        pdf.set_y(-16)
        pdf.para(f"{sc['n']}", 9)
    pdf.add_page()
    if script.get("moral"):
        pdf.para("Pesan cerita \u00b7 The moral", 12, "B", 7)
        pdf.para(f"\u201c{script['moral']}\u201d", 16, "", 8.5)
        pdf.ln(4)
    names = ", ".join(c.get("name", "") for c in script.get("characters", []))
    pdf.para(f"Tokoh \u00b7 Characters: {names}", 11)
    pdf.ln(4)
    pdf.para("Gambar oleh Meta Muse Image, wayang dipotong SAM 3.1, cerita oleh si anak dan Muse Spark \u00b7 Pictures by "
             "Meta Muse Image, puppets cut out by SAM 3.1, story by the child and Muse Spark."
             + (" (Placeholder art: no Meta key yet.)" if job.get("offline") else ""), 9)
    pdf.output(str(out))
    return out
