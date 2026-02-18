"""
Newfoundland & Labrador Retail Sales Pipeline
=============================================
Follows the Statistics Canada Metrics Skill Guide (stats-canada-metrics-guide.md)
steps 1–6 to download, validate, analyse, and publish retail trade data for NL.

NOTE: Table 20-10-0008-01 (Retail trade sales by province) is DISCONTINUED.
      This pipeline uses its replacement: 20-10-0056-01.

Run in Google Colab or any Python 3.9+ environment.
Output: index_retail.html  (ready for GitHub Pages)
"""

# ── Cell 1 — Configuration ────────────────────────────────────────────────────
TABLE_NUMBER    = "20-10-0056-01"   # Monthly retail trade sales by province/territory
GEO_FILTER      = "Newfoundland"
BREAKDOWN_COL   = "Trade group"
TOTAL_LABEL     = "Total, retail trade"
DASHBOARD_TITLE = "Newfoundland & Labrador — Retail Sales Dashboard"
START_YEAR      = 2015
INCLUDE = {
    "latest_snapshot": True,
    "mom_change":      True,
    "yoy_change":      True,
    "share_of_total":  True,
}
# ─────────────────────────────────────────────────────────────────────────────


# ── Cell 2 — Imports ──────────────────────────────────────────────────────────
import io, zipfile, re
from datetime import date, timedelta, datetime
from dataclasses import dataclass

import requests
import pandas as pd


# ── Cell 3 — Helper functions (Skill Guide Steps 1–5) ────────────────────────

STATCAN_DOWNLOAD_URL = (
    "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl!downloadTbl!csvDownload"
    "?pid={pid}"
)

COLUMN_MAP = {
    "REF_DATE":      "ref_date",
    "GEO":           "geo",
    "DGUID":         "dguid",
    "UOM":           "unit",
    "UOM_ID":        "unit_id",
    "SCALAR_FACTOR": "scalar",
    "SCALAR_ID":     "scalar_id",
    "VECTOR":        "vector",
    "COORDINATE":    "coordinate",
    "VALUE":         "value",
    "STATUS":        "status",
    "SYMBOL":        "symbol",
    "TERMINATED":    "terminated",
    "DECIMALS":      "decimals",
}


# Step 1c
def parse_table_input(user_input: str) -> str:
    user_input = user_input.strip()
    url_match = re.search(r"(\d{2}-\d{2}-\d{4}-\d{2})", user_input)
    if url_match:
        raw = url_match.group(1)
    elif re.fullmatch(r"\d{2}-\d{2}-\d{4}-\d{2}", user_input):
        raw = user_input
    elif re.fullmatch(r"\d{10}", user_input):
        return user_input
    else:
        raise ValueError(f"Cannot recognise '{user_input}' as a Statistics Canada table reference.")
    pid = raw.replace("-", "")
    if len(pid) != 10:
        raise ValueError(f"Parsed PID '{pid}' is not 10 digits.")
    return pid


# Step 2a
def download_statcan_table(pid: str) -> pd.DataFrame:
    url = STATCAN_DOWNLOAD_URL.format(pid=pid)
    print(f"Downloading table {pid} …")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        data_files = [n for n in zf.namelist()
                      if n.endswith(".csv") and "MetaData" not in n]
        if not data_files:
            raise FileNotFoundError("No data CSV in zip.")
        with zf.open(data_files[0]) as f:
            df = pd.read_csv(f, encoding="utf-8-sig", low_memory=False)
    print(f"  → {len(df):,} rows × {len(df.columns)} columns")
    return df


# Step 2b
def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    df.columns = [c.strip() for c in df.columns]
    return df


# Step 2c
def filter_table(df: pd.DataFrame, geo: str | None = None,
                 start_year: int | None = None) -> pd.DataFrame:
    if geo:
        df = df[df["geo"].str.contains(geo, case=False, na=False)].copy()
    if "ref_date" in df.columns:
        df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
        if start_year:
            df = df[df["ref_date"].dt.year >= start_year]
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.reset_index(drop=True)


# Step 4 — metric functions
def latest_snapshot(df: pd.DataFrame, col: str) -> pd.DataFrame:
    d = df["ref_date"].max()
    snap = df[df["ref_date"] == d][[col, "value"]].dropna()
    snap.columns = ["Category", "Value ($M)"]
    return snap.sort_values("Value ($M)", ascending=False).reset_index(drop=True)


def mom_change(df: pd.DataFrame, col: str) -> pd.DataFrame:
    dates = sorted(df["ref_date"].dropna().unique())
    cur, prev = dates[-1], dates[-2]
    c = df[df["ref_date"] == cur ].set_index(col)["value"]
    p = df[df["ref_date"] == prev].set_index(col)["value"]
    r = pd.DataFrame({"Current ($M)": c, "Previous ($M)": p})
    r["MoM %"] = ((r["Current ($M)"] - r["Previous ($M)"]) / r["Previous ($M)"].abs() * 100).round(1)
    r.index.name = "Category"
    return r.dropna().sort_values("MoM %", ascending=False).reset_index()


