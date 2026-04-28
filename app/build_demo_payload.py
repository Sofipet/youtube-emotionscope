from __future__ import annotations

from pathlib import Path

from app.agents.analysis_agent import AnalysisAgent
from app.contracts import AnalyzeVideoRequest
from app.settings import settings


DEMO_VIDEO_URL = "https://www.youtube.com/watch?v=KraE1Qxtv8I"


def main() -> None:
    agent = AnalysisAgent()
    result = agent.run(AnalyzeVideoRequest(video_url=DEMO_VIDEO_URL))

    payload = result.model_dump(mode="json")

    demo_path: Path = settings.demo_file_path
    demo_path.parent.mkdir(parents=True, exist_ok=True)
    demo_path.write_text(
        __import__("json").dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Demo payload saved to: {demo_path}")


if __name__ == "__main__":
    main()