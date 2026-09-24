import asyncio

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(title="Mock Streaming LLM")


async def tokens():
    chunks = [
        "Contact the customer at jo",
        "rdan.lee@example.com. Their SS",
        "N is 123-45-6789. Card 4111 1111 ",
        "1111 1111 should never be exposed.",
    ]
    for chunk in chunks:
        await asyncio.sleep(0.05)
        yield chunk


@app.post("/v1/generate")
async def generate():
    return StreamingResponse(tokens(), media_type="text/plain")