def yoy_change(df: pd.DataFrame, col: str) -> pd.DataFrame:
    latest  = df["ref_date"].max()
    target  = latest - timedelta(days=365)
    avail   = df["ref_date"].dropna().unique()
    yr_ago  = min(avail, key=lambda d: abs((d - target).days))
    c = df[df["ref_date"] == latest ].set_index(col)["value"]
    p = df[df["ref_date"] == yr_ago ].set_index(col)["value"]
    r = pd.DataFrame({"Current ($M)": c, "Year Ago ($M)": p})
    r["YoY %"] = ((r["Current ($M)"] - r["Year Ago ($M)"]) / r["Year Ago ($M)"].abs() * 100).round(1)
    r.index.name = "Category"
    return r.dropna().sort_values("YoY %", ascending=False).reset_index()


def share_of_total(df: pd.DataFrame, col: str,
                   total_label: str = "Total, retail trade") -> pd.DataFrame:
    latest = df["ref_date"].max()
    snap   = df[df["ref_date"] == latest].copy()
    tot_rows = snap[snap[col].str.contains(total_label, case=False, na=False)]
    if tot_rows.empty:
        raise ValueError(f"Cannot find '{total_label}' for share-of-total.")
    total_val = tot_rows["value"].iloc[0]
    snap = snap[~snap[col].str.contains(total_label, case=False, na=False)].copy()
    snap["Share %"] = (snap["value"] / total_val * 100).round(2)
    return (snap[[col, "value", "Share %"]]
            .rename(columns={col: "Category", "value": "Value ($M)"})
            .sort_values("Share %", ascending=False)
            .reset_index(drop=True))


# Step 5 — validation
@dataclass
class Check:
    name: str
    passed: bool
    expected: str
    actual: str


def run_validation(raw_df, filtered_df, col, total_label="Total, retail trade"):
    checks = []
    checks.append(Check("Raw download: not empty",
        len(raw_df) > 0, ">=1 row", f"{len(raw_df):,} rows"))
    checks.append(Check("Filtered data: not empty",
        len(filtered_df) > 0, ">=1 row", f"{len(filtered_df):,} rows"))
    if "ref_date" in filtered_df.columns and not filtered_df.empty:
        latest   = filtered_df["ref_date"].max()
        days_old = (pd.Timestamp(date.today()) - latest).days
        checks.append(Check("Data: latest date is recent",
            days_old <= 548, "<=548 days old", f"{days_old} days ({latest.date()})"))
    if "ref_date" in filtered_df.columns:
        n = filtered_df["ref_date"].nunique()
        checks.append(Check("Data: >=13 months for YoY",
            n >= 13, ">=13 months", f"{n} months"))
    checks.append(Check(f"Column '{col}' present",
        col in filtered_df.columns, "exists",
        "present" if col in filtered_df.columns else "MISSING"))
    if col in filtered_df.columns:
        n = filtered_df[col].nunique()
        checks.append(Check(f"Breakdown has >=5 categories",
            n >= 5, ">=5", f"{n} categories"))
    if col in filtered_df.columns:
        has_tot = filtered_df[col].str.contains(total_label, case=False, na=False).any()
        checks.append(Check(f"Total row present",
            has_tot, "found", "found" if has_tot else "NOT FOUND"))
    if "value" in filtered_df.columns:
        pct = filtered_df["value"].isna().mean() * 100
        checks.append(Check("Values: not all null",
            pct < 100, "<100% null", f"{pct:.1f}% null"))
    if "ref_date" in filtered_df.columns and not filtered_df.empty:
        latest = filtered_df["ref_date"].max()
        target = latest - timedelta(days=365)
        avail  = filtered_df["ref_date"].dropna().unique()
        yr_ago = min(avail, key=lambda d: abs((d - target).days))
        gap    = abs((yr_ago - target).days)
        checks.append(Check("YoY: year-ago within 35 days of 12 months",
            gap <= 35, "<=35 days", f"{gap} day(s)"))
    return checks


def print_validation_report(checks):
    passed = sum(c.passed for c in checks)
    total  = len(checks)
    print(f"\n=== Validation: {passed}/{total} passed "
          f"{'— ALL CLEAR' if passed == total else '— FAILURES PRESENT'} ===")
    for c in checks:
        print(f"  {'✓' if c.passed else '✗'}  {c.name}"
              + (f"  [{c.actual}]" if c.passed else f"\n       expected {c.expected}, got {c.actual}"))
    if passed < total:
        raise RuntimeError(f"{total - passed} validation check(s) failed.")


