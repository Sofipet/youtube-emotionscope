from app.pipelines.aggregation_pipeline import (
    AggregationPipeline,
    aggregation_result_to_dict,
)
from app.pipelines.emotion_pipeline import EmotionPipeline
from app.pipelines.fetch_pipeline import FetchPipeline


def main() -> None:
    video_url = input("Paste YouTube video URL: ").strip()

    fetch_pipeline = FetchPipeline()
    fetch_result = fetch_pipeline.run(video_url=video_url, max_comments=20)

    emotion_pipeline = EmotionPipeline()
    emotion_result = emotion_pipeline.run(
        comments=fetch_result.comments,
        detected_language=None,
        max_comments_to_analyze=15,
    )

    aggregation_pipeline = AggregationPipeline(
        representative_comments_per_emotion=2,
        timeline_bucket_count=5,
    )
    aggregation_result = aggregation_pipeline.run(
        classified_comments=emotion_result.classified_comments
    )

    payload = aggregation_result_to_dict(aggregation_result)

    print("\n=== FETCH WARNINGS ===")
    print(fetch_result.warnings)

    print("\n=== EMOTION WARNINGS ===")
    print(emotion_result.warnings)

    print("\n=== AGGREGATION WARNINGS ===")
    print(payload["warnings"])

    print("\n=== DOMINANT EMOTIONS ===")
    for item in payload["dominant_emotions"][:5]:
        print(item)

    print("\n=== VALENCE DISTRIBUTION ===")
    print(payload["valence_distribution"])

    print("\n=== TIMELINE (FIRST 2 BUCKETS) ===")
    for bucket in payload["timeline"][:2]:
        print(bucket)

    print("\n=== REPRESENTATIVE COMMENTS (FIRST 5) ===")
    for comment in payload["representative_comments"][:5]:
        print(comment)


if __name__ == "__main__":
    main()