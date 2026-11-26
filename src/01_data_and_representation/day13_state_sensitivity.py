r"""
Day 13 — SOC-state sensitivity and representation freeze
=======================================================

Purpose
-------
Resolve the remaining methodological concern that PulseBat uses:
- SOCR for LFP35Ah, LMO10Ah, NMC21Ah
- SOE for NMC2.1Ah

The current canonical state feature falls back from SOCR to SOE.
SOCR and SOE must NOT be assumed physically identical.

Day13 therefore tests whether the core cross-domain result depends on that
mixed state variable.

Representations
---------------
1. REL_RATIO_NO_STATE
   RATIO_U2 ... RATIO_U21 only

2. REL_RATIO_WITH_STATE
   RATIO_U2 ... RATIO_U21 + canonical state
   (SOCR where available, SOE fallback for NMC2.1Ah)

3. RAW_NO_STATE
   U1 ... U21 only

4. RAW_WITH_STATE
   U1 ... U21 + canonical state

Validation
----------
- Leave-one-group-out
- Leave-one-chemistry-out
- ExtraTrees
- HistGradientBoosting
- RandomForest

Goal
----
If REL_RATIO_NO_STATE remains strong, the main transferable pulse-shape claim
does not depend on mixing SOCR and SOE.

Output
------
D:\SecondLife_Research\Result\Day13_StateSensitivity
"""

from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SEED = 42
EPS = 1e-12

ROOT = Path(r"D:\SecondLife_Research")
DATA_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day13_StateSensitivity"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED = {
    "NMC_2.1Ah_W_5000.xlsx",
    "LMO_10Ah_W_5000.xlsx",
    "NMC_21Ah_W_5000.xlsx",
    "LFP_35Ah_W_5000.xlsx",
}


def numeric(s):
    return pd.to_numeric(s, errors="coerce")


def normalize_state(s):
    s = numeric(s)
    valid = s.dropna()
    if valid.empty:
        return s
    return s / 100.0 if valid.quantile(0.95) > 1.5 else s


def infer_group(f):
    n = f.name.upper()
    if "2.1AH" in n and "NMC" in n:
        return "2.1Ah NMC", "NMC"
    if "10AH" in n and "LMO" in n:
        return "10Ah LMO", "LMO"
    if "21AH" in n and "NMC" in n:
        return "21Ah NMC", "NMC"
    if "35AH" in n and "LFP" in n:
        return "35Ah LFP", "LFP"
    raise ValueError(f"Unknown group: {f.name}")


def load_data():
    files = sorted(f for f in DATA_ROOT.rglob("*.xlsx") if f.name in EXPECTED)
    if len(files) != 4:
        raise FileNotFoundError(f"Expected 4 PulseBat files; found {len(files)}")

    frames = []
    audit = []

    for f in files:
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(f, sheet_name=sheet).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]

        group, chem = infer_group(f)

        id_col = next(
            c for c in df.columns
            if str(c).strip().lower() in {"id","batteryid","battery_id","cellid","cell_id"}
        )
        soh_col = next(c for c in df.columns if str(c).strip().lower() == "soh")

        df["_group"] = group
        df["_chemistry"] = chem
        df["_cell_id"] = group + "::" + df[id_col].astype(str)
        df["_SOH"] = numeric(df[soh_col])
        if df["_SOH"].dropna().median() > 2:
            df["_SOH"] /= 100.0

        if "SOCR" in df.columns and numeric(df["SOCR"]).notna().any():
            df["_STATE_CANONICAL"] = normalize_state(df["SOCR"])
            state_source = "SOCR"
        elif "SOE" in df.columns and numeric(df["SOE"]).notna().any():
            df["_STATE_CANONICAL"] = normalize_state(df["SOE"])
            state_source = "SOE"
        elif "SOC" in df.columns and numeric(df["SOC"]).notna().any():
            df["_STATE_CANONICAL"] = normalize_state(df["SOC"])
            state_source = "SOC"
        else:
            df["_STATE_CANONICAL"] = np.nan
            state_source = "NONE"

        for k in range(1, 22):
            c = f"U{k}"
            if c not in df.columns:
                raise ValueError(f"{f.name}: missing {c}")
            df[c] = numeric(df[c])

        audit.append({
            "file": str(f),
            "group": group,
            "chemistry": chem,
            "rows": len(df),
            "cells": df["_cell_id"].nunique(),
            "state_source": state_source,
            "state_min": float(df["_STATE_CANONICAL"].min()),
            "state_max": float(df["_STATE_CANONICAL"].max()),
        })

        frames.append(df)

    pd.DataFrame(audit).to_csv(OUT / "01_state_schema_audit.csv", index=False)
    return pd.concat(frames, ignore_index=True, sort=False)


