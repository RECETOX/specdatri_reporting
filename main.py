import logging
import pandas as pd
from pandas import DataFrame
from src.utils import get_config_var, get_logger, log_function

# Create a logger instance
debug_mode = get_config_var("DEFAULT", "DEBUG", "False").lower() == "true"
log_level = logging.DEBUG if debug_mode else logging.INFO
logger = get_logger(level=log_level)


@log_function(logger)
def load_repositories(
    file_path: str,
) -> DataFrame:
    """
    Reads a list of repositories from a TSV file and returns it as a DataFrame.

    :param file_path: Path to the TSV file containing the list of repositories.
    :return: DataFrame containing the list of repositories.
    """
    return pd.read_csv(file_path, sep="\t")


@log_function(logger)
def main():
    repo_file_path = get_config_var("DEFAULT", "REPO_FILE_PATH")
    if repo_file_path:
        logger.info("REPO_FILE_PATH found in .config file")
        repositories_df = load_repositories(repo_file_path)
        logger.debug(f"Repositories DataFrame: \n{repositories_df}")
    else:
        logger.error("REPO_FILE_PATH not found in .config file")
        print("REPO_FILE_PATH not found in .config file")


if __name__ == "__main__":
    main()
