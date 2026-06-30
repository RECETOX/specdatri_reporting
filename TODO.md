# Plan: Add Galaxy Tool Usage Statistics Collection

## Overview

This document outlines the steps to add functionality for collecting Galaxy tool usage statistics from the research-software-ecosystem GitHub repository, following the existing OO architecture for PyPI, CRAN, Bioconda, and GitHub data sources.

**Key Design Decision**: Galaxy instances are configured via a separate config file (similar to `repository_list.tsv`), allowing multiple Galaxy instances to be tracked per tool without requiring individual CLI entries for each instance.

---

## Background

The existing framework consists of:
- **Data Sources** (`src/data_sources/`): OO hierarchy with `DataSource` base class implementing `fetch()` and `process()` methods
- **Report Generators** (`src/reports/`): OO hierarchy with `ReportGenerator` base class for aggregating collected JSON data into TSV reports
- **CLI** (`src/cli.py`): Commands for `add-repo`, `collect-stats`, `generate-reports`, and `generate-dashboard`
- **GitHub Actions** (`.github/workflows/actions.yml`): Automated weekly collection pipeline

Galaxy data is available at: `https://github.com/research-software-ecosystem/content/tree/master/imports/galaxy/`

**Repository scale**: ~1,674 Galaxy tool packages available.

---

## Validated Data Structure

After inspecting multiple Galaxy JSON files (`bioconductor_scp.galaxy.json`, `aoptk.galaxy.json`, `abricate.galaxy.json`, `multiqc.galaxy.json`, `10x_bamtofastq.galaxy.json`, `adapter_removal.galaxy.json`), the following patterns are confirmed:

### Consistent Field Naming Pattern

All files use the **same** naming convention for runs and users:

```
Suite_runs_(<instance>)           # e.g., Suite_runs_(usegalaxy.eu)
Suite_users_(<instance>)          # e.g., Suite_users_(usegalaxy.org.au)
Suite_runs_(last_5_years)_(<instance>)  # e.g., Suite_runs_(last_5_years)_(usegalaxy.fr)
Suite_users_(last_5_years)_(<instance>)
Suite_runs_on_main_servers        # Aggregate across all main servers
Suite_users_on_main_servers
Suite_runs_(last_5_years)_on_main_servers
Suite_users_(last_5_years)_on_main_servers
```

### Common Galaxy Instances Found

| Instance | Key Pattern |
|----------|-------------|
| usegalaxy.eu | `(usegalaxy.eu)` |
| usegalaxy.org | `(usegalaxy.org)` |
| usegalaxy.org.au | `(usegalaxy.org.au)` |
| usegalaxy.fr | `(usegalaxy.fr)` |

### Additional Metadata Fields

- `Suite_ID`: Unique identifier (e.g., "abricate", "multiqc")
- `Suite_conda_package`: Conda package name
- `Suite_owner`: Tool suite owner (e.g., "iuc", "bgruening")
- `Suite_first_commit_date`: ISO date string
- `Suite_version`: Version number
- `bio.tool_name`: Human-readable tool name
- `bio.tool_description`: Tool description
- `EDAM_operations`: List of EDAM operation terms
- `EDAM_topics`: List of EDAM topic terms
- `Number_of_tools_on_<server>`: Tool count on specific server (NOT run/user stats)

### Important Notes

1. **Instance names in keys use lowercase** with underscores (e.g., `usegalaxy.eu`, NOT `UseGalaxy.eu`)
2. **Parentheses are part of the key name** (e.g., `(usegalaxy.eu)`)
3. **Some tools may have zero counts** for certain instances (still present in JSON)
4. **`Number_of_tools_on_*` fields are NOT run/user statistics** - they indicate how many tools from the suite exist on that server

---

## Architecture Overview

### Configuration Files

1. **`repository_list.tsv`** - Lists projects/packages to track (unchanged)
   ```
   repository	project	package	source	action
   RECETOX/scp	scp	bioconductor_scp	Galaxy	runs
   RECETOX/scp	scp	bioconductor_scp	Galaxy	users
   ```

