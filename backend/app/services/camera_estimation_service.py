"""Camera and lens estimation service for P2-03.

Estimates camera parameters from video metadata and extracted frame analysis.
Uses deterministic heuristics based on resolution, frame count, and
visual analysis. Does NOT require AI model inference.

Every estimate includes: value, confidence, estimated flag, and source/method.
Never presents estimated focal length as ground truth.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, Literal

from pathlib import Path

from app.core.config import Settings

from app.utils.ffprobe import extract_metadata


class LensCategory:
    """Categories of camera lenses for estimation purposes."""

    FISHEYE = "fisheye"
    WIDE_ANGLE = "wide_angle"
    STANDARD = "standard"
    TELEPHOTO = "telephoto"
    MACRO = "macro"
    UNKNOWN = "unknown"


class CameraMovement:
    """Camera motion categories."""

    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    DOLLY = "dolly"
    CRANE = "crane"
    HANDHELD = "handheld"
    UNKNOWN = "unknown"


class FocusDistance:
    """Focus distance categories."""

    INFINITY = "infinity"
    HYPERFOCAL = "hyperfocal"
    FAR = "far"
    MEDIUM = "medium"
    NEAR = "near"
    UNKNOWN = "unknown"


def _classify_lens_focal_length(
    focal_length_mm: Optional[float],
) -> tuple[Optional[float], LensCategory]:
    """Classify a focal length into a lens category.

    Args:
        focal_length_mm: Focal length in millimeters, or None.

    Returns:
        Tuple of (focal_length_mm, lens_category). If focal_length_mm is None,
        returns (None, LensCategory.UNKNOWN).
    """
    if focal_length_mm is None:
        return None, LensCategory.UNKNOWN

    FL = float(focal_length_mm)
    if FL < 15:
        return FL, LensCategory.FISHEYE
    elif FL < 35:
        return FL, LensCategory.WIDE_ANGLE
    elif FL <= 70:
        return FL, LensCategory.STANDARD
    elif FL <= 200:
        return FL, LensCategory.TELEPHOTO
    else:
        return FL, LensCategory.MACRO


def _classify_camera_movement(
    frame_count: int, duration_seconds: float, resolution: tuple[int, int]
) -> str:
    """Heuristically classify camera movement from frame count and duration.

    More frames relative to duration suggest more motion/activity in the video,
    which can indicate camera movement or a more dynamic scene.
    """
    if duration_seconds <= 0 or frame_count <= 1:
        return CameraMovement.STATIC

    fps = frame_count / duration_seconds
    width, height = resolution
    pixel_count = width * height

    # Heuristics: high frame rate + high resolution + many frames may indicate
    # camera movement or a very dynamic scene
    if fps > 30 and pixel_count > 100_000_000:
        return CameraMovement.HANDHELD
    elif fps > 24:
        return CameraMovement.PAN
    elif fps > 15:
        return CameraMovement.TILT
    elif frame_count > 300:
        return CameraMovement.DOLLY
    else:
        return CameraMovement.STATIC


def _classify_shot_size(
    width: int, height: int, diagonal_mm: Optional[float] = None
) -> str:
    """Classify shot size based on sensor/frame dimensions.

    Larger sensors/frames generally correspond to wider shots,
    smaller sensors to tighter shots. This is a very rough heuristic.
    """
    if width <= 0 or height <= 0:
        return "unknown"

    diag = (width ** 2 + height ** 2) ** 0.5
    if diag >= 1920:
        return "wide"
    elif diag >= 1280:
        return "medium"
    else:
        return "tight"


class CameraLensEstimate:
    """Structured camera and lens estimation result."""

    def __init__(
        self,
        focal_length_mm: Optional[float] = None,
        lens_category: LensCategory = LensCategory.UNKNOWN,
        field_of_view_degrees: Optional[float] = None,
        perspective: Optional[str] = None,
        camera_distance_meters: Optional[float] = None,
        shot_size: Optional[str] = None,
        camera_movement: str = CameraMovement.STATIC,
        camera_height: Optional[float] = None,
        camera_angle: Optional[float] = None,
        confidence: float = 0.0,
        estimated: bool = False,
        method: str = "heuristic",
        limitations: Optional[list[str]] = None,
    ):
        self.focal_length_mm = focal_length_mm
        self.lens_category = lens_category
        self.field_of_view_degrees = field_of_view_degrees
        self.perspective = perspective
        self.camera_distance_meters = camera_distance_meters
        self.shot_size = shot_size
        self.camera_movement = camera_movement
        self.camera_height = camera_height
        self.camera_angle = camera_angle
        self.confidence = min(confidence, 1.0)
        self.estimated = estimated
        self.method = method
        self.limitations = limitations or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dict with all fields including explicit availability flags."""
        return {
            "focal_length_mm": self.focal_length_mm,
            "lens_category": self.lens_category,
            "field_of_view_degrees": self.field_of_view_degrees,
            "perspective": self.perspective,
            "camera_distance_meters": self.camera_distance_meters,
            "shot_size": self.shot_size,
            "camera_movement": self.camera_movement,
            "camera_height": self.camera_height,
            "camera_angle": self.camera_angle,
            "confidence": self.confidence,
            "estimated": self.estimated,
            "method": self.method,
            "limitations": self.limitations,
        }


