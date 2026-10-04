"""Prompt Readiness Timeline service (Day 27).

A deterministic, read-only layer that chains Day 26 readiness diffs
across consecutive saved prompt versions. The flow is:

    stored video -> Day 16 list/get versions (read-only)
                 -> Day 26 compare_versions for each consecutive pair
                 -> chained timeline of readiness-state changes
                 -> neutral aggregate summary

This answers only: "how did production readiness change between each
consecutive pair of saved versions?" It never ranks versions, never
picks a best version, never declares one version superior, and never
predicts which prompt will generate better video output. Coverage
deltas are neutral arithmetic differences, not improvements or gains.

No LLM, no network, no filesystem, no database operations. Every
output is a deterministic function of the stored prompt texts (no
timestamps, random IDs, or environment values are produced). The
service never modifies history, favorites, tags, or any prompt, and
never saves timeline results anywhere.

Each timeline step is byte-for-byte what Day 26 `compare_versions`
returns for that pair of versions: Day 24 readiness states and Day 21
scores are never recomputed or altered here.
"""

from app.services.prompt_quality_service import DIMENSIONS
from app.services.prompt_readiness_change_service import TRANSITION_KEYS


class PromptReadinessTimelineService:
    """Deterministic readiness change chain across saved versions (Day 27)."""

    def __init__(self, history_service, readiness_change_service):
        self.history_service = history_service
        self.readiness_change_service = readiness_change_service

    def build_timeline(self, stored_filename: str,
                       versions=None) -> dict:
        """Chain Day 26 readiness diffs across consecutive versions.

        Selection rules (identical to Day 25):
        - ``versions=None``: every live version, ascending version order.
        - ``versions=[...]``: only those versions, in the requested
          order (deterministic; never substituted or reordered).

        The timeline contains one Day 26 comparison per consecutive
        pair of the selected versions, in selection order. A video
        with no saved versions (or a single version) returns an empty
        timeline with HTTP 200 semantics.

        Raises:
            ValueError: When the versions list is invalid (not a
            non-empty list of unique positive integers) or when a
            requested version does not exist (including deleted ones).
        """
        records = self._select(stored_filename, versions)
        selected = [record["version"] for record in records]

        timeline = [
            self.readiness_change_service.compare_versions(
                stored_filename,
                records[index]["version"],
                records[index + 1]["version"],
            )
            for index in range(len(records) - 1)
        ]

        changed_total = 0
        unchanged_total = 0
        required_total = 0
        supporting_total = 0
        transition_totals = {key: 0 for key in TRANSITION_KEYS}

        for step in timeline:
            changed_total += step["dimensions_changed"]
            unchanged_total += step["dimensions_unchanged"]
            required_total += len(step["required_changes"])
            supporting_total += len(step["supporting_changes"])
            for key in TRANSITION_KEYS:
                transition_totals[key] += step["transition_summary"][key]

        if timeline:
            first_coverage = timeline[0]["required_coverage"]["version_a"]
            last_coverage = timeline[-1]["required_coverage"]["version_b"]
        elif selected:
            # Single selected version: the same-version Day 26 compare
            # supplies that version's own Day 24 coverage block.
            same = self.readiness_change_service.compare_versions(
                stored_filename, selected[0], selected[0]
            )
            first_coverage = same["version_a"]["required_coverage_percentage"]
            last_coverage = same["version_b"]["required_coverage_percentage"]
        else:
            first_coverage = None
            last_coverage = None

        summary = {
            "versions_analyzed": len(records),
            "steps": len(timeline),
            "dimensions_changed_total": changed_total,
            "dimensions_unchanged_total": unchanged_total,
            "required_changes_total": required_total,
            "supporting_changes_total": supporting_total,
            "transition_summary": transition_totals,
            "first_version": selected[0] if selected else None,
            "last_version": selected[-1] if selected else None,
            "first_required_coverage_percentage": first_coverage,
            "last_required_coverage_percentage": last_coverage,
            "required_coverage_delta": (
                last_coverage - first_coverage
                if first_coverage is not None and last_coverage is not None
                else 0
            ),
        }

        return {
            "video_filename": stored_filename,
            "versions_analyzed": selected,
            "steps": len(timeline),
            "timeline": timeline,
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
