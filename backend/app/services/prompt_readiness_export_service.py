"""Prompt Readiness Report Export service (Day 30).

A deterministic, read-only serialization layer over the Day 29 Prompt
Readiness Report service. The flow is:

    stored video + selection + format
        -> Day 29 report (Day 28 snapshot + Day 27 timeline +
                           Day 16 selection)
        -> render json | markdown | txt
        -> deterministic export envelope

This answers only: "how can the exact Day 29 report be serialized for
download?" It never rebuilds report calculations: there is no Day 24
readiness logic, no Day 25 aggregation, no Day 26 transition logic, no
Day 27 timeline logic, and no Day 28 snapshot logic in this module -
every value rendered here comes verbatim from
``PromptReadinessReportService.generate_report``.

It never ranks versions, never chooses a best or worst version, never
recommends a version, never labels any number an improvement or a
degradation, and never evaluates which version is better or worse.
Markdown and TXT contain only factual report data - no evaluative
commentary is ever written.

No LLM, no network, no database, no filesystem writes. The service
creates no files in storage, persists nothing, and generates no
timestamps, random IDs, or UUIDs (the only time values rendered are
each snapshot's stored Day 16 ``created_at``). The report and every
stored record are read without modification: export is pure string
rendering of stored data.

Format handling mirrors the Day 19 ``PromptExportService``: the same
three formats (json, markdown, txt), the same ValueError message on an
unsupported format, the same media types, and the same envelope shape
({"format", "content", "media_type", "filename"}).
"""

import json

# Reuse Day 19's exact format contract (no second validation list).
from app.services.prompt_export_service import VALID_EXPORT_FORMATS

_MEDIA_TYPES = {
    "json": "application/json",
    "markdown": "text/markdown",
    "txt": "text/plain",
}

_EXTENSIONS = {
    "json": "json",
    "markdown": "md",
    "txt": "txt",
}

# Deterministic, stable download name: never derived from user input,
# never contains random IDs or version lists.
FILENAME_STEM = "visionprompt_readiness_report"


def _fmt(value) -> str:
    """Canonical neutral rendering of one report leaf value."""
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _list_text(values) -> str:
    """Render a list of report values as 'a, b, c' or 'none'."""
    if not values:
        return "none"
    return ", ".join(_fmt(value) for value in values)


def _coverage_text(value) -> str:
    """Render a coverage percentage as '61%' or 'none'."""
    if value is None:
        return "none"
    return f"{value}%"


