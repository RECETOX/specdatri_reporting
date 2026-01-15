"""Unified CLI for the Spec Data Reporting framework."""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import click
import pandas as pd

from src.data_sources import (
    PyPIDataSource,
    GitHubDataSource,
    CRANDataSource,
    CondaDataSource,
)
from src.utils import get_config_var, get_env_var, log_function, setup_logger
from src.reports import (
    BiocondaReportGenerator,
    CRANReportGenerator,
    PyPIReportGenerator,
    GitHubReportGenerator,
)

logger = setup_logger()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Unified CLI for download statistics collection and reporting."""
    pass


# ============================================================================
# ADD-REPO SUBCOMMAND
# ============================================================================


def read_existing_entries(repository_list_path: Path) -> List[dict]:
    """Read existing entries from repository_list.tsv"""
    entries = []

    if repository_list_path.exists():
        with open(repository_list_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
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

    if has_pypi:
        entries.append(
            {
                "repository": repository,
                "project": project,
                "package": project,
                "source": "pypi",
                "action": "downloads",
            }
        )

    if has_bioconda:
        bioconda_package = project if has_pypi else f"r-{project}"
        entries.append(
            {
                "repository": repository,
                "project": project,
                "package": bioconda_package.lower(),
                "source": "bioconda",
                "action": "downloads",
            }
        )

    if has_cran:
        entries.append(
            {
                "repository": repository,
                "project": project,
                "package": project,
                "source": "CRAN",
                "action": "downloads",
            }
        )

    if has_github:
        entries.append(
            {
                "repository": repository,
                "project": project,
                "package": project,
                "source": "GitHub",
                "action": "views",
            }
        )
        entries.append(
            {
                "repository": repository,
                "project": project,
                "package": project,
                "source": "GitHub",
                "action": "clones",
            }
        )

    return entries


def write_repository_list(entries: List[dict], repository_list_path: Path) -> None:
    """Write entries to repository_list.tsv"""
    fieldnames = ["repository", "project", "package", "source", "action"]

    with open(repository_list_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(entries)


@cli.command()
@click.option(
    "--repository",
    default=None,
    help="Repository path in format OWNER/REPO (default: RECETOX/<PROJECT>)",
)
@click.option("--project", required=True, help="Project name")
@click.option(
    "--repository-list",
    type=click.Path(),
    default="repository_list.tsv",
    help="Path to repository_list.tsv",
)
@click.option("--pypi", is_flag=True, help="Add PyPI downloads entry")
@click.option("--bioconda", is_flag=True, help="Add Bioconda downloads entry")
@click.option("--cran", is_flag=True, help="Add CRAN downloads entry")
@click.option("--github", is_flag=True, help="Add GitHub views and clones entries")
def add_repo(repository, project, repository_list, pypi, bioconda, cran, github):
    """Add a new package to the repository list."""

    if not any([pypi, bioconda, cran, github]):
        click.echo(
            "Error: At least one source flag must be specified (--pypi, --bioconda, --cran, or --github)"
        )
        raise click.Exit(1)

    if repository is None:
        repository = f"RECETOX/{project}"

    repo_list_path = Path(repository_list)
    existing_entries = read_existing_entries(repo_list_path)

    new_entries = generate_new_entries(
        repository=repository,
        project=project,
        has_pypi=pypi,
        has_bioconda=bioconda,
        has_cran=cran,
        has_github=github,
    )

    all_entries = existing_entries + new_entries
    write_repository_list(all_entries, repo_list_path)

    click.echo(f"✓ Added {len(new_entries)} new entries for {project}")
    for entry in new_entries:
        click.echo(f"  - {entry['source']}: {entry['action']}")


# ============================================================================
# COLLECT-STATS SUBCOMMAND
# ============================================================================


@log_function(logger)
def process_repositories(
    repositories_df: pd.DataFrame,
    github_token: str,
    pepy_x_api_key: str,
):
    """Process repositories by fetching download statistics from various sources."""
    last_month = datetime.now().replace(day=1) - timedelta(days=1)
    twelve_months_earlier = datetime.now() - timedelta(days=365)

    for _, row in repositories_df.iterrows():
        source = row["source"].lower()
        repository = row["repository"]
        action = row["action"]
        project = row["project"]
        package = row["package"]

        try:
            if source == "github":
                owner, repo = repository.split("/")
                data_source = GitHubDataSource(
                    project, package, owner, repo, github_token
                )
                data_source.process(action)
            elif source == "pypi":
                data_source = PyPIDataSource(project, package, pepy_x_api_key)
                data_source.process(action)
            elif source == "bioconda":
                data_source = CondaDataSource(project, package, "bioconda")
                data_source.process(
                    action,
                    start_month=twelve_months_earlier.strftime("%Y-%m"),
                    end_month=last_month.strftime("%Y-%m"),
                )
            elif source == "cran":
                data_source = CRANDataSource(project, package)
                data_source.process(
                    action,
                    start_date=twelve_months_earlier.strftime("%Y-%m-%d"),
                    end_date=last_month.strftime("%Y-%m-%d"),
                )
            else:
                logger.error(f"Unknown source: {source}")
        except Exception as e:
            logger.error(f"Failed to process {source} repository {package}: {e}")


def organize_run_reports(run_timestamp: str, tmp_dir: Path) -> None:
    """Organize reports generated during this run into a timestamped folder."""
    import shutil

    runs_dir = tmp_dir / "runs"
    runs_dir.mkdir(exist_ok=True)

    run_folder = runs_dir / run_timestamp
    run_folder.mkdir(exist_ok=True)

    files_to_move = list(tmp_dir.glob(f"{run_timestamp}_*"))

    if not files_to_move:
        logger.warning(f"No files found for run timestamp: {run_timestamp}")
        return

    for file_path in files_to_move:
        destination = run_folder / file_path.name
        shutil.move(str(file_path), str(destination))
        logger.debug(f"Moved {file_path.name} to {run_folder}")

    logger.info(f"Organized {len(files_to_move)} files into {run_folder}")
    click.echo(f"✓ Organized {len(files_to_move)} reports into {run_folder}")


@cli.command()
@click.option(
    "--repository-list",
    type=click.Path(exists=True),
    default="repository_list.tsv",
    help="Path to repository_list.tsv",
)
@click.option(
    "--tmp-dir",
    type=click.Path(),
    default="tmp",
    help="Directory to store collected JSON files (default: ./tmp)",
)
def collect_stats(repository_list, tmp_dir):
    """Collect download statistics from all configured sources."""

    tmp_dir_path = Path(tmp_dir)

    if not Path(repository_list).exists():
        click.echo(f"Error: Repository list file not found: {repository_list}")
        raise click.Exit(1)

    click.echo(f"Loading repositories from {repository_list}...")
    repositories_df = pd.read_csv(repository_list, sep="\t")

    github_token = get_env_var("github_token")
    pepy_x_api_key = get_env_var("pepy_x_api_key")

    if not github_token:
        click.echo("Warning: github_token not found in environment")
    if not pepy_x_api_key:
        click.echo("Warning: pepy_x_api_key not found in environment")

    click.echo(f"\nCollecting statistics for {len(repositories_df)} entries...")
    click.echo("=" * 60)

    process_repositories(repositories_df, github_token, pepy_x_api_key)

    run_timestamp = datetime.now().strftime("%Y-%m-%d")
    organize_run_reports(run_timestamp, tmp_dir_path)

    click.echo("=" * 60)
    click.echo("✓ Statistics collection completed")


# ============================================================================
# GENERATE-REPORTS SUBCOMMAND
# ============================================================================


@cli.command()
@click.option(
    "--year",
    type=int,
    default=datetime.now().year,
    help=f"Year to process (default: {datetime.now().year})",
)
@click.option(
    "--tmp-dir",
    type=click.Path(exists=True),
    default="tmp",
    help="Directory with JSON files (default: ./tmp)",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="reports",
    help="Output directory for TSV reports (default: ./reports)",
)
def generate_reports(year, tmp_dir, output_dir):
    """Generate aggregated TSV reports from collected statistics."""

    tmp_path = Path(tmp_dir)
    output_path = Path(output_dir)

    if not tmp_path.exists():
        click.echo(f"Error: tmp directory not found: {tmp_path}")
        raise click.Exit(1)

    click.echo(f"Generating reports for year {year}...")
    click.echo("=" * 60)

    # Bioconda
    click.echo("\n1. Bioconda Report")
    click.echo("-" * 60)
    output_file = output_path / str(year) / "bioconda_downloads.tsv"
    generator = BiocondaReportGenerator(tmp_path, output_file, year)
    generator.create_report(year=year)

    # PyPI
    click.echo("\n2. PyPI Report")
    click.echo("-" * 60)
    output_file = output_path / str(year) / "pypi_downloads.tsv"
    generator = PyPIReportGenerator(tmp_path, output_file, year)
    generator.create_report(year=year)

    # CRAN
    click.echo("\n3. CRAN Report")
    click.echo("-" * 60)
    output_file = output_path / str(year) / "cran_downloads.tsv"
    generator = CRANReportGenerator(tmp_path, output_file, year)
    generator.create_report(year=year)

    # GitHub Clones
    click.echo("\n4. GitHub Clones Report")
    click.echo("-" * 60)
    output_file = output_path / str(year) / "github_clones.tsv"
    generator = GitHubReportGenerator(tmp_path, output_file, year, "clones")
    generator.create_report(year=year)

    # GitHub Views
    click.echo("\n5. GitHub Views Report")
    click.echo("-" * 60)
    output_file = output_path / str(year) / "github_views.tsv"
    generator = GitHubReportGenerator(tmp_path, output_file, year, "views")
    generator.create_report(year=year)

    click.echo("\n" + "=" * 60)
    click.echo(f"✓ All 5 reports generated successfully for {year}")
    click.echo(f"  Output directory: {output_path / str(year)}")


if __name__ == "__main__":
    cli()
