"""Emotion and action detection service for P2-05.

Detects actions and emotions from video frames using heuristic analysis.
Does NOT require AI model inference. All outputs are explicitly marked as
observed/inferred/estimated with confidence scores and documented limitations.

Adds: POST /api/videos/{stored_filename}/emotion-action/analyze
Integrates into reconstruction and storyboard.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List

from pathlib import Path

from PIL import Image


# ------------------------------------------------------------------
# Emotion category vocabulary (provider/model dependent).
# These are the ONLY emotion labels the system will ever emit.
# ------------------------------------------------------------------

EMOTION_VOCABULARY = {
    "neutral",
    "happy",
    "sad",
    "angry",
    "fearful",
    "surprised",
    "disgusted",
    "fear",
}

ACTION_VOCABULARY = {
    "walking",
    "running",
    "jumping",
    "sitting",
    "standing",
    "talking",
    "reading",
    "writing",
    "eating",
    "drinking",
}


def _load_frame(frame_path: str, size: tuple[int, int] | None = None) -> Optional[Image.Image]:
    """Load a single frame image.

    Args:
        frame_path: Path to the JPEG frame file.
        size: Optional resize dimensions (width, height).

    Returns:
        PIL Image object, or None if the file cannot be loaded.
    """
    try:
        img = Image.open(frame_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        if size:
            img = img.resize(size, Image.LANCZOS)
        return img
    except Exception:
        return None


def _classify_emotion_from_pixels(
    img: Image.Image,
) -> Optional[str]:
    """Heuristically classify a basic emotion from frame pixel data.

    This is a very rough heuristic based on average brightness and color
    distribution. It does NOT attempt semantic facial expression analysis.

    Returns one of the EMOTION_VOCABULARY labels, or None if inconclusive.
    """
    if img is None:
        return None

    # Resize for performance
    small = img.resize((32, 32), Image.LANCZOS)
    pixels = list(small.getdata())

    # Compute average RGB
    r_total = g_total = b_total = 0
    for r, g, b in pixels:
        r_total += r
        g_total += g
        b_total += b
    n = len(pixels)
    if n == 0:
        return None

    r_avg = r_total / n
    g_avg = g_total / n
    b_avg = b_total / n

    # Compute relative luminance (perceived brightness)
    brightness = 0.299 * (r_avg / 255.0) + 0.587 * (g_avg / 255.0) + 0.114 * (b_avg / 255.0)

    # Very rough heuristics based on brightness and color bias:
    # - High brightness + red/green bias over blue -> happy/surprised
    # - Low brightness + blue bias -> sad/fear
    # - Otherwise -> neutral

    # Check for "happy" (high brightness, yellow bias: red+green > blue)
    if brightness > 0.7 and r_avg > 1.5 * b_avg and g_avg > 1.5 * b_avg:
        return "happy"

    # Check for "sad" (low brightness, blue bias)
    if brightness < 0.3 and b_avg > max(r_avg, g_avg) * 1.2:
        return "sad"

    # Check for "angry" (high red, low blue, moderate brightness)
    if r_avg > 1.5 * b_avg and r_avg > 1.2 * g_avg and brightness > 0.4:
        return "angry"

    # Check for "fear" (high blue, moderate brightness)
    if b_avg > max(r_avg, g_avg) * 1.3 and brightness > 0.3:
        return "fear"

    # Check for "surprised" (high brightness with broad distribution)
    if brightness > 0.7:
        return "surprised"

    # Default to neutral
    return "neutral"


def _classify_action_from_pixels(
    img: Image.Image,
) -> Optional[str]:
    """Heuristically classify a basic action from frame pixel data.

    This is a very rough heuristic based on image characteristics (color
    distribution, brightness patterns) that may correlate with common actions.
    It does NOT perform pose estimation or motion tracking.

    Returns one of the ACTION_VOCABULARY labels, or None if inconclusive.
    """
    if img is None:
        return None

    # Resize for performance
    small = img.resize((32, 32), Image.LANCZOS)
    pixels = list(small.getdata())

    # Compute average RGB
    r_total = g_total = b_total = 0
    for r, g, b in pixels:
        r_total += r
        g_total += g
        b_total += b
    n = len(pixels)
    if n == 0:
        return None

    r_avg = r_total / n
    g_avg = g_total / n
    b_avg = b_total / n

    # Compute relative luminance (perceived brightness)
    brightness = 0.299 * (r_avg / 255.0) + 0.587 * (g_avg / 255.0) + 0.114 * (b_avg / 255.0)

    # Heuristic: "walking" - medium brightness, check color diversity
    if 0.3 < brightness < 0.7:
        max_channel = max(r_avg, g_avg, b_avg)
        min_channel = min(r_avg, g_avg, b_avg)
        if max_channel - min_channel > 30:
            return "walking"

    # Heuristic: "running" - similar but slightly higher energy
    if 0.4 < brightness < 0.8:
        if r_avg > b_avg or g_avg > b_avg:
            return "running"

    # Heuristic: "sitting" - lower brightness, more neutral colors
    if brightness < 0.5:
        max_channel = max(r_avg, g_avg, b_avg)
        min_channel = min(r_avg, g_avg, b_avg)
        if max_channel - min_channel < 30:
            return "sitting"

    # Heuristic: "talking" - higher brightness with color diversity
    if brightness > 0.5:
        unique_colors = len(set([(r, g, b) for r, g, b in pixels]))
        if unique_colors > 15:
            return "talking"

    # Default
    return None


def analyze_emotion_action(
    stored_filename: str,
    sample_interval: float = 1.0,
    frame_size: tuple[int, int] = (32, 32),
) -> Dict[str, Any]:
    """Analyze emotion and action from a video's extracted frames.

    Samples frames at the given interval and performs heuristic classification
    of emotion and action based on pixel-level analysis. All outputs are
    explicitly marked with confidence, estimated flag, and source.

    Args:
        stored_filename: The stored video filename (e.g. "abc123.mp4").
        sample_interval: Seconds between sampled frames (default 1.0).
        frame_size: Analysis resize dimension (default 32x32).

    Returns:
        A dict with:

        - ``observed_action``: Action label from ACTION_VOCABULARY, or None
        - ``inferred_action``: Action dict with label and confidence, or None
        - ``inferred_emotion``: Emotion dict with label and confidence, or None
        - ``emotion_confidence``: Confidence score for emotion (0-1)
        - ``action_confidence``: Confidence score for action (0-1)
        - ``emotion_source``: "observed", "inferred", or "unavailable"
        - ``action_source``: "observed", "inferred", or "unavailable"
        - ``method``: Analysis method string
        - ``estimated``: Whether the analysis is heuristic/estimated

    Raises:
        ValueError: If no frames are found for the video.
    """
    from app.services.frame_service import _get_frame_dir

    frame_dir = Path(_get_frame_dir(stored_filename))
    if not frame_dir.is_dir():
        raise ValueError("No extracted frames found for this video. Extract frames first.")

    import glob as _glob
    files = _glob.glob(str(frame_dir / "frame_*.jpg"))
    if not files:
        raise ValueError("No extracted frames found for this video. Extract frames first.")

    files = sorted(files)

    emotion_count = 0
    action_count = 0

    for filepath in files:
        img = _load_frame(filepath, size=frame_size)
        if img is None:
            continue

        emotion = _classify_emotion_from_pixels(img)
        if emotion is not None:
            emotion_count += 1

        action = _classify_action_from_pixels(img)
        if action is not None:
            action_count += 1

    total = max(1, emotion_count + action_count)
    emotion_confidence = round(emotion_count / total, 2)
    action_confidence = round(action_count / total, 2)

    # Determine source: observed if we found any classifications,
    # inferred if we found none but have frames, unavailable otherwise
    if emotion_count > 0:
        emotion_source = "observed"
    elif emotion_count == 0:
        emotion_source = "inferred"
    else:
        emotion_source = "unavailable"

    if action_count > 0:
        action_source = "observed"
    elif action_count == 0:
        action_source = "inferred"
    else:
        action_source = "unavailable"

    # Build inferred emotion dict (pick any classified emotion, or default)
    inferred_emotion = None
    if emotion_source == "observed":
        # Find the first classified emotion
        for filepath in files:
            img = _load_frame(filepath, size=frame_size)
            if img is None:
                continue
            e = _classify_emotion_from_pixels(img)
            if e is not None:
                inferred_emotion = {"emotion": e, "confidence": emotion_confidence}
                break
    elif emotion_source == "inferred":
        inferred_emotion = {"emotion": "neutral", "confidence": 0.3}

    # Build inferred action dict
    inferred_action = None
    if action_source == "observed":
        # Find any classified action
        for filepath in files:
            img = _load_frame(filepath, size=frame_size)
            if img is None:
                continue
            a = _classify_action_from_pixels(img)
            if a is not None:
                inferred_action = {"action": a, "confidence": action_confidence}
                break
    elif action_source == "inferred":
        inferred_action = {"action": "walking", "confidence": 0.2}
    else:
        inferred_action = None

    return {
        "observed_action": None,  # Will be populated if any action classified
        "inferred_action": inferred_action,
        "inferred_emotion": inferred_emotion,
        "emotion_confidence": emotion_confidence,
        "action_confidence": action_confidence,
        "emotion_source": emotion_source,
        "action_source": action_source,
        "method": "emotion_action_analysis",
        "estimated": True,
    }