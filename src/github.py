import requests
from src.reports import write_stats_response

from .utils import (
    log_function,
    make_api_request,
    setup_logger,
)

logger = setup_logger()


def _get_headers(github_token: str) -> dict:
    return {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {github_token}",
    }


@log_function(logger)
def get_clone_stats(
    owner: str,
    repo: str,
    github_token: str,
) -> requests.Response:
    """
    Fetches the clone statistics for a given GitHub repository.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        github_token (str): The GitHub token.

    Returns:
        dict: A dictionary containing the clone statistics.
    """

    url = f"https://api.github.com/repos/{owner}/{repo}/traffic/clones"
    headers = _get_headers(github_token)
    response = make_api_request(http_method="GET", url=url, headers=headers)
    return response


@log_function(logger)
def get_repo_views(
    owner: str,
    repo: str,
    github_token: str,
) -> requests.Response:
    """
    Fetches the view statistics for a given GitHub repository.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        github_token (str): The GitHub token.

    Returns:
        dict: A dictionary containing the view statistics.
    """

    url = f"https://api.github.com/repos/{owner}/{repo}/traffic/views"
    headers = _get_headers(github_token)
    response = make_api_request(http_method="GET", url=url, headers=headers)
    return response


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
    if action == "clones":
        clone_stats = get_clone_stats(owner, repo, github_token)
        write_stats_response(clone_stats, project, package, "github", "clones")
    elif action == "views":
        view_stats = get_repo_views(owner, repo, github_token)
        write_stats_response(view_stats, project, package, "github", "views")
    else:
        logger.error(f"Invalid action: {action}")
