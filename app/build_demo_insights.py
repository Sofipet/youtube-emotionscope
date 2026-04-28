from __future__ import annotations

import json
from pathlib import Path

from app.agents.video_insight_agent import VideoInsightAgent
from app.contracts import VideoAnalysisResponse
from app.contracts_agent import DemoInsightItem, DemoInsightsPayload, VideoInsightRequest


DEMO_ANALYSIS_PATH = Path("data/demo/demo_video_analysis.json")
DEMO_INSIGHTS_PATH = Path("data/demo/demo_video_insights.json")

DEMO_QUESTIONS = [
    "Is the emotional tone closer to moral outrage or collective grief?",
]


def main() -> None:
    if not DEMO_ANALYSIS_PATH.exists():
        raise FileNotFoundError(f"Demo analysis file not found: {DEMO_ANALYSIS_PATH}")

    analysis_payload = json.loads(DEMO_ANALYSIS_PATH.read_text(encoding="utf-8"))
    analysis = VideoAnalysisResponse.model_validate(analysis_payload)

    agent = VideoInsightAgent()
    items: list[DemoInsightItem] = []

    for question in DEMO_QUESTIONS:
        response = agent.run(
            VideoInsightRequest(
                analysis=analysis,
                question=question,
            ),
            force_refresh=True,
        )

        items.append(
            DemoInsightItem(
                question=question,
                answer=response.answer,
                suggested_followups=response.suggested_followups,
                tools_used=response.tools_used,
            )
        )

    payload = DemoInsightsPayload(
        video_id=analysis.video.video_id,
        items=items,
    )

    DEMO_INSIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEMO_INSIGHTS_PATH.write_text(
        json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved demo insights to {DEMO_INSIGHTS_PATH}")


if __name__ == "__main__":
    main()