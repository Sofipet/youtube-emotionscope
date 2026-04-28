from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.contracts import ClassifiedComment
from app.pipelines.preprocess_pipeline import CleanedComment
from app.providers.openai_provider import (
    BatchCommentInput,
    BatchCommentOutput,
    OpenAIProvider,
    OpenAIProviderError,
    merge_comment_with_batch_output,
)
from app.settings import settings
from app.tracing import traceable


@dataclass
class EmotionPipelineResult:
    classified_comments: list[ClassifiedComment]
    warnings: list[str]
    stats: dict[str, int]


class EmotionPipelineError(Exception):
    pass


class EmotionPipeline:
    def __init__(
        self,
        openai_provider: Optional[OpenAIProvider] = None,
        *,
        batch_size: Optional[int] = None,
    ) -> None:
        self.openai_provider = openai_provider or OpenAIProvider()
        self.batch_size = batch_size or settings.classification_batch_size
    @traceable(run_type="tool", name="emotion_pipeline")
    def run(
        self,
        *,
        comments: list[CleanedComment],
        detected_language: Optional[str] = None,
    ) -> EmotionPipelineResult:
        if not comments:
            return EmotionPipelineResult(
                classified_comments=[],
                warnings=["too_few_comments"],
                stats={
                    "comments_input": 0,
                    "comments_classified": 0,
                    "classification_failures": 0,
                    "low_confidence_comments": 0,
                },
            )

        warnings: list[str] = []
        classified_comments: list[ClassifiedComment] = []
        classification_failures = 0
        low_confidence_comments = 0

        for batch in self._chunk_comments(comments, self.batch_size):
            batch_inputs = [
                BatchCommentInput(
                    local_id=comment.comment_id,
                    text=comment.text_clean,
                    detected_language=detected_language,
                )
                for comment in batch
            ]

            try:
                outputs = self.openai_provider.classify_comments_batch(comments=batch_inputs)
            except OpenAIProviderError:
                classification_failures += len(batch)
                continue
            except Exception as exc:
                raise EmotionPipelineError(
                    f"Unexpected emotion pipeline failure during batch classification: {exc}"
                ) from exc

            output_map: dict[str, BatchCommentOutput] = {item.local_id: item for item in outputs}

            for comment in batch:
                classification = output_map.get(comment.comment_id)
                if classification is None:
                    classification_failures += 1
                    continue

                merged = merge_comment_with_batch_output(
                    comment_id=comment.comment_id,
                    published_at=comment.published_at,
                    like_count=comment.like_count,
                    text_original=comment.text_original,
                    text_clean=comment.text_clean,
                    detected_language=detected_language,
                    classification=classification,
                )

                classified_comments.append(merged)

                if merged.confidence < 0.55:
                    low_confidence_comments += 1

        if not classified_comments:
            raise EmotionPipelineError("No comments could be classified successfully.")

        if len(classified_comments) < 20:
            warnings.append("too_few_comments")

        if low_confidence_comments / max(len(classified_comments), 1) >= 0.3:
            warnings.append("low_confidence_distribution")

        if classification_failures > 0:
            warnings.append("api_partial_data")

        stats = {
            "comments_input": len(comments),
            "comments_classified": len(classified_comments),
            "classification_failures": classification_failures,
            "low_confidence_comments": low_confidence_comments,
        }

        return EmotionPipelineResult(
            classified_comments=classified_comments,
            warnings=warnings,
            stats=stats,
        )

    @staticmethod
    def _chunk_comments(
        comments: list[CleanedComment],
        batch_size: int,
    ) -> list[list[CleanedComment]]:
        return [
            comments[i : i + batch_size]
            for i in range(0, len(comments), batch_size)
        ]


def classified_comments_to_dicts(
    comments: list[ClassifiedComment],
) -> list[dict]:
    return [comment.model_dump(mode="json") for comment in comments]