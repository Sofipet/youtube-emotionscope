from __future__ import annotations

from app.agents.analysis_agent import AnalysisAgent
from app.contracts import AnalyzeVideoRequest

VIDEO_URLS = [
    "https://www.youtube.com/watch?v=KraE1Qxtv8I",
    "https://www.youtube.com/watch?v=1ICnnVI3t_k",
]

def main() -> None:
    agent = AnalysisAgent()

    for url in VIDEO_URLS:
        result = agent.run(AnalyzeVideoRequest(video_url=url))
        print(f"Updated analysis payload for {result.video.video_id}")
        print(f"Languages: {[f'{x.language_label} {round(x.share*100)}%' for x in result.video.languages]}")

if __name__ == "__main__":
    main()