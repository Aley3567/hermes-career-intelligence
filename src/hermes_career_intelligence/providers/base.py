"""Platform-neutral contracts for social research providers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import Field

from ..models import ContentType, Platform, StrictModel


class MCPToolClient(Protocol):
    """Minimal boundary required from an MCP transport."""

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, tool: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.tool = tool
        self.retryable = retryable


class NormalizedCreator(StrictModel):
    platform: Platform
    platform_creator_id: str
    nickname: str
    bio: str = ""
    profile_url: str | None = None
    avatar_url: str | None = None
    followers: int | None = Field(default=None, ge=0)
    following: int | None = Field(default=None, ge=0)
    likes_and_collects: int | None = Field(default=None, ge=0)
    raw_locator: str | None = None


class NormalizedContent(StrictModel):
    platform: Platform
    platform_content_id: str
    creator_id: str | None = None
    creator_nickname: str | None = None
    title: str = ""
    text: str = ""
    content_type: ContentType
    url: str
    published_at: datetime | None = None
    like_count: int = Field(default=0, ge=0)
    comment_count: int = Field(default=0, ge=0)
    collect_count: int = Field(default=0, ge=0)
    share_count: int = Field(default=0, ge=0)
    media_urls: list[str] = Field(default_factory=list)


class NormalizedComment(StrictModel):
    platform: Platform
    platform_comment_id: str
    content_id: str
    creator_id: str | None = None
    creator_nickname: str | None = None
    text: str
    like_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)
    published_at: datetime | None = None


class PageMetadata(StrictModel):
    cache_url: str | None = None
    next_cursor: str | None = None
    search_id: str | None = None
    search_session_id: str | None = None
    has_more: bool = False
    provider_request_id: str | None = None


class ContentPage(PageMetadata):
    items: list[NormalizedContent]


class CreatorPage(PageMetadata):
    items: list[NormalizedCreator]


class CommentPage(PageMetadata):
    items: list[NormalizedComment]
