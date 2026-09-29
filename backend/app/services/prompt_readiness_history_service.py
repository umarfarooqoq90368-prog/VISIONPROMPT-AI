"""Prompt Readiness History Analysis service (Day 25).

A deterministic, read-only analysis layer over the Day 16 Prompt History
system and the Day 24 Production Readiness Validator. The flow is:

    stored video -> Day 16 list/get versions (read-only)
                 -> Day 24 validate_prompt for each selected prompt
                 -> per-version readiness + aggregate summary
                 -> dimension occurrence summary

This answers only: "what readiness information is available across the
saved prompt versions?" It never ranks versions, never selects a best
version, never declares one version superior, and never predicts which
prompt will generate better video output.

No LLM, no network, no filesystem, no database operations. Every output
is a deterministic function of the stored prompt texts (no timestamps,
random IDs, or environment values are produced by the analysis).

The service never modifies history, favorites, tags, or any prompt, and
never saves analysis results anywhere. Day 24 readiness rules are reused
exactly - statuses, scores, and coverage are never recomputed or altered.
"""

from app.services.prompt_quality_service import DIMENSIONS
from app.services.prompt_readiness_service import (
    REQUIRED_DIMENSIONS,
    SUPPORTING_DIMENSIONS,
)


class PromptReadinessHistoryService:
    """Deterministic readiness analysis across saved versions (Day 25)."""

    def __init__(self, history_service, readiness_service):
        self.history_service = history_service
        self.readiness_service = readiness_service

    def analyze_versions(self, stored_filename: str,
                         versions=None) -> dict:
        """Analyze Day 24 readiness across selected saved versions.

        Selection rules:
        - ``versions=None``: every live version, ascending version order.
        - ``versions=[...]``: only those versions, in the requested
          order (deterministic; never substituted or reordered).

        Raises:
            ValueError: When the versions list is invalid (not a
            non-empty list of unique positive integers) or when a
            requested version does not exist (including deleted ones).
        """
        records = self._select(stored_filename, versions)

        results = []
        ready_count = 0
        needs_attention_count = 0
        required_totals = {"present": 0, "weak": 0, "missing": 0}
        supporting_totals = {"present": 0, "weak": 0, "missing": 0}
        dimension_counts = {
            dim: {"present_count": 0, "weak_count": 0, "missing_count": 0}
            for dim in DIMENSIONS
        }

        for record in records:
            readiness = self.readiness_service.validate_prompt(
                record["prompt"]
            )["readiness"]

            results.append({
                "version": record["version"],
                "version_id": record["version_id"],
                "source": record["source"],
                "operation": record["operation"],
                "readiness": readiness,
            })

            if readiness["status"] == "ready":
                ready_count += 1
            else:
                needs_attention_count += 1

            coverage = readiness["coverage"]
            for key in ("present", "weak", "missing"):
                required_totals[key] += coverage[f"required_{key}"]
                supporting_totals[key] += coverage[f"supporting_{key}"]

            for item in readiness["checklist"]:
                counts = dimension_counts[item["dimension"]]
                if item["status"] == "present":
                    counts["present_count"] += 1
                elif item["status"] == "weak":
                    counts["weak_count"] += 1
                else:
                    counts["missing_count"] += 1

        versions_analyzed = [r["version"] for r in results]
        required_total = len(records) * len(REQUIRED_DIMENSIONS)
        supporting_total = len(records) * len(SUPPORTING_DIMENSIONS)

        summary = {
            "versions_analyzed": len(records),
            "ready_count": ready_count,
            "needs_attention_count": needs_attention_count,
            "required_dimensions_total": required_total,
            "required_dimensions_present": required_totals["present"],
            "required_dimensions_weak": required_totals["weak"],
            "required_dimensions_missing": required_totals["missing"],
            "required_coverage_percentage": _percentage(
                required_totals["present"], required_total
            ),
            "supporting_dimensions_total": supporting_total,
            "supporting_dimensions_present": supporting_totals["present"],
            "supporting_dimensions_weak": supporting_totals["weak"],
            "supporting_dimensions_missing": supporting_totals["missing"],
            "supporting_coverage_percentage": _percentage(
                supporting_totals["present"], supporting_total
            ),
        }

        dimension_summary = [
            {"dimension": dim, **dimension_counts[dim]}
            for dim in DIMENSIONS
        ]

        return {
            "video_filename": stored_filename,
            "versions_analyzed": versions_analyzed,
            "results": results,
            "summary": summary,
            "dimension_summary": dimension_summary,
        }

    def _select(self, stored_filename: str, versions):
        """Resolve the requested versions to stored records (read-only)."""
        if versions is None:
            # list_versions already returns ascending version order
            return self.history_service.list_versions(stored_filename)

        if not isinstance(versions, (list, tuple)) or not versions:
            raise ValueError(
                "versions must be a non-empty list of positive integers."
            )
        seen = set()
        for version in versions:
            if type(version) is not int or version < 1:
                raise ValueError(
                    "versions must contain positive integers."
                )
            if version in seen:
                raise ValueError("duplicate versions are not allowed.")
            seen.add(version)

        return [
            self.history_service.get_version(stored_filename, version)
            for version in versions
        ]


def _percentage(present: int, total: int) -> int:
    """round(present / total * 100), bounded to 0-100 (0 when empty)."""
    if total <= 0:
        return 0
    return round(present / total * 100)
