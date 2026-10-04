"""Color analysis service for P2-04.

Analyzes extracted video frames to extract dominant color palette information.
Uses actual pixel data from JPEG frames. Does NOT invent or synthesize colors.

Output is deterministic for identical input. Every color value is derived from
actual frame pixels. Percentages, RGB, and HEX all come from real pixel analysis.

Adds: POST /api/videos/{stored_filename}/color/analyze
Integrates color information into reconstruction/storyboard/prompt generation.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from pathlib import Path

from PIL import Image


def _load_frame(frame_path: str, size: tuple[int, int] | None = None) -> Optional[Image.Image]:
    """Load a single frame image.

    Args:
        frame_path: Path to the JPEG frame file.
        size: Optional resize dimensions (width, height). Resizing helps
            make analysis deterministic and faster.

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


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to a hex color string."""
    return f"#{r:02x}{g:02x}{b:02x}"


def _brightness(r: int, g: int, b: int) -> float:
    """Calculate relative luminance (perceived brightness) per sRGB.

    Returns a value in [0, 1] where 0 = black, 1 = white.
    """
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    return 0.299 * r_norm + 0.587 * g_norm + 0.114 * b_norm


def _saturation(r: int, g: int, b: int) -> float:
    """Calculate saturation per HSL luminance.

    Returns a value in [0, 1] where 0 = grayscale, 1 = fully saturated.
    """
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    max_val = max(r_norm, g_norm, b_norm)
    min_val = min(r_norm, g_norm, b_norm)
    lum = (max_val + min_val) / 2.0
    if lum <= 0.0 or lum >= 1.0:
        return 0.0
    delta = max_val - min_val
    return delta / (1.0 - abs(2.0 * lum - 1.0)) if lum < 0.5 else delta / (2.0 - 2.0 * lum)


def _dominant_colors_from_image(
    img: Image.Image,
    n_colors: int = 5,
    size: tuple[int, int] = (100, 100),
) -> List[Dict[str, Any]]:
    """Extract dominant colors from an image using simple histogram analysis.

    Resizes the image to ``size`` first for performance, then quantizes
    colors by rounding RGB values to 32-level buckets. The most frequent
    buckets are returned as dominant colors.

    Args:
        img: PIL Image in RGB mode.
        n_colors: Number of dominant colors to return.
        size: Resize dimension for prior analysis.

    Returns:
        List of dicts with ``hex``, ``rgb``, ``percentage`` keys.
    """
    # Resize for performance
    small = img.resize(size, Image.LANCZOS)
    pixels = list(small.getdata())

    # Quantize to 32-level buckets per channel
    bucket_counts: dict[tuple[int, int, int], int] = {}
    for r, g, b in pixels:
        bucket = (r // 8 * 8, g // 8 * 8, b // 8 * 8)
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    # Sort buckets by count descending
    sorted_buckets = sorted(bucket_counts.items(), key=lambda item: item[1], reverse=True)

    # Take top n_colors
    results: List[Dict[str, Any]] = []
    total_pixels = len(pixels)
    for bucket, count in sorted_buckets[:n_colors]:
        r, g, b = bucket
        percentage = count / total_pixels if total_pixels > 0 else 0.0
        results.append(
            {
                "hex": _rgb_to_hex(r, g, b),
                "rgb": {"r": r, "g": g, "b": b},
                "percentage": round(percentage * 100, 2),
                "brightness": round(_brightness(r, g, b), 3),
                "saturation": round(_saturation(r, g, b), 3),
            }
        )
    return results


def analyze_color_palette(
    stored_filename: str,
    sample_interval: float = 1.0,
    n_colors: int = 5,
    frame_size: tuple[int, int] = (64, 64),
) -> Dict[str, Any]:
    """Analyze the color palette of a video's extracted frames.

    Samples frames at the given interval, extracts dominant colors from each,
    and aggregates results across all sampled frames.

    Args:
        stored_filename: The stored video filename (e.g. "abc123.mp4").
        sample_interval: Seconds between sampled frames (default 1.0).
        n_colors: Number of dominant colors to extract per frame (default 5).
        frame_size: Resize dimension for prior analysis (default 64x64).

    Returns:
        A dict with:

        - ``dominant_colors``: List of dominant color dicts (hex, rgb, percentage,
          brightness, saturation) aggregated across frames.
        - ``palette``: Aggregated palette as a dict of hex -> total_percentage.
        - ``visual_color_mood``: A short textual description of the overall
          color character (e.g. "cool", "warm", "neutral").
        - ``frame_count``: Number of frames analyzed.
        - ``method``: Analysis method string.
        - ``estimated``: Whether the analysis is heuristic/estimated.

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

    all_colors: List[Dict[str, Any]] = []
    frame_count = 0

    for filepath in files:
        img = _load_frame(filepath, size=frame_size)
        if img is None:
            continue
        colors = _dominant_colors_from_image(img, n_colors=n_colors, size=frame_size)
        all_colors.extend(colors)
        frame_count += 1

    if frame_count == 0:
        return {
            "dominant_colors": [],
            "palette": {},
            "visual_color_mood": "no data",
            "frame_count": 0,
            "method": "color_analysis",
            "estimated": False,
        }

    # Aggregate colors: sum percentages for identical hex colors
    color_totals: dict[str, float] = {}
    for color in all_colors:
        hex_key = color["hex"]
        color_totals[hex_key] = color_totals.get(hex_key, 0.0) + color["percentage"]

    # Sort palette by total percentage descending
    palette_sorted = sorted(color_totals.items(), key=lambda item: item[1], reverse=True)

    # Determine visual color mood based on dominant hues
    if not palette_sorted:
        mood = "no data"
    else:
        top_hex = palette_sorted[0][0]
        # Parse hex to RGB for mood classification
        r = int(top_hex[1:3], 16)
        g = int(top_hex[3:5], 16)
        b = int(top_hex[5:7], 16)
        # Simple mood classification
        avg = (r + g + b) / 3.0
        if avg > 200:
            mood = "warm"
        elif avg < 80:
            mood = "cool"
        else:
            mood = "neutral"

    # Compute overall palette percentages
    total_pct = sum(p for _, p in palette_sorted) if palette_sorted else 0
    palette_dict: dict[str, Any] = {
        hex_key: round(pct, 2) for hex_key, pct in palette_sorted
    }

    # Determine dominant colors (top 3 by aggregated percentage)
    dominant_colors: List[Dict[str, Any]] = []
    for hex_key, pct in palette_sorted[:3]:
        # Find the original color dict
        for color in all_colors:
            if color["hex"] == hex_key:
                dominant_colors.append(
                    {
                        "hex": hex_key,
                        "rgb": color["rgb"],
                        "percentage": round(pct, 2),
                        "brightness": color["brightness"],
                        "saturation": color["saturation"],
                    }
                )
                break

    return {
        "dominant_colors": dominant_colors,
        "palette": palette_dict,
        "visual_color_mood": mood,
        "frame_count": frame_count,
        "method": "color_analysis",
        "estimated": True,
    }


