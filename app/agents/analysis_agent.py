from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.contracts import (
    AnalysisWarning,
    AnalyzeVideoRequest,
    VideoAnalysisResponse,
    VideoBlock,
)
from app.language_utils import compute_language_distribution
from app.pipelines.aggregation_pipeline import AggregationPipeline
from app.pipelines.description_pipeline import DescriptionPipeline
from app.pipelines.emotion_pipeline import EmotionPipeline, classified_comments_to_dicts
from app.pipelines.fetch_pipeline import FetchPipeline, fetch_pipeline_to_dict
from app.pipelines.preprocess_pipeline import PreprocessPipeline, cleaned_comments_to_dicts
from app.settings import settings
from app.storage.cache import FileCache
from app.tracing import traceable


@dataclass
class AnalysisAgentConfig:
    fetch_all_comments: bool
    max_comments_to_fetch: int
    sample_size: int
    classification_batch_size: int
    top_primary_emotions_limit: int
    top_nuanced_emotions_limit: int
    representative_comments_limit: int


class AnalysisAgentError(Exception):
    pass


class AnalysisAgent:
    def __init__(
        self,
        *,
        fetch_pipeline: Optional[FetchPipeline] = None,
        preprocess_pipeline: Optional[PreprocessPipeline] = None,
        emotion_pipeline: Optional[EmotionPipeline] = None,
        aggregation_pipeline: Optional[AggregationPipeline] = None,
        description_pipeline: Optional[DescriptionPipeline] = None,
        file_cache: Optional[FileCache] = None,
        config: Optional[AnalysisAgentConfig] = None,
    ) -> None:
        self.fetch_pipeline = fetch_pipeline or FetchPipeline()
        self.preprocess_pipeline = preprocess_pipeline or PreprocessPipeline(
            sample_size=settings.sample_size,
            random_seed=settings.random_seed,
            min_text_length=settings.min_text_length,
            deduplicate_comments=settings.deduplicate_comments,
        )
        self.emotion_pipeline = emotion_pipeline or EmotionPipeline(
            batch_size=settings.classification_batch_size,
        )
        self.aggregation_pipeline = aggregation_pipeline or AggregationPipeline(
            top_primary_emotions_limit=settings.top_primary_emotions_limit,
            top_nuanced_emotions_limit=settings.top_nuanced_emotions_limit,
            representative_comments_limit=settings.representative_comments_limit,
            min_nuanced_emotion_frequency=settings.min_nuanced_emotion_frequency,
        )
        self.description_pipeline = description_pipeline or DescriptionPipeline()
        self.file_cache = file_cache or FileCache()

        self.config = config or AnalysisAgentConfig(
            fetch_all_comments=settings.fetch_all_comments,
            max_comments_to_fetch=settings.max_comments_to_fetch,
            sample_size=settings.sample_size,
            classification_batch_size=settings.classification_batch_size,
            top_primary_emotions_limit=settings.top_primary_emotions_limit,
            top_nuanced_emotions_limit=settings.top_nuanced_emotions_limit,
            representative_comments_limit=settings.representative_comments_limit,
        )

    @traceable(run_type="chain", name="analyze_video")
    def run(self, request: AnalyzeVideoRequest) -> VideoAnalysisResponse:
        try:
            video_url = str(request.video_url)
            video_id = self.fetch_pipeline.youtube_provider.parse_video_id(video_url)

            analysis_cache_key = self.file_cache.build_analysis_cache_key(
                video_id=video_id,
                classification_model=settings.classification_model,
                description_model=settings.description_model,
                sample_size=self.config.sample_size,
                batch_size=self.config.classification_batch_size,
                top_primary_limit=self.config.top_primary_emotions_limit,
                top_nuanced_limit=self.config.top_nuanced_emotions_limit,
                timeline_bucket_count=0,
                version_tag="v2_date_timeline",
            )

            cached_analysis = self.file_cache.load_analysis(cache_key=analysis_cache_key)
            if cached_analysis is not None:
                payload = cached_analysis.get("payload", cached_analysis)
                payload = self._ensure_languages_in_payload(
                    video_id=video_id,
                    analysis_cache_key=analysis_cache_key,
                    payload=payload,
                )
                return VideoAnalysisResponse.model_validate(payload)

            raw_fetch_cache = self.file_cache.load_raw_fetch(video_id=video_id)

            if raw_fetch_cache is not None:
                raw_payload = raw_fetch_cache.get("payload", raw_fetch_cache)
                fetch_dict = raw_payload
            else:
                fetch_result = self.fetch_pipeline.run(
                    video_url=video_url,
                    fetch_all_comments=self.config.fetch_all_comments,
                    max_comments=self.config.max_comments_to_fetch,
                )
                fetch_dict = fetch_pipeline_to_dict(fetch_result)

                if settings.use_cache:
                    self.file_cache.save_raw_fetch(video_id=video_id, payload=fetch_dict)

                if settings.save_artifacts:
                    self.file_cache.save_artifact(
                        artifact_type="raw",
                        name=video_id,
                        payload=fetch_dict,
                    )

            raw_comments = self._raw_comments_from_fetch_payload(fetch_dict)

            preprocess_result = self.preprocess_pipeline.run(raw_comments)

            if settings.save_artifacts:
                self.file_cache.save_artifact(
                    artifact_type="cleaned",
                    name=video_id,
                    payload={
                        "warnings": preprocess_result.warnings,
                        "stats": preprocess_result.stats,
                        "comments": cleaned_comments_to_dicts(preprocess_result.cleaned_comments),
                    },
                )
                self.file_cache.save_artifact(
                    artifact_type="sampled",
                    name=video_id,
                    payload={
                        "warnings": preprocess_result.warnings,
                        "stats": preprocess_result.stats,
                        "comments": cleaned_comments_to_dicts(preprocess_result.sampled_comments),
                    },
                )

            emotion_result = self.emotion_pipeline.run(
                comments=preprocess_result.sampled_comments,
                detected_language=None,
            )

            if settings.save_artifacts:
                self.file_cache.save_artifact(
                    artifact_type="classified",
                    name=video_id,
                    payload={
                        "warnings": emotion_result.warnings,
                        "stats": emotion_result.stats,
                        "comments": classified_comments_to_dicts(emotion_result.classified_comments),
                    },
                )

            aggregation_result = self.aggregation_pipeline.run(
                classified_comments=emotion_result.classified_comments
            )

            combined_warning_strings = list(
                dict.fromkeys(
                    fetch_dict.get("warnings", [])
                    + preprocess_result.warnings
                    + emotion_result.warnings
                    + aggregation_result.warnings
                )
            )

            description_result = self.description_pipeline.run(
                video_title=fetch_dict["video"]["title"],
                comments_analyzed=len(emotion_result.classified_comments),
                top_primary_emotions=aggregation_result.top_primary_emotions,
                top_nuanced_emotions=aggregation_result.top_nuanced_emotions,
                valence=aggregation_result.valence,
                warnings=combined_warning_strings,
                representative_comments=aggregation_result.representative_comments,
            )

            languages = self._extract_languages_from_fetch_payload(fetch_dict)

            final_response = VideoAnalysisResponse(
                video=VideoBlock(
                    video_id=fetch_dict["video"]["video_id"],
                    video_url=fetch_dict["video"]["video_url"],
                    title=fetch_dict["video"]["title"],
                    channel_title=fetch_dict["video"].get("channel_title"),
                    published_at=fetch_dict["video"].get("published_at"),
                    comments_fetched=fetch_dict["stats"]["comments_fetched"],
                    comments_analyzed=len(emotion_result.classified_comments),
                    languages=languages,
                ),
                top_primary_emotions=aggregation_result.top_primary_emotions,
                top_nuanced_emotions=aggregation_result.top_nuanced_emotions,
                valence=aggregation_result.valence,
                timeline=aggregation_result.timeline,
                warnings=self._map_warning_strings(combined_warning_strings),
                description=description_result.description,
                representative_comments=aggregation_result.representative_comments,
            )

            final_payload = final_response.model_dump(mode="json")

            if settings.use_cache:
                self.file_cache.save_analysis(
                    cache_key=analysis_cache_key,
                    payload=final_payload,
                )

            if settings.save_artifacts:
                self.file_cache.save_artifact(
                    artifact_type="final",
                    name=video_id,
                    payload=final_payload,
                )

            return final_response

        except Exception as exc:
            raise AnalysisAgentError(f"Analysis agent failed: {exc}") from exc

    def _ensure_languages_in_payload(
        self,
        *,
        video_id: str,
        analysis_cache_key: str,
        payload: dict,
    ) -> dict:
        raw_fetch_cache = self.file_cache.load_raw_fetch(video_id=video_id)
        if raw_fetch_cache is None:
            video_block = payload.get("video", {})
            video_block["languages"] = video_block.get("languages", [])
            payload["video"] = video_block
            return payload

        raw_payload = raw_fetch_cache.get("payload", raw_fetch_cache)
        languages = self._extract_languages_from_fetch_payload(raw_payload)

        video_block = payload.get("video", {})
        video_block["languages"] = [item.model_dump(mode="json") for item in languages]
        payload["video"] = video_block

        if settings.use_cache:
            self.file_cache.save_analysis(
                cache_key=analysis_cache_key,
                payload=payload,
            )

        return payload

    def _extract_languages_from_fetch_payload(self, fetch_payload: dict):
        texts = [
            item.get("text_original", "")
            for item in fetch_payload.get("comments", [])
        ]
        return compute_language_distribution(texts)

    @staticmethod
    def _map_warning_strings(warnings: list[str]) -> list[AnalysisWarning]:
        valid = {warning.value: warning for warning in AnalysisWarning}
        mapped: list[AnalysisWarning] = []

        for warning in warnings:
            if warning in valid:
                mapped.append(valid[warning])

        return mapped

    @staticmethod
    def _raw_comments_from_fetch_payload(fetch_payload: dict):
        from app.providers.youtube_provider import RawComment

        comments = []
        for item in fetch_payload.get("comments", []):
            comments.append(
                RawComment(
                    comment_id=item["comment_id"],
                    published_at=item["published_at"],
                    like_count=item["like_count"],
                    reply_count=item.get("reply_count", 0),
                    text_original=item["text_original"],
                    author_display_name=item.get("author_display_name"),
                )
            )
        return comments