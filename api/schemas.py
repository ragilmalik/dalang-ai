"""Pydantic models for the lakon (script), checks and motion plans (spec §6)."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Lang = Literal["id", "jv", "en"]


class Character(BaseModel):
    id: str
    name: str
    role: Literal["hero", "villain", "helper", "elder"] = "hero"
    wayang_archetype: str = "alus (refined)"
    visual_description: str
    kind: Literal["human", "animal", "creature", "object"] = "human"
    sam_phrase: str = "puppet"
    cultural_note: str = ""  # one line on the wayang tradition behind this puppet, in the story language

    @field_validator("id")
    @classmethod
    def slug(cls, v: str) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", v.lower()).strip("_")[:24] or "c"


class Staging(BaseModel):
    id: str
    position: float = Field(0.5, ge=0.0, le=1.0)
    facing: Literal["left", "right"] = "right"

    @field_validator("id")
    @classmethod
    def slug(cls, v: str) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", v.lower()).strip("_")[:24] or "c"


class Scene(BaseModel):
    n: int
    setting: str
    characters: list[str] = []
    action: str = ""
    narration: str
    image_prompt: str
    motion_prompt: str = "gentle sway"
    duration_s: float = Field(6, ge=4, le=16)
    mood: Literal["calm", "happy", "tense", "magical", "night", "triumphant"] = "calm"
    staging: list[Staging] = []

    @field_validator("characters")
    @classmethod
    def slugs(cls, v: list[str]) -> list[str]:
        return [re.sub(r"[^a-z0-9_]+", "_", x.lower()).strip("_")[:24] for x in v]


class Script(BaseModel):
    title: str
    language: Lang = "id"
    moral: str = ""
    opening: str = ""  # the dalang's traditional opening line ("Kocap kacarita...") in the story language
    characters: list[Character] = Field(min_length=1, max_length=4)
    scenes: list[Scene] = Field(min_length=4, max_length=6)

    @model_validator(mode="after")
    def tidy(self) -> Script:
        ids = {c.id for c in self.characters}
        for i, s in enumerate(self.scenes, 1):
            s.n = i
            s.characters = [c for c in s.characters if c in ids][:4]
            s.staging = [st for st in s.staging if st.id in s.characters]
            missing = [c for c in s.characters if c not in {st.id for st in s.staging}]
            for k, cid in enumerate(missing):  # spread unstaged puppets across the screen, facing the middle
                pos = (k + 1) / (len(missing) + 1)
                s.staging.append(Staging(id=cid, position=pos, facing="right" if pos < 0.5 else "left"))
        return self


class Moderation(BaseModel):
    allowed: bool
    category: Literal["none", "graphic_violence", "sexual", "political", "war", "medical", "hate", "self_harm", "other"]
    message_to_user: str


class Verdict(BaseModel):
    passed: bool
    issues: list[str] = []
    fix_prompt: str = ""


class Keyframe(BaseModel):
    t: float = Field(ge=0.0, le=1.0)
    x: float = Field(ge=-0.3, le=1.3)
    lift: float = Field(0.0, ge=-0.4, le=0.4)
    angle: float = Field(0.0, ge=-25, le=25)
    facing: Literal["left", "right"] = "right"


class PuppetTrack(BaseModel):
    id: str
    idle: Literal["sway", "bob", "still", "tremble"] = "sway"
    keyframes: list[Keyframe] = Field(min_length=1)


class Camera(BaseModel):
    zoom_from: float = Field(1.0, ge=1.0, le=1.4)
    zoom_to: float = Field(1.06, ge=1.0, le=1.4)
    pan_x: float = Field(0.0, ge=-1.0, le=1.0)
    pan_y: float = Field(0.0, ge=-1.0, le=1.0)


class MotionPlan(BaseModel):
    camera: Camera = Field(default_factory=lambda: Camera(zoom_from=1.0, zoom_to=1.06, pan_x=0.0, pan_y=0.0))
    lamp_flicker: float = Field(0.4, ge=0.0, le=1.0)
    puppets: list[PuppetTrack] = []
