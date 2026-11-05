"""Regenerate docs/prompts.md from api/prompts.py:  python scripts/gen_prompts_doc.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api import prompts as P  # noqa: E402

out = ["# Prompts", "", "Generated from `api/prompts.py` by `scripts/gen_prompts_doc.py`. Edit the Python file, then rerun.", "",
       "Style guide (SPEC §7): flat side-profile buffalo-leather puppets, perforated tatahan, sunggingan gold with deep red "
       "and indigo, warm blencong lamp glow on a cotton kelir screen, gunungan between scenes; never 3D, anime or "
       "photoreal; never text inside images.", ""]


def sec(title: str, body: str, lang: str = "text") -> None:
    out.extend([f"## {title}", "", f"```{lang}", body.strip(), "```", ""])


sec("Lakon (Muse Spark system prompt)", P.LAKON_SYSTEM)
sec("Lakon user message (example)", P.lakon_user("Dulu ada kancil yang pintar...", "id"))
sec("Lakon JSON schema", json.dumps(P.LAKON_SCHEMA, indent=1), "json")
sec("Safety screen (Muse Spark, or Muse Glimmer with USE_OPEN_WEIGHTS=true)", P.MODERATION_SYSTEM)
sec("Puppet sheet (Muse Image, example)", P.puppet_prompt("Si Kancil", "wayang animal (kancil)",
                                                          "small golden-brown mouse deer, red and gold collar", "classic"))
sec("Backdrop (Muse Image, example)", P.backdrop_prompt("jungle edge by a wide river", "happy", "classic"))
sec("Gunungan (Muse Image)", P.GUNUNGAN_PROMPT)
sec("Verify agent (Muse Spark vision)", P.VERIFY_SYSTEM)
sec("Verify JSON schema", json.dumps(P.VERIFY_SCHEMA, indent=1), "json")
sec("Dalang's hands (Muse Wonder motion plan)", P.ANIMATE_SYSTEM)
sec("Motion plan JSON schema", json.dumps(P.ANIMATE_SCHEMA, indent=1), "json")
sec("Gara-gara question (Muse Spark)", P.GARA_SYSTEM)
sec("Gara-gara question JSON schema", json.dumps(P.GARA_SCHEMA, indent=1), "json")
sec("Gara-gara rewrite (Muse Spark, appended to the lakon prompt)", P.REWRITE_SYSTEM.split("GARA-GARA REWRITE:", 1)[1])
sec("Title and moral polish (Muse Glimmer, open weights)", P.POLISH_SYSTEM)
sec("Dalang Director (Muse Spark shot plan)", P.DIRECTOR_SYSTEM)
sec("Dalang Director JSON schema", json.dumps(P.DIRECTOR_SCHEMA, indent=1), "json")
sec("Remix (Muse Spark: re-tell in another language or the villain's voice)", P.REMIX_SYSTEM)
sec("Remix JSON schema", json.dumps(P.REMIX_SCHEMA, indent=1), "json")
(ROOT / "docs" / "prompts.md").write_text("\n".join(out), encoding="utf-8")
print("wrote docs/prompts.md")
