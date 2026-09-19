"""_arabic_placeholders.py — shield inline Arabic from a model that rewrites the prose around it.

A model cannot reliably copy script it can SEE: on isaf-al-talib (bk-28) the translation model dropped
`⟪ar:…⟫` Qur'an spans three times in a row, and the retry prompt could only name the words. Swapping each
span for a `[[ARn]]` token BEFORE the call and restoring the exact source span AFTER makes the quotation
survive letter for letter, because the model never had the script to alter. The retention gate stays
strict; this only stops giving the model something it will break.

One implementation for every prose-rewriting route (translation, fluency, voice, Composer rearticulate,
which run the same gate), replacing the private copy that lived in `_translation_chunk`.
"""

from __future__ import annotations

import re

_SPAN_RE = re.compile("⟪(?:ar):[^⟫]+⟫")
_TOKEN_RE = re.compile(r"\[\[AR(\d+)\]\]")
_TOKEN_NOTE = (
    "\n\nARABIC PLACEHOLDERS: each token like [[AR1]] in the source stands for a protected Arabic "
    "quotation. Copy every token into your prose exactly once, unchanged, at the point where the "
    "quotation belongs. Never translate, expand, drop or renumber a token."
)


class ArabicPlaceholders:
    """One rewrite's span table: protect the input, restore the output, and say so in the prompt."""

    def __init__(self) -> None:
        self.table: dict[str, str] = {}

    def protect(self, body: str) -> str:
        def _swap(m: re.Match[str]) -> str:
            key = f"[[AR{len(self.table) + 1}]]"
            self.table[key] = m.group(0)
            return key

        return _SPAN_RE.sub(_swap, body)

    def restore(self, text: str) -> str:
        """Put the exact source spans back. A token the model dropped stays absent (the retention gate sees
        it); one it invented is left visible, never guessed at."""
        return _TOKEN_RE.sub(lambda m: self.table.get(m.group(0), m.group(0)), text)

    @property
    def note(self) -> str:
        """The prompt suffix explaining the tokens — empty when there is nothing to protect."""
        return _TOKEN_NOTE if self.table else ""
