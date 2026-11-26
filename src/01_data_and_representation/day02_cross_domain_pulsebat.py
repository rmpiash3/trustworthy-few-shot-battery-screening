r"""
Day 02 — PulseBat schema harmonization + cross-domain validation
AUTO-DETECT VERSION

Research root:
D:\SecondLife_Research

PulseBat search root:
D:\SecondLife_Research\Data\PulseBat

This version recursively searches ALL subfolders under PulseBat for .xlsx files,
so it works whether the files are:
- directly inside PulseBat,
- inside ProcessedData_adjustable,
- inside chemistry subfolders,
- or one extra extracted folder deep.

Results:
D:\SecondLife_Research\Result\Day02_CrossDomain
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
ROOT = Path(r"D:\SecondLife_Research")
PULSEBAT_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day02_CrossDomain"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_BASENAMES = {
    "NMC_2.1Ah_W_5000.xlsx",
    "LMO_10Ah_W_5000.xlsx",
    "NMC_21Ah_W_5000.xlsx",
    "LFP_35Ah_W_5000.xlsx",
}

def normalize_name(x):
    return str(x).strip()

def numeric_series(s):
    return pd.to_numeric(s, errors="coerce")

def normalize_soc(s):
    s = numeric_series(s)
    valid = s.dropna()
    if valid.empty:
        return s
    if valid.quantile(0.95) > 1.5:
        return s / 100.0
    return s

def chemistry_from_text(text):
    s = str(text).upper()
    if "NMC" in s:
        return "NMC"
    if "LMO" in s:
        return "LMO"
    if "LFP" in s:
        return "LFP"
    return "UNKNOWN"

def capacity_ah_from_text(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*AH", str(text), flags=re.I)
    return float(m.group(1)) if m else np.nan

def infer_group_from_file(f):
    name = f.name.upper()
    if "2.1AH" in name and "NMC" in name:
        return "2.1Ah NMC"
    if "10AH" in name and "LMO" in name:
        return "10Ah LMO"
    if "21AH" in name and "NMC" in name:
        return "21Ah NMC"
    if "35AH" in name and "LFP" in name:
        return "35Ah LFP"
    # fallback to parent folder
    return f.parent.name

def find_pulsebat_files():
    if not PULSEBAT_ROOT.exists():
        raise FileNotFoundError(
            f"PulseBat root does not exist:\n{PULSEBAT_ROOT}\n"
            "Create it and place the downloaded Excel files somewhere inside it."
        )

    all_xlsx = sorted(PULSEBAT_ROOT.rglob("*.xlsx"))

    # Prefer the four expected processed files.
    expected = [f for f in all_xlsx if f.name in EXPECTED_BASENAMES]

    print("\n=== FILE DISCOVERY ===")
    print(f"Search root: {PULSEBAT_ROOT}")
    print(f"All .xlsx files found: {len(all_xlsx)}")

    if all_xlsx:
        for f in all_xlsx:
            print("FOUND:", f)

    if len(expected) == 4:
        files = sorted(expected)
    else:
        files = all_xlsx

    if not files:
        raise FileNotFoundError(
            f"No .xlsx files found anywhere under:\n{PULSEBAT_ROOT}\n\n"
            "Move/extract the four processed PulseBat Excel files under this folder."
        )

    # If there are many xlsx files, retain only recognized processed filenames when possible.
    recognized = [f for f in files if f.name in EXPECTED_BASENAMES]
    if recognized:
        files = recognized

    print("\nFiles selected for Day02:")
    for f in files:
        print("USE:", f)

    discovery = pd.DataFrame({
        "selected_file": [str(f) for f in files],
        "basename": [f.name for f in files],
    })
    discovery.to_csv(OUT / "00_file_discovery.csv", index=False)

    return files

def read_pulsebat():
    files = find_pulsebat_files()

    frames = []
    audit_rows = []

    for f in files:
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(f, sheet_name=sheet)
        df.columns = [normalize_name(c) for c in df.columns]
        df = df.dropna(how="all").copy()

        group = infer_group_from_file(f)
        chemistry = chemistry_from_text(group + " " + f.name)
        capacity = capacity_ah_from_text(group + " " + f.name)

        df["_source_file"] = str(f)
        df["_group"] = group
        df["_chemistry"] = chemistry
        df["_capacity_Ah"] = capacity

        id_candidates = [c for c in df.columns if str(c).strip().lower() in {
            "id", "batteryid", "battery_id", "cell_id", "cellid"
        }]
        if not id_candidates:
            raise ValueError(f"No battery ID column found in {f.name}")
        id_col = id_candidates[0]

        df["_cell_id"] = df["_group"].astype(str) + "::" + df[id_col].astype(str)

        soh_candidates = [c for c in df.columns if str(c).strip().lower() == "soh"]
        if not soh_candidates:
            raise ValueError(f"No SOH column found in {f.name}")
        soh_col = soh_candidates[0]

        df["_SOH"] = numeric_series(df[soh_col])
        if df["_SOH"].dropna().median() > 2:
            df["_SOH"] = df["_SOH"] / 100.0

        if "SOCR" in df.columns and numeric_series(df["SOCR"]).notna().any():
            df["_SOC_CANONICAL"] = normalize_soc(df["SOCR"])
            soc_source = "SOCR"
        elif "SOE" in df.columns and numeric_series(df["SOE"]).notna().any():
            df["_SOC_CANONICAL"] = normalize_soc(df["SOE"])
            soc_source = "SOE"
        elif "SOC" in df.columns and numeric_series(df["SOC"]).notna().any():
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
            df[c] = numeric_series(df[c])

        audit_rows.append({
            "file": str(f),
            "group": group,
            "chemistry": chemistry,
            "capacity_Ah": capacity,
            "rows": len(df),
            "unique_cells": df["_cell_id"].nunique(),
            "id_column": id_col,
            "soh_column": soh_col,
            "soc_source_used": soc_source,
            "u_feature_count": len(ucols),
            "u_first": ucols[0] if ucols else None,
            "u_last": ucols[-1] if ucols else None,
            "SOH_min": df["_SOH"].min(),
            "SOH_max": df["_SOH"].max(),
            "SOC_min": df["_SOC_CANONICAL"].min(),
            "SOC_max": df["_SOC_CANONICAL"].max(),
        })

        frames.append(df)

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(OUT / "01_dataset_schema_audit.csv", index=False)

    data = pd.concat(frames, ignore_index=True, sort=False)

    u_feature_sets = []
    for _, gdf in data.groupby("_group"):
        us = set()
        for c in gdf.columns:
            if re.fullmatch(r"U(\d+)", str(c), flags=re.I):
                if numeric_series(gdf[c]).notna().any():
                    us.add(c)
        u_feature_sets.append(us)

    common_u = sorted(
        set.intersection(*u_feature_sets),
        key=lambda x: int(re.findall(r"\d+", x)[0])
    )

    if len(common_u) < 5:
        raise RuntimeError(
            f"Only {len(common_u)} common U-features across groups: {common_u}"
        )

    return data, audit, common_u

def make_models():
    return {
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=800,
            random_state=SEED,
            n_jobs=-1,
            min_samples_leaf=2,
            max_features=0.8,
        ),
        "RandomForest": RandomForestRegressor(
            n_estimators=600,
            random_state=SEED,
            n_jobs=-1,
            min_samples_leaf=2,
            max_features=0.8,
        ),
        "HistGradientBoosting": HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_iter=600,
            l2_regularization=1e-3,
            random_state=SEED,
        ),
    }

def fit_predict(train_df, test_df, feature_cols, estimator):
    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", estimator),
    ])

    Xtr = train_df[feature_cols]
    ytr = train_df["_SOH"]
    Xte = test_df[feature_cols]
    yte = test_df["_SOH"]

    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)

    mae = mean_absolute_error(yte, pred)
    rmse = mean_squared_error(yte, pred) ** 0.5
    r2 = r2_score(yte, pred) if len(yte) > 1 else np.nan

    return pipe, pred, mae, rmse, r2

data, audit, common_u = read_pulsebat()

feature_cols = common_u + ["_SOC_CANONICAL"]

model_df = data.copy()
model_df = model_df[model_df["_SOH"].notna()].copy()
model_df = model_df[model_df[common_u].notna().any(axis=1)].copy()

group_summary = (
    model_df.groupby(["_group", "_chemistry", "_capacity_Ah"], dropna=False)
    .agg(
        rows=("_SOH", "size"),
        cells=("_cell_id", "nunique"),
        soh_mean=("_SOH", "mean"),
        soh_std=("_SOH", "std"),
        soh_min=("_SOH", "min"),
        soh_max=("_SOH", "max"),
        soc_min=("_SOC_CANONICAL", "min"),
        soc_max=("_SOC_CANONICAL", "max"),
    )
    .reset_index()
)
group_summary.to_csv(OUT / "02_group_summary.csv", index=False)

all_metrics = []
all_preds = []

for target_group in sorted(model_df["_group"].unique()):
    train_df = model_df[model_df["_group"] != target_group].copy()
    test_df = model_df[model_df["_group"] == target_group].copy()

    for model_name, estimator in make_models().items():
        pipe, pred, mae, rmse, r2 = fit_predict(
            train_df, test_df, feature_cols, estimator
        )

        all_metrics.append({
            "experiment": "LeaveOneGroupOut",
            "target_domain": target_group,
            "target_chemistry": test_df["_chemistry"].iloc[0],
            "model": model_name,
            "MAE_pp": mae * 100,
            "RMSE_pp": rmse * 100,
            "R2": r2,
            "train_cells": train_df["_cell_id"].nunique(),
            "test_cells": test_df["_cell_id"].nunique(),
            "train_rows": len(train_df),
            "test_rows": len(test_df),
        })

        p = test_df[[
            "_cell_id", "_group", "_chemistry", "_capacity_Ah",
            "_SOC_CANONICAL", "_SOH", "_source_file"
        ]].copy()
        p["experiment"] = "LeaveOneGroupOut"
        p["target_domain"] = target_group
        p["model"] = model_name
        p["pred_SOH"] = pred
        p["error_pp"] = (pred - p["_SOH"].to_numpy()) * 100
        all_preds.append(p)

        safe_group = re.sub(r"[^A-Za-z0-9]+", "_", target_group)
        joblib.dump(
            pipe,
            OUT / f"model_LOGO_{safe_group}_{model_name}.joblib"
        )

for target_chem in sorted(model_df["_chemistry"].unique()):
    train_df = model_df[model_df["_chemistry"] != target_chem].copy()
    test_df = model_df[model_df["_chemistry"] == target_chem].copy()

    if train_df.empty or test_df.empty:
        continue

    for model_name, estimator in make_models().items():
        pipe, pred, mae, rmse, r2 = fit_predict(
            train_df, test_df, feature_cols, estimator
        )

        all_metrics.append({
            "experiment": "LeaveOneChemistryOut",
            "target_domain": target_chem,
            "target_chemistry": target_chem,
            "model": model_name,
            "MAE_pp": mae * 100,
            "RMSE_pp": rmse * 100,
            "R2": r2,
            "train_cells": train_df["_cell_id"].nunique(),
            "test_cells": test_df["_cell_id"].nunique(),
            "train_rows": len(train_df),
            "test_rows": len(test_df),
        })

        p = test_df[[
            "_cell_id", "_group", "_chemistry", "_capacity_Ah",
            "_SOC_CANONICAL", "_SOH", "_source_file"
        ]].copy()
        p["experiment"] = "LeaveOneChemistryOut"
        p["target_domain"] = target_chem
        p["model"] = model_name
        p["pred_SOH"] = pred
        p["error_pp"] = (pred - p["_SOH"].to_numpy()) * 100
        all_preds.append(p)

metrics = pd.DataFrame(all_metrics)
preds = pd.concat(all_preds, ignore_index=True)

metrics.to_csv(OUT / "03_cross_domain_metrics.csv", index=False)
preds.to_csv(OUT / "04_cross_domain_predictions.csv", index=False)

best_by_target = (
    metrics.sort_values(["experiment", "target_domain", "MAE_pp"])
    .groupby(["experiment", "target_domain"], as_index=False)
    .first()
)
best_by_target.to_csv(OUT / "05_best_model_by_domain.csv", index=False)

fig1 = best_by_target[best_by_target["experiment"] == "LeaveOneGroupOut"].copy()
plt.figure(figsize=(8.5, 5.2))
x = np.arange(len(fig1))
plt.bar(x, fig1["MAE_pp"])
plt.xticks(x, fig1["target_domain"], rotation=25, ha="right")
plt.ylabel("MAE (SOH percentage points)")
plt.title("Leave-one-battery-group-out SOH error")
plt.tight_layout()
plt.savefig(OUT / "Fig01_LOGO_MAE.png", dpi=300)
plt.savefig(OUT / "Fig01_LOGO_MAE.pdf")
plt.close()

fig2 = best_by_target[best_by_target["experiment"] == "LeaveOneChemistryOut"].copy()
plt.figure(figsize=(7.2, 5.0))
x = np.arange(len(fig2))
plt.bar(x, fig2["MAE_pp"])
plt.xticks(x, fig2["target_domain"])
plt.ylabel("MAE (SOH percentage points)")
plt.title("Leave-one-chemistry-out SOH error")
plt.tight_layout()
plt.savefig(OUT / "Fig02_LOCO_MAE.png", dpi=300)
plt.savefig(OUT / "Fig02_LOCO_MAE.pdf")
plt.close()

selected_parts = []
for _, row in best_by_target[
    best_by_target["experiment"] == "LeaveOneGroupOut"
].iterrows():
    part = preds[
        (preds["experiment"] == "LeaveOneGroupOut")
        & (preds["target_domain"] == row["target_domain"])
        & (preds["model"] == row["model"])
    ].copy()
    selected_parts.append(part)

selected = pd.concat(selected_parts, ignore_index=True)

plt.figure(figsize=(6.5, 6.0))
for g, gdf in selected.groupby("_group"):
    plt.scatter(
        gdf["_SOH"] * 100,
        gdf["pred_SOH"] * 100,
        alpha=0.65,
        label=g,
    )
lo = min((selected["_SOH"] * 100).min(), (selected["pred_SOH"] * 100).min())
hi = max((selected["_SOH"] * 100).max(), (selected["pred_SOH"] * 100).max())
plt.plot([lo, hi], [lo, hi], linestyle="--")
plt.xlabel("True SOH (%)")
plt.ylabel("Predicted SOH (%)")
plt.title("Cross-domain SOH prediction")
plt.legend(fontsize=8)
plt.tight_layout()
plt.savefig(OUT / "Fig03_CrossDomain_True_vs_Predicted.png", dpi=300)
plt.savefig(OUT / "Fig03_CrossDomain_True_vs_Predicted.pdf")
plt.close()

plt.figure(figsize=(8.5, 5.2))
groups = sorted(model_df["_group"].unique())
data_for_box = [
    model_df.loc[model_df["_group"] == g, "_SOH"].dropna().to_numpy() * 100
    for g in groups
]
plt.boxplot(data_for_box, tick_labels=groups, showfliers=False)
plt.xticks(rotation=25, ha="right")
plt.ylabel("SOH (%)")
plt.title("SOH distribution by PulseBat battery group")
plt.tight_layout()
plt.savefig(OUT / "Fig04_SOH_Distribution.png", dpi=300)
plt.savefig(OUT / "Fig04_SOH_Distribution.pdf")
plt.close()

summary = {
    "day": "Day02",
    "pulsebat_search_root": str(PULSEBAT_ROOT),
    "output_dir": str(OUT),
    "total_rows": int(len(model_df)),
    "total_unique_cells": int(model_df["_cell_id"].nunique()),
    "groups": sorted(model_df["_group"].unique().tolist()),
    "chemistries": sorted(model_df["_chemistry"].unique().tolist()),
    "common_u_features": common_u,
    "u_feature_count": len(common_u),
    "final_feature_cols": feature_cols,
    "soc_harmonization_rule": "Prefer SOCR; fallback SOE; fallback SOC; normalize percent to fraction.",
    "methodological_note": (
        "Leave-one-group-out and leave-one-chemistry-out tests intentionally evaluate "
        "domain shift. Large degradation relative to Day01 is expected and scientifically meaningful."
    ),
}

(OUT / "06_run_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 02 COMPLETE ===")
print("\nDataset/groups:")
print(group_summary.to_string(index=False))
print("\nBest model per held-out domain:")
print(best_by_target.to_string(index=False))
print(f"\nAll results saved to:\n{OUT}")
print("\nSend me these files after the run:")
print("00_file_discovery.csv")
print("01_dataset_schema_audit.csv")
print("03_cross_domain_metrics.csv")
print("05_best_model_by_domain.csv")
print("06_run_summary.json")
