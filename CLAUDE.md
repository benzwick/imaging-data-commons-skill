# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

This is a Claude Code skill for querying and downloading public cancer imaging data from the NCI Imaging Data Commons (IDC). The skill documentation in SKILL.md is read by Claude Code to understand how to use `idc-index` for medical imaging data access.

## Commands

```bash
# Install dependencies
uv sync

# Install with test dependencies
uv sync --extra test

# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_queries.py -v

# Run a specific test
uv run pytest tests/test_queries.py::TestBasicQueries::test_simple_select -v

# Run scripts directly
uv run python scripts/batch_download.py --collection rider_pilot --output ./data --dry-run
uv run python scripts/validate_download.py --dir ./data
```

## Architecture

```
SKILL.md              # Main skill documentation (Claude reads this when skill is invoked)
references/           # Extended documentation for complex topics (BigQuery, DICOMweb, etc.)
scripts/              # Standalone CLI utilities for batch operations
tests/                # pytest suite validating skill documentation accuracy
_reference/           # Reference implementations (gitignored, for local comparison)
```

## Reference Implementation

The `_reference/idc-claude-skill/` directory contains the official ImagingDataCommons/idc-claude-skill for comparison. Consult it when:
- Adding new features to see how the official skill handles them
- Checking for updates or new patterns in IDC skill design
- Resolving questions about best practices

### Key Files

- **SKILL.md**: The skill entry point. Contains core API patterns, code examples, and references to other documentation. This is what Claude Code reads to learn how to use IDC.
- **scripts/batch_download.py**: `BatchDownloader` class with progress tracking, resume capability, and disk space checking
- **scripts/validate_download.py**: `DicomValidator` class for DICOM integrity and CT geometry validation
- **tests/conftest.py**: pytest fixtures including `idc_client`, `sample_series_uids`, `expected_index_columns`

### IDC Data Model

The skill works with `idc-index` which provides SQL access to IDC metadata tables:
- `index`: Primary table with all DICOM series metadata
- `collections_index`: Collection-level metadata (cancer types, descriptions)
- `analysis_results_index`: AI segmentations and expert annotations
- `seg_index`: DICOM Segmentation cross-references

Access tables via `IDCClient.sql_query()` and `IDCClient.fetch_index()`.

## Testing Notes

Tests require network access to query live IDC data. The `idc_client` fixture in conftest.py creates a session-scoped client. Tests use `rider_pilot` as a small, stable collection for validation.
