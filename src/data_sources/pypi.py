"""PyPI data source."""

import requests
from src.utils import log_function, make_api_request, setup_logger
from .base import DataSource

logger = setup_logger()


class PyPIDataSource(DataSource):
    """Data source for PyPI package downloads."""

    def __init__(self, project: str, package: str, pepy_x_api_key: str):
        """
        Initialize PyPI data source.

        Args:
            project (str): The project name
            package (str): The package name (PyPI package name)
            pepy_x_api_key (str): The PePy API key
        """
        super().__init__(project, package, "pypi")
        self.pepy_x_api_key = pepy_x_api_key

    @log_function(logger)
    def fetch(self, action: str = None, **kwargs) -> requests.Response:
        """
        Fetch download statistics from PyPI via PePy API.

        Args:
            action (str): Unused (for interface compatibility)
            **kwargs: Additional parameters (unused)

        Returns:
            requests.Response: The API response
        """
        url = f"https://api.pepy.tech/api/v2/projects/{self.package}"
        headers = {"X-API-Key": self.pepy_x_api_key}
        return make_api_request(http_method="GET", url=url, headers=headers)
