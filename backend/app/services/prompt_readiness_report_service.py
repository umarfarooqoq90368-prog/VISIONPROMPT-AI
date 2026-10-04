"""Prompt Readiness Report service (Day 29).

A deterministic, read-only orchestration layer that combines existing
readiness information into one structured report for a video. The flow
is:

    stored video -> Day 28 snapshot (Day 16 selection, Day 24 readiness
                          per version, Day 17 favorite/tags, aggregate)
                 -> Day 27 timeline (Day 26 chained diffs, neutral totals)
                 -> report metadata + combined report payload

This answers only: "what does the structured readiness report for these
saved versions look like?" It never ranks versions, never chooses a
best or worst version, never recommends a version, never labels any
number an improvement or a degradation, and never predicts which prompt
will generate better video output.

No LLM, no network, no filesystem, no database operations. Every output
is a deterministic function of stored metadata (the only time value
ever returned is each snapshot's `created_at`, which is stored Day 16
version metadata - the service itself generates no timestamps, random
IDs, UUIDs, or environment values).

Dependency graph (kept minimal per the service contracts):
- Day 28 `PromptReadinessSnapshotService` already holds the Day 16
  history store, the Day 24 readiness service, and the Day 17
  organization service, and applies Day 25 selection semantics.
- Day 27 `PromptReadinessTimelineService` already holds the Day 16
  history store and the Day 26 change service, and applies the same
  Day 25 selection semantics.
Both services share the single Day 16 store, so the report introduces
no second store and no duplicate readiness, transition, selection, or
aggregation logic. The report itself only assembles their outputs plus
deterministic report metadata.

The service never modifies history, favorites, tags, or any prompt,
and never saves report results anywhere. Every section is byte-equal
to the existing service output it reuses: `summary` and the per-version
snapshots are exactly Day 28's, `timeline.steps` and the timeline
totals are exactly Day 27's.
"""


class PromptReadinessReportService:
    """Deterministic readiness report across saved versions (Day 29)."""

    def __init__(self, readiness_timeline_service,
                 readiness_snapshot_service):
        self.readiness_timeline_service = readiness_timeline_service
        self.readiness_snapshot_service = readiness_snapshot_service

    def generate_report(self, stored_filename: str,
                        versions=None) -> dict:
        """Combine Day 28 snapshot and Day 27 timeline into one report.

        Selection rules (identical to Day 25/27/28):
        - ``versions=None``: every live version, ascending version order.
        - ``versions=[...]``: only those versions, in the requested
          order (deterministic; never substituted or reordered).

        The report contains exactly five top-level keys:
        ``video_filename``, ``versions_analyzed``, ``report``
        (deterministic metadata plus the exact Day 28 per-version
        snapshots), ``timeline`` (the exact Day 27 steps plus neutral
        totals), and ``summary`` (the exact Day 28 aggregate summary).

        Raises:
            ValueError: When the versions list is invalid (not a
            non-empty list of unique positive integers) or when a
            requested version does not exist (including deleted ones) -
            raised by the delegated services with their exact messages.
        """
        snapshot = self.readiness_snapshot_service.create_snapshot(
            stored_filename, versions
        )
        timeline = self.readiness_timeline_service.build_timeline(
            stored_filename, versions
        )

        # Both delegated services resolve selection through the same
        # Day 16 store with identical Day 25 semantics, so their
        # selected version lists always match for equal inputs.
        selected = snapshot["versions_analyzed"]
        timeline_summary = timeline["summary"]

        report_timeline = {
            "steps": timeline["timeline"],
            "changed_dimensions": timeline_summary[
                "dimensions_changed_total"],
            "unchanged_dimensions": timeline_summary[
                "dimensions_unchanged_total"],
            "required_changes": timeline_summary[
                "required_changes_total"],
            "supporting_changes": timeline_summary[
                "supporting_changes_total"],
            "transition_summary": dict(
                timeline_summary["transition_summary"]
            ),
            "required_coverage_delta": (
                timeline_summary["required_coverage_delta"]
                if selected else None
            ),
        }

        report_metadata = {
            "type": "prompt_readiness_report",
            "version_count": len(selected),
            "first_version": selected[0] if selected else None,
            "last_version": selected[-1] if selected else None,
            "selection_order": list(selected),
            "snapshots": snapshot["snapshots"],
        }

        return {
            "video_filename": stored_filename,
            "versions_analyzed": list(selected),
            "report": report_metadata,
            "timeline": report_timeline,
            "summary": snapshot["summary"],
        }
