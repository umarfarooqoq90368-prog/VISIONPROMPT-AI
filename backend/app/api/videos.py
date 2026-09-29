from pathlib import Path
from typing import Literal
from fastapi import APIRouter, File, HTTPException, Path as FastPath, Query, Response, UploadFile
from pydantic import BaseModel, Field

from app.services.frame_service import (
    extract_frames,
    validate_interval,
)
from app.services.prompt_service import PromptGenerationService
from app.services.scene_service import SceneDetectionService
from app.services.subject_service import SubjectTrackingService
from app.services.vision_service import VisionService
from app.services.video_analysis_service import VideoAnalysisService
from app.services.video_service import (
    validate_file_extension,
    validate_file_size,
    get_stored_filepath,
    save_uploaded_file,
)
from app.services.audio_service import AudioService
from app.services.intelligence_service import IntelligenceService
from app.services.advanced_prompt_service import AdvancedPromptService, VALID_STYLES
from app.services.prompt_refinement_service import (
    PromptRefinementService,
    VALID_OPERATIONS as REFINEMENT_OPERATIONS,
)
from app.services.prompt_template_service import (
    PromptTemplateService,
    VALID_TEMPLATES,
)
from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_search_service import PromptSearchService, VALID_SORTS
from app.services.prompt_export_service import PromptExportService, VALID_EXPORT_FORMATS
from app.services.prompt_package_service import PromptPackageService
from app.services.prompt_quality_service import PromptQualityService
from app.services.prompt_improvement_service import PromptImprovementService
from app.services.prompt_comparison_service import PromptComparisonService
from app.services.prompt_readiness_service import PromptReadinessService
from app.services.prompt_readiness_history_service import (
    PromptReadinessHistoryService,
)
from app.services.prompt_readiness_change_service import (
    PromptReadinessChangeService,
)
from app.utils.ffprobe import extract_metadata

router = APIRouter()

STORAGE_DIR = Path("storage/uploads")
FRAME_STORAGE_DIR = Path("storage/frames")

vision_service = VisionService()
analysis_service = VideoAnalysisService()
prompt_service = PromptGenerationService()
scene_service = SceneDetectionService()
subject_service = SubjectTrackingService()
audio_service = AudioService()
intelligence_service = IntelligenceService()
advanced_prompt_service = AdvancedPromptService()
refinement_service = PromptRefinementService()
template_service = PromptTemplateService()
prompt_history_service = PromptHistoryService()
organization_service = PromptOrganizationService(prompt_history_service)
search_service = PromptSearchService(prompt_history_service, organization_service)
export_service = PromptExportService(prompt_history_service, organization_service)
package_service = PromptPackageService(
    prompt_history_service, organization_service, export_service
)
quality_service = PromptQualityService()
improvement_service = PromptImprovementService(quality_service)
comparison_service = PromptComparisonService(
    prompt_history_service, quality_service
)
readiness_service = PromptReadinessService(quality_service)
readiness_history_service = PromptReadinessHistoryService(
    prompt_history_service, readiness_service
)
readiness_change_service = PromptReadinessChangeService(
    prompt_history_service, readiness_service
)


class PromptQualityRequest(BaseModel):
    prompt: str


class PromptImproveRequest(BaseModel):
    prompt: str


class PromptReadinessRequest(BaseModel):
    prompt: str


class PromptRefineRequest(BaseModel):
    operation: str


class PromptTemplateRequest(BaseModel):
    template: str
    custom_instruction: str = ""


class PromptHistoryCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = ""
    source: Literal["advanced_prompt", "refinement", "template", "custom"] = "custom"
    operation: str = ""
    metadata: dict = Field(default_factory=dict)


class PromptTagsRequest(BaseModel):
    tags: list[str]


