import unittest
from unittest.mock import MagicMock, mock_open, patch
import orjson
import pandas as pd
import requests
from src.data_sources.base import DataSource


class ConcreteDataSource(DataSource):
    """Concrete implementation of DataSource for testing."""
    
    def fetch(self, action: str = None, **kwargs):
        """Mock fetch implementation."""
        return MagicMock()


class TestDataSource(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.project = "test_project"
        self.package = "test_package"
        self.source = "test_source"
        self.ds = ConcreteDataSource(self.project, self.package, self.source)

    def test_initialization(self):
        """Test that DataSource initializes correctly."""
        self.assertEqual(self.ds.project, self.project)
        self.assertEqual(self.ds.package, self.package)
        self.assertEqual(self.ds.source, self.source)

    @patch("src.data_sources.base.datetime")
    def test_prep_filename(self, mock_datetime):
        """Test prep_filename method."""
        # Mock the current date
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2023-01-01_12-00-00"
        mock_datetime.now.return_value = mock_now

        folder = "tmp"
        action = "downloads"

        result = self.ds.prep_filename(folder, action)

        expected_filename = (
            "tmp/2023-01-01_12-00-00__test_project__test_package__test_source__downloads.json"
        )
        self.assertEqual(result, expected_filename)

    @patch("src.data_sources.base.datetime")
    def test_prep_filename_with_special_characters(self, mock_datetime):
        """Test prep_filename with special characters in project/package names."""
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2023-01-01_12-00-00"
        mock_datetime.now.return_value = mock_now

        ds = ConcreteDataSource("project@name", "package name!", "source#test")
        result = ds.prep_filename("tmp", "action test")

        expected_filename = (
            "tmp/2023-01-01_12-00-00__project_name__package_name___source_test__action_test.json"
        )
        self.assertEqual(result, expected_filename)

    @patch("builtins.open", new_callable=mock_open)
    def test_write_prep_filename_metadata(self, mock_file_open):
        """Test write_prep_filename_metadata method."""
        action = "downloads"
        filename = "tmp/test_file.json"

        self.ds.write_prep_filename_metadata(action, filename)

        # Expected metadata
        expected_metadata = {
            "project": self.project,
            "package": self.package,
            "source": self.source,
            "action": action,
            "filename": filename,
        }

        # Verify the file was opened correctly
        metadata_filename = "tmp/test_file.metadata.json"
        mock_file_open.assert_called_once_with(metadata_filename, "wb")

        # Get what was written
        handle = mock_file_open()
        written_data = b"".join(call[0][0] for call in handle.write.call_args_list)
        
        # Parse and verify the written metadata
        parsed_metadata = orjson.loads(written_data)
        self.assertEqual(parsed_metadata, expected_metadata)

    @patch("src.data_sources.base.write_json")
    def test_write_stats_response_with_requests_response(self, mock_write_json):
        """Test write_stats_response with requests.Response object."""
        # Create an actual requests.Response object for type checking to work
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = b'{"count": 100}'
        
        with patch.object(self.ds, 'prep_filename', return_value='test_file.json'):
            with patch.object(self.ds, 'write_prep_filename_metadata'):
                self.ds.write_stats_response(mock_response, "downloads")
        
        # Verify write_json was called with the JSON data
        mock_write_json.assert_called_once()
        call_args = mock_write_json.call_args[0]
        self.assertEqual(call_args[0], {"count": 100})
        self.assertEqual(call_args[1], "test_file.json")

    @patch("src.data_sources.base.write_json")
    def test_write_stats_response_with_pandas_series(self, mock_write_json):
        """Test write_stats_response with pandas Series object."""
        # Create a pandas Series
        test_series = pd.Series({"2023-01": 100, "2023-02": 200})
        
        with patch.object(self.ds, 'prep_filename', return_value='test_file.json'):
            with patch.object(self.ds, 'write_prep_filename_metadata'):
                self.ds.write_stats_response(test_series, "downloads")
        
        # Verify write_json was called with the dict data
        mock_write_json.assert_called_once()
        call_args = mock_write_json.call_args[0]
        self.assertIsInstance(call_args[0], dict)
        self.assertEqual(call_args[1], "test_file.json")

    @patch("src.data_sources.base.write_json")
    @patch("src.data_sources.base.logger")
    def test_write_stats_response_with_unexpected_type(self, mock_logger, mock_write_json):
        """Test write_stats_response with unexpected result type."""
        # Create an object that's neither Response nor Series
        unexpected_result = MagicMock()
        unexpected_result.response_type = "unknown"
        
        with patch.object(self.ds, 'prep_filename', return_value='failed/test_file.json'):
            with patch.object(self.ds, 'write_prep_filename_metadata'):
                self.ds.write_stats_response(unexpected_result, "downloads")
        
        # Verify error was logged
        mock_logger.error.assert_called()

    @patch.object(ConcreteDataSource, 'fetch')
    @patch.object(DataSource, 'write_stats_response')
    def test_process(self, mock_write_stats, mock_fetch):
        """Test process method orchestration."""
        mock_result = MagicMock()
        mock_fetch.return_value = mock_result
        
        self.ds.process("downloads")
        
        # Verify fetch was called with correct action
        mock_fetch.assert_called_once_with(action="downloads")
        
        # Verify write_stats_response was called with the result
        mock_write_stats.assert_called_once_with(mock_result, "downloads")

    @patch.object(ConcreteDataSource, 'fetch')
    @patch("src.data_sources.base.logger")
    def test_process_with_exception(self, mock_logger, mock_fetch):
        """Test process method handles exceptions."""
        mock_fetch.side_effect = Exception("Test error")
        
        with self.assertRaises(Exception):
            self.ds.process("downloads")
        
        # Verify error was logged
        mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
