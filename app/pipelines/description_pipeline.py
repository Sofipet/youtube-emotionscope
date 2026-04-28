from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.contracts import (
    NuancedEmotionAggregate,
    PrimaryEmotionAggregate,
    RepresentativeComment,
    ValenceDistribution,
)
from app.providers.openai_provider import OpenAIProvider, OpenAIProviderError
from app.tracing import traceable


@dataclass
class DescriptionPipelineResult:
    description: str
    stats: dict[str, int]


class DescriptionPipelineError(Exception):
    pass


class DescriptionPipeline:
    def __init__(self, openai_provider: Optional[OpenAIProvider] = None) -> None:
        self.openai_provider = openai_provider or OpenAIProvider()
    @traceable(run_type="tool", name="description_pipeline")
    def run(
        self,
        *,
        video_title: str,
        comments_analyzed: int,
        top_primary_emotions: list[PrimaryEmotionAggregate],
        top_nuanced_emotions: list[NuancedEmotionAggregate],
        valence: ValenceDistribution,
        warnings: list[str],
        representative_comments: list[RepresentativeComment],
    ) -> DescriptionPipelineResult:
        try:
            description = self.openai_provider.generate_description(
                video_title=video_title,
                comments_analyzed=comments_analyzed,
                top_primary_emotions=[
                    item.model_dump(mode="json") for item in top_primary_emotions
                ],
                top_nuanced_emotions=[
                    item.model_dump(mode="json") for item in top_nuanced_emotions
                ],
                valence=valence.model_dump(mode="json"),
                warnings=warnings,
                representative_comments=[
                    item.model_dump(mode="json") for item in representative_comments
                ],
            )
        except OpenAIProviderError as exc:
            raise DescriptionPipelineError(str(exc)) from exc
        except Exception as exc:
            raise DescriptionPipelineError(
                f"Unexpected description pipeline failure: {exc}"
            ) from exc

        return DescriptionPipelineResult(
            description=description,
            stats={
                "representative_comments_used": min(len(representative_comments), 8),
                "top_primary_emotions_used": len(top_primary_emotions),
                "top_nuanced_emotions_used": len(top_nuanced_emotions),
            },
        )


def description_result_to_dict(result: DescriptionPipelineResult) -> dict:
    return {
        "description": result.description,
        "stats": result.stats,
    }