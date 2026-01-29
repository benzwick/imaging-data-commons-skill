"""
Tests for IDC SQL queries and index table access.

Run with: pytest tests/test_queries.py -v
"""

import pytest


class TestIDCClient:
    """Test IDC client initialization and basic operations."""

    def test_client_initialization(self, idc_client):
        """Test that IDC client initializes successfully."""
        assert idc_client is not None

    def test_get_idc_version(self, idc_client):
        """Test that IDC version is retrievable."""
        version = idc_client.get_idc_version()
        assert version is not None
        assert isinstance(version, str)
        assert version.startswith('v')

    def test_index_dataframe_available(self, idc_client):
        """Test that index DataFrame is accessible."""
        index = idc_client.index
        assert index is not None
        assert len(index) > 0


class TestIndexSchema:
    """Test index table schema and columns."""

    def test_index_has_expected_columns(self, idc_client, expected_index_columns):
        """Test that index contains expected columns."""
        index = idc_client.index
        for col in expected_index_columns:
            assert col in index.columns, f"Missing column: {col}"

    def test_indices_overview_available(self, idc_client):
        """Test that indices_overview provides schema information."""
        overview = idc_client.indices_overview
        assert 'index' in overview
        assert 'schema' in overview['index']
        assert 'columns' in overview['index']['schema']


class TestBasicQueries:
    """Test basic SQL query functionality."""

    def test_simple_select(self, idc_client):
        """Test simple SELECT query."""
        result = idc_client.sql_query("SELECT COUNT(*) as count FROM index")
        assert result is not None
        assert 'count' in result.columns
        assert result['count'].iloc[0] > 0

    def test_query_returns_dataframe(self, idc_client):
        """Test that queries return pandas DataFrame."""
        import pandas as pd
        result = idc_client.sql_query("SELECT * FROM index LIMIT 5")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5

    def test_modality_filter(self, idc_client, expected_modalities):
        """Test filtering by modality."""
        result = idc_client.sql_query("""
            SELECT DISTINCT Modality FROM index
        """)
        modalities = set(result['Modality'].values)
        # At least some expected modalities should be present
        assert len(modalities & set(expected_modalities)) > 0

    def test_collection_filter(self, idc_client, sample_collection):
        """Test filtering by collection."""
        result = idc_client.sql_query(f"""
            SELECT COUNT(*) as count
            FROM index
            WHERE collection_id = '{sample_collection}'
        """)
        assert result['count'].iloc[0] > 0

    def test_license_filter(self, idc_client):
        """Test filtering by license."""
        result = idc_client.sql_query("""
            SELECT DISTINCT license_short_name
            FROM index
            WHERE license_short_name IS NOT NULL
            LIMIT 10
        """)
        assert len(result) > 0
        # Check that license names exist and are non-empty strings
        for license_name in result['license_short_name']:
            assert isinstance(license_name, str) and len(license_name) > 0


class TestAggregationQueries:
    """Test aggregation and grouping queries."""

    def test_count_by_modality(self, idc_client):
        """Test counting series by modality."""
        result = idc_client.sql_query("""
            SELECT Modality, COUNT(*) as series_count
            FROM index
            GROUP BY Modality
            ORDER BY series_count DESC
            LIMIT 10
        """)
        assert 'Modality' in result.columns
        assert 'series_count' in result.columns
        assert len(result) > 0

    def test_sum_series_size(self, idc_client, sample_collection):
        """Test summing series sizes."""
        result = idc_client.sql_query(f"""
            SELECT SUM(series_size_MB) as total_mb
            FROM index
            WHERE collection_id = '{sample_collection}'
        """)
        total_mb = result['total_mb'].iloc[0]
        assert total_mb is not None
        assert total_mb > 0


class TestAdditionalIndices:
    """Test fetching and querying additional indices."""

    def test_fetch_collections_index(self, idc_client):
        """Test fetching collections_index."""
        idc_client.fetch_index("collections_index")
        result = idc_client.sql_query("""
            SELECT collection_id, CancerTypes
            FROM collections_index
            LIMIT 5
        """)
        assert len(result) > 0
        assert 'collection_id' in result.columns

    def test_fetch_analysis_results_index(self, idc_client):
        """Test fetching analysis_results_index."""
        idc_client.fetch_index("analysis_results_index")
        result = idc_client.sql_query("""
            SELECT analysis_result_id
            FROM analysis_results_index
            LIMIT 5
        """)
        assert len(result) > 0


class TestViewerURL:
    """Test viewer URL generation."""

    def test_get_viewer_url_for_series(self, idc_client, sample_series_uids):
        """Test generating viewer URL for a series."""
        if not sample_series_uids:
            pytest.skip("No sample series available")

        url = idc_client.get_viewer_URL(seriesInstanceUID=sample_series_uids[0])
        assert url is not None
        assert url.startswith('http')
        assert 'viewer' in url.lower() or 'ohif' in url.lower()
