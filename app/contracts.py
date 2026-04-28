from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class PrimaryEmotion(str, Enum):
    ANGER = "anger"
    FEAR = "fear"
    SADNESS = "sadness"
    DISGUST = "disgust"
    JOY = "joy"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    SURPRISE = "surprise"


class Valence(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class AnalysisWarning(str, Enum):
    TOO_FEW_COMMENTS = "too_few_comments"
    MULTILINGUAL_MIX = "multilingual_mix"
    LOW_CONFIDENCE_DISTRIBUTION = "low_confidence_distribution"
    SPARSE_TIMELINE = "sparse_timeline"
    API_PARTIAL_DATA = "api_partial_data"


class AnalyzeVideoRequest(BaseModel):
    video_url: HttpUrl


class LanguageShare(BaseModel):
    language_code: str = Field(min_length=1)
    language_label: str = Field(min_length=1)
    share: float = Field(ge=0.0, le=1.0)


class VideoBlock(BaseModel):
    video_id: str = Field(min_length=1)
    video_url: HttpUrl
    title: str = Field(min_length=1)
    channel_title: Optional[str] = None
    published_at: Optional[str] = None
    comments_fetched: int = Field(ge=0)
    comments_analyzed: int = Field(ge=0)
    languages: list[LanguageShare] = []


class PrimaryEmotionAggregate(BaseModel):
    emotion: PrimaryEmotion
    prevalence: float = Field(ge=0.0, le=1.0)
    avg_intensity: float = Field(ge=0.0, le=1.0)


class NuancedEmotionAggregate(BaseModel):
    emotion: str = Field(min_length=1)
    prevalence: float = Field(ge=0.0, le=1.0)
    avg_intensity: float = Field(ge=0.0, le=1.0)


class ValenceDistribution(BaseModel):
    positive: float = Field(ge=0.0, le=1.0)
    negative: float = Field(ge=0.0, le=1.0)
    mixed: float = Field(ge=0.0, le=1.0)
    neutral: float = Field(ge=0.0, le=1.0)


class EmotionTimelinePoint(BaseModel):
    date: str = Field(min_length=1)
    comment_count: int = Field(ge=0)
    primary_emotions: list[PrimaryEmotionAggregate]
    valence: ValenceDistribution


class RepresentativeComment(BaseModel):
    comment_id: str = Field(min_length=1)
    primary_emotion: PrimaryEmotion
    nuanced_emotion: Optional[str] = None
    emotion_intensity: float = Field(ge=0.0, le=1.0)
    valence: Valence
    like_count: int = Field(ge=0)
    text: str = Field(min_length=1)


class ClassifiedComment(BaseModel):
    comment_id: str = Field(min_length=1)
    published_at: str = Field(min_length=1)
    like_count: int = Field(ge=0)
    text_original: str = Field(min_length=1)
    text_clean: str = Field(min_length=1)
    detected_language: Optional[str] = None
    primary_emotion: PrimaryEmotion
    nuanced_emotion: Optional[str] = None
    emotion_intensity: float = Field(ge=0.0, le=1.0)
    valence: Valence
    confidence: float = Field(ge=0.0, le=1.0)


class VideoAnalysisResponse(BaseModel):
    video: VideoBlock
    top_primary_emotions: list[PrimaryEmotionAggregate]
    top_nuanced_emotions: list[NuancedEmotionAggregate]
    valence: ValenceDistribution
    timeline: list[EmotionTimelinePoint]
    warnings: list[AnalysisWarning]
    description: str = Field(min_length=1)
    representative_comments: list[RepresentativeComment]