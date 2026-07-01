"""Dashboard generator for download statistics visualization.

This module generates an interactive HTML dashboard that can be served
statically on GitHub Pages. It uses Altair (Vega-Lite) for charts and
includes filtering capabilities, summary statistics, and per-project tables.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def load_tsv(path: Path) -> Optional[pd.DataFrame]:
    """Load a TSV report file and return a tidy (long-form) DataFrame.

    Parameters
    ----------
    path:
        Absolute path to the TSV file.

    Returns
    -------
    DataFrame with columns ``period``, ``package``, ``count``, or *None* if
    the file cannot be read.
    """
    try:
        df = pd.read_csv(path, sep="\t", dtype=str, on_bad_lines="skip")
    except Exception as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    if df.empty or df.columns.size < 2:
        return None

    period_col = df.columns[0]
    df = df.rename(columns={period_col: "period"})

    # Melt to long form
    df = df.melt(id_vars="period", var_name="package", value_name="count")
    df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
    df = df[df["count"] > 0].reset_index(drop=True)

    return df


def load_all_data(reports_dir: Path) -> dict:
    """Load all TSV reports from *reports_dir* (all year sub-directories).

    Returns a dict mapping report-type label to long-form DataFrame, e.g::

        {
            "PyPI Downloads": <DataFrame>,
            "Bioconda Downloads": <DataFrame>,
            "CRAN Downloads": <DataFrame>,
            "GitHub Clones": <DataFrame>,
            "GitHub Views": <DataFrame>,
            "Galaxy Runs": <DataFrame>,
            "Galaxy Users": <DataFrame>,
        }
    """
    report_specs = {
        "pypi_downloads.tsv": "PyPI Downloads",
        "bioconda_downloads.tsv": "Bioconda Downloads",
        "cran_downloads.tsv": "CRAN Downloads",
        "github_clones.tsv": "GitHub Clones",
        "github_views.tsv": "GitHub Views",
        "galaxy_runs.tsv": "Galaxy Runs",
        "galaxy_users.tsv": "Galaxy Users",
    }

    collected: dict[str, list[pd.DataFrame]] = {v: [] for v in report_specs.values()}

    for year_dir in sorted(reports_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        for filename, label in report_specs.items():
            tsv_path = year_dir / filename
            if tsv_path.exists():
                df = load_tsv(tsv_path)
                if df is not None and not df.empty:
                    collected[label].append(df)

    result = {}
    for label, frames in collected.items():
        if frames:
            merged = pd.concat(frames, ignore_index=True)
            # De-duplicate: if the same period+package appears in multiple
            # yearly files, keep the maximum (most complete) value.
            merged = merged.groupby(["period", "package"], as_index=False)[
                "count"
            ].max()
            merged = merged.sort_values("period").reset_index(drop=True)
            result[label] = merged

    return result


def get_all_packages(data: dict) -> list[str]:
    """Extract unique package names across all data sources."""
    packages = set()
    for df in data.values():
        packages.update(df["package"].unique())
    return sorted(packages)


def compute_summary_stats(data: dict) -> dict:
    """Compute overall summary statistics across all data sources."""
    stats = {}

    for label, df in data.items():
        total = int(df["count"].sum())
        num_packages = len(df["package"].unique())
        num_periods = len(df["period"].unique())

        # Find top package
        pkg_totals = df.groupby("package")["count"].sum()
        top_pkg = pkg_totals.idxmax() if not pkg_totals.empty else "N/A"
        top_count = int(pkg_totals.max()) if not pkg_totals.empty else 0

        stats[label] = {
            "total": total,
            "packages": num_packages,
            "periods": num_periods,
            "top_package": top_pkg,
            "top_count": top_count,
        }

    return stats


# ---------------------------------------------------------------------------
# Altair chart builders
# ---------------------------------------------------------------------------


def _y_title_for(label: str) -> str:
    """Return y-axis title for a given data source label."""
    titles = {
        "GitHub Clones": "Clones",
        "GitHub Views": "Views",
        "Galaxy Runs": "Runs",
        "Galaxy Users": "Active Users",
    }
    return titles.get(label, "Downloads")


def build_overall_chart(data: dict) -> str:
    """Build a combined overview chart showing all data sources normalized.

    Returns Vega-Lite spec as JSON string with inline data values.
    """

    # Combine all data with a source column
    rows = []
    for label, df in data.items():
        for _, row in df.iterrows():
            rows.append({
                "source": label,
                "period": row["period"],
                "package": row["package"],
                "count": row["count"],
            })

    if not rows:
        return json.dumps({})

    # Build chart spec manually to ensure inline data works in browser
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
        "data": {"values": rows},
        "mark": {"type": "line", "point": True},
        "encoding": {
            "x": {"field": "period", "type": "ordinal", "title": "Period",
                  "axis": {"labelAngle": -45}},
            "y": {"field": "count", "type": "quantitative", "title": "Count"},
            "color": {"field": "package", "type": "nominal", "legend": {"title": "Package"}},
            "tooltip": [
                {"field": "source", "type": "nominal", "title": "Source"},
                {"field": "period", "type": "ordinal", "title": "Period"},
                {"field": "package", "type": "nominal", "title": "Package"},
                {"field": "count", "type": "quantitative", "title": "Count", "format": ",d"}
            ]
        },
        "height": 300,
        "width": "container",
        "params": [{
            "name": "zoom",
            "select": {"type": "interval", "encodings": ["x", "y"]},
            "bind": "scales"
        }]
    }

    return json.dumps(spec)


def build_filtered_chart(df: pd.DataFrame, y_title: str) -> str:
    """Build an interactive line chart with zoom/pan support.

    Parameters
    ----------
    df:
        Long-form DataFrame with columns ``period``, ``package``, ``count``.
    y_title:
        Label shown on the y-axis.

    Returns
    -------
    Vega-Lite spec as JSON string with inline data values.
    """

    # Build chart spec manually to ensure inline data works in browser
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
        "data": {"values": df.to_dict(orient="records")},
        "mark": {"type": "line", "point": True},
        "encoding": {
            "x": {
                "field": "period",
                "type": "ordinal",
                "title": "Period",
                "axis": {"labelAngle": -45, "labelOverlap": False}
            },
            "y": {"field": "count", "type": "quantitative", "title": y_title},
            "color": {"field": "package", "type": "nominal", "legend": {"title": "Package"}},
            "tooltip": [
                {"field": "period", "type": "ordinal", "title": "Period"},
                {"field": "package", "type": "nominal", "title": "Package"},
                {"field": "count", "type": "quantitative", "title": y_title, "format": ",d"}
            ]
        },
        "height": 350,
        "width": "container",
        "params": [{
            "name": "zoom",
            "select": {"type": "interval", "encodings": ["x", "y"]},
            "bind": "scales"
        }]
    }

    return json.dumps(spec)


def build_bar_chart_by_package(df: pd.DataFrame, y_title: str) -> str:
    """Build a bar chart showing total counts per package.

    Returns Vega-Lite spec as JSON string with inline data values.
    """

    pkg_totals = df.groupby("package", as_index=False)["count"].sum()
    pkg_totals = pkg_totals.sort_values("count", ascending=True)

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
        "data": {"values": pkg_totals.to_dict(orient="records")},
        "mark": "bar",
        "encoding": {
            "x": {"field": "count", "type": "quantitative", "title": y_title},
            "y": {"field": "package", "type": "nominal", "title": "Package", "sort": "-x"},
            "tooltip": [
                {"field": "package", "type": "nominal", "title": "Package"},
                {"field": "count", "type": "quantitative", "title": y_title, "format": ",d"}
            ]
        },
        "height": max(200, len(pkg_totals) * 30),
        "width": "container"
    }

    return json.dumps(spec)


def _chart_spec(label: str, df: pd.DataFrame) -> str:
    """Return the Vega-Lite JSON spec string for *label*."""
    y_title = _y_title_for(label)
    chart = build_filtered_chart(df, y_title)
    return chart


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------


def _summary_cards(data: dict) -> str:
    """Return Bootstrap card HTML for per-source totals."""
    icons = {
        "PyPI Downloads": "📦",
        "Bioconda Downloads": "🐍",
        "CRAN Downloads": "📊",
        "GitHub Clones": "🔁",
        "GitHub Views": "👁️",
        "Galaxy Runs": "⚙️",
        "Galaxy Users": "👥",
    }
    cards_html = []
    for label, df in data.items():
        total = int(df["count"].sum())
        icon = icons.get(label, "📈")
        cards_html.append(f"""
        <div class="col">
          <div class="card h-100 text-center shadow-sm hover-lift">
            <div class="card-body">
              <div style="font-size:2rem">{icon}</div>
              <h6 class="card-subtitle mb-1 text-muted">{label}</h6>
              <p class="card-text fs-4 fw-bold">{total:,}</p>
            </div>
          </div>
        </div>""")
    return "\n".join(cards_html)


def _overall_stats_table(stats: dict) -> str:
    """Return HTML table with detailed statistics per data source."""
    rows = []
    for label, s in stats.items():
        rows.append(f"""
        <tr>
          <td>{label}</td>
          <td>{s['total']:,}</td>
          <td>{s['packages']}</td>
          <td>{s['periods']}</td>
          <td><strong>{s['top_package']}</strong></td>
          <td>{s['top_count']:,}</td>
        </tr>""")

    return f"""
    <div class="card shadow-sm">
      <div class="card-header bg-light">
        <h5 class="mb-0">📊 Overall Statistics</h5>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-striped table-hover mb-0">
            <thead class="table-light">
              <tr>
                <th>Data Source</th>
                <th>Total Count</th>
                <th>Packages</th>
                <th>Periods</th>
                <th>Top Package</th>
                <th>Top Count</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
        </div>
      </div>
    </div>"""


def _filter_panel(packages: list[str]) -> str:
    """Return HTML filter panel with checkboxes for packages."""
    checkbox_html = []
    for i, pkg in enumerate(packages):
        checked = "checked" if i < 10 else ""  # Pre-select first 10
        checkbox_html.append(f"""
          <div class="form-check form-check-inline">
            <input class="form-check-input package-filter" type="checkbox"
                   id="filter-{pkg}" value="{pkg}" {checked}>
            <label class="form-check-label" for="filter-{pkg}">{pkg}</label>
          </div>""")

    return f"""
    <div class="card shadow-sm mb-4">
      <div class="card-header bg-light d-flex justify-content-between align-items-center">
        <h5 class="mb-0">🔍 Filter by Package</h5>
        <div>
          <button class="btn btn-sm btn-outline-primary" id="select-all">Select All</button>
          <button class="btn btn-sm btn-outline-secondary" id="clear-all">Clear All</button>
        </div>
      </div>
      <div class="card-body">
        {''.join(checkbox_html)}
      </div>
    </div>"""


def _data_tables(data: dict) -> str:
    """Return collapsible data tables for each data source."""
    tables = []
    for label, df in data.items():
        slug = label.lower().replace(" ", "-")

        # Prepare table data
        rows = []
        for _, row in df.iterrows():
            rows.append(f'<tr><td>{row["period"]}</td><td>{row["package"]}</td><td>{row["count"]:,}</td></tr>')

        y_title = _y_title_for(label)

        tables.append(f"""
        <div class="card shadow-sm mb-4" id="table-card-{slug}">
          <div class="card-header bg-light d-flex justify-content-between align-items-center">
            <h5 class="mb-0">{label} Data</h5>
            <button class="btn btn-sm btn-outline-primary toggle-table"
                    data-target="table-{slug}">
              Show Table
            </button>
          </div>
          <div class="collapse" id="table-{slug}">
            <div class="card-body p-0">
              <div class="table-responsive">
                <table class="table table-sm table-hover mb-0" id="table-{slug}">
                  <thead class="table-light">
                    <tr>
                      <th>Period</th>
                      <th>Package</th>
                      <th>{y_title}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {''.join(rows[:100])}
                    {'<tr><td colspan="3" class="text-center text-muted">... truncated ...</td></tr>' if len(rows) > 100 else ''}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>""")

    return "\n".join(tables)


def _per_project_section(data: dict) -> str:
    """Return section with per-project breakdown charts and tables."""
    packages = get_all_packages(data)

    sections = []
    for pkg in packages:
        slug = pkg.replace("/", "-").replace("_", "-")

        # Gather data for this package across all sources
        pkg_rows = []
        has_data = False
        for label, df in data.items():
            pkg_df = df[df["package"] == pkg]
            if not pkg_df.empty:
                has_data = True
                for _, row in pkg_df.iterrows():
                    pkg_rows.append({
                        "source": label,
                        "period": row["period"],
                        "count": row["count"],
                    })

        if not has_data:
            continue

        pkg_data = pd.DataFrame(pkg_rows)
        pkg_data_json = pkg_data.to_json(orient="records")

        # Build a proper Vega-Lite spec for this package's data
        pkg_chart_spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
            "data": {"values": json.loads(pkg_data_json)},
            "mark": {"type": "line", "point": True},
            "encoding": {
                "x": {"field": "period", "type": "ordinal", "title": "Period"},
                "y": {"field": "count", "type": "quantitative", "title": "Count"},
                "color": {"field": "source", "type": "nominal", "title": "Source"},
                "tooltip": [
                    {"field": "source", "type": "nominal", "title": "Source"},
                    {"field": "period", "type": "ordinal", "title": "Period"},
                    {"field": "count", "type": "quantitative", "title": "Count", "format": ",d"}
                ]
            },
            "height": 250,
            "width": "container"
        }
        pkg_chart_spec_json = json.dumps(pkg_chart_spec)

        sections.append(f"""
        <div class="card shadow-sm mb-4 project-section" data-package="{pkg}">
          <div class="card-header bg-light">
            <h5 class="mb-0">📁 Project: {pkg}</h5>
          </div>
          <div class="card-body">
            <div id="project-chart-{slug}"></div>
            <script>
              (function() {{
                const spec = {pkg_chart_spec_json};
                vegaEmbed('#project-chart-{slug}', spec, {{ actions: false }})
                  .catch(console.error);
              }})();
            </script>
          </div>
        </div>""")

    return "\n".join(sections) if sections else '<p class="text-muted">No per-project data available.</p>'


def generate_dashboard(reports_dir: Path, output_file: Path) -> None:
    """Read TSV reports and write a self-contained HTML dashboard.

    The generated dashboard includes:
    - Summary cards with total counts per data source
    - Overall statistics table
    - Interactive charts with package filtering
    - Per-project breakdown sections
    - Collapsible data tables

    Parameters
    ----------
    reports_dir:
        Root directory that contains year sub-directories (e.g. ``reports/``).
    output_file:
        Path where the HTML file will be written.
    """
    data = load_all_data(reports_dir)

    if not data:
        logger.error("No report data found in %s", reports_dir)
        raise FileNotFoundError(f"No report data found in {reports_dir}")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    packages = get_all_packages(data)
    stats = compute_summary_stats(data)

    # Build chart specs
    overall_chart_spec = build_overall_chart(data)

    # Build chart specs (for embedding in JS below)
    overall_chart_spec_json = build_overall_chart(data)

    # Generate HTML components
    summary_cards_html = _summary_cards(data)
    stats_table_html = _overall_stats_table(stats)
    filter_panel_html = _filter_panel(packages)
    data_tables_html = _data_tables(data)
    per_project_html = _per_project_section(data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>RECETOX – Download Statistics Dashboard</title>
  <link
    rel="stylesheet"
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
    crossorigin="anonymous"
  />
  <style>
    body {{ background: #f0f2f5; }}
    .navbar {{ background: linear-gradient(135deg, #0d6efd, #0a58ca); }}
    .tab-content {{ background: #fff; border: 1px solid #dee2e6;
                    border-top: none; padding: 1.25rem; border-radius: 0 0 .375rem .375rem; }}
    .nav-tabs .nav-link.active {{ font-weight: 600; }}
    .summary-cards {{ margin-bottom: 1.5rem; }}
    footer {{ font-size: .8rem; color: #6c757d; text-align: center; margin: 2rem 0 1rem; }}
    .hover-lift {{ transition: transform 0.2s ease, box-shadow 0.2s ease; }}
    .hover-lift:hover {{ transform: translateY(-4px); box-shadow: 0 0.5rem 1rem rgba(0,0,0,.15)!important; }}
    .package-filter {{ margin-right: 0.5rem; }}
    .chart-container {{ min-height: 400px; margin: 1rem 0; }}
    .section-title {{ border-left: 4px solid #0d6efd; padding-left: 1rem; margin: 2rem 0 1rem; }}
    /* Scrollable filter panel */
    .filter-scroll {{ max-height: 300px; overflow-y: auto; }}
  </style>
</head>
<body>
  <nav class="navbar navbar-dark mb-4">
    <div class="container-fluid px-4">
      <span class="navbar-brand fw-bold">
        📊 RECETOX – Download Statistics Dashboard
      </span>
      <span class="navbar-text text-white">
        Interactive analytics for package downloads and usage
      </span>
    </div>
  </nav>

  <div class="container-fluid px-4">

    <!-- Summary cards -->
    <h5 class="section-title">📈 Summary Overview</h5>
    <div class="row row-cols-2 row-cols-sm-3 row-cols-lg-5 g-3 summary-cards">
      {summary_cards_html}
    </div>

    <!-- Overall statistics table -->
    <h5 class="section-title">📋 Detailed Statistics</h5>
    {stats_table_html}

    <!-- Main charts section -->
    <h5 class="section-title">📊 Trend Charts</h5>
    {filter_panel_html}

    <!-- Overall trends chart -->
    <div class="card shadow-sm mb-4">
      <div class="card-header bg-light">
        <h5 class="mb-0">All Sources Combined</h5>
      </div>
      <div class="card-body">
        <div id="overall-chart" class="chart-container"></div>
      </div>
    </div>

    <!-- Per-data-source charts -->
    <div class="accordion mb-4" id="source-accordion">
"""

    # Add accordion items for each data source
    for i, (label, df) in enumerate(data.items()):
        active = "show" if i == 0 else ""
        slug = label.lower().replace(" ", "-")
        y_title = _y_title_for(label)

        chart_spec = _chart_spec(label, df)
        barchart_spec = build_bar_chart_by_package(df, y_title)

        # Use single braces for JavaScript - not inside an f-string for the script parts
        html += f"""
      <div class="accordion-item">
        <h2 class="accordion-header" id="heading-{slug}">
          <button class="accordion-button {active}" type="button"
                  data-bs-toggle="collapse" data-bs-target="#collapse-{slug}"
                  aria-expanded="{'true' if i == 0 else 'false'}" aria-controls="collapse-{slug}">
            {label}
          </button>
        </h2>
        <div class="accordion-collapse collapse {active}" id="collapse-{slug}"
             aria-labelledby="heading-{slug}" data-bs-parent="#source-accordion">
          <div class="accordion-body">
            <div id="chart-{slug}" class="chart-container"></div>
            <script>
              vegaEmbed('#chart-{slug}', {chart_spec}, {{ actions: true }})
                .catch(console.error);
            </script>
            <hr/>
            <h6>Bar Chart: Total by Package</h6>
            <div id="barchart-{slug}"></div>
            <script>
              (function() {{
                var spec = {barchart_spec};
                vegaEmbed('#barchart-{slug}', spec, {{ actions: false }});
              }})();
            </script>
          </div>
        </div>
      </div>"""

    html += """
    </div>

    <!-- Per-project sections -->
    <h5 class="section-title">📁 Per-Project Breakdown</h5>
    <div class="row">
      <div class="col-12">
        """ + per_project_html + """
      </div>
    </div>

    <!-- Data tables -->
    <h5 class="section-title">📄 Raw Data Tables</h5>
    """ + data_tables_html + """

  </div>

  <footer>
    <div class="container">
      <p>Generated by <strong>specdatri</strong> · data sourced from PyPI, Bioconda, CRAN, GitHub, and Galaxy</p>
      <p class="mb-0">Last updated: """ + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M UTC") + """</p>
    </div>
  </footer>

  <!-- Bootstrap JS -->
  <script
    src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
    integrity="sha384-YvpcrYf0tY3lHB60NNkmXc4s9bIOgUxi8T/jzmB7sQEq87UEJ9w6N3EFUfg7/rM"
    crossorigin="anonymous"
  ></script>
  <!-- Vega / Vega-Lite / Vega-Embed (used by Altair charts) -->
  <script src="https://cdn.jsdelivr.net/npm/vega@6" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@6.1.0" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@7" crossorigin="anonymous"></script>

  <!-- Dashboard interactivity scripts -->
  <script>
