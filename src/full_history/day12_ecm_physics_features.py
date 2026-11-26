r"""
Day 12 — ECM-inspired pulse-physics feature audit and cross-domain benchmark
===========================================================================

Purpose
-------
Use the known PulseBat 5-s pulse / 75-s rest turning-point semantics to derive
physically interpretable resistance/polarization SURROGATE features from U1-U21.

Important scope boundary
------------------------
These are NOT certified R0/R1/C1/R2/C2 parameters and NOT a fitted 2RC twin.
They are ECM-inspired pulse-response surrogates derived from voltage turning
points and known C-rate amplitudes.

Official PulseBat U1-U21 semantics used:
- U1: OCV after 10-min rest
- U2-U9: 0.5C positive pulse / rest / negative pulse / rest
- U10-U17: 1C positive pulse / rest / negative pulse / rest
- U18-U21: 1.5C positive pulse / rest
- pulse width = 5 s
- rest = 75 s

Nominal capacities:
- NMC 2.1Ah
- LMO 10Ah
- NMC 21Ah
- LFP 35Ah

Feature families
----------------
1. REL_RATIO:
   Day03 representation.

2. PHYSICS:
   ECM-inspired resistance / polarization / relaxation surrogates.

3. REL_PLUS_PHYSICS:
   Combined representation.

Validation
----------
- Leave-one-group-out
- Leave-one-chemistry-out
- ExtraTrees / RandomForest / HistGradientBoosting

Output
------
D:\SecondLife_Research\Result\Day12_ECM_PhysicsFeatures
"""

from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

SEED = 42
EPS = 1e-12

ROOT = Path(r"D:\SecondLife_Research")
DATA_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day12_ECM_PhysicsFeatures"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED = {
    "NMC_2.1Ah_W_5000.xlsx",
    "LMO_10Ah_W_5000.xlsx",
    "NMC_21Ah_W_5000.xlsx",
    "LFP_35Ah_W_5000.xlsx",
}


def numeric(s):
    return pd.to_numeric(s, errors="coerce")


def normalize_soc(s):
    s = numeric(s)
    v = s.dropna()
    if v.empty:
        return s
    return s / 100.0 if v.quantile(0.95) > 1.5 else s


def infer_group(f):
    n = f.name.upper()
    if "2.1AH" in n and "NMC" in n:
        return "2.1Ah NMC", "NMC", 2.1
    if "10AH" in n and "LMO" in n:
        return "10Ah LMO", "LMO", 10.0
    if "21AH" in n and "NMC" in n:
        return "21Ah NMC", "NMC", 21.0
    if "35AH" in n and "LFP" in n:
        return "35Ah LFP", "LFP", 35.0
    raise ValueError(f"Unknown group from {f.name}")


def find_u_cols(cols):
    pairs = []
    for c in cols:
        m = re.fullmatch(r"U(\d+)", str(c).strip(), flags=re.I)
        if m:
            pairs.append((int(m.group(1)), str(c).strip()))
    return [c for _, c in sorted(pairs)]


def load_data():
    files = sorted(f for f in DATA_ROOT.rglob("*.xlsx") if f.name in EXPECTED)
    if len(files) != 4:
        raise FileNotFoundError(f"Expected 4 source files, found {len(files)}")

    frames = []
    audit = []

    for f in files:
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(f, sheet_name=sheet).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]

        group, chem, cap = infer_group(f)

        id_col = next(
            c for c in df.columns
            if str(c).strip().lower() in {"id","batteryid","battery_id","cellid","cell_id"}
        )
        soh_col = next(c for c in df.columns if str(c).strip().lower() == "soh")

        df["_group"] = group
        df["_chemistry"] = chem
        df["_capacity_Ah"] = cap
        df["_cell_id"] = group + "::" + df[id_col].astype(str)

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

        ucols = find_u_cols(df.columns)
        for c in ucols:
            df[c] = numeric(df[c])

        audit.append({
            "file": str(f),
            "group": group,
            "chemistry": chem,
            "nominal_capacity_Ah": cap,
            "rows": len(df),
            "cells": df["_cell_id"].nunique(),
            "soc_source": soc_source,
            "u_count": len(ucols),
        })
        frames.append(df)

    data = pd.concat(frames, ignore_index=True, sort=False)
    pd.DataFrame(audit).to_csv(OUT / "01_schema_audit.csv", index=False)
    return data


