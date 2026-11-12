# Stage 4.3 — Dialogue, Lip-Sync & Expression System
## Architecture Plan

**Project:** Local 3D Cartoon Animation Studio  
**Planned stage:** 4.3  
**Prerequisites:** PR #16 merged into `develop`  
**Base branch:** `develop` (after PR #16 merge)  
**New branch:** `feature/stage-4-3-dialogue-lipsync`  
**Status:** PLANNING — not yet started

**Gate:** Do not begin implementation until `git log develop` confirms `feature/stage-4-2-2-transform-hierarchy` is merged.

---

## 1. Objective

Build a reusable dialogue, lip-sync and facial expression system for Aarav and Aanya that can drive cartoon-style character speech animation for future episode production.

The system must work with:
- The existing rigid-object-parented character rigs
- Blender Workbench rendering (no EEVEE/Cycles)
- Python 3.11.9 + Blender 4.4.3 + FFmpeg 9.0.2
- CPU-only hardware (Intel i7-8650U, 32 GB RAM)
- Piper TTS (already integrated)
- Ollama Qwen3 4B (for dialogue generation)

---

## 2. Module Architecture

```
Local_3D_Cartoon_Studio/
  studio/
    dialogue/
      __init__.py
      phoneme_mapper.py      # Text → phoneme sequence
      mouth_shapes.py        # Phoneme → mouth shape definitions
      lipsync_generator.py   # Generates per-frame mouth positions
      expression_library.py  # Emotion → facial component transforms
      dialogue_sequencer.py  # Combines TTS timing + lipsync + expressions
      conversation_scene.py  # Two-character conversation orchestration

  blender/
    scripts/
      apply_lipsync.py       # Applies lipsync data to blend file per frame
      apply_expression.py    # Applies expression to character
      render_dialogue.py     # Renders dialogue scene with animation

  output/
    stage4_3/
      previews/              # Dialogue scene previews
      audio/                 # TTS audio files
      lipsync_data/          # JSON lipsync timing files

  tests/
    test_stage4_3_dialogue.py
    test_stage4_3_lipsync.py
    test_stage4_3_expressions.py
```

---

## 3. Module Specifications

### 3.1 Phoneme Mapper (`phoneme_mapper.py`)

Converts text to a timed phoneme sequence compatible with Piper TTS output.

Approach:
- Use CMU Pronouncing Dictionary (cmudict via NLTK or a lightweight bundled version) for English phoneme mapping
- For each word in dialogue text, produce a list of ARPABET phonemes
- Map phonemes to simplified viseme groups (7 groups sufficient for cartoon):
  - REST (silence/neutral)
  - MBP (lips together: M, B, P)
  - FV (teeth on lip: F, V)
  - TD (tongue up: T, D, N, L)
  - WQ (rounded lips: W, OO, Q)
  - OPEN (open: AA, AH, AO)
  - EI (spread lips: EE, IH)
  - CH (puckered: CH, SH, ZH)

```python
def text_to_phonemes(text: str) -> list[tuple[str, str]]:
    """Returns list of (word, phoneme_sequence) pairs."""

def phonemes_to_visemes(phonemes: list[str]) -> list[str]:
    """Maps ARPABET phonemes to 7 cartoon viseme groups."""
```

### 3.2 Mouth Shapes (`mouth_shapes.py`)

Defines the mouth object transform for each viseme.

Since characters use separate mesh objects (not shape keys), each viseme is defined as a set of object transforms:

```python
VISEME_TRANSFORMS = {
    "REST": {"Mouth": {"scale": (1.0, 1.0, 1.0), "location_offset": (0, 0, 0)}},
    "MBP":  {"Mouth": {"scale": (0.3, 1.0, 0.5)}},   # closed lips
    "OPEN": {"Mouth": {"scale": (1.5, 1.0, 1.5), "location_offset": (0, 0, -0.02)}},  # open
    "EI":   {"Mouth": {"scale": (1.3, 1.0, 0.8)}},   # smile-like
    # ...
}
```

Also define eye blinking: periodic Eye_L/Eye_R scale Z → 0 → 1 at natural blink rate (~4s).

### 3.3 Lip-Sync Generator (`lipsync_generator.py`)

Takes Piper TTS audio timing data and produces per-frame mouth transform keyframes.

Piper TTS outputs a WAV file. We extract approximate word timing using:
- Audio duration / word count for even distribution (simple approach)
- Or Whisper transcription alignment (better, but adds dependency)

For Stage 4.3, use the simple approach:
```python
def generate_lipsync_data(
    text: str,
    audio_duration_s: float,
    fps: int = 24
) -> dict:
    """
    Returns {frame_number: viseme_name} mapping.
    Distributes phonemes evenly across audio duration.
    """
```

Output format (JSON):
```json
{
  "fps": 24,
  "total_frames": 72,
  "character": "Aarav",
  "frames": {
    "1": "REST",
    "5": "MBP",
    "8": "OPEN",
    ...
  }
}
```

### 3.4 Expression Library (`expression_library.py`)

Defines facial expression transforms for 6 emotions using existing facial component objects.

```python
EXPRESSIONS = {
    "neutral":   {},  # all at rest
    "happy":     {"Eyebrow_L": {"z": +0.02}, "Eyebrow_R": {"z": +0.02}, "Mouth": {"scale_z": 0.8}},
    "surprised": {"Eyebrow_L": {"z": +0.03}, "Eye_L": {"scale_z": 1.2}, "Mouth": {"scale": 1.3}},
    "sad":       {"Eyebrow_L": {"z": -0.02}, "Eyebrow_R": {"z": -0.02}},
    "thinking":  {"Eyebrow_R": {"z": +0.015}},
    "excited":   {"Eyebrow_L": {"z": +0.025}, "Eye_L": {"scale_z": 1.1}, "Mouth": {"scale": 1.2}},
}
```

### 3.5 Dialogue Sequencer (`dialogue_sequencer.py`)

Combines:
1. Ollama-generated dialogue text
2. Piper TTS audio generation
3. Lipsync data generation
4. Expression sequence (emotion tags in dialogue)
5. Animation frame schedule

```python
@dataclass
class DialogueLine:
    character: str          # 'Aarav' or 'Aanya'
    text: str
    emotion: str = 'neutral'
    start_frame: int = 1

class DialogueSequencer:
    def sequence(self, lines: list[DialogueLine]) -> DialogueScene: ...
    def generate_audio(self, line: DialogueLine) -> Path: ...
    def generate_lipsync(self, line: DialogueLine, audio: Path) -> dict: ...
```

### 3.6 Conversation Scene (`conversation_scene.py`)

Orchestrates a two-character conversation:

```python
class ConversationScene:
    def render_conversation(
        self,
        dialogue: list[DialogueLine],
        output_dir: Path,
        use_garden: bool = True
    ) -> Path:  # returns final MP4 path
```

Steps:
1. Load garden environment (optional)
2. Append both characters
3. Apply lipsync + expressions per frame via Blender subprocess
4. Render each frame as PNG
5. Assemble with FFmpeg (audio + video)

---

## 4. Implementation Stages

### Stage 4.3.1 — Foundation
- Phoneme mapper (cmudict-based)
- Mouth shape definitions (7 viseme groups)
- Expression library (6 emotions)
- Basic lipsync generator (even distribution)
- Unit tests for all modules
- No Blender integration yet

### Stage 4.3.2 — Blender Integration
- `apply_lipsync.py` Blender script
- `apply_expression.py` Blender script
- Single-character dialogue preview rendering
- Tests with real Blender execution
- Previews: Aarav speaking 2 sentences, Aanya speaking 2 sentences

### Stage 4.3.3 — Conversation Scenes
- `conversation_scene.py`
- Two-character conversation rendering
- Garden environment integration
- Piper TTS + Ollama dialogue generation
- FFmpeg audio/video assembly
- 30-second test conversation

### Stage 4.3.4 — Validation and QA
- Full regression (all Stage 4.1/4.2/4.2.1/4.2.2 tests)
- New Stage 4.3 tests
- Performance benchmarks (render time per frame)
- check_before_push.py validation
- PR targeting develop

---

## 5. New Files and Modules

```
studio/dialogue/__init__.py
studio/dialogue/phoneme_mapper.py
studio/dialogue/mouth_shapes.py
studio/dialogue/lipsync_generator.py
studio/dialogue/expression_library.py
studio/dialogue/dialogue_sequencer.py
studio/dialogue/conversation_scene.py

blender/scripts/apply_lipsync.py
blender/scripts/apply_expression.py
blender/scripts/render_dialogue.py

tests/test_stage4_3_dialogue.py
tests/test_stage4_3_lipsync.py
tests/test_stage4_3_expressions.py

docs/reports/STAGE_4_3_*.md
output/stage4_3/previews/
output/stage4_3/audio/
output/stage4_3/lipsync_data/
```

---

## 6. Dependencies

| Dependency | Status | Notes |
|---|---|---|
| Piper TTS | Already installed | Audio generation |
| Ollama + Qwen3 4B | Already installed | Dialogue generation |
| FFmpeg 9.0.2 | Already installed | Audio/video assembly |
| NLTK / cmudict | To be evaluated | Phoneme mapping — may use bundled dict instead |
| Blender 4.4.3 | Already installed | Animation rendering |
| numpy | Already installed | Audio processing |
| Pillow | Already installed | Image validation |

No new large dependencies required. NLTK cmudict is small (~2 MB) and free.

---

## 7. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Piper TTS audio timing not aligned with phonemes | MEDIUM | Use simple even-distribution approach; upgrade to Whisper alignment in Stage 4.4 |
| Mouth shapes too crude for readable lipsync | LOW | 7-viseme groups are standard for cartoon; can tune transforms |
| Rigid-parenting limits expression range | MEDIUM | Use larger transform offsets; for Stage 4.4 consider shape keys |
| Render performance too slow for full conversation | MEDIUM | Render at 640×360 Workbench; benchmark per-frame timing before committing to full scenes |
| Ollama dialogue quality | LOW | Qwen3 4B is adequate for simple children's dialogue |
| FFmpeg audio sync | LOW | Use `-async 1` flag; well-tested in existing code |

---

## 8. Testing Strategy

| Test | Type | Target |
|---|---|---|
| Phoneme mapping accuracy | Unit | 20 test words against expected viseme sequences |
| Lipsync data structure | Unit | Valid JSON, correct frame count, all visemes valid |
| Expression transform safety | Unit | No transforms cause > 2× scale or > 0.5 offset |
| Blender apply_lipsync | Integration | Mouth objects move per frame, no detachment |
| Blender apply_expression | Integration | Expression visible in render, pixel diff > 1% |
| Piper audio generation | Integration | WAV file exists, non-zero duration |
| FFmpeg audio+video | Integration | MP4 has audio track, correct duration |
| Full conversation render | End-to-end | 10-frame test conversation renders successfully |
| All Stage 4.2.x regression | Regression | 61/61 must still pass |

---

## 9. Character File Protections

- Original `aarav.blend` and `aanya.blend` remain READ-ONLY
- Stage 4 working copies (`aarav_stage4.blend`, `aanya_stage4.blend`) used for all animation
- Stage 4.3 creates NO new working copies — uses existing Stage 4 copies
- All lipsync applied at render time (not saved back to blend files)
- Expressions applied transiently and restored after each frame render

---

## 10. Gate Condition

**Stage 4.3 implementation MUST NOT begin until:**

```bash
git checkout develop
git pull origin develop
git log --oneline -3  # Must show PR #16 merge commit
```

Confirm: `Merge pull request #16 from feature/stage-4-2-2-transform-hierarchy` appears in develop history.

Then:
```bash
git checkout -b feature/stage-4-3-dialogue-lipsync
```

---

*Architecture plan prepared 2026-11-12. Subject to revision based on Stage 4.2.3 PR merge outcome and any Stage 4.2.3 fixes required after human review.*
