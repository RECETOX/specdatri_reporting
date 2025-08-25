from condastats.cli import overall
import pandas as pd
from .utils import (
    log_function,
    setup_logger,
)
from .reports import write_stats_response

logger = setup_logger()


@log_function(logger)
def get_download_stats(
    package_name: str,
    data_source: str,
    start_month: str,
    end_month: str,
) -> pd.Series:
    """
    Fetches the download statistics for a given package from Anaconda.

    Args:
        package_name (str): The name of the package.
        data_source (str): The data source eg bioconda.
        start_date (str): The start month in the format YYYY-MM eg 2024-03.
        end_date (str): The end month in the format YYYY-MM eg 2024-03.

    Returns:

    """
    try:
        return overall(
            package=package_name,
            data_source=data_source,
            start_month=start_month,
            end_month=end_month,
            monthly=True,
        )
    except Exception as e:
        logger.error(
            f"Failed to fetch download statistics for {package_name} from {data_source} for the period {start_month} to {end_month}."
        )
        logger.error(e)
        return pd.Series()


@log_function(logger)
def process_conda_repositories(
    package_name: str,
    data_source: str,
    start_month: str,
    end_month: str,
    action: str,
    project: str,
):
    """
    Processes the specified conda repository to fetch download statistics.
    """
    if action == "downloads":
        downloads = get_download_stats(
            package_name=package_name,
            data_source=data_source,
            start_month=start_month,
            end_month=end_month,
        )
        write_stats_response(
            result=downloads,
            project=project,
            package=package_name,
            source=data_source,
            action=action,
        )
