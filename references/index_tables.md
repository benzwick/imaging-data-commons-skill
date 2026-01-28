# Index Tables Reference

The `idc-index` package provides multiple metadata index tables, accessible via SQL or as pandas DataFrames.

**Important:** Use `client.indices_overview` to get current table descriptions and column schemas. This is the authoritative source for available columns and their types - always query it when writing SQL or exploring data structure.

## Available Tables

| Table | Row Granularity | Loaded | Description |
|-------|-----------------|--------|-------------|
| `index` | 1 row = 1 DICOM series | Auto | Primary metadata for all current IDC data |
| `prior_versions_index` | 1 row = 1 DICOM series | Auto | Series from previous IDC releases; for downloading deprecated data |
| `collections_index` | 1 row = 1 collection | fetch_index() | Collection-level metadata and descriptions |
| `analysis_results_index` | 1 row = 1 analysis result collection | fetch_index() | Metadata about derived datasets (annotations, segmentations) |
| `clinical_index` | 1 row = 1 clinical data column | fetch_index() | Dictionary mapping clinical table columns to collections |
| `sm_index` | 1 row = 1 slide microscopy series | fetch_index() | Slide Microscopy (pathology) series metadata |
| `sm_instance_index` | 1 row = 1 slide microscopy instance | fetch_index() | Instance-level (SOPInstanceUID) metadata for slide microscopy |
| `seg_index` | 1 row = 1 DICOM Segmentation series | fetch_index() | Segmentation metadata: algorithm, segment count, reference to source image series |

**Auto** = loaded automatically when `IDCClient()` is instantiated
**fetch_index()** = requires `client.fetch_index("table_name")` to load

## Joining Tables

**Key columns are not explicitly labeled, the following is a subset that can be used in joins.**

| Join Column | Tables | Use Case |
|-------------|--------|----------|
| `collection_id` | index, prior_versions_index, collections_index, clinical_index | Link series to collection metadata or clinical data |
| `SeriesInstanceUID` | index, prior_versions_index, sm_index, sm_instance_index | Link series across tables; connect to slide microscopy details |
| `StudyInstanceUID` | index, prior_versions_index | Link studies across current and historical data |
| `PatientID` | index, prior_versions_index | Link patients across current and historical data |
| `analysis_result_id` | index, analysis_results_index | Link series to analysis result metadata (annotations, segmentations) |
| `source_DOI` | index, analysis_results_index | Link by publication DOI |
| `crdc_series_uuid` | index, prior_versions_index | Link by CRDC unique identifier |
| `Modality` | index, prior_versions_index | Filter by imaging modality |
| `SeriesInstanceUID` | index, seg_index | Link segmentation series to its index metadata |
| `segmented_SeriesInstanceUID` | seg_index -> index | Link segmentation to its source image series (join seg_index.segmented_SeriesInstanceUID = index.SeriesInstanceUID) |

**Note:** `Subjects`, `Updated`, and `Description` appear in multiple tables but have different meanings (counts vs identifiers, different update contexts).

## Example Joins

```python
from idc_index import IDCClient
client = IDCClient()

# Join index with collections_index to get cancer types
client.fetch_index("collections_index")
result = client.sql_query("""
    SELECT i.SeriesInstanceUID, i.Modality, c.CancerTypes, c.TumorLocations
    FROM index i
    JOIN collections_index c ON i.collection_id = c.collection_id
    WHERE i.Modality = 'MR'
    LIMIT 10
""")

# Join index with sm_index for slide microscopy details
client.fetch_index("sm_index")
result = client.sql_query("""
    SELECT i.collection_id, i.PatientID, s.ObjectiveLensPower, s.min_PixelSpacing_2sf
    FROM index i
    JOIN sm_index s ON i.SeriesInstanceUID = s.SeriesInstanceUID
    LIMIT 10
""")

# Join seg_index with index to find segmentations and their source images
client.fetch_index("seg_index")
result = client.sql_query("""
    SELECT
        s.SeriesInstanceUID as seg_series,
        s.AlgorithmName,
        s.total_segments,
        src.collection_id,
        src.Modality as source_modality,
        src.BodyPartExamined
    FROM seg_index s
    JOIN index src ON s.segmented_SeriesInstanceUID = src.SeriesInstanceUID
    WHERE s.AlgorithmType = 'AUTOMATIC'
    LIMIT 10
""")
```

## Accessing Index Tables

### Via SQL (recommended for filtering/aggregation)

