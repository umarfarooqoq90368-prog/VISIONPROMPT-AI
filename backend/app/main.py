from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.batches import router as batches_router
from app.api.v1 import router as v1_router
from app.api.v1_auth import router as auth_router
from app.api.health import router as health_router
from app.api.videos import router as videos_router

app = FastAPI(
    title="VisionPrompt AI",
    description="Turn Any Video Into a Production-Ready AI Prompt",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "https://umarfarooqoq90368-prog.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
app.include_router(videos_router, prefix="/api", tags=["videos"])
app.include_router(batches_router, prefix="/api", tags=["batches"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])


@app.get("/", tags=["root"])
def root():
    """Return the base application info."""
    return {
        "name": "VisionPrompt AI",
        "status": "running",
        "version": "0.1.0",
    }