2. **`galaxy_instances.tsv`** (NEW) - Lists Galaxy instances to aggregate across
   ```
   instance_name	key_pattern	enabled
   usegalaxy.eu	(usegalaxy.eu	true
   usegalaxy.org	(usegalaxy.org)	true
   usegalaxy.org.au	(usegalaxy.org.au)	true
   usegalaxy.fr	(usegalaxy.fr)	true
   ```

The data source will:
- Read all enabled instances from `galaxy_instances.tsv`
- Fetch the single Galaxy JSON file for each tracked tool
- Extract stats using the key pattern `<metric>_<key_pattern>` (e.g., `Suite_runs_(usegalaxy.eu)`)
- Write a combined JSON file containing all instance data

---

## Phase 1: Configuration File Support

### 1.1 Create Galaxy Instances Config File

**File**: `galaxy_instances.tsv` (new file in project root)

**Task**: Create default configuration file with common Galaxy instances

**Content**:
```tsv
instance_name	key_pattern	enabled
usegalaxy.eu	(usegalaxy.eu	true
usegalaxy.org	(usegalaxy.org)	true
usegalaxy.org.au	(usegalaxy.org.au)	true
usegalaxy.fr	(usegalaxy.fr)	true
```

**Testing approach**:
- Test file parsing with valid TSV
- Test handling of missing file (default to bundled defaults)
- Test filtering by `enabled` column

### 1.2 Add Config File Utility Functions

**File**: `src/utils.py` (or new `src/config.py`)

**Tasks**:
- Add `read_galaxy_instances(config_path: Path) -> List[dict]` function
- Similar pattern to existing `read_existing_entries()` in cli.py but for galaxy instances
- Return list of dicts with keys: `instance_name`, `key_pattern`, `enabled`

**Testing approach**:
- Unit tests for parsing logic
- Edge cases: empty file, malformed rows, missing columns

---

## Phase 2: Data Source Implementation

### 2.1 Create Galaxy Data Source Module

**File**: `src/data_sources/galaxy.py`

**Task**: Implement `GalaxyDataSource` class extending `DataSource`

**Requirements**:
- Constructor accepts: `project`, `package`, `config_path` (path to `galaxy_instances.tsv`), `github_token`
- Implements `fetch(action, **kwargs)` method:
  - Reads enabled Galaxy instances from config file
  - Downloads single JSON from `https://raw.githubusercontent.com/research-software-ecosystem/content/master/imports/galaxy/{package}.galaxy.json`
  - For each enabled instance, extracts stats using key pattern:
    - Runs: `f"Suite_runs_{key_pattern}"` → e.g., `Suite_runs_(usegalaxy.eu)`
    - Users: `f"Suite_users_{key_pattern}"` → e.g., `Suite_users_(usegalaxy.org.au)`
  - Returns dict mapping instance_name → stats (e.g., `{"usegalaxy.eu": {"runs": 156, "users": 34}, ...}`)
  - Falls back to bundled default instances if config file missing
- Uses existing `make_api_request()` utility
- Handles missing files gracefully (404 → empty result for all instances)
- Handles missing keys gracefully (instance not in JSON → 0 or None)

**Key design**: One fetch call returns data for all instances, minimizing API calls.

**Testing approach**:
- Unit test with mocked HTTP responses
- Test key pattern construction and extraction
- Test handling of missing config file
- Test handling of missing/invalid Galaxy JSON files
- Test handling of instances with zero counts
- Mock the GitHub raw content endpoint

### 2.2 Register Galaxy Data Source

**File**: `src/data_sources/__init__.py`

**Task**: Export `GalaxyDataSource` in module's `__all__` list

---

## Phase 3: Report Generator Implementation

### 3.1 Create Galaxy Report Generator Module

**File**: `src/reports/galaxy.py`

**Task**: Implement `GalaxyReportGenerator` class extending `ReportGenerator`