# ── Cell 4 — Download and validate ───────────────────────────────────────────
pid      = parse_table_input(TABLE_NUMBER)
raw_df   = download_statcan_table(pid)
norm_df  = normalise_columns(raw_df)
filtered = filter_table(norm_df, geo=GEO_FILTER, start_year=START_YEAR)

# Detect actual breakdown column name (casing may vary)
actual_col = next((c for c in filtered.columns
                   if c.lower().replace(" ", "") == BREAKDOWN_COL.lower().replace(" ", "")),
                  BREAKDOWN_COL)
filtered = filtered.rename(columns={actual_col: "trade_group"})
BDOWN = "trade_group"

checks = run_validation(norm_df, filtered, BDOWN, TOTAL_LABEL)
print_validation_report(checks)


# ── Cell 5 — Compute metrics ──────────────────────────────────────────────────
results = {}
if INCLUDE["latest_snapshot"]: results["latest_snapshot"] = latest_snapshot(filtered, BDOWN)
if INCLUDE["mom_change"]:      results["mom_change"]      = mom_change(filtered, BDOWN)
if INCLUDE["yoy_change"]:      results["yoy_change"]      = yoy_change(filtered, BDOWN)
if INCLUDE["share_of_total"]:  results["share_of_total"]  = share_of_total(filtered, BDOWN, TOTAL_LABEL)
print("Metrics computed:", list(results.keys()))


# ── Cell 6 — Build takeaways ──────────────────────────────────────────────────
latest_date = filtered["ref_date"].max()

def build_takeaways(results, latest_date):
    lines = []
    if "share_of_total" in results:
        top = results["share_of_total"].iloc[0]
        lines.append(
            f"The largest retail category in NL is <strong>{top['Category']}</strong>, "
            f"representing <strong>{top['Share %']:.1f}%</strong> of total retail sales "
            f"({latest_date.strftime('%B %Y')}).")
    if "latest_snapshot" in results:
        snap = results["latest_snapshot"]
        tot = snap[snap["Category"].str.contains(TOTAL_LABEL, case=False, na=False)]
        if not tot.empty:
            lines.append(
                f"Total NL retail sales: <strong>${tot['Value ($M)'].iloc[0]:,.0f} million"
                f"</strong> ({latest_date.strftime('%B %Y')}).")
    if "yoy_change" in results:
        yoy = results["yoy_change"]
        tot = yoy[yoy["Category"].str.contains(TOTAL_LABEL, case=False, na=False)]
        non = yoy[~yoy["Category"].str.contains(TOTAL_LABEL, case=False, na=False)]
        if not tot.empty and not non.empty:
            tv   = tot["YoY %"].iloc[0]
            best = non.iloc[0]
            sign = "+" if tv >= 0 else ""
            lines.append(
                f"Total retail sales are <strong>{sign}{tv:.1f}%</strong> year-over-year. "
                f"Fastest-growing sub-sector: <strong>{best['Category']}</strong> "
                f"(<strong>+{best['YoY %']:.1f}%</strong>).")
    return lines

takeaways = build_takeaways(results, latest_date)


