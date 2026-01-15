"""Base class for report generators."""

import csv
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


class ReportGenerator(ABC):
    """Abstract base class for generating download statistics reports."""

    def __init__(self, tmp_dir: Path, output_path: Path):
        self.tmp_dir = tmp_dir
        self.output_path = output_path

    @staticmethod
    def parse_filename(filename: str) -> Optional[Tuple[datetime, str, str, str, str]]:
        """Parse filename to extract timestamp and metadata.

        Format: YYYY-MM-DD_HH-MM-SS__PROJECT__PACKAGE__SOURCE__ACTION.json
        Returns: (timestamp, project, package, source, action)
        """
        parts = filename.replace(".json", "").split("__")
        if len(parts) != 5:
            return None

        try:
            timestamp = datetime.strptime(parts[0], "%Y-%m-%d_%H-%M-%S")
            return (timestamp, parts[1], parts[2], parts[3], parts[4])
        except ValueError:
            return None

    @abstractmethod
    def get_file_pattern(self) -> str:
        """Return glob pattern for finding relevant files."""
        pass

    @abstractmethod
    def should_include_file(self, parsed: Tuple) -> bool:
        """Determine if a parsed filename should be included."""
        pass

    @abstractmethod
    def get_period_key(self, date: datetime) -> str:
        """Convert date to period key (e.g., '2025-12' for month, '2025-W50' for week)."""
        pass

    @abstractmethod
    def aggregate_data(self, file_path: Path) -> Dict[str, Tuple[int, bool]]:
        """Aggregate data from file into period -> (total, is_complete) mapping."""
        pass

    def get_latest_files(self) -> Dict[str, Path]:
        """Find the latest file for each project/package."""
        files = {}

        for file in self.tmp_dir.rglob(self.get_file_pattern()):
            parsed = self.parse_filename(file.name)
            if not parsed or not self.should_include_file(parsed):
                continue

            timestamp, _, entity, _, _ = parsed

            if entity not in files or timestamp > files[entity][0]:
                files[entity] = (timestamp, file)

        return {entity: filepath for entity, (_, filepath) in files.items()}

    def load_existing_report(self) -> Dict[str, Dict[str, int]]:
        """Load existing report data from TSV file."""
        if not self.output_path.exists():
            return {}

        with open(self.output_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            period_col = self.get_period_label()
            return {
                row[period_col]: {
                    k: int(v) for k, v in row.items() if k != period_col and v
                }
                for row in reader
            }

    def filter_periods(self, all_periods: set, year: Optional[int] = None) -> list:
        """Filter and sort periods based on year criteria."""
        if year is None:
            return sorted(all_periods)

        return sorted(
            p
            for p in all_periods
            if p.startswith(f"{year:04d}-") or p.startswith(f"{year - 1:04d}-")
        )

    def create_report(self, year: Optional[int] = None) -> None:
        """Generate or update the TSV report."""
        files = self.get_latest_files()
        if not files:
            print(f"No files found matching pattern: {self.get_file_pattern()}")
            return

        existing_data = self.load_existing_report()

        # Aggregate data from all entities
        entity_data = {
            entity: self.aggregate_data(path) for entity, path in files.items()
        }

        # Get all periods and filter
        all_periods = {p for data in entity_data.values() for p in data.keys()}
        periods = self.filter_periods(all_periods, year)

        if not periods:
            print(f"No data found{f' for year {year}' if year else ''}")
            return

        entities = sorted(entity_data.keys())

        # Build data matrix
        data_matrix = {}
        preserved = filled = incomplete = 0

        for period in periods:
            data_matrix[period] = {}
            for entity in entities:
                if period in existing_data and entity in existing_data[period]:
                    data_matrix[period][entity] = existing_data[period][entity]
                    preserved += 1
                elif entity in entity_data and period in entity_data[entity]:
                    total, is_complete = entity_data[entity][period]
                    if is_complete:
                        data_matrix[period][entity] = total
                        filled += 1 if existing_data else 0
                    else:
                        data_matrix[period][entity] = None
                        incomplete += 1
                else:
                    data_matrix[period][entity] = None
                    incomplete += 1

        # Write TSV
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        period_label = self.get_period_label()

        with open(self.output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([period_label] + entities)
            for period in periods:
                writer.writerow(
                    [period] + [data_matrix[period].get(e) or "" for e in entities]
                )

        # Print summary
        action = "updated" if existing_data else "created"
        print(f"✓ Report {action}: {self.output_path}")
        print(f"  - {len(periods)} {period_label}s, {len(entities)} entities")

        if existing_data:
            print(f"  - {preserved} preserved, {filled} backfilled, {incomplete} empty")
        else:
            total_filled = sum(
                1
                for p in periods
                for e in entities
                if data_matrix[p].get(e) is not None
            )
            print(f"  - {total_filled} filled, {incomplete} empty")

    @abstractmethod
    def get_period_label(self) -> str:
        """Return the label for the period column (e.g., 'month' or 'week')."""
        pass
