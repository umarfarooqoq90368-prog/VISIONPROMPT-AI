"""Batch video processing API routes for P2-07.

Routes:
    POST /api/batches
    GET /api/batches/{batch_id}
    GET /api/batches/{batch_id}/results
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.services.batch_processing_service import (
    BatchProcessingService,
    BatchStatus,
    create_batch,
    get_batch,
    get_batch_results,
    process_video_in_batch,
    fail_video_in_batch,
)

router = APIRouter()


@router.post("/batches", response_model=dict)
def create_batch(video_filenames: List[str]):
    """Create a new batch for processing the given videos.

    Args:
        video_filenames: List of stored video filenames to include in the batch.

    Returns:
        Batch dict with id, status, and per-video entries.
    """
    return create_batch(video_filenames)


@router.get("/batches/{batch_id}", response_model=dict)
def read_batch(batch_id: str):
    """Get the status of a batch.

    Args:
        batch_id: The batch ID.

    Returns:
        Batch dict with status and per-video entries.
    """
    batch = get_batch(batch_id)
    return batch


@router.get("/batches/{batch_id}/results", response_model=dict)
def read_batch_results(batch_id: str):
    """Get the results of a completed batch.

    Args:
        batch_id: The batch ID.

    Returns:
        Batch results dict.

    Raises:
        HTTPException: If batch not found or not completed.
    """
    batch = get_batch_results(batch_id)
    return batch