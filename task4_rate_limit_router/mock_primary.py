import asyncio
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock Primary Model")


@app.post("/v1/completions")
async def completions(simulate: str | None = Query(default=None)):
    if simulate == "429":
        return JSONResponse(status_code=429, content={"error": "provider throttled"})
    if simulate == "timeout":
        await asyncio.sleep(4)
    return {"provider": "primary", "text": "primary completion"}
