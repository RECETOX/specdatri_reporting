import unittest
from unittest.mock import mock_open, patch

import orjson

from src.reports import write_json


class TestReports(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open)
    @patch("src.reports.orjson.dumps")
    def test_write_json(self, mock_dumps, mock_open):
        # Mock the return value of orjson.dumps
        mock_dumps.return_value = b'{"key": "value"}'

        # Data to be serialized
        data = {"key": "value"}
        filename = "test.json"

        # Call the function
        write_json(data, filename)

        # Assert that orjson.dumps was called with the correct data and options
        mock_dumps.assert_called_once_with(data, option=orjson.OPT_INDENT_2)

        # Assert that the file was opened in binary write mode
        mock_open.assert_called_once_with(filename, "wb")

        # Assert that the data was written to the file
        mock_open().write.assert_called_once_with(b'{"key": "value"}')


if __name__ == "__main__":
    unittest.main()
