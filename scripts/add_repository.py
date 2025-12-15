#!/usr/bin/env python
"""
Script to add a new package to the repository list.

Usage:
    python add_repository.py --repository OWNER/REPO --project PROJECT_NAME [--pypi] [--bioconda] [--cran] [--github]

Example:
    python add_repository.py --repository owner/repo --project myproject --pypi --github
"""

import argparse
import csv
import os
from pathlib import Path
from typing import List, Tuple


def read_existing_entries(repository_list_path: Path) -> List[dict]:
    """Read existing entries from repository_list.tsv"""
    entries = []
    
    if repository_list_path.exists():
        with open(repository_list_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            entries = list(reader)
    
    return entries


def generate_new_entries(
    repository: str,
    project: str,
    has_pypi: bool,
    has_bioconda: bool,
    has_cran: bool,
    has_github: bool,
) -> List[dict]:
    """Generate new entries based on the provided flags"""
    entries = []
    
    # PyPI entry
    if has_pypi:
        entries.append({
            'repository': repository,
            'project': project,
            'package': project,
            'source': 'pypi',
            'action': 'downloads'
        })
    
    # Bioconda entry
    if has_bioconda:
        # If PyPI is not specified, add 'r-' prefix to bioconda package name
        bioconda_package = project if has_pypi else f"r-{project}"
        entries.append({
            'repository': repository,
            'project': project,
            'package': bioconda_package.lower(),
            'source': 'bioconda',
            'action': 'downloads'
        })
    
    # CRAN entry
    if has_cran:
        entries.append({
            'repository': repository,
            'project': project,
            'package': project,
            'source': 'CRAN',
            'action': 'downloads'
        })
    
    # GitHub entries (views and clones)
    if has_github:
        entries.append({
            'repository': repository,
            'project': project,
            'package': project,
            'source': 'GitHub',
            'action': 'views'
        })
        entries.append({
            'repository': repository,
            'project': project,
            'package': project,
            'source': 'GitHub',
            'action': 'clones'
        })
       
    return entries


def write_repository_list(entries: List[dict], repository_list_path: Path) -> None:
    """Write entries to repository_list.tsv"""
    # Define the field names
    fieldnames = ['repository', 'project', 'package', 'source', 'action']
    
    with open(repository_list_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(entries)


def main():
    parser = argparse.ArgumentParser(
        description='Add a new package to the repository list',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--repository',
        required=True,
        help='Repository path in format OWNER/REPO'
    )
    parser.add_argument(
        '--project',
        required=True,
        help='Project name'
    )
    parser.add_argument(
        '--repository-list',
        type=Path,
        required=True,
        help='Path to repository_list.tsv file'
    )
    parser.add_argument(
        '--pypi',
        action='store_true',
        help='Add PyPI downloads entry'
    )
    parser.add_argument(
        '--bioconda',
        action='store_true',
        help='Add Bioconda downloads entry'
    )
    parser.add_argument(
        '--cran',
        action='store_true',
        help='Add CRAN downloads entry'
    )
    parser.add_argument(
        '--github',
        action='store_true',
        help='Add GitHub views and clones entries'
    )
    
    args = parser.parse_args()
    
    # Validate that at least one source is specified
    if not any([args.pypi, args.bioconda, args.cran, args.github]):
        parser.error('At least one source flag must be specified (--pypi, --bioconda, --cran, or --github)')
    
    # Read existing entries
    existing_entries = read_existing_entries(args.repository_list)
    
    # Generate new entries
    new_entries = generate_new_entries(
        repository=args.repository,
        project=args.project,
        has_pypi=args.pypi,
        has_bioconda=args.bioconda,
        has_cran=args.cran,
        has_github=args.github,
    )
    
    # Combine entries
    all_entries = existing_entries + new_entries
    
    # Write to file
    write_repository_list(all_entries, args.repository_list)
    
    # Print summary
    print(f"✓ Added {len(new_entries)} new entries for {args.project}")
    for entry in new_entries:
        print(f"  - {entry['source']}: {entry['action']}")


if __name__ == '__main__':
    main()
