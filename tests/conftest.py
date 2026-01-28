"""
Pytest configuration and fixtures for IDC skill tests.
"""

import pytest


@pytest.fixture(scope="session")
def idc_client():
    """Create IDC client for session-scoped tests."""
    try:
        from idc_index import IDCClient
        client = IDCClient()
        yield client
    except ImportError:
        pytest.skip("idc-index not installed")


@pytest.fixture
def sample_series_uids(idc_client):
    """Get a few sample series UIDs for testing."""
    result = idc_client.sql_query("""
        SELECT SeriesInstanceUID
        FROM index
        WHERE collection_id = 'rider_pilot'
        LIMIT 3
    """)
    return list(result['SeriesInstanceUID'].values)


@pytest.fixture
def sample_collection():
    """A small collection suitable for testing."""
    return "rider_pilot"


@pytest.fixture
def expected_modalities():
    """Known modalities in IDC."""
    return ['CT', 'MR', 'PT', 'SM', 'SEG', 'RTSTRUCT', 'SR', 'CR', 'DX']


@pytest.fixture
def expected_index_columns():
    """Expected columns in the primary index table."""
    return [
        'collection_id',
        'PatientID',
        'StudyInstanceUID',
        'SeriesInstanceUID',
        'Modality',
        'BodyPartExamined',
        'series_size_MB',
        'instanceCount',
        'license_short_name'
    ]
