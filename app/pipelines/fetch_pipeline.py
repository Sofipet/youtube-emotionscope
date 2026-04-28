from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.providers.youtube_provider import (
    RawComment,
    RawVideoMetadata,
    YouTubeProvider,
    YouTubeProviderError,
    comments_to_dicts,
)
from app.settings import settings
from app.tracing import traceable


@dataclass
class FetchPipelineResult:
    video: RawVideoMetadata
    comments: list[RawComment]
    warnings: list[str]
    stats: dict[str, int | bool | str]


class FetchPipelineError(Exception):
    pass


class FetchPipeline:
    def __init__(self, youtube_provider: Optional[YouTubeProvider] = None) -> None:
        self.youtube_provider = youtube_provider or YouTubeProvider()
    @traceable(run_type="tool", name="fetch_pipeline")
    def run(
        self,
        *,
        video_url: str,
        fetch_all_comments: Optional[bool] = None,
        max_comments: Optional[int] = None,
        order: Optional[str] = None,
    ) -> FetchPipelineResult:
        fetch_all = settings.fetch_all_comments if fetch_all_comments is None else fetch_all_comments
        max_comments_value = max_comments or settings.max_comments_to_fetch
        order_value = order or settings.youtube_comment_order

        try:
            video, comments = self.youtube_provider.fetch_video_and_comments(
                video_url=video_url,
                fetch_all_comments=fetch_all,
                max_comments=max_comments_value,
                order=order_value,
            )
        except YouTubeProviderError as exc:
            raise FetchPipelineError(str(exc)) from exc
        except Exception as exc:
            raise FetchPipelineError(f"Unexpected fetch pipeline failure: {exc}") from exc

        warnings = self._build_warnings(
            comments=comments,
            fetch_all_comments=fetch_all,
            max_comments=max_comments_value,
        )

        stats = {
            "comments_fetched": len(comments),
            "fetch_all_comments": fetch_all,
            "max_comments_requested": max_comments_value,
            "order": order_value,
        }

        return FetchPipelineResult(
            video=video,
            comments=comments,
            warnings=warnings,
            stats=stats,
        )

    def _build_warnings(
        self,
        *,
        comments: list[RawComment],
        fetch_all_comments: bool,
        max_comments: int,
    ) -> list[str]:
        warnings: list[str] = []

        if len(comments) == 0:
            warnings.append("too_few_comments")
            return warnings

        if len(comments) < 20:
            warnings.append("too_few_comments")

        # If we did not fetch all comments and exactly hit the limit,
        # the result may be truncated relative to the full available pool.
        if not fetch_all_comments and len(comments) >= max_comments:
            warnings.append("api_partial_data")

        # Very low diversity in comment text can be a hint of weak fetch quality or repetitive data.
        unique_texts = {
            comment.text_original.strip().lower()
            for comment in comments
            if comment.text_original.strip()
        }

        if len(unique_texts) <= max(3, int(len(comments) * 0.35)):
            if "api_partial_data" not in warnings:
                warnings.append("api_partial_data")

        return warnings


def fetch_pipeline_to_dict(result: FetchPipelineResult) -> dict:
    return {
        "video": {
            "video_id": result.video.video_id,
            "video_url": result.video.video_url,
            "title": result.video.title,
            "channel_title": result.video.channel_title,
            "published_at": result.video.published_at,
        },
        "comments": comments_to_dicts(result.comments),
        "warnings": result.warnings,
        "stats": result.stats,
    }