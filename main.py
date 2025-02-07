import pandas as pd
from pandas import DataFrame

from src.github import process_github_repositories
from src.pypi import process_pypi_repositories
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
            process_pypi_repositories(
                package, pepy_x_api_key, action, project
            )
        else:
            logger.error(f"Unknown source: {source}")


@log_function(logger)
def main():
    repo_file_path = get_config_var("DEFAULT", "REPO_FILE_PATH")
    if repo_file_path:
        logger.info("REPO_FILE_PATH found in .config file")
        repositories_df = load_repositories(repo_file_path)
        github_token = get_env_var("github_token")
        pepy_x_api_key = get_env_var("pepy_x_api_key")
        process_repositories(repositories_df, github_token, pepy_x_api_key)
        logger.debug(f"Repositories DataFrame: \n{repositories_df}")
    else:
        logger.error("REPO_FILE_PATH not found in .config file")
        print("REPO_FILE_PATH not found in .config file")


if __name__ == "__main__":
    main()
