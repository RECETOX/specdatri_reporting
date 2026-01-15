# Data Sources Package Refactoring

## Overview

The `src/data_sources/` package is a refactored, object-oriented framework for fetching download statistics from various sources. It replaces the previous function-based approach in `src/pypi.py`, `src/github.py`, `src/cran.py`, and `src/conda.py` with a unified OOP architecture.

## Architecture

### Base Class: `DataSource`

**File**: `src/data_sources/base.py`

Abstract base class implementing the **Template Method Pattern**:

```python
class DataSource(ABC):
    def __init__(self, project: str, package: str, source: str)
    
    @abstractmethod
    def fetch(self, **kwargs) -> Any
        """Implemented by each subclass to fetch from its specific source."""
    
    def process(self, action: str, **kwargs) -> None
        """Template method: calls fetch() and write_stats_response()."""
```

**Key Features**:
- Unified `process()` method handles common workflow: fetch → write response
- Abstract `fetch()` requires each source to implement its own API logic
- Consistent error handling across all sources
- Uses decorator `@log_function(logger)` for logging

### Concrete Implementations

#### 1. PyPIDataSource

**File**: `src/data_sources/pypi.py`

```python
class PyPIDataSource(DataSource):
    def __init__(self, project: str, package: str, pepy_x_api_key: str)
    
    def fetch(self, **kwargs) -> requests.Response
        """Calls PePy API endpoint."""
```

**Usage in `src/pypi.py`**:
```python
data_source = PyPIDataSource(project, package, pepy_x_api_key)
data_source.process(action)
```

#### 2. GitHubDataSource

**File**: `src/data_sources/github.py`

```python
class GitHubDataSource(DataSource):
    def __init__(self, project: str, package: str, owner: str, repo: str, github_token: str)
    
    def fetch(self, action: str = 'clones', **kwargs) -> requests.Response
        """Calls GitHub API for clones or views based on action parameter."""
```

**Usage in `src/github.py`**:
```python
data_source = GitHubDataSource(project, package, owner, repo, github_token)
data_source.process(action)  # action is 'clones' or 'views'
```

#### 3. CRANDataSource

**File**: `src/data_sources/cran.py`

```python
class CRANDataSource(DataSource):
    def __init__(self, project: str, package: str)
    
    def fetch(self, start_date: str, end_date: str, **kwargs) -> requests.Response
        """Calls CRAN logs API."""
```

**Usage in `src/cran.py`**:
```python
data_source = CRANDataSource(project, package)
data_source.process(action, start_date=start_date, end_date=end_date)
```

#### 4. CondaDataSource

**File**: `src/data_sources/conda.py`

```python
class CondaDataSource(DataSource):
    def __init__(self, project: str, package: str, data_source: str)
    
    def fetch(self, start_month: str, end_month: str, **kwargs) -> pd.Series
        """Calls condastats API."""
```

**Usage in `src/conda.py`**:
```python
conda_source = CondaDataSource(project, package_name, data_source)
conda_source.process(action, start_month=start_month, end_month=end_month)
```

## Code Reduction

| Module | Before | After | Reduction |
|--------|--------|-------|-----------|
| `src/pypi.py` | 44 lines | 18 lines | 59% ↓ |
| `src/github.py` | 94 lines | 32 lines | 66% ↓ |
| `src/cran.py` | 45 lines | 28 lines | 38% ↓ |
| `src/conda.py` | 60 lines | 30 lines | 50% ↓ |
| **Total** | **243 lines** | **108 lines** | **56% ↓** |

New data sources package: **192 lines** (shared infrastructure)

**Net result**: Reduced main module complexity while centralizing common patterns.

## Refactoring Benefits

1. **DRY (Don't Repeat Yourself)**
   - Eliminated identical `process_*_repositories()` patterns
   - Consolidated error handling and logging
   - Single `process()` implementation serving all sources

2. **Template Method Pattern**
   - Consistent workflow: fetch → write
   - Subclasses only implement source-specific fetch logic
   - Easy to add new sources (just inherit and implement `fetch()`)

3. **Cleaner Module Interfaces**
   - Original modules now contain only public API functions
   - All complexity hidden in data sources package
   - Easier to test, maintain, and extend

4. **Type Safety**
   - Abstract base class enforces interface compliance
   - IDE autocomplete works across all sources
   - Clear parameter expectations for each source

5. **Separation of Concerns**
   - **Data Sources Package**: How to fetch from each API
   - **Original Modules**: Public function interfaces (backward compatible)
   - **Reports Module**: How to write fetched data

## Migration Path

All original `process_*_repositories()` functions remain unchanged from the caller's perspective. They now simply delegate to the data sources:

```python
# Before: Multiple functions with duplicated logic
get_pypi_downloads() → write_stats_response()
get_clone_stats() → write_stats_response()
get_repo_views() → write_stats_response()
get_download_stats() → write_stats_response()

# After: Unified template pattern
PyPIDataSource.process() → fetch() → write_stats_response()
GitHubDataSource.process() → fetch() → write_stats_response()
CRANDataSource.process() → fetch() → write_stats_response()
CondaDataSource.process() → fetch() → write_stats_response()
```

## Package Structure

```
src/
├── data_sources/
│   ├── __init__.py          # Package exports
│   ├── base.py              # Abstract DataSource class (42 lines)
│   ├── pypi.py              # PyPIDataSource (26 lines)
│   ├── github.py            # GitHubDataSource (46 lines)
│   ├── cran.py              # CRANDataSource (38 lines)
│   └── conda.py             # CondaDataSource (40 lines)
├── pypi.py                  # Refactored (18 lines)
├── github.py                # Refactored (32 lines)
├── cran.py                  # Refactored (28 lines)
├── conda.py                 # Refactored (30 lines)
├── reports.py               # Unchanged
└── utils.py                 # Unchanged
```

## Example Usage

### Using Individual Data Sources Directly

```python
from src.data_sources import PyPIDataSource, GitHubDataSource

# PyPI
pypi = PyPIDataSource('MyProject', 'my-package', 'api-key')
pypi.process('downloads')

# GitHub (clones)
github = GitHubDataSource('MyProject', 'repo', 'owner', 'repo-name', 'token')
github.process('clones')

# GitHub (views)
github.process('views')
```

### Using Module-Level Functions (Backward Compatible)

```python
from src import pypi, github, cran, conda

# Original interfaces still work
pypi.process_pypi_repositories(
    package='my-package',
    pepy_x_api_key='key',
    action='downloads',
    project='MyProject'
)

github.process_github_repositories(
    owner='owner',
    repo='repo',
    github_token='token',
    action='clones',
    project='MyProject',
    package='repo'
)
```

## Testing

All modules compile without syntax errors:
```bash
python3 -m py_compile src/data_sources/*.py src/pypi.py src/github.py src/cran.py src/conda.py
```

Import verification:
```python
from src.data_sources import PyPIDataSource, GitHubDataSource, CRANDataSource, CondaDataSource
```

## Future Enhancements

1. **New Sources**: Add `NPMDataSource`, `RubyGemsDataSource`, etc. by inheriting from `DataSource`
2. **Caching**: Implement caching layer in base class
3. **Retries**: Add exponential backoff for failed requests
4. **Async**: Convert to async/await for parallel source fetching
5. **Validation**: Add response schema validation before writing
