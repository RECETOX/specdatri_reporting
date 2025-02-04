import pandas as pd
from pandas import DataFrame
from src.utils import get_config_var, setup_logger, log_function, get_env_var
from src.github import get_clone_stats, get_repo_views

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


def process_github_repositories(
        owner: str,
        repo: str,
        github_token: str,
):
    """
    Process the list of repositories to fetch clone and view statistics.

    :param repositories_df: DataFrame containing the list of repositories.
    :param github_token: GitHub token to access the GitHub API.
    """
    clone_stats = get_clone_stats(owner, repo, github_token)
    view_stats = get_repo_views(owner, repo, github_token)
    logger.info(f"Clone stats for {owner}/{repo}: {clone_stats}")
    logger.info(f"View stats for {owner}/{repo}: {view_stats}")


def process_repositories(
    repositories_df: DataFrame,
    github_token: str,
):
    """
    Process the list of repositories to fetch clone and view statistics.

    :param repositories_df: DataFrame containing the list of repositories.
    :param github_token: GitHub token to access the GitHub API.
    """
    for _, row in repositories_df.iterrows():
        source = row["source"].lower()
        if source == "github":
            repository = row["repository"]
            owner, repo = repository.split("/")
            process_github_repositories(owner, repo, github_token)


@log_function(logger)
def main():
    repo_file_path = get_config_var("DEFAULT", "REPO_FILE_PATH")
    if repo_file_path:
        logger.info("REPO_FILE_PATH found in .config file")
        repositories_df = load_repositories(repo_file_path)
        github_token = get_env_var("github_token")
        process_repositories(repositories_df, github_token)
        logger.debug(f"Repositories DataFrame: \n{repositories_df}")
    else:
        logger.error("REPO_FILE_PATH not found in .config file")
        print("REPO_FILE_PATH not found in .config file")


if __name__ == "__main__":
    main()
