import requests
from .utils import (
    log_function,
    make_api_request,
    setup_logger,
)
from .reports import write_stats_response

logger = setup_logger()


@log_function(logger)
def get_pypi_downloads(
    package_name: str,
    pepy_x_api_key: str,
) -> requests.Response:
    """
    Fetches the download statistics for a given PyPI package.

    Returns:
        dict: A dictionary containing the download statistics.
    """

    url = f"https://api.pepy.tech/api/v2/projects/{package_name}"
    headers = {"X-API-Key": pepy_x_api_key}
    response = make_api_request(http_method="GET", url=url, headers=headers)
    return response


@log_function(logger)
def process_pypi_repositories(
    package: str,
    pepy_x_api_key: str,
    action: str,
    project: str,
):
    """
    Fetches the download statistics for a given PyPI package.

    Args:
        package (str): The name of the PyPI package.
        pepy_x_api_key (str): The PyPI API key.
        action (str): The action to perform.
        project (str): The name of the project.

    Returns:
        None
    """
    if action == "downloads":
        downloads = get_pypi_downloads(package, pepy_x_api_key)
        write_stats_response(downloads, project, package, "pypi", action)
    else:
        logger.error(f"Unknown action: {action}")
