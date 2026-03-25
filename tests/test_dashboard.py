"""Tests for the dashboard generator module."""

import shutil
import tempfile
import unittest
from pathlib import Path

from src.dashboard import generate_dashboard, load_all_data, load_tsv


class TestLoadTsv(unittest.TestCase):
    """Unit tests for load_tsv."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def _write_tsv(self, name: str, content: str) -> Path:
        path = self.tmp_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_monthly_tsv_returns_long_form(self):
        content = "month\tpkg_a\tpkg_b\n2025-01\t100\t50\n2025-02\t200\t\n"
        path = self._write_tsv("pypi.tsv", content)
        df = load_tsv(path)
        self.assertIsNotNone(df)
        self.assertIn("period", df.columns)
        self.assertIn("package", df.columns)
        self.assertIn("count", df.columns)
        # Only rows with count > 0 are kept
        self.assertEqual(len(df), 3)
        self.assertIn("pkg_a", df["package"].values)
        self.assertIn("pkg_b", df["package"].values)

    def test_weekly_tsv_returns_long_form(self):
        content = "week\tpkg_x\n2026-W01\t10\n2026-W02\t20\n"
        path = self._write_tsv("clones.tsv", content)
        df = load_tsv(path)
        self.assertIsNotNone(df)
        self.assertEqual(list(df["package"].unique()), ["pkg_x"])
        self.assertEqual(df["count"].sum(), 30)

    def test_empty_counts_are_dropped(self):
        content = "month\tpkg\n2025-01\t\n2025-02\t5\n"
        path = self._write_tsv("test.tsv", content)
        df = load_tsv(path)
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["count"], 5)

    def test_missing_file_returns_none(self):
        result = load_tsv(self.tmp_dir / "nonexistent.tsv")
        self.assertIsNone(result)

    def test_empty_file_returns_none(self):
        path = self._write_tsv("empty.tsv", "")
        result = load_tsv(path)
        self.assertIsNone(result)


class TestLoadAllData(unittest.TestCase):
    """Unit tests for load_all_data."""

    def setUp(self):
        self.reports_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.reports_dir)

    def _make_year(self, year: str, files: dict) -> None:
        year_dir = self.reports_dir / year
        year_dir.mkdir()
        for filename, content in files.items():
            (year_dir / filename).write_text(content, encoding="utf-8")

    def test_loads_multiple_years(self):
        self._make_year(
            "2025",
            {"pypi_downloads.tsv": "month\tpkg_a\n2025-01\t100\n"},
        )
        self._make_year(
            "2026",
            {"pypi_downloads.tsv": "month\tpkg_a\n2026-01\t200\n"},
        )
        data = load_all_data(self.reports_dir)
        self.assertIn("PyPI Downloads", data)
        df = data["PyPI Downloads"]
        periods = df["period"].tolist()
        self.assertIn("2025-01", periods)
        self.assertIn("2026-01", periods)

    def test_deduplicates_same_period(self):
        # Same period appears in both year files; max value should be kept.
        self._make_year(
            "2025",
            {"pypi_downloads.tsv": "month\tpkg_a\n2025-11\t50\n"},
        )
        self._make_year(
            "2026",
            {"pypi_downloads.tsv": "month\tpkg_a\n2025-11\t100\n"},
        )
        data = load_all_data(self.reports_dir)
        df = data["PyPI Downloads"]
        row = df[(df["period"] == "2025-11") & (df["package"] == "pkg_a")]
        self.assertEqual(row.iloc[0]["count"], 100)

    def test_empty_reports_dir_returns_empty_dict(self):
        data = load_all_data(self.reports_dir)
        self.assertEqual(data, {})


class TestGenerateDashboard(unittest.TestCase):
    """Integration tests for generate_dashboard."""

    def setUp(self):
        self.reports_dir = Path(tempfile.mkdtemp())
        self.output_dir = Path(tempfile.mkdtemp())
        self.output_file = self.output_dir / "index.html"

        # Create sample reports
        year_dir = self.reports_dir / "2026"
        year_dir.mkdir()
        (year_dir / "pypi_downloads.tsv").write_text(
            "month\tpkg_a\tpkg_b\n2026-01\t100\t50\n2026-02\t200\t75\n",
            encoding="utf-8",
        )
        (year_dir / "github_clones.tsv").write_text(
            "week\tpkg_a\n2026-W01\t10\n2026-W02\t20\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.reports_dir)
        shutil.rmtree(self.output_dir)

    def test_output_file_is_created(self):
        generate_dashboard(self.reports_dir, self.output_file)
        self.assertTrue(self.output_file.exists())

    def test_output_contains_html_structure(self):
        generate_dashboard(self.reports_dir, self.output_file)
        content = self.output_file.read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("PyPI Downloads", content)
        self.assertIn("GitHub Clones", content)

    def test_output_embeds_package_data(self):
        generate_dashboard(self.reports_dir, self.output_file)
        content = self.output_file.read_text(encoding="utf-8")
        self.assertIn("pkg_a", content)
        self.assertIn("pkg_b", content)

    def test_output_creates_parent_dirs(self):
        nested_output = self.output_dir / "sub" / "dir" / "dashboard.html"
        generate_dashboard(self.reports_dir, nested_output)
        self.assertTrue(nested_output.exists())

    def test_raises_when_no_data_found(self):
        empty_reports = Path(tempfile.mkdtemp())
        try:
            with self.assertRaises(FileNotFoundError):
                generate_dashboard(empty_reports, self.output_file)
        finally:
            shutil.rmtree(empty_reports)


if __name__ == "__main__":
    unittest.main()
