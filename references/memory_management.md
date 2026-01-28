# Memory Management Guide

Strategies for efficiently handling large IDC datasets.

## Estimating Download Size

Always estimate size before downloading:

```python
from idc_index import IDCClient

client = IDCClient()

# Check size for your query
size_estimate = client.sql_query("""
    SELECT
        SUM(series_size_MB) as total_mb,
        COUNT(*) as series_count,
        SUM(instanceCount) as total_instances
    FROM index
    WHERE collection_id = 'nlst' AND Modality = 'CT'
""")

total_gb = size_estimate['total_mb'].iloc[0] / 1024
print(f"Estimated download: {total_gb:.1f} GB")
print(f"Series count: {size_estimate['series_count'].iloc[0]}")

# Check available disk space
import shutil
free_gb = shutil.disk_usage('.').free / (1024**3)
print(f"Available disk space: {free_gb:.1f} GB")

# Rule of thumb: need 1.5x estimated size for safety
if total_gb * 1.5 > free_gb:
    print("WARNING: May not have enough disk space!")
```

## Batch Downloading Strategy

For large datasets, download in batches:

```python
from idc_index import IDCClient
import time

client = IDCClient()

# Get all series to download
all_series = client.sql_query("""
    SELECT SeriesInstanceUID, series_size_MB
    FROM index
    WHERE collection_id = 'nlst' AND Modality = 'CT'
    LIMIT 500
""")

# Download in batches
batch_size = 20
total_batches = (len(all_series) + batch_size - 1) // batch_size

for i in range(0, len(all_series), batch_size):
    batch = all_series.iloc[i:i+batch_size]
    batch_num = i // batch_size + 1

    print(f"Downloading batch {batch_num}/{total_batches}")
    print(f"  Series: {len(batch)}")
    print(f"  Size: {batch['series_size_MB'].sum():.1f} MB")

    client.download_from_selection(
        seriesInstanceUID=list(batch['SeriesInstanceUID'].values),
        downloadDir=f"./data/batch_{batch_num:03d}"
    )

    # Optional: pause between batches to avoid rate limiting
    time.sleep(2)
```

## Memory-Efficient DICOM Processing

When processing large volumes, avoid loading everything into memory:

```python
import pydicom
from pathlib import Path
import numpy as np

def process_series_streaming(series_dir, process_func):
    """Process DICOM series slice-by-slice without loading entire volume"""
    files = sorted(Path(series_dir).glob('*.dcm'))

    results = []
    for f in files:
        # Read single slice
        ds = pydicom.dcmread(str(f))
        pixel_array = ds.pixel_array

        # Process slice
        result = process_func(pixel_array, ds)
        results.append(result)

        # Memory is freed after each iteration
        del ds, pixel_array

    return results

# Example: calculate mean intensity per slice
def slice_mean(pixels, ds):
    return {'slice': ds.InstanceNumber, 'mean': pixels.mean()}

results = process_series_streaming("./data/ct_series", slice_mean)
```

## Chunked Volume Loading

For volumes too large for memory, use memory-mapped arrays:

```python
import numpy as np
import pydicom
from pathlib import Path

def load_volume_mmap(series_dir, output_file):
    """Load DICOM series into memory-mapped numpy array"""
    files = sorted(Path(series_dir).glob('*.dcm'))

    # Read first slice to get dimensions
    first = pydicom.dcmread(str(files[0]))
    shape = (len(files), first.Rows, first.Columns)
    dtype = first.pixel_array.dtype

    # Create memory-mapped array
    mmap = np.memmap(output_file, dtype=dtype, mode='w+', shape=shape)

    # Load slices one at a time
    for i, f in enumerate(files):
        ds = pydicom.dcmread(str(f))
        mmap[i] = ds.pixel_array

    mmap.flush()
    return mmap

# Create memory-mapped volume
volume = load_volume_mmap("./data/ct_series", "volume.dat")
print(f"Volume shape: {volume.shape}")

# Access without loading entire volume into RAM
slice_100 = volume[100]  # Only loads this slice
```

## Download Directory Organization

Organize downloads to enable incremental processing:

```python
from idc_index import IDCClient

client = IDCClient()

# Organize by collection and patient for easy cleanup
client.download_from_selection(
    collection_id="nlst",
    downloadDir="./data",
    dirTemplate="%collection_id/%PatientID/%Modality_%SeriesInstanceUID"
)

# This creates:
# ./data/nlst/PATIENT001/CT_1.2.3.../
# ./data/nlst/PATIENT001/CT_1.2.4.../
# ./data/nlst/PATIENT002/CT_1.2.5.../
```

## Cleanup After Processing

Remove downloaded data after processing to free disk space:

```python
import shutil
from pathlib import Path

def process_and_cleanup(series_dirs, output_dir):
    """Process series and clean up to save disk space"""
    for series_dir in series_dirs:
        try:
            # Process series
            result = process_series(series_dir)

            # Save result
            output_path = output_dir / f"{series_dir.name}_result.npy"
            np.save(output_path, result)

            # Clean up DICOM files
            shutil.rmtree(series_dir)
            print(f"Processed and cleaned: {series_dir.name}")

        except Exception as e:
            print(f"Error processing {series_dir}: {e}")
            # Keep failed series for debugging
```

## Parallel Download Considerations

The idc-index package handles downloads efficiently, but for very large datasets:

```python
from idc_index import IDCClient
from concurrent.futures import ThreadPoolExecutor
import os

def download_collection(collection_id, output_dir):
    """Download a single collection"""
    client = IDCClient()  # Create new client per thread
    client.download_from_selection(
        collection_id=collection_id,
        downloadDir=output_dir
    )

# Download multiple small collections in parallel
collections = ['rider_pilot', 'phantom_fda', 'lidc_idri']

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(download_collection, c, f"./data/{c}")
        for c in collections
    ]
```

## Disk Space Monitoring

Monitor disk space during long downloads:

```python
import shutil
import time
from pathlib import Path

def monitor_disk_space(download_dir, min_free_gb=10, check_interval=60):
    """Monitor disk space and warn if running low"""
    while True:
        free_gb = shutil.disk_usage(download_dir).free / (1024**3)
        used_gb = sum(f.stat().st_size for f in Path(download_dir).rglob('*')) / (1024**3)

        print(f"Downloaded: {used_gb:.1f} GB, Free: {free_gb:.1f} GB")

        if free_gb < min_free_gb:
            print(f"WARNING: Less than {min_free_gb} GB free!")
            return False

        time.sleep(check_interval)
```

## Size Reference

Typical IDC data sizes:

| Data Type | Typical Size per Series |
|-----------|------------------------|
| CT scan (chest) | 100-500 MB |
| MRI series | 50-200 MB |
| PET scan | 20-100 MB |
| Whole slide image | 500 MB - 5 GB |
| Segmentation | 1-50 MB |

Collection sizes vary from < 1 GB to > 10 TB. Always check before downloading!