def add_rel_ratio(df):
    out = df.copy()
    u1 = out["U1"].astype(float)
    cols = []
    for k in range(2, 22):
        c = f"U{k}"
        name = f"RATIO_U{k}"
        out[name] = (out[c] - u1) / (u1.abs() + EPS)
        cols.append(name)
    return out, cols + ["_SOC_CANONICAL"]


def safe_div(num, den):
    return num / (den + EPS)


def add_physics_features(df):
    out = df.copy()
    physics = []

    # Helpers to create one positive pulse block.
    def positive_block(prefix, baseline_col, u_start, u_end, u_rest_start, u_rest_end, c_rate):
        I = c_rate * out["_capacity_Ah"]

        out[f"{prefix}_Rstart"] = np.abs(out[u_start] - out[baseline_col]) / (I + EPS)
        out[f"{prefix}_R5s"] = np.abs(out[u_end] - out[baseline_col]) / (I + EPS)
        out[f"{prefix}_Rpol_build"] = np.abs(out[u_end] - out[u_start]) / (I + EPS)
        out[f"{prefix}_Rrelax75"] = np.abs(out[u_rest_end] - out[u_rest_start]) / (I + EPS)
        out[f"{prefix}_RecoveryFrac"] = safe_div(
            np.abs(out[u_rest_end] - out[u_rest_start]),
            np.abs(out[u_end] - out[u_start])
        )

        return [
            f"{prefix}_Rstart",
            f"{prefix}_R5s",
            f"{prefix}_Rpol_build",
            f"{prefix}_Rrelax75",
            f"{prefix}_RecoveryFrac",
        ]

    # 0.5C positive: baseline U1, pulse U2->U3, rest U4->U5
    physics += positive_block("C05_POS", "U1", "U2", "U3", "U4", "U5", 0.5)

    # 0.5C negative: local baseline U5, pulse U6->U7, rest U8->U9
    I05 = 0.5 * out["_capacity_Ah"]
    out["C05_NEG_Rstart"] = np.abs(out["U6"] - out["U5"]) / (I05 + EPS)
    out["C05_NEG_R5s"] = np.abs(out["U7"] - out["U5"]) / (I05 + EPS)
    out["C05_NEG_Rpol_build"] = np.abs(out["U7"] - out["U6"]) / (I05 + EPS)
    out["C05_NEG_Rrelax75"] = np.abs(out["U9"] - out["U8"]) / (I05 + EPS)
    out["C05_NEG_RecoveryFrac"] = safe_div(
        np.abs(out["U9"] - out["U8"]),
        np.abs(out["U7"] - out["U6"])
    )
    physics += [
        "C05_NEG_Rstart","C05_NEG_R5s","C05_NEG_Rpol_build",
        "C05_NEG_Rrelax75","C05_NEG_RecoveryFrac"
    ]

    # 1C positive: baseline after 0.5C pair = U9
    physics += positive_block("C10_POS", "U9", "U10", "U11", "U12", "U13", 1.0)

    # 1C negative: local baseline U13, pulse U14->U15, rest U16->U17
    I10 = 1.0 * out["_capacity_Ah"]
    out["C10_NEG_Rstart"] = np.abs(out["U14"] - out["U13"]) / (I10 + EPS)
    out["C10_NEG_R5s"] = np.abs(out["U15"] - out["U13"]) / (I10 + EPS)
    out["C10_NEG_Rpol_build"] = np.abs(out["U15"] - out["U14"]) / (I10 + EPS)
    out["C10_NEG_Rrelax75"] = np.abs(out["U17"] - out["U16"]) / (I10 + EPS)
    out["C10_NEG_RecoveryFrac"] = safe_div(
        np.abs(out["U17"] - out["U16"]),
        np.abs(out["U15"] - out["U14"])
    )
    physics += [
        "C10_NEG_Rstart","C10_NEG_R5s","C10_NEG_Rpol_build",
        "C10_NEG_Rrelax75","C10_NEG_RecoveryFrac"
    ]

    # 1.5C positive: baseline after 1C pair = U17
    physics += positive_block("C15_POS", "U17", "U18", "U19", "U20", "U21", 1.5)

    # Cross-amplitude / asymmetry summaries
    out["ASYM_C05_Rstart"] = np.abs(out["C05_POS_Rstart"] - out["C05_NEG_Rstart"])
    out["ASYM_C05_R5s"] = np.abs(out["C05_POS_R5s"] - out["C05_NEG_R5s"])
    out["ASYM_C10_Rstart"] = np.abs(out["C10_POS_Rstart"] - out["C10_NEG_Rstart"])
    out["ASYM_C10_R5s"] = np.abs(out["C10_POS_R5s"] - out["C10_NEG_R5s"])

    out["AMP_SLOPE_Rstart_05_to_10"] = out["C10_POS_Rstart"] - out["C05_POS_Rstart"]
    out["AMP_SLOPE_Rstart_10_to_15"] = out["C15_POS_Rstart"] - out["C10_POS_Rstart"]
    out["AMP_SLOPE_R5s_05_to_10"] = out["C10_POS_R5s"] - out["C05_POS_R5s"]
    out["AMP_SLOPE_R5s_10_to_15"] = out["C15_POS_R5s"] - out["C10_POS_R5s"]

    out["OCV_U1"] = out["U1"]

    extra = [
        "ASYM_C05_Rstart","ASYM_C05_R5s",
        "ASYM_C10_Rstart","ASYM_C10_R5s",
        "AMP_SLOPE_Rstart_05_to_10","AMP_SLOPE_Rstart_10_to_15",
        "AMP_SLOPE_R5s_05_to_10","AMP_SLOPE_R5s_10_to_15",
        "OCV_U1",
        "_SOC_CANONICAL",
    ]
    physics += extra

    # Clean obvious infinities from near-zero denominators in recovery fractions.
    for c in physics:
        out[c] = pd.to_numeric(out[c], errors="coerce")
        out.loc[~np.isfinite(out[c]), c] = np.nan

    return out, physics


