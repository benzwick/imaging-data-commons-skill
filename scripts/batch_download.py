#!/usr/bin/env python3
"""
Batch download utility for IDC data with progress tracking and resume capability.

Usage:
    python batch_download.py --query "SELECT SeriesInstanceUID FROM index WHERE collection_id='nlst' LIMIT 100" --output ./data
    python batch_download.py --manifest manifest.csv --output ./data
    python batch_download.py --collection rider_pilot --output ./data
"""

import argparse
import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from idc_index import IDCClient
    import pandas as pd
except ImportError:
    print("Error: Required packages not installed.")
    print("Install with: pip install idc-index pandas")
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchDownloader:
    """Memory-efficient batch downloader for IDC data."""

    def __init__(self, output_dir: str, batch_size: int = 20,
                 dir_template: str = "%collection_id/%PatientID/%Modality_%SeriesInstanceUID"):
        self.client = IDCClient()
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        self.dir_template = dir_template
        self.progress_file = self.output_dir / ".download_progress.json"

    def get_series_from_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return series to download."""
        logger.info("Executing query...")
        results = self.client.sql_query(query)

        if 'SeriesInstanceUID' not in results.columns:
            raise ValueError("Query must return SeriesInstanceUID column")

        logger.info(f"Query returned {len(results)} series")
        return results

    def get_series_from_manifest(self, manifest_path: str) -> pd.DataFrame:
        """Load series from CSV manifest file."""
        logger.info(f"Loading manifest from {manifest_path}")
        df = pd.read_csv(manifest_path)

        if 'SeriesInstanceUID' not in df.columns:
            raise ValueError("Manifest must contain SeriesInstanceUID column")

        logger.info(f"Manifest contains {len(df)} series")
        return df

    def get_series_from_collection(self, collection_id: str) -> pd.DataFrame:
        """Get all series from a collection."""
        query = f"""
            SELECT SeriesInstanceUID, series_size_MB, instanceCount
            FROM index
            WHERE collection_id = '{collection_id}'
        """
        return self.get_series_from_query(query)

    def estimate_download_size(self, series_df: pd.DataFrame) -> dict:
        """Estimate total download size."""
        if 'series_size_MB' in series_df.columns:
            total_mb = series_df['series_size_MB'].sum()
        else:
            # Query for sizes if not in DataFrame
            uids = "', '".join(series_df['SeriesInstanceUID'].values)
            size_query = f"""
                SELECT SUM(series_size_MB) as total_mb
                FROM index
                WHERE SeriesInstanceUID IN ('{uids}')
            """
            result = self.client.sql_query(size_query)
            total_mb = result['total_mb'].iloc[0] if not result.empty else 0

        return {
            'series_count': len(series_df),
            'total_mb': round(total_mb, 2),
            'total_gb': round(total_mb / 1024, 2)
        }

    def check_disk_space(self, required_mb: float) -> bool:
        """Check if sufficient disk space is available."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        free_mb = shutil.disk_usage(self.output_dir).free / (1024 * 1024)
        # Require 1.5x the estimated size for safety
        required_with_buffer = required_mb * 1.5

        logger.info(f"Required: {required_mb:.1f} MB (with buffer: {required_with_buffer:.1f} MB)")
        logger.info(f"Available: {free_mb:.1f} MB")

        return free_mb >= required_with_buffer

    def load_progress(self) -> set:
        """Load previously downloaded series UIDs."""
        if self.progress_file.exists():
            with open(self.progress_file) as f:
                data = json.load(f)
                return set(data.get('completed', []))
        return set()

    def save_progress(self, completed: set):
        """Save download progress."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump({
                'completed': list(completed),
                'last_updated': datetime.now().isoformat()
            }, f)

    def download(self, series_df: pd.DataFrame, resume: bool = True,
                 dry_run: bool = False) -> dict:
        """
        Download series in batches with progress tracking.

        Args:
            series_df: DataFrame with SeriesInstanceUID column
            resume: Skip previously downloaded series
            dry_run: Only show what would be downloaded

        Returns:
            dict with download statistics
        """
        all_uids = set(series_df['SeriesInstanceUID'].values)

        # Filter out already downloaded
        completed = self.load_progress() if resume else set()
        remaining = all_uids - completed
        skipped = len(all_uids) - len(remaining)

        if skipped > 0:
            logger.info(f"Skipping {skipped} previously downloaded series")

        if not remaining:
            logger.info("All series already downloaded")
            return {'downloaded': 0, 'skipped': skipped, 'failed': 0}

        # Estimate size for remaining
        remaining_df = series_df[series_df['SeriesInstanceUID'].isin(remaining)]
        size_info = self.estimate_download_size(remaining_df)

        logger.info(f"To download: {size_info['series_count']} series ({size_info['total_gb']:.2f} GB)")

        if dry_run:
            logger.info("Dry run - no files will be downloaded")
            return {'to_download': size_info['series_count'], 'size_gb': size_info['total_gb']}

        # Check disk space
        if not self.check_disk_space(size_info['total_mb']):
            raise RuntimeError("Insufficient disk space")

        # Download in batches
        remaining_list = list(remaining)
        total_batches = (len(remaining_list) + self.batch_size - 1) // self.batch_size
        downloaded = 0
        failed = []

        for i in range(0, len(remaining_list), self.batch_size):
            batch = remaining_list[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1

            logger.info(f"Batch {batch_num}/{total_batches}: {len(batch)} series")

            try:
                self.client.download_from_selection(
                    seriesInstanceUID=batch,
                    downloadDir=str(self.output_dir),
                    dirTemplate=self.dir_template
                )

                # Update progress
                completed.update(batch)
                self.save_progress(completed)
                downloaded += len(batch)

                logger.info(f"Batch {batch_num} complete. Total: {downloaded}/{len(remaining_list)}")

            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                failed.extend(batch)

            # Brief pause between batches
            if batch_num < total_batches:
                time.sleep(1)

        return {
            'downloaded': downloaded,
            'skipped': skipped,
            'failed': len(failed),
            'failed_uids': failed if failed else None
        }


def main():
    parser = argparse.ArgumentParser(
        description='Batch download IDC data with progress tracking'
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--query', type=str,
                            help='SQL query returning SeriesInstanceUID')
    input_group.add_argument('--manifest', type=str,
                            help='CSV file with SeriesInstanceUID column')
    input_group.add_argument('--collection', type=str,
                            help='Collection ID to download')

    # Output options
    parser.add_argument('--output', '-o', type=str, required=True,
                       help='Output directory')
    parser.add_argument('--dir-template', type=str,
                       default='%collection_id/%PatientID/%Modality_%SeriesInstanceUID',
                       help='Directory template for organizing downloads')

    # Download options
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Number of series per batch (default: 20)')
    parser.add_argument('--no-resume', action='store_true',
                       help='Start fresh, ignore previous progress')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be downloaded without downloading')

    args = parser.parse_args()

    # Initialize downloader
    downloader = BatchDownloader(
        output_dir=args.output,
        batch_size=args.batch_size,
        dir_template=args.dir_template
    )

    # Get series to download
    if args.query:
        series_df = downloader.get_series_from_query(args.query)
    elif args.manifest:
        series_df = downloader.get_series_from_manifest(args.manifest)
    else:
        series_df = downloader.get_series_from_collection(args.collection)

    # Download
    result = downloader.download(
        series_df,
        resume=not args.no_resume,
        dry_run=args.dry_run
    )

    # Report
    print("\n--- Download Summary ---")
    for key, value in result.items():
        if value is not None and key != 'failed_uids':
            print(f"{key}: {value}")

    if result.get('failed_uids'):
        failed_file = Path(args.output) / 'failed_series.txt'
        with open(failed_file, 'w') as f:
            f.write('\n'.join(result['failed_uids']))
        print(f"Failed UIDs saved to: {failed_file}")


if __name__ == '__main__':
    main()