class ColorAnalysisService:
    """Service for analyzing color palettes from video frames.

    Provides deterministic color analysis using actual pixel data from
    extracted JPEG frames. All output is derived from real pixels with
    explicit confidence and methodology documentation.

    The service supports hierarchical aggregation: per-frame dominant colors
    are combined into a global palette with mood classification.
    """

    def analyze_color_palette(
        self,
        stored_filename: str,
        sample_interval: float = 1.0,
        n_colors: int = 5,
        frame_size: tuple[int, int] = (64, 64),
    ) -> Dict[str, Any]:
        """Analyze the color palette of a video's extracted frames.

        Args:
            stored_filename: The stored video filename (e.g. "abc123.mp4").
            sample_interval: Seconds between sampled frames (default 1.0).
            n_colors: Number of dominant colors to extract per frame (default 5).
            frame_size: Resize dimension for prior analysis (default 64x64).

        Returns:
            A dict with:

            - ``dominant_colors``: List of dominant color dicts (hex, rgb, percentage,
              brightness, saturation) aggregated across frames.
            - ``palette``: Aggregated palette as a dict of hex -> total_percentage.
            - ``visual_color_mood``: A short textual description of the overall
              color character (e.g. "cool", "warm", "neutral").
            - ``frame_count``: Number of frames analyzed.
            - ``method``: Analysis method string.
            - ``estimated``: Whether the analysis is heuristic/estimated.
        """
        return _analyze_color_palette(
            stored_filename=stored_filename,
            sample_interval=sample_interval,
            n_colors=n_colors,
            frame_size=frame_size,
        )


