#!/usr/bin/env python3
"""
Validation utility for downloaded IDC DICOM data.

Usage:
    python validate_download.py --dir ./data
    python validate_download.py --dir ./data --manifest manifest.csv
    python validate_download.py --dir ./data --check-geometry
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

try:
    import pydicom
    import pandas as pd
except ImportError:
    print("Error: Required packages not installed.")
    print("Install with: pip install pydicom pandas")
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DicomValidator:
    """Validate downloaded DICOM data integrity and completeness."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.results = []

    def find_series_directories(self) -> list:
        """Find all directories containing DICOM files."""
        series_dirs = []
        for path in self.download_dir.rglob('*.dcm'):
            series_dir = path.parent
            if series_dir not in series_dirs:
                series_dirs.append(series_dir)
        return series_dirs

    def validate_dicom_file(self, filepath: Path) -> dict:
        """Validate a single DICOM file."""
        try:
            ds = pydicom.dcmread(str(filepath))
            result = {
                'valid': True,
                'series_uid': ds.SeriesInstanceUID,
                'modality': ds.Modality,
                'has_pixels': hasattr(ds, 'PixelData')
            }

            # Try to access pixel array for image modalities
            if result['has_pixels'] and ds.Modality in ['CT', 'MR', 'PT', 'CR', 'DX', 'SM']:
                try:
                    _ = ds.pixel_array
                    result['pixels_readable'] = True
                except Exception as e:
                    result['pixels_readable'] = False
                    result['pixel_error'] = str(e)

            return result

        except pydicom.errors.InvalidDicomError as e:
            return {'valid': False, 'error': f'Invalid DICOM: {e}'}
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    def validate_series(self, series_dir: Path, check_geometry: bool = False) -> dict:
        """Validate all DICOM files in a series directory."""
        dcm_files = list(series_dir.glob('*.dcm'))

        if not dcm_files:
            return {
                'directory': str(series_dir),
                'status': 'EMPTY',
                'error': 'No DICOM files found'
            }

        result = {
            'directory': str(series_dir),
            'total_files': len(dcm_files),
            'valid_files': 0,
            'corrupted_files': [],
            'series_uid': None,
            'modality': None
        }

        # Validate each file
        for f in dcm_files:
            file_result = self.validate_dicom_file(f)
            if file_result['valid']:
                result['valid_files'] += 1
                if result['series_uid'] is None:
                    result['series_uid'] = file_result.get('series_uid')
                    result['modality'] = file_result.get('modality')
            else:
                result['corrupted_files'].append({
                    'file': f.name,
                    'error': file_result.get('error')
                })

        # Determine status
        if result['valid_files'] == result['total_files']:
            result['status'] = 'VALID'
        elif result['valid_files'] > 0:
            result['status'] = 'PARTIAL'
        else:
            result['status'] = 'CORRUPTED'

        # Check geometry for CT series
        if check_geometry and result['modality'] == 'CT' and result['status'] == 'VALID':
            geometry = self.check_ct_geometry(series_dir)
            result['geometry'] = geometry
            if not geometry['valid']:
                result['status'] = 'GEOMETRY_ISSUE'

        return result

    def check_ct_geometry(self, series_dir: Path) -> dict:
        """Check CT series geometry consistency."""
        dcm_files = sorted(series_dir.glob('*.dcm'))

        if len(dcm_files) < 2:
            return {'valid': True, 'note': 'Single slice series'}

        slices = []
        for f in dcm_files:
            try:
                ds = pydicom.dcmread(str(f))
                slices.append({
                    'rows': ds.Rows,
                    'cols': ds.Columns,
                    'spacing': list(ds.PixelSpacing) if hasattr(ds, 'PixelSpacing') else None,
                    'position': list(ds.ImagePositionPatient) if hasattr(ds, 'ImagePositionPatient') else None
                })
            except Exception:
                continue

        issues = []

        # Check consistent dimensions
        rows = set(s['rows'] for s in slices if s['rows'])
        cols = set(s['cols'] for s in slices if s['cols'])
        if len(rows) > 1:
            issues.append(f"Inconsistent rows: {rows}")
        if len(cols) > 1:
            issues.append(f"Inconsistent columns: {cols}")

        # Check consistent spacing
        spacings = set(tuple(s['spacing']) for s in slices if s['spacing'])
        if len(spacings) > 1:
            issues.append(f"Inconsistent pixel spacing")

        return {
            'valid': len(issues) == 0,
            'num_slices': len(slices),
            'dimensions': (list(rows)[0] if rows else None, list(cols)[0] if cols else None),
            'issues': issues
        }

    def validate_against_manifest(self, manifest_path: str) -> list:
        """Validate downloads against a manifest file."""
        manifest = pd.read_csv(manifest_path)

        if 'SeriesInstanceUID' not in manifest.columns:
            raise ValueError("Manifest must contain SeriesInstanceUID column")

        results = []
        for _, row in manifest.iterrows():
            series_uid = row['SeriesInstanceUID']
            expected_count = row.get('instanceCount', None)

            # Find series directory
            matches = list(self.download_dir.rglob(f"*{series_uid[-12:]}*"))
            series_dirs = [m for m in matches if m.is_dir() and list(m.glob('*.dcm'))]

            if not series_dirs:
                results.append({
                    'series_uid': series_uid,
                    'status': 'NOT_FOUND',
                    'expected_count': expected_count
                })
                continue

            # Validate the series
            validation = self.validate_series(series_dirs[0])
            validation['series_uid'] = series_uid
            validation['expected_count'] = expected_count

            if expected_count and validation['valid_files'] != expected_count:
                validation['status'] = 'INCOMPLETE'
                validation['missing'] = expected_count - validation['valid_files']

            results.append(validation)

        return results

    def validate_all(self, check_geometry: bool = False) -> list:
        """Validate all series in download directory."""
        series_dirs = self.find_series_directories()
        logger.info(f"Found {len(series_dirs)} series directories")

        results = []
        for i, series_dir in enumerate(series_dirs, 1):
            logger.info(f"Validating {i}/{len(series_dirs)}: {series_dir.name}")
            result = self.validate_series(series_dir, check_geometry)
            results.append(result)

        return results

    def generate_report(self, results: list) -> dict:
        """Generate summary report from validation results."""
        summary = {
            'total_series': len(results),
            'valid': 0,
            'partial': 0,
            'corrupted': 0,
            'not_found': 0,
            'incomplete': 0,
            'geometry_issues': 0,
            'total_files': 0,
            'valid_files': 0
        }

        for r in results:
            status = r.get('status', 'UNKNOWN')
            summary[status.lower()] = summary.get(status.lower(), 0) + 1
            summary['total_files'] += r.get('total_files', 0)
            summary['valid_files'] += r.get('valid_files', 0)

        summary['validation_rate'] = (
            f"{summary['valid_files']}/{summary['total_files']}"
            if summary['total_files'] > 0 else "N/A"
        )

        return summary


