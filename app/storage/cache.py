from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from app.settings import settings


class CacheError(Exception):
    pass


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, tuple):
        return [_to_jsonable(v) for v in obj]
    return obj


class FileCache:
    def __init__(
        self,
        *,
        raw_cache_dir: Optional[Path] = None,
        analysis_cache_dir: Optional[Path] = None,
        agent_insights_cache_dir: Optional[Path] = None,
        raw_artifacts_dir: Optional[Path] = None,
        cleaned_artifacts_dir: Optional[Path] = None,
        sampled_artifacts_dir: Optional[Path] = None,
        classified_artifacts_dir: Optional[Path] = None,
        final_artifacts_dir: Optional[Path] = None,
    ) -> None:
        self.raw_cache_dir = raw_cache_dir or settings.raw_cache_path
        self.analysis_cache_dir = analysis_cache_dir or settings.analysis_cache_path
        self.agent_insights_cache_dir = agent_insights_cache_dir or (settings.analysis_cache_path.parent / "agent_insights")

        self.raw_artifacts_dir = raw_artifacts_dir or settings.raw_artifacts_path
        self.cleaned_artifacts_dir = cleaned_artifacts_dir or settings.cleaned_artifacts_path
        self.sampled_artifacts_dir = sampled_artifacts_dir or settings.sampled_artifacts_path
        self.classified_artifacts_dir = classified_artifacts_dir or settings.classified_artifacts_path
        self.final_artifacts_dir = final_artifacts_dir or settings.final_artifacts_path

        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        dirs = [
            self.raw_cache_dir,
            self.analysis_cache_dir,
            self.agent_insights_cache_dir,
            self.raw_artifacts_dir,
            self.cleaned_artifacts_dir,
            self.sampled_artifacts_dir,
            self.classified_artifacts_dir,
            self.final_artifacts_dir,
        ]
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def build_analysis_cache_key(
        *,
        video_id: str,
        classification_model: str,
        description_model: str,
        sample_size: int,
        batch_size: int,
        top_primary_limit: int,
        top_nuanced_limit: int,
        timeline_bucket_count: int,
        version_tag: str = "v1",
    ) -> str:
        raw = (
            f"{video_id}|"
            f"{classification_model}|"
            f"{description_model}|"
            f"{sample_size}|"
            f"{batch_size}|"
            f"{top_primary_limit}|"
            f"{top_nuanced_limit}|"
            f"{timeline_bucket_count}|"
            f"{version_tag}"
        )
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"{video_id}__{digest}"

    @staticmethod
    def _normalize_question(question: str) -> str:
        return " ".join(question.strip().lower().split())

    @classmethod
    def build_agent_insight_cache_key(
        cls,
        *,
        video_id: str,
        question: str,
        version_tag: str = "v1",
    ) -> str:
        normalized_question = cls._normalize_question(question)
        raw = f"{video_id}|{normalized_question}|{version_tag}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"{video_id}__{digest}"

    def load_raw_fetch(self, *, video_id: str) -> Optional[dict]:
        path = self.raw_cache_dir / f"{video_id}.json"
        if not settings.use_cache or not path.exists():
            return None
        return self._load_json(path)

    def save_raw_fetch(
        self,
        *,
        video_id: str,
        payload: dict,
    ) -> Path:
        path = self.raw_cache_dir / f"{video_id}.json"
        wrapped = {
            "saved_at": _now_utc_iso(),
            "type": "raw_fetch",
            "video_id": video_id,
            "payload": _to_jsonable(payload),
        }
        self._save_json(path, wrapped)
        return path

    def load_analysis(self, *, cache_key: str) -> Optional[dict]:
        path = self.analysis_cache_dir / f"{cache_key}.json"
        if not settings.use_cache or not path.exists():
            return None
        return self._load_json(path)

    def save_analysis(
        self,
        *,
        cache_key: str,
        payload: dict,
    ) -> Path:
        path = self.analysis_cache_dir / f"{cache_key}.json"
        wrapped = {
            "saved_at": _now_utc_iso(),
            "type": "analysis",
            "cache_key": cache_key,
            "payload": _to_jsonable(payload),
        }
        self._save_json(path, wrapped)
        return path

    def load_agent_insight(self, *, cache_key: str) -> Optional[dict]:
        path = self.agent_insights_cache_dir / f"{cache_key}.json"
        if not settings.use_cache or not path.exists():
            return None
        return self._load_json(path)

    def save_agent_insight(
        self,
        *,
        cache_key: str,
        video_id: str,
        question: str,
        payload: dict,
    ) -> Path:
        path = self.agent_insights_cache_dir / f"{cache_key}.json"
        wrapped = {
            "saved_at": _now_utc_iso(),
            "type": "agent_insight",
            "cache_key": cache_key,
            "video_id": video_id,
            "question": question,
            "payload": _to_jsonable(payload),
        }
        self._save_json(path, wrapped)
        return path

    def save_artifact(
        self,
        *,
        artifact_type: str,
        name: str,
        payload: Any,
    ) -> Path:
        directory = self._artifact_dir_for_type(artifact_type)
        path = directory / f"{name}.json"
        wrapped = {
            "saved_at": _now_utc_iso(),
            "artifact_type": artifact_type,
            "name": name,
            "payload": _to_jsonable(payload),
        }
        self._save_json(path, wrapped)
        return path

    def _artifact_dir_for_type(self, artifact_type: str) -> Path:
        mapping = {
            "raw": self.raw_artifacts_dir,
            "cleaned": self.cleaned_artifacts_dir,
            "sampled": self.sampled_artifacts_dir,
            "classified": self.classified_artifacts_dir,
            "final": self.final_artifacts_dir,
        }
        if artifact_type not in mapping:
            raise CacheError(f"Unknown artifact type: {artifact_type}")
        return mapping[artifact_type]

    @staticmethod
    def _load_json(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CacheError(f"Failed to load JSON from {path}: {exc}") from exc

    @staticmethod
    def _save_json(path: Path, payload: dict) -> None:
        try:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            raise CacheError(f"Failed to save JSON to {path}: {exc}") from exc