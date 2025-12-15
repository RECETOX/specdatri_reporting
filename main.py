import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta
from pathlib import Path
import shutil

from src.github import process_github_repositories
from src.pypi import process_pypi_repositories
from src.conda import process_conda_repositories
from src.cran import process_cran_repositories
from src.utils import get_config_var, get_env_var, log_function, setup_logger

logger = setup_logger()


@log_function(logger)
def load_repositories(
    file_path: str,
) -> DataFrame:
    """
    Reads a list of repositories from a TSV file and returns it as a DataFrame.

    :param file_path: Path to the TSV file containing the list of repositories.
    :return: DataFrame containing the list of repositories.
    """
    return pd.read_csv(file_path, sep="\t")


@log_function(logger)
def process_repositories(
    repositories_df: DataFrame,
    github_token: str,
    pepy_x_api_key: str,
):
    """
    Args:
        repositories_df (DataFrame): DataFrame containing the list of repositories.
        github_token (str): GitHub token to access the GitHub API.
    Returns:
        None
    """
    last_month = (datetime.now().replace(day=1) - timedelta(days=1))
    twelve_months_ealier = (datetime.now() - timedelta(days=365))
    for _, row in repositories_df.iterrows():
        source = row["source"].lower()
        repository = row["repository"]
        action = row["action"]
        project = row["project"]
        package = row["package"]
        if source == "github":
            owner, repo = repository.split("/")
            process_github_repositories(
                owner, repo, github_token, action, project, package
            )
        elif source == "pypi":
            process_pypi_repositories(package, pepy_x_api_key, action, project)
        elif source == "bioconda":
            process_conda_repositories(
                package,
                "bioconda",
                twelve_months_ealier.strftime("%Y-%m"),
                last_month.strftime("%Y-%m"),
                action,
                project
            )
        elif source == "cran":
            process_cran_repositories(
                package,
                twelve_months_ealier.strftime("%Y-%m-%d"),
                last_month.strftime("%Y-%m-%d"),
                action,
                project
            )
        else:
            logger.error(f"Unknown source: {source}")


@log_function(logger)
def organize_run_reports(run_timestamp: str, tmp_dir: Path) -> None:
    """
    Organize reports generated during this run into a timestamped folder.
    
    Args:
        run_timestamp (str): Timestamp string for this run (format: YYYY-MM-DD)
        tmp_dir (Path): Path to the tmp directory
    """
    # Create runs directory if it doesn't exist
    runs_dir = tmp_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    
    # Create folder for this run
    run_folder = runs_dir / run_timestamp
    run_folder.mkdir(exist_ok=True)
    
    # Find all files in tmp that start with the run timestamp
    files_to_move = list(tmp_dir.glob(f"{run_timestamp}_*"))
    
    if not files_to_move:
        logger.warning(f"No files found for run timestamp: {run_timestamp}")
        return
    
    # Move files to the run folder
    for file_path in files_to_move:
        destination = run_folder / file_path.name
        shutil.move(str(file_path), str(destination))
        logger.debug(f"Moved {file_path.name} to {run_folder}")
    
    logger.info(f"Organized {len(files_to_move)} files into {run_folder}")
    print(f"✓ Organized {len(files_to_move)} reports into {run_folder}")


@log_function(logger)
def main():
    # Capture the run timestamp at the start
    run_timestamp = datetime.now().strftime("%Y-%m-%d")
    
    repo_file_path = get_config_var("DEFAULT", "REPO_FILE_PATH")

    if not repo_file_path:
        logger.error("REPO_FILE_PATH not found in .config file")
        print("REPO_FILE_PATH not found in .config file")
        return

    logger.info("REPO_FILE_PATH found in .config file")
    repositories_df = load_repositories(repo_file_path)
    github_token = get_env_var("github_token")
    pepy_x_api_key = get_env_var("pepy_x_api_key")
    
    # Process all repositories
    process_repositories(repositories_df, github_token, pepy_x_api_key)
    logger.debug(f"Repositories DataFrame: \n{repositories_df}")
    
    # Organize reports into a timestamped folder
    tmp_dir = Path(__file__).parent / "tmp"
    organize_run_reports(run_timestamp, tmp_dir)



if __name__ == "__main__":
    main()
