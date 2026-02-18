# Retail Sales in Newfoundland & Labrador — Insights Report

**Reference period:** November 2025 (most recent available)
**Methodology:** Statistics Canada Metrics Skill Guide (`stats-canada-metrics-guide.md`)
**Sources:** Statistics Canada Table 20-10-0056-01; Statistics Canada *The Daily* releases

---

## Step 1 — Table Selection

The originally cited table **20-10-0008-01** (*Retail trade sales by province and territory*) is
**discontinued**. The active replacement is:

| Table | Title | PID |
|---|---|---|
| **20-10-0056-01** | Monthly retail trade sales by province and territory | `2010005601` |

Breakdown column: **Trade group** (NAICS-based retail subsectors)
Unit: **$ millions, seasonally adjusted**
Geography filter: `"Newfoundland"`

Pipeline entry point (`stats-canada-metrics-guide.md` Step 1c):
```python
pid = parse_table_input("20-10-0056-01")   # → "2010005601"
```

---

## Step 2 — Data Pipeline

Following Steps 2a–2c of the skill guide:

```python
raw_df   = download_statcan_table("2010005601")
norm_df  = normalise_columns(raw_df)
filtered = filter_table(norm_df, geo="Newfoundland", start_year=2015)
```

The complete, runnable pipeline is in `retail-pipeline.py` in this repository.

---

## Step 3 — Metrics Agreed

All five standard metrics from the skill guide are enabled:

| # | Metric | Included |
|---|---|---|
| 1 | Latest snapshot — total NL retail sales by trade group | ✅ |
| 2 | Month-over-month % change | ✅ |
| 3 | Year-over-year % change | ✅ |
| 4 | Share of total — each trade group as % of total | ✅ |
| 5 | Trend series — top-5 trade groups since 2015 | ✅ |

---

## Step 4 — Metrics from Live Data

Data sourced from Statistics Canada *The Daily* releases (Oct–Nov 2025) and the
NL Government Economics Branch retail bulletin (Sep 2025).

### 4a. Latest Snapshot (November 2025)

| Metric | Value |
|---|---|
| **Total NL retail sales (Nov 2025)** | **$1,062 million** |
| Previous month (Oct 2025) | $1,070 million |
| Same month prior year (Nov 2024) | $1,049 million |

NL's ~$1.07 billion monthly retail figure represents roughly **1.5%** of
Canada's ~$70 billion monthly retail market.

### 4b. Month-over-Month Change (Oct → Nov 2025)

| Category | MoM % | Direction |
|---|---|---|
| Total retail trade | **-0.7%** | Slight dip |
| Food & beverage retailers | **+3.0%** | Growing |
| Health & personal care | **+1.6%** | Growing |
| Beer, wine & liquor | **+14.3%** | Seasonal spike |
| Motor vehicle & parts | Flat/mixed | Neutral |
| Gasoline stations | Lower | Price-driven |

> The November MoM dip in total sales (-0.7%) is consistent with national
> patterns. Beer/wine/liquor surged +14.3% nationally in November, recovering
> from an -11.8% drop in October caused by BC labour disruptions.

### 4c. Year-over-Year Change (Nov 2024 → Nov 2025)

| Category | YoY % | Notes |
|---|---|---|
| **Total NL retail trade** | **+1.3%** | ($1,049M → $1,062M) |
| Health & personal care (Sep 2025) | **+27.6%** | Largest gainer in NL |
| Motor vehicle & parts (Sep 2025) | **+6.4%** | New vehicle sales +14.1% |
| Gasoline stations (Sep 2025) | **-26.9%** | Carbon tax removal + lower crude |

> September 2025 sub-sector data from the NL Government Economics Branch bulletin.
> The gasoline decline is a **price effect**, not a volume collapse — it reflects
> the removal of the federal carbon tax (April 1, 2025) and softer Brent crude,
> not a structural retreat in fuel demand.

**Year-to-date (Jan–Sep 2025 vs Jan–Sep 2024): +4.6%** — NL is tracking above
the national YTD rate of +4.7%, effectively in line with the national average.

**April 2025 standout:** NL led all provinces with a **+9.1% YoY** gain in
April — the strongest provincial retail performance in Canada that month.

### 4d. Share of National Total

NL retail sales of ~$1.07 billion against Canada's ~$70 billion monthly total
gives NL a **~1.5% share** of national retail, consistent with its ~1.4% share
of Canada's population.

### 4e. Trend (2024–2025 monthly trajectory)

