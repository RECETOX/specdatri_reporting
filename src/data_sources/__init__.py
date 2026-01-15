"""
Data sources package for fetching download statistics from various sources.

This package provides an object-oriented framework for fetching download statistics
from different data sources (PyPI, GitHub, CRAN, Bioconda) with consistent handling
of API calls and response writing.
"""

from .base import DataSource
from .conda import CondaDataSource
from .cran import CRANDataSource
from .github import GitHubDataSource
from .pypi import PyPIDataSource

__all__ = [
    "DataSource",
    "PyPIDataSource",
    "GitHubDataSource",
    "CRANDataSource",
    "CondaDataSource",
]
