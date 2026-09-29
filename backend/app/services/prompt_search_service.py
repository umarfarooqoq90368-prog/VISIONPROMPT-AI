"""Prompt Search & Filtering service (Day 18).

A read/filter layer over the Day 16 Prompt History service (single source
of truth for versions) and the Day 17 Prompt Organization service
(favorite flag + tags metadata).

There is no second version store. Search never modifies stored prompt
text, never fabricates video information, and never returns deleted
versions.
"""

from typing import Optional

from app.services.prompt_history_service import PromptHistoryService, VALID_SOURCES
from app.services.prompt_organization_service import PromptOrganizationService, MAX_TAG_LENGTH

VALID_SORTS = {"version_asc", "version_desc", "created_at_asc", "created_at_desc"}


class PromptSearchService:
    """Deterministic in-memory search over existing history + organization."""

    def __init__(
        self,
        history_service: PromptHistoryService,
        organization_service: PromptOrganizationService,
    ):
        self._history = history_service
        self._organization = organization_service

    def search_versions(
        self,
        video_filename: str,
        query: Optional[str] = None,
        source: Optional[str] = None,
        operation: Optional[str] = None,
        favorite: Optional[bool] = None,
        tag: Optional[str] = None,
        min_version: Optional[int] = None,
        max_version: Optional[int] = None,
        sort: str = "version_asc",
    ) -> list:
        """Filter existing prompt versions. All filters are AND-combined.

        Raises:
            ValueError: On invalid filter values (source, tag, range, sort).
        """
        if source is not None and source not in VALID_SOURCES:
            raise ValueError(
                "Invalid source. Must be one of: "
                + ", ".join(sorted(VALID_SOURCES))
            )
        if sort not in VALID_SORTS:
            raise ValueError(
                "Invalid sort. Must be one of: "
                + ", ".join(sorted(VALID_SORTS))
            )

        self._validate_range(min_version, max_version)
        normalized_tag = self._normalize_tag(tag)
        search_text = query.strip().lower() if isinstance(query, str) else None
        if search_text == "":
            search_text = None

        # Day 16 history is the single source of truth: deleted versions
        # are never returned because they no longer exist there.
        results = []
        for record in self._history.list_versions(video_filename):
            if source is not None and record["source"] != source:
                continue
            if operation is not None and record["operation"] != operation:
                continue
            if min_version is not None and record["version"] < min_version:
                continue
            if max_version is not None and record["version"] > max_version:
                continue
            if search_text is not None and search_text not in record["prompt"].lower():
                continue

            org = self._organization.get_organization(
                video_filename, record["version"]
            )
            if favorite is not None and org["favorite"] != favorite:
                continue
            if normalized_tag is not None and normalized_tag not in org["tags"]:
                continue

            results.append({
                "version_id": record["version_id"],
                "video_filename": record["video_filename"],
                "version": record["version"],
                "source": record["source"],
                "operation": record["operation"],
                "prompt": record["prompt"],
                "negative_prompt": record["negative_prompt"],
                "created_at": record["created_at"],
                "metadata": dict(record.get("metadata", {})),
                "favorite": org["favorite"],
                "tags": list(org["tags"]),
            })

        return self._sort(results, sort)

    def _sort(self, results: list, sort: str) -> list:
        if sort == "version_asc":
            return sorted(results, key=lambda r: r["version"])
        if sort == "version_desc":
            return sorted(results, key=lambda r: r["version"], reverse=True)
        if sort == "created_at_asc":
            return sorted(
                results, key=lambda r: (r["created_at"], r["version"])
            )
        return sorted(
            results, key=lambda r: (r["created_at"], r["version"]), reverse=True
        )

    def _validate_range(
        self, min_version: Optional[int], max_version: Optional[int]
    ) -> None:
        for name, value in (("min_version", min_version), ("max_version", max_version)):
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
        if (
            min_version is not None
            and max_version is not None
            and min_version > max_version
        ):
            raise ValueError("min_version must not be greater than max_version.")

    def _normalize_tag(self, tag: Optional[str]) -> Optional[str]:
        if tag is None:
            return None
        if not isinstance(tag, str):
            raise ValueError("tag must be a string.")
        normalized = tag.strip().lower()
        if not normalized:
            return None
        if len(normalized) > MAX_TAG_LENGTH:
            raise ValueError(
                f"tag must be at most {MAX_TAG_LENGTH} characters."
            )
        return normalized
