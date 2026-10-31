"""Application answer preparation; official scoring rules remain untouched."""
from __future__ import annotations

import re

# Evidence references are bracketed E labels, singly or comma/semicolon/space grouped.
# Factual numbers (including ordinary bracketed numbers) are never citation labels.
_CITATION = re.compile(r"\[\s*E\d+(?:(?:\s*[,;]\s*|\s+)E\d+)*\s*\]")


def answer_content(answer: str) -> str:
    return _CITATION.sub("", answer).strip()


def has_answer_content(answer) -> bool:
    """Punctuation surviving citation removal does not constitute an answer."""
    return isinstance(answer, str) and any(char.isalnum() for char in answer_content(answer))