def models():
    return {
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=800, min_samples_leaf=2, max_features=0.8,
            random_state=SEED, n_jobs=-1
        ),
        "RandomForest": RandomForestRegressor(
            n_estimators=600, min_samples_leaf=2, max_features=0.8,
            random_state=SEED, n_jobs=-1
        ),
        "HistGradientBoosting": HistGradientBoostingRegressor(
            learning_rate=0.05, max_iter=600, random_state=SEED
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
data, rel_features = add_rel_ratio(data)
data, physics_features = add_physics_features(data)
data = data[data["_SOH"].notna()].copy()

feature_sets = {
    "REL_RATIO": rel_features,
    "PHYSICS": physics_features,
    "REL_PLUS_PHYSICS": list(dict.fromkeys(rel_features + physics_features)),
}

# Physics plausibility / missingness audit
audit_rows = []
for c in physics_features:
    s = pd.to_numeric(data[c], errors="coerce")
    valid = s.dropna()
    audit_rows.append({
        "feature": c,
        "valid_fraction": float(s.notna().mean()),
        "median": float(valid.median()) if len(valid) else np.nan,
        "p05": float(valid.quantile(0.05)) if len(valid) else np.nan,
        "p95": float(valid.quantile(0.95)) if len(valid) else np.nan,
        "min": float(valid.min()) if len(valid) else np.nan,
        "max": float(valid.max()) if len(valid) else np.nan,
    })
pd.DataFrame(audit_rows).to_csv(OUT / "02_physics_feature_audit.csv", index=False)

metrics = []

# Leave-one-group-out
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
                **res,
                "train_cells": train["_cell_id"].nunique(),
                "test_cells": test["_cell_id"].nunique(),
            })

# Leave-one-chemistry-out
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
                **res,
                "train_cells": train["_cell_id"].nunique(),
                "test_cells": test["_cell_id"].nunique(),
            })

metrics = pd.DataFrame(metrics)
metrics.to_csv(OUT / "03_ecm_feature_cross_domain_metrics.csv", index=False)

