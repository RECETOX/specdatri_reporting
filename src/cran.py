import requests
from .utils import (
    log_function,
    make_api_request,
    setup_logger,
)
from .reports import write_stats_response

logger = setup_logger()


@log_function(logger)
def get_download_stats(
        start_date:str,
        end_date:str,
        package:str,
)->requests.Response:
    """

    """
    url = f"https://cranlogs.r-pkg.org/downloads/daily/{start_date}:{end_date}/{package}"
    response = make_api_request(http_method="GET", url=url)
    return response


@log_function(logger)
def process_cran_repositories(
    package: str,
    start_date: str,
    end_date: str,
    action: str,
    project: str,
):
    """
    Processes the specified CRAN repository to fetch download statistics.
    """
    if action == "downloads":
        downloads = get_download_stats(
            start_date=start_date,
            end_date=end_date,
            package=package,
        )
        write_stats_response(
            result=downloads,
            project=project,
            package=package,
            source="cran",
            action="downloads",
        )
