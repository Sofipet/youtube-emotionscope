from app.pipelines.fetch_pipeline import FetchPipeline
from app.pipelines.preprocess_pipeline import (
    PreprocessPipeline,
    preprocessed_comments_to_dicts,
)


def main() -> None:
    video_url = input("Paste YouTube video URL: ").strip()

    fetch_pipeline = FetchPipeline()
    fetch_result = fetch_pipeline.run(video_url=video_url, max_comments=100)

    preprocess_pipeline = PreprocessPipeline(sample_size=30, random_seed=42)
    preprocess_result = preprocess_pipeline.run(fetch_result.comments)

    print("\n=== FETCH WARNINGS ===")
    print(fetch_result.warnings)

    print("\n=== PREPROCESS WARNINGS ===")
    print(preprocess_result.warnings)

    print("\n=== PREPROCESS STATS ===")
    print(preprocess_result.stats)

    print("\n=== FIRST 5 CLEANED COMMENTS ===")
    for comment in preprocessed_comments_to_dicts(preprocess_result.cleaned_comments)[:5]:
        print(comment)

    print("\n=== FIRST 5 SAMPLED COMMENTS ===")
    for comment in preprocessed_comments_to_dicts(preprocess_result.sampled_comments)[:5]:
        print(comment)


if __name__ == "__main__":
    main()