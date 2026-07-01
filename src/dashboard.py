"""Dashboard generator for download statistics visualization.

This module generates a simple HTML dashboard that can be served
statically on GitHub Pages. It displays summary cards and a data table.
"""

import json
import logging
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


def compute_summary_stats(data: dict) -> dict:
    """Compute overall summary statistics across all data sources."""
    stats = {}

    for label, df in data.items():
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


def generate_dashboard(reports_dir: Path, output_file: Path) -> None:
    """Read TSV reports and write a self-contained HTML dashboard.

    The generated dashboard includes:
    - Summary cards with total counts per data source
    - A placeholder for trend charts
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
    template = env.get_template("dashboard.html")
    html = template.render({
        "summary_cards": summary_cards,
        "icons": icons,
        "all_data": all_data,
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M UTC"),
    })

    output_file.write_text(html, encoding="utf-8")
    logger.info("Dashboard written to %s", output_file)
