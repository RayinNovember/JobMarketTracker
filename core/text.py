"""Text helpers shared by projects: content hashing and keyword theme tagging."""

import hashlib
import re
from pathlib import Path

import yaml


_WS = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w\s]")


def normalize(text: str | None) -> str:
    """Lowercase, drop punctuation, collapse whitespace."""
    if not text:
        return ""
    return _WS.sub(" ", _NON_WORD.sub(" ", text.lower())).strip()


def content_hash(*parts: str | None) -> str:
    """Stable fingerprint of a record's content, used to spot reposts."""
    joined = "\x1f".join(normalize(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class ThemeTagger:
    """Tags text with themes whose signal phrases appear in it.

    themes.yaml format:
        - theme: Generative AI & LLMs
          phrases: [llm, large language model, rag, prompt engineering]
    Phrases match whole words, case-insensitively.
    """

    def __init__(self, themes: list[dict]):
        self.patterns = []
        for t in themes:
            alts = "|".join(re.escape(p.strip()) for p in t["phrases"] if p.strip())
            self.patterns.append((t["theme"], re.compile(rf"(?<!\w)(?:{alts})(?!\w)", re.I)))

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ThemeTagger":
        return cls(yaml.safe_load(Path(path).read_text()))

    def tag(self, text: str | None) -> list[str]:
        if not text:
            return []
        return [theme for theme, pat in self.patterns if pat.search(text)]