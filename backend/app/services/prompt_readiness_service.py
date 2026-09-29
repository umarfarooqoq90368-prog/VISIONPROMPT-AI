"""Production Readiness Validator service (Day 24).

A deterministic, read-only validation layer over the Day 21 Prompt
Quality Analyzer. The flow is:

    prompt -> PromptQualityService (Day 21, single source of truth)
           -> structural readiness rules (required vs supporting)
           -> checklist + coverage + neutral suggestions

This answers only: "does this prompt contain enough structured
information to be considered ready for production-oriented AI video
prompting?" It never claims a video will be good, never predicts model
output, and never ranks one prompt against another.

No LLM, no network, no filesystem, no database operations. Every output
is a deterministic function of the input prompt text (no timestamps,
random IDs, or environment values are produced).

The service never modifies history, favorites, tags, or the prompt
itself, and never saves readiness reports anywhere.
"""

from app.services.prompt_quality_service import DIMENSIONS

# Structural split (not a quality ranking): core information needed for
# production-oriented video prompting vs supporting extra detail.
REQUIRED_DIMENSIONS = (
    "subject",
    "action",
    "environment",
    "camera",
    "lighting",
    "visual_style",
    "composition",
)
SUPPORTING_DIMENSIONS = (
    "color",
    "audio",
)

STATUS_PRESENT = "present"
STATUS_WEAK = "weak"
STATUS_MISSING = "missing"

READY = "ready"
NEEDS_ATTENTION = "needs_attention"

_LABELS = {
    "subject": "Subject",
    "action": "Action",
    "environment": "Environment",
    "camera": "Camera",
    "lighting": "Lighting",
    "visual_style": "Visual style",
    "color": "Color",
    "composition": "Composition",
    "audio": "Audio",
}


def _status_for_score(score: int) -> str:
    """Map a Day 21 score to a readiness status.

    Day 21 only produces 0, 40, 70, and 100:
    100 -> present, 70 -> present, 40 -> weak, 0 -> missing.
    Day 21 scoring itself is never altered.
    """
    if score >= 70:
        return STATUS_PRESENT
    if score > 0:
        return STATUS_WEAK
    return STATUS_MISSING


def _message(label: str, status: str) -> str:
    if status == STATUS_PRESENT:
        return f"{label} information detected."
    if status == STATUS_WEAK:
        return (
            f"{label} information is present but may need more detail."
        )
    return f"{label} information is not detected."


def _suggestion(dim: str, status: str) -> str:
    name = dim.replace("_", " ")
    if status == STATUS_MISSING:
        return f"Specify {name} information if known."
    if status == STATUS_WEAK:
        return f"Expand {name} information if known."
    return ""


class PromptReadinessService:
    """Deterministic production readiness validation (Day 24)."""

    def __init__(self, quality_service):
        self.quality_service = quality_service

    def validate_prompt(self, prompt: str) -> dict:
        """Validate prompt readiness without modifying anything.

        Raises:
            ValueError: When the prompt is not a string or is empty/
            whitespace-only (same validation as Day 21).
        """
        if not isinstance(prompt, str):
            raise ValueError("prompt must be a string.")
        if not prompt.strip():
            raise ValueError("prompt must not be empty.")

        report = self.quality_service.analyze_prompt(prompt)["quality"]

        checklist = []
        statuses = {}
        for dim in DIMENSIONS:
            score = report["dimensions"][dim]["score"]
            status = _status_for_score(score)
            statuses[dim] = status
            checklist.append({
                "dimension": dim,
                "status": status,
                "present": status == STATUS_PRESENT,
                "score": score,
                "message": _message(_LABELS[dim], status),
            })

        coverage = self._coverage(statuses, REQUIRED_DIMENSIONS, "required")
        coverage.update(
            self._coverage(statuses, SUPPORTING_DIMENSIONS, "supporting")
        )

        required_ok = all(
            statuses[dim] == STATUS_PRESENT for dim in REQUIRED_DIMENSIONS
        )

        missing_dimensions = [
            dim for dim in DIMENSIONS
            if statuses[dim] == STATUS_MISSING
        ]
        weak_dimensions = [
            dim for dim in DIMENSIONS if statuses[dim] == STATUS_WEAK
        ]
        suggestions = [
            _suggestion(dim, statuses[dim])
            for dim in DIMENSIONS
            if statuses[dim] != STATUS_PRESENT
        ]

        return {
            "prompt": prompt,
            "readiness": {
                "status": READY if required_ok else NEEDS_ATTENTION,
                "required_dimensions": list(REQUIRED_DIMENSIONS),
                "supporting_dimensions": list(SUPPORTING_DIMENSIONS),
                "checklist": checklist,
                "coverage": coverage,
                "missing_dimensions": missing_dimensions,
                "weak_dimensions": weak_dimensions,
                "suggestions": suggestions,
            },
        }

    @staticmethod
    def _coverage(statuses: dict, dimensions: tuple, prefix: str) -> dict:
        """Count statuses for one dimension group.

        `*_present` counts only status == "present" (Day 21 score 70 or
        100); weak dimensions (score 40) do NOT count as present.
        `*_coverage_percentage` = round(present / total * 100), an
        integer between 0 and 100.
        """
        total = len(dimensions)
        present = sum(
            1 for dim in dimensions if statuses[dim] == STATUS_PRESENT
        )
        missing = sum(
            1 for dim in dimensions if statuses[dim] == STATUS_MISSING
        )
        weak = sum(1 for dim in dimensions if statuses[dim] == STATUS_WEAK)
        return {
            f"{prefix}_total": total,
            f"{prefix}_present": present,
            f"{prefix}_missing": missing,
            f"{prefix}_weak": weak,
            f"{prefix}_coverage_percentage": (
                round(present / total * 100) if total else 0
            ),
        }
