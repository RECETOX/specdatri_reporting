"""PyPI report generator."""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from .base import ReportGenerator


class PyPIReportGenerator(ReportGenerator):
    """Generator for PyPI download reports (monthly aggregation with completeness check)."""

    def __init__(self, tmp_dir: Path, output_path: Path, year: int):
        super().__init__(tmp_dir, output_path)
        self.year = year

    def get_file_pattern(self) -> str:
        return "*__pypi__downloads.json"

    def should_include_file(self, parsed: Tuple) -> bool:
        return parsed[0].year == self.year

    def get_period_key(self, date: datetime) -> str:
        return f"{date.year:04d}-{date.month:02d}"

    def get_period_label(self) -> str:
        return "month"

    @staticmethod
    def get_adjacent_month(year: int, month: int, offset: int) -> str:
        """Get adjacent month key."""
        month += offset
        if month == 0:
            return f"{year - 1:04d}-12"
        elif month == 13:
            return f"{year + 1:04d}-01"
        return f"{year:04d}-{month:02d}"

    def aggregate_data(self, file_path: Path) -> Dict[str, Tuple[int, bool]]:
        """Aggregate daily downloads by month with completeness check."""
        with open(file_path, "r") as f:
            daily_downloads = json.load(f).get("downloads", {})

        monthly_data = defaultdict(int)
        months_present = set()

        for date_str, version_downloads in daily_downloads.items():
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                month_key = self.get_period_key(date)
                monthly_data[month_key] += sum(version_downloads.values())
                months_present.add(month_key)
            except (ValueError, AttributeError):
                continue

        # Month is complete if adjacent months exist
        return {
            month: (
                total,
                self.get_adjacent_month(*map(int, month.split("-")), -1)
                in months_present
                and self.get_adjacent_month(*map(int, month.split("-")), +1)
                in months_present,
            )
            for month, total in monthly_data.items()
        }
