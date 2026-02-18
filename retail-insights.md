# Retail Sales in Newfoundland & Labrador — Insights Report

**Reference period:** January 2026 (employment) / 2024 (GDP)
**Methodology:** Statistics Canada Metrics Skill Guide (`stats-canada-metrics-guide.md`)
**Sources:** Statistics Canada Tables 14-10-0022-01 and 36-10-0400-01

---

## Analytical Framework

This report follows the six-step methodology defined in `stats-canada-metrics-guide.md`:

| Step | Action | Applied here |
|---|---|---|
| 1 | Find the right table | Tables 14-10-0022-01 (employment) and 36-10-0400-01 (GDP) |
| 2 | Build the data pipeline | Geo filter: `"Newfoundland"`, scalar: thousands of persons / chained 2017 $ |
| 3 | Agree on metrics | Latest snapshot, MoM change, YoY change, share of total |
| 4 | Generate metrics | Extracted from `index.html` (generated Feb 8, 2026) |
| 5 | Validate | 9/9 automated checks passed — all clear |
| 6 | Publish | See `index.html` on GitHub Pages |

---

## 1. Retail's Place in the NL Economy

### GDP Contribution (2024)

| Sector | % of NL GDP |
|---|---|
| Retail trade [44-45] | **5.3%** |
| Wholesale trade [41] | 2.18% |
| **Wholesale + Retail combined** | **~7.5%** |

**Finding:** Retail trade is the 5th-largest individual industry in NL's economy by GDP share, behind Services-producing industries (57.6% aggregate), Mining/oil & gas (27.9%), Real estate (9.8%), and Health care (9.5%). Retail outranks Public administration (8.1%) and Construction (7.0%) only at the sub-aggregate level; as a discrete NAICS group it ranks approximately 5th.

**Context:** The GDP figure represents value-added (output), not sales volume. For gross retail sales figures, Statistics Canada Table 20-10-0008-01 (*Retail trade, sales by province and territory*) is required — see the **Data Gap** section below.

---

## 2. Latest Snapshot — Employment (January 2026)

| Category | Employees (thousands) |
|---|---|
| Total, all industries | 234.7 |
| Services-producing sector | 195.7 |
| **Retail trade [44-45]** | **31.7** |
| Wholesale trade [41] | 7.3 |
| **Wholesale & Retail combined [41, 44-45]** | **39.0** |

**Retail employment share of total NL workforce:** 31.7 / 234.7 = **13.5%**
**Wholesale + Retail share:** 39.0 / 234.7 = **16.6%**

Retail trade is the **second-largest employer** in Newfoundland & Labrador after Health care & social assistance (49.4K), accounting for roughly 1 in 7 NL jobs.

---

## 3. Month-over-Month Change (Dec 2025 → Jan 2026)

| Category | Dec 2025 | Jan 2026 | MoM % |
|---|---|---|---|
| Retail trade [44-45] | 32.8K | 31.7K | **-3.4%** |
| Wholesale trade [41] | 6.2K | 7.3K | **+17.7%** |
| Wholesale & Retail [41, 44-45] | 39.0K | 39.0K | **0.0%** |

**Finding:** The January dip in retail employment (-3.4%) is consistent with typical post-holiday seasonal contraction across Canada. The striking wholesale trade surge (+17.7% MoM) offset the retail decline exactly, leaving the combined category flat. These are unadjusted figures; seasonal adjustment would likely show a more neutral picture for retail.

---

## 4. Year-over-Year Change (Jan 2025 → Jan 2026)

| Category | Jan 2025 | Jan 2026 | YoY % |
|---|---|---|---|
| Total, all industries | 229.8K | 234.7K | **+2.1%** |
| **Retail trade [44-45]** | 32.5K | 31.7K | **-2.5%** |
| Wholesale trade [41] | 4.0K | 7.3K | **+82.5%** |
| Wholesale & Retail combined | 36.5K | 39.0K | **+6.8%** |
| Health care [62] | 47.5K | 49.4K | **+4.0%** |
| Accommodation & food services [72] | 11.3K | 13.7K | **+21.2%** |
| Finance & insurance [52] | 4.5K | 6.2K | **+37.8%** |

### Key findings

1. **Retail employment is contracting.** Retail trade lost approximately 800 jobs YoY (-2.5%), bucking the province-wide trend of +2.1% total employment growth. Retail is one of only a handful of sectors shrinking in absolute terms.

