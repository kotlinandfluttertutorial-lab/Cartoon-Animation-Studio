"""
studio/dialogue/phoneme_mapper.py
Maps English text → 7-viseme cartoon groups.

Approach: lightweight bundled dictionary of common words, with rule-based
fallback for unknown words.  No NLTK or external dependencies required.

Viseme groups (ARPABET-based):
    REST  — silence, punctuation pauses
    MBP   — M, B, P  (lips together)
    FV    — F, V      (teeth on lip)
    TD    — T, D, N, L, S, Z  (tongue tip)
    WQ    — W, R, OW, UW      (rounded)
    OPEN  — AA, AH, AO, AE    (open jaw)
    EI    — EH, IH, IY, AY    (spread lips)
"""
from __future__ import annotations

import re
import string
from typing import List, Tuple

# ---------------------------------------------------------------------------
# ARPABET phoneme → viseme mapping
# ---------------------------------------------------------------------------
_ARPABET_TO_VISEME: dict[str, str] = {
    # Silence / pause
    "SIL":  "REST",
    "SP":   "REST",
    # Bilabials — lips together
    "M":    "MBP",
    "B":    "MBP",
    "P":    "MBP",
    # Labiodentals — teeth on lip
    "F":    "FV",
    "V":    "FV",
    # Tongue tip — alveolar/dental
    "T":    "TD",
    "D":    "TD",
    "N":    "TD",
    "L":    "TD",
    "S":    "TD",
    "Z":    "TD",
    "TH":   "TD",
    "DH":   "TD",
    # Rounded lips
    "W":    "WQ",
    "R":    "WQ",
    "OW":   "WQ",
    "UW":   "WQ",
    "UH":   "WQ",
    "OY":   "WQ",
    "AW":   "WQ",
    # Open jaw
    "AA":   "OPEN",
    "AH":   "OPEN",
    "AO":   "OPEN",
    "AE":   "OPEN",
    # Spread lips
    "EH":   "EI",
    "IH":   "EI",
    "IY":   "EI",
    "AY":   "EI",
    "EY":   "EI",
    "ER":   "EI",
    # Velars / other consonants — approximate
    "K":    "TD",
    "G":    "TD",
    "NG":   "TD",
    "CH":   "TD",
    "JH":   "TD",
    "SH":   "TD",
    "ZH":   "TD",
    "HH":   "OPEN",
    "Y":    "EI",
}

