from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests

from app.settings import settings


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeProviderError(Exception):
    pass


@dataclass
class RawVideoMetadata:
    video_id: str
    video_url: str
    title: str
    channel_title: Optional[str]
    published_at: Optional[str]


@dataclass
class RawComment:
    comment_id: str
    published_at: str
    like_count: int
    text_original: str
    author_display_name: Optional[str] = None
    reply_count: int = 0


class YouTubeProvider:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30) -> None:
        self.api_key = api_key or settings.youtube_api_key
        self.timeout = timeout

        if not self.api_key:
            raise YouTubeProviderError("YOUTUBE_API_KEY is not configured.")

    def parse_video_id(self, video_url: str) -> str:
        parsed = urlparse(video_url)

        if parsed.netloc in {"youtu.be", "www.youtu.be"}:
            video_id = parsed.path.lstrip("/")
            if video_id:
                return video_id

        if parsed.netloc in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
        }:
            if parsed.path == "/watch":
                query = parse_qs(parsed.query)
                video_id = query.get("v", [None])[0]
                if video_id:
                    return video_id

            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
                return path_parts[1]

        raise YouTubeProviderError(f"Could not parse video ID from URL: {video_url}")

    def fetch_video_metadata(self, video_url: str) -> RawVideoMetadata:
        video_id = self.parse_video_id(video_url)

        payload = self._get(
            endpoint="videos",
            params={
                "part": "snippet",
                "id": video_id,
            },
        )

        items = payload.get("items", [])
        if not items:
            raise YouTubeProviderError(f"No video metadata found for video ID: {video_id}")

        snippet = items[0].get("snippet", {})

        title = snippet.get("title", "").strip()
        if not title:
            raise YouTubeProviderError(f"Video title missing for video ID: {video_id}")

        return RawVideoMetadata(
            video_id=video_id,
            video_url=video_url,
            title=title,
            channel_title=snippet.get("channelTitle"),
            published_at=snippet.get("publishedAt"),
        )

    def fetch_comments(
        self,
        video_id: str,
        *,
        fetch_all_comments: Optional[bool] = None,
        max_comments: Optional[int] = None,
        order: Optional[str] = None,
    ) -> list[RawComment]:
        fetch_all = settings.fetch_all_comments if fetch_all_comments is None else fetch_all_comments
        order_value = order or settings.youtube_comment_order
        target_count = max_comments or settings.max_comments_to_fetch

        collected: list[RawComment] = []
        seen_comment_ids: set[str] = set()
        page_token: Optional[str] = None

        while True:
            per_page = 100
            if not fetch_all:
                remaining = target_count - len(collected)
                if remaining <= 0:
                    break
                per_page = min(100, remaining)

            payload = self._get(
                endpoint="commentThreads",
                params={
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": per_page,
                    "order": order_value,
                    "textFormat": "plainText",
                    "pageToken": page_token,
                },
            )

            items = payload.get("items", [])
            if not items:
                break

            for item in items:
                top_comment = item.get("snippet", {}).get("topLevelComment", {})
                snippet = top_comment.get("snippet", {})

                comment_id = top_comment.get("id")
                published_at = snippet.get("publishedAt")
                text_original = snippet.get("textDisplay", "")

                if not comment_id or not published_at:
                    continue

                normalized_text = normalize_comment_text(text_original)
                if not normalized_text:
                    continue

                if comment_id in seen_comment_ids:
                    continue

                seen_comment_ids.add(comment_id)

                collected.append(
                    RawComment(
                        comment_id=comment_id,
                        published_at=published_at,
                        like_count=int(snippet.get("likeCount", 0)),
                        text_original=text_original.strip(),
                        author_display_name=snippet.get("authorDisplayName"),
                        reply_count=int(item.get("snippet", {}).get("totalReplyCount", 0)),
                    )
                )

                if not fetch_all and len(collected) >= target_count:
                    break

            if not fetch_all and len(collected) >= target_count:
                break

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return collected

    def fetch_video_and_comments(
        self,
        video_url: str,
        *,
        fetch_all_comments: Optional[bool] = None,
        max_comments: Optional[int] = None,
        order: Optional[str] = None,
    ) -> tuple[RawVideoMetadata, list[RawComment]]:
        metadata = self.fetch_video_metadata(video_url)
        comments = self.fetch_comments(
            video_id=metadata.video_id,
            fetch_all_comments=fetch_all_comments,
            max_comments=max_comments,
            order=order,
        )
        return metadata, comments

    def _get(self, endpoint: str, params: dict) -> dict:
        response = requests.get(
            f"{YOUTUBE_API_BASE}/{endpoint}",
            params={**params, "key": self.api_key},
            timeout=self.timeout,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text[:500]
            raise YouTubeProviderError(
                f"YouTube API request failed for endpoint '{endpoint}': {detail}"
            ) from exc

        payload = response.json()
        if "error" in payload:
            raise YouTubeProviderError(
                f"YouTube API error on endpoint '{endpoint}': {payload['error']}"
            )

        return payload


def normalize_comment_text(text: str) -> str:
    return " ".join(text.split()).strip()


def comments_to_dicts(comments: list[RawComment]) -> list[dict]:
    return [
        {
            "comment_id": comment.comment_id,
            "published_at": comment.published_at,
            "like_count": comment.like_count,
            "reply_count": comment.reply_count,
            "text_original": comment.text_original,
            "text_clean": normalize_comment_text(comment.text_original),
            "author_display_name": comment.author_display_name,
        }
        for comment in comments
    ]