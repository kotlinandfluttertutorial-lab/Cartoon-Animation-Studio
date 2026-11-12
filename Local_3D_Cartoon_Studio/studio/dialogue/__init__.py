"""
studio/dialogue/__init__.py
Dialogue, Lip-Sync and Expression System — Stage 4.3

Exports the public API for the dialogue subsystem.
"""
from studio.dialogue.phoneme_mapper import PhonemeMapper, text_to_viseme_sequence
from studio.dialogue.mouth_shapes import MouthShapes
from studio.dialogue.lipsync_generator import LipsyncGenerator, LipsyncData, generate_lipsync, save_lipsync, load_lipsync
from studio.dialogue.expression_library import ExpressionLibrary, EXPRESSIONS, apply_expression, restore_expression
from studio.dialogue.dialogue_sequencer import DialogueSequencer, DialogueLine
from studio.dialogue.conversation_scene import ConversationScene

__all__ = [
    "PhonemeMapper",
    "text_to_viseme_sequence",
    "MouthShapes",
    "LipsyncGenerator",
    "LipsyncData",
    "generate_lipsync",
    "save_lipsync",
    "load_lipsync",
    "ExpressionLibrary",
    "EXPRESSIONS",
    "apply_expression",
    "restore_expression",
    "DialogueSequencer",
    "DialogueLine",
    "ConversationScene",
]
