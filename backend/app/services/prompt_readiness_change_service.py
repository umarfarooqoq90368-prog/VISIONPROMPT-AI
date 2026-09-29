"""Prompt Readiness Change Tracking service (Day 26).

A deterministic, read-only informational diff between the Day 24
readiness states of two saved prompt versions. The flow is:

    version A + version B -> Day 16 get_version (read-only)
                           -> Day 24 validate_prompt for each prompt
                           -> dimension-by-dimension state comparison
                           -> changed dimensions + transitions + deltas

This answers only: "which production-readiness dimensions changed
between these two saved prompt versions?" It never ranks versions,
never scores versions against each other, never chooses a preferred
version, never calls one version better/worse, and never predicts
video-generation quality. Coverage deltas are neutral arithmetic
differences, not improvements or gains.

No LLM, no network, no filesystem, no database operations. Every
output is a deterministic function of the two stored prompt texts (no
timestamps, random IDs, or environment values are produced). The
service never modifies history, favorites, tags, or either prompt, and
never saves the comparison result.

Day 24 readiness rules and Day 21 scores are reused exactly: statuses
are the Day 24 mapping (70/100 -> present, 40 -> weak, 0 -> missing)
applied to the raw Day 21 scores echoed from each checklist. Scores
are returned exactly as Day 21 reports them, but only a status change
counts as a readiness-state change (70 -> 100 is NOT a state change).
"""

from app.services.prompt_quality_service import DIMENSIONS
from app.services.prompt_readiness_service import (
    REQUIRED_DIMENSIONS,
    SUPPORTING_DIMENSIONS,
)

# The six possible directional state transitions (same-state excluded).
TRANSITION_KEYS = (
    "missing_to_weak",
    "missing_to_present",
    "weak_to_missing",
    "weak_to_present",
    "present_to_missing",
    "present_to_weak",
)


class PromptReadinessChangeService:
    """Deterministic readiness-state diff between two versions (Day 26)."""

    def __init__(self, history_service, readiness_service):
        self.history_service = history_service
        self.readiness_service = readiness_service

    def compare_versions(self, stored_filename: str,
                         version_a: int, version_b: int) -> dict:
        """Compare Day 24 readiness states of two saved versions.

        The requested direction is preserved: version A stays A and
        version B stays B (never sorted or swapped). Comparing a
        version with itself returns all dimensions unchanged.

        Raises:
            ValueError: If a version number is not a positive integer
            or the version does not exist (including deleted ones).
        """
        record_a = self.history_service.get_version(
            stored_filename, version_a
        )
        record_b = self.history_service.get_version(
            stored_filename, version_b
        )
        readiness_a = self.readiness_service.validate_prompt(
            record_a["prompt"]
        )["readiness"]
        readiness_b = self.readiness_service.validate_prompt(
            record_b["prompt"]
        )["readiness"]

        checks_a = {
            item["dimension"]: item for item in readiness_a["checklist"]
        }
        checks_b = {
            item["dimension"]: item for item in readiness_b["checklist"]
        }

        dimensions = []
        transitions = []
        changed_dimensions = []
        required_changes = []
        supporting_changes = []
        transition_summary = {key: 0 for key in TRANSITION_KEYS}

        for dimension in DIMENSIONS:
            state_a = checks_a[dimension]["status"]
            state_b = checks_b[dimension]["status"]
            changed = state_a != state_b
            dimensions.append({
                "dimension": dimension,
                "version_a": {
                    "status": state_a,
                    "score": checks_a[dimension]["score"],
                },
                "version_b": {
                    "status": state_b,
                    "score": checks_b[dimension]["score"],
                },
                "changed": changed,
            })
            if changed:
                changed_dimensions.append(dimension)
                transitions.append({
                    "dimension": dimension,
                    "from": state_a,
                    "to": state_b,
                })
                transition_summary[f"{state_a}_to_{state_b}"] += 1
                if dimension in REQUIRED_DIMENSIONS:
                    required_changes.append(dimension)
                else:
                    supporting_changes.append(dimension)

        coverage_a = readiness_a["coverage"][
            "required_coverage_percentage"
        ]
        coverage_b = readiness_b["coverage"][
            "required_coverage_percentage"
        ]

        return {
            "video_filename": stored_filename,
            "version_a": self._summary(record_a, readiness_a),
            "version_b": self._summary(record_b, readiness_b),
            "dimensions": dimensions,
            "changed_dimensions": changed_dimensions,
            "dimensions_changed": len(changed_dimensions),
            "dimensions_unchanged": len(DIMENSIONS) - len(changed_dimensions),
            "required_changes": required_changes,
            "supporting_changes": supporting_changes,
            "transitions": transitions,
            "transition_summary": transition_summary,
            "required_coverage": {
                "version_a": coverage_a,
                "version_b": coverage_b,
                "delta": coverage_b - coverage_a,
            },
        }

    @staticmethod
    def _summary(record: dict, readiness: dict) -> dict:
        """Informational per-version block (no comparative claims)."""
        return {
            "version": record["version"],
            "source": record["source"],
            "operation": record["operation"],
            "readiness_status": readiness["status"],
            "required_coverage_percentage": readiness["coverage"][
                "required_coverage_percentage"
            ],
        }
