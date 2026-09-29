"""Prompt Package Generation service (Day 20).

A read-only packaging layer over the Day 16 Prompt History service
(single source of truth for versions), the Day 17 Prompt Organization
service (favorite flag + tags), and the Day 19 Prompt Export service
(JSON/Markdown/TXT rendering).

There is no second version store. Package generation never modifies
stored prompts, never modifies favorites/tags, never fabricates video
information, and never returns deleted versions. Output is deterministic:
the same stored version always produces a byte-identical ZIP.
"""

import io
import json
import zipfile

from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_export_service import PromptExportService

PACKAGE_FILES = (
    "prompt.json",
    "prompt.md",
    "prompt.txt",
    "package_metadata.json",
)

METADATA_KEYS = (
    "video_filename",
    "version",
    "version_id",
    "source",
    "operation",
    "created_at",
    "favorite",
    "tags",
)

# Fixed timestamp for every ZIP entry so repeated generation of the same
# version is byte-identical (ZIP epoch: 1980-01-01 00:00:00).
_FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)


class PromptPackageService:
    """Deterministic read-only ZIP packaging of one existing history version."""

    def __init__(
        self,
        history_service: PromptHistoryService,
        organization_service: PromptOrganizationService,
        export_service: PromptExportService,
    ):
        self._history = history_service
        self._organization = organization_service
        self._export = export_service

    def create_package(self, stored_filename: str, version: int) -> dict:
        """Build the ZIP package for one live version.

        Returns a deterministic envelope:
        {"content" (ZIP bytes), "media_type", "filename", "files",
        "metadata"}.

        Raises:
            ValueError: When the version is invalid, nonexistent, or
            deleted (Day 16 history is the single source of truth).
        """
        # Verifies the version exists (deleted/nonexistent -> ValueError).
        # Day 17 organization metadata is read for the same live version.
        record = self._history.get_version(stored_filename, version)
        org = self._organization.get_organization(stored_filename, version)

        metadata = {
            "video_filename": record["video_filename"],
            "version": record["version"],
            "version_id": record["version_id"],
            "source": record["source"],
            "operation": record["operation"],
            "created_at": record["created_at"],
            "favorite": org["favorite"],
            "tags": list(org["tags"]),
        }

        # Reuse the Day 19 export service - no duplicated formatting logic.
        files = {
            "prompt.json": self._export.export_version(
                stored_filename, version, "json"
            )["content"],
            "prompt.md": self._export.export_version(
                stored_filename, version, "markdown"
            )["content"],
            "prompt.txt": self._export.export_version(
                stored_filename, version, "txt"
            )["content"],
            "package_metadata.json": json.dumps(
                metadata, indent=2, ensure_ascii=False
            ),
        }

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in PACKAGE_FILES:
                info = zipfile.ZipInfo(name, date_time=_FIXED_DATE_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0
                zf.writestr(info, files[name].encode("utf-8"))

        return {
            "content": buffer.getvalue(),
            "media_type": "application/zip",
            "filename": f"visionprompt_video_v{version}.zip",
            "files": list(PACKAGE_FILES),
            "metadata": metadata,
        }
