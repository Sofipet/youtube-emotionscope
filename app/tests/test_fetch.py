from app.pipelines.fetch_pipeline import FetchPipeline, fetch_pipeline_to_dict


def main() -> None:
    video_url = input("Paste YouTube video URL: ").strip()

    pipeline = FetchPipeline()
    result = pipeline.run(video_url=video_url, max_comments=20)

    payload = fetch_pipeline_to_dict(result)

    print("\n=== VIDEO ===")
    print(payload["video"])

    print("\n=== WARNINGS ===")
    print(payload["warnings"])

    print("\n=== FIRST 3 COMMENTS ===")
    for comment in payload["comments"][:3]:
        print(comment)


if __name__ == "__main__":
    main()