best = (
    metrics.sort_values(["experiment","target_domain","MAE_pp"])
    .groupby(["experiment","target_domain"], as_index=False)
    .first()
)
best.to_csv(OUT / "04_best_feature_model_by_domain.csv", index=False)

agg = (
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
agg.to_csv(OUT / "05_feature_set_aggregate.csv", index=False)

# Figure 1: chemistry-level aggregate
chem = agg[agg["experiment"] == "LeaveOneChemistryOut"].copy()
plt.figure(figsize=(7.5,5.0))
x = np.arange(len(chem))
plt.bar(x, chem["mean_MAE_pp"])
plt.xticks(x, chem["feature_set"], rotation=25, ha="right")
plt.ylabel("Mean MAE across held-out chemistries (pp)")
plt.title("ECM-inspired physics features vs REL_RATIO")
plt.tight_layout()
plt.savefig(OUT / "Fig01_Chemistry_FeatureSet_MAE.png", dpi=300)
plt.savefig(OUT / "Fig01_Chemistry_FeatureSet_MAE.pdf")
plt.close()

# Figure 2: group-level aggregate
grp = agg[agg["experiment"] == "LeaveOneGroupOut"].copy()
plt.figure(figsize=(7.5,5.0))
x = np.arange(len(grp))
plt.bar(x, grp["mean_MAE_pp"])
plt.xticks(x, grp["feature_set"], rotation=25, ha="right")
plt.ylabel("Mean MAE across held-out groups (pp)")
plt.title("Group transfer: ECM-inspired physics features")
plt.tight_layout()
plt.savefig(OUT / "Fig02_Group_FeatureSet_MAE.png", dpi=300)
plt.savefig(OUT / "Fig02_Group_FeatureSet_MAE.pdf")
plt.close()

# Figure 3: selected resistance surrogates by chemistry
selected = ["C05_POS_Rstart","C10_POS_Rstart","C15_POS_Rstart"]
long = []
for c in selected:
    for chem_name, g in data.groupby("_chemistry"):
        for val in g[c].dropna().to_numpy():
            long.append({"chemistry": chem_name, "feature": c, "value": val})
long = pd.DataFrame(long)

if not long.empty:
    labels = []
    values = []
    for feat in selected:
        for chem_name in sorted(data["_chemistry"].unique()):
            arr = long[
                (long["feature"] == feat) & (long["chemistry"] == chem_name)
            ]["value"].to_numpy()
            if len(arr):
                labels.append(f"{feat}\n{chem_name}")
                values.append(arr)

    plt.figure(figsize=(11,5.5))
    plt.boxplot(values, labels=labels, showfliers=False)
    plt.ylabel("Resistance surrogate (Ohm)")
    plt.title("Pulse resistance surrogates by chemistry")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(OUT / "Fig03_Resistance_Surrogates.png", dpi=300)
    plt.savefig(OUT / "Fig03_Resistance_Surrogates.pdf")
    plt.close()

run_summary = {
    "day": "Day12",
    "purpose": "Derive ECM-inspired pulse-response surrogate features from PulseBat U1-U21 and test cross-domain SOH value.",
    "pulse_width_s": 5.0,
    "rest_time_s": 75.0,
    "feature_semantics": {
        "U1": "OCV after 10-min rest",
        "U2_U9": "0.5C positive/rest/negative/rest turning points",
        "U10_U17": "1C positive/rest/negative/rest turning points",
        "U18_U21": "1.5C positive/rest turning points",
    },
    "feature_sets": list(feature_sets.keys()),
    "important_scope_boundary": (
        "Derived resistance/polarization values are ECM-inspired surrogates, not certified "
        "R0/R1/C1/R2/C2 parameters and not a fitted 2RC Digital Twin."
    ),
    "output_dir": str(OUT),
}
(OUT / "06_run_summary.json").write_text(
    json.dumps(run_summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 12 COMPLETE ===")
print("\nAggregate feature-set benchmark:")
print(agg.to_string(index=False))
print("\nBest by held-out domain:")
print(best.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("02_physics_feature_audit.csv")
print("03_ecm_feature_cross_domain_metrics.csv")
print("04_best_feature_model_by_domain.csv")
print("05_feature_set_aggregate.csv")
print("06_run_summary.json")
