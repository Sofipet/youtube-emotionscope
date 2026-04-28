from __future__ import annotations

from app.agents.analysis_agent import AnalysisAgent
from app.settings import settings


VIDEO_URLS = [
    "https://www.youtube.com/watch?v=KraE1Qxtv8I",
    "https://www.youtube.com/watch?v=1ICnnVI3t_k",
]


def main() -> None:
    agent = AnalysisAgent()

    for video_url in VIDEO_URLS:
        video_id = agent.fetch_pipeline.youtube_provider.parse_video_id(video_url)

        cache_key = agent.file_cache.build_analysis_cache_key(
            video_id=video_id,
            classification_model=settings.classification_model,
            description_model=settings.description_model,
            sample_size=agent.config.sample_size,
            batch_size=agent.config.classification_batch_size,
            top_primary_limit=agent.config.top_primary_emotions_limit,
            top_nuanced_limit=agent.config.top_nuanced_emotions_limit,
            timeline_bucket_count=0,
            version_tag="v2_date_timeline",
        )

        cached = agent.file_cache.load_analysis(cache_key=cache_key)

        print(f"\nVideo ID: {video_id}")
        print(f"Expected cache key: {cache_key}")
        print("Status:", "CACHE HIT" if cached is not None else "CACHE MISS")


if __name__ == "__main__":
    main()