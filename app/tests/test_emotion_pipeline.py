from app.pipelines.emotion_pipeline import (
    EmotionPipeline,
    classified_comments_to_dicts,
)
from app.pipelines.fetch_pipeline import FetchPipeline


def main() -> None:
    video_url = input("Paste YouTube video URL: ").strip()

    fetch_pipeline = FetchPipeline()
    fetch_result = fetch_pipeline.run(video_url=video_url, max_comments=15)

    emotion_pipeline = EmotionPipeline()
    emotion_result = emotion_pipeline.run(
        comments=fetch_result.comments,
        detected_language=None,
        max_comments_to_analyze=10,
    )

    print("\n=== FETCH WARNINGS ===")
    print(fetch_result.warnings)

    print("\n=== EMOTION WARNINGS ===")
    print(emotion_result.warnings)

    print("\n=== FIRST 5 CLASSIFIED COMMENTS ===")
    for comment in classified_comments_to_dicts(emotion_result.classified_comments)[:5]:
        print(comment)


if __name__ == "__main__":
    main()