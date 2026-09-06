from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class UpstreamMcpTests(unittest.TestCase):
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
        error = json.loads(rows[2]["result"]["content"][0]["text"])["error"]
        self.assertEqual(error["code"], "MISSING_API_KEY")


if __name__ == "__main__":
    unittest.main()
