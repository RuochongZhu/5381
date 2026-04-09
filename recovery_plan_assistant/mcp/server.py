from __future__ import annotations

import json
from pathlib import Path
import sys

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared import search_recovery_projects, summarize_sector_counts

app = FastAPI()

TOOLS = [
    {
        "name": "search_recovery_projects",
        "description": "Search the local recovery project dataset for community planning ideas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords describing the need or project type."},
                "community": {"type": "string", "description": "Optional exact community filter."},
                "sector": {"type": "string", "description": "Optional exact sector filter."},
                "top_n": {"type": "integer", "description": "Maximum number of records to return."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "summarize_sector_counts",
        "description": "Count how many recovery projects appear in each sector, optionally within one community.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "community": {"type": "string", "description": "Optional exact community filter."}
            },
            "required": [],
        },
    },
]


def run_tool(name: str, args: dict) -> str:
    if name == "search_recovery_projects":
        return search_recovery_projects(
            query=args.get("query", ""),
            community=args.get("community", ""),
            sector=args.get("sector", ""),
            top_n=args.get("top_n", 4),
        )
    if name == "summarize_sector_counts":
        return summarize_sector_counts(community=args.get("community", ""))
    raise ValueError(f"Unknown tool: {name}")


@app.post("/mcp")
async def mcp_post(request: Request) -> Response:
    body = await request.json()
    method = body.get("method")
    request_id = body.get("id")

    if isinstance(method, str) and method.startswith("notifications/"):
        return Response(status_code=202)

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "recovery-assistant-mcp", "version": "0.1.0"},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            tool_result = run_tool(
                body["params"]["name"],
                body["params"].get("arguments", {}),
            )
            result = {"content": [{"type": "text", "text": tool_result}], "isError": False}
        else:
            raise ValueError(f"Method not found: {method}")
    except Exception as exc:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": str(exc)}}
        )

    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


@app.options("/mcp")
async def mcp_options() -> Response:
    return Response(status_code=204, headers={"Allow": "GET, POST, OPTIONS"})


@app.get("/mcp")
async def mcp_get() -> Response:
    return Response(
        content=json.dumps({"error": "This MCP server uses stateless HTTP. Use POST."}),
        status_code=405,
        headers={"Allow": "GET, POST, OPTIONS"},
        media_type="application/json",
    )
