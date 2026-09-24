import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="MCP Security Gateway")
DOWNSTREAM_URL = os.getenv("DOWNSTREAM_URL", "http://127.0.0.1:9001/mcp")

ROLE_BY_TOKEN = {
    "admin-token": "admin",
    "viewer-token": "viewer",
}


def jsonrpc_error(request_id: Any, code: int, message: str, status: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        },
    )


def role_from_authorization(value: str | None) -> str | None:
    if not value or not value.startswith("Bearer "):
        return None
    token = value[7:].strip()
    return ROLE_BY_TOKEN.get(token)


@app.post("/mcp")
async def proxy_mcp(request: Request, authorization: str | None = Header(default=None)) -> Response:
    try:
        payload = await request.json()
    except Exception:
        return jsonrpc_error(None, -32700, "Parse error")

    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        return jsonrpc_error(payload.get("id") if isinstance(payload, dict) else None, -32600, "Invalid Request")

    request_id = payload.get("id")
    method = payload.get("method")

    if method == "tools/call":
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            return jsonrpc_error(request_id, -32602, "Invalid params")
        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            return jsonrpc_error(request_id, -32602, "Invalid params")

        if tool_name.startswith("admin_") and role_from_authorization(authorization) != "admin":
            return jsonrpc_error(request_id, -32001, "Unauthorized Tool Call")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            upstream = await client.post(
                DOWNSTREAM_URL,
                json=payload,
                headers={"content-type": "application/json"},
            )
    except httpx.RequestError:
        return jsonrpc_error(request_id, -32000, "Downstream MCP server unavailable")

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )
