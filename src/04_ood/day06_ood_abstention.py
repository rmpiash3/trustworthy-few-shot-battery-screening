r"""
Day 06 — OOD detection + abstention / selective prediction
=========================================================

Purpose
-------
Test whether the framework can detect an unseen chemistry as out-of-distribution
and abstain from unsafe SOH predictions.

Primary evaluation:
- Hold out one chemistry at a time as OOD
- Train OOD detector ONLY on source/in-distribution cells
- Evaluate against held-out source validation cells + unseen chemistry cells
- Metrics: AUROC, AUPRC, FPR@95TPR

OOD representations:
1. REL_CELL:
   cell-level mean/std of REL_RATIO pulse features + SOC statistics

2. RAW_REL_CELL:
   cell-level mean/std of raw U1-U21 + REL_RATIO + SOC statistics

Detectors:
- Mahalanobis distance with Ledoit-Wolf covariance
- Isolation Forest
- kNN distance (k=5)

Deployment-style abstention:
- Threshold is set from source validation cells ONLY
- 95th percentile source OOD score is used
- Target cells above threshold are rejected/abstained
- Accepted-target MAE is compared with all-target MAE

Selective risk curves:
- Retain lowest-risk 100%, 90%, 80%, 70%, 60%, 50% target cells
- Report retained MAE/RMSE

All evaluation is CELL-level.

Output:
D:\SecondLife_Research\Result\Day06_OOD_Abstention
"""

from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.covariance import LedoitWolf
from sklearn.ensemble import ExtraTreesRegressor, IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
    average_precision_score,
    roc_curve,
)
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

SEED = 42
REPEATS = 10
KNN_K = 5
SOURCE_VAL_FRACTION = 0.20
SOURCE_THRESHOLD_QUANTILE = 0.95
RETENTION_LEVELS = [1.00, 0.90, 0.80, 0.70, 0.60, 0.50]
EPS = 1e-8

ROOT = Path(r"D:\SecondLife_Research")
PULSEBAT_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day06_OOD_Abstention"
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


def load_data():
    files = sorted(
        f for f in PULSEBAT_ROOT.rglob("*.xlsx")
        if f.name in EXPECTED_BASENAMES
    )
    if len(files) != 4:
        raise FileNotFoundError(
            f"Expected 4 PulseBat processed files under {PULSEBAT_ROOT}; "
            f"found {len(files)}."
        )

    frames = []
    audit = []

    for f in files:
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(f, sheet_name=sheet).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]

        group = infer_group(f)
        chem = chemistry_from_text(group)
        cap = capacity_from_text(group)

        id_col = next(
            (c for c in df.columns if str(c).strip().lower()
             in {"id", "batteryid", "battery_id", "cell_id", "cellid"}),
            None
        )
        soh_col = next(
            (c for c in df.columns if str(c).strip().lower() == "soh"),
            None
        )
        if id_col is None or soh_col is None:
            raise ValueError(f"Missing ID/SOH field in {f.name}")

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
            "chemistry": chem,
            "rows": len(df),
            "cells": df["_cell_id"].nunique(),
            "soc_source": soc_source,
            "u_count": len(ucols),
        })
        frames.append(df)

    data = pd.concat(frames, ignore_index=True, sort=False)

    common = None
    for _, g in data.groupby("_group"):
        s = {
            c for c in g.columns
            if re.fullmatch(r"U(\d+)", str(c), flags=re.I)
            and numeric(g[c]).notna().any()
        }
        common = s if common is None else common & s

    ucols = sorted(common, key=lambda x: int(re.findall(r"\d+", x)[0]))
    pd.DataFrame(audit).to_csv(OUT / "01_schema_audit.csv", index=False)
    return data, ucols


def add_rel_ratio(df, ucols):
    out = df.copy()
    u1 = out[ucols[0]].astype(float)
    ratio_cols = []
    for c in ucols[1:]:
        name = f"RATIO_{c}"
        out[name] = (out[c] - out[ucols[0]]) / (u1.abs() + EPS)
        ratio_cols.append(name)
    return out, ratio_cols


def build_cell_features(df, raw_cols, ratio_cols):
    rows = []

    for cell_id, g in df.groupby("_cell_id"):
        row = {
            "_cell_id": cell_id,
            "_group": g["_group"].iloc[0],
            "_chemistry": g["_chemistry"].iloc[0],
            "_SOH": float(g["_SOH"].median()),
            "SOC_MEAN": float(g["_SOC_CANONICAL"].mean()),
            "SOC_STD": float(g["_SOC_CANONICAL"].std(ddof=0)),
        }

        for c in raw_cols:
            row[f"RAW_MEAN_{c}"] = float(g[c].mean())
            row[f"RAW_STD_{c}"] = float(g[c].std(ddof=0))

        for c in ratio_cols:
            row[f"REL_MEAN_{c}"] = float(g[c].mean())
            row[f"REL_STD_{c}"] = float(g[c].std(ddof=0))

        rows.append(row)

    return pd.DataFrame(rows)


def representation_columns(cell_df):
    rel_cols = [
        c for c in cell_df.columns
        if c.startswith("REL_MEAN_") or c.startswith("REL_STD_")
    ] + ["SOC_MEAN", "SOC_STD"]

    raw_rel_cols = [
        c for c in cell_df.columns
        if (
            c.startswith("RAW_MEAN_")
            or c.startswith("RAW_STD_")
            or c.startswith("REL_MEAN_")
            or c.startswith("REL_STD_")
        )
    ] + ["SOC_MEAN", "SOC_STD"]

    return {
        "REL_CELL": rel_cols,
        "RAW_REL_CELL": raw_rel_cols,
    }


class OODDetector:
    def __init__(self, kind, seed=SEED):
        self.kind = kind
        self.seed = seed
        self.imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        self.model = None

    def fit(self, X):
        X = self.imputer.fit_transform(X)
        X = self.scaler.fit_transform(X)

        if self.kind == "Mahalanobis":
            self.model = LedoitWolf().fit(X)

        elif self.kind == "IsolationForest":
            self.model = IsolationForest(
                n_estimators=500,
                contamination="auto",
                random_state=self.seed,
                n_jobs=-1,
            ).fit(X)

        elif self.kind == "KNN":
            k = min(KNN_K, max(1, len(X)))
            self.model = NearestNeighbors(n_neighbors=k)
            self.model.fit(X)

        else:
            raise ValueError(self.kind)

        return self

    def score(self, X):
        X = self.imputer.transform(X)
        X = self.scaler.transform(X)

        if self.kind == "Mahalanobis":
            center = self.model.location_
            precision = self.model.precision_
            d = X - center
            # squared Mahalanobis distance
            return np.einsum("ij,jk,ik->i", d, precision, d)

        if self.kind == "IsolationForest":
            # score_samples: larger = more normal; invert so larger = more OOD
            return -self.model.score_samples(X)

        if self.kind == "KNN":
            dist, _ = self.model.kneighbors(X)
            return dist.mean(axis=1)

        raise ValueError(self.kind)


def fpr_at_95_tpr(y_true, scores):
    fpr, tpr, _ = roc_curve(y_true, scores)
    idx = np.where(tpr >= 0.95)[0]
    if len(idx) == 0:
        return np.nan
    return float(fpr[idx[0]])


def fit_soh_source_model(source_rows, ratio_cols, seed):
    features = ratio_cols + ["_SOC_CANONICAL"]

    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(source_rows[features])
    y = source_rows["_SOH"].to_numpy()

    model = ExtraTreesRegressor(
        n_estimators=800,
        min_samples_leaf=2,
        max_features=0.8,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X, y)
    return imputer, model, features


def predict_cell_soh(imputer, model, features, rows):
    row_pred = model.predict(imputer.transform(rows[features]))
    temp = rows[["_cell_id", "_SOH"]].copy()
    temp["pred"] = row_pred

    cell = (
        temp.groupby("_cell_id", as_index=False)
        .agg(
            true_SOH=("_SOH", "median"),
            pred_SOH=("pred", "mean"),
        )
    )
    cell["abs_error_pp"] = np.abs(cell["pred_SOH"] - cell["true_SOH"]) * 100
    return cell


data, ucols = load_data()
data, ratio_cols = add_rel_ratio(data, ucols)
data = data[data["_SOH"].notna()].copy()

