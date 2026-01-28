"""
Tests for DICOM validation utilities.

Run with: pytest tests/test_validation.py -v
"""

import pytest
import tempfile
from pathlib import Path
import sys

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestValidatorImport:
    """Test that validation module can be imported."""

    def test_import_validator(self):
        """Test importing the validator module."""
        try:
            from validate_download import DicomValidator
            assert DicomValidator is not None
        except ImportError as e:
            pytest.skip(f"Could not import validator: {e}")


class TestValidatorInitialization:
    """Test validator initialization."""

    def test_validator_with_temp_dir(self):
        """Test creating validator with temporary directory."""
        from validate_download import DicomValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            validator = DicomValidator(tmpdir)
            assert validator.download_dir == Path(tmpdir)

    def test_find_empty_directory(self):
        """Test finding series in empty directory."""
        from validate_download import DicomValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            validator = DicomValidator(tmpdir)
            series_dirs = validator.find_series_directories()
            assert series_dirs == []


class TestValidationResults:
    """Test validation result handling."""

    def test_generate_report_empty(self):
        """Test generating report with empty results."""
        from validate_download import DicomValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            validator = DicomValidator(tmpdir)
            report = validator.generate_report([])
            assert report['total_series'] == 0
            assert report['valid'] == 0

    def test_generate_report_with_results(self):
        """Test generating report with mock results."""
        from validate_download import DicomValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            validator = DicomValidator(tmpdir)

            mock_results = [
                {'status': 'VALID', 'total_files': 100, 'valid_files': 100},
                {'status': 'VALID', 'total_files': 50, 'valid_files': 50},
                {'status': 'CORRUPTED', 'total_files': 10, 'valid_files': 0},
            ]

            report = validator.generate_report(mock_results)
            assert report['total_series'] == 3
            assert report['valid'] == 2
            assert report['corrupted'] == 1
            assert report['total_files'] == 160
            assert report['valid_files'] == 150


class TestBatchDownloaderImport:
    """Test that batch downloader module can be imported."""

    def test_import_batch_downloader(self):
        """Test importing the batch downloader module."""
        try:
            from batch_download import BatchDownloader
            assert BatchDownloader is not None
        except ImportError as e:
            pytest.skip(f"Could not import batch downloader: {e}")


class TestBatchDownloaderInitialization:
    """Test batch downloader initialization."""

    def test_downloader_with_temp_dir(self):
        """Test creating downloader with temporary directory."""
        from batch_download import BatchDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = BatchDownloader(tmpdir)
            assert downloader.output_dir == Path(tmpdir)
            assert downloader.batch_size == 20  # default

    def test_downloader_custom_batch_size(self):
        """Test creating downloader with custom batch size."""
        from batch_download import BatchDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = BatchDownloader(tmpdir, batch_size=50)
            assert downloader.batch_size == 50


class TestProgressTracking:
    """Test download progress tracking."""

    def test_save_and_load_progress(self):
        """Test saving and loading download progress."""
        from batch_download import BatchDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = BatchDownloader(tmpdir)

            # Save progress
            test_uids = {'uid1', 'uid2', 'uid3'}
            downloader.save_progress(test_uids)

            # Load progress
            loaded = downloader.load_progress()
            assert loaded == test_uids

    def test_empty_progress(self):
        """Test loading progress when no file exists."""
        from batch_download import BatchDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = BatchDownloader(tmpdir)
            progress = downloader.load_progress()
            assert progress == set()


class TestDiskSpaceCheck:
    """Test disk space checking functionality."""

    def test_check_disk_space_small_requirement(self):
        """Test disk space check with small requirement."""
        from batch_download import BatchDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = BatchDownloader(tmpdir)
            # 1 MB should always be available
            assert downloader.check_disk_space(1) is True

    def test_check_disk_space_huge_requirement(self):
        """Test disk space check with unrealistic requirement."""
        from batch_download import BatchDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = BatchDownloader(tmpdir)
            # 1 PB should not be available
            assert downloader.check_disk_space(1024 * 1024 * 1024 * 1024) is False
