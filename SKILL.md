---
name: imaging-data-commons
description: Query and download public cancer imaging data from NCI Imaging Data Commons using idc-index. Use for accessing large-scale radiology (CT, MR, PET) and pathology datasets for AI training or research. No authentication required. Query by metadata, visualize in browser, check licenses.
license: This skill is provided under the MIT License. IDC data itself has individual licensing (mostly CC-BY, some CC-NC) that must be respected when using the data.
allowed-tools:
    - Read
    - Write
    - Bash
    - WebFetch
    - Grep
    - Glob
argument-hint: "[collection_id | SQL query | 'help']"
metadata:
    skill-author: Andrey Fedorov, @fedorov
    idc-index-version: "0.11.7"
    idc-data-version: "v23"
---

# Imaging Data Commons

## Overview

Use the `idc-index` Python package to query and download public cancer imaging data from the National Cancer Institute Imaging Data Commons (IDC). No authentication required for data access.

**Primary tool:** `idc-index` ([GitHub](https://github.com/imagingdatacommons/idc-index))

**Check current data scale for the latest version:**

```python
from idc_index import IDCClient
client = IDCClient()

# get IDC data version
print(client.get_idc_version())

# Get collection count and total series
stats = client.sql_query("""
    SELECT   
        COUNT(DISTINCT collection_id) as collections,
        COUNT(DISTINCT analysis_result_id) as analysis_results,
        COUNT(DISTINCT PatientID) as patients,
        COUNT(DISTINCT StudyInstanceUID) as studies,
        COUNT(DISTINCT SeriesInstanceUID) as series,
        SUM(instanceCount) as instances,
        SUM(series_size_MB)/1000000 as size_TB
    FROM index
""")
print(stats)
```

**Core workflow:**
1. Query metadata → `client.sql_query()`
2. Download DICOM files → `client.download_from_selection()`
3. Visualize in browser → `client.get_viewer_URL(seriesInstanceUID=...)`

## When to Use This Skill

- Finding publicly available radiology (CT, MR, PET) or pathology (slide microscopy) images
- Selecting image subsets by cancer type, modality, anatomical site, or other metadata
- Downloading DICOM data from IDC
- Checking data licenses before use in research or commercial applications
- Visualizing medical images in a browser without local DICOM viewer software

## IDC Data Model

IDC adds two grouping levels above the standard DICOM hierarchy (Patient → Study → Series → Instance):

- **collection_id**: Groups patients by disease, modality, or research focus (e.g., `tcga_luad`, `nlst`). A patient belongs to exactly one collection.
- **analysis_result_id**: Identifies derived objects (segmentations, annotations, radiomics features) across one or more original collections.

Use `collection_id` to find original imaging data, may include annotations deposited along with the images; use `analysis_result_id` to find AI-generated or expert annotations.

**Key identifiers for queries:**
| Identifier | Scope | Use for |
|------------|-------|---------|
| `collection_id` | Dataset grouping | Filtering by project/study |
| `PatientID` | Patient | Grouping images by patient |
| `StudyInstanceUID` | DICOM study | Grouping of related series, visualization |
| `SeriesInstanceUID` | DICOM series | Grouping of related series, visualization |

## Index Tables

The `idc-index` package provides 8 metadata index tables accessible via SQL or pandas DataFrames.

| Table | Description |
|-------|-------------|
| `index` | Primary metadata for all current IDC data (auto-loaded) |
| `collections_index` | Collection-level metadata and descriptions |
| `analysis_results_index` | Metadata about derived datasets (annotations, segmentations) |
| `seg_index` | DICOM Segmentation metadata with source image references |
| `sm_index` | Slide microscopy (pathology) series metadata |

**Important:** Always use `client.indices_overview` to get current table schemas - this is the authoritative source for available columns.

```python
from idc_index import IDCClient
client = IDCClient()

# Query the primary index
results = client.sql_query("SELECT * FROM index WHERE Modality = 'CT' LIMIT 10")

# Fetch and query additional indices
client.fetch_index("collections_index")
collections = client.sql_query("SELECT collection_id, CancerTypes FROM collections_index")

# Get schema for any table
schema = client.indices_overview["index"]["schema"]
```

See `references/index_tables.md` for complete table documentation, join patterns, column schemas, and clinical data access.

## Data Access Options

| Method | Auth Required | Best For |
|--------|---------------|----------|
| `idc-index` | No | Key queries and downloads (recommended) |
| IDC Portal | No | Interactive exploration, manual selection, browser-based download |
| BigQuery | Yes (GCP account) | Complex queries, full DICOM metadata |
| DICOMweb proxy | No | Tool integration via DICOMweb API |

**DICOMweb access**

IDC data is available via DICOMweb interface (Google Cloud Healthcare API implementation) for integration with PACS systems and DICOMweb-compatible tools.

| Endpoint | Auth | Use Case |
|----------|------|----------|
| Public proxy | No | Testing, moderate queries, daily quota |
| Google Healthcare | Yes (GCP) | Production use, higher quotas |

See `references/dicomweb_guide.md` for endpoint URLs, code examples, supported operations, and implementation details.

## Installation and Setup

**Required (for basic access):**
```bash
pip install --upgrade idc-index
```

**Important:** New IDC data release will always trigger a new version of `idc-index`. Always use `--upgrade` flag while installing, unless an older version is needed for reproducibility.

**Tested with:** idc-index 0.11.7 (IDC data version v23)

**Optional (for data analysis):**
```bash
pip install pandas numpy pydicom
```

## Core Capabilities

### 1. Data Discovery and Exploration

Discover what imaging collections and data are available in IDC:

```python
from idc_index import IDCClient

client = IDCClient()

# Get summary statistics from primary index
query = """
SELECT
  collection_id,
  COUNT(DISTINCT PatientID) as patients,
  COUNT(DISTINCT SeriesInstanceUID) as series,
  SUM(series_size_MB) as size_mb
FROM index
GROUP BY collection_id
ORDER BY patients DESC
"""
collections_summary = client.sql_query(query)

# For richer collection metadata, use collections_index
client.fetch_index("collections_index")
collections_info = client.sql_query("""
    SELECT collection_id, CancerTypes, TumorLocations, Species, Subjects, SupportingData
    FROM collections_index
""")

# For analysis results (annotations, segmentations), use analysis_results_index
client.fetch_index("analysis_results_index")
analysis_info = client.sql_query("""
    SELECT analysis_result_id, analysis_result_title, Subjects, Collections, Modalities
    FROM analysis_results_index
""")
```

**`collections_index`** provides curated metadata per collection: cancer types, tumor locations, species, subject counts, and supporting data types — without needing to aggregate from the primary index.

**`analysis_results_index`** lists derived datasets (AI segmentations, expert annotations, radiomics features) with their source collections and modalities.

### 2. Querying Metadata with SQL

Query the IDC mini-index using SQL to find specific datasets.

**Important:** Use single quotes for SQL string literals (`'MR'`), not double quotes. Double quotes in SQL are for column/table identifiers and will cause errors like `Referenced column "MR" not found`.

**First, explore available values for filter columns:**
```python
from idc_index import IDCClient

client = IDCClient()

# Check what Modality values exist
modalities = client.sql_query("""
    SELECT DISTINCT Modality, COUNT(*) as series_count
    FROM index
    GROUP BY Modality
    ORDER BY series_count DESC
""")
print(modalities)

# Check what BodyPartExamined values exist for MR modality
body_parts = client.sql_query("""
    SELECT DISTINCT BodyPartExamined, COUNT(*) as series_count
    FROM index
    WHERE Modality = 'MR' AND BodyPartExamined IS NOT NULL
    GROUP BY BodyPartExamined
    ORDER BY series_count DESC
    LIMIT 20
""")
print(body_parts)
```

**Then query with validated filter values:**
```python
# Find breast MRI scans (use actual values from exploration above)
results = client.sql_query("""
    SELECT
      collection_id,
      PatientID,
      SeriesInstanceUID,
      Modality,
      SeriesDescription,
      license_short_name
    FROM index
    WHERE Modality = 'MR'
      AND BodyPartExamined = 'BREAST'
    LIMIT 20
""")

# Access results as pandas DataFrame
for idx, row in results.iterrows():
    print(f"Patient: {row['PatientID']}, Series: {row['SeriesInstanceUID']}")
```

**To filter by cancer type, join with `collections_index`:**
```python
client.fetch_index("collections_index")
results = client.sql_query("""
    SELECT i.collection_id, i.PatientID, i.SeriesInstanceUID, i.Modality
    FROM index i
    JOIN collections_index c ON i.collection_id = c.collection_id
    WHERE c.CancerTypes LIKE '%Breast%'
      AND i.Modality = 'MR'
    LIMIT 20
""")
```

**Available metadata fields** (use `client.indices_overview` for complete list):
- Identifiers: collection_id, PatientID, StudyInstanceUID, SeriesInstanceUID
- Imaging: Modality, BodyPartExamined, Manufacturer, ManufacturerModelName
- Clinical: PatientAge, PatientSex, StudyDate
- Descriptions: StudyDescription, SeriesDescription
- Licensing: license_short_name

**Note:** Cancer type is in `collections_index.CancerTypes`, not in the primary `index` table.

### 3. Downloading DICOM Files

Download imaging data efficiently from IDC's cloud storage:

**Download entire collection:**
```python
from idc_index import IDCClient

client = IDCClient()

# Download small collection (RIDER Pilot ~1GB)
client.download_from_selection(
    collection_id="rider_pilot",
    downloadDir="./data/rider"
)
```

**Download specific series:**
```python
# First, query for series UIDs
series_df = client.sql_query("""
    SELECT SeriesInstanceUID
    FROM index
    WHERE Modality = 'CT'
      AND BodyPartExamined = 'CHEST'
      AND collection_id = 'nlst'
    LIMIT 5
""")

# Download only those series
client.download_from_selection(
    seriesInstanceUID=list(series_df['SeriesInstanceUID'].values),
    downloadDir="./data/lung_ct"
)
```

**Custom directory structure:**

Default `dirTemplate`: `%collection_id/%PatientID/%StudyInstanceUID/%Modality_%SeriesInstanceUID`

```python
# Simplified hierarchy (omit StudyInstanceUID level)
client.download_from_selection(
    collection_id="tcga_luad",
    downloadDir="./data",
    dirTemplate="%collection_id/%PatientID/%Modality"
)
# Results in: ./data/tcga_luad/TCGA-05-4244/CT/

# Flat structure (all files in one directory)
client.download_from_selection(
    seriesInstanceUID=list(series_df['SeriesInstanceUID'].values),
    downloadDir="./data/flat",
    dirTemplate=""
)
# Results in: ./data/flat/*.dcm
```

### Command-Line Download

The `idc download` command provides command-line access to download functionality without writing Python code. Available after installing `idc-index`.

**Auto-detects input type:** manifest file path, or identifiers (collection_id, PatientID, StudyInstanceUID, SeriesInstanceUID, crdc_series_uuid).

```bash
# Download entire collection
idc download rider_pilot --download-dir ./data

# Download specific series by UID
idc download "1.3.6.1.4.1.9328.50.1.69736" --download-dir ./data

# Download multiple items (comma-separated)
idc download "tcga_luad,tcga_lusc" --download-dir ./data

# Download from manifest file (auto-detected)
idc download manifest.txt --download-dir ./data
```

**Options:**

| Option | Description |
|--------|-------------|
| `--download-dir` | Output directory (default: current directory) |
| `--dir-template` | Directory hierarchy template (default: `%collection_id/%PatientID/%StudyInstanceUID/%Modality_%SeriesInstanceUID`) |
| `--log-level` | Verbosity: debug, info, warning, error, critical |

**Manifest files:**

Manifest files contain S3 URLs (one per line) and can be:
- Exported from the IDC Portal after cohort selection
- Shared by collaborators for reproducible data access
- Generated programmatically from query results

Format (one S3 URL per line):
```
s3://idc-open-data/cb09464a-c5cc-4428-9339-d7fa87cfe837/*
s3://idc-open-data/88f3990d-bdef-49cd-9b2b-4787767240f2/*
```

**Example: Generate manifest from Python query:**

```python
from idc_index import IDCClient

client = IDCClient()

# Query for series URLs
results = client.sql_query("""
    SELECT series_aws_url
    FROM index
    WHERE collection_id = 'rider_pilot' AND Modality = 'CT'
""")

# Save as manifest file
with open('ct_manifest.txt', 'w') as f:
    for url in results['series_aws_url']:
        f.write(url + '\n')
```

Then download:
```bash
idc download ct_manifest.txt --download-dir ./ct_data
```

### 4. Visualizing IDC Images

View DICOM data in browser without downloading:

```python
from idc_index import IDCClient
import webbrowser

client = IDCClient()

# First query to get valid UIDs
results = client.sql_query("""
    SELECT SeriesInstanceUID, StudyInstanceUID
    FROM index
    WHERE collection_id = 'rider_pilot' AND Modality = 'CT'
    LIMIT 1
""")

# View single series
viewer_url = client.get_viewer_URL(seriesInstanceUID=results.iloc[0]['SeriesInstanceUID'])
webbrowser.open(viewer_url)

# View all series in a study (useful for multi-series exams like MRI protocols)
viewer_url = client.get_viewer_URL(studyInstanceUID=results.iloc[0]['StudyInstanceUID'])
webbrowser.open(viewer_url)
```

The method automatically selects OHIF v3 for radiology or SLIM for slide microscopy. Viewing by study is useful when a DICOM Study contains multiple Series (e.g., T1, T2, DWI sequences from a single MRI session).

### 5. Understanding and Checking Licenses

Check data licensing before use (critical for commercial applications):

```python
from idc_index import IDCClient

client = IDCClient()

# Check licenses for all collections
query = """
SELECT DISTINCT
  collection_id,
  license_short_name,
  COUNT(DISTINCT SeriesInstanceUID) as series_count
FROM index
GROUP BY collection_id, license_short_name
ORDER BY collection_id
"""

licenses = client.sql_query(query)
print(licenses)
```

**License types in IDC:**
- **CC BY 4.0** / **CC BY 3.0** (~97% of data) - Allows commercial use with attribution
- **CC BY-NC 4.0** / **CC BY-NC 3.0** (~3% of data) - Non-commercial use only
- **Custom licenses** (rare) - Some collections have specific terms (e.g., NLM Terms and Conditions)

**Important:** Always check the license before using IDC data in publications or commercial applications. Each DICOM file is tagged with its specific license in metadata.

### Generating Citations for Attribution

The `source_DOI` column contains DOIs linking to publications describing how the data was generated. To satisfy attribution requirements, use `citations_from_selection()` to generate properly formatted citations:

```python
from idc_index import IDCClient

client = IDCClient()

# Get citations for a collection (APA format by default)
citations = client.citations_from_selection(collection_id="rider_pilot")
for citation in citations:
    print(citation)

# Get citations for specific series
results = client.sql_query("""
    SELECT SeriesInstanceUID FROM index
    WHERE collection_id = 'tcga_luad' LIMIT 5
""")
citations = client.citations_from_selection(
    seriesInstanceUID=list(results['SeriesInstanceUID'].values)
)

# Alternative format: BibTeX (for LaTeX documents)
bibtex_citations = client.citations_from_selection(
    collection_id="tcga_luad",
    citation_format=IDCClient.CITATION_FORMAT_BIBTEX
)
```

**Parameters:**
- `collection_id`: Filter by collection(s)
- `patientId`: Filter by patient ID(s)
- `studyInstanceUID`: Filter by study UID(s)
- `seriesInstanceUID`: Filter by series UID(s)
- `citation_format`: Use `IDCClient.CITATION_FORMAT_*` constants:
  - `CITATION_FORMAT_APA` (default) - APA style
  - `CITATION_FORMAT_BIBTEX` - BibTeX for LaTeX
  - `CITATION_FORMAT_JSON` - CSL JSON
  - `CITATION_FORMAT_TURTLE` - RDF Turtle

**Best practice:** When publishing results using IDC data, include the generated citations to properly attribute the data sources and satisfy license requirements.

### 6. Batch Processing and Filtering

Process large datasets efficiently with filtering:

```python
from idc_index import IDCClient
import pandas as pd

client = IDCClient()

# Find chest CT scans from GE scanners
query = """
SELECT
  SeriesInstanceUID,
  PatientID,
  collection_id,
  ManufacturerModelName
FROM index
WHERE Modality = 'CT'
  AND BodyPartExamined = 'CHEST'
  AND Manufacturer = 'GE MEDICAL SYSTEMS'
  AND license_short_name = 'CC BY 4.0'
LIMIT 100
"""

results = client.sql_query(query)

# Save manifest for later
results.to_csv('lung_ct_manifest.csv', index=False)

# Download in batches to avoid timeout
batch_size = 10
for i in range(0, len(results), batch_size):
    batch = results.iloc[i:i+batch_size]
    client.download_from_selection(
        seriesInstanceUID=list(batch['SeriesInstanceUID'].values),
        downloadDir=f"./data/batch_{i//batch_size}"
    )
```

### 7. Advanced Queries with BigQuery

For queries requiring full DICOM metadata, complex JOINs, or clinical data tables, use Google BigQuery. Requires GCP account with billing enabled.

**Quick reference:**
- Dataset: `bigquery-public-data.idc_current.*`
- Main table: `dicom_all` (combined metadata)
- Full metadata: `dicom_metadata` (all DICOM tags)

See `references/bigquery_guide.md` for setup, table schemas, query patterns, and cost optimization.

### 8. Tool Selection Guide

| Task | Tool | Reference |
|------|------|-----------|
| Programmatic queries & downloads | `idc-index` | This document |
| Interactive exploration | IDC Portal | https://portal.imaging.datacommons.cancer.gov/ |
| Complex metadata queries | BigQuery | `references/bigquery_guide.md` |
| 3D visualization & analysis | SlicerIDCBrowser | https://github.com/ImagingDataCommons/SlicerIDCBrowser |

**Default choice:** Use `idc-index` for most tasks (no auth, easy API, batch downloads).

### 9. Integration with Analysis Pipelines

After downloading DICOM data, integrate with common analysis tools:

| Tool | Use Case |
|------|----------|
| pydicom | Read DICOM files, extract metadata and pixel arrays |
| SimpleITK | Build 3D volumes, convert to NIfTI, apply filters |
| MONAI | Deep learning preprocessing and training |
| radiomics | Feature extraction from images and segmentations |
| OpenSlide/histolab | Pathology whole slide image processing |

See `references/analysis_integration.md` for complete code examples.

## Common Use Cases

| Use Case | Description |
|----------|-------------|
| Deep Learning Dataset | Query and download lung CT scans with license filtering |
| Quality Study | Compare images across scanner manufacturers |
| Preview Without Download | Visualize series in browser before committing |
| Commercial Use | License-aware download (CC BY only) |
| Multi-Modal Dataset | Find patients with CT + PET for fusion analysis |
| Segmentation Pairs | Download AI segmentations with source images |
| Pathology Setup | Download high-resolution whole slide images |
| Reproducible Research | Create versioned datasets with full provenance |

See `references/use_cases.md` for complete code examples for each use case.

## Best Practices

- **Check licenses before use** - Always query the `license_short_name` field and respect licensing terms (CC BY vs CC BY-NC)
- **Generate citations for attribution** - Use `citations_from_selection()` to get properly formatted citations from `source_DOI` values; include these in publications
- **Start with small queries** - Use `LIMIT` clause when exploring to avoid long downloads and understand data structure
- **Use mini-index for simple queries** - Only use BigQuery when you need comprehensive metadata or complex JOINs
- **Organize downloads with dirTemplate** - Use meaningful directory structures like `%collection_id/%PatientID/%Modality`
- **Cache query results** - Save DataFrames to CSV files to avoid re-querying and ensure reproducibility
- **Estimate size first** - Check collection size before downloading - some collection sizes are in terabytes! See `references/memory_management.md` for batch download strategies
- **Save manifests** - Always save query results with Series UIDs for reproducibility and data provenance
- **Read documentation** - IDC data structure and metadata fields are documented at https://learn.canceridc.dev/
- **Use IDC forum** - Search for questons/answers and ask your questions to the IDC maintainers and users at https://discourse.canceridc.dev/

## Troubleshooting

**Issue: `ModuleNotFoundError: No module named 'idc_index'`**
- **Cause:** idc-index package not installed
- **Solution:** Install with `pip install --upgrade idc-index`

**Issue: Download fails with connection timeout**
- **Cause:** Network instability or large download size
- **Solution:**
  - Download smaller batches (e.g., 10-20 series at a time)
  - Check network connection
  - Use `dirTemplate` to organize downloads by batch
  - Implement retry logic with delays

**Issue: `BigQuery quota exceeded` or billing errors**
- **Cause:** BigQuery requires billing-enabled GCP project
- **Solution:** Use idc-index mini-index for simple queries (no billing required), or see `references/bigquery_guide.md` for cost optimization tips

**Issue: Series UID not found or no data returned**
- **Cause:** Typo in UID, data not in current IDC version, or wrong field name
- **Solution:**
  - Check if data is in current IDC version (some old data may be deprecated)
  - Use `LIMIT 5` to test query first
  - Check field names against metadata schema documentation

**Issue: Downloaded DICOM files won't open**
- **Cause:** Corrupted download or incompatible viewer
- **Solution:**
  - Check DICOM object type (Modality and SOPClassUID attributes) - some object types require specialized tools
  - Verify file integrity (check file sizes)
  - Use pydicom to validate: `pydicom.dcmread(file, force=True)`
  - Try different DICOM viewer (3D Slicer, Horos, RadiAnt, QuPath)
  - Re-download the series
  - See `references/data_validation.md` for comprehensive validation scripts

## Common SQL Query Patterns

Quick reference for common query patterns:

```python
from idc_index import IDCClient
client = IDCClient()

# Discover available values
client.sql_query("SELECT DISTINCT Modality FROM index")

# Find segmentations
client.sql_query("SELECT * FROM index WHERE Modality = 'SEG' LIMIT 10")

# Estimate download size
client.sql_query("""
    SELECT SUM(series_size_MB) as total_mb, COUNT(*) as series
    FROM index WHERE collection_id = 'nlst' AND Modality = 'CT'
""")

# Filter by license (commercial use)
client.sql_query("""
    SELECT * FROM index
    WHERE license_short_name LIKE 'CC BY%' AND license_short_name NOT LIKE '%NC%'
    LIMIT 10
""")
```

See `references/sql_patterns.md` for complete query patterns including:
- Annotations and segmentation queries
- Slide microscopy queries
- Clinical data linkage
- Multi-modality studies
- Collection statistics

## Related Skills

The following skills complement IDC workflows for downstream analysis and visualization:

### DICOM Processing
- **pydicom** - Read, write, and manipulate downloaded DICOM files. Use for extracting pixel data, reading metadata, anonymization, and format conversion. Essential for working with IDC radiology data (CT, MR, PET).

### Pathology and Slide Microscopy
- **histolab** - Lightweight tile extraction and preprocessing for whole slide images. Use for basic slide processing, tissue detection, and dataset preparation from IDC slide microscopy data.
- **pathml** - Full-featured computational pathology toolkit. Use for advanced WSI analysis including multiplexed imaging, nucleus segmentation, and ML model training on pathology data downloaded from IDC.

### Metadata Visualization
- **matplotlib** - Low-level plotting for full customization. Use for creating static figures summarizing IDC query results (bar charts of modalities, histograms of series counts, etc.).
- **seaborn** - Statistical visualization with pandas integration. Use for quick exploration of IDC metadata distributions, relationships between variables, and categorical comparisons with attractive defaults.
- **plotly** - Interactive visualization. Use when you need hover info, zoom, and pan for exploring IDC metadata, or for creating web-embeddable dashboards of collection statistics.

### Data Exploration
- **exploratory-data-analysis** - Comprehensive EDA on scientific data files. Use after downloading IDC data to understand file structure, quality, and characteristics before analysis.

## Resources

### Schema Reference (Primary Source)

**Always use `client.indices_overview` for current column schemas.** This ensures accuracy with the installed idc-index version:

```python
# Get all column names and types for any table
schema = client.indices_overview["index"]["schema"]
columns = [(c['name'], c['type'], c.get('description', '')) for c in schema['columns']]
```

### Reference Documentation

| File | Description |
|------|-------------|
| `references/index_tables.md` | Complete index table documentation, join patterns, column schemas |
| `references/sql_patterns.md` | Common SQL query patterns and examples |
| `references/use_cases.md` | Detailed code examples for common workflows |
| `references/analysis_integration.md` | Integration with pydicom, SimpleITK, MONAI, etc. |
| `references/memory_management.md` | Large dataset handling, batch downloads, disk management |
| `references/data_validation.md` | DICOM integrity checking, series completeness verification |
| `references/bigquery_guide.md` | Advanced BigQuery usage for complex metadata queries |
| `references/dicomweb_guide.md` | DICOMweb endpoint URLs and API integration |

**External:** [indices_reference](https://idc-index.readthedocs.io/en/latest/indices_reference.html) - Official idc-index documentation

### Scripts

| Script | Description |
|--------|-------------|
| `scripts/batch_download.py` | Batch download with progress tracking, resume capability, disk space checking |
| `scripts/validate_download.py` | DICOM validation, completeness checking, geometry verification |

Usage:
```bash
# Download from SQL query
python scripts/batch_download.py --query "SELECT SeriesInstanceUID FROM index WHERE collection_id='nlst' LIMIT 100" --output ./data

# Download from manifest file
python scripts/batch_download.py --manifest series.csv --output ./data

# Download entire collection
python scripts/batch_download.py --collection rider_pilot --output ./data

# Dry run to see what would be downloaded
python scripts/batch_download.py --collection rider_pilot --output ./data --dry-run

# Validate downloaded data
python scripts/validate_download.py --dir ./data

# Validate against manifest with geometry checking
python scripts/validate_download.py --dir ./data --manifest manifest.csv --check-geometry --output report.json

# Run tests
pytest tests/ -v
```

### Tests

The `tests/` directory contains pytest tests for validating skill functionality:

| Test File | Description |
|-----------|-------------|
| `tests/test_queries.py` | IDC client, SQL queries, index schema, viewer URLs |
| `tests/test_validation.py` | Validation scripts, progress tracking, disk space checks |

Run tests with:
```bash
pip install pytest
pytest tests/ -v
```

### External Links

- **IDC Portal**: https://portal.imaging.datacommons.cancer.gov/explore/
- **Documentation**: https://learn.canceridc.dev/
- **Tutorials**: https://github.com/ImagingDataCommons/IDC-Tutorials
- **User Forum**: https://discourse.canceridc.dev/
- **idc-index GitHub**: https://github.com/ImagingDataCommons/idc-index
- **Citation**: Fedorov, A., et al. "National Cancer Institute Imaging Data Commons: Toward Transparency, Reproducibility, and Scalability in Imaging Artificial Intelligence." RadioGraphics 43.12 (2023). https://doi.org/10.1148/rg.230180
