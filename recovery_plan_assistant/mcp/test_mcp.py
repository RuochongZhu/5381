from __future__ import annotations

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SERVER = "http://127.0.0.1:8000/mcp"


def mcp_request(method: str, params: dict | None = None, request_id: int = 1) -> dict:
    body = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    response = requests.post(SERVER, json=body, timeout=30)
    response.raise_for_status()
    return response.json()["result"]


def main() -> None:
    init = mcp_request(
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "clientInfo": {"name": "recovery-test-client", "version": "0.1.0"},
            "capabilities": {},
        },
    )
    tools = mcp_request("tools/list")
    search_result = mcp_request(
        "tools/call",
        {
            "name": "search_recovery_projects",
            "arguments": {
                "query": "backup power shelter flood",
                "community": "Red Hook",
                "top_n": 3,
            },
        },
    )

    report = [
        "MCP TEST",
        "",
        f"Server: {init['serverInfo']['name']} v{init['serverInfo']['version']}",
        "",
        "Available tools:",
        json.dumps(tools, indent=2),
        "",
        "Direct tool call result:",
        search_result["content"][0]["text"],
    ]
    output = "\n".join(report)
    print(output)
    output_path = ROOT / "output" / "07_mcp_test.txt"
    output_path.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
