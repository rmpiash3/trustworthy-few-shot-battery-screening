r"""
Day 03 — Physics-motivated pulse normalization for cross-domain SOH prediction
=============================================================================

Purpose
-------
Day02 showed strong domain shift when an entire battery group or chemistry was held out.
This script tests whether within-sample, physics-motivated pulse-shape transformations
reduce chemistry/capacity-domain dependence without using target labels.

Search root:
D:\SecondLife_Research\Data\PulseBat

Results:
D:\SecondLife_Research\Result\Day03_PhysicsNormalizedFeatures

Feature sets compared
---------------------
1. RAW:
   U1...U21 + canonical SOC

2. REL_U1:
   Ui - U1, i=2...21 + canonical SOC

3. REL_RATIO:
   (Ui - U1) / |U1|, i=2...21 + canonical SOC

4. STEP_DIFF:
   Ui - U(i-1), i=2...21 + canonical SOC

5. HYBRID_SHAPE:
   REL_RATIO + STEP_DIFF + compact pulse-shape statistics + canonical SOC

Validation
----------
A. Leave-one-battery-group-out
B. Leave-one-chemistry-out

Models
------
ExtraTrees
RandomForest
HistGradientBoosting
"""

from pathlib import Path
import json
import re
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import (
    ExtraTreesRegressor,
    RandomForestRegressor,
    HistGradientBoostingRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

SEED = 42
EPS = 1e-8

ROOT = Path(r"D:\SecondLife_Research")
PULSEBAT_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day03_PhysicsNormalizedFeatures"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_BASENAMES = {
    "NMC_2.1Ah_W_5000.xlsx",
    "LMO_10Ah_W_5000.xlsx",
    "NMC_21Ah_W_5000.xlsx",
    "LFP_35Ah_W_5000.xlsx",
}


def numeric(s):
    return pd.to_numeric(s, errors="coerce")


def normalize_soc(s):
    s = numeric(s)
    valid = s.dropna()
    if valid.empty:
        return s
    return s / 100.0 if valid.quantile(0.95) > 1.5 else s


def infer_group(f):
    name = f.name.upper()
    if "2.1AH" in name and "NMC" in name:
        return "2.1Ah NMC"
    if "10AH" in name and "LMO" in name:
        return "10Ah LMO"
    if "21AH" in name and "NMC" in name:
        return "21Ah NMC"
    if "35AH" in name and "LFP" in name:
        return "35Ah LFP"
    return f.parent.name


def chemistry_from_text(s):
    s = str(s).upper()
    if "NMC" in s:
        return "NMC"
    if "LMO" in s:
        return "LMO"
    if "LFP" in s:
        return "LFP"
    return "UNKNOWN"


def capacity_from_text(s):
    m = re.search(r"(\d+(?:\.\d+)?)\s*AH", str(s), flags=re.I)
    return float(m.group(1)) if m else np.nan


def find_files():
    files = sorted(PULSEBAT_ROOT.rglob("*.xlsx"))
    selected = [f for f in files if f.name in EXPECTED_BASENAMES]
    if len(selected) != 4:
        raise FileNotFoundError(
            "Expected 4 PulseBat processed Excel files under "
            f"{PULSEBAT_ROOT}, but found {len(selected)} recognized files.\n"
            f"Recognized: {[str(f) for f in selected]}"
        )
    return sorted(selected)


