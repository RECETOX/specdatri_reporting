"""Galaxy report generator for tool usage statistics."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from .base import ReportGenerator


class GalaxyReportGenerator(ReportGenerator):
    """Generator for Galaxy tool usage statistics reports.

    Aggregates monthly statistics (runs or users) across multiple Galaxy instances
    from collected JSON data files.
    """

    def __init__(self, tmp_dir: Path, output_path: Path, stat_type: str = "runs"):
        """
        Initialize Galaxy report generator.

        Args:
            tmp_dir: Directory containing collected JSON files
            output_path: Path for the output TSV file
            stat_type: Either 'runs' or 'users' to specify which metric to report
        """
        super().__init__(tmp_dir, output_path)
        self.stat_type = stat_type

    def get_file_pattern(self) -> str:
        """Return glob pattern for finding Galaxy JSON files of the specified type."""
        return f"*__Galaxy__{self.stat_type}.json"

    def should_include_file(self, parsed: Tuple) -> bool:
        """Include files from the current year."""
        # We'll filter by year in create_report based on the output filename
        return True

    def get_period_key(self, date: datetime) -> str:
        """Convert date to monthly period key (e.g., '2025-01')."""
        return f"{date.year:04d}-{date.month:02d}"

    def get_period_label(self) -> str:
        """Return the label for the period column."""
        return "month"

    def aggregate_data(self, file_path: Path) -> Dict[str, Tuple[int, bool]]:
        """
        Aggregate Galaxy statistics by month.

        Args:
            file_path: Path to the collected JSON file

        Returns:
            Dict mapping period_key -> (total_count, is_complete)
            For Galaxy data, we use the file timestamp and treat it as complete.
        """
        with open(file_path, "r") as f:
            data = json.load(f)

        # Parse filename to get timestamp
        parsed = self.parse_filename(file_path.name)
        if not parsed:
            return {}

        file_timestamp = parsed[0]
        period_key = self.get_period_key(file_timestamp)

        # Extract action type from metadata
        action = parsed[4]  # e.g., 'runs' or 'users'

        # Sum up counts across all instances
        total = 0
        instances_data = data.get("instances", {})

        for instance_name, instance_stats in instances_data.items():
            count = instance_stats.get(action, 0)
            total += count

        # Mark as complete since we're aggregating a full snapshot
        return {period_key: (total, True)}

    def get_latest_files(self) -> Dict[str, Path]:
        """
        Find the latest file for each project/package combination.

        Overrides base class to handle Galaxy's multi-instance data structure.
        """
        files = {}

        for file in self.tmp_dir.rglob(self.get_file_pattern()):
            # Metadata snapshots are sidecar files and should not be aggregated.
            if "metadata" in file.name.lower():
                continue

            parsed = self.parse_filename(file.name)
            if not parsed:
                continue

            timestamp, _, entity, source, action = parsed

            # Only include Galaxy sources
            if source.lower() != "galaxy":
                continue

            # Use entity + action as the key (e.g., "abricate_runs")
            key = f"{entity}"

            if key not in files or timestamp > files[key][0]:
                files[key] = (timestamp, file)

        return {key: filepath for key, (_, filepath) in files.items()}
