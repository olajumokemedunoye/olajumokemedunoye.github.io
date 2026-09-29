"""Load the UK Gender Pay Gap files into SQLite, run sql/analysis.sql and draw the report charts."""
from pathlib import Path
import json
import re
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
FILES = {"2023/24": ROOT / "data" / "gpg_2023_24.csv", "2024/25": ROOT / "data" / "gpg_2024_25.csv"}
SIZE_ORDER = {"Less than 250": 1, "250 to 499": 2, "500 to 999": 3, "1000 to 4999": 4,
              "5000 to 19,999": 5, "20,000 or more": 6, "Not Provided": 9}

frames = []
for year, path in FILES.items():
    d = pd.read_csv(path)
    first_sic = d["SicCodes"].fillna("").astype(str).str.split(",").str[0].str.strip()
    # SIC codes are 4 or 5 digits; the division is the first two digits of the zero-padded code.
    division = pd.to_numeric(first_sic.str.zfill(5).str[:2], errors="coerce")
    division[first_sic.isin(["", "1", "0"])] = None   # 1 = public sector body on the GPG service, blank = not given
    frames.append(pd.DataFrame({
        "year": year,
        "employer_id": d["EmployerId"],
        "size_band": d["EmployerSize"],
        "size_order": d["EmployerSize"].map(SIZE_ORDER),
        "sic_division": division,
        "median_gap": d["DiffMedianHourlyPercent"],
        "mean_gap": d["DiffMeanHourlyPercent"],
        "median_bonus_gap": d["DiffMedianBonusPercent"],
        "male_bonus_pct": d["MaleBonusPercent"],
        "female_bonus_pct": d["FemaleBonusPercent"],
        "female_lower": d["FemaleLowerQuartile"],
        "female_lower_middle": d["FemaleLowerMiddleQuartile"],
        "female_upper_middle": d["FemaleUpperMiddleQuartile"],
        "female_top": d["FemaleTopQuartile"],
        "late": d["SubmittedAfterTheDeadline"].astype(str).str.lower().eq("true").astype(int),
    }))

con = sqlite3.connect(":memory:")
pd.concat(frames).to_sql("gpg", con, index=False)

sql = (ROOT / "sql" / "analysis.sql").read_text(encoding="utf-8")
setup, *named = re.split(r"^-- @name ", sql, flags=re.M)
con.executescript(setup)
results = {}
for block in named:
    name, query = block.split("\n", 1)
    body = "\n".join(l for l in query.splitlines() if not l.strip().startswith("--"))
    results[name.strip()] = pd.read_sql_query(body, con)

json.dump({k: v.to_dict("records") for k, v in results.items()},
          open(OUT / "results.json", "w"), indent=2)

WINE, ROSE, SLATE, GREY = "#3B1C4A", "#B5446E", "#44506A", "#A7AEBB"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#9AA5B1"})

# Chart 1: sector gaps
s = results["by_sector"].sort_values("median_gap")
fig, ax = plt.subplots(figsize=(8, 6.4))
ax.barh(s["section"], s["median_gap"], color=[ROSE if v > 10 else SLATE for v in s["median_gap"]])
for i, v in enumerate(s["median_gap"]):
    ax.text(v + 0.3 if v >= 0 else v - 0.3, i, f"{v:.1f}%", va="center",
            ha="left" if v >= 0 else "right", fontsize=9)
ax.axvline(0, color=GREY, lw=1)
ax.set(title="Median hourly pay gap by sector, 2024/25\n(median across employers; positive = men paid more)",
       xlabel="Median gender pay gap (%)")
fig.tight_layout(); fig.savefig(OUT / "gap_by_sector.png", dpi=200); plt.close(fig)

# Chart 2: quartile representation
q = results["quartiles"].iloc[0]
labels = ["Lower", "Lower middle", "Upper middle", "Top"]
vals = [q["women_in_lower_quartile"], q["women_in_lower_middle"], q["women_in_upper_middle"], q["women_in_top_quartile"]]
fig, ax = plt.subplots(figsize=(7, 4.2))
ax.bar(labels, vals, color=[ROSE, ROSE, SLATE, WINE])
for i, v in enumerate(vals): ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=11)
ax.axhline(50, ls="--", color=GREY, lw=1)
ax.set(ylim=(0, 70), ylabel="Women as % of the quartile (employer average)",
       title="Women's share of each pay quartile, 2024/25")
fig.tight_layout(); fig.savefig(OUT / "quartiles.png", dpi=200); plt.close(fig)

# Chart 3: distribution of employer gaps
latest = pd.concat(frames).query("year == '2024/25'")
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.hist(latest["median_gap"].clip(-40, 60), bins=50, color=SLATE, edgecolor="white")
ax.axvline(0, color=ROSE, lw=2)
ax.set(title="Spread of employer median pay gaps, 2024/25 (clipped at -40% and 60%)",
       xlabel="Median gender pay gap (%)", ylabel="Employers")
fig.tight_layout(); fig.savefig(OUT / "distribution.png", dpi=200); plt.close(fig)

for k, v in results.items():
    print(f"\n== {k}\n{v.to_string(index=False)}")
