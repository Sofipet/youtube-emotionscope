from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.contracts import (
    AnalysisWarning,
    ClassifiedComment,
    EmotionTimelinePoint,
    NuancedEmotionAggregate,
    PrimaryEmotion,
    PrimaryEmotionAggregate,
    RepresentativeComment,
    Valence,
    ValenceDistribution,
)
from app.settings import settings
from app.tracing import traceable


@dataclass
class AggregationPipelineResult:
    top_primary_emotions: list[PrimaryEmotionAggregate]
    top_nuanced_emotions: list[NuancedEmotionAggregate]
    valence: ValenceDistribution
    timeline: list[EmotionTimelinePoint]
    representative_comments: list[RepresentativeComment]
    warnings: list[str]
    stats: dict[str, int]


class AggregationPipelineError(Exception):
    pass


class AggregationPipeline:
    def __init__(
        self,
        *,
        top_primary_emotions_limit: Optional[int] = None,
        top_nuanced_emotions_limit: Optional[int] = None,
        representative_comments_limit: Optional[int] = None,
        min_nuanced_emotion_frequency: Optional[int] = None,
    ) -> None:
        self.top_primary_emotions_limit = top_primary_emotions_limit or settings.top_primary_emotions_limit
        self.top_nuanced_emotions_limit = top_nuanced_emotions_limit or settings.top_nuanced_emotions_limit
        self.representative_comments_limit = representative_comments_limit or settings.representative_comments_limit
        self.min_nuanced_emotion_frequency = (
            min_nuanced_emotion_frequency or settings.min_nuanced_emotion_frequency
        )

    @traceable(run_type="tool", name="aggregation_pipeline")
    def run(self, *, classified_comments: list[ClassifiedComment]) -> AggregationPipelineResult:
        if not classified_comments:
            raise AggregationPipelineError("Cannot aggregate an empty classified comment list.")

        warnings: list[str] = []

        top_primary_emotions = self._build_top_primary_emotions(classified_comments)
        top_nuanced_emotions = self._build_top_nuanced_emotions(classified_comments)
        valence = self._build_valence_distribution(classified_comments)
        timeline = self._build_timeline(classified_comments)
        representative_comments = self._select_representative_comments(classified_comments)

        if len(classified_comments) < 20:
            warnings.append(AnalysisWarning.TOO_FEW_COMMENTS.value)

        if len(timeline) < 2:
            warnings.append(AnalysisWarning.SPARSE_TIMELINE.value)

        avg_confidence = sum(comment.confidence for comment in classified_comments) / len(classified_comments)
        if avg_confidence < 0.6:
            warnings.append(AnalysisWarning.LOW_CONFIDENCE_DISTRIBUTION.value)

        stats = {
            "comments_aggregated": len(classified_comments),
            "top_primary_emotions_count": len(top_primary_emotions),
            "top_nuanced_emotions_count": len(top_nuanced_emotions),
            "timeline_points_count": len(timeline),
            "representative_comments_count": len(representative_comments),
        }

        return AggregationPipelineResult(
            top_primary_emotions=top_primary_emotions,
            top_nuanced_emotions=top_nuanced_emotions,
            valence=valence,
            timeline=timeline,
            representative_comments=representative_comments,
            warnings=warnings,
            stats=stats,
        )

    def _build_top_primary_emotions(
        self,
        comments: list[ClassifiedComment],
    ) -> list[PrimaryEmotionAggregate]:
        total_comments = len(comments)
        grouped: dict[PrimaryEmotion, list[ClassifiedComment]] = defaultdict(list)

        for comment in comments:
            grouped[comment.primary_emotion].append(comment)

        aggregates: list[PrimaryEmotionAggregate] = []

        for emotion in PrimaryEmotion:
            emotion_comments = grouped.get(emotion, [])
            if not emotion_comments:
                continue

            prevalence = len(emotion_comments) / total_comments
            avg_intensity = sum(c.emotion_intensity for c in emotion_comments) / len(emotion_comments)

            aggregates.append(
                PrimaryEmotionAggregate(
                    emotion=emotion,
                    prevalence=round(prevalence, 4),
                    avg_intensity=round(avg_intensity, 4),
                )
            )

        aggregates.sort(key=lambda item: (item.prevalence, item.avg_intensity), reverse=True)
        return aggregates[: self.top_primary_emotions_limit]

    def _build_top_nuanced_emotions(
        self,
        comments: list[ClassifiedComment],
    ) -> list[NuancedEmotionAggregate]:
        total_comments = len(comments)
        grouped: dict[str, list[ClassifiedComment]] = defaultdict(list)

        for comment in comments:
            if comment.nuanced_emotion:
                normalized = comment.nuanced_emotion.strip().lower()
                if normalized:
                    grouped[normalized].append(comment)

        aggregates: list[NuancedEmotionAggregate] = []

        for nuanced_emotion, emotion_comments in grouped.items():
            if len(emotion_comments) < self.min_nuanced_emotion_frequency:
                continue

            prevalence = len(emotion_comments) / total_comments
            avg_intensity = sum(c.emotion_intensity for c in emotion_comments) / len(emotion_comments)

            aggregates.append(
                NuancedEmotionAggregate(
                    emotion=nuanced_emotion,
                    prevalence=round(prevalence, 4),
                    avg_intensity=round(avg_intensity, 4),
                )
            )

        aggregates.sort(key=lambda item: (item.prevalence, item.avg_intensity), reverse=True)
        return aggregates[: self.top_nuanced_emotions_limit]

    def _build_valence_distribution(
        self,
        comments: list[ClassifiedComment],
    ) -> ValenceDistribution:
        total_comments = len(comments)

        counts = {
            Valence.POSITIVE: 0,
            Valence.NEGATIVE: 0,
            Valence.MIXED: 0,
            Valence.NEUTRAL: 0,
        }

        for comment in comments:
            counts[comment.valence] += 1

        return ValenceDistribution(
            positive=round(counts[Valence.POSITIVE] / total_comments, 4),
            negative=round(counts[Valence.NEGATIVE] / total_comments, 4),
            mixed=round(counts[Valence.MIXED] / total_comments, 4),
            neutral=round(counts[Valence.NEUTRAL] / total_comments, 4),
        )

    def _build_timeline(
        self,
        comments: list[ClassifiedComment],
    ) -> list[EmotionTimelinePoint]:
        grouped: dict[str, list[ClassifiedComment]] = defaultdict(list)

        for comment in comments:
            dt = self._parse_timestamp(comment)
            day_key = dt.date().isoformat()
            grouped[day_key].append(comment)

        timeline: list[EmotionTimelinePoint] = []

        for day in sorted(grouped.keys()):
            day_comments = grouped[day]

            timeline.append(
                EmotionTimelinePoint(
                    date=day,
                    comment_count=len(day_comments),
                    primary_emotions=self._build_primary_emotions_for_group(day_comments),
                    valence=self._build_valence_distribution(day_comments),
                )
            )

        return timeline

    def _build_primary_emotions_for_group(
        self,
        comments: list[ClassifiedComment],
    ) -> list[PrimaryEmotionAggregate]:
        total_comments = len(comments)
        grouped: dict[PrimaryEmotion, list[ClassifiedComment]] = defaultdict(list)

        for comment in comments:
            grouped[comment.primary_emotion].append(comment)

        aggregates: list[PrimaryEmotionAggregate] = []

        for emotion, emotion_comments in grouped.items():
            prevalence = len(emotion_comments) / total_comments
            avg_intensity = sum(c.emotion_intensity for c in emotion_comments) / len(emotion_comments)

            aggregates.append(
                PrimaryEmotionAggregate(
                    emotion=emotion,
                    prevalence=round(prevalence, 4),
                    avg_intensity=round(avg_intensity, 4),
                )
            )

        aggregates.sort(key=lambda item: (item.prevalence, item.avg_intensity), reverse=True)
        return aggregates

    def _select_representative_comments(
        self,
        comments: list[ClassifiedComment],
    ) -> list[RepresentativeComment]:
        ranked = sorted(
            comments,
            key=lambda c: (
                c.emotion_intensity,
                c.like_count,
                c.confidence,
            ),
            reverse=True,
        )

        selected = ranked[: self.representative_comments_limit]

        return [
            RepresentativeComment(
                comment_id=comment.comment_id,
                primary_emotion=comment.primary_emotion,
                nuanced_emotion=comment.nuanced_emotion,
                emotion_intensity=comment.emotion_intensity,
                valence=comment.valence,
                like_count=comment.like_count,
                text=comment.text_original,
            )
            for comment in selected
        ]

    @staticmethod
    def _parse_timestamp(comment: ClassifiedComment) -> datetime:
        published_at = comment.published_at.replace("Z", "+00:00")
        return datetime.fromisoformat(published_at)


def aggregation_result_to_dict(result: AggregationPipelineResult) -> dict:
    return {
        "top_primary_emotions": [item.model_dump(mode="json") for item in result.top_primary_emotions],
        "top_nuanced_emotions": [item.model_dump(mode="json") for item in result.top_nuanced_emotions],
        "valence": result.valence.model_dump(mode="json"),
        "timeline": [item.model_dump(mode="json") for item in result.timeline],
        "warnings": result.warnings,
        "representative_comments": [item.model_dump(mode="json") for item in result.representative_comments],
        "stats": result.stats,
    }