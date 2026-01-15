# Spec Data Reporting - Unified CLI

A unified command-line interface for collecting download statistics and generating reports for packages across multiple sources (PyPI, GitHub, CRAN, Bioconda).

## Installation

```bash
# Make the CLI executable
chmod +x specdata
```

## Usage

The CLI provides three main subcommands:

### 1. Add Repository (`add-repo`)

Add a new package to the repository list for tracking.

```bash
# Add a package with PyPI and GitHub tracking
./specdata add-repo --project myproject --pypi --github

# Add with custom repository path
./specdata add-repo --project myproject --repository RECETOX/myproject --pypi --bioconda --github

# Add CRAN package
./specdata add-repo --project MyPackage --cran

# Specify custom repository list file
./specdata add-repo --project myproject --pypi --repository-list /path/to/list.tsv
```

**Options:**
- `--repository TEXT` - Repository path in format OWNER/REPO (default: RECETOX/<PROJECT>)
- `--project TEXT` - Project name (required)
- `--repository-list PATH` - Path to repository_list.tsv (default: ./repository_list.tsv)
- `--pypi` - Add PyPI downloads entry
- `--bioconda` - Add Bioconda downloads entry
- `--cran` - Add CRAN downloads entry
- `--github` - Add GitHub views and clones entries

### 2. Collect Statistics (`collect-stats`)

Collect download statistics from all configured sources for packages in the repository list.

```bash
# Collect stats using default settings
./specdata collect-stats

# Specify custom paths
./specdata collect-stats --repository-list custom_list.tsv --tmp-dir data/tmp
```

**Options:**
- `--repository-list PATH` - Path to repository_list.tsv (default: ./repository_list.tsv)
- `--tmp-dir PATH` - Directory to store collected JSON files (default: ./tmp)

**Requirements:**
- Set environment variables: `github_token` and `pepy_x_api_key`

**Output:**
- Creates JSON files with download statistics in `tmp/runs/YYYY-MM-DD/`

### 3. Generate Reports (`generate-reports`)

Generate aggregated TSV reports from collected statistics.

```bash
# Generate reports for current year
./specdata generate-reports

# Generate reports for specific year
./specdata generate-reports --year 2025

# Specify custom paths
./specdata generate-reports --year 2025 --tmp-dir data/tmp --output-dir data/reports
```

**Options:**
- `--year INTEGER` - Year to process (default: current year)
- `--tmp-dir PATH` - Directory with JSON files (default: ./tmp)
- `--output-dir PATH` - Output directory for TSV reports (default: ./reports)

**Output:**
Creates 5 TSV files in `reports/YYYY/`:
- `bioconda_downloads.tsv` - Monthly Bioconda downloads
- `pypi_downloads.tsv` - Monthly PyPI downloads
- `cran_downloads.tsv` - Monthly CRAN downloads
- `github_clones.tsv` - Weekly GitHub repository clones
- `github_views.tsv` - Weekly GitHub repository views

## Complete Workflow Example

```bash
# 1. Add packages to track
./specdata add-repo --project matchms --pypi --bioconda --github
./specdata add-repo --project spec2vec --pypi --bioconda --github

# 2. Collect statistics (requires API tokens)
export github_token="your_github_token"
export pepy_x_api_key="your_pepy_api_key"
./specdata collect-stats

# 3. Generate reports
./specdata generate-reports --year 2025
```

## Using as Python Module

You can also use the CLI programmatically:

```python
from cli import cli

# Use with Click's testing utilities or invoke directly
if __name__ == '__main__':
    cli()
```

## Architecture

The CLI is built on top of two OOP frameworks:

1. **Data Sources Framework** (`src/data_sources/`) - For collecting raw statistics
   - `PyPIDataSource` - PePy API for PyPI downloads
   - `GitHubDataSource` - GitHub API for clones and views
   - `CRANDataSource` - CRAN logs API
   - `CondaDataSource` - Condastats for Bioconda

2. **Reports Framework** (`src/reports/`) - For generating TSV reports
   - `BiocondaReportGenerator` - Monthly aggregation
   - `PyPIReportGenerator` - Monthly aggregation
   - `CRANReportGenerator` - Monthly aggregation
   - `GitHubReportGenerator` - Weekly aggregation

## Environment Variables

Required for collecting statistics:

- `github_token` - GitHub personal access token with repo scope
- `pepy_x_api_key` - PePy API key for PyPI statistics

## File Structure

```
.
├── cli.py                   # Main CLI implementation
├── specdata                 # Entry point script
├── repository_list.tsv      # Configuration file
├── tmp/                     # Collected raw statistics
│   └── runs/
│       └── YYYY-MM-DD/      # Daily run folders
└── reports/                 # Generated TSV reports
    └── YYYY/                # Reports by year
```

## Alternative Tools

For backwards compatibility, the following scripts are still available:

- `scripts/add_repository.py` - Original add repository script
- `scripts/generate_reports.py` - Original report generation script
- `main_oop.py` - OOP-based statistics collection
- `main.py` - Original statistics collection script

However, the unified CLI (`./specdata`) is now the recommended interface for all operations.
