# Reports Package

A modular Python package for generating download statistics reports from multiple data sources.

## Package Structure

```
reports/
├── __init__.py          # Package initialization, exports all classes
├── base.py             # Abstract base class (ReportGenerator)
├── bioconda.py         # Bioconda report generator
├── pypi.py             # PyPI report generator
└── github.py           # GitHub report generator
```

## Module Organization

### `base.py` - Core Framework
Contains the `ReportGenerator` abstract base class that provides:
- File parsing and discovery
- Existing report loading
- Period filtering
- Data matrix building
- TSV writing
- Statistics tracking

**Abstract methods** that subclasses must implement:
- `get_file_pattern()` - Glob pattern for file discovery
- `should_include_file()` - File filtering logic
- `get_period_key()` - Date to period conversion
- `get_period_label()` - Period column label
- `aggregate_data()` - Data extraction and aggregation

### `bioconda.py` - Bioconda Reports
Handles Bioconda download statistics:
- **Source**: Pre-aggregated monthly data
- **Period**: Monthly (`YYYY-MM`)
- **Completeness**: All months marked complete
- **Output**: `reports/YYYY/bioconda_downloads.tsv`

### `pypi.py` - PyPI Reports
Handles PyPI download statistics:
- **Source**: Daily download data
- **Period**: Monthly (`YYYY-MM`)
- **Completeness**: Month complete if adjacent months (n-1, n+1) have data
- **Output**: `reports/YYYY/pypi_downloads.tsv`

### `github.py` - GitHub Reports
Handles GitHub clone/view statistics:
- **Source**: GitHub API (2-week windows)
- **Period**: Weekly (ISO format `YYYY-Wxx`)
- **Completeness**: Week complete if entirely within file's coverage window
- **Output**: `reports/YYYY/github_clones.tsv` and `github_views.tsv`

## Usage

### Importing Classes

```python
# Import all classes
from reports import (
    ReportGenerator,
    BiocondaReportGenerator,
    PyPIReportGenerator,
    GitHubReportGenerator
)

# Or import specific classes
from reports.bioconda import BiocondaReportGenerator
from reports.pypi import PyPIReportGenerator
from reports.github import GitHubReportGenerator
```

### Creating Reports

```python
from pathlib import Path
from reports import BiocondaReportGenerator, PyPIReportGenerator, GitHubReportGenerator

# Bioconda
bioconda = BiocondaReportGenerator(
    tmp_dir=Path('tmp'),
    output_path=Path('reports/2025/bioconda_downloads.tsv'),
    year=2025
)
bioconda.create_report(year=2025)

# PyPI
pypi = PyPIReportGenerator(
    tmp_dir=Path('tmp'),
    output_path=Path('reports/2025/pypi_downloads.tsv'),
    year=2025
)
pypi.create_report(year=2025)

# GitHub
github_clones = GitHubReportGenerator(
    tmp_dir=Path('tmp'),
    output_path=Path('reports/2025/github_clones.tsv'),
    year=2025,
    stat_type='clones'
)
github_clones.create_report(year=2025)
```

## Extending the Package

### Adding a New Report Type

1. Create a new module in the `reports/` directory:

```python
# reports/cran.py
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from .base import ReportGenerator


class CRANReportGenerator(ReportGenerator):
    """Generator for CRAN download reports."""
    
    def __init__(self, tmp_dir: Path, output_path: Path, year: int):
        super().__init__(tmp_dir, output_path)
        self.year = year
    
    def get_file_pattern(self) -> str:
        return "*__cran__downloads.json"
    
    def should_include_file(self, parsed: Tuple) -> bool:
        return parsed[0].year == self.year
    
    def get_period_key(self, date: datetime) -> str:
        return f"{date.year:04d}-{date.month:02d}"
    
    def get_period_label(self) -> str:
        return "month"
    
    def aggregate_data(self, file_path: Path) -> Dict[str, Tuple[int, bool]]:
        # Implement data extraction logic
        pass
```

2. Export the class in `__init__.py`:

```python
from .cran import CRANReportGenerator

__all__ = [
    'ReportGenerator',
    'BiocondaReportGenerator',
    'PyPIReportGenerator',
    'GitHubReportGenerator',
    'CRANReportGenerator',  # Add new class
]
```

## Benefits of Package Structure

1. **Modularity**: Each report type is self-contained in its own module
2. **Maintainability**: Changes to one report type don't affect others
3. **Discoverability**: Easy to find and understand each component
4. **Testing**: Each module can be tested independently
5. **Extensibility**: New report types can be added without modifying existing code
6. **Import flexibility**: Import only what you need

## Migration from Monolithic Module

The package maintains backward compatibility with the original `reports.py` module:

```python
# Old way (still works if reports.py exists)
from reports import BiocondaReportGenerator

# New way (package structure)
from reports import BiocondaReportGenerator  # Same import!
```

The import statements in existing code don't need to change. The package `__init__.py` exports all classes at the package level.

## Development Guidelines

When adding new report generators:

1. **Inherit from `ReportGenerator`**: Use the abstract base class
2. **Implement all abstract methods**: Required for functionality
3. **Follow naming conventions**: `<Source>ReportGenerator` class name
4. **Use type hints**: Maintain type safety
5. **Document thoroughly**: Include docstrings for all methods
6. **Handle errors gracefully**: Catch and log exceptions appropriately
7. **Add to `__init__.py`**: Export the new class
8. **Create wrapper script**: Add `report_<source>_v2.py` for CLI access
