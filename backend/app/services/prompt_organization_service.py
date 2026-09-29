"""Prompt Favorites & Tags organization service (Day 17).

Deterministic metadata layer layered ON TOP of the Day 16 Prompt History
service. There is no second version store: favorites and tags reference
existing Day 16 version records only.

Tags are explicit user-provided metadata. They are never inferred from
video content (objects, characters, locations, actions, camera, lighting,
colors, brands, audio, dialogue) and prompt text is never modified.
"""

from typing import Optional

from app.services.prompt_history_service import PromptHistoryService

MAX_TAG_LENGTH = 50


class PromptOrganizationService:
    """Attaches favorite flags and tags to existing prompt versions."""

    def __init__(self, history_service: PromptHistoryService):
        self._history = history_service
        self._org = {}

    def favorite_version(self, video_filename: str, version: int) -> dict:
        """Mark an existing version as favorite (idempotent)."""
        self._require_version(video_filename, version)
        self._entry(video_filename, version)["favorite"] = True
        return {
            "video_filename": video_filename,
            "version": version,
            "favorite": True,
        }

    def unfavorite_version(self, video_filename: str, version: int) -> dict:
        """Remove an existing version from favorites (idempotent)."""
        self._require_version(video_filename, version)
        self._entry(video_filename, version)["favorite"] = False
        return {
            "video_filename": video_filename,
            "version": version,
            "favorite": False,
        }

    def add_tags(
        self, video_filename: str, version: int, tags: list
    ) -> dict:
        """Add normalized tags to an existing version.

        Normalization: trim whitespace, lowercase, drop empty/whitespace
        tags, drop duplicates over 50 chars rejected, alphabetical order.
        """
        self._require_version(video_filename, version)
        normalized = self._normalize_tags(tags)
        entry = self._entry(video_filename, version)
        entry["tags"] = sorted(set(entry["tags"]) | set(normalized))
        return {
            "video_filename": video_filename,
            "version": version,
            "tags": list(entry["tags"]),
        }

    def remove_tags(
        self, video_filename: str, version: int, tags: list
    ) -> dict:
        """Remove tags from an existing version (missing tags are harmless)."""
        self._require_version(video_filename, version)
        normalized = self._normalize_tags(tags)
        entry = self._entry(video_filename, version)
        entry["tags"] = sorted(set(entry["tags"]) - set(normalized))
        return {
            "video_filename": video_filename,
            "version": version,
            "tags": list(entry["tags"]),
        }

    def get_organization(self, video_filename: str, version: int) -> dict:
        """Return favorite flag and tags for one existing version."""
        entry = self._read_entry(video_filename, version)
        return {
            "video_filename": video_filename,
            "version": version,
            "favorite": entry["favorite"],
            "tags": list(entry["tags"]),
        }

    def list_favorites(self, video_filename: str) -> list:
        """Favorite versions only, ascending (deleted versions excluded)."""
        existing = self._existing_versions(video_filename)
        results = []
        for version in sorted(existing):
            entry = self._read_entry(video_filename, version)
            if entry["favorite"]:
                results.append({
                    "version": version,
                    "favorite": True,
                    "tags": list(entry["tags"]),
                })
        return results

    def list_by_tag(self, video_filename: str, tag: str) -> list:
        """Versions carrying the exact normalized tag, ascending."""
        if not isinstance(tag, str):
            raise ValueError("tag must be a string.")
        normalized = tag.strip().lower()
        if not normalized:
            return []
        if len(normalized) > MAX_TAG_LENGTH:
            raise ValueError(
                f"tag must be at most {MAX_TAG_LENGTH} characters."
            )
        existing = self._existing_versions(video_filename)
        results = []
        for version in sorted(existing):
            entry = self._read_entry(video_filename, version)
            if normalized in entry["tags"]:
                results.append({
                    "version": version,
                    "favorite": entry["favorite"],
                    "tags": list(entry["tags"]),
                })
        return results

    def _require_version(self, video_filename: str, version: int) -> None:
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise ValueError("version must be a positive integer.")
        try:
            self._history.get_version(video_filename, version)
        except ValueError as e:
            raise e

    def _entry(self, video_filename: str, version: int) -> dict:
        """Get or create the org entry, resetting it if the version was
        deleted and recreated (created_at no longer matches)."""
        origin = self._history.get_version(video_filename, version)["created_at"]
        video_org = self._org.setdefault(video_filename, {})
        entry = video_org.get(version)
        if entry is None or entry.get("_origin") != origin:
            entry = {"favorite": False, "tags": [], "_origin": origin}
            video_org[version] = entry
        return entry

    def _read_entry(self, video_filename: str, version: int) -> dict:
        """Fresh org entry for an existing version (never creates stale data)."""
        origin = self._history.get_version(video_filename, version)["created_at"]
        entry = self._org.get(video_filename, {}).get(version)
        if entry is None or entry.get("_origin") != origin:
            return {"favorite": False, "tags": []}
        return {"favorite": entry["favorite"], "tags": list(entry["tags"])}

    def _existing_versions(self, video_filename: str) -> set:
        return {
            record["version"]
            for record in self._history.list_versions(video_filename)
        }

    def _normalize_tags(self, tags) -> list:
        if not isinstance(tags, list):
            raise ValueError("tags must be a list of strings.")
        normalized = []
        for tag in tags:
            if not isinstance(tag, str):
                raise ValueError("tags must be a list of strings.")
            cleaned = tag.strip().lower()
            if not cleaned:
                continue
            if len(cleaned) > MAX_TAG_LENGTH:
                raise ValueError(
                    f"each tag must be at most {MAX_TAG_LENGTH} characters."
                )
            normalized.append(cleaned)
        return sorted(set(normalized))