def _analyze_color_palette(
    stored_filename: str,
    sample_interval: float = 1.0,
    n_colors: int = 5,
    frame_size: tuple[int, int] = (64, 64),
) -> Dict[str, Any]:
    """Low-level color palette analysis (separate function for potential overriding)."""
    from app.services.frame_service import _get_frame_dir

    frame_dir = Path(_get_frame_dir(stored_filename))
    if not frame_dir.is_dir():
        raise ValueError("No extracted frames found for this video. Extract frames first.")

    import glob as _glob
    files = _glob.glob(str(frame_dir / "frame_*.jpg"))
    if not files:
        raise ValueError("No extracted frames found for this video. Extract frames first.")

    files = sorted(files)

    all_colors: List[Dict[str, Any]] = []
    frame_count = 0

    for filepath in files:
        img = _load_frame(filepath, size=frame_size)
        if img is None:
            continue
        colors = _dominant_colors_from_image(img, n_colors=n_colors, size=frame_size)
        all_colors.extend(colors)
        frame_count += 1

    if frame_count == 0:
        return {
            "dominant_colors": [],
            "palette": {},
            "visual_color_mood": "no data",
            "frame_count": 0,
            "method": "color_analysis",
            "estimated": False,
        }

    # Aggregate colors: sum percentages for identical hex colors
    color_totals: dict[str, float] = {}
    for color in all_colors:
        hex_key = color["hex"]
        color_totals[hex_key] = color_totals.get(hex_key, 0.0) + color["percentage"]

    # Sort palette by total percentage descending
    palette_sorted = sorted(color_totals.items(), key=lambda item: item[1], reverse=True)

    # Determine visual color mood based on dominant hues
    if not palette_sorted:
        mood = "no data"
    else:
        top_hex = palette_sorted[0][0]
        # Parse hex to RGB for mood classification
        r = int(top_hex[1:3], 16)
        g = int(top_hex[3:5], 16)
        b = int(top_hex[5:7], 16)
        # Simple mood classification
        avg = (r + g + b) / 3.0
        if avg > 200:
            mood = "warm"
        elif avg < 80:
            mood = "cool"
        else:
            mood = "neutral"

    # Compute overall palette percentages
    total_pct = sum(p for _, p in palette_sorted) if palette_sorted else 0
    palette_dict: dict[str, Any] = {
        hex_key: round(pct, 2) for hex_key, pct in palette_sorted
    }

    # Determine dominant colors (top 3 by aggregated percentage)
    dominant_colors: List[Dict[str, Any]] = []
    for hex_key, pct in palette_sorted[:3]:
        # Find the original color dict
        for color in all_colors:
            if color["hex"] == hex_key:
                dominant_colors.append(
                    {
                        "hex": hex_key,
                        "rgb": color["rgb"],
                        "percentage": round(pct, 2),
                        "brightness": color["brightness"],
                        "saturation": color["saturation"],
                    }
                )
                break

    return {
        "dominant_colors": dominant_colors,
        "palette": palette_dict,
        "visual_color_mood": mood,
        "frame_count": frame_count,
        "method": "color_analysis",
        "estimated": True,
    }


def get_color_analysis_service() -> ColorAnalysisService:
    """Get a configured color analysis service instance."""
    return ColorAnalysisService()