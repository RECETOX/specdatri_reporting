import os
import logging
import orjson
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import configparser
from functools import wraps
from dotenv import load_dotenv


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


def log_function(logger: logging.Logger):
    """
    A decorator that logs the function name, arguments, return value, and exceptions.

    Args:
        logger (logging.Logger): The logger instance to use for logging.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(
                f"Calling function '{func.__name__}' with arguments {args} and keyword arguments {kwargs}"
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
    error_message="Some kind of API error ccured while interacting with the given ERP",
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
        status_forcelist=[403, 406, 408, 413, 429, 500, 502, 503, 504],
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