def load_data():
    frames = []
    audit = []

    for f in find_files():
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(f, sheet_name=sheet).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]

        group = infer_group(f)
        chemistry = chemistry_from_text(group)
        capacity = capacity_from_text(group)

        id_col = next(
            (c for c in df.columns if str(c).strip().lower()
             in {"id", "batteryid", "battery_id", "cell_id", "cellid"}),
            None
        )
        if id_col is None:
            raise ValueError(f"No battery ID field in {f.name}")

        soh_col = next(
            (c for c in df.columns if str(c).strip().lower() == "soh"),
            None
        )
        if soh_col is None:
            raise ValueError(f"No SOH field in {f.name}")

        df["_group"] = group
        df["_chemistry"] = chemistry
        df["_capacity_Ah"] = capacity
        df["_cell_id"] = group + "::" + df[id_col].astype(str)
        df["_source_file"] = str(f)

        df["_SOH"] = numeric(df[soh_col])
        if df["_SOH"].dropna().median() > 2:
            df["_SOH"] /= 100.0

        if "SOCR" in df.columns and numeric(df["SOCR"]).notna().any():
            df["_SOC_CANONICAL"] = normalize_soc(df["SOCR"])
            soc_source = "SOCR"
        elif "SOE" in df.columns and numeric(df["SOE"]).notna().any():
            df["_SOC_CANONICAL"] = normalize_soc(df["SOE"])
            soc_source = "SOE"
        elif "SOC" in df.columns and numeric(df["SOC"]).notna().any():
            df["_SOC_CANONICAL"] = normalize_soc(df["SOC"])
            soc_source = "SOC"
        else:
            df["_SOC_CANONICAL"] = np.nan
            soc_source = "NONE"

        ucols = []
        for c in df.columns:
            m = re.fullmatch(r"U(\d+)", str(c), flags=re.I)
            if m:
                ucols.append((int(m.group(1)), c))
        ucols = [c for _, c in sorted(ucols)]

        for c in ucols:
            df[c] = numeric(df[c])

        audit.append({
            "file": str(f),
            "group": group,
            "chemistry": chemistry,
            "capacity_Ah": capacity,
            "rows": len(df),
            "cells": df["_cell_id"].nunique(),
            "soc_source": soc_source,
            "u_count": len(ucols),
        })
        frames.append(df)

    data = pd.concat(frames, ignore_index=True, sort=False)

    common_u = None
    for _, g in data.groupby("_group"):
        current = {
            c for c in g.columns
            if re.fullmatch(r"U(\d+)", str(c), flags=re.I)
            and numeric(g[c]).notna().any()
        }
        common_u = current if common_u is None else common_u & current

    common_u = sorted(
        common_u,
        key=lambda c: int(re.findall(r"\d+", str(c))[0])
    )

    pd.DataFrame(audit).to_csv(OUT / "01_schema_audit.csv", index=False)

    if len(common_u) != 21:
        print(f"WARNING: expected 21 common U-features, found {len(common_u)}")

    return data, common_u


def add_feature_sets(df, ucols):
    out = df.copy()

    u1 = out[ucols[0]].astype(float)

    rel_cols = []
    ratio_cols = []
    step_cols = []

    for i, c in enumerate(ucols):
        if i == 0:
            continue

        rel_name = f"REL_{c}"
        ratio_name = f"RATIO_{c}"
        step_name = f"STEP_{c}"

        out[rel_name] = out[c] - out[ucols[0]]
        out[ratio_name] = (out[c] - out[ucols[0]]) / (u1.abs() + EPS)
        out[step_name] = out[c] - out[ucols[i-1]]

        rel_cols.append(rel_name)
        ratio_cols.append(ratio_name)
        step_cols.append(step_name)

    # compact shape descriptors; all are computed within each sample,
    # so they do not use target-domain population statistics.
    umat = out[ucols].astype(float)
    out["PULSE_SPAN"] = umat.max(axis=1) - umat.min(axis=1)
    out["END_MINUS_START"] = out[ucols[-1]] - out[ucols[0]]
    out["MEAN_MINUS_START"] = umat.mean(axis=1) - out[ucols[0]]
    out["STD_U"] = umat.std(axis=1)
    out["EARLY_CHANGE"] = out[ucols[min(4, len(ucols)-1)]] - out[ucols[0]]
    out["LATE_CHANGE"] = out[ucols[-1]] - out[ucols[max(0, len(ucols)-5)]]

    shape_stats = [
        "PULSE_SPAN",
        "END_MINUS_START",
        "MEAN_MINUS_START",
        "STD_U",
        "EARLY_CHANGE",
        "LATE_CHANGE",
    ]

    feature_sets = {
        "RAW": ucols + ["_SOC_CANONICAL"],
        "REL_U1": rel_cols + ["_SOC_CANONICAL"],
        "REL_RATIO": ratio_cols + ["_SOC_CANONICAL"],
        "STEP_DIFF": step_cols + ["_SOC_CANONICAL"],
        "HYBRID_SHAPE": ratio_cols + step_cols + shape_stats + ["_SOC_CANONICAL"],
    }

    return out, feature_sets


def models():
    return {
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=800,
            min_samples_leaf=2,
            max_features=0.8,
            random_state=SEED,
            n_jobs=-1,
        ),
        "RandomForest": RandomForestRegressor(
            n_estimators=600,
            min_samples_leaf=2,
            max_features=0.8,
            random_state=SEED,
            n_jobs=-1,
        ),
        "HistGradientBoosting": HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_iter=600,
            l2_regularization=1e-3,
            random_state=SEED,
        ),
    }