cell_df = build_cell_features(data, ucols, ratio_cols)
rep_cols = representation_columns(cell_df)

cell_df.to_csv(OUT / "02_cell_level_features.csv", index=False)

detector_metric_rows = []
abstention_rows = []
selective_rows = []

for target_chem in sorted(cell_df["_chemistry"].unique()):
    source_cells_all = cell_df[cell_df["_chemistry"] != target_chem].copy()
    target_cells = cell_df[cell_df["_chemistry"] == target_chem].copy()

    source_ids_all = np.array(sorted(source_cells_all["_cell_id"].unique()))

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED + rep)
        source_ids = source_ids_all.copy()
        rng.shuffle(source_ids)

        n_val = max(10, int(round(len(source_ids) * SOURCE_VAL_FRACTION)))
        val_ids = source_ids[:n_val]
        train_ids = source_ids[n_val:]

        source_train_cells = source_cells_all[
            source_cells_all["_cell_id"].isin(train_ids)
        ].copy()
        source_val_cells = source_cells_all[
            source_cells_all["_cell_id"].isin(val_ids)
        ].copy()

        # Pulse-row source training set for SOH predictor
        source_train_rows = data[
            data["_cell_id"].isin(train_ids)
        ].copy()

        imputer_soh, model_soh, soh_features = fit_soh_source_model(
            source_train_rows, ratio_cols, SEED + rep
        )

        target_rows = data[
            data["_chemistry"] == target_chem
        ].copy()
        target_soh = predict_cell_soh(
            imputer_soh, model_soh, soh_features, target_rows
        )

        target_eval = target_cells.merge(
            target_soh,
            on="_cell_id",
            how="inner"
        )

        all_target_mae = mean_absolute_error(
            target_eval["true_SOH"],
            target_eval["pred_SOH"]
        ) * 100

        for rep_name, cols in rep_cols.items():
            for det_name in ["Mahalanobis", "IsolationForest", "KNN"]:
                detector = OODDetector(det_name, seed=SEED + rep)
                detector.fit(source_train_cells[cols])

                src_scores = detector.score(source_val_cells[cols])
                tgt_scores = detector.score(target_eval[cols])

                y_true = np.concatenate([
                    np.zeros(len(src_scores), dtype=int),
                    np.ones(len(tgt_scores), dtype=int),
                ])
                scores = np.concatenate([src_scores, tgt_scores])

                auroc = roc_auc_score(y_true, scores)
                auprc = average_precision_score(y_true, scores)
                fpr95 = fpr_at_95_tpr(y_true, scores)

                detector_metric_rows.append({
                    "target_chemistry": target_chem,
                    "repeat": rep,
                    "representation": rep_name,
                    "detector": det_name,
                    "AUROC": auroc,
                    "AUPRC": auprc,
                    "FPR_at_95TPR": fpr95,
                    "source_train_cells": len(source_train_cells),
                    "source_val_cells": len(source_val_cells),
                    "ood_target_cells": len(target_eval),
                })

                # Deployment-style threshold from source validation only
                threshold = float(
                    np.quantile(src_scores, SOURCE_THRESHOLD_QUANTILE)
                )
                accepted = tgt_scores <= threshold

                if accepted.sum() > 0:
                    accepted_mae = mean_absolute_error(
                        target_eval.loc[accepted, "true_SOH"],
                        target_eval.loc[accepted, "pred_SOH"]
                    ) * 100
                    accepted_rmse = mean_squared_error(
                        target_eval.loc[accepted, "true_SOH"],
                        target_eval.loc[accepted, "pred_SOH"]
                    ) ** 0.5 * 100
                else:
                    accepted_mae = np.nan
                    accepted_rmse = np.nan

                abstention_rows.append({
                    "target_chemistry": target_chem,
                    "repeat": rep,
                    "representation": rep_name,
                    "detector": det_name,
                    "threshold_quantile_source": SOURCE_THRESHOLD_QUANTILE,
                    "threshold": threshold,
                    "target_cells": len(target_eval),
                    "accepted_cells": int(accepted.sum()),
                    "abstained_cells": int((~accepted).sum()),
                    "acceptance_rate": float(accepted.mean()),
                    "abstention_rate": float((~accepted).mean()),
                    "all_target_MAE_pp": all_target_mae,
                    "accepted_MAE_pp": accepted_mae,
                    "accepted_RMSE_pp": accepted_rmse,
                    "MAE_reduction_pp":
                        all_target_mae - accepted_mae
                        if np.isfinite(accepted_mae) else np.nan,
                })

                # Selective risk curve on target cells
                order = np.argsort(tgt_scores)  # low score = more ID-like
                n = len(order)

                for retention in RETENTION_LEVELS:
                    keep_n = max(1, int(np.ceil(n * retention)))
                    keep = order[:keep_n]

                    yk = target_eval["true_SOH"].to_numpy()[keep]
                    pk = target_eval["pred_SOH"].to_numpy()[keep]

                    selective_rows.append({
                        "target_chemistry": target_chem,
                        "repeat": rep,
                        "representation": rep_name,
                        "detector": det_name,
                        "retention_fraction": retention,
                        "coverage_fraction": retention,
                        "retained_cells": keep_n,
                        "MAE_pp":
                            mean_absolute_error(yk, pk) * 100,
                        "RMSE_pp":
                            mean_squared_error(yk, pk) ** 0.5 * 100,
                        "R2":
                            r2_score(yk, pk) if len(yk) > 1 else np.nan,
                    })

