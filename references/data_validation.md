# Data Validation Guide

Strategies for validating downloaded DICOM data integrity and completeness.

## Quick Validation Check

Basic validation after download:

```python
import pydicom
from pathlib import Path

def validate_series(series_dir):
    """Quick validation of a downloaded DICOM series"""
    series_path = Path(series_dir)
    dcm_files = list(series_path.glob('*.dcm'))

    if not dcm_files:
        return {'valid': False, 'error': 'No DICOM files found'}

    errors = []
    valid_count = 0

    for f in dcm_files:
        try:
            ds = pydicom.dcmread(str(f))
            valid_count += 1
        except Exception as e:
            errors.append(f"{f.name}: {str(e)}")

    return {
        'valid': len(errors) == 0,
        'total_files': len(dcm_files),
        'valid_files': valid_count,
        'errors': errors
    }

result = validate_series("./data/ct_series")
print(f"Valid: {result['valid']}, Files: {result['valid_files']}/{result['total_files']}")
```

## Verify Series Completeness

Check if all expected instances were downloaded:

```python
from idc_index import IDCClient
import pydicom
from pathlib import Path

def verify_series_completeness(series_uid, download_dir):
    """Verify downloaded series matches expected instance count"""
    client = IDCClient()

    # Get expected count from index
    expected = client.sql_query(f"""
        SELECT instanceCount, series_size_MB
        FROM index
        WHERE SeriesInstanceUID = '{series_uid}'
    """)

    if expected.empty:
        return {'complete': False, 'error': 'Series not found in index'}

    expected_count = expected['instanceCount'].iloc[0]
    expected_size_mb = expected['series_size_MB'].iloc[0]

    # Count downloaded files
    series_path = Path(download_dir)
    dcm_files = list(series_path.rglob('*.dcm'))
    actual_count = len(dcm_files)

    # Calculate actual size
    actual_size_mb = sum(f.stat().st_size for f in dcm_files) / (1024 * 1024)

    return {
        'complete': actual_count == expected_count,
        'expected_instances': expected_count,
        'actual_instances': actual_count,
        'expected_size_mb': expected_size_mb,
        'actual_size_mb': round(actual_size_mb, 2),
        'missing': expected_count - actual_count
    }

result = verify_series_completeness(
    "1.3.6.1.4.1.9328.50.1.123456",
    "./data/ct_series"
)
print(f"Complete: {result['complete']}, Missing: {result['missing']} instances")
```

## Validate DICOM Metadata Consistency

Check that downloaded data matches query criteria:

```python
import pydicom
from pathlib import Path

def validate_metadata(series_dir, expected_modality=None, expected_body_part=None):
    """Validate DICOM metadata matches expected values"""
    series_path = Path(series_dir)
    dcm_files = list(series_path.glob('*.dcm'))

    if not dcm_files:
        return {'valid': False, 'error': 'No DICOM files found'}

    # Read first file for series-level metadata
    ds = pydicom.dcmread(str(dcm_files[0]))

    issues = []

    if expected_modality and ds.Modality != expected_modality:
        issues.append(f"Modality mismatch: expected {expected_modality}, got {ds.Modality}")

    if expected_body_part and getattr(ds, 'BodyPartExamined', None) != expected_body_part:
        actual = getattr(ds, 'BodyPartExamined', 'NOT SET')
        issues.append(f"BodyPart mismatch: expected {expected_body_part}, got {actual}")

    return {
        'valid': len(issues) == 0,
        'modality': ds.Modality,
        'body_part': getattr(ds, 'BodyPartExamined', None),
        'patient_id': ds.PatientID,
        'series_uid': ds.SeriesInstanceUID,
        'issues': issues
    }

result = validate_metadata("./data/ct_series", expected_modality='CT', expected_body_part='CHEST')
```

## Check for Corrupted Files

Detect truncated or corrupted DICOM files:

```python
import pydicom
from pathlib import Path

def check_file_integrity(series_dir):
    """Check for corrupted or truncated DICOM files"""
    series_path = Path(series_dir)
    dcm_files = list(series_path.glob('*.dcm'))

    results = {
        'total': len(dcm_files),
        'valid': 0,
        'corrupted': [],
        'truncated': [],
        'no_pixels': []
    }

    for f in dcm_files:
        try:
            # Try to read the full file including pixel data
            ds = pydicom.dcmread(str(f))

            # Check if pixel data exists (for image modalities)
            if hasattr(ds, 'PixelData'):
                # Try to access pixel array to verify it's readable
                _ = ds.pixel_array
                results['valid'] += 1
            elif ds.Modality in ['CT', 'MR', 'PT', 'CR', 'DX']:
                # Image modality but no pixel data
                results['no_pixels'].append(f.name)
            else:
                # Non-image modality (SEG, SR, etc.) - pixel data optional
                results['valid'] += 1

        except pydicom.errors.InvalidDicomError as e:
            results['corrupted'].append({'file': f.name, 'error': str(e)})
        except Exception as e:
            if 'truncated' in str(e).lower():
                results['truncated'].append(f.name)
            else:
                results['corrupted'].append({'file': f.name, 'error': str(e)})

    return results

integrity = check_file_integrity("./data/ct_series")
print(f"Valid: {integrity['valid']}/{integrity['total']}")
if integrity['corrupted']:
    print(f"Corrupted: {len(integrity['corrupted'])} files")
```

## Validate CT Volume Geometry

For CT series, verify consistent geometry for 3D reconstruction:

