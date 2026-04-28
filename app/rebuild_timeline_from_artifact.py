from __future__ import annotations

import json
from pathlib import Path

from app.contracts import ClassifiedComment
from app.pipelines.aggregation_pipeline import AggregationPipeline
from app.settings import settings


VIDEO_ID = "KraE1Qxtv8I"


def main() -> None:
    classified_path = settings.classified_artifacts_path / f"{VIDEO_ID}.json"
    final_demo_path = settings.demo_file_path

    if not classified_path.exists():
        raise FileNotFoundError(f"Classified artifact not found: {classified_path}")

    if not final_demo_path.exists():
        raise FileNotFoundError(f"Demo file not found: {final_demo_path}")

    classified_payload = json.loads(classified_path.read_text(encoding="utf-8"))
    classified_comments_raw = classified_payload["payload"]["comments"]

    classified_comments = [
        ClassifiedComment.model_validate(item)
        for item in classified_comments_raw
    ]

    aggregation = AggregationPipeline()
    aggregation_result = aggregation.run(classified_comments=classified_comments)

    final_payload = json.loads(final_demo_path.read_text(encoding="utf-8"))
    final_payload["timeline"] = [
        item.model_dump(mode="json")
        for item in aggregation_result.timeline
    ]

    final_demo_path.write_text(
        json.dumps(final_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Updated timeline in {final_demo_path}")


if __name__ == "__main__":
    main()