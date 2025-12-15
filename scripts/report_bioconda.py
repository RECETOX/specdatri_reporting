#!/usr/bin/env python
"""
Script to generate a TSV report of Bioconda download statistics.

This script:
1. Identifies the latest set of download reports in the tmp folder
2. Filters for bioconda reports
3. Creates a TSV file with months as rows and projects as columns
"""

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


def parse_filename(filename: str) -> Tuple[datetime, str, str, str, str]:
    """
    Parse filename to extract timestamp, project, package, source, and action.
    
    Format: YYYY-MM-DD_HH-MM-SS__PROJECT__PACKAGE__SOURCE__ACTION.json
    
    Returns:
        tuple: (timestamp, project, package, source, action)
    """
    parts = filename.replace('.json', '').split('__')
    if len(parts) != 5:
        return None
    
    timestamp_str = parts[0]
    project = parts[1]
    package = parts[2]
    source = parts[3]
    action = parts[4]
    
    try:
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d_%H-%M-%S')
        return (timestamp, project, package, source, action)
    except ValueError:
        return None


def get_latest_bioconda_files(tmp_dir: Path) -> Dict[str, Path]:
    """
    Find the latest bioconda download files for each project.
    
    Returns:
        dict: Mapping of project name to file path
    """
    # Find all bioconda download files
    bioconda_files = {}
    
    for file in tmp_dir.glob('*__bioconda__downloads.json'):
        parsed = parse_filename(file.name)
        if parsed is None:
            continue
        
        timestamp, project, package, source, action = parsed
        
        # Keep only the latest file for each project
        if project not in bioconda_files or timestamp > bioconda_files[project][0]:
            bioconda_files[project] = (timestamp, file)
    
    # Extract just the file paths
    return {project: filepath for project, (timestamp, filepath) in bioconda_files.items()}


def load_download_data(file_path: Path) -> Dict[str, int]:
    """
    Load download data from a JSON file.
    
    Returns:
        dict: Mapping of month (YYYY-MM) to download count
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Convert to month -> count mapping
    monthly_data = {}
    for key, count in data.items():
        # key format: "('package_name', 'YYYY-MM')"
        # Parse the tuple-like string
        if isinstance(key, str) and key.startswith("('") and "')" in key:
            parts = key.split("', '")
            if len(parts) == 2:
                month = parts[1].rstrip("')")
                monthly_data[month] = count
    
    return monthly_data


def create_report(bioconda_files: Dict[str, Path], output_path: Path) -> None:
    """
    Create a TSV report with months as rows and projects as columns.
    """
    # Load all data
    project_data = {}
    all_months = set()
    
    for project, file_path in bioconda_files.items():
        monthly_data = load_download_data(file_path)
        project_data[project] = monthly_data
        all_months.update(monthly_data.keys())
    
    # Sort months chronologically
    sorted_months = sorted(all_months)
    
    # Sort projects alphabetically
    sorted_projects = sorted(project_data.keys())
    
    # Write TSV file
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        
        # Write header
        header = ['month'] + sorted_projects
        writer.writerow(header)
        
        # Write data rows
        for month in sorted_months:
            row = [month]
            for project in sorted_projects:
                count = project_data[project].get(month, 0)
                row.append(count)
            writer.writerow(row)
    
    print(f"✓ Report created: {output_path}")
    print(f"  - {len(sorted_months)} months")
    print(f"  - {len(sorted_projects)} projects: {', '.join(sorted_projects)}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate TSV report of Bioconda download statistics',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--tmp-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'tmp',
        help='Directory containing download report JSON files (default: ../tmp)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path(__file__).parent.parent / 'bioconda_downloads.tsv',
        help='Output TSV file path (default: ../bioconda_downloads.tsv)'
    )
    
    args = parser.parse_args()
    
    if not args.tmp_dir.exists():
        print(f"Error: tmp directory not found: {args.tmp_dir}")
        return 1
    
    # Find latest bioconda files
    bioconda_files = get_latest_bioconda_files(args.tmp_dir)
    
    if not bioconda_files:
        print("No bioconda download files found in tmp directory")
        return 1
    
    # Create report
    create_report(bioconda_files, args.output)
    
    return 0


if __name__ == '__main__':
    exit(main())
