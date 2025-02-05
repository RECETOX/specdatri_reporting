import unittest
from unittest.mock import patch, MagicMock
from src.github import get_clone_stats, get_repo_views


class TestGitHubAPI(unittest.TestCase):

    @patch("src.github.make_api_request")
    def test_get_clone_stats_success(self, mock_make_api_request):
        success_response = {
            "count": 3,
            "uniques": 3,
            "clones": [
                {"timestamp": "2025-01-31T00:00:00Z", "count": 2, "uniques": 2},
                {"timestamp": "2025-02-03T00:00:00Z", "count": 1, "uniques": 1},
            ],
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = success_response
        mock_make_api_request.return_value = mock_response

        result = get_clone_stats("owner", "repo", "fake_token")
        self.assertEqual(result, success_response)

    @patch("src.github.make_api_request")
    def test_get_clone_stats_failure(self, mock_make_api_request):
        failure_response = {"status": 404, "message": "Not Found"}
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = failure_response
        mock_make_api_request.return_value = mock_response

        result = get_clone_stats("owner", "repo", "fake_token")
        self.assertEqual(result["status"], failure_response["status"])
        self.assertEqual(result["message"], failure_response["message"])

    @patch("src.github.make_api_request")
    def test_get_repo_views_success(self, mock_make_api_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 20, "uniques": 10}
        mock_make_api_request.return_value = mock_response

        result = get_repo_views("owner", "repo", "fake_token")
        self.assertEqual(result, {"count": 20, "uniques": 10})

    @patch("src.github.make_api_request")
    def test_get_repo_views_failure(self, mock_make_api_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_make_api_request.return_value = mock_response

        result = get_repo_views("owner", "repo", "fake_token")
        self.assertEqual(result["status"], mock_response.status_code)


if __name__ == "__main__":
    unittest.main()