**Requirements**:
- Constructor accepts: `tmp_dir`, `output_path`
- Implements required abstract methods:
  - `get_file_pattern()`: Returns `"*__galaxy__*.json"`
  - `should_include_file(parsed)`: Filters by year
  - `get_period_key(date)`: Returns monthly key like `"2025-01"`
  - `get_period_label()`: Returns `"month"`
  - `aggregate_data(file_path)`: Aggregates runs/users by month, with per-instance breakdown

**Data aggregation strategy**:
- Parse filename metadata to identify project/package
- Load JSON containing all instance data
- For each instance, extract runs/users counts
- Group by time period (monthly)
- Output TSV format options (see Open Questions below)

**Testing approach**:
- Test file pattern matching
- Test period key generation
- Test aggregation logic with sample data containing multiple instances
- Test handling of missing months
- Test filtering by year

### 3.2 Register Galaxy Report Generator

**File**: `src/reports/__init__.py`

**Task**: Export `GalaxyReportGenerator` in module's `__all__` list

---

## Phase 4: CLI Integration

### 4.1 Extend `add-repo` Command

**File**: `src/cli.py`

**Tasks**:

1. **Add import** for Galaxy-related functions

2. **Add `--galaxy` flag** to `add_repo` command:
   ```python
   @click.option("--galaxy", is_flag=True, help="Add Galaxy tool usage entry")
   ```

3. **Update `generate_new_entries()` function**:
   - Accept `has_galaxy` parameter
   - When `has_galaxy` is True, generate ONE entry per action type (not per instance):
     ```python
     if has_galaxy:
         # Single entry for runs - data source will fetch all instances
         entries.append({
             "repository": repository,
             "project": project,
             "package": package,  # e.g., "bioconductor_scp"
             "source": "Galaxy",
             "action": "runs",
         })
         entries.append({
             "repository": repository,
             "project": project,
             "package": package,
             "source": "Galaxy",
             "action": "users",
         })
     ```

4. **Update error message** to include `--galaxy` as valid option

**Testing approach**:
- Test CLI argument parsing with `--galaxy` flag
- Test entry generation (single entry, not duplicated per instance)
- Verify TSV output format

### 4.2 Extend `collect-stats` Command

**File**: `src/cli.py`

**Tasks**:

1. **Update `process_repositories()` function**:
   - Add branch for `source == "galaxy"`
   - Instantiate `GalaxyDataSource` with config path
   - Call `process(action)` for each action type (runs, users)
   - The data source internally handles all instances

2. **Config file path handling**:
   - Default to `galaxy_instances.tsv` in project root
   - Allow override via `--galaxy-config` option (optional)

**Testing approach**:
- Integration test with mocked data source returning multi-instance data
- Verify correct instantiation and method calls
- Verify single JSON fetch results in multiple instance records

### 4.3 Extend `generate-reports` Command

**File**: `src/cli.py`

**Tasks**:

1. **Add import** for `GalaxyReportGenerator`

2. **Add Galaxy report section** in `generate_reports()` function:
   ```python
   # Galaxy
   click.echo("\n6. Galaxy Report")
   click.echo("-" * 60)
   output_file = output_path / str(year) / "galaxy_runs.tsv"
   generator = GalaxyReportGenerator(tmp_path, output_file)
   generator.create_report(year=year)

   # Optionally generate users report separately
   output_file = output_path / str(year) / "galaxy_users.tsv"
   generator = GalaxyReportGenerator(tmp_path, output_file)
   generator.create_report(year=year)
   ```

**Testing approach**:
- Test report generation with multi-instance sample data
- Verify TSV output format includes instance information
- Test aggregation across instances

---

## Phase 5: Documentation Updates

### 5.1 Update README.md

**Sections to update**:

