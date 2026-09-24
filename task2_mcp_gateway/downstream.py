from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock MCP Downstream")


@app.post("/mcp")
async def mcp(request: Request) -> JSONResponse:
    payload = await request.json()
    request_id = payload.get("id")
    method = payload.get("method")

    if method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {"name": "get_profile", "description": "Read profile"},
                    {"name": "admin_reset_key", "description": "Reset an API key"},
                ]
            },
        })

    if method == "tools/call":
        params = payload.get("params") or {}
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": f"executed:{params.get('name')}"}]
            },
        })

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "Method not found"},
    })
