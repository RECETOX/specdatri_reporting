import requests
from .utils import make_api_request, setup_logger, log_function

logger = setup_logger()


def _get_headers(github_token: str) -> dict:
    return {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {github_token}",
    }


def _get_failed_response(response: requests.Response) -> dict:
    return {
        "status": response.status_code,
        "message": response.json().get("message", "Request failed"),
        "response": response.text,
    }


@log_function(logger)
def get_clone_stats(
    owner: str,
    repo: str,
    github_token: str,
) -> dict:
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
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(
            f"Failed to fetch clone stats: {response.status_code} {response.text}"
        )
        return _get_failed_response(response)


@log_function(logger)
def get_repo_views(
    owner: str,
    repo: str,
    github_token: str,
) -> dict:
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
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(
            f"Failed to fetch view stats: {response.status_code} {response.text}"
        )
        return _get_failed_response(response)
