import unittest
from unittest.mock import MagicMock, patch
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
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), success_response)

    @patch("src.github.make_api_request")
    def test_get_clone_stats_failure(self, mock_make_api_request):
        failure_response = {"message": "Not Found", "documentation_url": "https://docs.github.com/rest/metrics/traffic#get-repository-clones", "status": "404"}
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = failure_response
        mock_make_api_request.return_value = mock_response

        result = get_clone_stats("owner", "repo", "fake_token")
        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.json(), failure_response)

    @patch("src.github.make_api_request")
    def test_get_repo_views_success(self, mock_make_api_request):
        success_response = {"count": 20, "uniques": 10}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = success_response
        mock_make_api_request.return_value = mock_response

        result = get_repo_views("owner", "repo", "fake_token")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), success_response)

    @patch("src.github.make_api_request")
    def test_get_repo_views_failure(self, mock_make_api_request):
        failure_response = {"message": "Not Found", "documentation_url": "https://docs.github.com/rest/metrics/traffic#get-repository-views", "status": "404"}
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = failure_response
        mock_make_api_request.return_value = mock_response

        result = get_repo_views("owner", "repo", "fake_token")
        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.json(), failure_response)

if __name__ == '__main__':
    unittest.main()
