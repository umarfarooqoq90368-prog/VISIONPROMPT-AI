"""Prompt Export & Packaging service (Day 19).

A read-only presentation layer over the Day 16 Prompt History service
(single source of truth for versions) and the Day 17 Prompt Organization
service (favorite flag + tags metadata).

There is no second version store. Export never modifies stored prompts,
never modifies favorites/tags, never fabricates video information, and
never returns deleted versions. Output is fully deterministic: the same
stored version always produces byte-identical export content.
"""

import json
import re
from pathlib import Path

from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService

VALID_EXPORT_FORMATS = {"json", "markdown", "txt"}

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


class PromptExportService:
    """Deterministic read-only export of one existing history version."""

    def __init__(
        self,
        history_service: PromptHistoryService,
        organization_service: PromptOrganizationService,
    ):
        self._history = history_service
        self._organization = organization_service

    def export_version(
        self, stored_filename: str, version: int, format: str
    ) -> dict:
        """Export one live version as json, markdown, or txt.

        Returns a deterministic envelope:
        {"format", "content", "media_type", "filename"} where "content"
        is always the fully rendered string.

        Raises:
            ValueError: On unsupported format or when the version does
            not exist (deleted versions included).
        """
        if not isinstance(format, str) or format not in VALID_EXPORT_FORMATS:
            raise ValueError(
                "Invalid format. Must be one of: "
                + ", ".join(sorted(VALID_EXPORT_FORMATS))
            )

        # Day 16 history is the single source of truth: a deleted or
        # nonexistent version raises ValueError (surfaced as 404 by the API).
        record = self._history.get_version(stored_filename, version)
        org = self._organization.get_organization(stored_filename, version)

        data = {
            "video_filename": record["video_filename"],
            "version": record["version"],
            "version_id": record["version_id"],
            "source": record["source"],
            "operation": record["operation"],
            "prompt": record["prompt"],
            "negative_prompt": record["negative_prompt"],
            "created_at": record["created_at"],
            "metadata": dict(record.get("metadata", {})),
            "favorite": org["favorite"],
            "tags": list(org["tags"]),
        }

        if format == "json":
            content = self._render_json(data)
        elif format == "markdown":
            content = self._render_markdown(data)
        else:
            content = self._render_txt(data)

        return {
            "format": format,
            "content": content,
            "media_type": _MEDIA_TYPES[format],
            "filename": self._filename(data["video_filename"], version, format),
        }

    def _render_json(self, data: dict) -> str:
        # Fixed key order comes from the data dict literal in export_version,
        # so the serialized structure is deterministic.
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _render_markdown(self, data: dict) -> str:
        sections = ["# VisionPrompt AI Prompt"]
        sections.append(f"## Video\n\n`{data['video_filename']}`")
        sections.append(f"## Version\n\n{data['version']}")
        sections.append(f"## Source\n\n{data['source']}")
        sections.append(
            "## Operation\n\n" + (data["operation"] or "(empty)")
        )
        sections.append(f"## Prompt\n\n{data['prompt']}")
        sections.append(
            "## Negative Prompt\n\n" + (data["negative_prompt"] or "(empty)")
        )
        if data["tags"]:
            sections.append(
                "## Tags\n\n" + "\n".join(f"* {tag}" for tag in data["tags"])
            )
        else:
            sections.append("## Tags\n\n(none)")
        sections.append(f"## Favorite\n\n{str(data['favorite']).lower()}")
        sections.append(f"## Created At\n\n{data['created_at']}")
        if data["metadata"]:
            sections.append(
                "## Metadata\n\n```json\n"
                + json.dumps(data["metadata"], indent=2, ensure_ascii=False)
                + "\n```"
            )
        return "\n\n".join(sections) + "\n"

    def _render_txt(self, data: dict) -> str:
        lines = [
            "# VISIONPROMPT AI PROMPT",
            "",
            f"Video: {data['video_filename']}",
            f"Version: {data['version']}",
            f"Source: {data['source']}",
            f"Operation: {data['operation'] or '(empty)'}",
            f"Favorite: {str(data['favorite']).lower()}",
            "Tags: " + (", ".join(data["tags"]) if data["tags"] else "(none)"),
            f"Created At: {data['created_at']}",
            "",
            "## PROMPT",
            "",
            data["prompt"],
            "",
            "## NEGATIVE PROMPT",
            "",
            data["negative_prompt"] or "(empty)",
        ]
        if data["metadata"]:
            lines += [
                "",
                "## METADATA",
                "",
                json.dumps(data["metadata"], indent=2, ensure_ascii=False),
            ]
        return "\n".join(lines) + "\n"

    def _filename(self, video_filename: str, version: int, format: str) -> str:
        """Deterministic, safe download filename (no raw user input)."""
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(video_filename).stem)
        if not stem:
            stem = "video"
        return f"visionprompt_{stem}_v{version}.{_EXTENSIONS[format]}"
