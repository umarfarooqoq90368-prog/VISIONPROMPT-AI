"""Prompt Readiness Snapshot service (Day 28).

A deterministic, read-only layer that produces a compact structured
snapshot of the readiness state of one or more saved prompt versions.
The flow is:

    stored video -> Day 16 list/get versions (read-only)
                 -> Day 24 validate_prompt for each selected prompt
                 -> Day 17 organization metadata (favorite/tags)
                 -> per-version snapshot + neutral aggregate summary

This answers only: "what does the current readiness state of these
saved versions look like?" It never ranks versions, never selects a
best version, never declares one version superior, never recommends a
version, and never predicts which prompt will generate better video
output.

No LLM, no network, no filesystem, no database operations. Every
output is a deterministic function of stored metadata (the only time
value ever returned is `created_at`, which is stored Day 16 version
metadata - the service itself generates no timestamps, random IDs, or
environment values).

The service never modifies history, favorites, tags, or any prompt,
and never saves snapshot results anywhere. Day 24 readiness rules are
reused exactly - statuses, scores, and coverage are never recomputed
or altered - and Day 17 organization metadata is returned verbatim.
"""

from app.services.prompt_quality_service import DIMENSIONS
from app.services.prompt_readiness_service import (
    REQUIRED_DIMENSIONS,
    SUPPORTING_DIMENSIONS,
)


class PromptReadinessSnapshotService:
    """Deterministic readiness snapshot across saved versions (Day 28)."""

    def __init__(self, history_service, readiness_service,
                 organization_service):
        self.history_service = history_service
        self.readiness_service = readiness_service
        self.organization_service = organization_service

    def create_snapshot(self, stored_filename: str,
                        versions=None) -> dict:
        """Snapshot Day 24 readiness of selected saved versions.

        Selection rules (identical to Day 25/27):
        - ``versions=None``: every live version, ascending version order.
        - ``versions=[...]``: only those versions, in the requested
          order (deterministic; never substituted or reordered).

        Raises:
            ValueError: When the versions list is invalid (not a
            non-empty list of unique positive integers) or when a
            requested version does not exist (including deleted ones).
        """
        records = self._select(stored_filename, versions)

        snapshots = []
        ready_count = 0
        needs_attention_count = 0
        required_totals = {"present": 0, "weak": 0, "missing": 0}
        supporting_totals = {"present": 0, "weak": 0, "missing": 0}
        dimension_counts = {
            dim: {"present": 0, "weak": 0, "missing": 0}
            for dim in DIMENSIONS
        }
        favorite_count = 0
        tag_counts = {}

        for record in records:
            readiness = self.readiness_service.validate_prompt(
                record["prompt"]
            )["readiness"]
            organization = self.organization_service.get_organization(
                stored_filename, record["version"]
            )

            checks = {
                item["dimension"]: item for item in readiness["checklist"]
            }
            required = {
                dim: {
                    "status": checks[dim]["status"],
                    "score": checks[dim]["score"],
                }
                for dim in REQUIRED_DIMENSIONS
            }
            supporting = {
                dim: {
                    "status": checks[dim]["status"],
                    "score": checks[dim]["score"],
                }
                for dim in SUPPORTING_DIMENSIONS
            }

            snapshots.append({
                "version": record["version"],
                "source": record["source"],
                "operation": record["operation"],
                "created_at": record["created_at"],
                "favorite": organization["favorite"],
                "tags": list(organization["tags"]),
                "readiness": {
                    "status": readiness["status"],
                    "required_coverage_percentage": readiness[
                        "coverage"
                    ]["required_coverage_percentage"],
                    "required": required,
                    "supporting": supporting,
                    "missing_dimensions": list(
                        readiness["missing_dimensions"]
                    ),
                    "weak_dimensions": list(readiness["weak_dimensions"]),
                },
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
                    counts["present"] += 1
                elif item["status"] == "weak":
                    counts["weak"] += 1
                else:
                    counts["missing"] += 1

            if organization["favorite"]:
                favorite_count += 1
            for tag in organization["tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        required_total = len(records) * len(REQUIRED_DIMENSIONS)
        supporting_total = len(records) * len(SUPPORTING_DIMENSIONS)

        if records:
            dimension_summary = [
                {"dimension": dim, **dimension_counts[dim]}
                for dim in DIMENSIONS
            ]
        else:
            dimension_summary = []

        summary = {
            "versions_analyzed": len(records),
            "ready_count": ready_count,
            "needs_attention_count": needs_attention_count,
            "required": {
                "total": required_total,
                "present": required_totals["present"],
                "weak": required_totals["weak"],
                "missing": required_totals["missing"],
                "coverage_percentage": (
                    round(required_totals["present"]
                          / required_total * 100)
                    if required_total else None
                ),
            },
            "supporting": {
                "total": supporting_total,
                "present": supporting_totals["present"],
                "weak": supporting_totals["weak"],
                "missing": supporting_totals["missing"],
            },
            "dimension_summary": dimension_summary,
            "organization": {
                "favorite_count": favorite_count,
                "tag_counts": {
                    tag: tag_counts[tag] for tag in sorted(tag_counts)
                },
            },
        }

        return {
            "video_filename": stored_filename,
            "versions_analyzed": [record["version"] for record in records],
            "snapshots": snapshots,
            "summary": summary,
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
