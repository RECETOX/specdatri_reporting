import unittest
from unittest.mock import MagicMock, patch
from src.data_sources.github import GitHubDataSource


class TestGitHubDataSource(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.project = "test_project"
        self.package = "test_package"
        self.owner = "test_owner"
        self.repo = "test_repo"
        self.token = "fake_token"
        self.github_ds = GitHubDataSource(
            self.project, self.package, self.owner, self.repo, self.token
        )

    def test_initialization(self):
        """Test that GitHubDataSource initializes correctly."""
        self.assertEqual(self.github_ds.project, self.project)
        self.assertEqual(self.github_ds.package, self.package)
        self.assertEqual(self.github_ds.source, "github")
        self.assertEqual(self.github_ds.owner, self.owner)
        self.assertEqual(self.github_ds.repo, self.repo)
        self.assertEqual(self.github_ds.github_token, self.token)

    def test_get_headers(self):
        """Test that _get_headers returns correct headers."""
        headers = self.github_ds._get_headers()
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")
        self.assertEqual(headers["X-GitHub-Api-Version"], "2022-11-28")
        self.assertEqual(headers["Authorization"], f"Bearer {self.token}")

    @patch("src.data_sources.github.make_api_request")
    def test_fetch_clones_success(self, mock_make_api_request):
        """Test fetching clone statistics successfully."""
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

        result = self.github_ds.fetch(action="clones")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), success_response)
        
        # Verify the correct URL was called
        expected_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/traffic/clones"
        mock_make_api_request.assert_called_once()
        call_kwargs = mock_make_api_request.call_args[1]
        self.assertEqual(call_kwargs["url"], expected_url)
        self.assertEqual(call_kwargs["http_method"], "GET")

    @patch("src.data_sources.github.make_api_request")
    def test_fetch_views_success(self, mock_make_api_request):
        """Test fetching view statistics successfully."""
        success_response = {"count": 20, "uniques": 10}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = success_response
        mock_make_api_request.return_value = mock_response

        result = self.github_ds.fetch(action="views")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), success_response)
        
        # Verify the correct URL was called
        expected_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/traffic/views"
        mock_make_api_request.assert_called_once()
        call_kwargs = mock_make_api_request.call_args[1]
        self.assertEqual(call_kwargs["url"], expected_url)

    @patch("src.data_sources.github.make_api_request")
    def test_fetch_clones_failure(self, mock_make_api_request):
        """Test handling of failed clone statistics request."""
        failure_response = {
            "message": "Not Found",
            "documentation_url": "https://docs.github.com/rest/metrics/traffic#get-repository-clones",
            "status": "404",
        }
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = failure_response
        mock_make_api_request.return_value = mock_response

        result = self.github_ds.fetch(action="clones")
        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.json(), failure_response)

    @patch("src.data_sources.github.make_api_request")
    def test_fetch_views_failure(self, mock_make_api_request):
        """Test handling of failed view statistics request."""
        failure_response = {
            "message": "Not Found",
            "documentation_url": "https://docs.github.com/rest/metrics/traffic#get-repository-views",
            "status": "404",
        }
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = failure_response
        mock_make_api_request.return_value = mock_response

        result = self.github_ds.fetch(action="views")
        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.json(), failure_response)

    def test_fetch_invalid_action(self):
        """Test that fetch raises ValueError for invalid action."""
        with self.assertRaises(ValueError) as context:
            self.github_ds.fetch(action="invalid")
        self.assertIn("Invalid action", str(context.exception))


if __name__ == "__main__":
    unittest.main()
