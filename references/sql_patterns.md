# Common SQL Query Patterns

Quick reference for common queries. For detailed examples with context, see the Core Capabilities section in the main SKILL.md.

## Discover Available Filter Values

```python
from idc_index import IDCClient
client = IDCClient()

# What modalities exist?
client.sql_query("SELECT DISTINCT Modality FROM index")

# What body parts for a specific modality?
client.sql_query("""
    SELECT DISTINCT BodyPartExamined, COUNT(*) as n
    FROM index WHERE Modality = 'CT' AND BodyPartExamined IS NOT NULL
    GROUP BY BodyPartExamined ORDER BY n DESC
""")

# What manufacturers for MR?
client.sql_query("""
    SELECT DISTINCT Manufacturer, COUNT(*) as n
    FROM index WHERE Modality = 'MR'
    GROUP BY Manufacturer ORDER BY n DESC
""")
```

## Find Annotations and Segmentations

**Note:** Not all image-derived objects belong to analysis result collections. Some annotations are deposited alongside original images. Use DICOM Modality or SOPClassUID to find all derived objects regardless of collection type.

```python
# Find ALL segmentations and structure sets by DICOM Modality
# SEG = DICOM Segmentation, RTSTRUCT = Radiotherapy Structure Set
client.sql_query("""
    SELECT collection_id, Modality, COUNT(*) as series_count
    FROM index
    WHERE Modality IN ('SEG', 'RTSTRUCT')
    GROUP BY collection_id, Modality
    ORDER BY series_count DESC
""")

# Find segmentations for a specific collection (includes non-analysis-result items)
client.sql_query("""
    SELECT SeriesInstanceUID, SeriesDescription, analysis_result_id
    FROM index
    WHERE collection_id = 'tcga_luad' AND Modality = 'SEG'
""")

# List analysis result collections (curated derived datasets)
client.fetch_index("analysis_results_index")
client.sql_query("""
    SELECT analysis_result_id, analysis_result_title, Collections, Modalities
    FROM analysis_results_index
""")

# Find analysis results for a specific source collection
client.sql_query("""
    SELECT analysis_result_id, analysis_result_title
    FROM analysis_results_index
    WHERE Collections LIKE '%tcga_luad%'
""")
```

## Segmentation Index Queries

```python
# Use seg_index for detailed DICOM Segmentation metadata
client.fetch_index("seg_index")

# Get segmentation statistics by algorithm
client.sql_query("""
    SELECT AlgorithmName, AlgorithmType, COUNT(*) as seg_count
    FROM seg_index
    WHERE AlgorithmName IS NOT NULL
    GROUP BY AlgorithmName, AlgorithmType
    ORDER BY seg_count DESC
    LIMIT 10
""")

# Find segmentations for specific source images (e.g., chest CT)
client.sql_query("""
    SELECT
        s.SeriesInstanceUID as seg_series,
        s.AlgorithmName,
        s.total_segments,
        s.segmented_SeriesInstanceUID as source_series
    FROM seg_index s
    JOIN index src ON s.segmented_SeriesInstanceUID = src.SeriesInstanceUID
    WHERE src.Modality = 'CT' AND src.BodyPartExamined = 'CHEST'
    LIMIT 10
""")

# Find TotalSegmentator results with source image context
client.sql_query("""
    SELECT
        seg_info.collection_id,
        COUNT(DISTINCT s.SeriesInstanceUID) as seg_count,
        SUM(s.total_segments) as total_segments
    FROM seg_index s
    JOIN index seg_info ON s.SeriesInstanceUID = seg_info.SeriesInstanceUID
    WHERE s.AlgorithmName LIKE '%TotalSegmentator%'
    GROUP BY seg_info.collection_id
    ORDER BY seg_count DESC
""")
```

## Query Slide Microscopy Data

```python
# sm_index has detailed metadata; join with index for collection_id
client.fetch_index("sm_index")
client.sql_query("""
    SELECT i.collection_id, COUNT(*) as slides,
           MIN(s.min_PixelSpacing_2sf) as min_resolution
    FROM sm_index s
    JOIN index i ON s.SeriesInstanceUID = i.SeriesInstanceUID
    GROUP BY i.collection_id
    ORDER BY slides DESC
""")
```

## Estimate Download Size

```python
# Size for specific criteria
client.sql_query("""
    SELECT SUM(series_size_MB) as total_mb, COUNT(*) as series_count
    FROM index
    WHERE collection_id = 'nlst' AND Modality = 'CT'
""")

# Size by collection
client.sql_query("""
    SELECT collection_id,
           SUM(series_size_MB) as total_mb,
           COUNT(*) as series_count
    FROM index
    GROUP BY collection_id
    ORDER BY total_mb DESC
    LIMIT 20
""")
```

## Link to Clinical Data

```python
client.fetch_index("clinical_index")

# Find collections with clinical data and their tables
client.sql_query("""
    SELECT collection_id, table_name, COUNT(DISTINCT column_label) as columns
    FROM clinical_index
    GROUP BY collection_id, table_name
    ORDER BY collection_id
""")

# Find specific clinical variables
client.sql_query("""
    SELECT collection_id, table_name, column_label
    FROM clinical_index
    WHERE column_label LIKE '%survival%' OR column_label LIKE '%stage%'
""")
```

## Filter by License (Commercial Use)

```python
# Find only CC BY licensed data (allows commercial use)
client.sql_query("""
    SELECT collection_id, COUNT(*) as series_count
    FROM index
    WHERE license_short_name LIKE 'CC BY%'
      AND license_short_name NOT LIKE '%NC%'
    GROUP BY collection_id
    ORDER BY series_count DESC
""")

# Check license distribution for a collection
client.sql_query("""
    SELECT license_short_name, COUNT(*) as series_count
    FROM index
    WHERE collection_id = 'tcga_luad'
    GROUP BY license_short_name
""")
```

## Multi-Modality Studies

```python
# Find patients with both CT and PET scans
client.sql_query("""
    SELECT PatientID, collection_id
    FROM index
    WHERE Modality = 'CT'
    INTERSECT
    SELECT PatientID, collection_id
    FROM index
    WHERE Modality = 'PT'
""")

# Count modalities per patient
client.sql_query("""
    SELECT PatientID, collection_id,
           COUNT(DISTINCT Modality) as modality_count,
           GROUP_CONCAT(DISTINCT Modality) as modalities
    FROM index
    GROUP BY PatientID, collection_id
    HAVING modality_count > 1
    ORDER BY modality_count DESC
    LIMIT 20
""")
```

## Collection Statistics

```python
# Summary statistics for a collection
client.sql_query("""
    SELECT
        COUNT(DISTINCT PatientID) as patients,
        COUNT(DISTINCT StudyInstanceUID) as studies,
        COUNT(DISTINCT SeriesInstanceUID) as series,
        SUM(instanceCount) as instances,
        SUM(series_size_MB) as total_mb
    FROM index
    WHERE collection_id = 'nlst'
""")

# Modality breakdown for a collection
client.sql_query("""
    SELECT Modality, COUNT(*) as series_count, SUM(series_size_MB) as size_mb
    FROM index
    WHERE collection_id = 'tcga_luad'
    GROUP BY Modality
    ORDER BY series_count DESC
""")
```
