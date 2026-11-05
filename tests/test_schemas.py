import pytest
from pydantic import ValidationError

from api.pipeline import mock
from api.schemas import MotionPlan, Script


def test_sample_script_validates_and_numbers_scenes():
    s = Script(**mock.SAMPLE_SCRIPT)
    assert 4 <= len(s.scenes) <= 6
    assert [sc.n for sc in s.scenes] == list(range(1, len(s.scenes) + 1))
    for sc in s.scenes:
        assert {st.id for st in sc.staging} == set(sc.characters)


def test_unknown_characters_dropped_and_staging_filled():
    raw = {"title": "T", "language": "id", "moral": "m",
           "characters": [{"id": "Si Kancil!", "name": "Kancil", "visual_description": "deer"}],
           "scenes": [{"n": 9, "setting": "s", "characters": ["si_kancil", "ghost"], "narration": "x", "image_prompt": "p"}] * 4}
    s = Script(**raw)
    assert s.characters[0].id == "si_kancil"
    assert s.scenes[0].characters == ["si_kancil"]
    assert s.scenes[0].staging[0].id == "si_kancil"


def test_too_few_scenes_rejected():
    raw = dict(mock.SAMPLE_SCRIPT)
    raw["scenes"] = raw["scenes"][:3]
    with pytest.raises(ValidationError):
        Script(**raw)


def test_motion_plan_bounds():
    with pytest.raises(ValidationError):
        MotionPlan(puppets=[{"id": "a", "keyframes": [{"t": 2, "x": 0.5}]}])