2. **Wholesale trade is surging.** A +82.5% YoY employment jump in wholesale trade (from 4.0K to 7.3K) is exceptional. This likely reflects business investment activity tied to NL's energy and construction sectors (offshore oil & gas, hydroelectric projects) rather than consumer retail demand.

3. **The divergence matters for interpretation.** When wholesale and retail are aggregated (as Statistics Canada sometimes reports them together), the headline number (+6.8% YoY) masks a deteriorating retail picture. Analysts should always decompose the combined [41, 44-45] group.

4. **Retail is losing share.** Retail trade's share of total NL employment fell from 32.5/229.8 = 14.1% (Jan 2025) to 31.7/234.7 = 13.5% (Jan 2026), a 0.6 percentage-point decline in one year.

---

## 5. Structural Context — Why Retail May Be Under Pressure

Several structural factors plausibly explain retail employment contraction in NL:

| Factor | Implication |
|---|---|
| **Population & demographics** | NL has one of Canada's older and slower-growing populations; fewer new consumers entering the market |
| **E-commerce substitution** | Online purchasing erodes in-store employment; NL is not immune despite geographic isolation |
| **Energy sector wealth effect** | Oil & gas boom may shift spending patterns toward services (travel, dining, finance) more than goods retail |
| **Accommodation & food surge (+21.2% YoY)** | Growth in hospitality suggests consumer spending is shifting toward experiential categories |
| **Goods-producing sector decline (-5.4% YoY)** | Contraction in mining/construction employment in some segments reduces disposable income for retail |

---

## 6. Data Gap — Retail Sales Volumes

The current dashboard covers **employment headcounts** and **GDP value-added**. To analyse actual **retail sales volumes and trends**, the following Statistics Canada table should be added to the pipeline:

| Table | Name | Key dimensions |
|---|---|---|
| **20-10-0008-01** | Retail trade, sales by province and territory | Province, trade group (food, clothing, general, etc.), monthly |

### How to extend the pipeline (skill guide Step 1–2)

Using the methodology in `stats-canada-metrics-guide.md`:

```python
# Step 1: Parse the table
pid = parse_table_input("20-10-0008-01")   # → "2010000801"

# Step 2: Download and filter
raw_df    = download_statcan_table(pid)
norm_df   = normalise_columns(raw_df)
filtered  = filter_table(norm_df, geo="Newfoundland", start_year=2015)
```

This would enable:
- **Latest snapshot** — total NL retail sales in the most recent month ($ millions)
- **MoM % change** — seasonal buying patterns
- **YoY % change** — real growth vs. inflation-adjusted baseline
- **Share of total** — NL's share of national retail sales
- **Trend series** — multi-year trajectory by sub-sector (food, automotive, clothing, etc.)

### Recommended metrics for Table 20-10-0008-01

```
[Y] 1. Latest-period snapshot     — total NL retail sales in most recent month
[Y] 2. Month-over-month % change  — Dec/Jan seasonality in consumer spending
[Y] 3. Year-over-year % change    — real growth trend
[Y] 4. Share of national total    — NL's weight in Canadian retail
[Y] 5. Trend chart (top 5 sub-sectors since 2015)
```

---

## 7. Summary of Findings

| Metric | Value | Direction |
|---|---|---|
| Retail trade GDP share (2024) | 5.3% of NL GDP | — |
| Retail employment (Jan 2026) | 31.7K | Steady |
| Retail share of NL workforce | 13.5% | Declining |
| Retail MoM change | -3.4% | Seasonal dip |
| Retail YoY change | **-2.5%** | Contracting |
| Wholesale YoY change | **+82.5%** | Expanding rapidly |
| Combined wholesale + retail YoY | +6.8% | Misleadingly positive |
| Total NL employment YoY | +2.1% | Growing |

**Bottom line:** Retail trade in Newfoundland & Labrador is losing ground both in employment headcount and economic share, even as the overall provincial economy grows. The sector shed roughly 800 jobs year-over-year to January 2026. Wholesale trade, driven largely by non-consumer-facing industrial supply activity, is the dominant growth engine within the [41, 44-45] grouping and should not be conflated with consumer retail performance. To fully quantify the retail sales trend in dollar terms, extending this dashboard with Statistics Canada Table 20-10-0008-01 is the recommended next step.

---

*Data sourced under the [Statistics Canada Open Government Licence](https://www.statcan.gc.ca/en/reference/licence).*
*Methodology: `stats-canada-metrics-guide.md` in this repository.*
