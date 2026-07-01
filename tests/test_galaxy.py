"""Unit tests for Galaxy data source and report generator."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import requests

from src.data_sources.galaxy import GalaxyDataSource
from src.reports.galaxy import GalaxyReportGenerator


# Sample Galaxy JSON data based on real structure from research-software-ecosystem
SAMPLE_GALAXY_JSON = {
    "Suite_ID": "abricate",
    "bio.tool_name": "ABRicate",
    "Suite_runs_(usegalaxy.org.au)": 600408,
    "Suite_users_(usegalaxy.org.au)": 2216,
    "Suite_runs_(usegalaxy.eu)": 821957,
    "Suite_users_(usegalaxy.eu)": 4679,
    "Suite_runs_(usegalaxy.org)": 405363,
    "Suite_users_(usegalaxy.org)": 3468,
    "Suite_runs_(usegalaxy.fr)": 19178,
    "Suite_users_(usegalaxy.fr)": 85,
}

SAMPLE_GALAXY_INSTANCES_TSV = """instance_name\tkey_pattern\tenabled
usegalaxy.eu\t_(usegalaxy.eu)\ttrue
usegalaxy.org\t_(usegalaxy.org)\ttrue
usegalaxy.org.au\t_(usegalaxy.org.au)\ttrue
usegalaxy.fr\t_(usegalaxy.fr)\tfalse
"""


class TestGalaxyDataSource(unittest.TestCase):
    """Tests for GalaxyDataSource class."""

    def setUp(self):
        """Set up test fixtures."""
        self.project = "test_project"
        self.package = "abricate"
        self.config_content = SAMPLE_GALAXY_INSTANCES_TSV.strip()

    def test_initialization(self):
        """Test that GalaxyDataSource initializes correctly."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "galaxy_instances.tsv"
            config_path.write_text(self.config_content)

            ds = GalaxyDataSource(
                project=self.project,
                package=self.package,
                config_path=config_path,
                github_token="fake_token",
            )

            self.assertEqual(ds.project, self.project)
            self.assertEqual(ds.package, self.package)
            self.assertEqual(ds.source, "Galaxy")
            self.assertEqual(len(ds.instances), 3)  # Only enabled instances

    def test_initialization_with_missing_config(self):
        """Test initialization falls back to defaults when config is missing."""
        ds = GalaxyDataSource(
            project=self.project,
            package=self.package,
            config_path=Path("/nonexistent/path/config.tsv"),
            github_token="fake_token",
        )

        # Should fall back to default instances
        self.assertEqual(len(ds.instances), 4)
        instance_names = [inst["instance_name"] for inst in ds.instances]
        self.assertIn("usegalaxy.eu", instance_names)

    @patch("src.data_sources.galaxy.make_api_request")
    def test_fetch_runs_success(self, mock_request):
        """Test successful fetch of runs data."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_GALAXY_JSON
        mock_request.return_value = mock_response

        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "galaxy_instances.tsv"
            config_path.write_text(self.config_content)

            ds = GalaxyDataSource(
                project=self.project,
                package=self.package,
                config_path=config_path,
                github_token="fake_token",
            )

            result = ds.fetch(action="runs")

            self.assertEqual(result.status_code, 200)
            data = result.json()
            self.assertEqual(data["package"], self.package)
            self.assertEqual(data["action"], "runs")
            self.assertIn("instances", data)

            # Check extracted runs data
            self.assertEqual(data["instances"]["usegalaxy.eu"]["runs"], 821957)
            self.assertEqual(data["instances"]["usegalaxy.org"]["runs"], 405363)
            self.assertEqual(data["instances"]["usegalaxy.org.au"]["runs"], 600408)

    @patch("src.data_sources.galaxy.make_api_request")
    def test_fetch_users_success(self, mock_request):
        """Test successful fetch of users data."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_GALAXY_JSON
        mock_request.return_value = mock_response

        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "galaxy_instances.tsv"
            config_path.write_text(self.config_content)

            ds = GalaxyDataSource(
                project=self.project,
                package=self.package,
                config_path=config_path,
                github_token="fake_token",
            )

            result = ds.fetch(action="users")

            self.assertEqual(result.status_code, 200)
            data = result.json()
            self.assertEqual(data["action"], "users")

            # Check extracted users data
            self.assertEqual(data["instances"]["usegalaxy.eu"]["users"], 4679)
            self.assertEqual(data["instances"]["usegalaxy.org"]["users"], 3468)

    @patch("src.data_sources.galaxy.make_api_request")
    def test_fetch_invalid_action(self, mock_request):
        """Test that invalid action raises ValueError."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "galaxy_instances.tsv"
            config_path.write_text(self.config_content)

            ds = GalaxyDataSource(
                project=self.project,
                package=self.package,
                config_path=config_path,
                github_token="fake_token",
            )

            with self.assertRaises(ValueError):
                ds.fetch(action="invalid_action")

    @patch("src.data_sources.galaxy.make_api_request")
    def test_fetch_404_handling(self, mock_request):
        """Test handling of 404 response (missing package)."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "galaxy_instances.tsv"
            config_path.write_text(self.config_content)

            ds = GalaxyDataSource(
                project=self.project,
                package="nonexistent_package",
                config_path=config_path,
                github_token="fake_token",
            )

            result = ds.fetch(action="runs")
            self.assertEqual(result.status_code, 404)

    @patch("src.data_sources.galaxy.make_api_request")
    def test_fetch_with_zero_counts(self, mock_request):
        """Test handling of instances with zero counts."""
        # Note: key_pattern in config includes parentheses, so we need matching keys
        empty_json = {
            "Suite_ID": "empty_tool",
            "Suite_runs_(usegalaxy.eu)": 0,
            "Suite_runs_(usegalaxy.org)": 0,
            "Suite_runs_(usegalaxy.org.au)": 0,
            "Suite_users_(usegalaxy.eu)": 0,
            "Suite_users_(usegalaxy.org)": 0,
            "Suite_users_(usegalaxy.org.au)": 0,
        }

        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = empty_json
        mock_request.return_value = mock_response

        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "galaxy_instances.tsv"
            config_path.write_text(self.config_content)

            ds = GalaxyDataSource(
                project=self.project,
                package="empty_tool",
                config_path=config_path,
                github_token="fake_token",
            )

            result = ds.fetch(action="runs")
            data = result.json()
            self.assertEqual(data["instances"]["usegalaxy.eu"]["runs"], 0)
            self.assertEqual(data["instances"]["usegalaxy.org"]["runs"], 0)


