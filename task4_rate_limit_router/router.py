import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, Query, Request
from fastapi.responses import JSONResponse

from .rate_limiter import SQLiteTokenSlidingWindow

PRIMARY_URL = os.getenv("PRIMARY_URL", "http://127.0.0.1:9201/v1/completions")
BACKUP_URL = os.getenv("BACKUP_URL", "http://127.0.0.1:9202/v1/completions")
DB_PATH = os.getenv("RATE_LIMIT_DB", "rate_limit.db")
limiter = SQLiteTokenSlidingWindow(DB_PATH, limit=50_000, window_seconds=60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await limiter.initialize()
    yield


app = FastAPI(title="Resilient LLM Router", lifespan=lifespan)


def gateway_error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
    )


def estimate_tokens(payload: dict) -> int:
    # Lightweight assessment estimator. Production systems should use the
    # tokenizer matching the selected model.
    prompt = str(payload.get("prompt", ""))
    input_estimate = max(1, (len(prompt) + 3) // 4)
    output_budget = int(payload.get("max_tokens", 0) or 0)
    return input_estimate + max(0, output_budget)


async def call_provider(url: str, payload: dict, timeout_seconds: float, simulate: str | None = None):
    effective_url = url
    params = {}
    if simulate:
        params["simulate"] = simulate

    async with httpx.AsyncClient() as client:
        return await client.post(
            effective_url,
            json=payload,
            params=params,
            timeout=httpx.Timeout(timeout_seconds),
        )


@app.post("/v1/completions")
async def completions(
    request: Request,
    x_api_key: str | None = Header(default=None),
    simulate_primary: str | None = Query(default=None),
):
    if not x_api_key:
        return gateway_error(401, "missing_api_key", "X-API-Key header is required")

    try:
        payload = await request.json()
    except Exception:
        return gateway_error(400, "invalid_json", "Invalid JSON body")

    if not isinstance(payload, dict) or not isinstance(payload.get("prompt", ""), str):
        return gateway_error(400, "invalid_request", "Expected a JSON object with a string prompt")
    max_tokens = payload.get("max_tokens", 0)
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 0:
        return gateway_error(400, "invalid_request", "max_tokens must be a nonnegative integer")

    estimated_tokens = estimate_tokens(payload)
    allowed, remaining = await limiter.reserve(x_api_key, estimated_tokens)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "token_rate_limit_exceeded",
                    "message": "Tenant token-per-minute limit exceeded",
                },
                "remaining_tokens": remaining,
            },
        )

    should_fallback = False

    try:
        primary = await call_provider(
            PRIMARY_URL,
            payload,
            timeout_seconds=3.0,
            simulate=simulate_primary,
        )
        if primary.status_code == 429:
            should_fallback = True
        elif primary.is_error:
            return gateway_error(502, "primary_provider_error", "Primary model provider failed")
        else:
            return JSONResponse(status_code=primary.status_code, content=primary.json())
    except httpx.TimeoutException:
        should_fallback = True
    except httpx.RequestError:
        return gateway_error(502, "primary_provider_unavailable", "Primary model provider unavailable")
    except Exception:
        return gateway_error(500, "gateway_internal_error", "Gateway could not process the request")

    if should_fallback:
        try:
            backup = await call_provider(BACKUP_URL, payload, timeout_seconds=10.0)
            if backup.is_error:
                return gateway_error(502, "backup_provider_error", "Backup model provider failed")
            body = backup.json()
            if isinstance(body, dict):
                body["gateway_fallback"] = True
            return JSONResponse(status_code=backup.status_code, content=body)
        except (httpx.TimeoutException, httpx.RequestError):
            return gateway_error(503, "all_providers_unavailable", "No model provider is currently available")
        except Exception:
            return gateway_error(500, "gateway_internal_error", "Gateway could not process the request")

    return gateway_error(500, "gateway_internal_error", "Gateway routing failure")
