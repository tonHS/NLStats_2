# Statistics Canada Data Metrics — Skill Guide

A repeatable workflow for discovering Statistics Canada tables, building a live data pipeline, agreeing on metrics with the user, validating results, and publishing a polished dashboard to GitHub Pages via a Google Colab notebook.

---

## Table of Contents

1. [Step 1 — Find the Right Table](#step-1--find-the-right-table)
2. [Step 2 — Build the Data Pipeline](#step-2--build-the-data-pipeline)
3. [Step 3 — Agree on Metrics](#step-3--agree-on-metrics)
4. [Step 4 — Generate Metrics from Live Data](#step-4--generate-metrics-from-live-data)
5. [Step 5 — Validate the Analysis](#step-5--validate-the-analysis)
6. [Step 6 — Generate the Colab Notebook and Publish to GitHub Pages](#step-6--generate-the-colab-notebook-and-publish-to-github-pages)

---

## Step 1 — Find the Right Table

### 1a. Search Statistics Canada Directly

Statistics Canada organises its data as numbered tables (e.g., `36-10-0400-01`). You can find the right table through:

| Method | Where |
|---|---|
| Subject search | <https://www150.statcan.gc.ca/n1/en/type/data> |
| Keyword search | <https://www150.statcan.gc.ca/n1/en/catalogue/71-607-X> (StatsCan Search) |
| Topic browse | <https://www150.statcan.gc.ca/en/catalogue/subjects> |
| Survey index | <https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurveys&lang=en> |

**Useful search tips:**

- Search the subject + "NAICS" or "province" to narrow results to the right geographic or industrial breakdown.
- Table numbers follow the pattern `XX-XX-XXXX-XX`. The last two digits (`-01`, `-02`, …) indicate the table variant; `-01` is usually the main one.
- The numeric PID used in API calls is the table number with all hyphens removed and a leading zero if needed to reach 10 digits (e.g., `36-10-0400-01` → `3610040001`).

### 1b. Prompt the User When Uncertain

If the right table cannot be determined automatically, prompt the user with:

```
I need a Statistics Canada table number or URL to proceed.

Option A — Table number: enter the table ID shown on the StatsCan website,
            e.g.  36-10-0400-01  or  14-10-0022-01

Option B — Table URL: paste the full URL from your browser, e.g.
            https://www150.statcan.gc.ca/t1/tbl1/en/table/overview/crt!14-10-0022-01

Once you provide this I can download the data and propose metrics.
```

### 1c. Parse Any Format the User Provides

```python
import re

def parse_table_input(user_input: str) -> str:
    """
    Accept a table number (with or without hyphens) or a StatsCan URL.
    Returns a 10-digit PID string (e.g. '3610040001').
    """
    user_input = user_input.strip()

    # Full URL — extract the table number from the path
    url_match = re.search(r'(\d{2}-\d{2}-\d{4}-\d{2})', user_input)
    if url_match:
        raw = url_match.group(1)
    elif re.fullmatch(r'\d{2}-\d{2}-\d{4}-\d{2}', user_input):
        raw = user_input
    elif re.fullmatch(r'\d{10}', user_input):
        return user_input          # already a PID
    else:
        raise ValueError(
            f"Cannot recognise '{user_input}' as a Statistics Canada table "
            "reference. Please enter a table number like 36-10-0400-01 or a "
            "full URL from the Statistics Canada website."
        )

    pid = raw.replace('-', '')
    if len(pid) != 10:
        raise ValueError(f"Parsed PID '{pid}' is not 10 digits. Check the table number.")
    return pid
```

---

## Step 2 — Build the Data Pipeline

Statistics Canada publishes full table data as zipped CSV files. No API key is required.

### 2a. Download the Table

```python
import io
import zipfile
import requests
import pandas as pd

STATCAN_DOWNLOAD_URL = (
    "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl!downloadTbl!csvDownload"
    "?pid={pid}"
)

def download_statcan_table(pid: str) -> pd.DataFrame:
    """
    Download a Statistics Canada table by PID and return it as a DataFrame.
    The zip contains two CSVs: the data file and a metadata file.
    We load the data file (the larger one, without 'MetaData' in its name).
    """
    url = STATCAN_DOWNLOAD_URL.format(pid=pid)
    print(f"Downloading table {pid} from Statistics Canada …")

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        # Pick the data CSV (not the MetaData one)
        data_files = [n for n in zf.namelist()
                      if n.endswith('.csv') and 'MetaData' not in n]
        if not data_files:
            raise FileNotFoundError(
                "No data CSV found in the downloaded zip. "
                "Check that the PID is correct."
            )
        with zf.open(data_files[0]) as f:
            df = pd.read_csv(f, encoding='utf-8-sig', low_memory=False)

    print(f"Downloaded {len(df):,} rows × {len(df.columns)} columns.")
    return df
```

### 2b. Standardise Column Names

Statistics Canada CSV column names vary slightly across tables. Normalise them early:

```python
COLUMN_MAP = {
    'REF_DATE':   'ref_date',
    'GEO':        'geo',
    'DGUID':      'dguid',
    'UOM':        'unit',
    'UOM_ID':     'unit_id',
    'SCALAR_FACTOR': 'scalar',
    'SCALAR_ID':  'scalar_id',
    'VECTOR':     'vector',
    'COORDINATE': 'coordinate',
    'VALUE':      'value',
    'STATUS':     'status',
    'SYMBOL':     'symbol',
    'TERMINATED': 'terminated',
    'DECIMALS':   'decimals',
}

def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename StatsCan standard columns to lowercase snake_case."""
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    df.columns = [c.strip() for c in df.columns]
    return df
```

### 2c. Apply Common Filters

Most analyses need only a specific geography and a set of breakdowns. Apply these filters before doing any computation:

```python
def filter_table(
    df: pd.DataFrame,
    geo: str | None = None,
    start_year: int | None = None,
    keep_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Filter by geography name substring and optional start year.
    Converts ref_date to datetime and drops rows with missing values.
    """
    if geo:
        mask = df['geo'].str.contains(geo, case=False, na=False)
        df = df[mask].copy()

    if 'ref_date' in df.columns:
        df['ref_date'] = pd.to_datetime(df['ref_date'], errors='coerce')
        if start_year:
            df = df[df['ref_date'].dt.year >= start_year]

    if 'value' in df.columns:
        df['value'] = pd.to_numeric(df['value'], errors='coerce')

    if keep_columns:
        present = [c for c in keep_columns if c in df.columns]
        df = df[present]

    return df.reset_index(drop=True)
```

---

## Step 3 — Agree on Metrics

Before computing anything, ask the user what questions they want answered. Propose a concrete set of metrics and wait for approval or adjustments.

### 3a. Inspect the Table's Dimensions

```python
def summarise_table(df: pd.DataFrame) -> dict:
    """
    Return a plain-language summary of what breakdown columns exist,
    how many unique values each has, and the date range.
    """
    # Columns that are not the standard StatsCan system columns
    system_cols = {'ref_date', 'geo', 'dguid', 'unit', 'unit_id',
                   'scalar', 'scalar_id', 'vector', 'coordinate',
                   'value', 'status', 'symbol', 'terminated', 'decimals'}
    breakdown_cols = [c for c in df.columns if c.lower() not in system_cols]

    summary = {
        'rows': len(df),
        'date_range': (
            (str(df['ref_date'].min().date()), str(df['ref_date'].max().date()))
            if 'ref_date' in df.columns else None
        ),
        'geographies': sorted(df['geo'].dropna().unique().tolist())
                       if 'geo' in df.columns else [],
        'breakdowns': {
            col: sorted(df[col].dropna().unique().tolist())
            for col in breakdown_cols
        },
    }
    return summary
```

### 3b. Present a Metric Proposal to the User

After inspecting the table, generate and display a proposal. Example script (adapt to the specific table):

```
I have downloaded the table and found the following breakdowns:
  • Geography: [list of provinces/regions]
  • Industry: 26 categories
  • Date range: January 2001 – January 2026 (monthly)

Based on this, I propose the following metrics. Please confirm, remove, or add any:

  [Y/N] 1. Latest-period snapshot — value for every industry in the most
             recent reference period, sorted descending
  [Y/N] 2. Month-over-month % change — current vs. previous month
  [Y/N] 3. Year-over-year % change — current vs. same month last year
  [Y/N] 4. Share of total — each industry as a % of the "All industries" row
  [Y/N] 5. Trend chart data — full time-series for the top N industries
  [Y/N] 6. Custom metric — describe what you want

Type the numbers you want (e.g. 1 3 4) or 'all':
```

Store the confirmed metrics list before proceeding:

```python
AVAILABLE_METRICS = {
    1: "latest_snapshot",
    2: "mom_change",
    3: "yoy_change",
    4: "share_of_total",
    5: "trend_series",
    6: "custom",
}

def parse_metric_selection(user_response: str) -> list[str]:
    if user_response.strip().lower() == 'all':
        return list(AVAILABLE_METRICS.values())
    indices = [int(x) for x in user_response.split() if x.isdigit()]
    return [AVAILABLE_METRICS[i] for i in indices if i in AVAILABLE_METRICS]
```

---

## Step 4 — Generate Metrics from Live Data

Each metric function takes the normalised, filtered DataFrame and returns a result DataFrame ready for display.

```python
from datetime import timedelta

def latest_snapshot(df: pd.DataFrame, breakdown_col: str) -> pd.DataFrame:
    """Most recent value for each category, sorted descending."""
    latest_date = df['ref_date'].max()
    snap = df[df['ref_date'] == latest_date].copy()
    snap = snap[[breakdown_col, 'value']].dropna()
    snap.columns = ['Category', 'Value']
    return snap.sort_values('Value', ascending=False).reset_index(drop=True)


def mom_change(df: pd.DataFrame, breakdown_col: str) -> pd.DataFrame:
    """Month-over-month % change for the most recent two periods."""
    dates = sorted(df['ref_date'].dropna().unique())
    if len(dates) < 2:
        raise ValueError("Need at least 2 reference periods for MoM comparison.")
    cur, prev = dates[-1], dates[-2]

    cur_df  = df[df['ref_date'] == cur ].set_index(breakdown_col)['value']
    prev_df = df[df['ref_date'] == prev].set_index(breakdown_col)['value']

    result = pd.DataFrame({'Current': cur_df, 'Previous': prev_df})
    result['MoM %'] = ((result['Current'] - result['Previous'])
                        / result['Previous'].abs() * 100).round(1)
    result = result.dropna().sort_values('MoM %', ascending=False)
    result.index.name = 'Category'
    return result.reset_index()


def yoy_change(df: pd.DataFrame, breakdown_col: str) -> pd.DataFrame:
    """Year-over-year % change, matching the closest date ~12 months prior."""
    latest = df['ref_date'].max()
    target = latest - timedelta(days=365)
    # find the date in the data closest to exactly one year ago
    available = df['ref_date'].dropna().unique()
    year_ago = min(available, key=lambda d: abs((d - target).days))

    cur_df  = df[df['ref_date'] == latest  ].set_index(breakdown_col)['value']
    prev_df = df[df['ref_date'] == year_ago].set_index(breakdown_col)['value']

    result = pd.DataFrame({'Current': cur_df, 'Year Ago': prev_df})
    result['YoY %'] = ((result['Current'] - result['Year Ago'])
                        / result['Year Ago'].abs() * 100).round(1)
    result = result.dropna().sort_values('YoY %', ascending=False)
    result.index.name = 'Category'
    return result.reset_index()


def share_of_total(
    df: pd.DataFrame,
    breakdown_col: str,
    total_label: str = 'Total, all industries',
) -> pd.DataFrame:
    """Each category as a % of the total row in the latest period."""
    latest = df['ref_date'].max()
    snap   = df[df['ref_date'] == latest].copy()
    totals = snap[snap[breakdown_col].str.contains(total_label, na=False, case=False)]
    if totals.empty:
        raise ValueError(
            f"Cannot find a row matching '{total_label}' for share-of-total calculation."
        )
    total_value = totals['value'].iloc[0]
    snap = snap[~snap[breakdown_col].str.contains(total_label, na=False, case=False)].copy()
    snap['Share %'] = (snap['value'] / total_value * 100).round(2)
    snap = snap[[breakdown_col, 'value', 'Share %']].rename(
        columns={breakdown_col: 'Category', 'value': 'Value'}
    )
    return snap.sort_values('Share %', ascending=False).reset_index(drop=True)


def trend_series(
    df: pd.DataFrame,
    breakdown_col: str,
    top_n: int = 5,
    start_year: int = 2015,
) -> pd.DataFrame:
    """Pivot table of the top-N categories over time (for charting)."""
    latest = df['ref_date'].max()
    top_cats = (
        df[df['ref_date'] == latest]
        .nlargest(top_n, 'value')[breakdown_col]
        .tolist()
    )
    filtered = df[
        df[breakdown_col].isin(top_cats) &
        (df['ref_date'].dt.year >= start_year)
    ].copy()
    pivot = filtered.pivot_table(
        index='ref_date', columns=breakdown_col, values='value'
    )
    pivot.index = pivot.index.strftime('%Y-%m')
    return pivot
```

---

## Step 5 — Validate the Analysis

Embed these checks before rendering any output. They catch common problems: empty downloads, wrong geography filters, stale data, and broken totals.

```python
from dataclasses import dataclass

@dataclass
class Check:
    name: str
    passed: bool
    expected: str
    actual: str


def run_validation(
    raw_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    breakdown_col: str,
    total_label: str = 'Total, all industries',
) -> list[Check]:
    checks: list[Check] = []

    # 1. Raw download is not empty
    checks.append(Check(
        name="Raw download: not empty",
        passed=len(raw_df) > 0,
        expected="at least 1 row",
        actual=f"{len(raw_df):,} rows",
    ))

    # 2. Filtered data is not empty
    checks.append(Check(
        name="Filtered data: not empty",
        passed=len(filtered_df) > 0,
        expected="at least 1 row",
        actual=f"{len(filtered_df):,} rows",
    ))

    # 3. Latest reference date is recent (within 18 months of today)
    from datetime import date
    if 'ref_date' in filtered_df.columns and not filtered_df.empty:
        latest = filtered_df['ref_date'].max()
        days_old = (pd.Timestamp(date.today()) - latest).days
        checks.append(Check(
            name="Data: latest date is recent",
            passed=days_old <= 548,          # 18 months
            expected="<= 548 days old",
            actual=f"{days_old} days old ({latest.date()})",
        ))

    # 4. At least 13 months of data (required for YoY)
    if 'ref_date' in filtered_df.columns:
        n_months = filtered_df['ref_date'].nunique()
        checks.append(Check(
            name="Data: enough history for YoY (>=13 months)",
            passed=n_months >= 13,
            expected=">= 13 months",
            actual=f"{n_months} months",
        ))

    # 5. Required breakdown column is present
    checks.append(Check(
        name=f"Column '{breakdown_col}' present",
        passed=breakdown_col in filtered_df.columns,
        expected="column exists",
        actual="present" if breakdown_col in filtered_df.columns else "MISSING",
    ))

    # 6. At least 5 distinct categories in breakdown
    if breakdown_col in filtered_df.columns:
        n_cats = filtered_df[breakdown_col].nunique()
        checks.append(Check(
            name=f"Breakdown '{breakdown_col}': at least 5 categories",
            passed=n_cats >= 5,
            expected=">= 5 categories",
            actual=f"{n_cats} categories",
        ))

    # 7. Total row present for share-of-total metric
    if breakdown_col in filtered_df.columns:
        has_total = filtered_df[breakdown_col].str.contains(
            total_label, na=False, case=False
        ).any()
        checks.append(Check(
            name=f"Total row '{total_label}' present",
            passed=has_total,
            expected="row found",
            actual="found" if has_total else "NOT FOUND — share-of-total will fail",
        ))

    # 8. No all-NaN value column
    if 'value' in filtered_df.columns:
        pct_null = filtered_df['value'].isna().mean() * 100
        checks.append(Check(
            name="Values: not all null",
            passed=pct_null < 100,
            expected="< 100 % null",
            actual=f"{pct_null:.1f} % null",
        ))

    # 9. Year-ago date is within 35 days of exactly 12 months prior
    if 'ref_date' in filtered_df.columns and not filtered_df.empty:
        from datetime import timedelta
        latest = filtered_df['ref_date'].max()
        target = latest - timedelta(days=365)
        available = filtered_df['ref_date'].dropna().unique()
        year_ago  = min(available, key=lambda d: abs((d - target).days))
        gap = abs((year_ago - target).days)
        checks.append(Check(
            name="YoY: year-ago date within 35 days of exact 12 months",
            passed=gap <= 35,
            expected="<= 35 days gap",
            actual=f"{gap} day(s) gap",
        ))

    return checks


def print_validation_report(checks: list[Check]) -> None:
    passed = sum(c.passed for c in checks)
    total  = len(checks)
    status = "ALL CLEAR" if passed == total else f"{total - passed} FAILURE(S)"
    print(f"\n=== Validation Report — {passed}/{total} passed — {status} ===")
    for c in checks:
        icon = "✓" if c.passed else "✗"
        print(f"  {icon}  {c.name}")
        if not c.passed:
            print(f"       Expected : {c.expected}")
            print(f"       Actual   : {c.actual}")
    print()
    if passed < total:
        raise RuntimeError(
            f"{total - passed} validation check(s) failed. "
            "Review the report above before publishing."
        )
```

---

## Step 6 — Generate the Colab Notebook and Publish to GitHub Pages

### 6a. Complete Colab Notebook Template

Copy the cell contents below into a new Google Colab notebook (or use `nbformat` to generate it programmatically). Running all cells produces a self-contained `index.html` ready for GitHub Pages.

---

#### Cell 1 — Configuration (edit these values)

```python
# ── CONFIGURATION ──────────────────────────────────────────────────────────────
TABLE_NUMBER   = "14-10-0022-01"   # Statistics Canada table number
GEO_FILTER     = "Newfoundland"    # Geography substring filter (set '' for all)
BREAKDOWN_COL  = "North American Industry Classification System (NAICS)"
TOTAL_LABEL    = "Total, all industries"
DASHBOARD_TITLE = "Newfoundland & Labrador Economy Dashboard"
START_YEAR     = 2001              # Oldest data to keep (set None for all)
# Metrics to include (True / False)
INCLUDE = {
    "latest_snapshot": True,
    "mom_change":      True,
    "yoy_change":      True,
    "share_of_total":  True,
}
# ───────────────────────────────────────────────────────────────────────────────
```

#### Cell 2 — Install / Import

```python
!pip install requests pandas --quiet

import io, zipfile, re, textwrap
from datetime import date, timedelta, datetime
from dataclasses import dataclass

import requests
import pandas as pd
```

#### Cell 3 — Helper Functions

```python
# ── Paste all functions from Steps 2–5 of the Skill Guide here ─────────────────
# parse_table_input, download_statcan_table, normalise_columns,
# filter_table, latest_snapshot, mom_change, yoy_change,
# share_of_total, Check, run_validation, print_validation_report
```

#### Cell 4 — Download and Validate

```python
pid        = parse_table_input(TABLE_NUMBER)
raw_df     = download_statcan_table(pid)
norm_df    = normalise_columns(raw_df)
filtered   = filter_table(norm_df, geo=GEO_FILTER, start_year=START_YEAR)

# Rename the verbose NAICS column to something shorter for display
filtered   = filtered.rename(columns={BREAKDOWN_COL: 'industry'})
BDOWN      = 'industry'

checks = run_validation(norm_df, filtered, BDOWN, TOTAL_LABEL)
print_validation_report(checks)
```

#### Cell 5 — Compute Metrics

```python
results = {}

if INCLUDE["latest_snapshot"]:
    results["latest_snapshot"] = latest_snapshot(filtered, BDOWN)

if INCLUDE["mom_change"]:
    results["mom_change"] = mom_change(filtered, BDOWN)

if INCLUDE["yoy_change"]:
    results["yoy_change"] = yoy_change(filtered, BDOWN)

if INCLUDE["share_of_total"]:
    results["share_of_total"] = share_of_total(filtered, BDOWN, TOTAL_LABEL)

print("Metrics computed:", list(results.keys()))
```

#### Cell 6 — Build Key Takeaways

```python
def build_takeaways(results: dict, latest_date: pd.Timestamp) -> list[str]:
    """Auto-generate plain-English takeaways from computed metric DataFrames."""
    lines = []

    if "share_of_total" in results:
        top = results["share_of_total"].iloc[0]
        lines.append(
            f"The largest category is <strong>{top['Category']}</strong>, "
            f"representing <strong>{top['Share %']:.1f}%</strong> of the total "
            f"({latest_date.strftime('%B %Y')})."
        )

    if "latest_snapshot" in results:
        snap = results["latest_snapshot"]
        total_row = snap[snap['Category'].str.contains(TOTAL_LABEL, case=False, na=False)]
        if not total_row.empty:
            unit = norm_df['unit'].iloc[0] if 'unit' in norm_df.columns else ''
            lines.append(
                f"Total: <strong>{total_row['Value'].iloc[0]:,.1f} {unit}</strong> "
                f"as of {latest_date.strftime('%B %Y')}."
            )

    if "yoy_change" in results:
        yoy = results["yoy_change"]
        best = yoy.iloc[0]
        lines.append(
            f"Fastest-growing category year-over-year: "
            f"<strong>{best['Category']}</strong> "
            f"(<strong>+{best['YoY %']:.1f}%</strong>)."
        )

    return lines

latest_date = filtered['ref_date'].max()
takeaways   = build_takeaways(results, latest_date)
```

#### Cell 7 — Render HTML and Write index.html

```python
def df_to_html_table(df: pd.DataFrame, pos_cols: list[str] = None) -> str:
    """Convert a DataFrame to a styled HTML table."""
    pos_cols = pos_cols or []
    header = "<tr>" + "".join(f"<th>{c}</th>" for c in df.columns) + "</tr>\n"
    rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            val = row[col]
            cell_str = f"{val:.1f}" if isinstance(val, float) else str(val)
            css = ""
            if col in pos_cols and isinstance(val, (int, float)):
                css = ' class="pos"' if val > 0 else (' class="neg"' if val < 0 else "")
                cell_str = (f"+{val:.1f}%" if val > 0 else f"{val:.1f}%")
            cells.append(f"<td{css}>{cell_str}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table>\n{header}" + "\n".join(rows) + "\n</table>"


def validation_rows_html(checks: list) -> str:
    rows = []
    for c in checks:
        badge = '<span class="badge pass">PASS</span>' if c.passed \
                else '<span class="badge fail">FAIL</span>'
        rows.append(
            f"<tr><td>{c.name}</td><td>{badge}</td>"
            f"<td>{c.expected}</td><td>{c.actual}</td></tr>"
        )
    return "\n".join(rows)


# ── Build HTML sections ────────────────────────────────────────────────────────

takeaway_html = "\n".join(f"<li>{t}</li>" for t in takeaways)

sections_html = ""

if "share_of_total" in results:
    tbl = df_to_html_table(results["share_of_total"])
    sections_html += (
        f"\n<h2>Share of Total — {latest_date.strftime('%B %Y')}</h2>"
        f"\n<p class='source'>Source: Statistics Canada, Table {TABLE_NUMBER}</p>"
        f"\n{tbl}"
    )

if "latest_snapshot" in results:
    tbl = df_to_html_table(results["latest_snapshot"])
    sections_html += (
        f"\n<h2>Latest Values — {latest_date.strftime('%B %Y')}</h2>"
        f"\n<p class='source'>Source: Statistics Canada, Table {TABLE_NUMBER}</p>"
        f"\n{tbl}"
    )

if "mom_change" in results:
    tbl = df_to_html_table(results["mom_change"], pos_cols=["MoM %"])
    sections_html += "\n<h2>Month-over-Month Change</h2>" + tbl

if "yoy_change" in results:
    tbl = df_to_html_table(results["yoy_change"], pos_cols=["YoY %"])
    sections_html += "\n<h2>Year-over-Year Change</h2>" + tbl

passed_count = sum(c.passed for c in checks)
total_count  = len(checks)
summary_class = "all-pass" if passed_count == total_count else "has-fail"
summary_text  = (f"{passed_count} / {total_count} checks passed — all clear"
                 if passed_count == total_count
                 else f"{passed_count} / {total_count} checks passed — review failures")

generated_at = datetime.now().strftime("%B %d, %Y at %H:%M")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{DASHBOARD_TITLE}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          Helvetica, Arial, sans-serif; color: #1a1a1a; background: #f8f9fa;
          line-height: 1.6; padding: 2rem 1rem; }}
  .container {{ max-width: 1000px; margin: 0 auto; }}
  h1 {{ font-size: 1.8rem; margin-bottom: 0.25rem; }}
  .subtitle {{ color: #555; font-size: 0.95rem; margin-bottom: 1.5rem; }}
  .takeaways {{ background: #fff; border: 1px solid #dee2e6;
                border-left: 4px solid #1a3c5e; border-radius: 4px;
                padding: 1.25rem 1.5rem; margin-bottom: 2rem; }}
  .takeaways h2 {{ font-size: 1.1rem; margin-bottom: 0.75rem; color: #1a3c5e; }}
  .takeaways ol {{ padding-left: 1.25rem; }}
  .takeaways li {{ margin-bottom: 0.5rem; }}
  h2 {{ font-size: 1.3rem; margin: 2rem 0 0.75rem; color: #1a3c5e; }}
  .source {{ font-size: 0.8rem; color: #777; margin-bottom: 0.75rem; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff;
           font-size: 0.88rem; margin-bottom: 1.5rem; }}
  th {{ background: #1a3c5e; color: #fff; font-weight: 600; text-align: left;
        padding: 0.6rem 0.75rem; white-space: nowrap; }}
  td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid #e9ecef; }}
  tr:nth-child(even) td {{ background: #f0f4f8; }}
  .pos {{ color: #1a7a2e; font-weight: 600; }}
  .neg {{ color: #c0392b; font-weight: 600; }}
  .validation {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 2px solid #dee2e6; }}
  .validation h2 {{ margin-top: 0; }}
  .validation p {{ margin-bottom: 1rem; font-size: 0.9rem; color: #555; }}
  .badge {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 3px;
            font-size: 0.78rem; font-weight: 700; }}
  .badge.pass {{ background: #d4edda; color: #155724; }}
  .badge.fail {{ background: #f8d7da; color: #721c24; }}
  .summary-box {{ display: inline-block; padding: 0.5rem 1rem; border-radius: 4px;
                  font-weight: 600; margin-bottom: 1rem; }}
  .summary-box.all-pass {{ background: #d4edda; color: #155724; }}
  .summary-box.has-fail {{ background: #f8d7da; color: #721c24; }}
  .footer {{ margin-top: 2rem; font-size: 0.8rem; color: #999; text-align: center; }}
</style>
</head>
<body>
<div class="container">

  <h1>{DASHBOARD_TITLE}</h1>
  <p class="subtitle">
    Generated on {generated_at} using open data from
    <a href="https://www.statcan.gc.ca/">Statistics Canada</a>
    (Table {TABLE_NUMBER}).
  </p>

  <div class="takeaways">
    <h2>Key Takeaways</h2>
    <ol>{takeaway_html}</ol>
  </div>

  {sections_html}

  <div class="validation">
    <h2>Data Validation Report</h2>
    <p>Every time this dashboard is generated the data goes through automated
       checks that verify the download is complete, the geography filter matched
       data, and the metrics have enough history for meaningful comparisons.</p>
    <div class="summary-box {summary_class}">{summary_text}</div>
    <table>
      <tr><th>Check</th><th>Result</th><th>Expected</th><th>Actual</th></tr>
      {validation_rows_html(checks)}
    </table>
  </div>

  <p class="footer">
    Built with Python &amp; pandas.
    Data from Statistics Canada (Open Government Licence).
  </p>

</div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("index.html written successfully.")
print(f"File size: {len(html):,} characters")
```

#### Cell 8 — Download the File from Colab

```python
from google.colab import files
files.download("index.html")
```

---

### 6b. Publish to GitHub Pages

1. **Create or use a dedicated GitHub repository** (a separate repo avoids GitHub Pages conflicts with project repos that have complex branch setups).
2. **Upload `index.html`** to the root of the `main` branch.
3. In the repo's **Settings → Pages**, set:
   - Source: `Deploy from a branch`
   - Branch: `main` / `(root)`
4. GitHub will publish the page at `https://<username>.github.io/<repo>/`.

> **Tip:** If GitHub Pages does not activate on the project repo, create a standalone repo (e.g., `MyStats_Pages`) and push only `index.html` there. This is the pattern used in the current `NLStats_2` repository.

---

### 6c. Keeping the Dashboard Current

Re-run the Colab notebook at any time to pull fresh data from Statistics Canada and regenerate `index.html`. Because Statistics Canada updates most tables monthly, a monthly refresh cadence is recommended for employment and GDP data.

To automate updates, consider:
- A **GitHub Action** that runs a Python script on a schedule (cron) and commits the new `index.html`.
- A **Colab scheduled run** (Colab Pro feature) that emails you when complete.

---

## Quick Reference

| What you need | Where to find it |
|---|---|
| Table browser | <https://www150.statcan.gc.ca/n1/en/type/data> |
| Table number format | `36-10-0400-01` (dashes) → PID `3610040001` (no dashes) |
| CSV download URL | `https://www150.statcan.gc.ca/t1/tbl1/en/dtbl!downloadTbl!csvDownload?pid={PID}` |
| Open Government Licence | <https://www.statcan.gc.ca/en/reference/licence> |
| WDS API documentation | <https://www.statcan.gc.ca/en/developers/wds> |
| This repository's live dashboard | <https://tonhs.github.io/NLStats_2/> |

---

*Data sourced under the [Statistics Canada Open Government Licence](https://www.statcan.gc.ca/en/reference/licence).*
