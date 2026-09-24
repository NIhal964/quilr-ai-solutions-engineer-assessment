from fastapi import FastAPI

app = FastAPI(title="Mock Backup Model")


@app.post("/v1/completions")
async def completions():
    return {"provider": "backup", "text": "backup completion"}
