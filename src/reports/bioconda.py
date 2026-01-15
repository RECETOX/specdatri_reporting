"""Bioconda report generator."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from .base import ReportGenerator


class BiocondaReportGenerator(ReportGenerator):
    """Generator for Bioconda download reports (monthly aggregation)."""
    
    def __init__(self, tmp_dir: Path, output_path: Path, year: int):
        super().__init__(tmp_dir, output_path)
        self.year = year
    
    def get_file_pattern(self) -> str:
        return "*__bioconda__downloads.json"
    
    def should_include_file(self, parsed: Tuple) -> bool:
        return parsed[0].year == self.year
    
    def get_period_key(self, date: datetime) -> str:
        return f"{date.year:04d}-{date.month:02d}"
    
    def get_period_label(self) -> str:
        return "month"
    
    def aggregate_data(self, file_path: Path) -> Dict[str, Tuple[int, bool]]:
        """Load pre-aggregated monthly data from Bioconda JSON."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        monthly_data = {}
        for key, count in data.items():
            # Parse tuple-like string: "('package_name', 'YYYY-MM')"
            if isinstance(key, str) and key.startswith("('") and "')" in key:
                parts = key.split("', '")
                if len(parts) == 2:
                    month = parts[1].rstrip("')")
                    monthly_data[month] = (count, True)  # Always complete for Bioconda
        
        return monthly_data