# ── Cell 7 — Render and write index_retail.html ───────────────────────────────
def df_to_html_table(df, pos_cols=None):
    pos_cols = pos_cols or []
    header = "<tr>" + "".join(f"<th>{c}</th>" for c in df.columns) + "</tr>\n"
    rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            val      = row[col]
            cell_str = f"{val:.1f}" if isinstance(val, float) else str(val)
            css      = ""
            if col in pos_cols and isinstance(val, (int, float)):
                css      = ' class="pos"' if val > 0 else (' class="neg"' if val < 0 else "")
                cell_str = (f"+{val:.1f}%" if val > 0 else f"{val:.1f}%")
            cells.append(f"<td{css}>{cell_str}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table>\n" + header + "\n".join(rows) + "\n</table>"

def val_rows_html(checks):
    out = []
    for c in checks:
        badge = ('<span class="badge pass">PASS</span>'
                 if c.passed else '<span class="badge fail">FAIL</span>')
        out.append(f"<tr><td>{c.name}</td><td>{badge}</td>"
                   f"<td>{c.expected}</td><td>{c.actual}</td></tr>")
    return "\n".join(out)

prev_date    = sorted(filtered["ref_date"].unique())[-2]
sections     = ""

if "share_of_total" in results:
    sections += (f"\n<h2>Share of Total Retail Sales — {latest_date.strftime('%B %Y')}</h2>"
                 f"\n<p class='source'>Source: Statistics Canada, Table {TABLE_NUMBER}</p>"
                 + df_to_html_table(results["share_of_total"]))

if "latest_snapshot" in results:
    sections += (f"\n<h2>Latest Values ($ millions) — {latest_date.strftime('%B %Y')}</h2>"
                 f"\n<p class='source'>Source: Statistics Canada, Table {TABLE_NUMBER}</p>"
                 + df_to_html_table(results["latest_snapshot"]))

if "mom_change" in results:
    sections += (f"\n<h2>Month-over-Month Change "
                 f"({prev_date.strftime('%b %Y')} → {latest_date.strftime('%b %Y')})</h2>"
                 + df_to_html_table(results["mom_change"], pos_cols=["MoM %"]))

if "yoy_change" in results:
    sections += ("\n<h2>Year-over-Year Change</h2>"
                 + df_to_html_table(results["yoy_change"], pos_cols=["YoY %"]))

passed_n  = sum(c.passed for c in checks)
total_n   = len(checks)
sum_cls   = "all-pass" if passed_n == total_n else "has-fail"
sum_txt   = (f"{passed_n} / {total_n} checks passed — all clear"
             if passed_n == total_n
             else f"{passed_n} / {total_n} checks passed — review failures")

CSS = """
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
       color:#1a1a1a;background:#f8f9fa;line-height:1.6;padding:2rem 1rem}
  .container{max-width:1000px;margin:0 auto}
  h1{font-size:1.8rem;margin-bottom:.25rem}
  .subtitle{color:#555;font-size:.95rem;margin-bottom:1.5rem}
  .takeaways{background:#fff;border:1px solid #dee2e6;border-left:4px solid #1a3c5e;
             border-radius:4px;padding:1.25rem 1.5rem;margin-bottom:2rem}
  .takeaways h2{font-size:1.1rem;margin-bottom:.75rem;color:#1a3c5e}
  .takeaways ol{padding-left:1.25rem}
  .takeaways li{margin-bottom:.5rem}
  h2{font-size:1.3rem;margin:2rem 0 .75rem;color:#1a3c5e}
  .source{font-size:.8rem;color:#777;margin-bottom:.75rem}
  table{width:100%;border-collapse:collapse;background:#fff;font-size:.88rem;margin-bottom:1.5rem}
  th{background:#1a3c5e;color:#fff;font-weight:600;text-align:left;padding:.6rem .75rem;white-space:nowrap}
  td{padding:.5rem .75rem;border-bottom:1px solid #e9ecef}
  tr:nth-child(even) td{background:#f0f4f8}
  .pos{color:#1a7a2e;font-weight:600}
  .neg{color:#c0392b;font-weight:600}
  .validation{margin-top:3rem;padding-top:1.5rem;border-top:2px solid #dee2e6}
  .validation h2{margin-top:0}
  .validation p{margin-bottom:1rem;font-size:.9rem;color:#555}
  .badge{display:inline-block;padding:.15rem .5rem;border-radius:3px;font-size:.78rem;font-weight:700}
  .badge.pass{background:#d4edda;color:#155724}
  .badge.fail{background:#f8d7da;color:#721c24}
  .summary-box{display:inline-block;padding:.5rem 1rem;border-radius:4px;font-weight:600;margin-bottom:1rem}
  .summary-box.all-pass{background:#d4edda;color:#155724}
  .summary-box.has-fail{background:#f8d7da;color:#721c24}
  .footer{margin-top:2rem;font-size:.8rem;color:#999;text-align:center}
"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{DASHBOARD_TITLE}</title>
<style>{CSS}</style>
</head>
<body><div class="container">
  <h1>{DASHBOARD_TITLE}</h1>
  <p class="subtitle">Generated on {datetime.now().strftime("%B %d, %Y at %H:%M")} using open data from
    <a href="https://www.statcan.gc.ca/">Statistics Canada</a>
    (Table {TABLE_NUMBER} — Monthly retail trade sales by province and territory).
  </p>
  <div class="takeaways">
    <h2>Key Takeaways</h2>
    <ol>{"".join(f"<li>{t}</li>" for t in takeaways)}</ol>
  </div>
  {sections}
  <div class="validation">
    <h2>Data Validation Report</h2>
    <p>Every run passes the data through {total_n} automated checks verifying
       completeness, recency, and structural integrity before publishing.</p>
    <div class="summary-box {sum_cls}">{sum_txt}</div>
    <table><tr><th>Check</th><th>Result</th><th>Expected</th><th>Actual</th></tr>
    {val_rows_html(checks)}</table>
  </div>
  <p class="footer">Built with Python &amp; pandas &mdash;
    Data from Statistics Canada (Open Government Licence) &mdash;
    Table 20-10-0008-01 is discontinued; this pipeline uses 20-10-0056-01.
  </p>
</div></body></html>"""

with open("index_retail.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"index_retail.html written — {len(html):,} chars")
