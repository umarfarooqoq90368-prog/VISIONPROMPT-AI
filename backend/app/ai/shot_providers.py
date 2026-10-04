import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any

from PIL import Image

from app.ai.shot_provider import ShotBoundaryProvider, get_shot_provider as _get_shot_provider


def collect_frames(
    stored_filename: str,
    sample_interval_seconds: float = 1.0,
) -> List[Dict[str, Any]]:
    """Collect extracted frames for a stored video.

    Mirrors the Day 9 frame extraction convention: frames are expected
    in ``backend/storage/frames/<video_id>/`` with filenames
    ``frame_XXXX.jpg`` and timestamps computed from the extraction interval.

    Args:
        stored_filename: The stored video filename (e.g. ``test.mp4``).
        sample_interval_seconds: Interval in seconds between sampled frames.

    Returns:
        A list of frame dicts with ``filename``, ``timestamp_seconds``,
        and ``path`` keys, sorted chronologically.

    Raises:
        ValueError: If no extracted frames are found for this video.
    """
    from app.services.frame_service import _get_frame_dir

    frame_dir = _get_frame_dir(stored_filename)
    if not frame_dir.is_dir():
        raise ValueError("No extracted frames found for this video. Extract frames first.")

    pattern = str(frame_dir / "frame_*.jpg")
    import glob as _glob
    files = _glob.glob(pattern)
    if not files:
        raise ValueError("No extracted frames found for this video. Extract frames first.")

    files = sorted(files)
    frames = []
    for i, fpath in enumerate(files, start=1):
        fname = Path(fpath).name
        ts = round((i - 1) * sample_interval_seconds, 2)
        frames.append(
            {
                "filename": fname,
                "timestamp_seconds": ts,
                "path": str(Path(fpath)).replace("\\", "/"),
            }
        )
    return frames


class HeuristicShotProvider(ShotBoundaryProvider):
    """Heuristic shot boundary detection using RGB histogram comparison
    and pixel-level difference.

    This provider does NOT require any AI model inference. It uses
    deterministic image processing heuristics to identify shot boundaries
    from extracted frames.

    Transition type rules:
    - cut:           consecutive pair difference < 0.25 × threshold
    - fade:          |pix − hist| < 0.05 (ramp)
    - dissolve:      pix > hist (histogram comparison)
    - unknown:       default fallback for ramps
    """

    def __init__(
        self,
        threshold: float = 0.40,
        max_shots: int = 100,
    ):
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1.")
        if not 1 <= max_shots <= 100:
            raise ValueError("max_shots must be between 1 and 100.")
        self.threshold = threshold
        self.max_shots = max_shots

    # ---- VisionProvider overrides ----

    @property
    def model_name(self) -> str:
        return "heuristic-shot-provider"

    def compare(
        self,
        frame_path_a: str,
        frame_path_b: str,
    ) -> float:
        """Compute a visual difference score between two frames.

        Uses 32-bin RGB histogram intersection distance complemented
        by mean pixel difference. The combined score is normalized to [0, 1].

        Args:
            frame_path_a: Path to the first frame image.
            frame_path_b: Path to the second frame image.

        Returns:
            A float in [0, 1] where 0 = identical, 1 = completely different.
        """
        try:
            img_a = Image.open(frame_path_a).convert("RGB")
            img_b = Image.open(frame_path_b).convert("RGB")
        except Exception as e:
            raise ValueError(f"Invalid frame data: {str(e)}")

        target_size = (64, 64)
        img_a = img_a.resize(target_size, Image.LANCZOS)
        img_b = img_b.resize(target_size, Image.LANCZOS)

        arr_a = np.array(img_a, dtype=np.float64) / 255.0
        arr_b = np.array(img_b, dtype=np.float64) / 255.0

        # 32-bin RGB histogram intersection
        hist_a = np.histogram(
            np.dot(arr_a[..., :3], [0.299, 0.587, 0.114]).ravel(), bins=32, range=(0, 1)
        )[0]
        hist_b = np.histogram(
            np.dot(arr_b[..., :3], [0.299, 0.587, 0.114]).ravel(), bins=32, range=(0, 1)
        )[0]

        hist_intersection = np.minimum(hist_a, hist_b).sum()
        hist_score = 1.0 - (hist_intersection / (hist_a.sum() + hist_b.sum() - hist_intersection + 1e-6))

        # Mean pixel difference
        pix_diff = np.mean(np.abs(arr_a - arr_b))

        # Combined score: weighted combination
        combined = 0.6 * pix_diff + 0.4 * hist_score
        return float(min(combined, 1.0))

    def infer_shot_type(
        self,
        prev_score: float,
        curr_score: float,
        prev_change_score: Optional[float] = None,
    ) -> str:
        """Infer the transition type from consecutive comparison scores.

        Transition type rules:
        - cut:           consecutive pair difference < 0.25 × threshold
        - fade:          |pix − hist| < 0.05 (ramp / smooth transition)
        - dissolve:      pix > hist (histogram-based change)
        - unknown:       default fallback for ramps
        - None:          when scores are inconclusive

        Args:
            prev_score: Comparison score between the frame before the previous
                and the previous frame.
            curr_score: Comparison score between the previous frame and the
                current frame.
            prev_change_score: The change score from before prev_score, if available.

        Returns:
            One of: "cut", "fade", "dissolve", "unknown", "None".
        """
        # Use parent default first (cut at <0.25, unknown at |diff|<0.05, dissolve otherwise)
        return super().infer_shot_type(prev_score, curr_score, prev_change_score)


def get_shot_provider(name: str = "heuristic") -> ShotBoundaryProvider:
    """Create a shot boundary provider by name.

    Args:
        name: Provider name. Currently only 'heuristic' is supported.

    Returns:
        An instance of the requested ShotBoundaryProvider.

    Raises:
        ValueError: If the provider name is not recognized.
    """
    if name == "heuristic":
        from app.ai.shot_providers import HeuristicShotProvider

        return HeuristicShotProvider()
    raise ValueError(f"Unknown shot provider: {name}")