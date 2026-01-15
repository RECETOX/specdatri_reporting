"""Abstract base class for data sources."""

from abc import ABC, abstractmethod
from typing import Any

import orjson
import pandas as pd
import requests

from src.utils import (
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
    with open(filename, "wb") as f:
        f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))


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
        result (Any): The results from getting a stat.
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


class DataSource(ABC):
    """Abstract base class for fetching download statistics from various sources."""
    
    def __init__(self, project: str, package: str, source: str):
        """
        Initialize the data source.
        
        Args:
            project (str): The project name
            package (str): The package name
            source (str): The source name (e.g., 'pypi', 'github', 'cran', 'bioconda')
        """
        self.project = project
        self.package = package
        self.source = source
    
    @abstractmethod
    def fetch(self, action: str = None, **kwargs) -> Any:
        """
        Fetch data from the source.
        
        Args:
            action (str): The action to perform (optional, source-dependent)
            **kwargs: Source-specific parameters
            
        Returns:
            The fetched data (requests.Response, pd.Series, etc.)
        """
        pass
    
    @log_function(logger)
    def process(self, action: str, **kwargs) -> None:
        """
        Fetch data and write to file using a template method pattern.
        
        Args:
            action (str): The action to perform (e.g., 'downloads', 'clones')
            **kwargs: Source-specific parameters for fetch()
        """
        try:
            result = self.fetch(action=action, **kwargs)
            write_stats_response(result, self.project, self.package, self.source, action)
        except Exception as e:
            logger.error(f"Failed to process {self.source} for {self.project}/{self.package}: {e}")
            raise