def _leaf_values(obj):
    """Yield every scalar leaf of a JSON-like report structure."""
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _leaf_values(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _leaf_values(value)
    else:
        yield obj


class PromptReadinessExportService:
    """Deterministic read-only export of one Day 29 report (Day 30)."""

    def __init__(self, report_service):
        self.report_service = report_service

    def export_report(self, stored_filename: str, versions=None,
                      format: str = "json") -> dict:
        """Serialize the Day 29 report as json, markdown, or txt.

        Selection rules are exactly Day 29's (delegated unchanged):
        ``versions=None`` -> every live version ascending;
        ``versions=[...]`` -> requested order preserved, never
        substituted or reordered.

        Returns a deterministic envelope:
        {"format", "content", "media_type", "filename"} where
        "content" is always the fully rendered UTF-8 string and
        "filename" is the stable download name.

        Raises:
            ValueError: On unsupported format (Day 19's exact message)
            or when the report itself cannot be built (invalid
            versions list, missing/deleted version) - propagated from
            ``PromptReadinessReportService.generate_report`` with its
            exact messages.
        """
        if not isinstance(format, str) or format not in VALID_EXPORT_FORMATS:
            raise ValueError(
                "Invalid format. Must be one of: "
                + ", ".join(sorted(VALID_EXPORT_FORMATS))
            )

        report = self.report_service.generate_report(
            stored_filename, versions
        )

        if format == "json":
            content = self._render_json(report)
        elif format == "markdown":
            content = self._render_markdown(report)
        else:
            content = self._render_txt(report)

        return {
            "format": format,
            "content": content,
            "media_type": _MEDIA_TYPES[format],
            "filename": f"{FILENAME_STEM}.{_EXTENSIONS[format]}",
        }

    # --- JSON --------------------------------------------------------------

    def _render_json(self, report: dict) -> str:
        # Key order comes from the report dict itself (fixed by the
        # Day 29 service), indent is fixed, and there are no random
        # values - repeated exports are byte-identical. The trailing
        # newline keeps the file POSIX-friendly and stays semantically
        # identical to the report endpoint payload.
        return json.dumps(report, indent=2, ensure_ascii=False) + "\n"

    # --- Markdown ----------------------------------------------------------

    def _render_markdown(self, report: dict) -> str:
        sections = ["# Prompt Readiness Report"]
        sections.append("## Report\n\n" + self._md_report(report))
        sections.append(
            "## Version Readiness\n\n"
            + self._md_snapshots(report["report"]["snapshots"])
        )
        sections.append("## Timeline\n\n" + self._md_timeline(report["timeline"]))
        sections.append("## Summary\n\n" + self._md_summary(report["summary"]))
        return "\n\n".join(sections) + "\n"

    def _md_report(self, report: dict) -> str:
        meta = report["report"]
        return "\n".join([
            f"- Video: {report['video_filename']}",
            f"- Type: {meta['type']}",
            f"- Versions analyzed: {_list_text(report['versions_analyzed'])}",
            f"- Version count: {meta['version_count']}",
            f"- First version: {_fmt(meta['first_version'])}",
            f"- Last version: {_fmt(meta['last_version'])}",
            f"- Selection order: {_list_text(meta['selection_order'])}",
        ])

    def _md_snapshots(self, snapshots: list) -> str:
        if not snapshots:
            return "No saved versions."
        blocks = []
        for entry in snapshots:
            readiness = entry["readiness"]
            lines = [
                f"### Version {entry['version']}",
                "",
                f"- Source: {entry['source']}",
                f"- Operation: {entry['operation'] or '(empty)'}",
                f"- Created at: {entry['created_at']}",
                f"- Favorite: {_fmt(entry['favorite'])}",
                f"- Tags: {_list_text(entry['tags'])}",
                f"- Status: {readiness['status']}",
                "- Required coverage: "
                + _coverage_text(readiness["required_coverage_percentage"]),
                "",
                "#### Required Dimensions",
                "",
                "| Dimension | Status | Score |",
                "|---|---|---:|",
            ]
            for dimension, info in readiness["required"].items():
                lines.append(
                    f"| {dimension} | {info['status']} | {info['score']} |"
                )
            lines += [
                "",
                "#### Supporting Dimensions",
                "",
                "| Dimension | Status | Score |",
                "|---|---|---:|",
            ]
            for dimension, info in readiness["supporting"].items():
                lines.append(
                    f"| {dimension} | {info['status']} | {info['score']} |"
                )
            lines += [
                "",
                f"- Missing dimensions: "
                f"{_list_text(readiness['missing_dimensions'])}",
                f"- Weak dimensions: "
                f"{_list_text(readiness['weak_dimensions'])}",
            ]
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def _md_timeline(self, timeline: dict) -> str:
        parts = []
        steps = timeline["steps"]
        if not steps:
            parts.append("No timeline steps.")
        else:
            step_blocks = []
            for index, step in enumerate(steps, start=1):
                step_blocks.append(self._md_step(index, step))
            parts.append("\n\n".join(step_blocks))
        parts.append(self._md_timeline_summary(timeline))
        return "\n\n".join(parts)

    def _md_step(self, index: int, step: dict) -> str:
        version_a = step["version_a"]
        version_b = step["version_b"]
        lines = [
            f"### Step {index}: Version {version_a['version']} "
            f"\u2192 Version {version_b['version']}",
            "",
            f"- Version A: {version_a['version']} "
            f"(source: {version_a['source']}, "
            f"operation: {version_a['operation'] or '(empty)'}, "
            f"status: {version_a['readiness_status']}, "
            f"required coverage: "
            f"{version_a['required_coverage_percentage']}%)",
            f"- Version B: {version_b['version']} "
            f"(source: {version_b['source']}, "
            f"operation: {version_b['operation'] or '(empty)'}, "
            f"status: {version_b['readiness_status']}, "
            f"required coverage: "
            f"{version_b['required_coverage_percentage']}%)",
            f"- Dimensions changed: {step['dimensions_changed']}",
            f"- Dimensions unchanged: {step['dimensions_unchanged']}",
            f"- Required changes: {_list_text(step['required_changes'])}",
            f"- Supporting changes: {_list_text(step['supporting_changes'])}",
            "",
            "#### Step Dimensions",
            "",
            "| Dimension | A status | A score | B status | B score "
            "| Changed |",
            "|---|---|---:|---|---:|---|",
        ]
        for dimension in step["dimensions"]:
            state_a = dimension["version_a"]
            state_b = dimension["version_b"]
            lines.append(
                f"| {dimension['dimension']} "
                f"| {state_a['status']} | {state_a['score']} "
                f"| {state_b['status']} | {state_b['score']} "
                f"| {_fmt(dimension['changed'])} |"
            )
        lines += ["", "#### Transitions"]
        if step["transitions"]:
            for transition in step["transitions"]:
                lines.append(
                    f"- {transition['dimension']}: {transition['from']} "
                    f"-> {transition['to']}"
                )
        else:
            lines.append("- none")
        lines += ["", "#### Transition Summary"]
        for key, value in step["transition_summary"].items():
            lines.append(f"- {key}: {value}")
        coverage = step["required_coverage"]
        lines += [
            "",
            f"- Required coverage: {coverage['version_a']}% "
            f"-> {coverage['version_b']}% (delta {coverage['delta']})",
        ]
        return "\n".join(lines)

    def _md_timeline_summary(self, timeline: dict) -> str:
        lines = [
            "### Timeline Summary",
            "",
            f"- Changed dimensions: {timeline['changed_dimensions']}",
            f"- Unchanged dimensions: {timeline['unchanged_dimensions']}",
            f"- Required changes: {timeline['required_changes']}",
            f"- Supporting changes: {timeline['supporting_changes']}",
            "- Transition summary:",
        ]
        for key, value in timeline["transition_summary"].items():
            lines.append(f"  - {key}: {value}")
        lines.append(
            "- Required coverage delta: "
            f"{_fmt(timeline['required_coverage_delta'])}"
        )
        return "\n".join(lines)

    def _md_summary(self, summary: dict) -> str:
        required = summary["required"]
        supporting = summary["supporting"]
        parts = [
            "### Readiness\n\n" + "\n".join([
                f"- Versions analyzed: {summary['versions_analyzed']}",
                f"- Ready count: {summary['ready_count']}",
                f"- Needs attention count: "
                f"{summary['needs_attention_count']}",
            ]),
            "### Required\n\n" + "\n".join([
                f"- Total: {required['total']}",
                f"- Present: {required['present']}",
                f"- Weak: {required['weak']}",
                f"- Missing: {required['missing']}",
                "- Coverage: "
                + _coverage_text(required["coverage_percentage"]),
            ]),
            "### Supporting\n\n" + "\n".join([
                f"- Total: {supporting['total']}",
                f"- Present: {supporting['present']}",
                f"- Weak: {supporting['weak']}",
                f"- Missing: {supporting['missing']}",
            ]),
        ]
        dimension_lines = [
            "| Dimension | Present | Weak | Missing |",
            "|---|---:|---:|---:|",
        ]
        for row in summary["dimension_summary"]:
            dimension_lines.append(
                f"| {row['dimension']} | {row['present']} "
                f"| {row['weak']} | {row['missing']} |"
            )
        parts.append(
            "### Dimension Summary\n\n" + "\n".join(dimension_lines)
        )
        organization = summary["organization"]
        org_lines = [
            f"- Favorite count: {organization['favorite_count']}",
        ]
        if organization["tag_counts"]:
            org_lines.append("- Tags:")
            for tag, count in organization["tag_counts"].items():
                org_lines.append(f"  - {tag}: {count}")
        else:
            org_lines.append("- Tags: none")
        parts.append("### Organization\n\n" + "\n".join(org_lines))
        return "\n\n".join(parts)

    # --- TXT ---------------------------------------------------------------

    def _render_txt(self, report: dict) -> str:
        lines = [
            "PROMPT READINESS REPORT",
            "=======================",
            "",
            "REPORT",
            "------",
        ]
        lines += self._txt_report(report)
        lines += ["", "VERSION READINESS", "-----------------"]
        lines += self._txt_snapshots(report["report"]["snapshots"])
        lines += ["", "TIMELINE", "--------"]
        lines += self._txt_timeline(report["timeline"])
        lines += ["", "SUMMARY", "-------"]
        lines += self._txt_summary(report["summary"])
        return "\n".join(lines) + "\n"

    def _txt_report(self, report: dict) -> list:
        meta = report["report"]
        return [
            f"Video: {report['video_filename']}",
            f"Type: {meta['type']}",
            f"Versions analyzed: {_list_text(report['versions_analyzed'])}",
            f"Version count: {meta['version_count']}",
            f"First version: {_fmt(meta['first_version'])}",
            f"Last version: {_fmt(meta['last_version'])}",
            f"Selection order: {_list_text(meta['selection_order'])}",
        ]

    def _txt_snapshots(self, snapshots: list) -> list:
        if not snapshots:
            return ["No saved versions."]
        lines = []
        for index, entry in enumerate(snapshots):
            if index:
                lines.append("")
            readiness = entry["readiness"]
            lines += [
                f"VERSION {entry['version']}",
                f"Source: {entry['source']}",
                f"Operation: {entry['operation'] or '(empty)'}",
                f"Created at: {entry['created_at']}",
                f"Favorite: {_fmt(entry['favorite'])}",
                f"Tags: {_list_text(entry['tags'])}",
                f"Status: {readiness['status']}",
                "Required coverage: "
                + _coverage_text(readiness["required_coverage_percentage"]),
                "",
                "REQUIRED DIMENSIONS",
            ]
            for dimension, info in readiness["required"].items():
                lines.append(
                    f"{dimension}: {info['status']} ({info['score']})"
                )
            lines.append("")
            lines.append("SUPPORTING DIMENSIONS")
            for dimension, info in readiness["supporting"].items():
                lines.append(
                    f"{dimension}: {info['status']} ({info['score']})"
                )
            lines += [
                "",
                "Missing dimensions: "
                + _list_text(readiness["missing_dimensions"]),
                "Weak dimensions: " + _list_text(readiness["weak_dimensions"]),
            ]
        return lines

    def _txt_timeline(self, timeline: dict) -> list:
        steps = timeline["steps"]
        if not steps:
            lines = ["No timeline steps."]
        else:
            lines = []
            for index, step in enumerate(steps, start=1):
                if index > 1:
                    lines.append("")
                lines += self._txt_step(index, step)
        lines += ["", "TIMELINE SUMMARY"]
        lines += [
            f"Changed dimensions: {timeline['changed_dimensions']}",
            f"Unchanged dimensions: {timeline['unchanged_dimensions']}",
            f"Required changes: {timeline['required_changes']}",
            f"Supporting changes: {timeline['supporting_changes']}",
            "Transition summary:",
        ]
        for key, value in timeline["transition_summary"].items():
            lines.append(f"{key}: {value}")
        lines.append(
            "Required coverage delta: "
            + _fmt(timeline["required_coverage_delta"])
        )
        return lines

    def _txt_step(self, index: int, step: dict) -> list:
        version_a = step["version_a"]
        version_b = step["version_b"]
        lines = [
            f"Step {index}: Version {version_a['version']} "
            f"-> Version {version_b['version']}",
            f"Version A: {version_a['version']} "
            f"(source: {version_a['source']}, "
            f"operation: {version_a['operation'] or '(empty)'}, "
            f"status: {version_a['readiness_status']}, "
            f"required coverage: "
            f"{version_a['required_coverage_percentage']}%)",
            f"Version B: {version_b['version']} "
            f"(source: {version_b['source']}, "
            f"operation: {version_b['operation'] or '(empty)'}, "
            f"status: {version_b['readiness_status']}, "
            f"required coverage: "
            f"{version_b['required_coverage_percentage']}%)",
            f"Dimensions changed: {step['dimensions_changed']}",
            f"Dimensions unchanged: {step['dimensions_unchanged']}",
            f"Required changes: {_list_text(step['required_changes'])}",
            f"Supporting changes: {_list_text(step['supporting_changes'])}",
            "",
            "STEP DIMENSIONS",
        ]
        for dimension in step["dimensions"]:
            state_a = dimension["version_a"]
            state_b = dimension["version_b"]
            lines.append(
                f"{dimension['dimension']}: "
                f"{state_a['status']} ({state_a['score']}) -> "
                f"{state_b['status']} ({state_b['score']}), "
                f"changed: {_fmt(dimension['changed'])}"
            )
        lines.append("")
        lines.append("TRANSITIONS")
        if step["transitions"]:
            for transition in step["transitions"]:
                lines.append(
                    f"{transition['dimension']}: {transition['from']} -> "
                    f"{transition['to']}"
                )
        else:
            lines.append("none")
        lines.append("")
        lines.append("TRANSITION SUMMARY")
        for key, value in step["transition_summary"].items():
            lines.append(f"{key}: {value}")
        coverage = step["required_coverage"]
        lines.append("")
        lines.append(
            f"Required coverage: {coverage['version_a']}% -> "
            f"{coverage['version_b']}% (delta {coverage['delta']})"
        )
        return lines

    def _txt_summary(self, summary: dict) -> list:
        required = summary["required"]
        supporting = summary["supporting"]
        lines = [
            f"Versions analyzed: {summary['versions_analyzed']}",
            f"Ready count: {summary['ready_count']}",
            f"Needs attention count: {summary['needs_attention_count']}",
            "",
            "REQUIRED",
            f"Total: {required['total']}",
            f"Present: {required['present']}",
            f"Weak: {required['weak']}",
            f"Missing: {required['missing']}",
            "Coverage: " + _coverage_text(required["coverage_percentage"]),
            "",
            "SUPPORTING",
            f"Total: {supporting['total']}",
            f"Present: {supporting['present']}",
            f"Weak: {supporting['weak']}",
            f"Missing: {supporting['missing']}",
            "",
            "DIMENSION SUMMARY",
        ]
        if summary["dimension_summary"]:
            for row in summary["dimension_summary"]:
                lines.append(
                    f"{row['dimension']}: present {row['present']}, "
                    f"weak {row['weak']}, missing {row['missing']}"
                )
        else:
            lines.append("none")
        organization = summary["organization"]
        lines += [
            "",
            "ORGANIZATION",
            f"Favorite count: {organization['favorite_count']}",
        ]
        if organization["tag_counts"]:
            lines.append("Tags:")
            for tag, count in organization["tag_counts"].items():
                lines.append(f"{tag}: {count}")
        else:
            lines.append("Tags: none")
        return lines
