from __future__ import annotations

from collections import Counter
from typing import Iterable

from langdetect import DetectorFactory, LangDetectException, detect

from app.contracts import LanguageShare

DetectorFactory.seed = 0

LANGUAGE_LABELS = {
    "en": "English",
    "uk": "Ukrainian",
    "ru": "Russian",
    "de": "German",
    "tr": "Turkish",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pl": "Polish",
    "nl": "Dutch",
    "ar": "Arabic",
}

MIN_CHARS = 15
MIN_WORDS = 3
MIN_SHARE_TO_KEEP = 0.05
MAX_ITEMS = 300
TOP_K = 5


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _is_language_candidate(text: str) -> bool:
    if not text:
        return False

    stripped = _normalize_text(text)
    if len(stripped) < MIN_CHARS:
        return False

    words = [w for w in stripped.split() if any(ch.isalpha() for ch in w)]
    if len(words) < MIN_WORDS:
        return False

    alpha_chars = sum(ch.isalpha() for ch in stripped)
    return alpha_chars >= 10


def compute_language_distribution(
    texts: Iterable[str],
    *,
    max_items: int = MAX_ITEMS,
    top_k: int = TOP_K,
) -> list[LanguageShare]:
    counts: Counter[str] = Counter()
    valid_count = 0

    for text in list(texts)[:max_items]:
        normalized = _normalize_text(text)

        if not _is_language_candidate(normalized):
            continue

        try:
            code = detect(normalized)
        except LangDetectException:
            continue
        except Exception:
            continue

        counts[code] += 1
        valid_count += 1

    if valid_count == 0:
        return []

    kept: list[tuple[str, int]] = []
    other_count = 0

    for code, count in counts.most_common(top_k):
        share = count / valid_count
        if share >= MIN_SHARE_TO_KEEP:
            kept.append((code, count))
        else:
            other_count += count

    remaining_count = sum(count for _, count in counts.items()) - sum(count for _, count in kept) - other_count
    other_count += max(remaining_count, 0)

    result: list[LanguageShare] = []

    for code, count in kept:
        result.append(
            LanguageShare(
                language_code=code,
                language_label=LANGUAGE_LABELS.get(code, code.upper()),
                share=round(count / valid_count, 4),
            )
        )

    if other_count > 0:
        result.append(
            LanguageShare(
                language_code="other",
                language_label="Other",
                share=round(other_count / valid_count, 4),
            )
        )

    return result