#!/usr/bin/env python3
"""TikHub Xiaohongshu MCP server (stdio, zero dependency).

Wraps a small, agent-friendly subset of TikHub's Xiaohongshu App V2 API:
notes search, note detail, comments, and user/creator research.

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


def _request(path: str, params: dict) -> dict:
    if not API_KEY:
        return {"ok": False, "error": {"code": "MISSING_API_KEY", "message": "Set TIKHUB_API_KEY (get one at https://tikhub.io)"}}
    query = {k: v for k, v in params.items() if v not in (None, "")}
    url = API_BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json",
            # TikHub's Cloudflare blocks python-urllib's default UA; identify ourselves properly.
            "User-Agent": "hermes-media-suite/1.0 (+https://github.com/chenchen1010/hermes-media-suite)",
        },
    )
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
                _reply(msg_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "tikhub-xhs", "version": "1.0.0"}})
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
