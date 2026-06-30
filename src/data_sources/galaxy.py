"""Galaxy data source for fetching tool usage statistics."""

import requests
from pathlib import Path
from typing import Any, Dict, List

from src.utils import log_function, make_api_request, setup_logger, read_galaxy_instances
from .base import DataSource

logger = setup_logger()


class GalaxyDataSource(DataSource):
    """Data source for Galaxy tool usage statistics.

    Fetches usage statistics (runs and users) from the research-software-ecosystem
    GitHub repository for multiple Galaxy instances configured in galaxy_instances.tsv.
    """

    GALAXY_CONTENT_BASE_URL = (
        "https://raw.githubusercontent.com/research-software-ecosystem/content/master/imports/galaxy"
    )

    def __init__(
        self,
        project: str,
        package: str,
        config_path: Path,
        github_token: str,
    ):
        """
        Initialize Galaxy data source.

        Args:
            project (str): The project name
            package (str): The Galaxy tool suite package name (e.g., "abricate", "multiqc")
            config_path (Path): Path to galaxy_instances.tsv configuration file
            github_token (str): GitHub API token for authentication
        """
        super().__init__(project, package, "Galaxy")
        self.config_path = config_path
        self.github_token = github_token
        self.instances = read_galaxy_instances(config_path)

    def _get_headers(self) -> dict:
        """Get GitHub API headers."""
        return {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {self.github_token}",
        }

    @log_function(logger, obfuscate_keywords=["token", "key"])
    def fetch(self, action: str = "runs", **kwargs) -> requests.Response:
        """
        Fetch Galaxy tool usage statistics from the research-software-ecosystem repository.

        Args:
            action (str): Either 'runs' or 'users' to specify which metric to fetch
            **kwargs: Additional parameters (unused)

        Returns:
            requests.Response: API response containing JSON with statistics for all configured instances

        The method:
        1. Downloads the Galaxy JSON file for the specified package
        2. Extracts run/user statistics for all enabled Galaxy instances
        3. Returns a Response object with the aggregated data
        """
        if action not in ("runs", "users"):
            raise ValueError(f"Invalid action: {action}. Must be 'runs' or 'users'")

        # Build URL for the Galaxy JSON file
        url = f"{self.GALAXY_CONTENT_BASE_URL}/{self.package}.galaxy.json"
        headers = self._get_headers()

        # Make the API request
        response = make_api_request(http_method="GET", url=url, headers=headers)

        if response.status_code != 200:
            logger.error(f"Failed to fetch Galaxy data for {self.package}: {response.status_code}")
            return response

        # Parse the JSON and extract statistics for each instance
        try:
            data = response.json()
            extracted_data = self._extract_instance_stats(data, action)
            # Create a new response with the extracted data
            extracted_response = requests.Response()
            extracted_response.status_code = 200
            import json as stdlib_json
            extracted_response._content = stdlib_json.dumps(extracted_data).encode("utf-8")
            return extracted_response
        except Exception as e:
            logger.error(f"Failed to parse Galaxy JSON for {self.package}: {e}")
            return response

    def _extract_instance_stats(self, data: Dict[str, Any], action: str) -> Dict[str, Any]:
        """
        Extract statistics for each configured Galaxy instance from the raw JSON data.

        Args:
            data (dict): Raw JSON data from the Galaxy API
            action (str): Either 'runs' or 'users'

        Returns:
            dict: Mapping of instance_name -> {action: count, ...}
                  e.g., {"usegalaxy.eu": {"runs": 156}, "usegalaxy.org": {"runs": 245}}
        """
        result = {
            "package": self.package,
            "project": self.project,
            "source": "Galaxy",
            "action": action,
            "instances": {},
        }

        for instance in self.instances:
            instance_name = instance["instance_name"]
            key_pattern = instance["key_pattern"]

            # Build the JSON key for this instance
            json_key = f"Suite_{action}{key_pattern}"

            # Extract the value, defaulting to 0 if not found
            count = data.get(json_key, 0)

            result["instances"][instance_name] = {
                action: count if count is not None else 0
            }

        return result
