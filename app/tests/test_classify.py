from app.providers.openai_provider import OpenAIProvider


def main() -> None:
    comment = input("Paste a comment: ").strip()

    provider = OpenAIProvider()
    result = provider.classify_comment(comment_text=comment)

    print("\n=== CLASSIFICATION ===")
    print(result.model_dump(mode="json"))


if __name__ == "__main__":
    main()