@router.post("/videos/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file.

    Supported formats: mp4, mov, mkv, webm, avi
    Maximum file size: 500 MB (configurable via MAX_VIDEO_SIZE_MB).
    """
    try:
        validate_file_extension(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        validate_file_size(file)
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))

    try:
        filepath, stored_filename, extension = get_stored_filepath(file.filename)
        file_size = save_uploaded_file(file, filepath)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save the uploaded video.")

    return {
        "success": True,
        "message": "Video uploaded successfully",
        "video": {
            "original_filename": file.filename,
            "stored_filename": stored_filename,
            "file_size": file_size,
            "content_type": file.content_type,
            "extension": extension,
        },
    }


@router.get("/videos/{stored_filename}/metadata")
async def get_video_metadata(stored_filename: str = FastPath(...)):
    """Get technical metadata for an uploaded video.

    Uses the bundled FFmpeg binary via imageio-ffmpeg.
    """
    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()

    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    try:
        metadata = extract_metadata(filepath)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to extract video metadata.")

    return {
        "success": True,
        "message": "Video metadata extracted successfully",
        "video": metadata,
    }


@router.post("/videos/{stored_filename}/frames/extract")
async def extract_video_frames(
    stored_filename: str = FastPath(...),
    interval_seconds: float = Query(default=1.0, ge=0.1, le=60.0),
):
    """Extract JPEG frames from an uploaded video at a given interval.

    interval_seconds: time in seconds between each extracted frame (0.1 to 60).
    """
    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    try:
        validate_interval(interval_seconds)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = extract_frames(stored_filename, interval_seconds)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Frame extraction failed.")

    return {
        "success": True,
        "message": "Frames extracted successfully",
        **result,
    }


@router.post("/videos/{stored_filename}/frames/analyze")
async def analyze_frame(
    stored_filename: str = FastPath(...),
    frame_filename: str = Query(...),
):
    """Analyze an extracted frame using the configured vision model.

    frame_filename: name of the JPEG frame file (e.g., frame_000001.jpg).
    """
    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    if not frame_filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Invalid frame image format.")

    # Build the expected frame path with path traversal protection
    video_id = stored_filename.rsplit(".", 1)[0]
    frame_path = (FRAME_STORAGE_DIR / video_id / frame_filename).resolve()
    frame_storage_root = FRAME_STORAGE_DIR.resolve()

    if not str(frame_path).startswith(str(frame_storage_root)) or not frame_path.exists():
        raise HTTPException(status_code=404, detail="Frame not found.")

    try:
        result = vision_service.analyze_frame(str(frame_path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Frame image file not found.")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Frame analysis failed.")

    return {
        "success": True,
        "message": "Frame analyzed successfully",
        "video_filename": stored_filename,
        "frame_filename": frame_filename,
        "description": result["description"],
        "model": result["model"],
    }


@router.post("/videos/{stored_filename}/analyze")
async def analyze_video(
    stored_filename: str = FastPath(...),
    max_frames: int = Query(default=10, ge=1, le=50),
):
    """Analyze multiple frames from an uploaded video.

    max_frames: number of representative frames to analyze (1 to 50, default 10).
    """
    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    video_id = stored_filename.rsplit(".", 1)[0]
    frame_dir = FRAME_STORAGE_DIR / video_id

    if not frame_dir.exists():
        raise HTTPException(status_code=400, detail="No extracted frames found for this video. Extract frames first.")

    frame_files = sorted(
        f for f in frame_dir.glob("frame_*.jpg")
        if f.is_file()
    )

    if not frame_files:
        raise HTTPException(status_code=400, detail="No extracted frames found for this video. Extract frames first.")

    frame_filenames = []
    for i, fpath in enumerate(frame_files, start=1):
        frame_filenames.append({
            "index": i,
            "filename": fpath.name,
            "timestamp_seconds": round((i - 1) * 1.0, 2),
            "path": str(fpath),
        })

    try:
        result = analysis_service.analyze_video(
            stored_filename=stored_filename,
            frame_filenames=frame_filenames,
            max_frames=max_frames,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Video analysis failed.")

    return {
        "success": True,
        "message": "Video analysis completed successfully",
        **result,
    }


@router.post("/videos/{stored_filename}/prompt")
async def generate_prompt(
    stored_filename: str = FastPath(...),
    style: str = Query(default="cinematic"),
):
    """Generate a production-ready AI video prompt from structured analysis.

    style: 'cinematic' (default), 'realistic', or 'commercial'.
    """
    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    video_id = stored_filename.rsplit(".", 1)[0]
    frame_dir = FRAME_STORAGE_DIR / video_id

    if not frame_dir.exists():
        raise HTTPException(status_code=400, detail="No extracted frames found for this video. Extract frames first.")

    frame_files = sorted(f for f in frame_dir.glob("frame_*.jpg") if f.is_file())

    if not frame_files:
        raise HTTPException(status_code=400, detail="No extracted frames found for this video. Extract frames first.")

    frame_filenames = []
    for i, fpath in enumerate(frame_files, start=1):
        frame_filenames.append({
            "index": i,
            "filename": fpath.name,
            "timestamp_seconds": round((i - 1) * 1.0, 2),
            "path": str(fpath),
        })

    try:
        analysis_result = analysis_service.analyze_video(
            stored_filename=stored_filename,
            frame_filenames=frame_filenames,
            max_frames=10,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Video analysis failed.")

    try:
        prompt_result = prompt_service.generate_prompt(
            analysis=analysis_result,
            style=style,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Prompt generation failed.")

    return {
        "success": True,
        "message": "Prompt generated successfully",
        "video_filename": stored_filename,
        "style": style,
        "prompt": prompt_result["prompt"],
        "negative_prompt": prompt_result["negative_prompt"],
    }


@router.post("/videos/{stored_filename}/scenes/detect")
async def detect_scenes(
    stored_filename: str = FastPath(...),
    sample_interval_seconds: float = Query(default=1.0, gt=0),
    threshold: float = Query(default=0.30, ge=0, le=1),
):
    """Detect visual scene boundaries in an uploaded video.

    sample_interval_seconds: interval between sampled frames (default 1.0).
    threshold: visual difference threshold for scene boundary (default 0.30).
    """
    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    video_id = stored_filename.rsplit(".", 1)[0]
    frame_dir = FRAME_STORAGE_DIR / video_id

    if not frame_dir.exists():
        raise HTTPException(status_code=400, detail="No extracted frames found for this video. Extract frames first.")

    frame_files = sorted(f for f in frame_dir.glob("frame_*.jpg") if f.is_file())

    if not frame_files:
        raise HTTPException(status_code=400, detail="No extracted frames found for this video. Extract frames first.")

    frame_filenames = []
    for i, fpath in enumerate(frame_files, start=1):
        frame_filenames.append({
            "index": i,
            "filename": fpath.name,
            "timestamp_seconds": round((i - 1) * sample_interval_seconds, 2),
            "path": str(fpath),
        })

    video_duration = round(len(frame_files) * sample_interval_seconds, 2)

    try:
        result = scene_service.detect_scenes(
            stored_filename=stored_filename,
            frame_filenames=frame_filenames,
            video_duration=video_duration,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Scene detection failed.")

    # Assign scene IDs and ensure first scene has null change_score
    scenes = result.get("scenes", [])
    for i, scene in enumerate(scenes):
        scene["scene_id"] = i + 1
        if i == 0:
            scene["change_score_from_previous"] = None

    result["scenes"] = scenes

    # Ensure no absolute paths in response
    for scene in result["scenes"]:
        for key in ["start_frame", "end_frame", "representative_frame"]:
            val = scene.get(key, "")
            if val.startswith("/") or val.startswith("\\"):
                scene[key] = val.split("\\")[-1].split("/")[-1]

    return {
        "success": True,
        "message": "Scene detection completed successfully",
        "video_filename": stored_filename,
        "duration_seconds": result["duration_seconds"],
        "scenes_detected": result["scenes_detected"],
        "scenes": result["scenes"],
    }


@router.post("/videos/{stored_filename}/subjects/analyze")
async def analyze_subjects(
    stored_filename: str = FastPath(...),
):
    """Analyze subjects across video frames using heuristic tracking.

    This is NOT facial recognition or biometric identification.
    It performs heuristic text-based subject tracking from frame observations.
    """
    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    video_id = stored_filename.rsplit(".", 1)[0]
    frame_dir = FRAME_STORAGE_DIR / video_id

    if not frame_dir.exists():
        raise HTTPException(status_code=400, detail="No extracted frames found for this video. Extract frames first.")

    frame_files = sorted(f for f in frame_dir.glob("frame_*.jpg") if f.is_file())

    if not frame_files:
        raise HTTPException(status_code=400, detail="No extracted frames found for this video. Extract frames first.")

    # Run video analysis to get frame observations
    frame_filenames = []
    for i, fpath in enumerate(frame_files, start=1):
        frame_filenames.append({
            "index": i,
            "filename": fpath.name,
            "timestamp_seconds": round((i - 1) * 1.0, 2),
            "path": str(fpath),
        })

    try:
        analysis_result = analysis_service.analyze_video(
            stored_filename=stored_filename,
            frame_filenames=frame_filenames,
            max_frames=10,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Video analysis failed.")

    # Extract subjects from observations
    frame_observations = analysis_result.get("frame_observations", [])
    analysis = analysis_result.get("analysis", {})
    analysis_subjects = analysis.get("subjects", [])
    analysis_actions = analysis.get("actions", [])

    try:
        subject_result = subject_service.analyze_observations(
            frame_observations=frame_observations,
            analysis_subjects=analysis_subjects,
            analysis_actions=analysis_actions,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Subject analysis failed.")

    # Ensure no absolute paths
    for subject in subject_result.get("subjects", []):
        for frame in subject.get("frames_seen", []):
            if frame.startswith("/") or frame.startswith("\\"):
                subject["frames_seen"] = [
                    f.split("\\")[-1].split("/")[-1]
                    for f in subject["frames_seen"]
                ]

    return {
        "success": True,
        "message": "Subject analysis completed successfully",
        "video_filename": stored_filename,
        "subjects_detected": subject_result["subjects_detected"],
        "subjects": subject_result["subjects"],
    }


@router.post("/videos/{stored_filename}/audio/analyze")
async def analyze_audio(
    stored_filename: str = FastPath(...),
):
    """Analyze video audio and perform speech transcription if available.

    Uses the configured audio provider (default: mock).
    """
    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    try:
        result = audio_service.analyze_audio(stored_filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Audio analysis failed.")

    return {
        "success": True,
        "message": "Audio analysis completed successfully",
        "video_filename": result["video_filename"],
        "has_audio": result["has_audio"],
        "duration_seconds": result["duration_seconds"],
        "audio_format": result["audio_format"],
        "sample_rate": result["sample_rate"],
        "channels": result["channels"],
        "transcription": result["transcription"],
        "provider": result["provider"],
    }


@router.post("/videos/{stored_filename}/intelligence")
async def unified_intelligence(
    stored_filename: str = FastPath(...),
    max_frames: int = Query(default=10),
):
    """Run unified video intelligence analysis combining visual, scene, subject, and audio analysis.

    max_frames: number of representative frames to analyze (1 to 50, default 10).
    """
    if not isinstance(max_frames, int) or max_frames < 1 or max_frames > 50:
        raise HTTPException(status_code=400, detail="max_frames must be between 1 and 50.")

    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    try:
        result = intelligence_service.analyze(
            stored_filename=stored_filename,
            max_frames=max_frames,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Intelligence analysis failed.")

    return {
        "success": True,
        "message": "Unified intelligence analysis completed successfully",
        "video_filename": result["video_filename"],
        "duration_seconds": result["duration_seconds"],
        "visual": result["visual"],
        "scenes": result["scenes"],
        "subjects": result["subjects"],
        "audio": result["audio"],
    }


@router.post("/videos/{stored_filename}/advanced-prompt")
async def advanced_prompt(
    stored_filename: str = FastPath(...),
    style: str = Query(default="cinematic"),
):
    """Generate a production-ready AI video prompt from unified video intelligence.

    style: one of 'cinematic', 'realistic', 'commercial' (default cinematic).
    """
    if style not in VALID_STYLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style. Must be one of: {', '.join(sorted(VALID_STYLES))}",
        )

    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    try:
        intelligence = intelligence_service.analyze(
            stored_filename=stored_filename,
            max_frames=10,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Intelligence analysis failed.")

    try:
        result = advanced_prompt_service.generate_prompt(
            intelligence=intelligence,
            style=style,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Advanced prompt generation failed.")

    return {
        "success": True,
        "message": "Advanced prompt generated successfully",
        "video_filename": result["video_filename"],
        "style": result["style"],
        "prompt": result["prompt"],
        "negative_prompt": result["negative_prompt"],
        "sections": result["sections"],
    }


@router.post("/videos/{stored_filename}/prompt/refine")
async def refine_video_prompt(
    stored_filename: str = FastPath(...),
    request: PromptRefineRequest = None,
):
    """Refine an existing Day 13 generated prompt while preserving its facts.

    Body: {"operation": "refine"} where operation is one of
    refine, shorten, expand, cinematic, realistic, commercial.
    """
    if request is None or request.operation not in REFINEMENT_OPERATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid operation. Must be one of: {', '.join(sorted(REFINEMENT_OPERATIONS))}",
        )

    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    try:
        intelligence = intelligence_service.analyze(
            stored_filename=stored_filename,
            max_frames=10,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Intelligence analysis failed.")

    try:
        base = advanced_prompt_service.generate_prompt(
            intelligence=intelligence,
            style="cinematic",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Advanced prompt generation failed.")

    try:
        result = refinement_service.refine(
            source_prompt=base["prompt"],
            operation=request.operation,
            negative_prompt=base["negative_prompt"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Prompt refinement failed.")

    return {
        "success": True,
        "message": "Prompt refinement completed successfully",
        "video_filename": base["video_filename"],
        "operation": result["operation"],
        "source_prompt": result["source_prompt"],
        "refined_prompt": result["refined_prompt"],
        "negative_prompt": result["negative_prompt"],
        "preserved_information": result["preserved_information"],
    }


@router.post("/videos/{stored_filename}/prompt/template")
async def apply_prompt_template(
    stored_filename: str = FastPath(...),
    request: PromptTemplateRequest = None,
):
    """Apply a production template and optional custom instruction to the prompt.

    Body: {"template": "cinematic_story", "custom_instruction": ""}.
    Templates: cinematic_story, ai_video, commercial_ad, social_media,
    documentary.
    """
    if request is None or request.template not in VALID_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template. Must be one of: {', '.join(sorted(VALID_TEMPLATES))}",
        )

    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    try:
        intelligence = intelligence_service.analyze(
            stored_filename=stored_filename,
            max_frames=10,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Intelligence analysis failed.")

    try:
        base = advanced_prompt_service.generate_prompt(
            intelligence=intelligence,
            style="cinematic",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Advanced prompt generation failed.")

    try:
        result = template_service.apply_template(
            source_prompt=base["prompt"],
            template=request.template,
            intelligence=intelligence,
            custom_instruction=request.custom_instruction,
            negative_prompt=base["negative_prompt"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Prompt template application failed.")

    return {
        "success": True,
        "message": "Prompt template applied successfully",
        "video_filename": base["video_filename"],
        "template": result["template"],
        "source_prompt": result["source_prompt"],
        "custom_instruction": result["custom_instruction"],
        "prompt": result["prompt"],
        "negative_prompt": result["negative_prompt"],
        "preserved_information": result["preserved_information"],
    }


def _validate_history_video(stored_filename: str) -> None:
    """Validate the video path for prompt history endpoints (400/404)."""
    try:
        validate_file_extension(stored_filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    filepath = (STORAGE_DIR / stored_filename).resolve()
    if not str(filepath).startswith(str(STORAGE_DIR.resolve())) or not filepath.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")


@router.post("/videos/{stored_filename}/prompt/history")
async def create_prompt_history_version(
    stored_filename: str = FastPath(...),
    request: PromptHistoryCreateRequest = None,
):
    """Save a generated prompt as a new version.

    Body: {"prompt": "...", "negative_prompt": "", "source": "custom",
    "operation": "", "metadata": {}}.
    """
    if request is None:
        raise HTTPException(status_code=422, detail="Request body is required.")

    if not request.prompt.strip():
        raise HTTPException(status_code=422, detail="prompt must not be empty.")

    _validate_history_video(stored_filename)

    try:
        version = prompt_history_service.create_version(
            video_filename=stored_filename,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            source=request.source,
            operation=request.operation,
            metadata=request.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return version


@router.get("/videos/{stored_filename}/prompt/history")
async def list_prompt_history_versions(stored_filename: str = FastPath(...)):
    """List all saved prompt versions for a video, ascending by version."""
    _validate_history_video(stored_filename)

    return {
        "video_filename": stored_filename,
        "versions": prompt_history_service.list_versions(stored_filename),
    }


# NOTE: the static "compare" route MUST be registered before the numeric
# {version} route so it is never captured as a version lookup.
@router.get("/videos/{stored_filename}/prompt/history/compare/{version_a}/{version_b}")
async def compare_prompt_history_versions(
    stored_filename: str = FastPath(...),
    version_a: int = FastPath(..., ge=1),
    version_b: int = FastPath(..., ge=1),
):
    """Compare two saved prompt versions (deterministic token comparison)."""
    _validate_history_video(stored_filename)

    try:
        return prompt_history_service.compare_versions(
            stored_filename, version_a, version_b
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Day 23: Prompt Version Comparison & Diff ------------------------------
# Registered before the plain numeric {version} route (and coexists with
# the Day 16 token compare route above, which stays unchanged). Read-only:
# never modifies history, favorites, tags, and never saves the result.


@router.get(
    "/videos/{stored_filename}/prompt/history/compare/"
    "{version_a}/{version_b}/detailed"
)
async def compare_prompt_history_versions_detailed(
    stored_filename: str = FastPath(...),
    version_a: int = FastPath(..., ge=1),
    version_b: int = FastPath(..., ge=1),
):
    """Full structured comparison of two versions (Day 16 + Day 21).

    Returns both version summaries with Day 21 quality reports, a
    deterministic difflib text diff (added/removed/common text), neutral
    quality deltas, and the changed quality dimensions. Preserves the
    requested version order: deltas are always version_b - version_a.
    """
    _validate_history_video(stored_filename)

    try:
        return comparison_service.compare_versions(
            stored_filename, version_a, version_b
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Day 26: Prompt Readiness Change Tracking ------------------------------
# Static "/readiness" suffix keeps this route distinct from the Day 16
# token compare and the Day 23 detailed compare above. Read-only: never
# modifies history/favorites/tags, never saves the comparison result.


@router.get(
    "/videos/{stored_filename}/prompt/history/compare/"
    "{version_a}/{version_b}/readiness"
)
async def compare_prompt_history_versions_readiness(
    stored_filename: str = FastPath(...),
    version_a: int = FastPath(..., ge=1),
    version_b: int = FastPath(..., ge=1),
):
    """Informational readiness-state diff of two versions (Day 24 states).

    Preserves the requested direction: version A stays A, version B
    stays B (never auto-sorted). Reports which Day 21 dimensions
    changed readiness state, directional transitions, and neutral
    coverage arithmetic - no ranking, no winner, no comparison score.
    Nonexistent/deleted version -> 404; version below 1 -> 422.
    """
    _validate_history_video(stored_filename)

    try:
        return readiness_change_service.compare_versions(
            stored_filename, version_a, version_b
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Day 25: Prompt Readiness History Analysis -----------------------------
# Static "/prompt/history/readiness" route, registered BEFORE the plain
# numeric {version} routes below so it can never collide with them.
# Read-only: never modifies history/favorites/tags, never saves results.


def _parse_versions_query(
    values: "list[str] | None",
) -> "list[int] | None":
    """Parse the comma-separated ``versions`` query (strict).

    None -> None (meaning: analyze every live version).
    Accepts ``?versions=1,3,5`` and repeated ``?versions=1&versions=3``.
    Empty, malformed, non-positive, and duplicate entries -> 422.
    Requested order is preserved.
    """
    if values is None:
        return None
    parts: list[str] = []
    for value in values:
        parts.extend(part.strip() for part in value.split(","))
    if not parts or any(part == "" for part in parts):
        raise HTTPException(
            status_code=422,
            detail=(
                "versions must be a comma-separated list of "
                "positive integers."
            ),
        )
    parsed: list[int] = []
    for part in parts:
        if not part.isdigit():
            raise HTTPException(
                status_code=422,
                detail=f"Invalid version '{part}'.",
            )
        number = int(part)
        if number < 1:
            raise HTTPException(
                status_code=422,
                detail="versions must be positive integers.",
            )
        if number in parsed:
            raise HTTPException(
                status_code=422,
                detail=f"Duplicate version {number}.",
            )
        parsed.append(number)
    return parsed


@router.get("/videos/{stored_filename}/prompt/history/readiness")
async def prompt_history_readiness_analysis(
    stored_filename: str = FastPath(...),
    versions: "list[str] | None" = Query(None),
):
    """Analyze Day 24 readiness across saved prompt versions (read-only).

    No versions query: every live version, ascending version order.
    ``?versions=1,3,5``: only those versions, order preserved (never
    substituted or reordered). Empty/malformed/duplicate/non-positive
    versions -> 422; missing/deleted version -> 404. A video with no
    saved versions returns an empty (zero) analysis with 200.
    """
    selected = _parse_versions_query(versions)
    _validate_history_video(stored_filename)

    try:
        return readiness_history_service.analyze_versions(
            stored_filename, selected
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Day 17: Prompt Favorites & Tags -------------------------------------
# Static routes ("/favorites", "/tag/{tag}") are registered BEFORE the
# numeric {version} route so they can never be captured by it.


@router.get("/videos/{stored_filename}/prompt/history/favorites")
async def list_favorite_versions(stored_filename: str = FastPath(...)):
    """List favorite prompt versions for a video (ascending)."""
    _validate_history_video(stored_filename)

    return {
        "video_filename": stored_filename,
        "favorites": organization_service.list_favorites(stored_filename),
    }


@router.get("/videos/{stored_filename}/prompt/history/tag/{tag}")
async def list_versions_by_tag(
    stored_filename: str = FastPath(...),
    tag: str = FastPath(...),
):
    """List prompt versions carrying the exact normalized tag."""
    _validate_history_video(stored_filename)

    try:
        versions = organization_service.list_by_tag(stored_filename, tag)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "video_filename": stored_filename,
        "tag": tag.strip().lower(),
        "versions": versions,
    }


def _require_existing_version(stored_filename: str, version: int) -> None:
    try:
        prompt_history_service.get_version(stored_filename, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/videos/{stored_filename}/prompt/history/{version}/favorite")
async def favorite_prompt_version(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
):
    """Mark an existing prompt version as favorite (idempotent)."""
    _validate_history_video(stored_filename)
    _require_existing_version(stored_filename, version)

    return organization_service.favorite_version(stored_filename, version)


@router.delete("/videos/{stored_filename}/prompt/history/{version}/favorite")
async def unfavorite_prompt_version(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
):
    """Remove a prompt version from favorites (idempotent)."""
    _validate_history_video(stored_filename)
    _require_existing_version(stored_filename, version)

    return organization_service.unfavorite_version(stored_filename, version)


@router.post("/videos/{stored_filename}/prompt/history/{version}/tags")
async def add_prompt_version_tags(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
    request: PromptTagsRequest = None,
):
    """Add normalized tags to an existing prompt version."""
    if request is None:
        raise HTTPException(status_code=422, detail="Request body is required.")

    _validate_history_video(stored_filename)
    _require_existing_version(stored_filename, version)

    try:
        return organization_service.add_tags(
            stored_filename, version, request.tags
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/videos/{stored_filename}/prompt/history/{version}/tags")
async def remove_prompt_version_tags(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
    request: PromptTagsRequest = None,
):
    """Remove tags from an existing prompt version (missing tags harmless)."""
    if request is None:
        raise HTTPException(status_code=422, detail="Request body is required.")

    _validate_history_video(stored_filename)
    _require_existing_version(stored_filename, version)

    try:
        return organization_service.remove_tags(
            stored_filename, version, request.tags
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/videos/{stored_filename}/prompt/history/{version}/organization")
async def get_prompt_version_organization(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
):
    """Retrieve favorite flag and tags for one prompt version."""
    _validate_history_video(stored_filename)

    try:
        return organization_service.get_organization(stored_filename, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Day 19: Prompt Export & Packaging ------------------------------------
# The "/{version}/export" sub-route is registered before the plain numeric
# {version} route so the two can never collide.


# --- Day 20: Prompt Package Generation ------------------------------------
# The "/{version}/package" sub-route is registered before the plain numeric
# {version} route so the two can never collide.


@router.get("/videos/{stored_filename}/prompt/history/{version}/package")
async def package_prompt_history_version(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
):
    """Package one saved prompt version as a downloadable ZIP.

    Read-only: reuses the Day 19 export service; never modifies the
    stored version, favorites, or tags.
    """
    _validate_history_video(stored_filename)

    try:
        package = package_service.create_package(stored_filename, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=package["content"],
        media_type=package["media_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{package["filename"]}"'
        },
    )


# --- Day 21: Prompt Quality Analyzer (history integration) ----------------
# The "/{version}/quality" sub-route is registered before the plain numeric
# {version} route so the two can never collide.


@router.get("/videos/{stored_filename}/prompt/history/{version}/quality")
async def prompt_version_quality(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
):
    """Analyze the stored prompt of one history version (read-only).

    Passes the saved prompt text to PromptQualityService; never modifies
    the history record, favorites, or tags.
    """
    _validate_history_video(stored_filename)

    try:
        record = prompt_history_service.get_version(stored_filename, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return quality_service.analyze_prompt(record["prompt"])


# --- Day 22: Quality-Guided Prompt Improvement (history integration) ------
# The "/{version}/improve" sub-route is registered before the plain numeric
# {version} route so the two can never collide.


@router.get("/videos/{stored_filename}/prompt/history/{version}/improve")
async def improve_prompt_history_version(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
):
    """Improve the stored prompt of one history version (read-only).

    Retrieves the version via Day 16, runs the Day 22 improvement
    service over its prompt, and never modifies the history record,
    favorites, or tags.
    """
    _validate_history_video(stored_filename)

    try:
        record = prompt_history_service.get_version(stored_filename, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = improvement_service.improve_prompt(record["prompt"])
    return {"video_filename": stored_filename, **result}


# --- Day 24: Production Readiness Validator (history integration) ----------
# The "/{version}/readiness" sub-route is registered before the plain
# numeric {version} route so the two can never collide.


@router.get("/videos/{stored_filename}/prompt/history/{version}/readiness")
async def prompt_version_readiness(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
):
    """Validate the stored prompt of one history version (read-only).

    Retrieves the version via Day 16, runs the Day 24 readiness
    validation over its prompt, and never modifies the history record,
    favorites, or tags.
    """
    _validate_history_video(stored_filename)

    try:
        record = prompt_history_service.get_version(stored_filename, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        result = readiness_service.validate_prompt(record["prompt"])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"video_filename": stored_filename, **result}


@router.get("/videos/{stored_filename}/prompt/history/{version}/export")
async def export_prompt_history_version(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
    format: str = Query(...),
):
    """Export one saved prompt version as json, markdown, or txt.

    Read-only: never modifies the stored version, favorites, or tags.
    Example: GET .../prompt/history/3/export?format=markdown
    """
    _validate_history_video(stored_filename)

    if format not in VALID_EXPORT_FORMATS:
        raise HTTPException(
            status_code=422,
            detail="Invalid format. Must be one of: "
            + ", ".join(sorted(VALID_EXPORT_FORMATS)),
        )

    try:
        export = export_service.export_version(stored_filename, version, format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=export["content"],
        media_type=export["media_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{export["filename"]}"'
        },
    )


@router.get("/videos/{stored_filename}/prompt/history/{version}")
async def get_prompt_history_version(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
):
    """Retrieve one specific saved prompt version."""
    _validate_history_video(stored_filename)

    try:
        return prompt_history_service.get_version(stored_filename, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/videos/{stored_filename}/prompt/history/{version}")
async def delete_prompt_history_version(
    stored_filename: str = FastPath(...),
    version: int = FastPath(..., ge=1),
):
    """Delete one saved prompt version without renumbering the rest."""
    _validate_history_video(stored_filename)

    try:
        prompt_history_service.delete_version(stored_filename, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "deleted": True,
        "video_filename": stored_filename,
        "version": version,
    }


@router.get("/videos/{stored_filename}/prompt/search")
async def search_prompt_versions(
    stored_filename: str = FastPath(...),
    query: str = Query(default=""),
    source: str = Query(default=None),
    operation: str = Query(default=None),
    favorite: bool = Query(default=None),
    tag: str = Query(default=None),
    min_version: int = Query(default=None, ge=1),
    max_version: int = Query(default=None, ge=1),
    sort: str = Query(default="version_asc"),
):
    """Search and filter saved prompt versions (Day 16 history + Day 17 org).

    All supplied filters are AND-combined. Example:
    GET .../prompt/search?query=cinematic&favorite=true&tag=ai
    """
    _validate_history_video(stored_filename)

    if min_version is not None and max_version is not None:
        if min_version > max_version:
            raise HTTPException(
                status_code=422,
                detail="min_version must not be greater than max_version.",
            )

    try:
        results = search_service.search_versions(
            video_filename=stored_filename,
            query=query,
            source=source,
            operation=operation,
            favorite=favorite,
            tag=tag,
            min_version=min_version,
            max_version=max_version,
            sort=sort,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "video_filename": stored_filename,
        "filters": {
            "query": query,
            "source": source,
            "operation": operation,
            "favorite": favorite,
            "tag": tag,
            "min_version": min_version,
            "max_version": max_version,
        },
        "count": len(results),
        "results": results,
    }


# --- Day 21: Prompt Quality Analyzer ---------------------------------------
# POST /videos/{stored_filename}/prompt/quality analyzes arbitrary prompt
# text supplied in the request body. It does NOT require or touch history
# versions; it only validates that stored_filename is a real video.


@router.post("/videos/{stored_filename}/prompt/quality")
async def analyze_prompt_quality(
    stored_filename: str = FastPath(...),
    request: PromptQualityRequest = None,
):
    """Run the deterministic quality/coverage analysis on prompt text.

    Body: {"prompt": "<text to analyze>"}
    422 when the body is missing or the prompt is empty/whitespace.
    404 when stored_filename is not a valid video.
    """
    if request is None:
        raise HTTPException(
            status_code=422,
            detail="Request body is required with a 'prompt' field.",
        )

    _validate_history_video(stored_filename)

    try:
        return quality_service.analyze_prompt(request.prompt)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# --- Day 22: Quality-Guided Prompt Improvement -----------------------------
# POST /videos/{stored_filename}/prompt/improve analyzes and improves
# arbitrary prompt text supplied in the request body. It does NOT require
# or touch history versions; it only validates that stored_filename is a
# real video, and never saves the result into history.


@router.post("/videos/{stored_filename}/prompt/improve")
async def improve_prompt(
    stored_filename: str = FastPath(...),
    request: PromptImproveRequest = None,
):
    """Deterministically improve prompt coverage without fabricating facts.

    Body: {"prompt": "<text to improve>"}
    422 when the body is missing or the prompt is empty/whitespace.
    404 when stored_filename is not a valid video.
    """
    if request is None:
        raise HTTPException(
            status_code=422,
            detail="Request body is required with a 'prompt' field.",
        )

    _validate_history_video(stored_filename)

    try:
        result = improvement_service.improve_prompt(request.prompt)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"video_filename": stored_filename, **result}


# --- Day 24: Production Readiness Validator -------------------------------
# POST /videos/{stored_filename}/prompt/readiness validates arbitrary
# prompt text supplied in the request body. It does NOT require or touch
# history versions; it only validates that stored_filename is a real
# video, and never saves the readiness report anywhere.


@router.post("/videos/{stored_filename}/prompt/readiness")
async def validate_prompt_readiness(
    stored_filename: str = FastPath(...),
    request: PromptReadinessRequest = None,
):
    """Deterministically validate production readiness of prompt text.

    Body: {"prompt": "<text to validate>"}
    422 when the body is missing or the prompt is empty/whitespace.
    404 when stored_filename is not a valid video.
    """
    if request is None:
        raise HTTPException(
            status_code=422,
            detail="Request body is required with a 'prompt' field.",
        )

    _validate_history_video(stored_filename)

    try:
        result = readiness_service.validate_prompt(request.prompt)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"video_filename": stored_filename, **result}