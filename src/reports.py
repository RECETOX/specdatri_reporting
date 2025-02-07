import orjson
import requests

from .utils import log_function, setup_logger, prep_filename, write_prep_filename_metadata, get_failed_response_json

logger = setup_logger()


@log_function(logger)
def write_json(data, filename):
    """
    Serializes the given data to JSON and writes it to the specified file.

    Args:
        data (Any): The data to serialize.
        filename (str): The name of the file to write the JSON data to.
    """
    with open(filename, "wb") as f:  # Open the file in binary write mode
        f.write(
            orjson.dumps(data, option=orjson.OPT_INDENT_2)
        )  # Serialize the data and write it to the file


@log_function(logger)
def write_make_request_response(
    response: requests.Response,
    project: str,
    package: str,
    source: str,
    action: str,
):
    """
    Processes the response from a make_api_request call and writes the data to a file.

    Args:
        response (requests.Response): The response from the API request.
        filename (str): The filename to write the data to.
        project (str): The project name.
        package (str): The package name.
        source (str): The source of the data (e.g., "github").
        action (str): The action performed (e.g., "clones" or "views").
    """
    try:
        data = response.json()
        filename = prep_filename("tmp", project, package, source, action)
        write_json(data, filename)
        write_prep_filename_metadata(project, package, source, action, filename)
    except Exception:
        logger.error(
            f"Failed to fetch {action} status_code: {response.status_code} {response.text}"
        )
        failed_response = get_failed_response_json(response)
        filename = prep_filename("tmp", project, package, source, action)
        write_json(failed_response, filename)
        write_prep_filename_metadata(project, package, source, action, filename)
