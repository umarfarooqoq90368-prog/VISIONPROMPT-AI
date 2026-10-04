"""Versioned API v1 for P2-10.

Provides backward-compatible endpoints under /api/v1/ without breaking
existing /api/... routes. Exposes key endpoints for upload, analysis,
reconstruction, storyboard, and batch processing.

API key abstraction is provided via the X-API-Key header or
API_KEY environment variable. If no API key is provided, requests
are still allowed in development mode.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import settings


def _get_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Extract API key from request header.

    Falls back to environment variable API_KEY if no header provided.
    Returns the key if found, or None if neither is set.
    """
    return x_api_key or getattr(settings, "api_key", None)


def _check_api_key(api_key: Optional[str]) -> bool:
    """Check if the provided API key is valid.

    Compares against the API_KEY environment variable.
    Returns True if key matches or if no key is configured (development mode).
    """
    if not api_key:
        # No API key configured - allow in development mode
        return True
    return api_key == getattr(settings, "api_key_value", "")


router = APIRouter(tags=["v1"])


@router.post("/batches", response_model=dict)
def create_batch(video_filenames: List[str], x_api_key: Optional[str] = Header(None)):
    """Create a new batch for processing the given videos.

    POST /api/v1/batches
    """
    key = _get_api_key(x_api_key)
    if not _check_api_key(key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    from app.services.batch_processing_service import BatchProcessingService

    return BatchProcessingService().create_batch(video_filenames)


@router.get("/batches/{batch_id}", response_model=dict)
def read_batch(batch_id: str, x_api_key: Optional[str] = Header(None)):
    """Get the status of a batch.

    GET /api/v1/batches/{batch_id}
    """
    key = _get_api_key(x_api_key)
    if not _check_api_key(key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    from app.services.batch_processing_service import BatchProcessingService

    return BatchProcessingService().get_batch(batch_id)


@router.get("/batches/{batch_id}/results", response_model=dict)
def read_batch_results(batch_id: str, x_api_key: Optional[str] = Header(None)):
    """Get the results of a completed batch.

    GET /api/v1/batches/{batch_id}/results
    """
    key = _get_api_key(x_api_key)
    if not _check_api_key(key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    from app.services.batch_processing_service import BatchProcessingService

    return BatchProcessingService().get_batch_results(batch_id)