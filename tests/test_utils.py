import unittest
from unittest.mock import patch, MagicMock
import logging
from src.utils import (
    get_config_var,
    get_logger,
    log_function,
    get_failed_response,
    make_api_request,
    get_env_var,
)


class TestUtils(unittest.TestCase):

    @patch("src.utils.config")
    def test_get_config_var(self, mock_config):
        mock_config.get.return_value = "test_value"
        result = get_config_var("DEFAULT", "TEST_VAR", "default_value")
        self.assertEqual(result, "test_value")
        mock_config.get.assert_called_once_with(
            "DEFAULT", "TEST_VAR", fallback="default_value"
        )

    def test_get_logger(self):
        logger = get_logger("test-logger", logging.DEBUG)
        self.assertEqual(logger.name, "test-logger")
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertTrue(
            any(
                isinstance(handler, logging.StreamHandler)
                for handler in logger.handlers
            )
        )

    @patch("src.utils.logging.Logger")
    def test_log_function(self, MockLogger):
        mock_logger = MockLogger.return_value

        @log_function(mock_logger)
        def sample_function(x, y):
            return x + y

        result = sample_function(2, 3)
        self.assertEqual(result, 5)
        mock_logger.info.assert_any_call(
            "Calling function 'sample_function' with arguments (2, 3) and keyword arguments {}"
        )
        mock_logger.info.assert_any_call("Function 'sample_function' returned 5")

        @log_function(mock_logger)
        def sample_function_exception(x, y):
            raise ValueError("An error occurred")

        with self.assertRaises(ValueError):
            sample_function_exception(2, 3)
        mock_logger.error.assert_any_call(
            "Function 'sample_function_exception' raised an exception: An error occurred"
        )

    def test_get_failed_response(self):
        error_message = "Test error message"
        response = get_failed_response(error_message)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.reason, error_message)
        self.assertEqual(response.json(), {"message": error_message})

    @patch("src.utils.requests.Session")
    def test_make_api_request_success(self, MockSession):
        mock_response = MagicMock()
        mock_response.status_code = 200
        MockSession.return_value.send.return_value = mock_response

        url = "http://example.com"
        headers = {"Authorization": "Bearer token"}
        response = make_api_request(url, headers=headers)

        self.assertEqual(response.status_code, 200)
        MockSession.return_value.send.assert_called_once()

    @patch("src.utils.requests.Session")
    def test_make_api_request_failure(self, MockSession):
        mock_response = MagicMock()
        mock_response.status_code = 500
        MockSession.return_value.send.return_value = mock_response

        url = "http://example.com"
        headers = {"Authorization": ""}
        response = make_api_request(url, headers=headers)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "message": "Some kind of API error ccured while interacting with the given URL."
            },
        )
        MockSession.return_value.send.assert_not_called()

    @patch("src.utils.requests.Session")
    @patch("src.utils.get_logger")
    def test_make_api_request_exception(self, MockLogger, MockSession):
        MockSession.return_value.send.side_effect = Exception("Connection error")

        url = "http://example.com"
        headers = {"Authorization": "Bearer token"}
        response = make_api_request(url, headers=headers)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "message": "Some kind of API error ccured while interacting with the given URL."
            },
        )
        MockLogger.return_value.error.assert_called_once_with(
            "Connection error while fetching data Connection error"
        )

    @patch("src.utils.os.getenv")
    def test_get_env_var(self, mock_getenv):
        # Test when the environment variable is set
        mock_getenv.return_value = "test_value"
        result = get_env_var("TEST_VAR", "default_value")
        self.assertEqual(result, "test_value")
        mock_getenv.assert_called_once_with("TEST_VAR", "default_value")

        # Reset mock for the next test
        mock_getenv.reset_mock()

        # Test when the environment variable is not set
        mock_getenv.side_effect = lambda _, default=None: default
        result = get_env_var("NON_EXISTENT_VAR")
        self.assertEqual(result, None)
        mock_getenv.assert_called_with("NON_EXISTENT_VAR", None)

        # Test that default value works
        result = get_env_var("NON_EXISTENT_VAR", "default_value")
        self.assertEqual(result, "default_value")
        mock_getenv.assert_called_with("NON_EXISTENT_VAR", "default_value")


if __name__ == "__main__":
    unittest.main()