def evaluate(train, test, features, estimator):
    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", estimator),
    ])

    pipe.fit(train[features], train["_SOH"])
    pred = pipe.predict(test[features])

    err = pred - test["_SOH"].to_numpy()

    return {
        "pipe": pipe,
        "pred": pred,
        "MAE_pp": mean_absolute_error(test["_SOH"], pred) * 100,
        "RMSE_pp": mean_squared_error(test["_SOH"], pred) ** 0.5 * 100,
        "R2": r2_score(test["_SOH"], pred),
        "Bias_pp": np.mean(err) * 100,
        "MedianError_pp": np.median(err) * 100,
    }


data, ucols = load_data()
data, feature_sets = add_feature_sets(data, ucols)
data = data[data["_SOH"].notna()].copy()

metrics = []
predictions = []

# A. Leave-one-group-out
for target in sorted(data["_group"].unique()):
    train = data[data["_group"] != target].copy()
    test = data[data["_group"] == target].copy()

    for fs_name, features in feature_sets.items():
        for model_name, est in models().items():
            res = evaluate(train, test, features, est)

            metrics.append({
                "experiment": "LeaveOneGroupOut",
                "target_domain": target,
                "target_chemistry": test["_chemistry"].iloc[0],
                "feature_set": fs_name,
                "model": model_name,
                "MAE_pp": res["MAE_pp"],
                "RMSE_pp": res["RMSE_pp"],
                "R2": res["R2"],
                "Bias_pp": res["Bias_pp"],
                "MedianError_pp": res["MedianError_pp"],
                "train_cells": train["_cell_id"].nunique(),
                "test_cells": test["_cell_id"].nunique(),
            })

            p = test[[
                "_cell_id", "_group", "_chemistry", "_capacity_Ah",
                "_SOC_CANONICAL", "_SOH"
            ]].copy()
            p["experiment"] = "LeaveOneGroupOut"
            p["target_domain"] = target
            p["feature_set"] = fs_name
            p["model"] = model_name
            p["pred_SOH"] = res["pred"]
            p["error_pp"] = (res["pred"] - p["_SOH"].to_numpy()) * 100
            predictions.append(p)

# B. Leave-one-chemistry-out
for target in sorted(data["_chemistry"].unique()):
    train = data[data["_chemistry"] != target].copy()
    test = data[data["_chemistry"] == target].copy()

    for fs_name, features in feature_sets.items():
        for model_name, est in models().items():
            res = evaluate(train, test, features, est)

            metrics.append({
                "experiment": "LeaveOneChemistryOut",
                "target_domain": target,
                "target_chemistry": target,
                "feature_set": fs_name,
                "model": model_name,
                "MAE_pp": res["MAE_pp"],
                "RMSE_pp": res["RMSE_pp"],
                "R2": res["R2"],
                "Bias_pp": res["Bias_pp"],
                "MedianError_pp": res["MedianError_pp"],
                "train_cells": train["_cell_id"].nunique(),
                "test_cells": test["_cell_id"].nunique(),
            })

            p = test[[
                "_cell_id", "_group", "_chemistry", "_capacity_Ah",
                "_SOC_CANONICAL", "_SOH"
            ]].copy()
            p["experiment"] = "LeaveOneChemistryOut"
            p["target_domain"] = target
            p["feature_set"] = fs_name
            p["model"] = model_name
            p["pred_SOH"] = res["pred"]
            p["error_pp"] = (res["pred"] - p["_SOH"].to_numpy()) * 100
            predictions.append(p)

metrics = pd.DataFrame(metrics)
preds = pd.concat(predictions, ignore_index=True)

metrics.to_csv(OUT / "02_feature_set_cross_domain_metrics.csv", index=False)
preds.to_csv(OUT / "03_feature_set_predictions.csv", index=False)

best = (
    metrics.sort_values(["experiment", "target_domain", "MAE_pp"])
    .groupby(["experiment", "target_domain"], as_index=False)
    .first()
)
best.to_csv(OUT / "04_best_feature_model_by_domain.csv", index=False)

# Compare RAW best vs normalized best
rows = []
for (exp, target), g in metrics.groupby(["experiment", "target_domain"]):
    raw_best = g[g["feature_set"] == "RAW"].sort_values("MAE_pp").iloc[0]
    norm_best = g[g["feature_set"] != "RAW"].sort_values("MAE_pp").iloc[0]

    rows.append({
        "experiment": exp,
        "target_domain": target,
        "raw_best_model": raw_best["model"],
        "raw_MAE_pp": raw_best["MAE_pp"],
        "normalized_best_feature_set": norm_best["feature_set"],
        "normalized_best_model": norm_best["model"],
        "normalized_MAE_pp": norm_best["MAE_pp"],
        "MAE_improvement_pp": raw_best["MAE_pp"] - norm_best["MAE_pp"],
        "relative_improvement_percent":
            100 * (raw_best["MAE_pp"] - norm_best["MAE_pp"]) / raw_best["MAE_pp"],
        "raw_bias_pp": raw_best["Bias_pp"],
        "normalized_bias_pp": norm_best["Bias_pp"],
    })

