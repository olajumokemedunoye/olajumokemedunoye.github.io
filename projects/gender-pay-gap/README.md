# UK Gender Pay Gap Analysis 2023–2025

Benchmarks every employer that published gender pay gap figures for reporting years 2023/24 and 2024/25, by sector, employer size and pay quartile, and compares the same employers across both years.

- **Data:** gov.uk Gender Pay Gap Service downloads (`data/`). Contains public sector information licensed under the Open Government Licence v3.0.
- **SQL:** `sql/analysis.sql` (SQLite, medians via window functions, SIC section lookup, year-on-year self-join)
- **Python:** `python/run_analysis.py` loads the CSVs into SQLite, runs every query and draws the charts
- **Outputs:** `outputs/results.json` and three charts
- **Report:** https://olajumokemedunoye.github.io/projects/gender-pay-gap.html

Run: `python python/run_analysis.py` from this folder.
