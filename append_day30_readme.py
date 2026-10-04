"""Temp: append the Day 30 README section. Deleted after use."""
README = "README.md"

SECTION = """
## Day 30 - Prompt Readiness Report Export

Day 30 adds **Prompt Readiness Report Export**: deterministic, read-only serialization of the existing Day 29 Prompt Readiness Report into downloadable JSON, Markdown, or plain text. The export represents the Day 29 report exactly - it never alters report data, never rebuilds any readiness calculation, and never persists anything to disk. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Serialize one Day 29 report (metadata, per-version snapshots, timeline, aggregate summary) in three human- and machine-readable formats
- Reuse `PromptReadinessReportService` unchanged: no duplicate Day 24 readiness, Day 25 aggregation, Day 26 transitions, Day 27 timeline, or Day 28 snapshot logic exists in the export layer
- Keep output fully deterministic: the same stored selection always produces byte-identical content and the same filename

### Supported Formats

| Format | Media type | Filename |
|---|---|---|
| `json` | `application/json` | `visionprompt_readiness_report.json` |
| `markdown` | `text/markdown` | `visionprompt_readiness_report.md` |
| `txt` | `text/plain` | `visionprompt_readiness_report.txt` |

- Any other format value (including empty or wrong-case like `JSON`) -> HTTP 422 with Day 19's exact message: `Invalid format. Must be one of: json, markdown, txt`
- All content is UTF-8; responses carry `Content-Disposition: attachment; filename=...` and are streamed directly from memory (no file is written anywhere)

### JSON Structure

JSON serializes the complete Day 29 report - all five top-level keys (`video_filename`, `versions_analyzed`, `report`, `timeline`, `summary`) and every nested field, with no fields omitted or invented:

```json
{
  "video_filename": "...",
  "versions_analyzed": [1, 3, 5],
  "report": {"type": "...", "version_count": 3, "first_version": 1, "last_version": 5, "selection_order": [1, 3, 5], "snapshots": ["..."]},
  "timeline": {"steps": ["..."], "changed_dimensions": ..., "unchanged_dimensions": ..., "required_changes": ..., "supporting_changes": ..., "transition_summary": {"...": 0}, "required_coverage_delta": -86},
  "summary": {"versions_analyzed": ..., "ready_count": ..., "needs_attention_count": ..., "required": {"...": ...}, "supporting": {"...": ...}, "dimension_summary": ["..."], "organization": {"favorite_count": ..., "tag_counts": {"...": ...}}}
}
```

- Deterministic formatting: UTF-8, `indent=2`, stable key order (report dict order), trailing newline, no random values
- `json.loads(json_export) == GET .../readiness/report` for every selection (semantically and structurally equivalent)

### Markdown Structure

Human-readable `# Prompt Readiness Report` document with four `##` sections, containing all report information as factual data only:

- `## Report` - video filename, type, versions analyzed, version count, first/last version, selection order
- `## Version Readiness` - one `### Version N` block per snapshot: source, operation, created at, favorite, tags, status, required coverage, `#### Required Dimensions` table (7 rows), `#### Supporting Dimensions` table (2 rows), missing/weak dimension lists
- `## Timeline` - one `### Step i: Version A -> Version B` block per consecutive pair (versions A/B metadata, changed/unchanged counts, required/supporting changes, per-dimension `#### Step Dimensions` table, `#### Transitions`, `#### Transition Summary`), plus `### Timeline Summary` (changed/unchanged totals, required/supporting change totals, transition summary, required coverage delta)
- `## Summary` - `### Readiness`, `### Required`, `### Supporting` counts, `### Dimension Summary` table (9 rows in Day 21 order), `### Organization` (favorite count, tag counts alphabetically)

No evaluative commentary is ever written - only the report's own values.

### TXT Structure

Plain-text equivalent with `PROMPT READINESS REPORT` title and underlined `REPORT`, `VERSION READINESS`, `TIMELINE`, `SUMMARY` sections. Each version appears as a `VERSION N` block with `REQUIRED DIMENSIONS` / `SUPPORTING DIMENSIONS` lines (`dimension: status (score)`), timeline steps use ASCII `->` arrows with `STEP DIMENSIONS`, `TRANSITIONS`, `TRANSITION SUMMARY`, `TIMELINE SUMMARY` blocks, and the summary carries `DIMENSION SUMMARY` / `ORGANIZATION` blocks. Same factual information as Markdown; no prompt text, no internal objects, no absolute paths, no secrets.

### Selection Semantics

Byte-identical to Day 25/27/28/29 (delegated, never reimplemented):

- No `versions` query: every live version, ascending version order
- `?versions=1,3,5`: only those versions, in the requested order - never sorted, never substituted
- Repeated `?versions=1&versions=3` equals `?versions=1,3`; whitespace around entries tolerated
- Empty, malformed, non-integer, non-positive, or duplicate entries -> 422; missing or deleted version -> 404 (Day 16's exact message); nonexistent video -> 404; invalid extension -> 400; path traversal -> 404
- A video with no saved versions exports an empty report with HTTP 200 (zero counts, `null` coverage/delta in JSON, `No saved versions.` in Markdown/TXT)

### Filenames and Media Types

- Stable filenames only: `visionprompt_readiness_report.json` / `.md` / `.txt` - never derived from user input, never contain random IDs or version lists
- Media types as listed in the table above; responses are `Content-Disposition: attachment` downloads rendered in memory

### Determinism

- Repeated export calls (any format, any selection) produce byte-identical content, `Content-Type`, and `Content-Disposition`
- No generated timestamps, UUIDs, or random values: the only time values are each snapshot's stored Day 16 `created_at`

### Read-Only Behavior

- Export never modifies prompt history, favorites, tags, quality results, Day 19 prompt exports, or Day 20 packages; never creates, deletes, or renumbers versions
- No filesystem persistence: nothing is written to storage (or anywhere else); no second store, no cache, no saved export results
- The Day 29 report service is called read-only; its output is rendered to a string and returned

### Limitations

- Serialization only: it does not recompute, reinterpret, or extend readiness data, and never evaluates which version is better/worse or recommends a version
- Markdown/TXT present every report value as neutral text; they carry no analysis beyond what Day 29 already reports
- Exports reflect only the selected versions and are identical in content to the report endpoint for the same selection

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/readiness/report/export?format=json[&versions=1,3,5]
```

- Static route registered before numeric `{version}` routes; distinct from Day 19's `.../{version}/export` and Day 29's `.../readiness/report`
- Query: `format` required (`json` | `markdown` | `txt`), `versions` optional (same rules as Day 29)
- 200 with rendered content + media type + filename; 422 invalid format or versions; 404 missing/deleted version or unknown video; 400 invalid extension

### Tests

- `tests/test_prompt_readiness_export_service.py` - 450 service tests (wiring/single-store, envelope, JSON structure and Day 29 equivalence, Markdown structure and leaf completeness, TXT structure and leaf completeness, empty history, single version, selection, validation messages, determinism, read-only integrity, no-ranking/leak scans, source contract)
- `tests/test_prompt_readiness_export_api.py` - 208 API tests (200s, media types, Content-Disposition, semantic equivalence with Day 29, selections, repeated/whitespace params, empty/single, full validation matrix, determinism, read-only/no-file checks, route collision, Day 16-29 regression, leak scans)

### Files Created/Modified

- `backend/app/services/prompt_readiness_export_service.py` - `PromptReadinessExportService`
- `backend/app/api/videos.py` - Added import, service instance, and static `GET .../prompt/history/readiness/report/export` route (registered before numeric `{version}` routes)
- `tests/test_prompt_readiness_export_service.py` - 450 service tests
- `tests/test_prompt_readiness_export_api.py` - 208 API tests
- `backend/day30_e2e.py` - manual end-to-end verification script
"""

with open(README, "r", encoding="utf-8") as f:
    content = f.read()

assert "## Day 30 - Prompt Readiness Report Export" not in content
if not content.endswith("\n"):
    content += "\n"
content += SECTION
with open(README, "w", encoding="utf-8") as f:
    f.write(content)
print("Day 30 section appended")
