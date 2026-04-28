from __future__ import annotations

from pprint import pprint

from app.agents.analysis_agent import AnalysisAgent
from app.agents.video_insight_agent import VideoInsightAgent
from app.contracts import AnalyzeVideoRequest
from app.contracts_agent import VideoInsightRequest
from app.storage.cache import FileCache


VIDEO_URL = "https://www.youtube.com/watch?v=KraE1Qxtv8I"
QUESTION = "Why is anger dominant here, and what do the comments suggest?"


def main() -> None:
    analysis_agent = AnalysisAgent()
    insight_agent = VideoInsightAgent()
    file_cache = FileCache()

    analysis = analysis_agent.run(AnalyzeVideoRequest(video_url=VIDEO_URL))

    cache_key = file_cache.build_agent_insight_cache_key(
        video_id=analysis.video.video_id,
        question=QUESTION,
        version_tag=insight_agent.agent_version_tag,
    )

    print("\n=== FIRST RUN ===")
    response_1 = insight_agent.run(
        VideoInsightRequest(
            analysis=analysis,
            question=QUESTION,
        )
    )
    pprint(response_1.model_dump(mode="json"))

    cached = file_cache.load_agent_insight(cache_key=cache_key)
    print("\nCache exists after first run:", cached is not None)

    print("\n=== SECOND RUN ===")
    response_2 = insight_agent.run(
        VideoInsightRequest(
            analysis=analysis,
            question=QUESTION,
        )
    )
    pprint(response_2.model_dump(mode="json"))

    print("\n=== CACHE KEY ===")
    print(cache_key)


if __name__ == "__main__":
    main()