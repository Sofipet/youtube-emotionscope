from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.contracts import VideoAnalysisResponse
from app.contracts_agent import VideoInsightRequest, VideoInsightResponse
from app.prompts.loader import load_prompt
from app.settings import settings
from app.storage.cache import FileCache


class ToolPlan(BaseModel):
    tools_to_use: list[str] = Field(default_factory=list)
    reasoning_focus: str = Field(min_length=1)


class FinalInsightAnswer(BaseModel):
    answer: str = Field(min_length=1)
    suggested_followups: list[str] = Field(default_factory=list)


class VideoInsightAgent:
    def __init__(self) -> None:
        self.planner_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )
        self.answer_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )

        self.file_cache = FileCache()
        self.agent_version_tag = "v2_prompted_cached"

        self.planner_prompt = load_prompt("video_insight_planner.txt")
        self.synth_prompt = load_prompt("video_insight_synthesizer.txt")

    def run(
        self,
        request: VideoInsightRequest,
        force_refresh: bool = False,
    ) -> VideoInsightResponse:
        analysis = request.analysis
        question = request.question.strip()
        video_id = analysis.video.video_id

        cache_key = self.file_cache.build_agent_insight_cache_key(
            video_id=video_id,
            question=question,
            version_tag=self.agent_version_tag,
        )

        if settings.use_cache and not force_refresh:
            cached = self.file_cache.load_agent_insight(cache_key=cache_key)
            if cached is not None:
                payload = cached.get("payload", cached)
                return VideoInsightResponse.model_validate(payload)

        tools = self._build_tools(analysis)
        tool_map = {tool_obj.name: tool_obj for tool_obj in tools}

        plan = self._plan(question=question)

        tool_outputs: dict[str, Any] = {}
        tools_used: list[str] = []

        for tool_name in plan.tools_to_use:
            tool_obj = tool_map.get(tool_name)
            if tool_obj is None:
                continue
            result = tool_obj.invoke({})
            tool_outputs[tool_name] = result
            tools_used.append(tool_name)

        final = self._synthesize_answer(
            question=question,
            reasoning_focus=plan.reasoning_focus,
            tool_outputs=tool_outputs,
        )

        response = VideoInsightResponse(
            answer=final.answer,
            suggested_followups=final.suggested_followups,
            tools_used=tools_used,
        )

        if settings.use_cache:
            self.file_cache.save_agent_insight(
                cache_key=cache_key,
                video_id=video_id,
                question=question,
                payload=response.model_dump(mode="json"),
            )

        return response

    def _plan(self, *, question: str) -> ToolPlan:
        planner = self.planner_llm.with_structured_output(ToolPlan)

        return planner.invoke(
            [
                {"role": "system", "content": self.planner_prompt},
                {"role": "user", "content": f"Question: {question}"},
            ]
        )

    def _synthesize_answer(
        self,
        *,
        question: str,
        reasoning_focus: str,
        tool_outputs: dict[str, Any],
    ) -> FinalInsightAnswer:
        synthesizer = self.answer_llm.with_structured_output(FinalInsightAnswer)

        user = (
            f"Question:\n{question}\n\n"
            f"Reasoning focus:\n{reasoning_focus}\n\n"
            f"Tool outputs:\n{json.dumps(tool_outputs, ensure_ascii=False, indent=2)}"
        )

        return synthesizer.invoke(
            [
                {"role": "system", "content": self.synth_prompt},
                {"role": "user", "content": user},
            ]
        )

    def _build_tools(self, analysis: VideoAnalysisResponse):
        video_payload = analysis.model_dump(mode="json")

        @tool
        def get_video_metadata() -> dict:
            """Return video title, channel, publication date, comments fetched, and comments analyzed."""
            video = video_payload["video"]
            return {
                "title": video.get("title"),
                "channel_title": video.get("channel_title"),
                "published_at": video.get("published_at"),
                "comments_fetched": video.get("comments_fetched"),
                "comments_analyzed": video.get("comments_analyzed"),
            }

        @tool
        def get_language_mix() -> dict:
            """Return the language distribution of the analyzed comments."""
            return {
                "languages": video_payload["video"].get("languages", [])
            }

        @tool
        def get_top_primary_emotions() -> dict:
            """Return the top primary emotions with prevalence and average intensity."""
            return {
                "top_primary_emotions": video_payload.get("top_primary_emotions", [])
            }

        @tool
        def get_top_nuanced_emotions() -> dict:
            """Return the top nuanced emotions with prevalence and average intensity."""
            return {
                "top_nuanced_emotions": video_payload.get("top_nuanced_emotions", [])
            }

        @tool
        def get_valence_distribution() -> dict:
            """Return the positive, negative, mixed, and neutral valence distribution."""
            return {
                "valence": video_payload.get("valence", {})
            }

        @tool
        def get_timeline_summary() -> dict:
            """Return a compact summary of how top emotions and valence shift across timeline points."""
            timeline = video_payload.get("timeline", [])
            compact_points = []

            for point in timeline:
                compact_points.append(
                    {
                        "date": point.get("date"),
                        "comment_count": point.get("comment_count"),
                        "top_primary_emotions": point.get("primary_emotions", [])[:3],
                        "valence": point.get("valence", {}),
                    }
                )

            return {"timeline_summary": compact_points}

        @tool
        def get_representative_comments() -> dict:
            """Return representative comments illustrating major emotional patterns."""
            comments = video_payload.get("representative_comments", [])
            return {"representative_comments": comments[:6]}

        @tool
        def get_dashboard_description() -> dict:
            """Return the dashboard description text."""
            return {"description": video_payload.get("description", "")}

        return [
            get_video_metadata,
            get_language_mix,
            get_top_primary_emotions,
            get_top_nuanced_emotions,
            get_valence_distribution,
            get_timeline_summary,
            get_representative_comments,
            get_dashboard_description,
        ]