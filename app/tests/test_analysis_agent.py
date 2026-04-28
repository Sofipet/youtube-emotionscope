from app.agents.analysis_agent import AnalysisAgent
from app.contracts import AnalyzeVideoRequest


def main() -> None:
    video_url = input("Paste YouTube video URL: ").strip()

    agent = AnalysisAgent()
    result = agent.run(AnalyzeVideoRequest(video_url=video_url))

    payload = result.model_dump(mode="json")

    print("\n=== VIDEO ===")
    print(payload["video"])

    print("\n=== ANALYSIS ===")
    print(payload["analysis"])

    print("\n=== DOMINANT EMOTIONS ===")
    for item in payload["dominant_emotions"][:5]:
        print(item)

    print("\n=== TOP NUANCED EMOTIONS ===")
    for item in payload["top_nuanced_emotions"]:
        print(item)

    print("\n=== VALENCE DISTRIBUTION ===")
    print(payload["valence_distribution"])

    print("\n=== REPRESENTATIVE COMMENTS (FIRST 5) ===")
    for item in payload["representative_comments"][:5]:
        print(item)

    print("\n=== SUMMARY ===")
    print(payload["summary"])


if __name__ == "__main__":
    main()