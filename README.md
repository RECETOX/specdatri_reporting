# specdatri_reporting

## Overview

**specdatri_reporting** is an automated reporting tool that collects and aggregates download and usage statistics for [RECETOX](https://www.recetox.muni.cz/) research software packages. It monitors the adoption and impact of the organisation's scientific software across multiple distribution platforms.

### What it does

- Fetches download and traffic data from PyPI, CRAN, Bioconda, and GitHub on a weekly schedule.
- Aggregates raw data into human-readable TSV reports grouped by month (for package downloads) or by week (for GitHub traffic).
- Commits the updated reports back to the repository automatically via GitHub Actions.

### What kind of data is presented

| Platform | Metric | Aggregation |
|----------|--------|-------------|
| [PyPI](https://pypi.org/) | Package downloads | Monthly |
| [CRAN](https://cran.r-project.org/) | Package downloads | Monthly |
| [Bioconda](https://bioconda.github.io/) | Package downloads | Monthly |
| [GitHub](https://github.com/) | Repository views | Weekly |
| [GitHub](https://github.com/) | Repository clones | Weekly |

Generated reports are stored as TSV files under `reports/<YEAR>/` and are versioned in the repository.

### How it works (GitHub Actions)

A scheduled GitHub Actions workflow (`.github/workflows/actions.yml`) runs every Monday at 00:00 UTC and performs the following steps:

1. **Checkout** the repository.
2. **Install dependencies** (`pip install -r requirements.txt`).
3. **Collect statistics** by calling `./specdatri collect-stats`, which queries each configured data source and saves raw JSON responses to `tmp/runs/<YYYY-MM-DD>/`.
4. **Generate reports** by calling `./specdatri generate-reports`, which reads all collected JSON files and produces aggregated TSV files in `reports/<YEAR>/`.
5. **Commit and push** the updated report files back to the `main` branch.

The workflow can also be triggered manually from the GitHub Actions UI via `workflow_dispatch`.

---

## User Guide

This section explains how to run the reporting tool manually.

### Prerequisites

- Python 3.12+
- A GitHub personal access token with `repo` scope (`github_token`). Read access is sufficient for collecting traffic statistics manually; write access is required by the automated workflow to push report commits.
- A [PePy](https://pepy.tech/) API key for PyPI statistics (`pepy_x_api_key`).

### Setup

```bash
# Clone the repository
git clone https://github.com/RECETOX/specdatri_reporting.git
cd specdatri_reporting

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Make the entry point executable (Linux/macOS)
chmod +x specdatri

# Provide API tokens
cp example.env .env
# Edit .env and fill in your tokens:
#   github_token="your_github_token"
#   pepy_x_api_key="your_pepy_api_key"
```

> **Note:** The tool loads `.env` automatically via `python-dotenv`. Alternatively, export the variables in your shell before running any command.

### CLI commands

The `specdatri` entry point exposes three subcommands.

#### 1. Add a repository to track (`add-repo`)

```bash
# Add a package tracked on PyPI and GitHub
./specdatri add-repo --project mypackage --pypi --github

# Add a package with a custom repository path and all sources
./specdatri add-repo --project mypackage --repository OWNER/mypackage --pypi --bioconda --cran --github

# Add an R package tracked on CRAN only
./specdatri add-repo --project MyRPackage --cran
```

Options:

| Option | Description | Default |
|--------|-------------|---------|
| `--project TEXT` | Project name (required) | — |
| `--repository TEXT` | GitHub repo path `OWNER/REPO` | `RECETOX/<PROJECT>` |
| `--repository-list PATH` | Path to the tracking list | `./repository_list.tsv` |
| `--pypi` | Track PyPI downloads | off |
| `--bioconda` | Track Bioconda downloads | off |
| `--cran` | Track CRAN downloads | off |
| `--github` | Track GitHub views and clones | off |

#### 2. Collect statistics (`collect-stats`)

```bash
# Collect stats for all configured packages
./specdatri collect-stats

# Use custom paths
./specdatri collect-stats --repository-list custom_list.tsv --tmp-dir data/tmp
```

Output: JSON files in `tmp/runs/<YYYY-MM-DD>/` named using the pattern
`{timestamp}___{project}___{package}___{source}___{action}.json`.

#### 3. Generate reports (`generate-reports`)

```bash
# Generate reports for the current year
./specdatri generate-reports

# Generate reports for a specific year
./specdatri generate-reports --year 2025

# Use custom paths
./specdatri generate-reports --year 2025 --tmp-dir data/tmp --output-dir data/reports
```

Output: five TSV files per year in `reports/<YEAR>/`:

- `pypi_downloads.tsv`
- `bioconda_downloads.tsv`
- `cran_downloads.tsv`
- `github_views.tsv`
- `github_clones.tsv`

### Full manual workflow example

```bash
# 1. Add packages (one-time setup)
./specdatri add-repo --project matchms --pypi --bioconda --github
./specdatri add-repo --project spec2vec --pypi --bioconda --github

# 2. Collect statistics
./specdatri collect-stats

# 3. Generate reports
./specdatri generate-reports --year 2025
```

---

## Developer Guide

### Project setup

```bash
# Install development dependencies (includes pre-commit hooks)
pip install -r ./requirements/local.txt

# Install pre-commit hooks
pre-commit install
```

### Running tests

```bash
# Run all tests
python -m unittest discover -s tests

# Run with coverage
coverage run -m unittest discover -s tests
coverage report -m
coverage html   # generates htmlcov/index.html
```

### Testing GitHub Actions locally

You need [act](https://nektosact.com/) to simulate GitHub Actions on your machine.

```bash
# Simulate the weekly schedule trigger
act --secret-file .env schedule
```

> **Important notes when testing with `act`:**
>
> - Use a token **without** push permissions so that test data is never written to the production branch.
> - The push step will fail if branch protection rules are active — this is expected behaviour.
> - Files created inside the Docker container are **not** written to your local filesystem.
> - Never push directly to `main`; always work on a feature branch.

### Adding new repositories

Use the `add-repo` CLI command (see [User Guide](#1-add-a-repository-to-track-add-repo)) and then commit the updated `repository_list.tsv`:

```bash
./specdatri add-repo --project newpackage --pypi --github
git add repository_list.tsv
git commit -m "Track newpackage on PyPI and GitHub"
```

The `repository_list.tsv` file is a tab-separated table with the columns:

| Column | Description |
|--------|-------------|
| `repository` | GitHub repository path (`OWNER/REPO`) |
| `project` | Human-readable project identifier |
| `package` | Package name on the distribution platform |
| `source` | One of: `pypi`, `bioconda`, `CRAN`, `GitHub` |
| `action` | One of: `downloads`, `views`, `clones` |

### Integrating a new data source

Data sources live in `src/data_sources/` and inherit from the abstract `DataSource` base class in `src/data_sources/base.py`.

To add a new source:

1. **Create a new module** `src/data_sources/<name>.py` and implement the `DataSource` interface:

   ```python
   from .base import DataSource

   class MyNewDataSource(DataSource):
       def fetch(self, package: str, project: str) -> dict:
           # Call the external API and return raw data as a dict
           ...
   ```

2. **Register the source** in `src/cli.py` by mapping the source identifier to the new class, following the same pattern as existing sources.

3. **Add a new source flag** to the `add-repo` command if users need to opt in to this source.

4. **Write tests** in `tests/` following the patterns in `tests/test_data_sources.py`.

See `src/data_sources/README.md` for a detailed description of the data source architecture.

### Integrating a new report type

Report generators live in `src/reports/` and inherit from the abstract `ReportGenerator` base class in `src/reports/base.py`.

To add a new report:

1. **Create a new module** `src/reports/<name>.py` and implement the `ReportGenerator` interface:

   ```python
   from .base import ReportGenerator

   class MyNewReportGenerator(ReportGenerator):
       source = "mysource"
       action = "downloads"
       period = "monthly"   # or "weekly"

       def aggregate(self, data: list[dict]) -> dict:
           # Aggregate raw records into period → count mapping
           ...
   ```

2. **Register the generator** in `src/cli.py` so that `generate-reports` picks it up automatically.

3. **Write tests** in `tests/` following the patterns in `tests/test_report.py`.

See `src/reports/README.md` for a detailed description of the report generation architecture.

---

## Adopting This Framework

If you want to set up a similar automated download-statistics tracking system for your own organisation's repositories, follow these steps:

### 1. Fork or copy the repository

Fork this repository into your GitHub organisation (or copy the relevant files into a new repository).

### 2. Configure the packages to track

Edit `repository_list.tsv` (or use `./specdatri add-repo`) to list your own packages and their distribution channels.

### 3. Configure GitHub Actions secrets

In your repository's **Settings → Secrets and variables → Actions**, add:

| Secret | Description |
|--------|-------------|
| `RECEBOT_REPORTING_TOKEN` | A GitHub personal access token (PAT) with `repo` scope. Used to read traffic data from the GitHub API and push report commits. Consider using a dedicated bot account. |
| `pepy_x_api_key` | Your PePy API key for PyPI download statistics. |

> The `github_token` secret used by the push step is the built-in `secrets.github_token` provided by GitHub Actions and does not need to be configured manually.

### 4. Adjust the workflow schedule (optional)

Edit `.github/workflows/actions.yml` and change the `cron` expression to your preferred schedule:

```yaml
schedule:
  - cron: '0 0 * * 1'  # Every Monday at 00:00 UTC
```

### 5. Remove or adapt RECETOX-specific content

- Update the repository description and any references to RECETOX in the README.
- Remove or replace entries in `repository_list.tsv` with your own packages.
- Clear the `reports/` directory (or delete historical data you do not need).

### 6. Protect the default branch (recommended)

Enable branch protection on `main` to prevent accidental direct pushes. The GitHub Actions workflow pushes via the `ad-m/github-push-action` action using the workflow token, which is exempt from push restrictions when `secrets.github_token` is used.
