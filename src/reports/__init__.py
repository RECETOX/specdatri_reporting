"""
Unified reporting framework for download statistics.

This package provides an object-oriented framework for generating TSV reports
from different data sources (Bioconda, PyPI, GitHub) with consistent handling
of data aggregation, completeness checking, and report generation.
"""

from .base import ReportGenerator
from .bioconda import BiocondaReportGenerator
from .cran import CRANReportGenerator
from .github import GitHubReportGenerator
from .pypi import PyPIReportGenerator

__all__ = [
    "ReportGenerator",
    "BiocondaReportGenerator",
    "CRANReportGenerator",
    "PyPIReportGenerator",
    "GitHubReportGenerator",
]