class TestGalaxyReportGenerator(unittest.TestCase):
    """Tests for GalaxyReportGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = TemporaryDirectory()
        self.output_path = Path(self.tmp_dir.name) / "output" / "galaxy_runs.tsv"

    def tearDown(self):
        """Clean up temporary directory."""
        self.tmp_dir.cleanup()

    def test_get_file_pattern_runs(self):
        """Test that get_file_pattern returns correct pattern for runs."""
        generator = GalaxyReportGenerator(
            tmp_dir=Path(self.tmp_dir.name),
            output_path=self.output_path,
            stat_type="runs",
        )
        self.assertEqual(generator.get_file_pattern(), "*__Galaxy__runs.json")

    def test_get_file_pattern_users(self):
        """Test that get_file_pattern returns correct pattern for users."""
        generator = GalaxyReportGenerator(
            tmp_dir=Path(self.tmp_dir.name),
            output_path=self.output_path,
            stat_type="users",
        )
        self.assertEqual(generator.get_file_pattern(), "*__Galaxy__users.json")

    def test_get_period_key(self):
        """Test period key generation."""
        generator = GalaxyReportGenerator(
            tmp_dir=Path(self.tmp_dir.name),
            output_path=self.output_path,
            stat_type="runs",
        )

        from datetime import datetime

        date = datetime(2025, 3, 15)
        self.assertEqual(generator.get_period_key(date), "2025-03")

    def test_get_period_label(self):
        """Test period label returns 'month'."""
        generator = GalaxyReportGenerator(
            tmp_dir=Path(self.tmp_dir.name),
            output_path=self.output_path,
            stat_type="runs",
        )
        self.assertEqual(generator.get_period_label(), "month")

    def test_aggregate_data(self):
        """Test aggregation of Galaxy statistics."""
        generator = GalaxyReportGenerator(
            tmp_dir=Path(self.tmp_dir.name),
            stat_type="runs",
            output_path=self.output_path,
        )

        # Create a test JSON file
        test_data = {
            "package": "abricate",
            "project": "test_project",
            "source": "Galaxy",
            "action": "runs",
            "instances": {
                "usegalaxy.eu": {"runs": 100},
                "usegalaxy.org": {"runs": 200},
                "usegalaxy.org.au": {"runs": 50},
            },
        }

        test_file = (
            Path(self.tmp_dir.name)
            / "2025-01-15_12-00-00__test_project__abricate__Galaxy__runs.json"
        )
        test_file.write_text(json.dumps(test_data))

        result = generator.aggregate_data(test_file)

        # Should sum all instances: 100 + 200 + 50 = 350
        self.assertIn("2025-01", result)
        self.assertEqual(result["2025-01"][0], 350)
        self.assertTrue(result["2025-01"][1])  # is_complete

    def test_aggregate_data_empty_instances(self):
        """Test aggregation with no instances."""
        generator = GalaxyReportGenerator(
            tmp_dir=Path(self.tmp_dir.name),
            stat_type="runs",
            output_path=self.output_path,
        )

        test_data = {
            "package": "empty_tool",
            "project": "test_project",
            "source": "Galaxy",
            "action": "runs",
            "instances": {},
        }

        test_file = (
            Path(self.tmp_dir.name)
            / "2025-01-15_12-00-00__test_project__empty_tool__Galaxy__runs.json"
        )
        test_file.write_text(json.dumps(test_data))

        result = generator.aggregate_data(test_file)
        self.assertIn("2025-01", result)
        self.assertEqual(result["2025-01"][0], 0)

    def test_get_latest_files(self):
        """Test finding latest files per project/package."""
        generator = GalaxyReportGenerator(
            tmp_dir=Path(self.tmp_dir.name),
            stat_type="runs",
            output_path=self.output_path,
        )

        # Create multiple test files
        test_data = {
            "package": "abricate",
            "project": "test_project",
            "source": "Galaxy",
            "action": "runs",
            "instances": {"usegalaxy.eu": {"runs": 100}},
        }

        # Older file
        old_file = (
            Path(self.tmp_dir.name)
            / "2025-01-01_12-00-00__test_project__abricate__Galaxy__runs.json"
        )
        old_file.write_text(json.dumps(test_data))

        # Newer file
        new_file = (
            Path(self.tmp_dir.name)
            / "2025-02-01_12-00-00__test_project__abricate__Galaxy__runs.json"
        )
        new_file.write_text(json.dumps(test_data))

        latest = generator.get_latest_files()
        key = "abricate_runs"

        self.assertIn(key, latest)
        self.assertEqual(latest[key].name, new_file.name)

    def test_get_latest_files_excludes_metadata(self):
        """Test that metadata sidecar files are excluded."""
        generator = GalaxyReportGenerator(
            tmp_dir=Path(self.tmp_dir.name),
            output_path=self.output_path,
        )

        test_data = {
            "package": "abricate",
            "project": "test_project",
            "source": "Galaxy",
            "action": "runs",
            "instances": {"usegalaxy.eu": {"runs": 100}},
        }

        data_file = (
            Path(self.tmp_dir.name)
            / "2025-02-01_12-00-00__test_project__abricate__Galaxy__runs.json"
        )
        data_file.write_text(json.dumps(test_data))

        metadata_file = (
            Path(self.tmp_dir.name)
            / "2025-03-01_12-00-00__test_project__abricate__Galaxy__runs.metadata.json"
        )
        metadata_file.write_text(json.dumps({"status": "ok"}))

        latest = generator.get_latest_files()

        self.assertIn("abricate_runs", latest)
        self.assertEqual(latest["abricate_runs"].name, data_file.name)
        self.assertNotIn("abricate_runs.metadata", latest)


class TestGalaxyIntegration(unittest.TestCase):
    """Integration tests for Galaxy functionality."""

    @patch("src.data_sources.galaxy.make_api_request")
    def test_fetch_and_extract(self, mock_request):
        """Test that fetch correctly extracts data from Galaxy JSON."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_GALAXY_JSON
        mock_request.return_value = mock_response

        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_path = tmp_path / "galaxy_instances.tsv"
            config_path.write_text(SAMPLE_GALAXY_INSTANCES_TSV.strip())

            # Create data source
            ds = GalaxyDataSource(
                project="integration_test",
                package="abricate",
                config_path=config_path,
                github_token="fake_token",
            )

            # Fetch runs
            result = ds.fetch("runs")
            data = result.json()

            # Verify extracted data structure
            self.assertEqual(data["action"], "runs")
            self.assertEqual(data["package"], "abricate")
            self.assertIn("instances", data)

            # Verify instance data
            self.assertEqual(data["instances"]["usegalaxy.eu"]["runs"], 821957)
            self.assertEqual(data["instances"]["usegalaxy.org"]["runs"], 405363)
            self.assertEqual(data["instances"]["usegalaxy.org.au"]["runs"], 600408)

            # Fetch users
            result = ds.fetch("users")
            data = result.json()

            self.assertEqual(data["action"], "users")
            self.assertEqual(data["instances"]["usegalaxy.eu"]["users"], 4679)


if __name__ == "__main__":
    unittest.main()
