from __future__ import annotations

from pydantic import BaseModel, Field

from app.contracts import VideoAnalysisResponse


class VideoInsightRequest(BaseModel):
    analysis: VideoAnalysisResponse
    question: str = Field(min_length=1)


class VideoInsightResponse(BaseModel):
    answer: str = Field(min_length=1)
    suggested_followups: list[str] = []
    tools_used: list[str] = []


class DemoInsightItem(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    suggested_followups: list[str] = []
    tools_used: list[str] = []


class DemoInsightsPayload(BaseModel):
    video_id: str = Field(min_length=1)
    items: list[DemoInsightItem]