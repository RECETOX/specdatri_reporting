"""Conda/Bioconda data source."""

import pandas as pd
from condastats.cli import overall
from src.utils import log_function, setup_logger
from .base import DataSource

logger = setup_logger()


class CondaDataSource(DataSource):
    """Data source for Conda/Bioconda package downloads."""
    
    def __init__(self, project: str, package: str, data_source: str):
        """
        Initialize Conda data source.
        
        Args:
            project (str): The project name
            package (str): The package name
            data_source (str): The Conda data source (e.g., 'bioconda')
        """
        super().__init__(project, package, data_source)
        self.conda_data_source = data_source
    
    @log_function(logger)
    def fetch(self, action: str = None, start_month: str = None, end_month: str = None, **kwargs) -> pd.Series:
        """
        Fetch download statistics from Conda API.
        
        Args:
            action (str): Unused (for interface compatibility)
            start_month (str): Start month in YYYY-MM format
            end_month (str): End month in YYYY-MM format
            **kwargs: Additional parameters (unused)
            
        Returns:
            pd.Series: The download statistics
        """
        try:
            return overall(
                package=self.package,
                data_source=self.conda_data_source,
                start_month=start_month,
                end_month=end_month,
                monthly=True,
            )
        except Exception as e:
            logger.error(
                f"Failed to fetch download statistics for {self.package} from {self.conda_data_source} "
                f"for the period {start_month} to {end_month}."
            )
            logger.error(e)
            return pd.Series()
