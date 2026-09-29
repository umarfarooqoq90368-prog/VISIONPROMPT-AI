"""Prompt Version Comparison & Diff service (Day 23).

A deterministic, read-only comparison layer over the Day 16 Prompt
History system and the Day 21 Prompt Quality Analyzer. The flow is:

    version A + version B -> Day 16 history (read-only)
                          -> difflib word-level diff of the two prompts
                          -> Day 21 quality report for each prompt
                          -> structured comparison

This is a comparison/analysis feature only. It NEVER:

- generates or fabricates new factual video information
- modifies either history version, favorites, or tags
- saves a new version or the comparison result itself

No LLM, no network, no filesystem, no database operations. Every output
is a deterministic function of the two stored prompt strings (no
timestamps, random IDs, or environment values are produced; the diff,
quality reports, and deltas are pure functions of the input text).
"""

import difflib
import re

from app.services.prompt_quality_service import DIMENSIONS


def _tokenize(text: str) -> list:
    """Split into tokens that each carry their *leading* whitespace
    (plus a final token for any trailing whitespace).

    Leading attachment means appending a word never changes the token
    of the previous word, so appends show up as clean inserts. Joining
    the tokens back together reconstructs the original text exactly,
    so the diff never loses or invents characters.
    """
    return re.findall(r"\s*\S+|\s+$", text)


def _neutral_label(delta: int) -> str:
    """Describe a delta without ranking either version as better."""
    if delta > 0:
        return "increased"
    if delta < 0:
        return "decreased"
    return "unchanged"


class PromptComparisonService:
    """Deterministic, read-only prompt version comparison (Day 23)."""

    def __init__(self, history_service, quality_service):
        self.history_service = history_service
        self.quality_service = quality_service

    def compare_versions(self, stored_filename: str, version_a: int,
                         version_b: int) -> dict:
        """Compare two stored prompt versions without modifying anything.

        Raises:
            ValueError: When either version does not exist or the version
            number is invalid (raised by the Day 16 history service).
        """
        record_a = self.history_service.get_version(stored_filename, version_a)
        record_b = self.history_service.get_version(stored_filename, version_b)

        quality_a = self.quality_service.analyze_prompt(
            record_a["prompt"]
        )["quality"]
        quality_b = self.quality_service.analyze_prompt(
            record_b["prompt"]
        )["quality"]

        tokens_a = _tokenize(record_a["prompt"])
        tokens_b = _tokenize(record_b["prompt"])
        matcher = difflib.SequenceMatcher(None, tokens_a, tokens_b,
                                          autojunk=False)

        added_parts = []
        removed_parts = []
        common_parts = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                common_parts.append("".join(tokens_a[i1:i2]))
            elif tag == "insert":
                added_parts.append("".join(tokens_b[j1:j2]))
            elif tag == "delete":
                removed_parts.append("".join(tokens_a[i1:i2]))
            else:  # replace
                removed_parts.append("".join(tokens_a[i1:i2]))
                added_parts.append("".join(tokens_b[j1:j2]))

        added_text = "".join(added_parts)
        removed_text = "".join(removed_parts)
        identical = record_a["prompt"] == record_b["prompt"]

        score_delta = (quality_b["overall_score"]
                       - quality_a["overall_score"])
        completeness_delta = (quality_b["completeness_percentage"]
                              - quality_a["completeness_percentage"])

        changed_dimensions = []
        for dim in DIMENSIONS:
            before = quality_a["dimensions"][dim]
            after = quality_b["dimensions"][dim]
            if before == after:
                continue
            changed_dimensions.append({
                "dimension": dim,
                "before_present": before["present"],
                "after_present": after["present"],
                "before_score": before["score"],
                "after_score": after["score"],
            })

        return {
            "video_filename": stored_filename,
            "version_a": self._summary(record_a, quality_a),
            "version_b": self._summary(record_b, quality_b),
            "comparison": {
                "identical": identical,
                "changed": not identical,
                "added_text": added_text,
                "removed_text": removed_text,
                "common_text": "".join(common_parts),
                "quality_score_delta": score_delta,
                "quality_score_change": _neutral_label(score_delta),
                "completeness_delta": completeness_delta,
                "completeness_change": _neutral_label(completeness_delta),
                "changed_dimensions": changed_dimensions,
            },
        }

    def _summary(self, record: dict, quality: dict) -> dict:
        return {
            "version": record["version"],
            "version_id": record["version_id"],
            "source": record["source"],
            "operation": record["operation"],
            "prompt": record["prompt"],
            "quality": quality,
        }
