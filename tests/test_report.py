import csv
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

import orjson

from src.reports.github import GitHubReportGenerator
from src.utils import write_json


class TestReportPreservesExistingPeriods(unittest.TestCase):
    """Regression tests for https://github.com/RECETOX/specdatri_reporting/issues/12.

    Each weekly GitHub Action run only retrieves the last 14 days of traffic data.
    Older periods that are no longer returned by the API must be preserved from the
    existing report rather than silently dropped.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()
        self.output_file = Path(self.output_dir) / "github_clones.tsv"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)
        shutil.rmtree(self.output_dir)

    def _write_github_json(self, filename, stat_type, entries):
        """Write a GitHub API traffic response JSON file into tmp_dir."""
        data = {stat_type: entries}
        with open(os.path.join(self.tmp_dir, filename), "w") as f:
            json.dump(data, f)

    def _write_existing_report(self, periods_data):
        """Write a TSV report with the given {week: {package: count}} data."""
        packages = sorted({p for row in periods_data.values() for p in row})
        with open(self.output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["week"] + packages)
            for period, row in sorted(periods_data.items()):
                writer.writerow([period] + [row.get(p, "") for p in packages])

    def _read_report_weeks(self):
        """Return the list of week values from the written report."""
        with open(self.output_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            return [row["week"] for row in reader]

    def test_oldest_period_preserved_after_api_window_moves(self):
        """The oldest week in the report must not be dropped when the GitHub API
        no longer returns it (14-day rolling window moved forward).

        Scenario (mimics the observed weekly Action behaviour):
          - Existing report contains W07 and W08.
          - New API response only covers W08 and W09 (W07 has aged out of the window).
          - After regeneration W07 must still be present in the report.
        """
        year = 2026
        stat_type = "clones"
        package = "mypkg"

        # Existing report: W07 and W08 are already recorded.
        self._write_existing_report(
            {
                "2026-W07": {package: 10},
                "2026-W08": {package: 8},
            }
        )

        # New API file (dated 2026-03-02): coverage window is Feb 16 – Mar 02.
        # W07 (Feb 9-15) has fallen outside the window; only W08 and W09 data present.
        filename = f"2026-03-02_00-00-00__myproject__{package}__github__{stat_type}.json"
        self._write_github_json(
            filename,
            stat_type,
            [
                # W08 days (within coverage window)
                {"timestamp": "2026-02-16T00:00:00Z", "count": 5, "uniques": 5},
                {"timestamp": "2026-02-17T00:00:00Z", "count": 3, "uniques": 3},
                # W09 days (within coverage window)
                {"timestamp": "2026-02-23T00:00:00Z", "count": 7, "uniques": 7},
                {"timestamp": "2026-02-24T00:00:00Z", "count": 2, "uniques": 2},
            ],
        )

        generator = GitHubReportGenerator(
            Path(self.tmp_dir), self.output_file, year, stat_type
        )
        generator.create_report(year=year)

        weeks = self._read_report_weeks()

        self.assertIn("2026-W07", weeks, "Oldest existing week must be preserved")
        self.assertIn("2026-W08", weeks)
        self.assertIn("2026-W09", weeks)

    def test_oldest_period_value_preserved(self):
        """The data value for the oldest week must remain correct after regeneration."""
        year = 2026
        stat_type = "clones"
        package = "mypkg"

        self._write_existing_report({"2026-W07": {package: 42}})

        filename = f"2026-03-02_00-00-00__myproject__{package}__github__{stat_type}.json"
        self._write_github_json(
            filename,
            stat_type,
            [{"timestamp": "2026-02-23T00:00:00Z", "count": 5, "uniques": 5}],
        )

        generator = GitHubReportGenerator(
            Path(self.tmp_dir), self.output_file, year, stat_type
        )
        generator.create_report(year=year)

        with open(self.output_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            rows = {row["week"]: row for row in reader}

        self.assertIn("2026-W07", rows)
        self.assertEqual(rows["2026-W07"][package], "42")


class TestReports(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.utils.orjson.dumps")
    def test_write_json(self, mock_dumps, mock_open):
        # Mock the return value of orjson.dumps
        mock_dumps.return_value = b'{"key": "value"}'

        # Data to be serialized
        data = {"key": "value"}
        filename = "test.json"

        # Call the function
        write_json(data, filename)

        # Assert that orjson.dumps was called with the correct data and options
        mock_dumps.assert_called_once_with(data, option=orjson.OPT_INDENT_2)

        # Assert that the file was opened in binary write mode
        mock_open.assert_called_once_with(filename, "wb")

        # Assert that the data was written to the file
        mock_open().write.assert_called_once_with(b'{"key": "value"}')


if __name__ == "__main__":
    unittest.main()
