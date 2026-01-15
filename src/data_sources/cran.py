"""CRAN data source."""

import requests
from src.utils import log_function, make_api_request, setup_logger
from .base import DataSource

logger = setup_logger()


class CRANDataSource(DataSource):
    """Data source for CRAN package downloads."""

    def __init__(self, project: str, package: str):
        """
        Initialize CRAN data source.

        Args:
            project (str): The project name
            package (str): The package name (CRAN package name)
        """
        super().__init__(project, package, "cran")

    @log_function(logger)
    def fetch(
        self, action: str = None, start_date: str = None, end_date: str = None, **kwargs
    ) -> requests.Response:
        """
        Fetch download statistics from CRAN API.

        Args:
            action (str): Unused (for interface compatibility)
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            **kwargs: Additional parameters (unused)

        Returns:
            requests.Response: The API response
        """
        url = f"https://cranlogs.r-pkg.org/downloads/daily/{start_date}:{end_date}/{self.package}"
        return make_api_request(http_method="GET", url=url)