det_metrics = pd.DataFrame(detector_metric_rows)
abstention = pd.DataFrame(abstention_rows)
selective = pd.DataFrame(selective_rows)

det_metrics.to_csv(OUT / "03_ood_repeat_metrics.csv", index=False)
abstention.to_csv(OUT / "04_abstention_repeat_metrics.csv", index=False)
selective.to_csv(OUT / "05_selective_risk_repeat_metrics.csv", index=False)

det_agg = (
    det_metrics.groupby([
        "target_chemistry", "representation", "detector"
    ])
    .agg(
        AUROC_mean=("AUROC", "mean"),
        AUROC_std=("AUROC", "std"),
        AUPRC_mean=("AUPRC", "mean"),
        AUPRC_std=("AUPRC", "std"),
        FPR95_mean=("FPR_at_95TPR", "mean"),
        FPR95_std=("FPR_at_95TPR", "std"),
        repeats=("repeat", "nunique"),
    )
    .reset_index()
)
det_agg.to_csv(OUT / "06_ood_aggregate_metrics.csv", index=False)

abst_agg = (
    abstention.groupby([
        "target_chemistry", "representation", "detector"
    ])
    .agg(
        acceptance_rate_mean=("acceptance_rate", "mean"),
        acceptance_rate_std=("acceptance_rate", "std"),
        abstention_rate_mean=("abstention_rate", "mean"),
        all_target_MAE_mean_pp=("all_target_MAE_pp", "mean"),
        accepted_MAE_mean_pp=("accepted_MAE_pp", "mean"),
        accepted_MAE_std_pp=("accepted_MAE_pp", "std"),
        MAE_reduction_mean_pp=("MAE_reduction_pp", "mean"),
        repeats=("repeat", "nunique"),
    )
    .reset_index()
)
abst_agg.to_csv(OUT / "07_abstention_aggregate_metrics.csv", index=False)

sel_agg = (
    selective.groupby([
        "target_chemistry", "representation", "detector",
        "retention_fraction"
    ])
    .agg(
        MAE_mean_pp=("MAE_pp", "mean"),
        MAE_std_pp=("MAE_pp", "std"),
        RMSE_mean_pp=("RMSE_pp", "mean"),
        R2_mean=("R2", "mean"),
    )
    .reset_index()
)
sel_agg.to_csv(OUT / "08_selective_risk_aggregate.csv", index=False)

# Primary pre-specified OOD system:
# RAW_REL_CELL + Mahalanobis
primary_det = det_agg[
    (det_agg["representation"] == "RAW_REL_CELL")
    & (det_agg["detector"] == "Mahalanobis")
].copy()
primary_det.to_csv(OUT / "09_primary_ood_metrics.csv", index=False)

primary_abst = abst_agg[
    (abst_agg["representation"] == "RAW_REL_CELL")
    & (abst_agg["detector"] == "Mahalanobis")
].copy()
primary_abst.to_csv(OUT / "10_primary_abstention_metrics.csv", index=False)

