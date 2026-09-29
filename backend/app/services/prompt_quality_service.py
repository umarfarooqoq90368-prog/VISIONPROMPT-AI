"""Prompt Quality Analyzer service (Day 21).

A deterministic heuristic coverage analyzer for existing prompt text.
This is NOT a prompt-generation system and NOT an AI/LLM call: it only
scans the supplied prompt for conservative keyword/phrase signals and
reports which of nine quality dimensions contain detected information.

The analyzer never fabricates missing information, never modifies stored
prompts, history versions, favorites, or tags, and performs no network,
filesystem, or environment access.

Scoring model (documented, deterministic, integer, 0-100):

Per dimension, distinct signals are counted in the normalized prompt:
    0 signals  -> present=False, score=0   (missing)
    1 signal   -> present=True,  score=40  (present, weak)
    2 signals  -> present=True,  score=70  (present)
    3+ signals -> present=True,  score=100 (present, strong)

overall_score          = round-half-up of the mean of the 9 dimension scores
completeness_percentage = round-half-up of (present dimensions / 9) * 100

missing_dimensions = every dimension with present=False (dimension order)
suggestions        = "Add <name> information." for missing dimensions and
                     "Expand <name> information for better coverage." for
                     weak (score 40) dimensions, in dimension order.
"""

import re

DIMENSIONS = (
    "subject",
    "action",
    "environment",
    "camera",
    "lighting",
    "visual_style",
    "color",
    "composition",
    "audio",
)

WEAK_SCORE = 40

SIGNALS = {
    "subject": (
        "subject", "person", "people", "man", "woman", "girl", "boy",
        "child", "character", "figure", "face", "portrait", "silhouette",
        "animal", "dog", "cat", "bird", "robot", "dancer", "runner",
        "athlete",
    ),
    "action": (
        "action", "walking", "running", "moving", "turning", "rotating",
        "jumping", "dancing", "raising", "leaning", "crossing", "entering",
        "exiting", "pushing", "pulling", "holding", "reaching", "looking",
        "gesturing", "climbing", "sliding", "falling", "waving", "smiling",
        "sits", "stands",
    ),
    "environment": (
        "environment", "indoor", "outdoor", "forest", "city", "street",
        "room", "studio", "beach", "desert", "mountain", "park", "garden",
        "kitchen", "office", "market", "field", "interior", "exterior",
        "landscape", "urban", "rural", "rain", "snow", "fog", "background",
    ),
    "camera": (
        "camera", "shot", "close-up", "closeup", "close up", "wide shot",
        "medium shot", "long shot", "tracking", "dolly", "panning",
        "tilting", "zoom", "push-in", "pov", "angle", "framing",
        "cinematography", "shallow depth", "depth of field", "focus",
        "handheld", "steadicam", "aerial", "drone shot",
        "over-the-shoulder",
    ),
    "lighting": (
        "lighting", "light", "lit", "backlit", "rim light", "soft light",
        "hard light", "golden hour", "sunlight", "moonlight", "neon",
        "shadow", "shadows", "highlight", "glow", "lamplight",
        "candlelight", "overcast", "dusk", "dawn", "sunset", "sunrise",
        "volumetric light", "god rays", "chiaroscuro",
    ),
    "visual_style": (
        "visual style", "style", "cinematic", "documentary", "realistic",
        "photorealistic", "animated", "anime", "stylized", "vintage",
        "retro", "noir", "surreal", "minimalist", "epic", "dramatic",
        "naturalistic", "film grain", "35mm", "16mm", "aesthetic", "look",
    ),
    "color": (
        "color", "colour", "colorful", "monochrome", "black and white",
        "grayscale", "greyscale", "palette", "tone", "tones", "hue",
        "saturated", "desaturated", "vibrant", "muted", "warm tones",
        "cool tones", "teal", "orange", "crimson", "azure", "emerald",
        "pastel", "sepia",
    ),
    "composition": (
        "composition", "foreground", "background", "rule of thirds",
        "symmetry", "centered", "off-center", "framing", "negative space",
        "layered", "lead room", "headroom", "establishing shot", "profile",
    ),
    "audio": (
        "audio", "sound", "music", "ambient", "ambience", "silence",
        "footsteps", "dialogue", "voice", "voiceover", "narration",
        "soundtrack", "score", "heartbeat", "birds chirping", "humming",
        "echo", "whisper", "conversation", "crickets",
    ),
}

_PATTERNS = {
    dim: [
        re.compile(r"\b" + re.escape(signal) + r"\b")
        for signal in signals
    ]
    for dim, signals in SIGNALS.items()
}


class PromptQualityService:
    """Deterministic heuristic quality/coverage analysis of prompt text."""

    def analyze_prompt(self, prompt) -> dict:
        """Analyze one prompt and return a structured quality report.

        Raises:
            ValueError: When the prompt is not a string or is empty/
            whitespace-only.
        """
        if not isinstance(prompt, str):
            raise ValueError("prompt must be a string.")
        if not prompt.strip():
            raise ValueError("prompt must not be empty.")

        # Conservative normalization: lowercase + whitespace collapsing.
        # The original prompt is echoed back unchanged.
        normalized = " ".join(prompt.split()).lower()

        dimensions = {}
        missing = []
        suggestions = []
        for dim in DIMENSIONS:
            matches = sum(
                1 for pattern in _PATTERNS[dim] if pattern.search(normalized)
            )
            if matches == 0:
                present, score = False, 0
            elif matches == 1:
                present, score = True, WEAK_SCORE
            elif matches == 2:
                present, score = True, 70
            else:
                present, score = True, 100

            dimensions[dim] = {"present": present, "score": score}
            if not present:
                missing.append(dim)
                suggestions.append(
                    f"Add {dim.replace('_', ' ')} information."
                )
            elif score == WEAK_SCORE:
                suggestions.append(
                    f"Expand {dim.replace('_', ' ')} information "
                    "for better coverage."
                )

        scores = [dimensions[dim]["score"] for dim in DIMENSIONS]
        present_count = sum(
            1 for dim in DIMENSIONS if dimensions[dim]["present"]
        )

        return {
            "prompt": prompt,
            "quality": {
                "overall_score": int(sum(scores) / len(scores) + 0.5),
                "completeness_percentage": int(
                    present_count / len(DIMENSIONS) * 100 + 0.5
                ),
                "dimensions": dimensions,
                "missing_dimensions": missing,
                "suggestions": suggestions,
            },
        }
