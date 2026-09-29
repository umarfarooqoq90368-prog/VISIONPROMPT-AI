"""Prompt History & Versioning service (Day 16).

Deterministic in-memory storage for generated prompt versions. The storage
is abstracted behind service methods so it can later be replaced by
PostgreSQL/SQLite without changing the API contract.

No database, no external services. Never exposes internal storage
structures or absolute filesystem paths.
"""

import re
from datetime import datetime, timezone
from typing import Optional

VALID_SOURCES = {"advanced_prompt", "refinement", "template", "custom"}


class PromptHistoryService:
    """Maintains prompt versions safely and deterministically.

    Version numbers are sequential per video and are never renumbered
    after a deletion: deleting version 2 from [1, 2, 3] leaves [1, 3]
    and the next created version is 4.
    """

    def __init__(self):
        self._storage = {}

    def create_version(
        self,
        video_filename: str,
        prompt: str,
        negative_prompt: str = "",
        source: str = "custom",
        operation: str = "",
        metadata: Optional[dict] = None,
    ) -> dict:
        """Save a generated prompt as a new version.

        Raises:
            ValueError: On invalid or empty input.
        """
        if not isinstance(video_filename, str) or not video_filename.strip():
            raise ValueError("video_filename must be a non-empty string.")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must not be empty.")
        if not isinstance(negative_prompt, str):
            raise ValueError("negative_prompt must be a string.")
        if not isinstance(source, str) or source not in VALID_SOURCES:
            raise ValueError(
                "Invalid source. Must be one of: "
                + ", ".join(sorted(VALID_SOURCES))
            )
        if not isinstance(operation, str):
            raise ValueError("operation must be a string.")
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a dict.")

        versions = self._storage.setdefault(video_filename, {})
        next_version = max(versions) + 1 if versions else 1

        record = {
            "version_id": f"{video_filename}:{next_version}",
            "video_filename": video_filename,
            "version": next_version,
            "source": source,
            "operation": operation,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": dict(metadata),
        }
        versions[next_version] = record
        return self._copy(record)

    def list_versions(self, video_filename: str) -> list:
        """Return versions ordered by ascending version number ([] if none)."""
        versions = self._storage.get(video_filename, {})
        return [
            self._copy(versions[v]) for v in sorted(versions)
        ]

    def get_version(self, video_filename: str, version: int) -> dict:
        """Return the exact saved version.

        Raises:
            ValueError: If the version does not exist or input is invalid.
        """
        self._validate_version(version)
        versions = self._storage.get(video_filename, {})
        record = versions.get(version)
        if record is None:
            raise ValueError(
                f"Version {version} not found for video '{video_filename}'."
            )
        return self._copy(record)

    def delete_version(self, video_filename: str, version: int) -> dict:
        """Delete only that version. Remaining versions are NOT renumbered.

        Raises:
            ValueError: If the version does not exist or input is invalid.
        """
        self._validate_version(version)
        versions = self._storage.get(video_filename, {})
        record = versions.get(version)
        if record is None:
            raise ValueError(
                f"Version {version} not found for video '{video_filename}'."
            )
        del versions[version]
        if not versions:
            self._storage.pop(video_filename, None)
        return self._copy(record)

    def compare_versions(
        self, video_filename: str, version_a: int, version_b: int
    ) -> dict:
        """Return a deterministic token-based comparison of two versions.

        Raises:
            ValueError: If either version does not exist or input is invalid.
        """
        a = self.get_version(video_filename, version_a)
        b = self.get_version(video_filename, version_b)

        tokens_a = self._tokens(a["prompt"])
        tokens_b = self._tokens(b["prompt"])
        set_a = set(tokens_a)
        set_b = set(tokens_b)

        common = [t for t in dict.fromkeys(tokens_a) if t in set_b]
        added = [t for t in dict.fromkeys(tokens_b) if t not in set_a]
        removed = [t for t in dict.fromkeys(tokens_a) if t not in set_b]

        return {
            "video_filename": video_filename,
            "version_a": a["version"],
            "version_b": b["version"],
            "prompt_a": a["prompt"],
            "prompt_b": b["prompt"],
            "negative_prompt_a": a["negative_prompt"],
            "negative_prompt_b": b["negative_prompt"],
            "added_tokens": added,
            "removed_tokens": removed,
            "common_tokens": common,
            "changed": bool(added or removed),
        }

    def save_advanced_prompt(self, video_filename: str, prompt_result: dict) -> dict:
        """Save Day 13 AdvancedPromptService output as a version."""
        return self.create_version(
            video_filename=video_filename,
            prompt=prompt_result["prompt"],
            negative_prompt=prompt_result.get("negative_prompt") or "",
            source="advanced_prompt",
            operation=str(prompt_result.get("style", "")),
            metadata={"sections_keys": sorted(prompt_result.get("sections", {}).keys())}
            if isinstance(prompt_result.get("sections"), dict)
            else {},
        )

    def save_refinement(self, video_filename: str, refinement_result: dict) -> dict:
        """Save Day 14 PromptRefinementService output as a version."""
        return self.create_version(
            video_filename=video_filename,
            prompt=refinement_result["refined_prompt"],
            negative_prompt=refinement_result.get("negative_prompt") or "",
            source="refinement",
            operation=str(refinement_result.get("operation", "")),
            metadata={"preserved_information": refinement_result.get("preserved_information")},
        )

    def save_template(self, video_filename: str, template_result: dict) -> dict:
        """Save Day 15 PromptTemplateService output as a version."""
        return self.create_version(
            video_filename=video_filename,
            prompt=template_result["prompt"],
            negative_prompt=template_result.get("negative_prompt") or "",
            source="template",
            operation=str(template_result.get("template", "")),
            metadata={"custom_instruction": template_result.get("custom_instruction", "")},
        )

    def _validate_version(self, version) -> None:
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise ValueError("version must be a positive integer.")

    def _tokens(self, text: str) -> list:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _copy(self, record: dict) -> dict:
        copied = dict(record)
        copied["metadata"] = dict(record.get("metadata", {}))
        return copied