def estimate_from_metadata(
    stored_filename: str,
    settings: Settings,
) -> CameraLensEstimate:
    """Estimate camera/lens parameters from video metadata and settings.

    Uses video resolution, duration, and frame count from ffprobe metadata
    together with configured settings to produce deterministic estimates.

    Args:
        stored_filename: The stored video filename.
        settings: Application settings.

    Returns:
        A CameraLensEstimate with deterministic values and explicit confidence.
    """
    filepath = Path("storage/uploads") / stored_filename
    if not filepath.exists():
        return CameraLensEstimate(
            estimated=False,
            method="metadata",
            limitations=["Video file not found on disk."],
        )

    try:
        metadata = extract_metadata(filepath)
    except Exception:
        return CameraLensEstimate(
            estimated=False,
            method="metadata",
            limitations=["Could not extract video metadata."],
        )

    width = metadata.get("width", 1920)
    height = metadata.get("height", 1080)
    duration = metadata.get("duration_seconds", 0.0)
    frame_count = metadata.get("frame_count", 0)

    # Heuristic: estimate focal length from resolution and duration
    # Higher resolution + longer duration might suggest longer focal length
    # This is intentionally vague - real inference would use frame analysis
    focal_length: Optional[float] = None
    lens_category = LensCategory.UNKNOWN
    estimated = False

    # Very rough heuristic based on resolution alone
    if width >= 3840:  # 4K+
        focal_length = 50.0
        lens_category = LensCategory.TELEPHOTO
        estimated = True
    elif width >= 1920:  # HD+
        focal_length = 35.0
        lens_category = LensCategory.STANDARD
        estimated = True
    elif width >= 1280:  # HD
        focal_length = 24.0
        lens_category = LensCategory.WIDE_ANGLE
        estimated = True
    else:  # SD or smaller
        focal_length = 16.0
        lens_category = LensCategory.FISHEYE
        estimated = True

    # Another heuristic based on duration - longer videos might use wider lenses
    # to capture more scene context
    if duration and duration > 60:
        if focal_length is not None:
            focal_length = max(16.0, focal_length - 10.0)
    elif duration and duration > 0 and duration < 10:
        if focal_length is not None:
            focal_length = min(50.0, focal_length + 5.0)

    # Classify the focal length
    if focal_length is not None:
        _, lens_category = _classify_lens_focal_length(focal_length)

    # Heuristic camera movement from frame rate
    movement = _classify_camera_movement(frame_count or 0, duration or 0.0, (width, height))

    # Shot size from resolution
    shot_size = _classify_shot_size(width, height)

    # Heuristic camera angle - simpler videos may have simpler camera setups
    camera_angle = None
    if width >= 3840:
        camera_angle = 90.0
    elif width >= 1920:
        camera_angle = 60.0
    elif width >= 1280:
        camera_angle = 45.0
    else:
        camera_angle = 30.0

    # Camera height guess - based on typical setups
    camera_height = None
    if duration and duration > 60:
        camera_height = 1.5  # tripod height
    elif duration and duration > 0:
        camera_height = 0.5  # handheld or steady

    # Field of view estimate (derived from focal length)
    fov_degrees: Optional[float] = None
    if focal_length is not None:
        # Simple FOV approximation for full-frame sensor
        import math

        fov_degrees = 2 * 360.0 / 3.14159 * math.atan(
            36.0 / (2 * focal_length)
        )  # simplified

    limitations = [
        "Heuristic estimation based on resolution and duration only",
        "No actual frame content analysis performed",
        "Focal length not ground truth - may be inaccurate",
        "Sensor size assumed standard full-frame equivalent",
        "Movement classification based on FPS alone",
    ]

    return CameraLensEstimate(
        focal_length_mm=focal_length,
        lens_category=lens_category,
        field_of_view_degrees=fov_degrees,
        perspective=None,
        camera_distance_meters=None,
        shot_size=shot_size,
        camera_movement=movement,
        camera_height=camera_height,
        camera_angle=camera_angle,
        confidence=0.3 if not estimated else 0.5,
        estimated=estimated,
        method="heuristic-metadata",
        limitations=limitations,
    )


class CameraEstimationService:
    """Service for estimating camera and lens parameters from videos.

    Provides a provider abstraction for future CV/model-based implementations.
    All estimates are explicitly marked as heuristic/estimated with confidence
    scores and documented limitations.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()

    def estimate(self, stored_filename: str) -> CameraLensEstimate:
        """Estimate camera and lens parameters for a stored video.

        Args:
            stored_filename: The stored video filename (e.g. "abc123.mp4").

        Returns:
            A CameraLensEstimate with explicit estimated flag, confidence,
            and documented limitations.
        """
        return estimate_from_metadata(stored_filename, self.settings)

    def estimate_with_provider(
        self,
        stored_filename: str,
        provider_name: str = "heuristic",
    ) -> CameraLensEstimate:
        """Estimate using a named provider.

        Args:
            stored_filename: The stored video filename.
            provider_name: Name of the estimation provider.

        Returns:
            A CameraLensEstimate from the requested provider.
        """
        if provider_name == "heuristic":
            return self.estimate(stored_filename)
        raise ValueError(f"Unknown camera estimation provider: {provider_name}")


# Convenience function
def get_camera_estimation_service() -> CameraEstimationService:
    """Get a configured camera estimation service instance."""
    return CameraEstimationService()