def add_rel_ratio(df):
    out = df.copy()
    u1 = out["U1"].astype(float)
    rel = []
    for k in range(2, 22):
        c = f"U{k}"
        name = f"RATIO_U{k}"
        out[name] = (out[c] - u1) / (u1.abs() + EPS)
        rel.append(name)
    return out, rel


def model_dict():
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
        "MAE_pp": mean_absolute_error(test["_SOH"], pred) * 100,
        "RMSE_pp": mean_squared_error(test["_SOH"], pred) ** 0.5 * 100,
        "R2": r2_score(test["_SOH"], pred),
        "Bias_pp": np.mean(err) * 100,
    }


data = load_data()
data, rel_cols = add_rel_ratio(data)
data = data[data["_SOH"].notna()].copy()

raw_cols = [f"U{k}" for k in range(1, 22)]

feature_sets = {
    "REL_RATIO_NO_STATE": rel_cols,
    "REL_RATIO_WITH_STATE": rel_cols + ["_STATE_CANONICAL"],
    "RAW_NO_STATE": raw_cols,
    "RAW_WITH_STATE": raw_cols + ["_STATE_CANONICAL"],
}

rows = []

# Leave-one-group-out
for target in sorted(data["_group"].unique()):
    train = data[data["_group"] != target].copy()
    test = data[data["_group"] == target].copy()

    for fs_name, features in feature_sets.items():
        for model_name, estimator in model_dict().items():
            m = evaluate(train, test, features, estimator)
            rows.append({
                "experiment": "LeaveOneGroupOut",
                "target_domain": target,
                "target_chemistry": test["_chemistry"].iloc[0],
                "feature_set": fs_name,
                "model": model_name,
                **m,
                "train_cells": train["_cell_id"].nunique(),
                "test_cells": test["_cell_id"].nunique(),
            })

# Leave-one-chemistry-out
for target in sorted(data["_chemistry"].unique()):
    train = data[data["_chemistry"] != target].copy()
    test = data[data["_chemistry"] == target].copy()

    for fs_name, features in feature_sets.items():
        for model_name, estimator in model_dict().items():
            m = evaluate(train, test, features, estimator)
            rows.append({
                "experiment": "LeaveOneChemistryOut",
                "target_domain": target,
                "target_chemistry": target,
                "feature_set": fs_name,
                "model": model_name,
                **m,
                "train_cells": train["_cell_id"].nunique(),
                "test_cells": test["_cell_id"].nunique(),
            })

metrics = pd.DataFrame(rows)
metrics.to_csv(OUT / "02_state_sensitivity_metrics.csv", index=False)

# Best model per feature set / target, but never select feature set from target
best_model_per_fs = (
    metrics.sort_values(["experiment","target_domain","feature_set","MAE_pp"])
    .groupby(["experiment","target_domain","feature_set"], as_index=False)
    .first()
)
best_model_per_fs.to_csv(OUT / "03_best_model_per_feature_set.csv", index=False)

aggregate = (
    metrics.groupby(["experiment","feature_set"])
    .agg(
        mean_MAE_pp=("MAE_pp","mean"),
        median_MAE_pp=("MAE_pp","median"),
        mean_abs_bias_pp=("Bias_pp", lambda x: np.mean(np.abs(x))),
        mean_R2=("R2","mean"),
    )
    .reset_index()
    .sort_values(["experiment","mean_MAE_pp"])
)
aggregate.to_csv(OUT / "04_state_sensitivity_aggregate.csv", index=False)

