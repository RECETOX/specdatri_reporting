"""GitHub data source."""

import requests
from src.utils import log_function, make_api_request, setup_logger
from .base import DataSource

logger = setup_logger()


class GitHubDataSource(DataSource):
    """Data source for GitHub repository statistics."""

    def __init__(
        self, project: str, package: str, owner: str, repo: str, github_token: str
    ):
        """
        Initialize GitHub data source.

        Args:
            project (str): The project name
            package (str): The package name
            owner (str): The repository owner
            repo (str): The repository name
            github_token (str): The GitHub API token
        """
        super().__init__(project, package, "github")
        self.owner = owner
        self.repo = repo
        self.github_token = github_token

    def _get_headers(self) -> dict:
        """Get GitHub API headers."""
        return {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {self.github_token}",
        }

    @log_function(logger)
    def fetch(self, action: str = "clones", **kwargs) -> requests.Response:
        """
        Fetch statistics from GitHub API.

        Args:
            action (str): Either 'clones' or 'views'
            **kwargs: Additional parameters (unused)

        Returns:
            requests.Response: The API response
        """
        if action == "clones":
            url = (
                f"https://api.github.com/repos/{self.owner}/{self.repo}/traffic/clones"
            )
        elif action == "views":
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/traffic/views"
        else:
            raise ValueError(f"Invalid action: {action}. Must be 'clones' or 'views'")

        headers = self._get_headers()
        return make_api_request(http_method="GET", url=url, headers=headers)
