"""GitHub report generator."""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple

from .base import ReportGenerator


class GitHubReportGenerator(ReportGenerator):
    """Generator for GitHub statistics reports (weekly aggregation with coverage window check)."""
    
    def __init__(self, tmp_dir: Path, output_path: Path, year: int, stat_type: str):
        super().__init__(tmp_dir, output_path)
        self.year = year
        self.stat_type = stat_type  # 'clones' or 'views'
    
    def get_file_pattern(self) -> str:
        return f"*__github__{self.stat_type}.json"
    
    def should_include_file(self, parsed: Tuple) -> bool:
        return parsed[0].year == self.year
    
    def get_period_key(self, date: datetime) -> str:
        return f"{date.year:04d}-W{date.isocalendar()[1]:02d}"
    
    def get_period_label(self) -> str:
        return "week"
    
    def aggregate_data(self, file_path: Path) -> Dict[str, Tuple[int, bool]]:
        """Aggregate daily statistics by week with coverage window check."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Get file timestamp for coverage window calculation
        parsed = self.parse_filename(file_path.name)
        if not parsed:
            return {}
        
        file_timestamp = parsed[0]
        coverage_start = datetime(file_timestamp.year, file_timestamp.month, file_timestamp.day) - timedelta(days=14)
        coverage_end = datetime(file_timestamp.year, file_timestamp.month, file_timestamp.day) + timedelta(days=1)
        
        # Extract entries from GitHub API response
        daily_entries = data.get(self.stat_type, []) if isinstance(data, dict) else []
        
        weekly_data = defaultdict(int)
        week_dates = {}
        
        for entry in daily_entries:
            try:
                timestamp_str = entry.get('timestamp', '')
                date = datetime.strptime(timestamp_str.split('T')[0], '%Y-%m-%d')
                count = int(entry.get('uniques', 0))
                
                week_key = self.get_period_key(date)
                weekly_data[week_key] += count
                
                # Track date range for completeness check
                if week_key not in week_dates:
                    week_dates[week_key] = (date, date)
                else:
                    week_dates[week_key] = (min(week_dates[week_key][0], date), max(week_dates[week_key][1], date))
            except (ValueError, AttributeError, TypeError, KeyError):
                continue
        
        # Week is complete if entirely within coverage window
        return {
            week: (total, week_start >= coverage_start and week_end < coverage_end)
            for week, total in weekly_data.items()
            if (week_start := week_dates[week][0]) and (week_end := week_dates[week][1])
        }
