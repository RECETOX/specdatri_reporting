import pandas as pd
from pandas import DataFrame
from dotenv import load_dotenv
import os


# Load environment variables from .env file
load_dotenv()


def load_repositories(file_path: str) -> DataFrame:
    """
    Reads a list of repositories from a TSV file and returns it as a DataFrame.

    :param file_path: Path to the TSV file containing the list of repositories.
    :return: DataFrame containing the list of repositories.
    """
    return pd.read_csv(file_path, sep='\t')


def main():
    repo_file_path = os.getenv('REPO_FILE_PATH')
    if repo_file_path:
        repositories_df = load_repositories(repo_file_path)
        print(repositories_df)
    else:
        print("REPO_FILE_PATH not found in .env file")


if __name__ == "__main__":
    main()
