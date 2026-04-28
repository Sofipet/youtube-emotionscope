from app.pipelines.aggregation_pipeline import AggregationPipeline
from app.pipelines.emotion_pipeline import EmotionPipeline
from app.pipelines.fetch_pipeline import FetchPipeline
from app.pipelines.summary_pipeline import SummaryPipeline, summary_result_to_dict


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

    all_warnings = list(
        dict.fromkeys(
            fetch_result.warnings
            + emotion_result.warnings
            + aggregation_result.warnings
        )
    )

    summary_pipeline = SummaryPipeline()
    summary_result = summary_pipeline.run(
        video_title=fetch_result.video.title,
        comments_analyzed=len(emotion_result.classified_comments),
        dominant_emotions=aggregation_result.dominant_emotions,
        top_nuanced_emotions=aggregation_result.top_nuanced_emotions,
        valence_distribution=aggregation_result.valence_distribution,
        representative_comments=aggregation_result.representative_comments,
        warnings=all_warnings,
    )

    payload = summary_result_to_dict(summary_result)

    print("\n=== WARNINGS ===")
    print(all_warnings)

    print("\n=== TOP NUANCED EMOTIONS ===")
    for item in aggregation_result.top_nuanced_emotions:
        print(item.model_dump(mode="json"))

    print("\n=== SUMMARY ===")
    print(payload["summary"])


if __name__ == "__main__":
    main()