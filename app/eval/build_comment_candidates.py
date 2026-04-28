from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.settings import settings


TARGET_VIDEO_IDS = {
    "1ICnnVI3t_k",
    "KraE1Qxtv8I",
    "yiOb0yZCIcc",
}

OUTPUT_PATH = Path("data/eval/comment_candidates.json")


def load_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_comment_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "comment_id" in payload[0]:
            return payload

    if isinstance(payload, dict):
        for key in [
            "classified_comments",
            "comments",
            "items",
            "classified",
            "payload"
        ]:
            if key in payload:
                extracted = extract_comment_list(payload[key])
                if extracted:
                    return extracted

    return []


def detect_video_id(payload: Any, path: Path) -> str | None:
    if isinstance(payload, dict):
        for key in ["video_id", "source_video_id"]:
            value = payload.get(key)
            if isinstance(value, str) and value in TARGET_VIDEO_IDS:
                return value

        if "video" in payload and isinstance(payload["video"], dict):
            value = payload["video"].get("video_id")
            if isinstance(value, str) and value in TARGET_VIDEO_IDS:
                return value

        if "payload" in payload:
            nested = detect_video_id(payload["payload"], path)
            if nested:
                return nested

    stem = path.stem
    for video_id in TARGET_VIDEO_IDS:
        if stem.startswith(video_id):
            return video_id

    return None


def classify_bucket(comment: dict[str, Any]) -> str:
    text = (comment.get("text_original") or comment.get("text_clean") or comment.get("text") or "").strip()
    nuanced = comment.get("nuanced_emotion")
    intensity = float(comment.get("emotion_intensity") or 0.0)
    like_count = int(comment.get("like_count") or 0)

    if nuanced:
        return "nuanced_signal"

    if len(text) <= 20 or len(text.split()) <= 3:
        return "short_or_ambiguous"

    if intensity >= 0.85 and like_count >= 3:
        return "clear_high_emotion"

    return "difficult_or_noisy"


def normalize_comment(video_id: str, comment: dict[str, Any]) -> dict[str, Any]:
    text = (comment.get("text_original") or comment.get("text_clean") or comment.get("text") or "").strip()

    return {
        "video_id": video_id,
        "comment_id": comment.get("comment_id"),
        "published_at": comment.get("published_at"),
        "like_count": int(comment.get("like_count") or 0),
        "text": text,
        "detected_language": comment.get("detected_language"),
        "primary_emotion": comment.get("primary_emotion"),
        "emotion_intensity": comment.get("emotion_intensity"),
        "valence": comment.get("valence"),
        "nuanced_emotion": comment.get("nuanced_emotion"),
        "confidence": comment.get("confidence"),
        "suggested_bucket": classify_bucket(comment)
    }


def main() -> None:
    classified_dir = settings.classified_artifacts_path
    if not classified_dir.exists():
        raise FileNotFoundError(f"Classified artifacts directory not found: {classified_dir}")

    results: dict[str, list[dict[str, Any]]] = {video_id: [] for video_id in TARGET_VIDEO_IDS}

    for path in sorted(classified_dir.glob("*.json")):
        try:
            raw = load_json(path)
        except Exception:
            continue

        video_id = detect_video_id(raw, path)
        if video_id not in TARGET_VIDEO_IDS:
            continue

        comments = extract_comment_list(raw)
        if not comments:
            continue

        normalized_comments = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if "comment_id" not in comment:
                continue
            normalized_comments.append(normalize_comment(video_id, comment))

        if normalized_comments:
            results[video_id] = normalized_comments

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    for video_id, comments in results.items():
        print(f"{video_id}: {len(comments)} candidate comments saved")

    print(f"Saved candidate comments to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()