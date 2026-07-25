"""FastAPI app exposing the unified voice/text agent over a WebSocket.

Run with: uvicorn server.app:app --reload
"""
from dotenv import load_dotenv

# Must run before anything below (transitively) builds the agent graph or
# reads GROQ_API_KEY / LANGFUSE_* — loads the root .env once at process
# startup. See agent/tracing.py for what Langfuse wiring does with it.
load_dotenv()

from fastapi import FastAPI  # noqa: E402

from server.ws import router as ws_router  # noqa: E402

app = FastAPI(title="Voice Agent")
app.include_router(ws_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
