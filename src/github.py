from .utils import make_api_request, get_logger, get_failed_response

logger = get_logger()


def get_clone_stats(
    owner: str,
    repo: str,
    github_user: str,
    github_token: str,
) -> dict:
    """
    Fetches the clone statistics for a given GitHub repository.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        github_user (str): The GitHub username.
        github_token (str): The GitHub token.

    Returns:
        dict: A dictionary containing the clone statistics.
    """

    url = f"https://api.github.com/repos/{owner}/{repo}/traffic/clones"
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = make_api_request(
        http_method="GET", url=url, auth=(github_user, github_token), headers=headers
    )
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(
            f"Failed to fetch clone stats: {response.status_code} {response.text}"
        )
        return get_failed_response()