# Direct REL ratio comparison using same model/domain
rel_pair = metrics[
    metrics["feature_set"].isin(["REL_RATIO_NO_STATE","REL_RATIO_WITH_STATE"])
].copy()

pivot = rel_pair.pivot_table(
    index=["experiment","target_domain","model"],
    columns="feature_set",
    values=["MAE_pp","RMSE_pp","Bias_pp","R2"]
).reset_index()

# Flatten columns
pivot.columns = [
    "_".join([str(x) for x in col if str(x) != ""]).rstrip("_")
    if isinstance(col, tuple) else str(col)
    for col in pivot.columns
]

pivot["MAE_state_minus_no_state_pp"] = (
    pivot["MAE_pp_REL_RATIO_WITH_STATE"] -
    pivot["MAE_pp_REL_RATIO_NO_STATE"]
)
pivot["MAE_relative_change_percent"] = (
    pivot["MAE_state_minus_no_state_pp"] /
    pivot["MAE_pp_REL_RATIO_NO_STATE"] * 100.0
)
pivot.to_csv(OUT / "05_relratio_state_vs_nostate_paired.csv", index=False)

# Overall robustness decision summary
agg_rel = aggregate[
    aggregate["feature_set"].isin(["REL_RATIO_NO_STATE","REL_RATIO_WITH_STATE"])
].copy()

decision_rows = []
for exp in sorted(agg_rel["experiment"].unique()):
    d = agg_rel[agg_rel["experiment"] == exp].set_index("feature_set")
    no_state = float(d.loc["REL_RATIO_NO_STATE","mean_MAE_pp"])
    with_state = float(d.loc["REL_RATIO_WITH_STATE","mean_MAE_pp"])
    decision_rows.append({
        "experiment": exp,
        "REL_RATIO_NO_STATE_mean_MAE_pp": no_state,
        "REL_RATIO_WITH_STATE_mean_MAE_pp": with_state,
        "state_effect_pp": with_state - no_state,
        "state_effect_percent": (with_state - no_state) / no_state * 100.0,
    })

decision = pd.DataFrame(decision_rows)
decision.to_csv(OUT / "06_representation_freeze_summary.csv", index=False)

# Figures
for exp in ["LeaveOneChemistryOut","LeaveOneGroupOut"]:
    d = aggregate[aggregate["experiment"] == exp].copy()
    plt.figure(figsize=(8.5,5.2))
    x = np.arange(len(d))
    plt.bar(x, d["mean_MAE_pp"])
    plt.xticks(x, d["feature_set"], rotation=25, ha="right")
    plt.ylabel("Mean cross-domain MAE (pp)")
    plt.title(f"State sensitivity — {exp}")
    plt.tight_layout()
    plt.savefig(OUT / f"Fig01_{exp}_StateSensitivity.png", dpi=300)
    plt.savefig(OUT / f"Fig01_{exp}_StateSensitivity.pdf")
    plt.close()

run_summary = {
    "day": "Day13",
    "purpose": "Determine whether the transferable REL_RATIO result depends on mixing SOCR and SOE in the canonical state feature.",
    "state_schema": {
        "LFP35Ah": "SOCR",
        "LMO10Ah": "SOCR",
        "NMC21Ah": "SOCR",
        "NMC2.1Ah": "SOE",
    },
    "primary_scientific_question": (
        "Does REL_RATIO_NO_STATE retain cross-domain performance close to "
        "REL_RATIO_WITH_STATE?"
    ),
    "feature_sets": list(feature_sets.keys()),
    "important_scope_note": (
        "SOCR and SOE are not assumed physically equivalent. "
        "The no-state sensitivity is intended to remove that ambiguity."
    ),
    "output_dir": str(OUT),
}
(OUT / "07_run_summary.json").write_text(
    json.dumps(run_summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 13 COMPLETE ===")
print("\nState-sensitivity aggregate:")
print(aggregate.to_string(index=False))
print("\nRepresentation freeze summary:")
print(decision.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("04_state_sensitivity_aggregate.csv")
print("05_relratio_state_vs_nostate_paired.csv")
print("06_representation_freeze_summary.csv")
print("07_run_summary.json")