comparison = pd.DataFrame(rows)
comparison.to_csv(OUT / "05_raw_vs_normalized_comparison.csv", index=False)

# Aggregate feature-set ranking
agg = (
    metrics.groupby(["experiment", "feature_set"])
    .agg(
        mean_MAE_pp=("MAE_pp", "mean"),
        median_MAE_pp=("MAE_pp", "median"),
        mean_abs_bias_pp=("Bias_pp", lambda x: np.mean(np.abs(x))),
        mean_R2=("R2", "mean"),
    )
    .reset_index()
    .sort_values(["experiment", "mean_MAE_pp"])
)
agg.to_csv(OUT / "06_feature_set_aggregate_ranking.csv", index=False)

# Figure 1: raw vs best normalized MAE
plot_df = comparison.copy()
labels = plot_df["experiment"] + "\n" + plot_df["target_domain"]
x = np.arange(len(plot_df))
width = 0.38

plt.figure(figsize=(11, 5.5))
plt.bar(x - width/2, plot_df["raw_MAE_pp"], width, label="RAW")
plt.bar(x + width/2, plot_df["normalized_MAE_pp"], width, label="Best normalized")
plt.xticks(x, labels, rotation=35, ha="right")
plt.ylabel("MAE (SOH percentage points)")
plt.title("Raw vs physics-normalized pulse features")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig01_Raw_vs_Normalized_MAE.png", dpi=300)
plt.savefig(OUT / "Fig01_Raw_vs_Normalized_MAE.pdf")
plt.close()

# Figure 2: aggregate feature-set MAE by experiment
for exp in sorted(agg["experiment"].unique()):
    d = agg[agg["experiment"] == exp].sort_values("mean_MAE_pp")
    plt.figure(figsize=(8.0, 5.0))
    x = np.arange(len(d))
    plt.bar(x, d["mean_MAE_pp"])
    plt.xticks(x, d["feature_set"], rotation=25, ha="right")
    plt.ylabel("Mean MAE across held-out domains (pp)")
    plt.title(f"Feature-set robustness — {exp}")
    plt.tight_layout()
    safe = re.sub(r"[^A-Za-z0-9]+", "_", exp)
    plt.savefig(OUT / f"Fig02_{safe}_FeatureSet_MAE.png", dpi=300)
    plt.savefig(OUT / f"Fig02_{safe}_FeatureSet_MAE.pdf")
    plt.close()

# Figure 3: bias correction by target domain
plt.figure(figsize=(11, 5.5))
x = np.arange(len(comparison))
plt.bar(x - width/2, comparison["raw_bias_pp"], width, label="RAW bias")
plt.bar(x + width/2, comparison["normalized_bias_pp"], width, label="Best normalized bias")
plt.axhline(0, linestyle="--", linewidth=1)
plt.xticks(x, labels, rotation=35, ha="right")
plt.ylabel("Mean prediction bias (pp)")
plt.title("Domain-wise systematic bias")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig03_Raw_vs_Normalized_Bias.png", dpi=300)
plt.savefig(OUT / "Fig03_Raw_vs_Normalized_Bias.pdf")
plt.close()

summary = {
    "day": "Day03",
    "purpose": "Test whether within-sample physics-motivated pulse normalization improves unseen-domain SOH prediction.",
    "rows": int(len(data)),
    "cells": int(data["_cell_id"].nunique()),
    "u_features": ucols,
    "feature_sets": {k: v for k, v in feature_sets.items()},
    "experiments": ["LeaveOneGroupOut", "LeaveOneChemistryOut"],
    "models": list(models().keys()),
    "important_method_note": (
        "All normalized features are computed within each pulse sample. "
        "No target-domain population mean/std or target labels are used to build them."
    ),
}
(OUT / "07_run_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 03 COMPLETE ===")
print("\nRAW vs BEST NORMALIZED:")
print(comparison.to_string(index=False))
print("\nAggregate feature-set ranking:")
print(agg.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("02_feature_set_cross_domain_metrics.csv")
print("04_best_feature_model_by_domain.csv")
print("05_raw_vs_normalized_comparison.csv")
print("06_feature_set_aggregate_ranking.csv")
print("07_run_summary.json")