# ---------------------------------------------------------------------------
# Common English word → phoneme sequence (abbreviated ARPABET)
# This covers the most frequent words so pronunciation is accurate.
# ---------------------------------------------------------------------------
_WORD_PHONEMES: dict[str, list[str]] = {
    "a":        ["AH"],
    "about":    ["AH", "B", "AW", "T"],
    "after":    ["AE", "F", "T", "ER"],
    "am":       ["AE", "M"],
    "and":      ["AE", "N", "D"],
    "are":      ["AA", "R"],
    "at":       ["AE", "T"],
    "be":       ["B", "IY"],
    "big":      ["B", "IH", "G"],
    "but":      ["B", "AH", "T"],
    "by":       ["B", "AY"],
    "can":      ["K", "AE", "N"],
    "come":     ["K", "AH", "M"],
    "day":      ["D", "EY"],
    "do":       ["D", "UW"],
    "for":      ["F", "AO", "R"],
    "from":     ["F", "R", "AH", "M"],
    "get":      ["G", "EH", "T"],
    "go":       ["G", "OW"],
    "good":     ["G", "UH", "D"],
    "great":    ["G", "R", "EY", "T"],
    "had":      ["HH", "AE", "D"],
    "has":      ["HH", "AE", "Z"],
    "have":     ["HH", "AE", "V"],
    "he":       ["HH", "IY"],
    "hello":    ["HH", "EH", "L", "OW"],
    "here":     ["HH", "IH", "R"],
    "hi":       ["HH", "AY"],
    "his":      ["HH", "IH", "Z"],
    "how":      ["HH", "AW"],
    "i":        ["AY"],
    "if":       ["IH", "F"],
    "in":       ["IH", "N"],
    "is":       ["IH", "Z"],
    "it":       ["IH", "T"],
    "just":     ["JH", "AH", "S", "T"],
    "know":     ["N", "OW"],
    "let":      ["L", "EH", "T"],
    "like":     ["L", "AY", "K"],
    "look":     ["L", "UH", "K"],
    "love":     ["L", "AH", "V"],
    "make":     ["M", "EY", "K"],
    "me":       ["M", "IY"],
    "more":     ["M", "AO", "R"],
    "my":       ["M", "AY"],
    "name":     ["N", "EY", "M"],
    "new":      ["N", "UW"],
    "no":       ["N", "OW"],
    "not":      ["N", "AA", "T"],
    "now":      ["N", "AW"],
    "of":       ["AH", "V"],
    "oh":       ["OW"],
    "on":       ["AO", "N"],
    "one":      ["W", "AH", "N"],
    "or":       ["AO", "R"],
    "our":      ["AW", "ER"],
    "out":      ["AW", "T"],
    "say":      ["S", "EY"],
    "see":      ["S", "IY"],
    "she":      ["SH", "IY"],
    "so":       ["S", "OW"],
    "some":     ["S", "AH", "M"],
    "that":     ["DH", "AE", "T"],
    "the":      ["DH", "AH"],
    "their":    ["DH", "EH", "R"],
    "them":     ["DH", "EH", "M"],
    "then":     ["DH", "EH", "N"],
    "there":    ["DH", "EH", "R"],
    "they":     ["DH", "EY"],
    "this":     ["DH", "IH", "S"],
    "time":     ["T", "AY", "M"],
    "to":       ["T", "UW"],
    "today":    ["T", "AH", "D", "EY"],
    "up":       ["AH", "P"],
    "us":       ["AH", "S"],
    "very":     ["V", "EH", "R", "IY"],
    "was":      ["W", "AH", "Z"],
    "we":       ["W", "IY"],
    "well":     ["W", "EH", "L"],
    "what":     ["W", "AH", "T"],
    "when":     ["W", "EH", "N"],
    "where":    ["W", "EH", "R"],
    "which":    ["W", "IH", "CH"],
    "who":      ["HH", "UW"],
    "will":     ["W", "IH", "L"],
    "with":     ["W", "IH", "DH"],
    "would":    ["W", "UH", "D"],
    "yes":      ["Y", "EH", "S"],
    "you":      ["Y", "UW"],
    "your":     ["Y", "AO", "R"],
    # Common names
    "aarav":    ["AA", "R", "AH", "V"],
    "aanya":    ["AA", "N", "Y", "AH"],
    # Additional common words for coverage
    "animation": ["AE", "N", "AH", "M", "EY", "SH", "AH", "N"],
    "cartoon":   ["K", "AA", "R", "T", "UW", "N"],
    "happy":     ["HH", "AE", "P", "IY"],
    "play":      ["P", "L", "EY"],
    "run":       ["R", "AH", "N"],
    "stop":      ["S", "T", "AA", "P"],
    "walk":      ["W", "AO", "K"],
    "talk":      ["T", "AO", "K"],
    "listen":    ["L", "IH", "S", "AH", "N"],
    "think":     ["TH", "IH", "NG", "K"],
    "wait":      ["W", "EY", "T"],
    "help":      ["HH", "EH", "L", "P"],
    "please":    ["P", "L", "IY", "Z"],
    "thank":     ["TH", "AE", "NG", "K"],
    "thanks":    ["TH", "AE", "NG", "K", "S"],
    "ready":     ["R", "EH", "D", "IY"],
    "start":     ["S", "T", "AA", "R", "T"],
    "going":     ["G", "OW", "IH", "NG"],
    "come":      ["K", "AH", "M"],
}

# ---------------------------------------------------------------------------
# Vowel / consonant classification for rule-based fallback
# ---------------------------------------------------------------------------
_VOWELS = frozenset("aeiou")

# Simple consonant→phoneme mapping for rule-based approximation
_CONSONANT_PHONEME: dict[str, str] = {
    "b": "B", "c": "K", "d": "D", "f": "F", "g": "G",
    "h": "HH", "j": "JH", "k": "K", "l": "L", "m": "M",
    "n": "N", "p": "P", "q": "K", "r": "R", "s": "S",
    "t": "T", "v": "V", "w": "W", "x": "K", "y": "Y",
    "z": "Z",
}
_VOWEL_PHONEME: dict[str, str] = {
    "a": "AE", "e": "EH", "i": "IH", "o": "AO", "u": "AH",
}

