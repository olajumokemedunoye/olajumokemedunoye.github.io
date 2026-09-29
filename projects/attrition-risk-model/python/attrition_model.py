"""Attrition risk model on the IBM HR Analytics sample dataset (fictional, 1,470 employees).

Trains a logistic regression and a random forest, evaluates both on a held-out test set,
and writes metrics and charts for the project report.

Protected characteristics (age, gender, marital status) are excluded from the model features.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (confusion_matrix, f1_score, precision_score, recall_score,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ibm_hr_attrition.csv"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

NAVY, TEAL, GREY, RED = "#0B2545", "#13807B", "#8D99AE", "#B23A48"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#9AA5B1"})

df = pd.read_csv(DATA, encoding="utf-8-sig")
df["Left"] = (df["Attrition"] == "Yes").astype(int)

# Columns with one value carry no information; EmployeeNumber is an identifier.
drop = ["Attrition", "Left", "EmployeeCount", "Over18", "StandardHours", "EmployeeNumber"]
protected = ["Age", "Gender", "MaritalStatus"]
features = [c for c in df.columns if c not in drop + protected]
categorical = [c for c in features if not pd.api.types.is_numeric_dtype(df[c])]
numeric = [c for c in features if c not in categorical]

X, y = df[features], df["Left"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, stratify=y, random_state=42)

prep = ColumnTransformer([
    ("num", StandardScaler(), numeric),
    ("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), categorical),
])

models = {
    "Logistic regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
    "Random forest": RandomForestClassifier(n_estimators=400, min_samples_leaf=5,
                                            class_weight="balanced", random_state=42),
}

results, probs = {}, {}
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
for name, clf in models.items():
    pipe = Pipeline([("prep", prep), ("clf", clf)])
    cv_auc = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="roc_auc")
    pipe.fit(X_train, y_train)
    p = pipe.predict_proba(X_test)[:, 1]
    pred = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    results[name] = {
        "cv_roc_auc_mean": round(cv_auc.mean(), 3), "cv_roc_auc_sd": round(cv_auc.std(), 3),
        "test_roc_auc": round(roc_auc_score(y_test, p), 3),
        "precision": round(precision_score(y_test, pred), 3),
        "recall": round(recall_score(y_test, pred), 3),
        "f1": round(f1_score(y_test, pred), 3),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    probs[name] = (p, pipe)

# Descriptive context
overall = df["Left"].mean()
desc = {
    "employees": int(len(df)), "leavers": int(df["Left"].sum()), "rate": round(overall, 3),
    "test_size": int(len(y_test)), "test_leavers": int(y_test.sum()),
    "by_overtime": df.groupby("OverTime")["Left"].mean().round(3).to_dict(),
    "by_role": df.groupby("JobRole")["Left"].agg(["mean", "size"]).round(3)
                 .sort_values("mean", ascending=False).to_dict("index"),
    "by_joblevel": df.groupby("JobLevel")["Left"].mean().round(3).to_dict(),
    "by_years_at_company_band": df.assign(b=pd.cut(df["YearsAtCompany"], [-1, 1, 3, 5, 10, 40],
        labels=["0-1", "2-3", "4-5", "6-10", "11+"])).groupby("b", observed=True)["Left"].mean().round(3).to_dict(),
    "by_business_travel": df.groupby("BusinessTravel")["Left"].mean().round(3).to_dict(),
    "median_income_leavers": int(df.loc[df.Left == 1, "MonthlyIncome"].median()),
    "median_income_stayers": int(df.loc[df.Left == 0, "MonthlyIncome"].median()),
}

# Logistic regression drivers (standardised coefficients)
lr_pipe = probs["Logistic regression"][1]
names = lr_pipe.named_steps["prep"].get_feature_names_out()
coefs = pd.Series(lr_pipe.named_steps["clf"].coef_[0], index=names)
coefs.index = [n.split("__", 1)[1] for n in coefs.index]
top = coefs.reindex(coefs.abs().sort_values(ascending=False).index).head(10)

json.dump({"descriptive": desc, "models": results,
           "top_drivers_lr": top.round(3).to_dict()},
          open(OUT / "metrics.json", "w"), indent=2)

# Chart 1: ROC curves
fig, ax = plt.subplots(figsize=(6.4, 5))
for (name, (p, _)), col in zip(probs.items(), [TEAL, NAVY]):
    fpr, tpr, _ = roc_curve(y_test, p)
    ax.plot(fpr, tpr, color=col, lw=2.4, label=f"{name} (AUC {results[name]['test_roc_auc']:.2f})")
ax.plot([0, 1], [0, 1], ls="--", color=GREY, lw=1, label="Random guess")
ax.set(xlabel="False positive rate", ylabel="True positive rate (recall)",
       title="ROC curve on the held-out test set")
ax.legend(frameon=False, loc="lower right")
fig.tight_layout(); fig.savefig(OUT / "roc_curve.png", dpi=200); plt.close(fig)

# Chart 2: confusion matrix for logistic regression
c = results["Logistic regression"]["confusion"]
m = np.array([[c["tn"], c["fp"]], [c["fn"], c["tp"]]])
fig, ax = plt.subplots(figsize=(5.2, 4.4))
ax.imshow(m, cmap="Blues")
for (i, j), v in np.ndenumerate(m):
    ax.text(j, i, str(v), ha="center", va="center", fontsize=20,
            color="white" if v > m.max() / 2 else NAVY, fontweight="bold")
ax.set_xticks([0, 1], ["Predicted stay", "Predicted leave"])
ax.set_yticks([0, 1], ["Actually stayed", "Actually left"])
ax.set_title("Logistic regression: confusion matrix (threshold 0.5)")
for s in ax.spines.values(): s.set_visible(False)
fig.tight_layout(); fig.savefig(OUT / "confusion_matrix.png", dpi=200); plt.close(fig)

# Chart 3: top drivers
fig, ax = plt.subplots(figsize=(7, 4.8))
t = top.iloc[::-1]
ax.barh([n.replace("_", " = ", 1).replace("_", " ") for n in t.index], t.values,
        color=[RED if v > 0 else TEAL for v in t.values])
ax.axvline(0, color=GREY, lw=1)
ax.set(xlabel="Standardised coefficient (right = higher attrition risk)",
       title="Top 10 drivers in the logistic regression")
fig.tight_layout(); fig.savefig(OUT / "top_drivers.png", dpi=200); plt.close(fig)

# Chart 4: attrition by overtime and job role
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={"width_ratios": [1, 2.2]})
ot = df.groupby("OverTime")["Left"].mean() * 100
axes[0].bar(ot.index, ot.values, color=[TEAL, RED])
for i, v in enumerate(ot.values): axes[0].text(i, v + 0.8, f"{v:.1f}%", ha="center", fontsize=11)
axes[0].set(title="Attrition by overtime", ylabel="% who left")
jr = (df.groupby("JobRole")["Left"].mean() * 100).sort_values()
axes[1].barh(jr.index, jr.values, color=NAVY)
for i, v in enumerate(jr.values): axes[1].text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=10)
axes[1].set(title="Attrition by job role", xlabel="% who left")
fig.tight_layout(); fig.savefig(OUT / "attrition_by_overtime_role.png", dpi=200); plt.close(fig)

print(json.dumps({"descriptive": {k: desc[k] for k in ["employees", "leavers", "rate", "by_overtime"]},
                  "models": results, "top": top.round(3).to_dict()}, indent=2))
