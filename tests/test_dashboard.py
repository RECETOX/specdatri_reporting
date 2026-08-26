"""Tests for the dashboard generator module."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.dashboard import (
    MAX_CHART_SERIES,
    build_chart_specs,
    generate_dashboard,
    load_all_data,
    load_tsv,
)


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

    def test_output_embeds_chart_specs(self):
        generate_dashboard(self.reports_dir, self.output_file)
        content = self.output_file.read_text(encoding="utf-8")

        self.assertIn("chartSpecs", content)
        self.assertIn("vega-lite", content)

    def test_output_no_longer_shows_a_placeholder(self):
        generate_dashboard(self.reports_dir, self.output_file)
        content = self.output_file.read_text(encoding="utf-8")

        self.assertNotIn("Chart placeholder", content)

    def test_output_loads_vega_with_integrity_hashes(self):
        generate_dashboard(self.reports_dir, self.output_file)
        content = self.output_file.read_text(encoding="utf-8")

        self.assertIn("vega-embed@", content)
        self.assertIn('integrity="sha384-', content)

    def test_output_takes_its_colours_from_custom_properties(self):
        generate_dashboard(self.reports_dir, self.output_file)
        content = self.output_file.read_text(encoding="utf-8")

        self.assertIn("--sd-accent", content)
        self.assertNotIn("#0d6efd", content)

    def test_raises_when_no_data_found(self):
        empty_reports = Path(tempfile.mkdtemp())
        try:
            with self.assertRaises(FileNotFoundError):
                generate_dashboard(empty_reports, self.output_file)
        finally:
            shutil.rmtree(empty_reports)


class TestBuildChartSpecs(unittest.TestCase):
    """Unit tests for build_chart_specs."""

    def _records(self, source, rows):
        return [
            {"source": source, "period": period, "package": package, "count": count}
            for period, package, count in rows
        ]

    def test_one_spec_per_source(self):
        records = self._records("PyPI Downloads", [("2026-01", "pkg_a", 5)])
        records += self._records("GitHub Views", [("2026-W01", "pkg_a", 3)])

        specs = build_chart_specs(records)

        self.assertEqual(set(specs), {"PyPI Downloads", "GitHub Views"})

    def test_spec_declares_vega_lite_schema(self):
        records = self._records("PyPI Downloads", [("2026-01", "pkg_a", 5)])

        spec = build_chart_specs(records)["PyPI Downloads"]

        self.assertIn("vega-lite", spec["$schema"])

    def test_months_sort_chronologically(self):
        records = self._records("PyPI Downloads", [
            ("2026-02", "pkg_a", 1),
            ("2025-11", "pkg_a", 2),
            ("2026-01", "pkg_a", 3),
        ])

        spec = build_chart_specs(records)["PyPI Downloads"]

        self.assertEqual(spec["encoding"]["x"]["sort"], ["2025-11", "2026-01", "2026-02"])

    def test_iso_weeks_sort_numerically_not_lexically(self):
        records = self._records("GitHub Views", [
            ("2026-W10", "pkg_a", 1),
            ("2026-W2", "pkg_a", 2),
        ])

        spec = build_chart_specs(records)["GitHub Views"]

        self.assertEqual(spec["encoding"]["x"]["sort"], ["2026-W2", "2026-W10"])

    def test_unrecognised_period_sorts_last(self):
        records = self._records("PyPI Downloads", [
            ("nonsense", "pkg_a", 1),
            ("2026-01", "pkg_a", 2),
        ])

        spec = build_chart_specs(records)["PyPI Downloads"]

        self.assertEqual(spec["encoding"]["x"]["sort"][-1], "nonsense")

    def test_axis_titles_follow_the_source(self):
        monthly = self._records("PyPI Downloads", [("2026-01", "pkg_a", 1)])
        weekly = self._records("GitHub Views", [("2026-W01", "pkg_a", 1)])

        specs = build_chart_specs(monthly + weekly)

        self.assertEqual(specs["PyPI Downloads"]["encoding"]["x"]["title"], "Month")
        self.assertEqual(specs["PyPI Downloads"]["encoding"]["y"]["title"], "Downloads")
        self.assertEqual(specs["GitHub Views"]["encoding"]["x"]["title"], "Week")
        self.assertEqual(specs["GitHub Views"]["encoding"]["y"]["title"], "Views")

    def test_extra_packages_are_bucketed_without_losing_any_count(self):
        rows = [("2026-01", "pkg_%02d" % i, i + 1) for i in range(MAX_CHART_SERIES + 4)]
        records = self._records("PyPI Downloads", rows)

        spec = build_chart_specs(records)["PyPI Downloads"]
        domain = spec["encoding"]["color"]["scale"]["domain"]

        self.assertEqual(len(domain), MAX_CHART_SERIES + 1)
        self.assertEqual(domain[-1], "Other")
        self.assertEqual(
            sum(value["count"] for value in spec["data"]["values"]),
            sum(count for _, _, count in rows),
        )

    def test_every_series_has_a_colour(self):
        rows = [("2026-01", "pkg_%02d" % i, i + 1) for i in range(MAX_CHART_SERIES + 4)]

        spec = build_chart_specs(self._records("PyPI Downloads", rows))["PyPI Downloads"]
        scale = spec["encoding"]["color"]["scale"]

        self.assertEqual(len(scale["domain"]), len(scale["range"]))

    def test_spec_is_json_serialisable(self):
        records = self._records("PyPI Downloads", [("2026-01", "pkg_a", 5)])

        json.dumps(build_chart_specs(records))

    def test_spec_carries_no_config_block(self):
        records = self._records("PyPI Downloads", [("2026-01", "pkg_a", 5)])

        spec = build_chart_specs(records)["PyPI Downloads"]

        self.assertNotIn("config", spec)

    def test_no_records_means_no_specs(self):
        self.assertEqual(build_chart_specs([]), {})


if __name__ == "__main__":
    unittest.main()