def main():
    parser = argparse.ArgumentParser(
        description='Validate downloaded IDC DICOM data'
    )

    parser.add_argument('--dir', '-d', type=str, required=True,
                       help='Download directory to validate')
    parser.add_argument('--manifest', '-m', type=str,
                       help='CSV manifest to validate against')
    parser.add_argument('--check-geometry', action='store_true',
                       help='Check CT series geometry consistency')
    parser.add_argument('--output', '-o', type=str,
                       help='Output file for detailed JSON report')

    args = parser.parse_args()

    validator = DicomValidator(args.dir)

    # Run validation
    if args.manifest:
        logger.info(f"Validating against manifest: {args.manifest}")
        results = validator.validate_against_manifest(args.manifest)
    else:
        logger.info(f"Validating all series in: {args.dir}")
        results = validator.validate_all(args.check_geometry)

    # Generate report
    summary = validator.generate_report(results)

    # Print summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print("=" * 50)

    # List problematic series
    problems = [r for r in results if r.get('status') not in ['VALID', None]]
    if problems:
        print(f"\nProblematic series ({len(problems)}):")
        for p in problems[:10]:  # Show first 10
            print(f"  [{p.get('status')}] {p.get('series_uid', p.get('directory', 'unknown'))}")
        if len(problems) > 10:
            print(f"  ... and {len(problems) - 10} more")

    # Save detailed report
    if args.output:
        report = {
            'timestamp': datetime.now().isoformat(),
            'download_dir': args.dir,
            'manifest': args.manifest,
            'summary': summary,
            'results': results
        }
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed report saved to: {args.output}")

    # Exit with error code if validation failed
    if summary['valid'] < summary['total_series']:
        sys.exit(1)


if __name__ == '__main__':
    main()
