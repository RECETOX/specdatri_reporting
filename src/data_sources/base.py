"""Abstract base class for data sources."""

from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime

import pandas as pd
import requests

from src.utils import (
    log_function,
    setup_logger,
    get_failed_result_json,
    write_json,
    sanitize_filename_component,
)

logger = setup_logger()


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

    def prep_filename(self, folder: str, action: str, extension: str = "json") -> str:
        """
        Prepares a filename based on the instance's project, package, and source.

        Args:
            folder (str): The folder where the file will be saved.
            action (str): The action performed (e.g., "clones" or "views").
            extension (str): The file extension. Defaults to "json".

        Returns:
            str: The prepared filename.
        """
        now = datetime.now()
        date_part = now.strftime("%Y-%m-%d_%H-%M-%S")
        project = sanitize_filename_component(self.project)
        package = sanitize_filename_component(self.package)
        source = sanitize_filename_component(self.source)
        action = sanitize_filename_component(action)
        part_name = "__".join([date_part, project, package, source, action])
        return f"{folder}/{part_name}.{extension}"

    def write_prep_filename_metadata(self, action: str, filename: str):
        """
        Writes metadata about the prepared filename to a metadata file.

        Args:
            action (str): The action performed (e.g., "clones" or "views").
            filename (str): The prepared filename.
        """
        import os

        metadata = {
            "project": self.project,
            "package": self.package,
            "source": self.source,
            "action": action,
            "filename": filename,
        }
        base_filename = os.path.splitext(filename)[0]
        metadata_filename = f"{base_filename}.metadata.json"
        with open(metadata_filename, "wb") as f:
            import orjson

            f.write(orjson.dumps(metadata, option=orjson.OPT_INDENT_2))

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
    def write_stats_response(self, result: Any, action: str) -> None:
        """
        Processes the response from a make_api_request call and writes the data to a file.

        Args:
            result (Any): The results from getting a stat.
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
                filename = self.prep_filename("failed", action)
                write_json(failed_response, filename)
                self.write_prep_filename_metadata(action, filename)
                return
            filename = self.prep_filename("tmp", action)
            write_json(data, filename)
            self.write_prep_filename_metadata(action, filename)
        except Exception as e:
            logger.error(
                f"Failed to write {action} to file for {self.project} and {self.package}. {e}"
            )
            failed_response = get_failed_result_json(result)
            filename = self.prep_filename("failed", action)
            write_json(failed_response, filename)
            self.write_prep_filename_metadata(action, filename)

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
            self.write_stats_response(result, action)
        except Exception as e:
            logger.error(
                f"Failed to process {self.source} for {self.project}/{self.package}: {e}"
            )
            raise