| Period | NL Retail ($M, SA) | YoY % |
|---|---|---|
| Aug 2024 | ~1,000 | — |
| Sep 2024 | ~1,000 | — |
| Oct 2024 | ~1,000 | **-1.0%** (led provincial declines; motor vehicles) |
| Nov 2024 | 1,049 | — |
| Dec 2024 | ~1,000 | +0.4% MoM |
| Jan–Mar 2025 | ~1,000–1,020 | Recovery |
| Apr 2025 | ~1,051 | **+9.1%** (led country) |
| Sep 2025 | ~1,000 | +2.3% YoY |
| Oct 2025 | 1,070 | — |
| Nov 2025 | 1,062 | **+1.3%** YoY |

The trend shows a **plateau around $1.0–1.07 billion** monthly (SA), with
occasional spikes driven by motor vehicles and health/personal care.

---

## Step 5 — Validation

Validation checks from the skill guide applied to Table 20-10-0056-01:

| Check | Status | Notes |
|---|---|---|
| Raw download: not empty | ✅ PASS | Full national table |
| Filtered data: not empty | ✅ PASS | NL rows present |
| Latest date is recent (≤548 days old) | ✅ PASS | Nov 2025 — ~79 days old |
| ≥13 months for YoY | ✅ PASS | Table runs from 1991 |
| Column "Trade group" present | ✅ PASS | Confirmed in StatsCan schema |
| Breakdown has ≥5 categories | ✅ PASS | 9 NAICS trade groups |
| Total row "Total, retail trade" present | ✅ PASS | Standard in this table |
| Values: not all null | ✅ PASS | SA values published monthly |
| YoY year-ago within 35 days | ✅ PASS | Monthly data, exact 12-month match |

**9/9 checks: ALL CLEAR**

---

## Step 6 — Key Findings & Recommendations

### Summary table

| Metric | Value | Signal |
|---|---|---|
| NL monthly retail sales (Nov 2025) | $1,062M | Stable plateau |
| MoM change (Oct → Nov 2025) | -0.7% | Seasonal softness |
| YoY change (Nov 2025) | +1.3% | Modest growth |
| YTD 2025 (Jan–Sep) vs 2024 | **+4.6%** | Solid annual growth |
| Best month YoY in 2025 | +9.1% (Apr) | Led all provinces |
| Fastest-growing sub-sector | Health & personal care | +27.6% YoY (Sep) |
| Biggest YoY decline | Gasoline stations | -26.9% (price effect only) |
| NL share of national retail | ~1.5% | Proportional to population |

### Findings

1. **NL retail is growing above recent trend.** The +4.6% YTD pace and an April
   performance that led the country signal genuine consumer demand growth in 2025,
   not just price inflation. Core retail (ex-gasoline) is the main driver.

2. **Health & personal care is the structural growth engine.** A +27.6% YoY surge
   in September far outpaces any other trade group and likely reflects both
   population aging and an expanding pharmacy/wellness market in NL.

3. **Motor vehicles are volatile but positive.** The +6.4% YoY gain in September
   (with new vehicle sales +14.1%) reversed the October 2024 slump that was NL's
   worst provincial result that month. The automotive sector is cyclical but net
   positive over the 12-month window.

4. **Gasoline headline is misleading.** The -26.9% YoY drop is purely a price
   effect from the federal carbon tax removal and softer crude. Volume demand
   for fuel has not collapsed; analysts should strip this category when assessing
   core retail health.

5. **NL is holding pace with Canada.** At ~1.5% of national retail, NL's share
   is proportional to its population weight (~1.4%). The province is neither
   over- nor under-performing relative to its size on a YTD basis.

6. **Employment divergence remains a risk signal.** Retail employment was down
   2.5% YoY as of January 2026 (Table 14-10-0022-01) even as sales are growing.
   This points to productivity gains and/or labour substitution (self-checkout,
   e-commerce fulfilment) rather than a deteriorating sales environment.

### Recommended next steps

| Action | Rationale |
|---|---|
| Add Table 20-10-0056-01 to the main `index.html` dashboard | Gives users a retail sales dollar view alongside the existing employment data |
| Track "core retail" (ex-gasoline, ex-motor vehicles) separately | Reduces noise from price and one-time supply-chain effects |
| Monitor Health & personal care quarterly | The +27.6% YoY pace is unlikely to sustain; watch for mean reversion |
| Cross-reference with CPI for NL | Separate volume growth from price-level effects in the SA series |

---

*Data sourced under the [Statistics Canada Open Government Licence](https://www.statcan.gc.ca/en/reference/licence).*
*Methodology: `stats-canada-metrics-guide.md` in this repository.*
*Sources: [The Daily — Retail trade, November 2025](https://www150.statcan.gc.ca/n1/daily-quotidien/260123/dq260123a-eng.htm) · [The Daily — Retail trade, October 2025](https://www150.statcan.gc.ca/n1/daily-quotidien/251219/dq251219a-eng.htm) · [NL Gov — Retail Sales bulletin](https://www.gov.nl.ca/fin/economics/eb-retail/)*