# ----------------------------------------------------------
# Figures
# ----------------------------------------------------------

# AUROC by chemistry for all detector/representation pairs
plot = det_agg.copy()
plot["system"] = plot["representation"] + " + " + plot["detector"]

for chem in sorted(plot["target_chemistry"].unique()):
    d = plot[plot["target_chemistry"] == chem].sort_values(
        "AUROC_mean", ascending=False
    )
    plt.figure(figsize=(10, 5.5))
    x = np.arange(len(d))
    plt.bar(x, d["AUROC_mean"])
    plt.axhline(0.5, linestyle="--", linewidth=1)
    plt.xticks(x, d["system"], rotation=35, ha="right")
    plt.ylabel("OOD AUROC")
    plt.ylim(0, 1.05)
    plt.title(f"OOD detection — held-out {chem}")
    plt.tight_layout()
    plt.savefig(OUT / f"Fig01_OOD_AUROC_{chem}.png", dpi=300)
    plt.savefig(OUT / f"Fig01_OOD_AUROC_{chem}.pdf")
    plt.close()

# Primary selective risk curves
primary_sel = sel_agg[
    (sel_agg["representation"] == "RAW_REL_CELL")
    & (sel_agg["detector"] == "Mahalanobis")
].copy()

plt.figure(figsize=(7.8, 5.3))
for chem in sorted(primary_sel["target_chemistry"].unique()):
    d = primary_sel[
        primary_sel["target_chemistry"] == chem
    ].sort_values("retention_fraction")
    plt.plot(
        d["retention_fraction"] * 100,
        d["MAE_mean_pp"],
        marker="o",
        label=chem
    )
plt.xlabel("Retained target cells (%)")
plt.ylabel("SOH MAE among retained cells (pp)")
plt.title("Selective prediction — RAW_REL Mahalanobis")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig02_Primary_Selective_Risk.png", dpi=300)
plt.savefig(OUT / "Fig02_Primary_Selective_Risk.pdf")
plt.close()

# Primary abstention rate and accepted MAE
plt.figure(figsize=(7.5, 5.2))
x = np.arange(len(primary_abst))
width = 0.38
plt.bar(
    x - width/2,
    primary_abst["all_target_MAE_mean_pp"],
    width,
    label="All target"
)
plt.bar(
    x + width/2,
    primary_abst["accepted_MAE_mean_pp"],
    width,
    label="Accepted only"
)
plt.xticks(x, primary_abst["target_chemistry"])
plt.ylabel("SOH MAE (pp)")
plt.title("Error after source-calibrated OOD abstention")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig03_Primary_Abstention_MAE.png", dpi=300)
plt.savefig(OUT / "Fig03_Primary_Abstention_MAE.pdf")
plt.close()

summary = {
    "day": "Day06",
    "evaluation_grain": "cell-level",
    "held_out_domains": sorted(cell_df["_chemistry"].unique().tolist()),
    "ood_representations": list(rep_cols.keys()),
    "detectors": ["Mahalanobis", "IsolationForest", "KNN"],
    "repeats": REPEATS,
    "source_validation_fraction": SOURCE_VAL_FRACTION,
    "source_only_abstention_threshold_quantile": SOURCE_THRESHOLD_QUANTILE,
    "selective_retention_levels": RETENTION_LEVELS,
    "primary_pre_specified_system": "RAW_REL_CELL + Mahalanobis",
    "important_note": (
        "OOD detector fitting and abstention threshold use source cells only. "
        "Held-out target chemistry labels are used only for evaluation metrics, "
        "not detector training or threshold selection."
    )
}
(OUT / "11_run_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 06 COMPLETE ===")
print("\nPrimary OOD metrics:")
print(primary_det.to_string(index=False))
print("\nPrimary abstention metrics:")
print(primary_abst.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("06_ood_aggregate_metrics.csv")
print("07_abstention_aggregate_metrics.csv")
print("08_selective_risk_aggregate.csv")
print("09_primary_ood_metrics.csv")
print("10_primary_abstention_metrics.csv")
print("11_run_summary.json")
