from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


class UpstreamMcpTests(unittest.TestCase):
    @staticmethod
    def _module():
        path = Path(__file__).resolve().parents[1] / "mcp" / "tikhub_xhs_mcp.py"
        spec = importlib.util.spec_from_file_location("tikhub_xhs_mcp_for_test", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_tool_discovery_and_missing_key_error(self) -> None:
        root = Path(__file__).resolve().parents[1]
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "xhs_search_notes", "arguments": {"keyword": "AI Agent 实习"}},
            },
        ]
        result = subprocess.run(
            [sys.executable, str(root / "mcp" / "tikhub_xhs_mcp.py")],
            input="\n".join(json.dumps(item, ensure_ascii=False) for item in messages) + "\n",
            text=True,
            capture_output=True,
            check=True,
            env={"PATH": ""},
        )
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(rows[1]["result"]["tools"]), 20)
        tools = {item["name"]: item for item in rows[1]["result"]["tools"]}
        search_properties = tools["xhs_search_notes"]["inputSchema"]["properties"]
        self.assertIn("search_id", search_properties)
        self.assertIn("search_session_id", search_properties)
        self.assertIn("time_filter", search_properties)
        self.assertIn("index", tools["xhs_get_note_sub_comments"]["inputSchema"]["properties"])
        error = json.loads(rows[2]["result"]["content"][0]["text"])["error"]
        self.assertEqual(error["code"], "MISSING_API_KEY")

    def test_current_search_pagination_arguments_reach_tikhub_request(self) -> None:
        module = self._module()
        arguments = {
            "keyword": "AI Agent",
            "page": 2,
            "time_filter": "一周内",
            "search_id": "search-1",
            "search_session_id": "session-1",
        }
        with patch.object(module, "_request", return_value={"code": 200, "data": {}}) as request:
            module._tool_call("xhs_search_notes", arguments)
        params = request.call_args.args[1]
        self.assertEqual(params["time_filter"], "一周内")
        self.assertEqual(params["search_id"], "search-1")
        self.assertEqual(params["search_session_id"], "session-1")


if __name__ == "__main__":
    unittest.main()
