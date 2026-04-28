from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CANDIDATES_PATH = Path("data/eval/comment_candidates.json")
OUTPUT_PATH = Path("data/eval/comment_eval_cases.json")

VIDEO_ORDER = [
    "1ICnnVI3t_k",
    "KraE1Qxtv8I",
    "yiOb0yZCIcc",
]

TARGETS = {
    "clear_high_emotion": 4,
    "short_or_ambiguous": 2,
    "nuanced_signal": 2,
    "difficult_or_noisy": 2,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def short_text(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def pick_cases_for_video(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_bucket: dict[str, list[dict[str, Any]]] = {
        "clear_high_emotion": [],
        "short_or_ambiguous": [],
        "nuanced_signal": [],
        "difficult_or_noisy": [],
    }

    for c in comments:
        bucket = c.get("suggested_bucket", "difficult_or_noisy")
        by_bucket.setdefault(bucket, []).append(c)

    # deterministic ordering: higher likes first, then higher intensity
    for bucket_comments in by_bucket.values():
        bucket_comments.sort(
            key=lambda x: (
                -(x.get("like_count") or 0),
                -(x.get("emotion_intensity") or 0.0),
                str(x.get("comment_id") or "")
            )
        )

    selected: list[dict[str, Any]] = []

    for bucket, n in TARGETS.items():
        selected.extend(by_bucket.get(bucket, [])[:n])

    # if any bucket had too few items, backfill from remaining comments
    selected_ids = {c["comment_id"] for c in selected if c.get("comment_id")}
    remaining = [
        c for c in comments
        if c.get("comment_id") not in selected_ids
    ]
    remaining.sort(
        key=lambda x: (
            -(x.get("like_count") or 0),
            -(x.get("emotion_intensity") or 0.0),
            str(x.get("comment_id") or "")
        )
    )

    while len(selected) < 10 and remaining:
        selected.append(remaining.pop(0))

    return selected[:10]


def build_case(video_id: str, idx: int, comment: dict[str, Any]) -> dict[str, Any]:
    expected_primary = comment.get("primary_emotion")
    expected_valence = comment.get("valence")
    intensity = float(comment.get("emotion_intensity") or 0.0)

    lower = max(0.0, round(intensity - 0.15, 2))
    upper = min(1.0, round(intensity + 0.15, 2))

    nuanced = comment.get("nuanced_emotion")
    nuanced_options = [nuanced] if nuanced else [None]

    return {
        "case_id": f"comment_eval_{video_id}_{idx:02d}",
        "video_id": video_id,
        "comment_id": comment.get("comment_id"),
        "sampling_bucket": comment.get("suggested_bucket"),
        "text": comment.get("text"),
        "text_short": short_text(comment.get("text") or ""),
        "detected_language": comment.get("detected_language"),
        "expected_primary_emotion": expected_primary,
        "expected_valence": expected_valence,
        "expected_intensity_range": [lower, upper],
        "expected_nuanced_options": nuanced_options,
        "human_note": "Draft expectation generated from stored classified comment. Review manually before scoring."
    }


def main() -> None:
    if not CANDIDATES_PATH.exists():
        raise FileNotFoundError(f"Candidate file not found: {CANDIDATES_PATH}")

    candidates = load_json(CANDIDATES_PATH)
    all_cases: list[dict[str, Any]] = []

    for video_id in VIDEO_ORDER:
        comments = candidates.get(video_id, [])
        if not comments:
            raise ValueError(f"No candidate comments found for video_id={video_id}")

        selected = pick_cases_for_video(comments)

        if len(selected) != 10:
            raise ValueError(f"Expected 10 comments for {video_id}, got {len(selected)}")

        for idx, comment in enumerate(selected, start=1):
            all_cases.append(build_case(video_id, idx, comment))

    payload = {
        "comments_total": len(all_cases),
        "cases": all_cases
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Saved {len(all_cases)} comment eval cases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()