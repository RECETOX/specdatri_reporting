import orjson
from .utils import setup_logger, log_function

logger = setup_logger()


@log_function(logger)
def write_json(data, filename):
    """
    Serializes the given data to JSON and writes it to the specified file.

    Args:
        data (Any): The data to serialize.
        filename (str): The name of the file to write the JSON data to.
    """
    with open(filename, 'wb') as f:  # Open the file in binary write mode
        f.write(
            orjson.dumps(
                data, option=orjson.OPT_INDENT_2
            )
        )  # Serialize the data and write it to the file