"""

    # Build JavaScript separately to avoid f-string brace escaping issues
    js_parts = []

    # Overall chart embedding - use JSON.stringify to properly embed the spec
    js_parts.append(f"""
    // Overall chart embedding
    (async function() {{
      const overallSpec = JSON.parse({json.dumps(overall_chart_spec_json)});
      if (overallSpec && Object.keys(overallSpec).length > 0) {{
        await vegaEmbed('#overall-chart', overallSpec, {{ actions: true }});
      }}
    }})();
""")

    # Package filter functionality
    js_parts.append("""
    // Package filter functionality - filters per-project sections by selected packages
    function applyPackageFilter() {
      const checked = Array.from(document.querySelectorAll('.package-filter:checked'))
                        .map(cb => cb.value.toLowerCase());
      console.log('Selected packages:', checked);

      // Hide/show per-project sections based on selection
      document.querySelectorAll('.project-section').forEach(section => {
        const pkg = section.getAttribute('data-package').toLowerCase();
        if (checked.includes(pkg)) {
          section.style.display = 'block';
        } else {
          section.style.display = 'none';
        }
      });
    }

    document.querySelectorAll('.package-filter').forEach(cb => {
      cb.addEventListener('change', applyPackageFilter);
    });
""")

    # Select All / Clear All buttons
    js_parts.append("""
    // Select All / Clear All buttons
    document.getElementById('select-all')?.addEventListener('click', function() {
      document.querySelectorAll('.package-filter').forEach(cb => cb.checked = true);
      applyPackageFilter();
    });

    document.getElementById('clear-all')?.addEventListener('click', function() {
      document.querySelectorAll('.package-filter').forEach(cb => cb.checked = false);
      applyPackageFilter();
    });
""")

    # Toggle table visibility
    js_parts.append("""
    // Toggle table visibility
    document.querySelectorAll('.toggle-table').forEach(function(btn) {
      btn.addEventListener('click', function() {
        const target = btn.getAttribute('data-target');
        const collapse = document.getElementById(target);
        if (collapse) {
          const isCollapsed = !collapse.classList.contains('show');
          btn.textContent = isCollapsed ? 'Hide Table' : 'Show Table';
        }
      });
    });
""")


    html += "\n".join(js_parts)
    html += """
  </script>
</body>
</html>
"""

    output_file.write_text(html, encoding="utf-8")
    logger.info("Dashboard written to %s", output_file)
