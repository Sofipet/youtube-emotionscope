from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.contracts import ClassifiedComment, PrimaryEmotion, Valence
from app.settings import settings
from app.tracing import get_openai_client, traceable


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class OpenAIProviderError(Exception):
    pass


def _normalize_optional_label(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    if normalized.lower() in {"null", "none", "n/a", "na"}:
        return None

    return normalized


class CommentClassificationResult(BaseModel):
    primary_emotion: PrimaryEmotion
    nuanced_emotion: Optional[str] = None
    emotion_intensity: float = Field(ge=0.0, le=1.0)
    valence: Valence
    confidence: float = Field(ge=0.0, le=1.0)


class BatchCommentInput(BaseModel):
    local_id: str
    text: str
    detected_language: Optional[str] = None


class BatchCommentOutput(BaseModel):
    local_id: str
    primary_emotion: PrimaryEmotion
    nuanced_emotion: Optional[str] = None
    emotion_intensity: float = Field(ge=0.0, le=1.0)
    valence: Valence
    confidence: float = Field(ge=0.0, le=1.0)


class BatchCommentClassificationResult(BaseModel):
    items: list[BatchCommentOutput]


class OpenAIProvider:
    def __init__(
        self,
        api_key: Optional[str] = None,
        classification_model: Optional[str] = None,
        description_model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.classification_model = classification_model or settings.classification_model
        self.description_model = description_model or settings.description_model

        if not self.api_key:
            raise OpenAIProviderError("OPENAI_API_KEY is not configured.")

        self.client = get_openai_client()

    def _read_prompt(self, filename: str) -> str:
        path = PROMPTS_DIR / filename
        if not path.exists():
            raise OpenAIProviderError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    @traceable(run_type="tool", name="classify_comments_batch")
    def classify_comments_batch(
        self,
        *,
        comments: list[BatchCommentInput],
    ) -> list[BatchCommentOutput]:
        if not comments:
            return []

        system_prompt = self._read_prompt("classify_comment_batch.txt")

        payload = {
            "comments": [
                {
                    "local_id": item.local_id,
                    "text": item.text,
                    "detected_language": item.detected_language or "unknown",
                }
                for item in comments
            ]
        }

        try:
            response = self.client.responses.parse(
                model=self.classification_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False, indent=2),
                    },
                ],
                text_format=BatchCommentClassificationResult,
            )
            parsed = response.output_parsed
            if parsed is None:
                raise OpenAIProviderError("Batch classification response could not be parsed.")

            normalized_items: list[BatchCommentOutput] = []
            for item in parsed.items:
                normalized_items.append(
                    BatchCommentOutput(
                        local_id=item.local_id,
                        primary_emotion=item.primary_emotion,
                        nuanced_emotion=_normalize_optional_label(item.nuanced_emotion),
                        emotion_intensity=item.emotion_intensity,
                        valence=item.valence,
                        confidence=item.confidence,
                    )
                )

            return normalized_items

        except Exception as exc:
            raise OpenAIProviderError(f"OpenAI batch classification failed: {exc}") from exc

    @traceable(run_type="tool", name="generate_description")
    def generate_description(
        self,
        *,
        video_title: str,
        comments_analyzed: int,
        top_primary_emotions: list[dict],
        top_nuanced_emotions: list[dict],
        valence: dict,
        warnings: list[str],
        representative_comments: list[dict],
    ) -> str:
        system_prompt = self._read_prompt("describe_video.txt")

        user_payload = {
            "video_title": video_title,
            "comments_analyzed": comments_analyzed,
            "top_primary_emotions": top_primary_emotions,
            "top_nuanced_emotions": top_nuanced_emotions,
            "valence": valence,
            "warnings": warnings,
            "representative_comments": representative_comments[:8],
        }

        try:
            response = self.client.responses.create(
                model=self.description_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
                    },
                ],
            )

            text = response.output_text.strip()
            if not text:
                raise OpenAIProviderError("Description response was empty.")

            return text

        except Exception as exc:
            raise OpenAIProviderError(f"OpenAI description generation failed: {exc}") from exc


def merge_comment_with_batch_output(
    *,
    comment_id: str,
    published_at: str,
    like_count: int,
    text_original: str,
    text_clean: str,
    detected_language: Optional[str],
    classification: BatchCommentOutput,
) -> ClassifiedComment:
    return ClassifiedComment(
        comment_id=comment_id,
        published_at=published_at,
        like_count=like_count,
        text_original=text_original,
        text_clean=text_clean,
        detected_language=detected_language,
        primary_emotion=classification.primary_emotion,
        nuanced_emotion=_normalize_optional_label(classification.nuanced_emotion),
        emotion_intensity=classification.emotion_intensity,
        valence=classification.valence,
        confidence=classification.confidence,
    )