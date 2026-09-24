"""Dashboard generator for download statistics visualization.

This module generates a simple HTML dashboard that can be served
statically on GitHub Pages. It displays summary cards and a data table.
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)


def load_tsv(path: Path) -> Optional[pd.DataFrame]:
    """Load a TSV report file and return a tidy (long-form) DataFrame."""
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

    Returns a dict mapping report-type label to long-form DataFrame.
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
            # De-duplicate: keep the maximum value for duplicate period+package
            merged = merged.groupby(["period", "package"], as_index=False)["count"].max()
            merged = merged.sort_values("period").reset_index(drop=True)
            result[label] = merged

    return result


# Galaxy reports all-time suite totals, so each monthly row repeats the running
# total rather than counting that month. Adding those rows together counts the
# same runs once per month collected. Everything else is a per-period count and
# does sum.
CUMULATIVE_SOURCES = {"Galaxy Runs", "Galaxy Users"}


def compute_summary_stats(data: dict) -> dict:
    """Compute overall summary statistics across all data sources."""
    stats = {}

    for label, df in data.items():
        if label in CUMULATIVE_SOURCES:
            # The latest figure per package, not the sum of every snapshot. Taken
            # per package rather than from one period, so a tool that stops being
            # reported keeps its last known total instead of vanishing.
            latest = df.sort_values("period").groupby("package")["count"].last()
            total = int(latest.sum())
        else:
            total = int(df["count"].sum())
        stats[label] = {"total": total}

    return stats


def _get_jinja_env() -> Environment:
    """Get configured Jinja2 environment."""
    templates_dir = Path(__file__).parent / "templates"
    return Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True
    )


def _format_number(value: int) -> str:
    """Format a number with thousand separators."""
    return f"{value:,}"


# ---------------------------------------------------------------------------
# Vega-Lite chart builders
# ---------------------------------------------------------------------------

# Series beyond this many packages are grouped into OTHER_LABEL. Six named
# series cover 93-99% of the total in every current report, and a categorical
# scale rotating over the 14-17 packages some sources carry would encode a
# distinction the reader cannot resolve anyway.
MAX_CHART_SERIES = 6
OTHER_LABEL = "Other"

# Okabe-Ito, which is colour-blind safe, minus yellow and black and with
# orange and sky darkened. As bar fills these have to clear 3:1 against the
# white card (WCAG 1.4.11); the published orange, sky and yellow do not.
SERIES_COLORS = [
    "#0072B2",  # blue
    "#C38700",  # orange, darkened from #E69F00
    "#009E73",  # bluish green
    "#CC79A7",  # reddish purple
    "#1E9BE2",  # sky blue, darkened from #56B4E9
    "#D55E00",  # vermillion
]
OTHER_COLOR = "#939393"

_WEEK_PERIOD = re.compile(r"^(\d{4})-W(\d{1,2})$")
_MONTH_PERIOD = re.compile(r"^(\d{4})-(\d{1,2})$")


def _period_sort_key(period: str) -> tuple:
    """Return a chronological sort key for a report period label.

    Handles both month keys (``2026-01``) and ISO week keys (``2026-W07``).
    An unrecognised label sorts last rather than raising, so that one bad
    row cannot reorder the rest of the series.
    """
    for pattern in (_MONTH_PERIOD, _WEEK_PERIOD):
        match = pattern.match(period)
        if match:
            return (int(match.group(1)), int(match.group(2)))

    logger.warning("Unrecognised period label: %s", period)
    return (9999, 99)


def _period_title(periods: list) -> str:
    """Return the x-axis title for a set of period labels."""
    return "Week" if any(_WEEK_PERIOD.match(p) for p in periods) else "Month"


def _y_title_for(label: str) -> str:
    """Return y-axis title for a given data source label."""
    titles = {
        "GitHub Clones": "Clones",
        "GitHub Views": "Views",
        "Galaxy Runs": "Runs",
        "Galaxy Users": "Active Users",
    }
    return titles.get(label, "Downloads")


def _top_packages(rows: list) -> list:
    """Return the busiest package names, largest total first."""
    totals = {}
    for row in rows:
        totals[row["package"]] = totals.get(row["package"], 0) + row["count"]

    ranked = sorted(totals, key=lambda name: (-totals[name], name))
    return ranked[:MAX_CHART_SERIES]


def _build_chart_spec(label: str, rows: list) -> Optional[dict]:
    """Build a stacked bar chart spec for one data source.

    Returns a Vega-Lite specification with inline data values, or None when
    the source has no rows to draw. No config block is emitted: vega-embed
    merges its own config underneath the spec, which is what lets the page
    theme the chart from its CSS custom properties.
    """
    if not rows:
        return None

    top = _top_packages(rows)
    grouped = {}
    for row in rows:
        package = row["package"] if row["package"] in top else OTHER_LABEL
        key = (row["period"], package)
        grouped[key] = grouped.get(key, 0) + row["count"]

    values = [
        {"period": period, "package": package, "count": count}
        for (period, package), count in grouped.items()
    ]

    periods = sorted({row["period"] for row in rows}, key=_period_sort_key)
    domain = [name for name in top if any(v["package"] == name for v in values)]
    colors = SERIES_COLORS[:len(domain)]
    if any(v["package"] == OTHER_LABEL for v in values):
        domain = domain + [OTHER_LABEL]
        colors = colors + [OTHER_COLOR]

    period_title = _period_title(periods)
    y_title = _y_title_for(label)

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
        "data": {"values": values},
        # Bars, not lines: load_tsv drops zero rows, so a period with no data
        # is absent rather than zero, and a line would interpolate straight
        # through the gap and invent numbers that were never reported.
        "mark": {"type": "bar", "stroke": "#ffffff", "strokeWidth": 1},
        "height": 340,
        "width": "container",
        "background": "transparent",
        "encoding": {
            "x": {"field": "period", "type": "ordinal", "title": period_title,
                  "sort": periods,
                  "axis": {"labelAngle": -45, "labelOverlap": "greedy"}},
            "y": {"field": "count", "type": "quantitative", "title": y_title,
                  "stack": "zero"},
            "color": {"field": "package", "type": "nominal",
                      "legend": {"title": "Package"},
                      "scale": {"domain": domain, "range": colors}},
            "order": {"field": "package", "type": "nominal", "sort": domain},
            "tooltip": [
                {"field": "period", "type": "ordinal", "title": period_title},
                {"field": "package", "type": "nominal", "title": "Package"},
                {"field": "count", "type": "quantitative", "title": y_title,
                 "format": ",d"}
            ]
        }
    }


def build_chart_specs(all_data: list) -> dict:
    """Build one chart spec per data source.

    Takes the same long-form records the table is rendered from. Sources
    that yield no drawable rows are left out, so the page can say so rather
    than drawing an empty axis.
    """
    by_source = {}
    for row in all_data:
        by_source.setdefault(row["source"], []).append(row)

    specs = {}
    for label, rows in by_source.items():
        spec = _build_chart_spec(label, rows)
        if spec is not None:
            specs[label] = spec

    return specs


def generate_dashboard(reports_dir: Path, output_file: Path) -> None:
    """Read TSV reports and write a self-contained HTML dashboard.

    The generated dashboard includes:
    - Summary cards with total counts per data source
    - An interactive trend chart per data source
    - A combined data table

    Parameters
    ----------
    reports_dir:
        Root directory that contains year sub-directories.
    output_file:
        Path where the HTML file will be written.
    """
    data = load_all_data(reports_dir)

    if not data:
        logger.error("No report data found in %s", reports_dir)
        raise FileNotFoundError(f"No report data found in {reports_dir}")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Setup Jinja2 environment with custom filters
    env = _get_jinja_env()
    env.filters['format_number'] = _format_number

    # Prepare summary cards data
    icons = {
        "PyPI Downloads": "📦",
        "Bioconda Downloads": "🐍",
        "CRAN Downloads": "📊",
        "GitHub Clones": "🔁",
        "GitHub Views": "👁️",
        "Galaxy Runs": "⚙️",
        "Galaxy Users": "👥",
    }
    summary_cards = compute_summary_stats(data)

    # Combine all data into a single list for the table
    all_data = []
    for label, df in data.items():
        for _, row in df.iterrows():
            all_data.append({
                "source": label,
                "period": row["period"],
                "package": row["package"],
                "count": int(row["count"]),
            })
    # Sort by source, then period, then package
    all_data.sort(key=lambda x: (x["source"], x["period"], x["package"]))

    # Render template
    chart_specs = build_chart_specs(all_data)
    template = env.get_template("dashboard.html")
    html = template.render({
        "summary_cards": summary_cards,
        "icons": icons,
        "all_data": all_data,
        "chart_specs": chart_specs,
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M UTC"),
    })

    output_file.write_text(html, encoding="utf-8")
    logger.info("Dashboard written to %s", output_file)
