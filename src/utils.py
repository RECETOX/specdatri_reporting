import configparser
import logging
import os
import re
from datetime import datetime
from functools import wraps

import orjson
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Any

# Load .config file from the parent directory
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "..", ".config"))

# Load .env file from the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_env_var(var_name: str, default: str = None) -> str:
    """
    Args:
        var_name (str): The name of the environment variable.
        default (Any): The default value to return if the environment variable does not exist.

    Returns:
        Any: The value of the environment variable or the default value.
    """
    return os.getenv(var_name, default)


def get_config_var(section: str, var_name: str, default: str = None) -> str:
    """
    Args:
        section (str): The section of the configuration file.
        var_name (str): The name of the environment variable.
        default (Any): The default value to return if the environment variable does not exist.

    Returns:
        Any: The value of the environment variable or the default value.
    """
    return config.get(section, var_name, fallback=default)


def get_logger(name: str = "spec-logger", level: int = logging.INFO):
    """
    Returns a logger instance with the given name and log level.

    Args:
        name (str): The name of the logger.
        level (int): The logging level (e.g., logging.INFO, logging.DEBUG).

    Returns:
        logging.Logger: Configured logger instance.

    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # create console handler with the same log level
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def log_function(logger: logging.Logger, obfuscate_keywords=None):
    """
    A decorator that logs the function name, arguments, return value, and exceptions.
    Arguments and keyword arguments containing specified keywords are obfuscated to avoid logging sensitive information.

    Args:
        logger (logging.Logger): The logger instance to use for logging.
        obfuscate_keywords (list): List of keywords to check for obfuscation. Defaults to ["token", "key"].
    """
    if obfuscate_keywords is None:
        obfuscate_keywords = ["token", "key"]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            arg_names = func.__code__.co_varnames[: func.__code__.co_argcount]
            obfuscated_args = [
                (
                    "***"
                    if any(keyword in name for keyword in obfuscate_keywords)
                    else value
                )
                for name, value in zip(arg_names, args)
            ]
            obfuscated_kwargs = {
                k: "***" if any(keyword in k for keyword in obfuscate_keywords) else v
                for k, v in kwargs.items()
            }
            logger.info(
                f"Calling function '{func.__name__}' with arguments {obfuscated_args} and keyword arguments {obfuscated_kwargs}"
            )
            try:
                result = func(*args, **kwargs)
                logger.info(f"Function '{func.__name__}' returned {result}")
                return result
            except Exception as e:
                logger.error(f"Function '{func.__name__}' raised an exception: {e}")
                raise

        return wrapper

    return decorator


def get_failed_response(
    error_message="Some kind of API error ccured while interacting with the given URL.",
) -> requests.Response:
    failed_response = requests.Response()
    failed_response.status_code = 500
    failed_response.reason = error_message
    failed_response._content = orjson.dumps({"message": f"{error_message}"})
    return failed_response


def make_api_request(
    url: str,
    http_method: str = "GET",
    headers: dict = {},
    data: dict = {},
    auth: tuple = (),
    cookies: dict = {},
    params: dict = {},
) -> requests.Response:
    """Makes an API request to the given url with the given parameters."""
    if not all(headers.values()):
        return get_failed_response()
    s = requests.Session()
    retries = Retry(
        total=10,
        backoff_factor=0.1,
        status_forcelist=[408, 429, 500, 502, 503, 504],
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))

    try:
        req = requests.Request(
            http_method,
            url,
            data=data,
            headers=headers,
            auth=auth,
            cookies=cookies,
            params=params,
        )
        prepped = req.prepare()
        resp = s.send(prepped)
        return resp
    except Exception as e:
        get_logger().error("Connection error while fetching data {}".format(e))
        return get_failed_response()


def setup_logger() -> logging.Logger:
    """
    Sets up and returns a logger instance based on the configuration.

    Returns:
        logging.Logger: Configured logger instance.
    """
    debug_mode = get_config_var("DEFAULT", "DEBUG", "False").lower() == "true"
    log_level = logging.DEBUG if debug_mode else logging.INFO
    return get_logger(level=log_level)


def sanitize_filename_component(component: str) -> str:
    """
    Sanitizes a filename component by replacing spaces and special characters with underscores.

    Args:
        component (str): The filename component to sanitize.

    Returns:
        str: The sanitized filename component.
    """
    # Replace spaces and special characters with underscores
    return re.sub(r"[^\w\-]", "_", component)


def write_prep_filename_metadata(
    project: str, package: str, source: str, action: str, filename: str
):
    """
    Writes metadata about the prepared filename to a metadata file.

    Args:
        project (str): The project name.
        package (str): The package name.
        source (str): The source of the data (e.g., "github").
        action (str): The action performed (e.g., "clones" or "views").
        filename (str): The prepared filename.
    """
    metadata = {
        "project": project,
        "package": package,
        "source": source,
        "action": action,
        "filename": filename,
    }
    base_filename = os.path.splitext(filename)[0]
    metadata_filename = f"{base_filename}.metadata.json"
    with open(metadata_filename, "wb") as f:
        f.write(
            orjson.dumps(metadata, option=orjson.OPT_INDENT_2)
        )  # Serialize the data and write it to the file


def prep_filename(
    folder: str,
    project: str,
    package: str,
    source: str,
    action: str,
    extension: str = "json",
) -> str:
    """
    Prepares a filename based on the given parameters.

    Args:
        folder (str): The folder where the file will be saved.
        project (str): The project name.
        package (str): The package name.
        source (str): The source of the data (e.g., "github").
        action (str): The action performed (e.g., "clones" or "views").

    Returns:
        str: The prepared filename.
    """
    now = datetime.now()
    date_part = now.strftime("%Y-%m-%d_%H-%M-%S")
    project = sanitize_filename_component(project)
    package = sanitize_filename_component(package)
    source = sanitize_filename_component(source)
    action = sanitize_filename_component(action)
    seperator = "__"
    return f"{folder}/{project}{seperator}{package}{seperator}{source}{seperator}{action}{seperator}{date_part}.{extension}"


def get_failed_result_json(result: Any) -> dict:
    """
    Extracts and formats the failure details from a given result.

    Args:
        result (Results): A named tuple containing the actual result and its type.

    Returns:
        dict: A dictionary containing the status code, failure message, and the full response text.
    """
    if type(result) is requests.Response:
        return {
            "status": result.status_code,
            "message": result.json().get("message", "Request failed"),
            "response": result.text,
        }
    else:
        return {
            "status": "error",
            "message": "Unknown error type",
            "response": str(result),
        }
