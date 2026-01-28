# Common Use Cases

Detailed examples for common IDC workflows.

## Use Case 1: Find and Download Lung CT Scans for Deep Learning

**Objective:** Build training dataset of lung CT scans from NLST collection

**Steps:**
```python
from idc_index import IDCClient

client = IDCClient()

# 1. Query for lung CT scans with specific criteria
query = """
SELECT
  PatientID,
  SeriesInstanceUID,
  SeriesDescription
FROM index
WHERE collection_id = 'nlst'
  AND Modality = 'CT'
  AND BodyPartExamined = 'CHEST'
  AND license_short_name = 'CC BY 4.0'
ORDER BY PatientID
LIMIT 100
"""

results = client.sql_query(query)
print(f"Found {len(results)} series from {results['PatientID'].nunique()} patients")

# 2. Download data organized by patient
client.download_from_selection(
    seriesInstanceUID=list(results['SeriesInstanceUID'].values),
    downloadDir="./training_data",
    dirTemplate="%collection_id/%PatientID/%SeriesInstanceUID"
)

# 3. Save manifest for reproducibility
results.to_csv('training_manifest.csv', index=False)
```

## Use Case 2: Query Brain MRI by Manufacturer for Quality Study

**Objective:** Compare image quality across different MRI scanner manufacturers

**Steps:**
```python
from idc_index import IDCClient
import pandas as pd

client = IDCClient()

# Query for brain MRI grouped by manufacturer
query = """
SELECT
  Manufacturer,
  ManufacturerModelName,
  COUNT(DISTINCT SeriesInstanceUID) as num_series,
  COUNT(DISTINCT PatientID) as num_patients
FROM index
WHERE Modality = 'MR'
  AND BodyPartExamined LIKE '%BRAIN%'
GROUP BY Manufacturer, ManufacturerModelName
HAVING num_series >= 10
ORDER BY num_series DESC
"""

manufacturers = client.sql_query(query)
print(manufacturers)

# Download sample from each manufacturer for comparison
for _, row in manufacturers.head(3).iterrows():
    mfr = row['Manufacturer']
    model = row['ManufacturerModelName']

    query = f"""
    SELECT SeriesInstanceUID
    FROM index
    WHERE Manufacturer = '{mfr}'
      AND ManufacturerModelName = '{model}'
      AND Modality = 'MR'
      AND BodyPartExamined LIKE '%BRAIN%'
    LIMIT 5
    """

    series = client.sql_query(query)
    client.download_from_selection(
        seriesInstanceUID=list(series['SeriesInstanceUID'].values),
        downloadDir=f"./quality_study/{mfr.replace(' ', '_')}"
    )
```

## Use Case 3: Visualize Series Without Downloading

**Objective:** Preview imaging data before committing to download

```python
from idc_index import IDCClient
import webbrowser

client = IDCClient()

series_list = client.sql_query("""
    SELECT SeriesInstanceUID, PatientID, SeriesDescription
    FROM index
    WHERE collection_id = 'acrin_nsclc_fdg_pet' AND Modality = 'PT'
    LIMIT 10
""")

# Preview each in browser
for _, row in series_list.iterrows():
    viewer_url = client.get_viewer_URL(seriesInstanceUID=row['SeriesInstanceUID'])
    print(f"Patient {row['PatientID']}: {row['SeriesDescription']}")
    print(f"  View at: {viewer_url}")
    # webbrowser.open(viewer_url)  # Uncomment to open automatically
```

