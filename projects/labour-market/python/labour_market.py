"""UK labour market context for workforce planning, from ONS Labour Market Statistics time series.

Monthly ONS labels are rolling three-month periods: "2026 JUN" covers April to June 2026.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "outputs"
OUT.mkdir(exist_ok=True)

SERIES = {
    "vacancies_k": "ons_ap2y.csv",        # AP2Y  vacancies, thousands
    "unemployed_k": "ons_mgsc.csv",       # MGSC  unemployed 16+, thousands
    "unemployment_rate": "ons_mgsx.csv",  # MGSX  unemployment rate 16+, %
    "employment_rate": "ons_lf24.csv",    # LF24  employment rate 16-64, %
    "inactivity_rate": "ons_lf2s.csv",    # LF2S  inactivity rate 16-64, %
    "regular_pay_growth": "ons_kai9.csv", # KAI9  regular pay growth, 3-month avg y/y, %
}


def load_monthly(file):
    raw = pd.read_csv(DATA / file, header=None, names=["period", "value"], dtype=str)
    monthly = raw[raw["period"].str.match(r"^\d{4} [A-Z]{3}$", na=False)].copy()
    monthly["date"] = pd.to_datetime(monthly["period"], format="%Y %b")
    return monthly.set_index("date")["value"].astype(float)


df = pd.concat({k: load_monthly(f) for k, f in SERIES.items()}, axis=1, sort=True).dropna()
df["vacancies_per_unemployed"] = df["vacancies_k"] / df["unemployed_k"]
df.to_csv(OUT / "labour_market_monthly.csv")

latest = df.index.max()
recent = df.loc["2019-01-01":]
peak = recent["vacancies_k"].idxmax()


def at(date):
    return {k: round(float(v), 2) for k, v in df.loc[date].items()}


summary = {
    "latest_period_end": latest.strftime("%b %Y"),
    "latest": at(latest),
    "year_earlier": at(latest - pd.DateOffset(years=1)),
    "pre_pandemic_feb_2020": at(pd.Timestamp("2020-02-01")),
    "vacancy_peak": {"period_end": peak.strftime("%b %Y"), **at(peak)},
}
json.dump(summary, open(OUT / "summary.json", "w"), indent=2)

NAVY, AMBER, SLATE, GREY = "#0E3B43", "#D08C2E", "#5C6F7B", "#A9B4BC"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#9AA5B1"})


def fmt_dates(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


# Chart 1: vacancies vs unemployed
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(recent.index, recent["vacancies_k"], color=AMBER, lw=2.4, label="Vacancies")
ax.plot(recent.index, recent["unemployed_k"], color=NAVY, lw=2.4, label="Unemployed people")
ax.set(ylabel="Thousands", title="Vacancies and unemployed people, UK (rolling 3 months)")
ax.legend(frameon=False); fmt_dates(ax)
fig.tight_layout(); fig.savefig(OUT / "vacancies_vs_unemployed.png", dpi=200); plt.close(fig)

# Chart 2: labour market tightness
fig, ax = plt.subplots(figsize=(9, 4.0))
ax.plot(recent.index, recent["vacancies_per_unemployed"], color=NAVY, lw=2.4)
ax.axhline(df.loc["2020-02-01", "vacancies_per_unemployed"], ls="--", color=GREY, lw=1)
ax.text(recent.index[2], df.loc["2020-02-01", "vacancies_per_unemployed"] + 0.02,
        "Feb 2020 level", color=SLATE, fontsize=9)
ax.set(ylabel="Vacancies per unemployed person", title="Labour market tightness, UK")
fmt_dates(ax)
fig.tight_layout(); fig.savefig(OUT / "tightness.png", dpi=200); plt.close(fig)

# Chart 3: rates and pay growth
fig, axes = plt.subplots(1, 2, figsize=(11, 4.0))
axes[0].plot(recent.index, recent["unemployment_rate"], color=NAVY, lw=2.2)
axes[0].set_ylabel("Unemployment rate, 16+ (%)", color=NAVY)
twin = axes[0].twinx()
twin.plot(recent.index, recent["inactivity_rate"], color=AMBER, lw=2.2)
twin.set_ylabel("Inactivity rate, 16-64 (%)", color=AMBER)
twin.spines["right"].set_visible(True)
axes[0].set_title("Unemployment (navy) and inactivity (amber)")
axes[1].plot(recent.index, recent["regular_pay_growth"], color=SLATE, lw=2.2)
axes[1].set(ylabel="% year on year", title="Regular pay growth (nominal)")
for a in axes: fmt_dates(a); a.tick_params(axis="x", labelrotation=45)
fig.tight_layout(); fig.savefig(OUT / "rates_and_pay.png", dpi=200); plt.close(fig)

print(json.dumps(summary, indent=2))
