import json
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .redactor import StreamingPIIRedactor

app = FastAPI(title="LLM Streaming Guardrail")
UPSTREAM_URL = os.getenv("LLM_UPSTREAM_URL", "http://127.0.0.1:9101/v1/generate")


async def guarded_stream(payload: dict):
    redactor = StreamingPIIRedactor()

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", UPSTREAM_URL, json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    if not chunk:
                        continue
                    redacted = redactor.feed(chunk)
                    if redacted:
                        yield redacted
                tail = redactor.flush()
                if tail:
                    yield tail
    except httpx.HTTPError:
        # Streaming has already started, so emit a sanitized gateway event.
        yield "\n[GatewayError: upstream_generation_failed]\n"


@app.post("/v1/generate")
async def generate(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"code": "invalid_json", "message": "Invalid JSON body"}})

    return StreamingResponse(
        guarded_stream(payload),
        media_type="text/plain; charset=utf-8",
    )