For additional visualization options, see the [IDC Portal getting started guide](https://learn.canceridc.dev/portal/getting-started) or [SlicerIDCBrowser](https://github.com/ImagingDataCommons/SlicerIDCBrowser) for 3D Slicer integration.

## Use Case 4: License-Aware Batch Download for Commercial Use

**Objective:** Download only CC-BY licensed data suitable for commercial applications

**Steps:**
```python
from idc_index import IDCClient

client = IDCClient()

# Query ONLY for CC BY licensed data (allows commercial use with attribution)
query = """
SELECT
  SeriesInstanceUID,
  collection_id,
  PatientID,
  Modality
FROM index
WHERE license_short_name LIKE 'CC BY%'
  AND license_short_name NOT LIKE '%NC%'
  AND Modality IN ('CT', 'MR')
  AND BodyPartExamined IN ('CHEST', 'BRAIN', 'ABDOMEN')
LIMIT 200
"""

cc_by_data = client.sql_query(query)

print(f"Found {len(cc_by_data)} CC BY licensed series")
print(f"Collections: {cc_by_data['collection_id'].unique()}")

# Download with license verification
client.download_from_selection(
    seriesInstanceUID=list(cc_by_data['SeriesInstanceUID'].values),
    downloadDir="./commercial_dataset",
    dirTemplate="%collection_id/%Modality/%PatientID/%SeriesInstanceUID"
)

# Save license information
cc_by_data.to_csv('commercial_dataset_manifest_CC-BY_ONLY.csv', index=False)
```

## Use Case 5: Build Multi-Modal Dataset (CT + PET)

**Objective:** Find patients with both CT and PET scans for fusion analysis

```python
from idc_index import IDCClient

client = IDCClient()

# Find patients with both modalities
query = """
SELECT DISTINCT i1.PatientID, i1.collection_id
FROM index i1
INNER JOIN index i2 ON i1.PatientID = i2.PatientID
WHERE i1.Modality = 'CT' AND i2.Modality = 'PT'
  AND i1.collection_id = i2.collection_id
LIMIT 50
"""

multimodal_patients = client.sql_query(query)
print(f"Found {len(multimodal_patients)} patients with CT+PET")

# Download both modalities for each patient
for _, row in multimodal_patients.head(10).iterrows():
    patient = row['PatientID']
    collection = row['collection_id']

    # Get all CT and PET series for this patient
    series = client.sql_query(f"""
        SELECT SeriesInstanceUID, Modality
        FROM index
        WHERE PatientID = '{patient}'
          AND collection_id = '{collection}'
          AND Modality IN ('CT', 'PT')
    """)

    client.download_from_selection(
        seriesInstanceUID=list(series['SeriesInstanceUID'].values),
        downloadDir=f"./multimodal/{collection}/{patient}",
        dirTemplate="%Modality/%SeriesInstanceUID"
    )
```

## Use Case 6: Download Segmentations with Source Images

**Objective:** Download AI-generated segmentations along with their source images

```python
from idc_index import IDCClient

client = IDCClient()

# Fetch segmentation index
client.fetch_index("seg_index")

# Find TotalSegmentator segmentations with their source CT images
query = """
SELECT
    s.SeriesInstanceUID as seg_uid,
    s.segmented_SeriesInstanceUID as source_uid,
    s.AlgorithmName,
    s.total_segments,
    src.collection_id,
    src.PatientID
FROM seg_index s
JOIN index src ON s.segmented_SeriesInstanceUID = src.SeriesInstanceUID
WHERE s.AlgorithmName LIKE '%TotalSegmentator%'
  AND src.Modality = 'CT'
LIMIT 20
"""

results = client.sql_query(query)
print(f"Found {len(results)} segmentations")

# Download both segmentation and source image
for _, row in results.iterrows():
    uids = [row['seg_uid'], row['source_uid']]
    client.download_from_selection(
        seriesInstanceUID=uids,
        downloadDir=f"./segmentation_pairs/{row['PatientID']}",
        dirTemplate="%Modality_%SeriesInstanceUID"
    )
```

## Use Case 7: Pathology Slide Analysis Setup

**Objective:** Download whole slide images for computational pathology

```python
from idc_index import IDCClient

client = IDCClient()

# Fetch slide microscopy index for detailed metadata
client.fetch_index("sm_index")

# Find high-resolution slides from TCGA
query = """
SELECT
    i.SeriesInstanceUID,
    i.collection_id,
    i.PatientID,
    s.ObjectiveLensPower,
    s.min_PixelSpacing_2sf as resolution_mm,
    i.series_size_MB
FROM index i
JOIN sm_index s ON i.SeriesInstanceUID = s.SeriesInstanceUID
WHERE i.collection_id LIKE 'tcga_%'
  AND i.Modality = 'SM'
  AND s.ObjectiveLensPower >= 40
ORDER BY i.series_size_MB ASC
LIMIT 10
"""

slides = client.sql_query(query)
print(f"Found {len(slides)} high-resolution slides")
print(f"Total size: {slides['series_size_MB'].sum():.1f} MB")

# Download slides (warning: WSI files can be very large!)
client.download_from_selection(
    seriesInstanceUID=list(slides['SeriesInstanceUID'].values),
    downloadDir="./pathology_slides",
    dirTemplate="%collection_id/%PatientID"
)
```

## Use Case 8: Reproducible Research Dataset

**Objective:** Create a versioned, reproducible dataset with full provenance

```python
from idc_index import IDCClient
import json
from datetime import datetime

client = IDCClient()

# Document the IDC version
idc_version = client.get_idc_version()

# Define your selection criteria
query = """
SELECT
    SeriesInstanceUID,
    collection_id,
    PatientID,
    Modality,
    SeriesDescription,
    license_short_name,
    source_DOI
FROM index
WHERE collection_id = 'rider_pilot'
  AND Modality = 'CT'
"""

selection = client.sql_query(query)

# Generate citations for attribution
citations = client.citations_from_selection(
    seriesInstanceUID=list(selection['SeriesInstanceUID'].values)
)

# Create provenance record
provenance = {
    "created": datetime.now().isoformat(),
    "idc_version": idc_version,
    "query": query,
    "series_count": len(selection),
    "collections": list(selection['collection_id'].unique()),
    "licenses": list(selection['license_short_name'].unique()),
    "citations": citations
}

# Save provenance
with open('dataset_provenance.json', 'w') as f:
    json.dump(provenance, f, indent=2)

# Save manifest
selection.to_csv('dataset_manifest.csv', index=False)

# Download
client.download_from_selection(
    seriesInstanceUID=list(selection['SeriesInstanceUID'].values),
    downloadDir="./reproducible_dataset",
    dirTemplate="%collection_id/%PatientID/%SeriesInstanceUID"
)

print(f"Dataset created with {len(selection)} series")
print(f"IDC version: {idc_version}")
print(f"Provenance saved to dataset_provenance.json")
```
