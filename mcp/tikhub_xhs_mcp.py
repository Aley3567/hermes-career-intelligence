#!/usr/bin/env python3
"""TikHub social-media MCP server (stdio, zero dependency).

Wraps an agent-friendly subset of TikHub's APIs across four platforms:
- Xiaohongshu (App V2): notes search / detail / comments / creators
- Douyin: video by share url / keyword search / comments
- WeChat MP (公众号): article content by url / account article list
- WeChat Channels (视频号): search / video detail

Usage:
    export TIKHUB_API_KEY=...   # create one at https://tikhub.io
    python3 tikhub_xhs_mcp.py   # started by your MCP client, not by hand

Every TikHub request is billed per call (see tikhub.io pricing). Each
response includes a `cache_url` that can be re-fetched within 24h for free —
prefer it when you need the same data twice.

All tools accept either an explicit id (note_id / user_id) or `share_text`
(the share link / share text copied from the Xiaohongshu app), so agents can
paste whatever the user provides.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_BASE = os.getenv("TIKHUB_BASE_URL", "https://api.tikhub.io").rstrip("/")
API_KEY = os.getenv("TIKHUB_API_KEY", "").strip()
API_TIMEOUT_SECONDS = max(10, int(float(os.getenv("TIKHUB_TIMEOUT_SECONDS", "60") or "60")))

APP_V2 = "/api/v1/xiaohongshu/app_v2"

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _request(path: str, params: dict | None = None, json_body: dict | None = None) -> dict:
    if not API_KEY:
        return {"ok": False, "error": {"code": "MISSING_API_KEY", "message": "Set TIKHUB_API_KEY (get one at https://tikhub.io)"}}
    url = API_BASE + path
    if params:
        query = {k: v for k, v in params.items() if v not in (None, "")}
        if query:
            url += "?" + urllib.parse.urlencode(query)
    body = None
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        # TikHub's Cloudflare blocks python-urllib's default UA; identify ourselves properly.
        "User-Agent": "hermes-media-suite/1.0 (+https://github.com/chenchen1010/hermes-media-suite)",
    }
    if json_body is not None:
        body = json.dumps({k: v for k, v in json_body.items() if v not in (None, "")}, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method="POST" if json_body is not None else "GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        return {"ok": False, "error": {"code": "HTTP_ERROR", "status": int(exc.code), "message": str(exc), "body": body[:1000]}}
    except Exception as exc:
        return {"ok": False, "error": {"code": type(exc).__name__, "message": str(exc)}}


def _looks_ok(resp: dict) -> bool:
    return isinstance(resp, dict) and resp.get("code") == 200 and bool(resp.get("data"))


ID_OR_SHARE = {
    "note_id": {"type": "string", "description": "笔记 ID（和 share_text 二选一）"},
    "share_text": {"type": "string", "description": "小红书 App 里复制的分享链接/分享口令（和 note_id 二选一）"},
}

TOOLS = [
    {
        "name": "xhs_search_notes",
        "description": "按关键词搜索小红书笔记。适合选题调研、看一个话题下大家都在发什么。每次调用按 TikHub 计费。",
        "inputSchema": {
            "type": "object",
            "required": ["keyword"],
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
                "page": {"type": "integer", "minimum": 1, "default": 1, "description": "页码，翻页时递增"},
                "sort_type": {"type": "string", "description": "排序方式，不填为综合排序；具体可选值以 TikHub 文档为准"},
                "note_type": {"type": "string", "description": "笔记类型过滤（如 全部/图文/视频），具体可选值以 TikHub 文档为准"},
            },
        },
    },
    {
        "name": "xhs_get_note_detail",
        "description": "获取单篇笔记详情（标题、正文、作者、互动数、图片/视频信息）。note_type 不确定时用 auto：先按图文查，失败再按视频查（auto 最多产生两次计费调用）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                **ID_OR_SHARE,
                "note_type": {"type": "string", "enum": ["auto", "image", "video", "mixed"], "default": "auto", "description": "笔记类型；已知类型时明确指定可省一次调用"},
            },
        },
    },
    {
        "name": "xhs_get_note_comments",
        "description": "获取笔记一级评论列表。评论区是用户真实语言和需求的富矿。传 cursor 翻页。",
        "inputSchema": {
            "type": "object",
            "properties": {
                **ID_OR_SHARE,
                "cursor": {"type": "string", "description": "翻页游标，来自上一页响应"},
            },
        },
    },
    {
        "name": "xhs_get_note_sub_comments",
        "description": "获取某条评论下的二级回复。",
        "inputSchema": {
            "type": "object",
            "required": ["comment_id"],
            "properties": {
                "comment_id": {"type": "string", "description": "一级评论 ID"},
                **ID_OR_SHARE,
                "cursor": {"type": "string", "description": "翻页游标"},
            },
        },
    },
    {
        "name": "xhs_get_user_info",
        "description": "获取用户/博主主页信息（昵称、简介、粉丝量等）。适合对标账号分析。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID（和 share_text 二选一）"},
                "share_text": {"type": "string", "description": "用户主页的分享链接/口令（和 user_id 二选一）"},
            },
        },
    },
    {
        "name": "xhs_get_user_posted_notes",
        "description": "获取某个用户发布的笔记列表。适合拆解对标博主的内容结构。传 cursor 翻页。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID（和 share_text 二选一）"},
                "share_text": {"type": "string", "description": "用户主页的分享链接/口令（和 user_id 二选一）"},
                "cursor": {"type": "string", "description": "翻页游标"},
            },
        },
    },
    {
        "name": "xhs_search_users",
        "description": "按关键词搜索小红书用户/博主。适合批量找一个领域的对标账号。",
        "inputSchema": {
            "type": "object",
            "required": ["keyword"],
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
                "page": {"type": "integer", "minimum": 1, "default": 1},
            },
        },
    },
    {
        "name": "douyin_fetch_video_by_share_url",
        "description": "用抖音分享链接直接获取视频完整数据（标题、文案、作者、互动数、播放地址等）。丢一条分享链接进来即可，是处理'收藏的抖音视频'的主力工具。",
        "inputSchema": {
            "type": "object",
            "required": ["share_url"],
            "properties": {"share_url": {"type": "string", "description": "抖音 App 里复制的分享链接（v.douyin.com 短链或完整链接均可）"}},
        },
    },
    {
        "name": "douyin_search_videos",
        "description": "抖音关键词综合搜索。适合看一个话题在抖音的内容生态和爆款角度。",
        "inputSchema": {
            "type": "object",
            "required": ["keyword"],
            "properties": {
                "keyword": {"type": "string"},
                "cursor": {"type": "integer", "description": "翻页游标，来自上一页响应"},
                "sort_type": {"type": "string", "description": "排序方式，不填为综合；具体可选值以 TikHub 文档为准"},
                "publish_time": {"type": "string", "description": "发布时间过滤，具体可选值以 TikHub 文档为准"},
            },
        },
    },
    {
        "name": "douyin_fetch_video_comments",
        "description": "获取抖音视频评论。aweme_id 从视频数据里拿。",
        "inputSchema": {
            "type": "object",
            "required": ["aweme_id"],
            "properties": {
                "aweme_id": {"type": "string"},
                "cursor": {"type": "integer"},
                "count": {"type": "integer", "description": "单页数量"},
            },
        },
    },
    {
        "name": "wechat_search",
        "description": "微信搜一搜全局搜索：一个入口覆盖公众号账号、文章、视频号视频、直播。看一个话题在微信生态里的内容分布。",
        "inputSchema": {
            "type": "object",
            "required": ["keyword"],
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词（1-100 字）"},
                "business_type": {"type": "string", "enum": ["all", "account", "article", "video", "live_stream"], "default": "all", "description": "垂类：综合/公众号/文章/视频号视频/直播"},
                "sort": {"type": "string", "enum": ["default", "latest", "hot"], "description": "排序：相关性/最新/最热"},
                "publish_time": {"type": "string", "enum": ["all", "day", "week", "half_year"], "description": "发布时间过滤"},
                "cursor": {"type": "string", "description": "翻页游标：首页留空，翻页传上一页响应返回的 cursor"},
            },
        },
    },
    {
        "name": "wechat_mp_fetch_article",
        "description": "用公众号文章链接获取文章完整内容（结构化正文）。是处理'收藏的公众号文章'的主力工具——拿到正文后可直接交给整理流程。",
        "inputSchema": {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "description": "公众号文章链接（https://mp.weixin.qq.com/s/… 或带 __biz 的长链）"},
                "raw": {"type": "boolean", "default": False, "description": "False=精简解析结构（默认，省 token）；True=原始响应"},
            },
        },
    },
    {
        "name": "wechat_mp_fetch_account_articles",
        "description": "获取某个公众号的文章列表。适合拆解一个对标公众号在持续发什么。",
        "inputSchema": {
            "type": "object",
            "required": ["username"],
            "properties": {
                "username": {"type": "string", "description": "公众号 gh_username（gh_ 开头），可从文章详情数据中获得"},
                "page_size": {"type": "integer", "minimum": 10, "maximum": 20, "default": 20},
                "offset": {"type": "string", "description": "翻页游标（base64），首页留空，翻页传上一页响应的 next_offset"},
            },
        },
    },
    {
        "name": "channels_fetch_video_detail",
        "description": "获取视频号作品详情。直接丢视频号分享短链（https://weixin.qq.com/sph/…）即可，是处理'收藏的视频号视频'的主力工具。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "share_url": {"type": "string", "description": "视频号分享短链（最常用）"},
                "object_id": {"type": "string", "description": "作品 objectId（纯数字，优先级高于 share_url）"},
                "export_id": {"type": "string", "description": "搜索结果中的 exportId（export/ 开头，会过期需尽快用）"},
            },
        },
    },
]


def _tool_call(name: str, args: dict) -> dict:
    note_id = args.get("note_id") or None
    share_text = args.get("share_text") or None
    if name == "xhs_search_notes":
        return _request(APP_V2 + "/search_notes", {
            "keyword": args.get("keyword", ""),
            "page": args.get("page"),
            "sort_type": args.get("sort_type"),
            "note_type": args.get("note_type"),
        })
    if name == "xhs_get_note_detail":
        kind = args.get("note_type") or "auto"
        params = {"note_id": note_id, "share_text": share_text}
        if kind in ("image", "video", "mixed"):
            return _request(APP_V2 + f"/get_{kind}_note_detail", params)
        first = _request(APP_V2 + "/get_image_note_detail", params)
        if _looks_ok(first):
            return first
        second = _request(APP_V2 + "/get_video_note_detail", params)
        if _looks_ok(second):
            return second
        return {"ok": False, "error": {"code": "NOTE_DETAIL_FAILED", "message": "image and video detail both failed"}, "image_attempt": first, "video_attempt": second}
    if name == "xhs_get_note_comments":
        return _request(APP_V2 + "/get_note_comments", {"note_id": note_id, "share_text": share_text, "cursor": args.get("cursor")})
    if name == "xhs_get_note_sub_comments":
        return _request(APP_V2 + "/get_note_sub_comments", {
            "comment_id": args.get("comment_id", ""),
            "note_id": note_id,
            "share_text": share_text,
            "cursor": args.get("cursor"),
        })
    if name == "xhs_get_user_info":
        return _request(APP_V2 + "/get_user_info", {"user_id": args.get("user_id"), "share_text": share_text})
    if name == "xhs_get_user_posted_notes":
        return _request(APP_V2 + "/get_user_posted_notes", {"user_id": args.get("user_id"), "share_text": share_text, "cursor": args.get("cursor")})
    if name == "xhs_search_users":
        return _request(APP_V2 + "/search_users", {"keyword": args.get("keyword", ""), "page": args.get("page")})
    if name == "douyin_fetch_video_by_share_url":
        return _request("/api/v1/douyin/app/v3/fetch_one_video_by_share_url", {"share_url": args.get("share_url", "")})
    if name == "douyin_search_videos":
        return _request("/api/v1/douyin/search/fetch_general_search_v1", json_body={
            "keyword": args.get("keyword", ""),
            "cursor": args.get("cursor"),
            "sort_type": args.get("sort_type"),
            "publish_time": args.get("publish_time"),
        })
    if name == "douyin_fetch_video_comments":
        return _request("/api/v1/douyin/app/v3/fetch_video_comments", {
            "aweme_id": args.get("aweme_id", ""),
            "cursor": args.get("cursor"),
            "count": args.get("count"),
        })
    if name == "wechat_search":
        return _request("/api/v1/wechat_search/v2/fetch_search", json_body={
            "keyword": args.get("keyword", ""),
            "business_type": args.get("business_type") or "all",
            "sort": args.get("sort"),
            "publish_time": args.get("publish_time"),
            "cursor": args.get("cursor"),
            "raw": False,
        })
    if name == "wechat_mp_fetch_article":
        return _request("/api/v1/wechat_mp/v2/fetch_article_detail", json_body={
            "url": args.get("url", ""),
            "raw": bool(args.get("raw", False)),
        })
    if name == "wechat_mp_fetch_account_articles":
        return _request("/api/v1/wechat_mp/v2/fetch_account_articles", json_body={
            "username": args.get("username", ""),
            "page_size": args.get("page_size"),
            "offset": args.get("offset"),
            "raw": False,
        })
    if name == "channels_fetch_video_detail":
        return _request("/api/v1/wechat_channels/v2/fetch_video_detail", json_body={
            "share_url": args.get("share_url"),
            "object_id": args.get("object_id"),
            "export_id": args.get("export_id"),
            "raw": False,
        })
    return {"ok": False, "error": {"code": "UNKNOWN_TOOL", "message": name}}


def _reply(msg_id, result: dict | None = None, error: dict | None = None) -> None:
    payload = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result or {}
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> int:
    for line in sys.stdin:
        try:
            message = json.loads(line)
            method = message.get("method")
            params = message.get("params") or {}
            msg_id = message.get("id")
            if method == "initialize":
                _reply(msg_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "tikhub-social", "version": "1.1.0"}})
            elif method == "tools/list":
                _reply(msg_id, {"tools": TOOLS})
            elif method == "tools/call":
                result = _tool_call(str(params.get("name") or ""), params.get("arguments") or {})
                _reply(msg_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]})
            elif msg_id is not None:
                _reply(msg_id, {})
        except Exception as exc:
            _reply(None, error={"code": -32603, "message": str(exc)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