1. **Overview table** - Add Galaxy row:
   | Platform | Metric | Aggregation |
   |----------|--------|-------------|
   | [Galaxy](https://galaxyproject.org/) | Tool runs/users (multi-instance) | Monthly |

2. **Configuration section** - Document `galaxy_instances.tsv`:
   ```markdown
   ### Galaxy Instance Configuration

   Galaxy statistics are collected from multiple Galaxy instances configured in `galaxy_instances.tsv`:

   ```tsv
   instance_name	key_pattern	enabled
   usegalaxy.eu	(usegalaxy.eu	true
   usegalaxy.org.au	usegalaxy.org.au	true
   ```

   Set `enabled` to `false` to temporarily disable an instance without deleting it.
   ```

3. **User Guide** - Add Galaxy examples:
   ```bash
   # Add a Galaxy tool (automatically tracks all configured instances)
   ./specdatri add-repo --project bioconductor_scp --galaxy
   ```

4. **Developer Guide** - Document Galaxy integration

### 5.2 Create Data Source Documentation

**File**: `src/data_sources/README.md` (extend existing)

**Content**:
- Architecture overview
- How to add new data sources
- Specific notes for Galaxy data source (multi-instance configuration, key pattern matching)

### 5.3 Create Report Generator Documentation

**File**: `src/reports/README.md` (extend existing)

**Content**:
- Architecture overview
- How to add new report types
- Specific notes for Galaxy report generator (per-instance breakdown)

---

## Phase 6: Testing Strategy

### 6.1 Unit Tests for Config Parsing

**File**: `tests/test_galaxy_config.py`

**Test cases**:
1. `TestReadGalaxyInstances`:
   - Test parsing valid TSV file
   - Test filtering by enabled status
   - Test handling of missing file
   - Test handling of malformed rows

### 6.2 Unit Tests for Galaxy Data Source

**File**: `tests/test_galaxy.py`

**Test cases**:
1. `TestGalaxyDataSourceInitialization`:
   - Test constructor parameters
   - Test config file loading

2. `TestGalaxyDataSourceFetch`:
   - Test successful JSON download with multiple instances
   - Test key pattern construction: `Suite_runs_(<instance>)`
   - Test extraction of runs for all instances
   - Test extraction of users for all instances
   - Test handling of missing Galaxy JSON file
   - Test handling of malformed JSON
   - Test handling of missing config file (fallback to defaults)
   - Test handling of instances with zero counts

3. `TestGalaxyDataSourceProcess`:
   - Test orchestration of fetch → write_stats_response
   - Test exception handling

### 6.3 Unit Tests for Galaxy Report Generator

**File**: `tests/test_galaxy.py` (same file, separate test class)

**Test cases**:
1. `TestGalaxyReportGeneratorInitialization`:
   - Test constructor parameters

2. `TestGalaxyReportGeneratorMethods`:
   - Test `get_file_pattern()` returns correct pattern
   - Test `get_period_key()` generates correct monthly keys
   - Test `get_period_label()` returns "month"

3. `TestGalaxyReportGeneratorAggregation`:
   - Test aggregation with multiple instances
   - Test per-instance breakdown in output
   - Test handling of missing months
   - Test filtering by year

4. `TestGalaxyReportGeneration`:
   - Test full report creation with multi-instance data
   - Test TSV output format includes instance column
   - Test preservation of existing data

### 6.4 Integration Tests

**File**: `tests/test_integration.py` (optional, if not exists)

**Test cases**:
1. End-to-end flow: add-repo → collect-stats → generate-reports
2. Test with realistic mock data simulating actual Galaxy JSON with multiple instances
3. Test config file modification affects collected data

### 6.5 Running Tests

```bash
# Run Galaxy-specific tests
python -m unittest tests.test_galaxy tests.test_galaxy_config

# Run with coverage
coverage run -m unittest discover -s tests
coverage report -m
```

---

## Phase 7: GitHub Actions Integration

### 7.1 Update Workflow to Include Config File

**File**: `.github/workflows/actions.yml`

**Tasks**:
- Ensure `galaxy_instances.tsv` is committed and tracked
- No other workflow changes required since:
  - The `collect-stats` command now handles Galaxy entries automatically
  - The `generate-reports` command includes Galaxy report generation

### 7.2 Add Example Config to Documentation

Include example `galaxy_instances.tsv` in README showing common Galaxy instances.

---

## Implementation Order Summary

| Priority | Phase | Tasks | Estimated Complexity |
|----------|-------|-------|---------------------|
| 1 | 1 | Create config file support + utilities | Low |
| 2 | 2 | Create `GalaxyDataSource` (multi-instance) | Medium |
| 3 | 3 | Create `GalaxyReportGenerator` | Medium |
| 4 | 4 | Update CLI commands | Low-Medium |
| 5 | 6 | Write unit tests | Medium-High |
| 6 | 5 | Update documentation | Low |
| 7 | 7 | Update GitHub Actions | Low |

---

## Code Quality Checklist

Before merging:
- [ ] All unit tests pass
- [ ] Coverage meets project threshold (>80%)
- [ ] Code follows existing patterns
- [ ] Type hints added where appropriate
- [ ] Docstrings complete
- [ ] Pre-commit hooks pass
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] `galaxy_instances.tsv` included in repository

---

## Open Questions / Decisions Needed

1. **Default instances**: Should we bundle a default set of Galaxy instances, or require explicit config file?

2. **Report format**: Per-instance columns in TSV (wide format) or one row per instance (long format)?
   - Wide: `month | project | usegalaxy.eu | usegalaxy.org | ...`
   - Long: `month | project | instance | runs`

3. **Config file location**: Project root (`galaxy_instances.tsv`) or under a config directory (`config/galaxy_instances.tsv`)?

4. **Instance naming in config**: Store just the instance name (`usegalaxy.eu`) or the full key suffix (`(usegalaxy.eu)`)?

---

## Notes on Testing Approach

### Mocking Strategy

For unit tests, mock at these boundaries:

1. **HTTP layer**: Use `unittest.mock.patch` to simulate API responses
2. **File I/O**: Use `mock_open` for file operations
3. **Timestamps**: Mock `datetime.now()` for reproducible filename tests
4. **Config file**: Create temp config files for testing different scenarios

### Sample Multi-Instance Test Data

Based on validated data structure:

```python
SAMPLE_GALAXY_JSON = {
    "Suite_ID": "abricate",
    "bio.tool_name": "ABRicate",
    "Suite_runs_(usegalaxy.org.au)": 600408,
    "Suite_users_(usegalaxy.org.au)": 2216,
    "Suite_runs_(usegalaxy.eu)": 821957,
    "Suite_users_(usegalaxy.eu)": 4679,
    "Suite_runs_(usegalaxy.org)": 405363,
    "Suite_users_(usegalaxy.org)": 3468,
    "Suite_runs_(usegalaxy.fr)": 19178,
    "Suite_users_(usegalaxy.fr)": 85,
}

EXPECTED_FETCH_RESULT = {
    "usegalaxy.org.au": {"runs": 600408, "users": 2216},
    "usegalaxy.eu": {"runs": 821957, "users": 4679},
    "usegalaxy.org": {"runs": 405363, "users": 3468},
    "usegalaxy.fr": {"runs": 19178, "users": 85},
}
```

---

## References

- Existing data source: [src/data_sources/github.py](src/data_sources/github.py)
- Existing report: [src/reports/github.py](src/reports/github.py)
- Base classes: [src/data_sources/base.py](src/data_sources/base.py), [src/reports/base.py](src/reports/base.py)
- Existing config pattern: `repository_list.tsv` usage in [src/cli.py](src/cli.py)
- Galaxy example data:
  - https://github.com/research-software-ecosystem/content/blob/master/imports/galaxy/bioconductor_scp.galaxy.json
  - https://github.com/research-software-ecosystem/content/blob/master/imports/galaxy/abricate.galaxy.json
  - https://github.com/research-software-ecosystem/content/blob/master/imports/galaxy/multiqc.galaxy.json
