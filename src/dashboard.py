"""Dashboard generator for download statistics visualization."""

import logging
from pathlib import Path
from typing import Optional

import altair as alt
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

    Returns a dict mapping report-type label → long-form DataFrame, e.g.::

        {
            "PyPI Downloads": <DataFrame>,
            "Bioconda Downloads": <DataFrame>,
            "CRAN Downloads": <DataFrame>,
            "GitHub Clones": <DataFrame>,
            "GitHub Views": <DataFrame>,
        }
    """
    report_specs = {
        "pypi_downloads.tsv": "PyPI Downloads",
        "bioconda_downloads.tsv": "Bioconda Downloads",
        "cran_downloads.tsv": "CRAN Downloads",
        "github_clones.tsv": "GitHub Clones",
        "github_views.tsv": "GitHub Views",
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
            merged = (
                merged.groupby(["period", "package"], as_index=False)["count"]
                .max()
            )
            merged = merged.sort_values("period").reset_index(drop=True)
            result[label] = merged

    return result


# ---------------------------------------------------------------------------
# Altair chart builders
# ---------------------------------------------------------------------------


def _build_chart(df: pd.DataFrame, y_title: str) -> alt.Chart:
    """Return an interactive Altair line chart for *df*.

    Parameters
    ----------
    df:
        Long-form DataFrame with columns ``period``, ``package``, ``count``.
    y_title:
        Label shown on the y-axis (e.g. ``"Downloads"`` or ``"Views"``).
    """
    return (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "period:O",
                title="Period",
                axis=alt.Axis(labelAngle=-45, labelOverlap=False),
            ),
            y=alt.Y("count:Q", title=y_title),
            color=alt.Color("package:N", legend=alt.Legend(title="Package")),
            tooltip=[
                alt.Tooltip("period:O", title="Period"),
                alt.Tooltip("package:N", title="Package"),
                alt.Tooltip("count:Q", title=y_title, format=",d"),
            ],
        )
        .properties(width="container", height=420)
        .interactive()
    )


def _chart_spec(label: str, df: pd.DataFrame) -> str:
    """Return the Vega-Lite JSON spec string for *label*."""
    _y_titles = {
        "GitHub Clones": "Clones",
        "GitHub Views": "Views",
    }
    y_title = _y_titles.get(label, "Downloads")
    chart = _build_chart(df, y_title)
    return chart.to_json()


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
    }
    cards_html = []
    for label, df in data.items():
        total = int(df["count"].sum())
        icon = icons.get(label, "📈")
        cards_html.append(f"""
        <div class="col">
          <div class="card h-100 text-center shadow-sm">
            <div class="card-body">
              <div style="font-size:2rem">{icon}</div>
              <h6 class="card-subtitle mb-1 text-muted">{label}</h6>
              <p class="card-text fs-4 fw-bold">{total:,}</p>
            </div>
          </div>
        </div>""")
    return "\n".join(cards_html)


def _tab_nav(labels: list[str]) -> str:
    """Return Bootstrap tab nav HTML."""
    items = []
    for i, label in enumerate(labels):
        active = "active" if i == 0 else ""
        selected = "true" if i == 0 else "false"
        slug = label.lower().replace(" ", "-")
        items.append(
            f'<li class="nav-item" role="presentation">'
            f'<button class="nav-link {active}" id="tab-{slug}" '
            f'data-bs-toggle="tab" data-bs-target="#pane-{slug}" '
            f'type="button" role="tab" aria-selected="{selected}">'
            f"{label}</button></li>"
        )
    return "\n".join(items)


def _tab_panes(data: dict) -> str:
    """Return Bootstrap tab pane HTML with embedded Altair/Vega-Lite charts."""
    panes = []
    for i, (label, df) in enumerate(data.items()):
        active = "show active" if i == 0 else ""
        slug = label.lower().replace(" ", "-")
        chart_id = f"chart-{slug}"
        spec = _chart_spec(label, df)
        panes.append(f"""
        <div class="tab-pane fade {active}" id="pane-{slug}" role="tabpanel">
          <div id="{chart_id}"></div>
          <script>
            vegaEmbed("#{chart_id}", {spec}, {{actions: false, renderer: "svg"}})
              .catch(console.error);
          </script>
        </div>""")
    return "\n".join(panes)


def generate_dashboard(reports_dir: Path, output_file: Path) -> None:
    """Read TSV reports and write a self-contained HTML dashboard.

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

    labels = list(data.keys())
    cards_html = _summary_cards(data)
    tab_nav_html = _tab_nav(labels)
    tab_panes_html = _tab_panes(data)

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
    .navbar {{ background: #0d6efd; }}
    .tab-content {{ background: #fff; border: 1px solid #dee2e6;
                    border-top: none; padding: 1.25rem; border-radius: 0 0 .375rem .375rem; }}
    .nav-tabs .nav-link.active {{ font-weight: 600; }}
    .summary-cards {{ margin-bottom: 1.5rem; }}
    footer {{ font-size: .8rem; color: #6c757d; text-align: center; margin: 2rem 0 1rem; }}
  </style>
</head>
<body>
  <nav class="navbar navbar-dark mb-4">
    <div class="container">
      <span class="navbar-brand fw-bold">
        📊 RECETOX – Download Statistics Dashboard
      </span>
    </div>
  </nav>

  <div class="container-fluid px-4">

    <!-- Summary cards -->
    <div class="row row-cols-2 row-cols-sm-3 row-cols-lg-5 g-3 summary-cards">
      {cards_html}
    </div>

    <!-- Tabs -->
    <ul class="nav nav-tabs" role="tablist">
      {tab_nav_html}
    </ul>
    <div class="tab-content">
      {tab_panes_html}
    </div>

  </div>

  <footer>
    Generated by <strong>specdatri</strong> · data sourced from PyPI, Bioconda, CRAN, and GitHub
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
</body>
</html>
"""

    output_file.write_text(html, encoding="utf-8")
    logger.info("Dashboard written to %s", output_file)

