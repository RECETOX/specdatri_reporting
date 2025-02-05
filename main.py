import pandas as pd
from pandas import DataFrame
from src.utils import get_config_var, setup_logger, log_function, get_env_var, prep_filename, write_prep_filename_metadata
from src.github import get_clone_stats, get_repo_views
from src.reports import write_json

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
def process_github_repositories(
    owner: str,
    repo: str,
    github_token: str,
    action: str,
    project: str,
    package: str,
):
    """
    Processes the specified GitHub repository to fetch clone and view statistics.

       Args:
            owner (str): The owner of the GitHub repository.
            repo (str): The name of the GitHub repository.
            github_token (str): The GitHub token to access the GitHub API.
            action (str): The action to be performed on the repository.
            project (str): The project name.
            package (str): The specific package name.

       Returns:
            None

       Logs:
            Logs the clone and view statistics for the specified repository.
    """
    temp_folder = "tmp"
    if action == "clones":
        clone_stats = get_clone_stats(owner, repo, github_token)
        filename = prep_filename(temp_folder, project, package, "github", "clones")
        write_json(clone_stats, filename)
        write_prep_filename_metadata(project, package, "github", "clones", filename)
        logger.info(f"Clone stats for {owner}/{repo}: {clone_stats}")
    elif action == "views":
        view_stats = get_repo_views(owner, repo, github_token)
        filename = prep_filename(temp_folder, project, package, "github", "views")
        write_prep_filename_metadata(project, package, "github", "views", filename)
        write_json(view_stats, filename)
        logger.info(f"View stats for {owner}/{repo}: {view_stats}")
    else:
        logger.error(f"Invalid action: {action}")


@log_function(logger)
def process_repositories(
    repositories_df: DataFrame,
    github_token: str,
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
        if source == "github":
            repository = row["repository"]
            action = row["action"]
            project = row["project"]
            package = row["package"]
            owner, repo = repository.split("/")
            process_github_repositories(
                owner, repo, github_token,
                action, project, package
            )


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
