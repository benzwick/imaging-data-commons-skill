# Integration with Analysis Pipelines

Guide for integrating IDC data into imaging analysis workflows.

## Reading DICOM Files with pydicom

```python
import pydicom
import os

# Read DICOM files from downloaded series
series_dir = "./data/rider/rider_pilot/RIDER-1007893286/CT_1.3.6.1..."

dicom_files = [os.path.join(series_dir, f) for f in os.listdir(series_dir)
               if f.endswith('.dcm')]

# Load first image
ds = pydicom.dcmread(dicom_files[0])
print(f"Patient ID: {ds.PatientID}")
print(f"Modality: {ds.Modality}")
print(f"Image shape: {ds.pixel_array.shape}")
```

## Building 3D Volumes from CT Series

```python
import pydicom
import numpy as np
from pathlib import Path

def load_ct_series(series_path):
    """Load CT series as 3D numpy array"""
    files = sorted(Path(series_path).glob('*.dcm'))
    slices = [pydicom.dcmread(str(f)) for f in files]

    # Sort by slice location
    slices.sort(key=lambda x: float(x.ImagePositionPatient[2]))

    # Stack into 3D array
    volume = np.stack([s.pixel_array for s in slices])

    return volume, slices[0]  # Return volume and first slice for metadata

volume, metadata = load_ct_series("./data/lung_ct/series_dir")
print(f"Volume shape: {volume.shape}")  # (z, y, x)
```

## SimpleITK Integration

```python
import SimpleITK as sitk
from pathlib import Path

# Read DICOM series
series_path = "./data/ct_series"
reader = sitk.ImageSeriesReader()
dicom_names = reader.GetGDCMSeriesFileNames(series_path)
reader.SetFileNames(dicom_names)
image = reader.Execute()

# Apply processing
smoothed = sitk.CurvatureFlow(image1=image, timeStep=0.125, numberOfIterations=5)

# Save as NIfTI
sitk.WriteImage(smoothed, "processed_volume.nii.gz")
```

## Converting to NIfTI Format

```python
import SimpleITK as sitk
from pathlib import Path

def dicom_to_nifti(dicom_dir, output_path):
    """Convert DICOM series to NIfTI format"""
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(str(dicom_dir))
    reader.SetFileNames(dicom_names)
    image = reader.Execute()
    sitk.WriteImage(image, str(output_path))

# Example usage
dicom_to_nifti("./data/ct_series", "./output/volume.nii.gz")
```

## Radiomics Feature Extraction

```python
from radiomics import featureextractor
import SimpleITK as sitk

# Load image and segmentation
image = sitk.ReadImage("volume.nii.gz")
mask = sitk.ReadImage("segmentation.nii.gz")

# Initialize extractor
extractor = featureextractor.RadiomicsFeatureExtractor()

# Extract features
features = extractor.execute(image, mask)

# Print features
for key, value in features.items():
    if not key.startswith('diagnostics'):
        print(f"{key}: {value}")
```

## MONAI Integration for Deep Learning

```python
import monai
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd,
    ScaleIntensityRanged, Spacingd
)

# Define transforms for CT preprocessing
transforms = Compose([
    LoadImaged(keys=["image"]),
    EnsureChannelFirstd(keys=["image"]),
    Spacingd(keys=["image"], pixdim=(1.0, 1.0, 1.0)),
    ScaleIntensityRanged(
        keys=["image"],
        a_min=-1000, a_max=400,
        b_min=0.0, b_max=1.0,
        clip=True
    ),
])

# Apply to IDC data
data = {"image": "./data/ct_series"}
result = transforms(data)
print(f"Processed shape: {result['image'].shape}")
```

## Pathology Slide Processing with OpenSlide

```python
import openslide
from pathlib import Path

# Open whole slide image
wsi_path = "./data/pathology/slide.svs"
slide = openslide.OpenSlide(wsi_path)

# Get slide properties
print(f"Dimensions: {slide.dimensions}")
print(f"Level count: {slide.level_count}")
print(f"Level dimensions: {slide.level_dimensions}")

# Read a region at level 0
region = slide.read_region((0, 0), 0, (512, 512))

# Read thumbnail
thumbnail = slide.get_thumbnail((1024, 1024))
thumbnail.save("slide_thumbnail.png")
```

## histolab for Tile Extraction

```python
from histolab.slide import Slide
from histolab.tiler import GridTiler

# Load slide
slide = Slide("./data/pathology/slide.svs", "./output/tiles")

# Create tiler
tiler = GridTiler(
    tile_size=(256, 256),
    level=0,
    check_tissue=True,  # Only extract tiles with tissue
    pixel_overlap=0
)

# Extract tiles
tiler.extract(slide)
```

## Batch Processing Multiple Series

```python
from idc_index import IDCClient
import pydicom
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

def process_series(series_dir):
    """Process a single DICOM series"""
    files = list(Path(series_dir).glob('*.dcm'))
    if not files:
        return None

    ds = pydicom.dcmread(str(files[0]))
    return {
        'patient_id': ds.PatientID,
        'modality': ds.Modality,
        'series_uid': ds.SeriesInstanceUID,
        'num_files': len(files)
    }

# Process all downloaded series in parallel
download_dir = Path("./data")
series_dirs = [d for d in download_dir.rglob("*") if d.is_dir() and list(d.glob("*.dcm"))]

with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_series, series_dirs))

# Filter successful results
processed = [r for r in results if r is not None]
print(f"Processed {len(processed)} series")
```

## Integration Tips

1. **Memory Management**: For large volumes, use memory-mapped arrays or process slice-by-slice
2. **Coordinate Systems**: DICOM uses LPS (Left-Posterior-Superior), NIfTI uses RAS - SimpleITK handles conversion
3. **Spacing**: Always check pixel spacing and slice thickness for proper 3D reconstruction
4. **Orientation**: Use ImageOrientationPatient and ImagePositionPatient for correct 3D alignment
5. **Window/Level**: Apply appropriate window/level for visualization (CT: lung=-600/1500, soft tissue=40/400)