# Double-letter digraphs handled by rule-based
_DIGRAPHS: dict[str, str] = {
    "ch": "CH", "sh": "SH", "th": "TH", "ph": "F",
    "ck": "K", "ng": "NG", "wh": "W", "gh": "HH",
    "oo": "UW", "ee": "IY", "ea": "IY", "ai": "EY",
    "oa": "OW", "ou": "AW", "ow": "OW", "oi": "OY",
    "au": "AO", "aw": "AO", "ew": "UW", "ie": "IY",
    "ei": "EY", "qu": "K",
}


def _rule_based_phonemes(word: str) -> list[str]:
    """
    Approximate ARPABET phonemes from spelling using simple letter rules.
    This handles unknown words without any external library.
    """
    phonemes: list[str] = []
    w = word.lower()
    i = 0
    while i < len(w):
        # Try digraph first
        if i + 1 < len(w):
            digraph = w[i:i + 2]
            if digraph in _DIGRAPHS:
                phonemes.append(_DIGRAPHS[digraph])
                i += 2
                continue
        ch = w[i]
        if ch in _VOWEL_PHONEME:
            phonemes.append(_VOWEL_PHONEME[ch])
        elif ch in _CONSONANT_PHONEME:
            phonemes.append(_CONSONANT_PHONEME[ch])
        # skip unknown chars (apostrophes, hyphens, etc.)
        i += 1
    return phonemes if phonemes else ["AH"]  # fallback: schwa


def _word_to_phonemes(word: str) -> list[str]:
    """Return ARPABET phoneme list for a single word."""
    key = word.lower().strip(string.punctuation)
    if key in _WORD_PHONEMES:
        return _WORD_PHONEMES[key]
    return _rule_based_phonemes(key)


def _phonemes_to_visemes(phonemes: list[str]) -> list[str]:
    """Map ARPABET phoneme list to viseme list."""
    return [_ARPABET_TO_VISEME.get(p, "OPEN") for p in phonemes]


class PhonemeMapper:
    """
    Stateless helper that maps English text to viseme sequences.

    All public methods are classmethods so the class can be used without
    instantiation, matching the usage in LipsyncGenerator.
    """

    VISEMES = ("REST", "MBP", "FV", "TD", "WQ", "OPEN", "EI")

    @classmethod
    def text_to_phonemes(cls, text: str) -> list[str]:
        """Return flat ARPABET phoneme list for the given text."""
        words = re.split(r"[\s]+", text.strip())
        result: list[str] = []
        for word in words:
            if not word:
                continue
            result.extend(_word_to_phonemes(word))
        return result

    @classmethod
    def phonemes_to_visemes(cls, phonemes: list[str]) -> list[str]:
        """Map phoneme list to viseme list."""
        return _phonemes_to_visemes(phonemes)

    @classmethod
    def text_to_viseme_list(cls, text: str) -> list[str]:
        """Return flat viseme list for the given text."""
        return cls.phonemes_to_visemes(cls.text_to_phonemes(text))


def text_to_viseme_sequence(
    text: str,
    duration_s: float,
    fps: int = 24,
) -> list[tuple[int, str]]:
    """
    Map English text to a timed viseme sequence.

    Distributes visemes evenly across the given duration with a REST frame
    at the beginning (frame 1) and after the last speech phoneme.

    Parameters
    ----------
    text        : English sentence(s) to map
    duration_s  : total speech duration in seconds
    fps         : frames per second (default 24)

    Returns
    -------
    List of (frame_number, viseme_name) tuples sorted by frame, 1-indexed.
    """
    if not text or not text.strip():
        total = max(1, int(duration_s * fps))
        return [(1, "REST"), (total, "REST")]

    visemes = PhonemeMapper.text_to_viseme_list(text)
    if not visemes:
        total = max(1, int(duration_s * fps))
        return [(1, "REST"), (total, "REST")]

    total_frames = max(1, int(duration_s * fps))

    # Reserve first and last frame for REST (pre/post speech)
    speech_frames = max(1, total_frames - 2)
    n = len(visemes)

    result: list[tuple[int, str]] = [(1, "REST")]

    for idx, viseme in enumerate(visemes):
        # Distribute evenly in [2, total_frames - 1]
        frame = 2 + int(idx * speech_frames / n)
        frame = max(2, min(frame, total_frames - 1))
        result.append((frame, viseme))

    # Deduplicate consecutive duplicate frames (keep first)
    seen: dict[int, str] = {}
    for frame, viseme in result:
        if frame not in seen:
            seen[frame] = viseme

    # Append terminal REST
    seen[total_frames] = "REST"

    return sorted(seen.items())
