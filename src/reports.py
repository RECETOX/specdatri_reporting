import orjson
import requests
import pandas as pd
from typing import Any

from .utils import (
    log_function,
    setup_logger,
    prep_filename,
    write_prep_filename_metadata,
    get_failed_result_json,
)

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
def write_stats_response(
    result: Any,
    project: str,
    package: str,
    source: str,
    action: str,
):
    """
    Processes the response from a make_api_request call and writes the data to a file.

    Args:
        response (tuple): The results from getting a stat.
        filename (str): The filename to write the data to.
        project (str): The project name.
        package (str): The package name.
        source (str): The source of the data (e.g., "github").
        action (str): The action performed (e.g., "clones" or "views").
    """
    try:
        if type(result) is requests.Response:
            data = result.json()
        elif type(result) is pd.Series:
            data = result.to_dict()
            if isinstance(data, list):
                data = [{str(k): v for k, v in item.items()} for item in data]
            else:
                data = {str(k): v for k, v in data.items()}
        else:
            logger.error(f"Unexpected result type: {result.response_type}")
            failed_response = get_failed_result_json(result)
            filename = prep_filename("failed", project, package, source, action)
            write_json(data, filename)
            write_prep_filename_metadata(project, package, source, action, filename)
            return
        filename = prep_filename("tmp", project, package, source, action)
        write_json(data, filename)
        write_prep_filename_metadata(project, package, source, action, filename)
    except Exception as e:
        logger.error(f"Failed to write {action} to file for {project} and {package}. {e}")
        failed_response = get_failed_result_json(result)
        filename = prep_filename("failed", project, package, source, action)
        write_json(failed_response, filename)
        write_prep_filename_metadata(project, package, source, action, filename)