```python
import pydicom
from pathlib import Path
import numpy as np

def validate_ct_geometry(series_dir):
    """Validate CT series has consistent geometry for 3D reconstruction"""
    series_path = Path(series_dir)
    dcm_files = sorted(series_path.glob('*.dcm'))

    if len(dcm_files) < 2:
        return {'valid': False, 'error': 'Need at least 2 slices'}

    slices = []
    for f in dcm_files:
        ds = pydicom.dcmread(str(f))
        slices.append({
            'file': f.name,
            'rows': ds.Rows,
            'cols': ds.Columns,
            'spacing': list(ds.PixelSpacing),
            'position': list(ds.ImagePositionPatient),
            'orientation': list(ds.ImageOrientationPatient),
            'thickness': getattr(ds, 'SliceThickness', None)
        })

    issues = []

    # Check consistent dimensions
    rows = set(s['rows'] for s in slices)
    cols = set(s['cols'] for s in slices)
    if len(rows) > 1 or len(cols) > 1:
        issues.append(f"Inconsistent dimensions: rows={rows}, cols={cols}")

    # Check consistent pixel spacing
    spacings = set(tuple(s['spacing']) for s in slices)
    if len(spacings) > 1:
        issues.append(f"Inconsistent pixel spacing: {spacings}")

    # Check consistent orientation
    orientations = set(tuple(s['orientation']) for s in slices)
    if len(orientations) > 1:
        issues.append("Inconsistent image orientation")

    # Check slice spacing consistency
    positions = sorted(slices, key=lambda x: x['position'][2])
    slice_gaps = []
    for i in range(1, len(positions)):
        gap = positions[i]['position'][2] - positions[i-1]['position'][2]
        slice_gaps.append(round(gap, 3))

    unique_gaps = set(slice_gaps)
    if len(unique_gaps) > 1:
        # Allow small variation (< 1%)
        gap_variation = (max(slice_gaps) - min(slice_gaps)) / np.mean(slice_gaps)
        if gap_variation > 0.01:
            issues.append(f"Inconsistent slice spacing: {unique_gaps}")

    return {
        'valid': len(issues) == 0,
        'num_slices': len(slices),
        'dimensions': (slices[0]['rows'], slices[0]['cols']),
        'pixel_spacing': slices[0]['spacing'],
        'slice_thickness': slices[0]['thickness'],
        'issues': issues
    }

geometry = validate_ct_geometry("./data/ct_series")
print(f"Valid geometry: {geometry['valid']}")
print(f"Dimensions: {geometry['dimensions']}, Slices: {geometry['num_slices']}")
```

## Batch Validation

Validate multiple downloaded series:

```python
from pathlib import Path
import json

def batch_validate(download_root, manifest_df):
    """Validate all series listed in manifest"""
    results = []

    for _, row in manifest_df.iterrows():
        series_uid = row['SeriesInstanceUID']
        expected_count = row.get('instanceCount', None)

        # Find series directory
        series_dirs = list(Path(download_root).rglob(f"*{series_uid[-12:]}*"))

        if not series_dirs:
            results.append({
                'series_uid': series_uid,
                'status': 'NOT_FOUND',
                'error': 'Directory not found'
            })
            continue

        series_dir = series_dirs[0]

        # Run validations
        integrity = check_file_integrity(series_dir)
        metadata = validate_metadata(series_dir)

        status = 'VALID'
        issues = []

        if integrity['corrupted']:
            status = 'CORRUPTED'
            issues.extend([c['file'] for c in integrity['corrupted']])

        if expected_count and integrity['valid'] != expected_count:
            status = 'INCOMPLETE'
            issues.append(f"Missing {expected_count - integrity['valid']} instances")

        results.append({
            'series_uid': series_uid,
            'status': status,
            'valid_files': integrity['valid'],
            'expected_files': expected_count,
            'modality': metadata.get('modality'),
            'issues': issues
        })

    return results

# Usage with manifest from download
import pandas as pd
manifest = pd.read_csv('download_manifest.csv')
validation = batch_validate("./data", manifest)

# Summary
valid = sum(1 for r in validation if r['status'] == 'VALID')
print(f"Validation complete: {valid}/{len(validation)} series valid")

# Save detailed results
with open('validation_report.json', 'w') as f:
    json.dump(validation, f, indent=2)
```

## Re-download Failed Series

Automatically re-download incomplete or corrupted series:

```python
from idc_index import IDCClient

def redownload_failed(validation_results, download_dir):
    """Re-download series that failed validation"""
    client = IDCClient()

    failed_uids = [
        r['series_uid'] for r in validation_results
        if r['status'] in ['NOT_FOUND', 'INCOMPLETE', 'CORRUPTED']
    ]

    if not failed_uids:
        print("No failed series to re-download")
        return

    print(f"Re-downloading {len(failed_uids)} failed series...")

    client.download_from_selection(
        seriesInstanceUID=failed_uids,
        downloadDir=download_dir,
        dirTemplate="%SeriesInstanceUID"  # Flat structure for easy identification
    )

    print("Re-download complete. Run validation again to verify.")
```

## Validation Checklist

Use this checklist after downloading:

- [ ] All expected series directories exist
- [ ] Instance counts match expected values from index
- [ ] No corrupted or truncated DICOM files
- [ ] Metadata matches query criteria (modality, body part, etc.)
- [ ] For CT: consistent geometry across slices
- [ ] File sizes are reasonable (not 0 bytes)
- [ ] Manifest saved for reproducibility