```python
from idc_index import IDCClient
client = IDCClient()

# Query the primary index (always available)
results = client.sql_query("SELECT * FROM index WHERE Modality = 'CT' LIMIT 10")

# Fetch and query additional indices
client.fetch_index("collections_index")
collections = client.sql_query("SELECT collection_id, CancerTypes, TumorLocations FROM collections_index")

client.fetch_index("analysis_results_index")
analysis = client.sql_query("SELECT * FROM analysis_results_index LIMIT 5")
```

### As pandas DataFrames (direct access)

```python
# Primary index (always available after client initialization)
df = client.index

# Fetch and access on-demand indices
client.fetch_index("sm_index")
sm_df = client.sm_index
```

## Discovering Table Schemas

The `indices_overview` dictionary contains complete schema information for all tables. **Always consult this when writing queries or exploring data structure.**

**DICOM attribute mapping:** Many columns are populated directly from DICOM attributes in the source files. The column description in the schema indicates when a column corresponds to a DICOM attribute (e.g., "DICOM Modality attribute" or references a DICOM tag). This allows leveraging DICOM knowledge when querying - standard DICOM attribute names like `PatientID`, `StudyInstanceUID`, `Modality`, `BodyPartExamined` work as expected.

```python
from idc_index import IDCClient
client = IDCClient()

# List all available indices with descriptions
for name, info in client.indices_overview.items():
    print(f"\n{name}:")
    print(f"  Installed: {info['installed']}")
    print(f"  Description: {info['description']}")

# Get complete schema for a specific index (columns, types, descriptions)
schema = client.indices_overview["index"]["schema"]
print(f"\nTable: {schema['table_description']}")
print("\nColumns:")
for col in schema['columns']:
    desc = col.get('description', 'No description')
    # Description indicates if column is from DICOM attribute
    print(f"  {col['name']} ({col['type']}): {desc}")

# Find columns that are DICOM attributes (check description for "DICOM" reference)
dicom_cols = [c['name'] for c in schema['columns'] if 'DICOM' in c.get('description', '').upper()]
print(f"\nDICOM-sourced columns: {dicom_cols}")
```

**Alternative: use `get_index_schema()` method:**
```python
schema = client.get_index_schema("index")
# Returns same schema dict: {'table_description': ..., 'columns': [...]}
```

## Key Columns in Primary `index` Table

Most common columns for queries (use `indices_overview` for complete list and descriptions):

| Column | Type | DICOM | Description |
|--------|------|-------|-------------|
| `collection_id` | STRING | No | IDC collection identifier |
| `analysis_result_id` | STRING | No | If applicable, indicates what analysis results collection given series is part of |
| `source_DOI` | STRING | No | DOI linking to dataset details; use for learning more about the content and for attribution (see citations below) |
| `PatientID` | STRING | Yes | Patient identifier |
| `StudyInstanceUID` | STRING | Yes | DICOM Study UID |
| `SeriesInstanceUID` | STRING | Yes | DICOM Series UID - use for downloads/viewing |
| `Modality` | STRING | Yes | Imaging modality (CT, MR, PT, SM, etc.) |
| `BodyPartExamined` | STRING | Yes | Anatomical region |
| `SeriesDescription` | STRING | Yes | Description of the series |
| `Manufacturer` | STRING | Yes | Equipment manufacturer |
| `StudyDate` | STRING | Yes | Date study was performed |
| `PatientSex` | STRING | Yes | Patient sex |
| `PatientAge` | STRING | Yes | Patient age at time of study |
| `license_short_name` | STRING | No | License type (CC BY 4.0, CC BY-NC 4.0, etc.) |
| `series_size_MB` | FLOAT | No | Size of series in megabytes |
| `instanceCount` | INTEGER | No | Number of DICOM instances in series |

**DICOM = Yes**: Column value extracted from the DICOM attribute with the same name. Refer to the [DICOM standard](https://dicom.nema.org/medical/dicom/current/output/chtml/part06/chapter_6.html) for numeric tag mappings. Use standard DICOM knowledge for expected values and formats.

## Clinical Data Access

```python
# Fetch clinical index (also downloads clinical data tables)
client.fetch_index("clinical_index")

# Query clinical index to find available tables and their columns
tables = client.sql_query("SELECT DISTINCT table_name, column_label FROM clinical_index")

# Load a specific clinical table as DataFrame
clinical_df = client.get_clinical_table("table_name")
```
