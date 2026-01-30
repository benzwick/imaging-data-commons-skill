# Sync Report

Generated: 2026-01-30
Reference: ImagingDataCommons/idc-claude-skill @ 15d63a4

## Summary

- Total improvements: 9
- By priority: High (1), Medium (5), Low (3)
- By source: Official sync (4), Local enhancement (5)

## Improvements

### 1. Add USAGE.md Documentation

- **Status**: [ ] Pending
- **File**: `USAGE.md` (new file)
- **Priority**: Medium
- **Difficulty**: Easy
- **Type**: New Content
- **Source**: Official sync

**Description:**
The official skill includes a comprehensive USAGE.md file that documents how to install and use the skill across different environments (Claude.ai web, Claude Desktop, Claude Code, Claude API). This is valuable documentation for users who want to integrate the skill.

**Reference content:**
See `_reference/idc-claude-skill/USAGE.md` - covers:
- Installation from standalone or collection repos
- Claude.ai web interface usage (ZIP upload, individual files)
- Claude Desktop setup (file attachment, project context)
- Claude Code setup (npx install, personal skill, project skill, session import)
- Claude API setup with example code
- Example workflows and troubleshooting

**Action:**
Copy `_reference/idc-claude-skill/USAGE.md` to the repo root. Review for any local-specific changes needed.

---

### 2. Remove Duplicate Frontmatter Fields

- **Status**: [ ] Pending
- **File**: `SKILL.md`
- **Priority**: Low
- **Difficulty**: Easy
- **Type**: Fix
- **Source**: Official sync

**Description:**
Local SKILL.md includes extra frontmatter fields not in official: `allowed-tools`, `argument-hint`. The official uses a simpler frontmatter. These extra fields may not be recognized by skill frameworks.

**Local content:**
```yaml
allowed-tools: Read Write Bash WebFetch Grep Glob
argument-hint: "[collection_id | SQL query | 'help']"
```

**Reference content:**
Official frontmatter only has: `name`, `description`, `license`, `metadata` (with `skill-author` only).

**Action:**
Remove `allowed-tools` and `argument-hint` lines from SKILL.md frontmatter to match official pattern.

---

### 3. Update Frontmatter Metadata to Match Official

- **Status**: [ ] Pending
- **File**: `SKILL.md`
- **Priority**: Low
- **Difficulty**: Easy
- **Type**: Align
- **Source**: Official sync

**Description:**
Local skill includes `idc-index-version` and `idc-data-version` in metadata which the official doesn't include in frontmatter. Version info is documented inline instead ("Tested with: idc-index 0.11.7").

**Local content:**
```yaml
metadata:
    skill-author: Andrey Fedorov, @fedorov
    idc-index-version: "0.11.7"
    idc-data-version: "v23"
```

**Reference content:**
```yaml
metadata:
    skill-author: Andrey Fedorov, @fedorov
```

**Action:**
Remove `idc-index-version` and `idc-data-version` from metadata to match official pattern. Version info is already documented inline.

---

### 4. Update Index Tables Section to Match Official

- **Status**: [ ] Pending
- **File**: `SKILL.md`
- **Priority**: High
- **Difficulty**: Medium
- **Type**: Update
- **Source**: Official sync

**Description:**
The official SKILL.md has a significantly expanded Index Tables section with:
- Better table format showing row granularity and load status
- Complete joining tables documentation with key columns
- Detailed seg_index examples showing how to join segmentations to source images
- More comprehensive schema discovery examples
- Key columns table with DICOM indicator
- Clinical data access section

The local version has a simpler table that references `references/index_tables.md` for details.

**Reference content:**
The official includes inline documentation for:
- 8 tables (index, prior_versions_index, collections_index, analysis_results_index, clinical_index, sm_index, sm_instance_index, seg_index)
- Join column reference table
- Example SQL joins for seg_index → index
- Schema discovery with `indices_overview`
- Key columns with DICOM attribute flags
- Clinical data access via `fetch_index("clinical_index")` and `get_clinical_table()`

**Action:**
Update the Index Tables section in SKILL.md to match the official's expanded inline documentation. Consider whether `references/index_tables.md` is still needed or can be removed/simplified.

---

### 5. Update Common SQL Query Patterns Section

- **Status**: [ ] Pending
- **File**: `SKILL.md`
- **Priority**: Medium
- **Difficulty**: Medium
- **Type**: Update
- **Source**: Official sync

**Description:**
The official SKILL.md has a more comprehensive "Common SQL Query Patterns" section with detailed seg_index examples, notes about annotations not always being in analysis_results collections, and improved organization.

Key additions in official:
- Note: "Not all image-derived objects belong to analysis result collections"
- Better seg_index join examples
- Query for TotalSegmentator results with collection context
- Slide microscopy query joining sm_index with index

**Action:**
Update the Common SQL Query Patterns section to include the official's improved examples and notes. The local version references `references/sql_patterns.md` which may have some of this content - consider consolidating.

---

### 6. Add Analysis Pipeline Integration Examples

- **Status**: [ ] Pending
- **File**: `SKILL.md`
- **Priority**: Medium
- **Difficulty**: Easy
- **Type**: Update
- **Source**: Official sync

**Description:**
The official SKILL.md includes inline pydicom, SimpleITK integration examples in section "9. Integration with Analysis Pipelines". The local version references `references/analysis_integration.md` instead.

