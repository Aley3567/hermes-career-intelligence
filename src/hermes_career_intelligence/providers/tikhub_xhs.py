"""Xiaohongshu adapter over the upstream TikHub MCP tool surface.

TikHub response shapes can contain nested `data` envelopes and note-card wrappers.
This module isolates those provider details from the Career Intelligence domain.
It deliberately discards the full raw response after normalization.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable

from ..models import ContentType, Platform
from .base import (
    CommentPage,
    ContentPage,
    CreatorPage,
    MCPToolClient,
    NormalizedComment,
    NormalizedContent,
    NormalizedCreator,
    PageMetadata,
    ProviderError,
)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first(source: dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return default


def _count(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    text = str(value).strip().replace(",", "")
    multiplier = 1
    if text.endswith("万"):
        multiplier, text = 10_000, text[:-1]
    elif text.lower().endswith("w"):
        multiplier, text = 10_000, text[:-1]
    try:
        return max(0, int(float(text) * multiplier))
    except ValueError:
        return 0


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)) or str(value).isdigit():
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric /= 1000
        try:
            return datetime.fromtimestamp(numeric, UTC)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _find_list(value: Any, candidate_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    """Find the first record list under known provider keys, bounded by depth."""
    queue: list[tuple[Any, int]] = [(value, 0)]
    while queue:
        current, depth = queue.pop(0)
        if depth > 4 or not isinstance(current, dict):
            continue
        for key in candidate_keys:
            candidate = current.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        for key in ("data", "result", "response"):
            nested = current.get(key)
            if isinstance(nested, dict):
                queue.append((nested, depth + 1))
    return []


def _find_record(value: Any, candidate_keys: tuple[str, ...]) -> dict[str, Any]:
    current = _mapping(value)
    for _ in range(5):
        for key in candidate_keys:
            nested = current.get(key)
            if isinstance(nested, dict):
                return nested
        nested_data = current.get("data")
        if not isinstance(nested_data, dict):
            return current
        current = nested_data
    return current


def _find_value(value: Any, candidate_keys: tuple[str, ...]) -> Any:
    queue: list[tuple[Any, int]] = [(value, 0)]
    while queue:
        current, depth = queue.pop(0)
        if depth > 4 or not isinstance(current, dict):
            continue
        found = _first(current, candidate_keys)
        if found not in (None, ""):
            return found
        for key in ("data", "result", "response", "cursor"):
            nested = current.get(key)
            if isinstance(nested, dict):
                queue.append((nested, depth + 1))
    return None


def _page_metadata(envelope: dict[str, Any], payload: Any) -> PageMetadata:
    cursor = _find_value(payload, ("next_cursor", "nextCursor", "cursor"))
    if isinstance(cursor, dict):
        cursor = _first(cursor, ("cursor", "next_cursor", "id"))
    search_id = _find_value(payload, ("search_id", "searchId"))
    search_session_id = _find_value(payload, ("search_session_id", "searchSessionId"))
    return PageMetadata(
        cache_url=str(envelope.get("cache_url")) if envelope.get("cache_url") else None,
        next_cursor=str(cursor) if cursor not in (None, "") else None,
        search_id=str(search_id) if search_id else None,
        search_session_id=str(search_session_id) if search_session_id else None,
        has_more=bool(_find_value(payload, ("has_more", "hasMore", "more")) or False),
        provider_request_id=str(envelope.get("request_id")) if envelope.get("request_id") else None,
    )


def _media_urls(note: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("video_url", "play_url", "master_url", "url"):
        value = note.get(key)
        if isinstance(value, str) and value.startswith("http"):
            urls.append(value)
    for key in ("image_list", "images", "imageList"):
        for image in note.get(key) or []:
            if isinstance(image, str) and image.startswith("http"):
                urls.append(image)
            elif isinstance(image, dict):
                value = _first(image, ("url", "url_default", "original", "preview"))
                if isinstance(value, str) and value.startswith("http"):
                    urls.append(value)
    return list(dict.fromkeys(urls))


class TikHubXHSProvider:
    platform = Platform.XIAOHONGSHU

    def __init__(self, client: MCPToolClient) -> None:
        self.client = client

    def _call(self, tool: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], Any]:
        response = self.client.call(tool, {key: value for key, value in arguments.items() if value not in (None, "")})
        if not isinstance(response, dict):
            raise ProviderError("INVALID_RESPONSE", "TikHub returned a non-object response", tool=tool)
        error = _mapping(response.get("error"))
        code = response.get("code")
        if response.get("ok") is False or error or (code is not None and code != 200):
            safe_code = str(_first(error, ("code",), code or "PROVIDER_ERROR"))
            status = _count(error.get("status"))
            retryable = status == 429 or status >= 500 or safe_code in {"TimeoutError", "HTTP_ERROR"}
            raise ProviderError(safe_code, "TikHub request failed; inspect structured provider logs", tool=tool, retryable=retryable)
        if "data" not in response:
            raise ProviderError("MISSING_DATA", "TikHub response has no data field", tool=tool)
        payload = response["data"]
        if payload is None or isinstance(payload, str):
            raise ProviderError("UPSTREAM_DATA_ERROR", "TikHub returned unusable upstream data", tool=tool)
        return response, payload

    @staticmethod
    def _identity(note_id: str | None, share_text: str | None) -> dict[str, str]:
        if not note_id and not share_text:
            raise ValueError("note_id or share_text is required")
        return {"note_id": note_id or "", "share_text": share_text or ""}

    @staticmethod
    def _user_identity(user_id: str | None, share_text: str | None) -> dict[str, str]:
        if not user_id and not share_text:
            raise ValueError("user_id or share_text is required")
        return {"user_id": user_id or "", "share_text": share_text or ""}

    def _creator(self, value: dict[str, Any]) -> NormalizedCreator:
        user = _find_record(value, ("user", "author", "user_info", "basic_info"))
        creator_id = str(_first(user, ("user_id", "userid", "id", "red_id", "sec_uid"), ""))
        if not creator_id:
            raise ProviderError("MISSING_CREATOR_ID", "Creator response has no stable identifier", tool="normalize_creator")
        interactions = _mapping(_first(user, ("interactions", "interaction_info", "stats"), {}))
        profile_url = _first(user, ("profile_url", "share_url", "url"))
        return NormalizedCreator(
            platform=self.platform,
            platform_creator_id=creator_id,
            nickname=str(_first(user, ("nickname", "name", "nick_name"), "")),
            bio=str(_first(user, ("desc", "bio", "description"), "")),
            profile_url=str(profile_url) if profile_url else None,
            avatar_url=str(_first(user, ("avatar", "avatar_url", "image"))) if _first(user, ("avatar", "avatar_url", "image")) else None,
            followers=_count(_first(user, ("followers", "fans", "fans_count"), interactions.get("fans"))),
            following=_count(_first(user, ("following", "follows", "follow_count"), interactions.get("follows"))),
            likes_and_collects=_count(_first(user, ("liked", "likes", "liked_count"), interactions.get("interaction"))),
            raw_locator=str(_first(user, ("red_id", "user_id", "id"), creator_id)),
        )

    def _content(self, value: dict[str, Any]) -> NormalizedContent:
        note = _mapping(_first(value, ("note_card", "note", "note_info", "item"), value))
        note_id = str(_first(note, ("note_id", "id", "noteId"), _first(value, ("note_id", "id"), "")))
        if not note_id:
            raise ProviderError("MISSING_CONTENT_ID", "Note response has no stable identifier", tool="normalize_content")
        user = _mapping(_first(note, ("user", "author", "user_info"), {}))
        interact = _mapping(_first(note, ("interact_info", "interaction_info", "stats"), {}))
        kind = str(_first(note, ("type", "note_type"), "normal")).lower()
        content_type = ContentType.VIDEO if "video" in kind else ContentType.NOTE
        url = _first(note, ("share_url", "note_url", "url")) or f"https://www.xiaohongshu.com/explore/{note_id}"
        return NormalizedContent(
            platform=self.platform,
            platform_content_id=note_id,
            creator_id=str(_first(user, ("user_id", "id", "userid"))) if _first(user, ("user_id", "id", "userid")) else None,
            creator_nickname=str(_first(user, ("nickname", "name"))) if _first(user, ("nickname", "name")) else None,
            title=str(_first(note, ("display_title", "title"), "")),
            text=str(_first(note, ("desc", "content", "text"), "")),
            content_type=content_type,
            url=str(url),
            published_at=_timestamp(_first(note, ("time", "timestamp", "publish_time", "create_time"))),
            like_count=_count(_first(interact, ("liked_count", "like_count", "likes"))),
            comment_count=_count(_first(interact, ("comment_count", "comments"))),
            collect_count=_count(_first(interact, ("collected_count", "collect_count", "collects"))),
            share_count=_count(_first(interact, ("share_count", "shares"))),
            media_urls=_media_urls(note),
        )

    def _comment(self, value: dict[str, Any], content_id: str) -> NormalizedComment:
        user = _mapping(_first(value, ("user", "author", "user_info"), {}))
        comment_id = str(_first(value, ("comment_id", "id"), ""))
        if not comment_id:
            raise ProviderError("MISSING_COMMENT_ID", "Comment response has no stable identifier", tool="normalize_comment")
        return NormalizedComment(
            platform=self.platform,
            platform_comment_id=comment_id,
            content_id=content_id,
            creator_id=str(_first(user, ("user_id", "id", "userid"))) if _first(user, ("user_id", "id", "userid")) else None,
            creator_nickname=str(_first(user, ("nickname", "name"))) if _first(user, ("nickname", "name")) else None,
            text=str(_first(value, ("content", "text"), "")),
            like_count=_count(_first(value, ("like_count", "liked_count", "likes"))),
            reply_count=_count(_first(value, ("sub_comment_count", "reply_count", "replies"))),
            published_at=_timestamp(_first(value, ("create_time", "time", "timestamp"))),
        )

    def search_notes(
        self,
        keyword: str,
        *,
        page: int = 1,
        sort_type: str | None = None,
        note_type: str | None = None,
        time_filter: str | None = None,
        search_id: str | None = None,
        search_session_id: str | None = None,
        source: str | None = None,
        ai_mode: int | None = None,
    ) -> ContentPage:
        if not keyword.strip():
            raise ValueError("keyword must not be blank")
        if page < 1:
            raise ValueError("page must be at least 1")
        envelope, payload = self._call(
            "xhs_search_notes",
            {
                "keyword": keyword.strip(),
                "page": page,
                "sort_type": sort_type,
                "note_type": note_type,
                "time_filter": time_filter,
                "search_id": search_id,
                "search_session_id": search_session_id,
                "source": source,
                "ai_mode": ai_mode,
            },
        )
        records = _find_list(payload, ("items", "notes", "note_list", "list"))
        meta = _page_metadata(envelope, payload)
        return ContentPage(items=[self._content(record) for record in records], **meta.model_dump())

    def get_note(self, *, note_id: str | None = None, share_text: str | None = None, note_type: str = "auto") -> NormalizedContent:
        arguments = {**self._identity(note_id, share_text), "note_type": note_type}
        _, payload = self._call("xhs_get_note_detail", arguments)
        return self._content(_find_record(payload, ("note", "note_info", "item")))

    def get_creator(self, *, user_id: str | None = None, share_text: str | None = None) -> NormalizedCreator:
        _, payload = self._call("xhs_get_user_info", self._user_identity(user_id, share_text))
        return self._creator(payload)

    def search_creators(self, keyword: str, *, page: int = 1) -> CreatorPage:
        if not keyword.strip():
            raise ValueError("keyword must not be blank")
        if page < 1:
            raise ValueError("page must be at least 1")
        envelope, payload = self._call("xhs_search_users", {"keyword": keyword.strip(), "page": page})
        records = _find_list(payload, ("items", "users", "user_list", "list"))
        meta = _page_metadata(envelope, payload)
        return CreatorPage(items=[self._creator(record) for record in records], **meta.model_dump())

    def get_creator_notes(self, *, user_id: str | None = None, share_text: str | None = None, cursor: str | None = None) -> ContentPage:
        arguments = {**self._user_identity(user_id, share_text), "cursor": cursor}
        envelope, payload = self._call("xhs_get_user_posted_notes", arguments)
        records = _find_list(payload, ("items", "notes", "note_list", "list"))
        meta = _page_metadata(envelope, payload)
        return ContentPage(items=[self._content(record) for record in records], **meta.model_dump())

    def get_comments(self, *, note_id: str | None = None, share_text: str | None = None, cursor: str | None = None) -> CommentPage:
        arguments = {**self._identity(note_id, share_text), "cursor": cursor}
        envelope, payload = self._call("xhs_get_note_comments", arguments)
        records = _find_list(payload, ("comments", "comment_list", "items", "list"))
        content_id = note_id or str(_find_value(payload, ("note_id", "noteId")) or "shared-note")
        meta = _page_metadata(envelope, payload)
        return CommentPage(items=[self._comment(record, content_id) for record in records], **meta.model_dump())
