from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.videos import router as videos_router

app = FastAPI(
    title="VisionPrompt AI",
    description="Turn Any Video Into a Production-Ready AI Prompt",
    version="0.1.0",
)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(videos_router, prefix="/api", tags=["videos"])


@app.get("/", tags=["root"])
def root():
    """Return the base application info."""
    return {
        "name": "VisionPrompt AI",
        "status": "running",
        "version": "0.1.0",
    }