**Reference content:**
```python
# Read downloaded DICOM files
import pydicom
ds = pydicom.dcmread(dicom_files[0])

# Build 3D volume from CT series
def load_ct_series(series_path):
    ...

# Integrate with SimpleITK
import SimpleITK as sitk
reader = sitk.ImageSeriesReader()
```

**Action:**
Add the official's inline pydicom and SimpleITK examples to SKILL.md. The `references/analysis_integration.md` can remain for more comprehensive examples.

---

### 7. Add Expanded Use Cases Section

- **Status**: [ ] Pending
- **File**: `SKILL.md`
- **Priority**: Medium
- **Difficulty**: Medium
- **Type**: Update
- **Source**: Official sync

**Description:**
The official SKILL.md includes 4 detailed use case examples inline (Lung CT for Deep Learning, Brain MRI by Manufacturer, Visualize Without Downloading, License-Aware Download). The local version has a summary table that references `references/use_cases.md`.

**Reference content:**
Full code examples for:
- Use Case 1: Find and Download Lung CT Scans for Deep Learning
- Use Case 2: Query Brain MRI by Manufacturer for Quality Study
- Use Case 3: Visualize Series Without Downloading
- Use Case 4: License-Aware Batch Download for Commercial Use

**Action:**
Add the official's detailed use case code examples to SKILL.md. The local `references/use_cases.md` can be reviewed for additional content or consolidation.

---

### 8. Fix BigQuery Segmentations Query Column Name

- **Status**: [ ] Pending
- **File**: `references/bigquery_guide.md`
- **Priority**: Medium
- **Difficulty**: Easy
- **Type**: Fix
- **Source**: Official sync

**Description:**
The local BigQuery guide has a different column name in the segmentations join query. Local uses `ReferencedSeriesInstanceUID` while official uses `segmented_SeriesInstanceUID`. Also local has `SegmentNumber` but official has `SegmentedPropertyType`.

**Local content (line 160-171):**
```sql
SELECT
  src.collection_id,
  seg.SeriesInstanceUID as seg_series,
  seg.SegmentNumber,
  src.SeriesInstanceUID as source_series,
  src.Modality as source_modality
FROM `bigquery-public-data.idc_current.segmentations` seg
JOIN `bigquery-public-data.idc_current.dicom_all` src
  ON seg.ReferencedSeriesInstanceUID = src.SeriesInstanceUID
WHERE src.collection_id = 'qin_prostate_repeatability'
```

**Reference content:**
```sql
SELECT
  src.collection_id,
  seg.SeriesInstanceUID as seg_series,
  seg.SegmentedPropertyType,
  src.SeriesInstanceUID as source_series,
  src.Modality as source_modality
FROM `bigquery-public-data.idc_current.segmentations` seg
JOIN `bigquery-public-data.idc_current.dicom_all` src
  ON seg.segmented_SeriesInstanceUID = src.SeriesInstanceUID
```

**Action:**
Update the BigQuery guide segmentations query to use `segmented_SeriesInstanceUID` (consistent with seg_index in idc-index) and `SegmentedPropertyType`. Add the schema checking note that appears in local but not official.

---

### 9. Review Local-Only Reference Files for Simplification

- **Status**: [ ] Pending
- **File**: Multiple (`references/index_tables.md`, `references/sql_patterns.md`, `references/use_cases.md`, `references/analysis_integration.md`, `references/memory_management.md`, `references/data_validation.md`)
- **Priority**: Low
- **Difficulty**: Hard
- **Type**: Simplify
- **Source**: Local enhancement

**Description:**
The local skill has 6 reference files that don't exist in the official skill. After syncing the SKILL.md improvements above, review whether these files:
- Contain content now duplicated in SKILL.md (can be removed)
- Contain unique valuable content (should be kept)
- Can be simplified to complement rather than duplicate the main skill

Files to review:
- `references/index_tables.md` - May overlap with expanded Index Tables section
- `references/sql_patterns.md` - May overlap with expanded SQL Patterns section
- `references/use_cases.md` - May overlap with expanded Use Cases section
- `references/analysis_integration.md` - May overlap with Integration section
- `references/memory_management.md` - Unique batch download strategies
- `references/data_validation.md` - Unique DICOM validation content

**Action:**
After applying improvements 4-7, review each local-only reference file:
1. Remove content that's now in SKILL.md
2. Keep unique advanced content
3. Update cross-references in SKILL.md as needed

---

## Files Comparison Summary

| File | Status | Notes |
|------|--------|-------|
| `SKILL.md` | Needs updates | Official has expanded Index Tables, SQL Patterns, Use Cases, Integration sections |
| `USAGE.md` | Missing | Official has comprehensive usage documentation |
| `references/bigquery_guide.md` | Minor fix | Column name in segmentations query |
| `references/dicomweb_guide.md` | Identical | No changes needed |
| `references/index_tables.md` | Local only | Review after SKILL.md sync |
| `references/sql_patterns.md` | Local only | Review after SKILL.md sync |
| `references/use_cases.md` | Local only | Review after SKILL.md sync |
| `references/analysis_integration.md` | Local only | Review after SKILL.md sync |
| `references/memory_management.md` | Local only | Unique content, likely keep |
| `references/data_validation.md` | Local only | Unique content, likely keep |
