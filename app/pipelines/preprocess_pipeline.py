from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Optional

from app.providers.youtube_provider import RawComment
from app.settings import settings
from app.tracing import traceable

URL_ONLY_RE = re.compile(r"^(https?://\S+)$", re.IGNORECASE)
PUNCT_ONLY_RE = re.compile(r"^[\.\,\!\?\-\_\=\+\~\*]+$")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class CleanedComment:
    comment_id: str
    published_at: str
    like_count: int
    reply_count: int
    text_original: str
    text_clean: str
    author_display_name: Optional[str] = None


@dataclass
class PreprocessPipelineResult:
    cleaned_comments: list[CleanedComment]
    sampled_comments: list[CleanedComment]
    warnings: list[str]
    stats: dict[str, int]


class PreprocessPipelineError(Exception):
    pass


class PreprocessPipeline:
    def __init__(
        self,
        *,
        sample_size: Optional[int] = None,
        random_seed: Optional[int] = None,
        min_text_length: Optional[int] = None,
        deduplicate_comments: Optional[bool] = None,
    ) -> None:
        self.sample_size = sample_size or settings.sample_size
        self.random_seed = random_seed if random_seed is not None else settings.random_seed
        self.min_text_length = min_text_length or settings.min_text_length
        self.deduplicate_comments = (
            settings.deduplicate_comments
            if deduplicate_comments is None
            else deduplicate_comments
        )
    @traceable(run_type="tool", name="preprocess_pipeline")
    def run(self, comments: list[RawComment]) -> PreprocessPipelineResult:
        if not comments:
            return PreprocessPipelineResult(
                cleaned_comments=[],
                sampled_comments=[],
                warnings=["too_few_comments"],
                stats={
                    "raw_comments": 0,
                    "after_cleaning": 0,
                    "sampled_comments": 0,
                    "removed_empty": 0,
                    "removed_low_value": 0,
                    "removed_duplicates": 0,
                },
            )

        removed_empty = 0
        removed_low_value = 0
        removed_duplicates = 0

        cleaned_comments: list[CleanedComment] = []
        seen_texts: set[str] = set()

        for comment in comments:
            text_clean = self._normalize_text(comment.text_original)

            if not text_clean:
                removed_empty += 1
                continue

            if self._should_drop_low_value(text_clean):
                removed_low_value += 1
                continue

            dedup_key = self._dedup_key(text_clean)

            if self.deduplicate_comments and dedup_key in seen_texts:
                removed_duplicates += 1
                continue

            seen_texts.add(dedup_key)

            cleaned_comments.append(
                CleanedComment(
                    comment_id=comment.comment_id,
                    published_at=comment.published_at,
                    like_count=comment.like_count,
                    reply_count=comment.reply_count,
                    text_original=comment.text_original,
                    text_clean=text_clean,
                    author_display_name=comment.author_display_name,
                )
            )

        warnings: list[str] = []
        if len(cleaned_comments) < 20:
            warnings.append("too_few_comments")

        sampled_comments = self._sample_comments(cleaned_comments)

        if len(sampled_comments) < 10 and "too_few_comments" not in warnings:
            warnings.append("too_few_comments")

        stats = {
            "raw_comments": len(comments),
            "after_cleaning": len(cleaned_comments),
            "sampled_comments": len(sampled_comments),
            "removed_empty": removed_empty,
            "removed_low_value": removed_low_value,
            "removed_duplicates": removed_duplicates,
        }

        return PreprocessPipelineResult(
            cleaned_comments=cleaned_comments,
            sampled_comments=sampled_comments,
            warnings=warnings,
            stats=stats,
        )

    def _sample_comments(self, comments: list[CleanedComment]) -> list[CleanedComment]:
        if len(comments) <= self.sample_size:
            return sorted(comments, key=lambda c: c.published_at)

        rng = random.Random(self.random_seed)

        sorted_by_engagement = sorted(
            comments,
            key=lambda c: (c.like_count, c.reply_count),
            reverse=True,
        )

        top_pool_size = max(self.sample_size, len(comments) // 3)
        top_pool = sorted_by_engagement[:top_pool_size]

        n_top = self.sample_size // 2
        n_random = self.sample_size - n_top

        top_sample = rng.sample(top_pool, k=min(n_top, len(top_pool)))

        selected_ids = {c.comment_id for c in top_sample}
        remaining_pool = [c for c in comments if c.comment_id not in selected_ids]

        if len(remaining_pool) <= n_random:
            random_sample = remaining_pool
        else:
            random_sample = rng.sample(remaining_pool, k=n_random)

        sampled = top_sample + random_sample
        sampled = sorted(sampled, key=lambda c: c.published_at)
        return sampled

    def _should_drop_low_value(self, text: str) -> bool:
        stripped = text.strip()

        if not stripped:
            return True

        if URL_ONLY_RE.fullmatch(stripped):
            return True

        if PUNCT_ONLY_RE.fullmatch(stripped):
            return True

        if len(stripped) < self.min_text_length:
            return True

        return False

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.strip()
        text = WHITESPACE_RE.sub(" ", text)
        return text

    @staticmethod
    def _dedup_key(text: str) -> str:
        lowered = text.lower().strip()
        lowered = WHITESPACE_RE.sub(" ", lowered)
        return lowered


def cleaned_comments_to_dicts(comments: list[CleanedComment]) -> list[dict]:
    return [
        {
            "comment_id": c.comment_id,
            "published_at": c.published_at,
            "like_count": c.like_count,
            "reply_count": c.reply_count,
            "text_original": c.text_original,
            "text_clean": c.text_clean,
            "author_display_name": c.author_display_name,
        }
        for c in comments
    ]