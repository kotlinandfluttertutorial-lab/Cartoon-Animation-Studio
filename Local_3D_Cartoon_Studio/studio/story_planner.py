"""Validated story plans for the local cartoon production pipeline."""

from pathlib import Path
from typing import Annotated, Literal
from urllib.error import URLError
from urllib.request import Request, urlopen
import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

Character = Literal["Aarav", "Aanya"]
Emotion = Literal["neutral", "happy", "surprised", "sad", "thinking", "excited"]
Action = Literal["idle", "walk", "wave", "point", "nod", "greeting", "dance", "turn"]
Camera = Literal["wide", "medium", "close", "approach", "follow", "pullback"]
Effect = Literal["bird_chirp", "chime"]
PartSize = Annotated[float, Field(ge=0.02, le=1.5)]
PartAngle = Annotated[float, Field(ge=-360, le=360)]


class StoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class Dialogue(StoryModel):
    character: Character
    text: str = Field(min_length=1, max_length=300)
    emotion: Emotion


class Performance(StoryModel):
    character: Character
    action: Action
    expression: Emotion
    entrance: bool = False

    @model_validator(mode="after")
    def validate_entrance(self):
        if self.entrance and self.action != "walk":
            raise ValueError("An entrance requires the walk action.")
        return self


class SoundCue(StoryModel):
    effect: Effect
    at_seconds: int = Field(ge=0)


class PropPart(StoryModel):
    shape: Literal["box", "sphere", "cylinder", "cone", "torus"]
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    center: tuple[
        Annotated[float, Field(ge=-0.65, le=0.65)],
        Annotated[float, Field(ge=-0.65, le=0.65)],
        Annotated[float, Field(ge=-1.5, le=1.5)],
    ]
    size: tuple[PartSize, PartSize, PartSize]
    rotation: tuple[PartAngle, PartAngle, PartAngle] = (0, 0, 0)


class SceneProp(StoryModel):
    name: str = Field(min_length=1, max_length=60)
    position: Literal["screen_left", "center", "screen_right"]
    parts: list[PropPart] = Field(min_length=1, max_length=10)


class Scene(StoryModel):
    title: str = Field(min_length=1, max_length=100)
    duration_seconds: int = Field(ge=2, le=60)
    camera: Camera
    performances: list[Performance] = Field(max_length=2)
    narration: str = Field(max_length=300)
    dialogue: list[Dialogue] = Field(max_length=8)
    sound_effects: list[SoundCue] = Field(max_length=8)
    props: list[SceneProp] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def validate_cast_and_cues(self):
        cast = {performance.character for performance in self.performances}
        if len(cast) != len(self.performances):
            raise ValueError("A character can have only one performance per scene.")
        if any(line.character not in cast for line in self.dialogue):
            raise ValueError("Every speaker must have a performance in the scene.")
        if any(cue.at_seconds >= self.duration_seconds for cue in self.sound_effects):
            raise ValueError("Sound effects must start within the scene.")
        return self


class Story(StoryModel):
    title: str = Field(min_length=1, max_length=120)
    duration_seconds: int = Field(ge=2, le=120)
    characters: list[Character] = Field(min_length=1, max_length=2)
    scenes: list[Scene] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_schedule(self):
        cast = set(self.characters)
        if len(cast) != len(self.characters):
            raise ValueError("The cast contains duplicates.")
        if self.duration_seconds != sum(scene.duration_seconds for scene in self.scenes):
            raise ValueError("Scene durations must add up to the story duration.")
        if any(performance.character not in cast for scene in self.scenes for performance in scene.performances):
            raise ValueError("A performance refers to a character outside the story cast.")
        return self


def load_story(path: Path) -> Story:
    return Story.model_validate_json(path.read_text(encoding="utf-8-sig"))


def generate_story(idea: str, duration: int, url: str, model: str) -> Story:
    if not idea.strip() or not 2 <= duration <= 120:
        raise ValueError("Provide a story idea and a duration from 2 to 120 seconds.")
    schema = Story.model_json_schema()
    schema["$defs"]["Scene"]["required"].append("props")
    schema["properties"]["duration_seconds"] = {"type": "integer", "enum": [duration]}
    if duration < 15:
        schema["properties"]["scenes"].update(minItems=1, maxItems=1)
        schema["$defs"]["Scene"]["properties"]["duration_seconds"] = {
            "type": "integer", "enum": [duration],
        }
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": 0.2, "num_predict": 8192},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Plan a short English cartoon in the garden. Follow the JSON schema. "
                    "Scene durations must sum exactly to the requested duration. Include both characters, "
                    "short dialogue (for a story under 15 seconds, exactly one short line per character "
                    "and one scene), and one sound cue. Use an empty narration string if none is needed. "
                    "Set entrance to false unless the action is walk. "
                    "Build physical objects requested by the user as scene props in the relevant scenes, "
                    "even if characters also mention them in dialogue. Invent a recognizable low-poly "
                    "design for each object using colored geometric parts, with no preset object catalog. "
                    "Use a different position for each prop. Each part's center is local [x, y, z] in "
                    "meters, with positive z up. Size is its full [width, depth, height] in meters. "
                    "Optional rotation is [x, y, z] in degrees. Cylinders, cones and toruses use the z axis. "
                    "For example, a drum can be a red cylinder with two thin tan cylinders as its heads. "
                    "Use an empty props array in scenes without requested objects."
                ),
            },
            {"role": "user", "content": f"Duration: {duration} seconds. Story idea: {idea}"},
        ],
    }
    request = Request(
        f"{url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=180) as response:
            content = json.load(response)["message"]["content"]
        # Older and smaller models sometimes request an entrance with an
        # incompatible action. Preserve the action the model chose.
        data = json.loads(content)
        for scene in data["scenes"]:
            for performance in scene["performances"]:
                if performance["action"] != "walk" and performance.get("entrance") is True:
                    performance["entrance"] = False
        story = Story.model_validate_json(json.dumps(data))
        if story.duration_seconds != duration:
            raise ValueError(f"Expected a {duration}-second story, got {story.duration_seconds}.")
    except (URLError, TimeoutError, KeyError, TypeError, ValidationError, ValueError) as exc:
        raise RuntimeError(f"Ollama story generation failed. Use --story for manual JSON. {exc}") from exc
    return story
