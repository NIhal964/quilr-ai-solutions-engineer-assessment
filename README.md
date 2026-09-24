# AI Solutions Engineer Assessment

Python 3.11+ implementation of four practical assessment tasks. The upstream
services and credentials in this repository are local mocks for demonstration.

## Project layout

- `task1_mcp_server/` – official MCP SDK stdio server with strict Pydantic validation.
- `task2_mcp_gateway/` – FastAPI JSON-RPC reverse proxy with role-aware tool authorization.
- `task3_streaming_guardrail/` – streaming LLM gateway with boundary-safe PII redaction.
- `task4_rate_limit_router/` – SQLite-backed token sliding-window limiter with primary/backup routing.
- `tests/` – focused unit tests for validation, authorization, redaction, and token limiting.

## Setup

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

## Task 1 – MCP stdio server

```bash
python -m task1_mcp_server.server
```

For interactive inspection:

```bash
mcp dev task1_mcp_server/server.py
```

The server never uses `print()`. All application logs are configured to `stderr`.
The MCP SDK owns stdout for stdio JSON-RPC traffic.

## Task 2 – MCP security gateway

Start the mock downstream:

```bash
uvicorn task2_mcp_gateway.downstream:app --port 9001
```

Start the gateway in a second terminal:

```bash
uvicorn task2_mcp_gateway.gateway:app --port 9000
```

Viewer request (blocked):

```bash
curl -X POST http://127.0.0.1:9000/mcp \
  -H "Authorization: Bearer viewer-token" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"admin_reset_key\",\"arguments\":{}}}"
```

Admin request (forwarded):

```bash
curl -X POST http://127.0.0.1:9000/mcp \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"admin_reset_key\",\"arguments\":{}}}"
```

Demo tokens are deliberately simple for assessment purposes:

- `admin-token` -> `admin`
- `viewer-token` -> `viewer`

In production, replace this parser with JWT verification / an identity provider.

## Task 3 – streaming PII guardrail

Start mock LLM provider:

```bash
uvicorn task3_streaming_guardrail.mock_provider:app --port 9101
```

Start guardrail:

```bash
uvicorn task3_streaming_guardrail.gateway:app --port 9100
```

Call it:

```bash
curl -N -X POST http://127.0.0.1:9100/v1/generate \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"demo\"}"
```

The gateway retains a rolling tail and any unfinished email token. This allows
regex matching across chunk boundaries. Memory and latency depend on the longest
unfinished token; the regexes are demonstrative and are not a complete PII detector.

## Task 4 – token limiter + fallback

Start mock providers:

```bash
uvicorn task4_rate_limit_router.mock_primary:app --port 9201
uvicorn task4_rate_limit_router.mock_backup:app --port 9202
```

Start router:

```bash
uvicorn task4_rate_limit_router.router:app --port 9200
```

Normal call:

```bash
curl -X POST http://127.0.0.1:9200/v1/completions \
  -H "X-API-Key: tenant-a" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"hello\",\"max_tokens\":50}"
```

Force a primary 429 to exercise fallback:

```bash
curl -X POST "http://127.0.0.1:9200/v1/completions?simulate_primary=429" \
  -H "X-API-Key: tenant-a" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"hello\",\"max_tokens\":50}"
```

## Run tests

```bash
pytest -q
```

## Design notes

1. Protocol-facing errors are sanitized and never include upstream tracebacks.
2. Authorization is performed before forwarding privileged MCP tool calls.
3. Streaming redaction holds unfinished email tokens and uses overlap for fixed-length patterns, so PII split between provider chunks can be detected.
4. The rate limiter stores timestamped token reservations in SQLite and evicts entries older than 60 seconds.
5. The router falls back only for the assessment-defined failure cases: HTTP 429 or a 3000 ms timeout.
