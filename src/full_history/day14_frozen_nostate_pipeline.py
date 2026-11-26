r"""
Day 14 — Frozen no-state trustworthy pipeline replication
=========================================================

Purpose
-------
Day13 showed that REL_RATIO_NO_STATE performs essentially the same as
REL_RATIO_WITH_STATE and removes the SOCR-vs-SOE ambiguity.

Day14 therefore re-runs the core trustworthy pipeline using ONLY:

    REL_RATIO_i = (Ui - U1) / abs(U1), i=2..21

No SOC, SOCR, SOE or other state variable is used anywhere in the main predictor.

Stages
------
A. Internal chemistry-level zero-shot + few-shot adaptation
B. 90% split-conformal uncertainty calibration
C. OOD detection / abstention without SOC statistics
D. Overlap-excluded PulseBat -> Bipolar709 cross-dataset transfer

This is intended to become the final frozen representation for manuscript tables.

Output
------
D:\SecondLife_Research\Result\Day14_Frozen_NoState_Pipeline
"""

from pathlib import Path
import json
import re
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import ExtraTreesRegressor, IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    roc_auc_score, average_precision_score, roc_curve
)
from sklearn.covariance import LedoitWolf
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

SEED = 42
REPEATS = 10
K_VALUES = [0, 1, 5, 10, 20]
UQ_K_VALUES = [0, 5, 10, 20]
ALPHA = 0.10
TARGET_WEIGHT = 8.0
SOURCE_CAL_FRACTION = 0.20
SOURCE_VAL_FRACTION = 0.20
OOD_THRESHOLD_Q = 0.95
EPS = 1e-12

ROOT = Path(r"D:\SecondLife_Research")
PULSE_ROOT = ROOT / "Data" / "PulseBat"
BIPOLAR_ROOT = ROOT / "Data" / "Bipolar709" / "Data_Process_Output" / "Step2_CellLevel"
OUT = ROOT / "Result" / "Day14_Frozen_NoState_Pipeline"
OUT.mkdir(parents=True, exist_ok=True)

BIPOLAR_CACHE = OUT / "Bipolar709_NoState_cache.csv"

EXPECTED = {
    "NMC_2.1Ah_W_5000.xlsx",
    "LMO_10Ah_W_5000.xlsx",
    "NMC_21Ah_W_5000.xlsx",
    "LFP_35Ah_W_5000.xlsx",
}


def numeric(s):
    return pd.to_numeric(s, errors="coerce")


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


def find_ucols(cols):
    pairs = []
    for c in cols:
        m = re.fullmatch(r"U(\d+)", str(c).strip(), flags=re.I)
        if m:
            pairs.append((int(m.group(1)), str(c).strip()))
    return [c for _, c in sorted(pairs)]


def add_rel_ratio(df, ucols):
    out = df.copy()
    u1 = numeric(out[ucols[0]])
    rel = []
    for c in ucols[1:]:
        name = f"RATIO_{c}"
        out[name] = (numeric(out[c]) - u1) / (u1.abs() + EPS)
        rel.append(name)
    return out, rel


def load_pulsebat():
    files = sorted(f for f in PULSE_ROOT.rglob("*.xlsx") if f.name in EXPECTED)
    if len(files) != 4:
        raise FileNotFoundError(f"Expected 4 PulseBat files; found {len(files)}")

    frames = []
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
        df["_raw_id"] = df[id_col].astype(str).str.strip()
        df["_cell_id"] = group + "::" + df["_raw_id"]

        df["_SOH"] = numeric(df[soh_col])
        if df["_SOH"].dropna().median() > 2:
            df["_SOH"] /= 100.0

        for c in find_ucols(df.columns):
            df[c] = numeric(df[c])

        frames.append(df)

    data = pd.concat(frames, ignore_index=True, sort=False)
    ucols = [f"U{k}" for k in range(1,22)]
    data, rel = add_rel_ratio(data, ucols)
    return data[data["_SOH"].notna()].copy(), ucols, rel


def fit_et(train, features, seed, adapt=None):
    imp = SimpleImputer(strategy="median")
    Xs = imp.fit_transform(train[features])
    ys = train["_SOH"].to_numpy()

    if adapt is None or len(adapt) == 0:
        X = Xs
        y = ys
        w = np.ones(len(Xs))
    else:
        Xa = imp.transform(adapt[features])
        ya = adapt["_SOH"].to_numpy()
        X = np.vstack([Xs, Xa])
        y = np.concatenate([ys, ya])
        w = np.concatenate([
            np.ones(len(Xs)),
            np.full(len(Xa), TARGET_WEIGHT)
        ])

    model = ExtraTreesRegressor(
        n_estimators=800,
        min_samples_leaf=2,
        max_features=0.8,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X, y, sample_weight=w)
    return imp, model


def row_pred(imp, model, df, features):
    return model.predict(imp.transform(df[features]))


def cell_table(df, pred):
    t = df[["_cell_id","_chemistry","_group","_SOH"]].copy()
    t["pred"] = pred
    cell = (
        t.groupby(["_cell_id","_chemistry","_group"], as_index=False)
        .agg(
            true_SOH=("_SOH","median"),
            pred_SOH=("pred","mean"),
            n_rows=("pred","size"),
        )
    )
    cell["abs_error"] = np.abs(cell["pred_SOH"] - cell["true_SOH"])
    return cell


def calc_metrics(cell):
    return {
        "MAE_pp": mean_absolute_error(cell["true_SOH"], cell["pred_SOH"]) * 100,
        "RMSE_pp": mean_squared_error(cell["true_SOH"], cell["pred_SOH"]) ** 0.5 * 100,
        "R2": r2_score(cell["true_SOH"], cell["pred_SOH"]) if len(cell) > 1 else np.nan,
        "Bias_pp": np.mean(cell["pred_SOH"] - cell["true_SOH"]) * 100,
    }


def conformal_qhat(residuals, alpha=ALPHA):
    r = np.asarray(residuals, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n == 0:
        raise ValueError("No calibration residuals")
    level = min(1.0, math.ceil((n+1)*(1-alpha))/n)
    try:
        return float(np.quantile(r, level, method="higher"))
    except TypeError:
        return float(np.quantile(r, level, interpolation="higher"))


# =========================================================
# A. INTERNAL FEW-SHOT — CHEMISTRY LEVEL
# =========================================================

data, ucols, features = load_pulsebat()

few_rows = []

for target_chem in sorted(data["_chemistry"].unique()):
    source = data[data["_chemistry"] != target_chem].copy()
    target = data[data["_chemistry"] == target_chem].copy()
    cells = np.array(sorted(target["_cell_id"].unique()))

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED + rep)
        shuffled = cells.copy()
        rng.shuffle(shuffled)

        for K in K_VALUES:
            if K == 0:
                adapt_ids = np.array([], dtype=object)
                test_ids = shuffled
                imp, model = fit_et(source, features, SEED + rep)
            else:
                adapt_ids = shuffled[:K]
                test_ids = shuffled[K:]
                adapt = target[target["_cell_id"].isin(adapt_ids)]
                imp, model = fit_et(source, features, SEED + rep, adapt=adapt)

            test = target[target["_cell_id"].isin(test_ids)]
            pred = row_pred(imp, model, test, features)
            cell = cell_table(test, pred)

            few_rows.append({
                "target_chemistry": target_chem,
                "repeat": rep,
                "K_cells": K,
                "adapt_cells": len(adapt_ids),
                "test_cells": len(cell),
                **calc_metrics(cell)
            })

few = pd.DataFrame(few_rows)
few.to_csv(OUT / "01_internal_fewshot_repeat_metrics.csv", index=False)

few_agg = (
    few.groupby(["target_chemistry","K_cells"])
    .agg(
        MAE_mean_pp=("MAE_pp","mean"),
        MAE_std_pp=("MAE_pp","std"),
        RMSE_mean_pp=("RMSE_pp","mean"),
        R2_mean=("R2","mean"),
        Bias_mean_pp=("Bias_pp","mean"),
        repeats=("repeat","nunique"),
    )
    .reset_index()
)
few_agg.to_csv(OUT / "02_internal_fewshot_aggregate.csv", index=False)


# =========================================================
# B. 90% SPLIT-CONFORMAL UQ — CHEMISTRY LEVEL
# =========================================================

uq_rows = []

for target_chem in sorted(data["_chemistry"].unique()):
    source_all = data[data["_chemistry"] != target_chem].copy()
    target_all = data[data["_chemistry"] == target_chem].copy()

    src_cells_all = np.array(sorted(source_all["_cell_id"].unique()))
    tgt_cells_all = np.array(sorted(target_all["_cell_id"].unique()))

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED + rep)
        src_cells = src_cells_all.copy()
        rng.shuffle(src_cells)

        n_src_cal = max(10, int(round(len(src_cells)*SOURCE_CAL_FRACTION)))
        src_cal_ids = src_cells[:n_src_cal]
        src_train_ids = src_cells[n_src_cal:]

        src_train = source_all[source_all["_cell_id"].isin(src_train_ids)]
        src_cal = source_all[source_all["_cell_id"].isin(src_cal_ids)]

        tgt_cells = tgt_cells_all.copy()
        rng.shuffle(tgt_cells)

        for K in UQ_K_VALUES:
            if K == 0:
                adapt_ids = np.array([], dtype=object)
                cal_ids = np.array([], dtype=object)
                test_ids = tgt_cells

                imp, model = fit_et(src_train, features, SEED + rep)
                cal_pred = row_pred(imp, model, src_cal, features)
                cal_cell = cell_table(src_cal, cal_pred)
                qhat = conformal_qhat(cal_cell["abs_error"])

            else:
                if K >= len(tgt_cells):
                    continue

                labeled = tgt_cells[:K]
                test_ids = tgt_cells[K:]

                n_adapt = int(math.ceil(K/2))
                adapt_ids = labeled[:n_adapt]
                cal_ids = labeled[n_adapt:]

                if len(cal_ids) < 2:
                    continue

                adapt = target_all[target_all["_cell_id"].isin(adapt_ids)]
                cal = target_all[target_all["_cell_id"].isin(cal_ids)]

                imp, model = fit_et(src_train, features, SEED + rep, adapt=adapt)
                cal_pred = row_pred(imp, model, cal, features)
                cal_cell = cell_table(cal, cal_pred)
                qhat = conformal_qhat(cal_cell["abs_error"])

            test = target_all[target_all["_cell_id"].isin(test_ids)]
            pred = row_pred(imp, model, test, features)
            cell = cell_table(test, pred)

            y = cell["true_SOH"].to_numpy()
            p = cell["pred_SOH"].to_numpy()
            lower = p - qhat
            upper = p + qhat
            covered = (y >= lower) & (y <= upper)

            uq_rows.append({
                "target_chemistry": target_chem,
                "repeat": rep,
                "K_total_labeled_cells": K,
                "K_adaptation_cells": len(adapt_ids),
                "K_calibration_cells": len(cal_ids),
                "MAE_pp": mean_absolute_error(y,p)*100,
                "RMSE_pp": mean_squared_error(y,p)**0.5*100,
                "R2": r2_score(y,p) if len(y)>1 else np.nan,
                "PICP": covered.mean(),
                "MPIW_pp": np.mean(upper-lower)*100,
                "qhat_pp": qhat*100,
            })

uq = pd.DataFrame(uq_rows)
uq.to_csv(OUT / "03_uq_repeat_metrics.csv", index=False)

uq_agg = (
    uq.groupby(["target_chemistry","K_total_labeled_cells"])
    .agg(
        MAE_mean_pp=("MAE_pp","mean"),
        PICP_mean=("PICP","mean"),
        PICP_std=("PICP","std"),
        MPIW_mean_pp=("MPIW_pp","mean"),
        R2_mean=("R2","mean"),
        repeats=("repeat","nunique"),
    )
    .reset_index()
)
uq_agg.to_csv(OUT / "04_uq_aggregate.csv", index=False)


# =========================================================
# C. OOD WITHOUT STATE VARIABLES
# =========================================================

def build_cell_ood_features(df, ucols, relcols):
    rows = []
    for cid, g in df.groupby("_cell_id"):
        row = {
            "_cell_id": cid,
            "_chemistry": g["_chemistry"].iloc[0],
            "_group": g["_group"].iloc[0],
        }
        for c in ucols:
            row[f"RAW_MEAN_{c}"] = float(g[c].mean())
            row[f"RAW_STD_{c}"] = float(g[c].std(ddof=0))
        for c in relcols:
            row[f"REL_MEAN_{c}"] = float(g[c].mean())
            row[f"REL_STD_{c}"] = float(g[c].std(ddof=0))
        rows.append(row)
    return pd.DataFrame(rows)


class OODDetector:
    def __init__(self, kind, seed):
        self.kind = kind
        self.seed = seed
        self.imp = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        self.model = None

    def fit(self, X):
        X = self.imp.fit_transform(X)
        X = self.scaler.fit_transform(X)

        if self.kind == "Mahalanobis":
            self.model = LedoitWolf().fit(X)
        elif self.kind == "IsolationForest":
            self.model = IsolationForest(
                n_estimators=500, contamination="auto",
                random_state=self.seed, n_jobs=-1
            ).fit(X)
        elif self.kind == "KNN":
            self.model = NearestNeighbors(n_neighbors=min(5,len(X))).fit(X)
        return self

    def score(self, X):
        X = self.imp.transform(X)
        X = self.scaler.transform(X)

        if self.kind == "Mahalanobis":
            d = X - self.model.location_
            return np.einsum("ij,jk,ik->i", d, self.model.precision_, d)
        if self.kind == "IsolationForest":
            return -self.model.score_samples(X)
        if self.kind == "KNN":
            dist, _ = self.model.kneighbors(X)
            return dist.mean(axis=1)


def fpr95(y, s):
    fpr, tpr, _ = roc_curve(y,s)
    idx = np.where(tpr >= 0.95)[0]
    return float(fpr[idx[0]]) if len(idx) else np.nan


cell_ood = build_cell_ood_features(data, ucols, features)

ood_cols = [
    c for c in cell_ood.columns
    if c.startswith("RAW_") or c.startswith("REL_")
]

ood_rows = []

for target_chem in sorted(cell_ood["_chemistry"].unique()):
    src_all = cell_ood[cell_ood["_chemistry"] != target_chem].copy()
    tgt = cell_ood[cell_ood["_chemistry"] == target_chem].copy()
    src_ids_all = np.array(sorted(src_all["_cell_id"].unique()))

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED + rep)
        src_ids = src_ids_all.copy()
        rng.shuffle(src_ids)

        n_val = max(10, int(round(len(src_ids)*SOURCE_VAL_FRACTION)))
        val_ids = src_ids[:n_val]
        train_ids = src_ids[n_val:]

        tr = src_all[src_all["_cell_id"].isin(train_ids)]
        va = src_all[src_all["_cell_id"].isin(val_ids)]

        for kind in ["Mahalanobis","IsolationForest","KNN"]:
            det = OODDetector(kind, SEED+rep).fit(tr[ood_cols])
            s_src = det.score(va[ood_cols])
            s_tgt = det.score(tgt[ood_cols])

            y = np.concatenate([
                np.zeros(len(s_src),dtype=int),
                np.ones(len(s_tgt),dtype=int)
            ])
            s = np.concatenate([s_src,s_tgt])

            threshold = float(np.quantile(s_src, OOD_THRESHOLD_Q))
            accepted = s_tgt <= threshold

            ood_rows.append({
                "target_chemistry": target_chem,
                "repeat": rep,
                "detector": kind,
                "AUROC": roc_auc_score(y,s),
                "AUPRC": average_precision_score(y,s),
                "FPR95": fpr95(y,s),
                "acceptance_rate_target": accepted.mean(),
                "abstention_rate_target": (~accepted).mean(),
            })

ood = pd.DataFrame(ood_rows)
ood.to_csv(OUT / "05_ood_repeat_metrics.csv", index=False)

ood_agg = (
    ood.groupby(["target_chemistry","detector"])
    .agg(
        AUROC_mean=("AUROC","mean"),
        AUPRC_mean=("AUPRC","mean"),
        FPR95_mean=("FPR95","mean"),
        acceptance_rate_mean=("acceptance_rate_target","mean"),
        abstention_rate_mean=("abstention_rate_target","mean"),
        repeats=("repeat","nunique"),
    )
    .reset_index()
)
ood_agg.to_csv(OUT / "06_ood_aggregate.csv", index=False)


# =========================================================
# D. BIPOLAR709 OVERLAP-EXCLUDED EXTERNAL TRANSFER
# =========================================================

def parse_target_group(path):
    try:
        rel = path.relative_to(BIPOLAR_ROOT)
        return rel.parts[0] if len(rel.parts) > 1 else path.parent.name
    except Exception:
        return path.parent.name


def chemistry_from_text(s):
    s = str(s).upper()
    if "LFP" in s: return "LFP"
    if "LMO" in s: return "LMO"
    if "NMC" in s: return "NMC"
    return "UNKNOWN"


def load_bipolar():
    if BIPOLAR_CACHE.exists():
        return pd.read_csv(BIPOLAR_CACHE, low_memory=False)

    files = sorted(BIPOLAR_ROOT.rglob("*.xlsx"))
    rows = []

    for idx, f in enumerate(files,1):
        try:
            df = pd.read_excel(f, sheet_name=0).dropna(how="all")
            df.columns = [str(c).strip() for c in df.columns]
            if "ID" not in df.columns or "SOH" not in df.columns:
                continue

            group = parse_target_group(f)
            chem = chemistry_from_text(group + " " + f.name)

            df["_group"] = group
            df["_chemistry"] = chem
            df["_raw_id"] = df["ID"].astype(str).str.strip()
            df["_cell_id"] = group + "::" + df["_raw_id"]

            df["_SOH"] = numeric(df["SOH"])
            if df["_SOH"].dropna().median() > 2:
                df["_SOH"] /= 100.0

            present_u = find_ucols(df.columns)
            if len(present_u) < 21:
                continue

            for c in present_u:
                df[c] = numeric(df[c])

            keep = ["_group","_chemistry","_raw_id","_cell_id","_SOH"] + [f"U{k}" for k in range(1,22)]
            rows.append(df[keep])

            if idx % 100 == 0:
                print(f"External files parsed: {idx}/{len(files)}")

        except Exception:
            continue

    target = pd.concat(rows, ignore_index=True, sort=False)
    target.to_csv(BIPOLAR_CACHE, index=False)
    return target


target = load_bipolar()
target, _ = add_rel_ratio(target, ucols)

src_ids = set(data["_raw_id"].astype(str).unique())
target["_overlap"] = target["_raw_id"].astype(str).isin(src_ids)
target_clean = target[~target["_overlap"]].copy()

ext_rows = []

for chem in sorted(target_clean["_chemistry"].dropna().unique()):
    tgt = target_clean[target_clean["_chemistry"] == chem].copy()
    cells = np.array(sorted(tgt["_cell_id"].unique()))

    if len(cells) <= max(K_VALUES):
        continue

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED+rep)
        shuffled = cells.copy()
        rng.shuffle(shuffled)

        for K in K_VALUES:
            if K == 0:
                adapt_ids = np.array([],dtype=object)
                test_ids = shuffled
                imp, model = fit_et(data, features, SEED+rep)
            else:
                adapt_ids = shuffled[:K]
                test_ids = shuffled[K:]
                adapt = tgt[tgt["_cell_id"].isin(adapt_ids)]
                imp, model = fit_et(data, features, SEED+rep, adapt=adapt)

            test = tgt[tgt["_cell_id"].isin(test_ids)]
            pred = row_pred(imp, model, test, features)
            cell = cell_table(test,pred)

            ext_rows.append({
                "target_chemistry": chem,
                "repeat": rep,
                "K_cells": K,
                "test_cells": len(cell),
                **calc_metrics(cell)
            })

ext = pd.DataFrame(ext_rows)
ext.to_csv(OUT / "07_external_fewshot_repeat_metrics.csv", index=False)

ext_agg = (
    ext.groupby(["target_chemistry","K_cells"])
    .agg(
        MAE_mean_pp=("MAE_pp","mean"),
        MAE_std_pp=("MAE_pp","std"),
        RMSE_mean_pp=("RMSE_pp","mean"),
        R2_mean=("R2","mean"),
        Bias_mean_pp=("Bias_pp","mean"),
        repeats=("repeat","nunique"),
    )
    .reset_index()
)
ext_agg.to_csv(OUT / "08_external_fewshot_aggregate.csv", index=False)

overlap_summary = pd.DataFrame([{
    "source_unique_raw_ids": data["_raw_id"].nunique(),
    "target_unique_raw_ids": target["_raw_id"].nunique(),
    "overlapping_raw_ids": int(target[target["_overlap"]]["_raw_id"].nunique()),
    "target_cells_after_exclusion": target_clean["_cell_id"].nunique(),
    "target_rows_after_exclusion": len(target_clean),
}])
overlap_summary.to_csv(OUT / "09_external_overlap_summary.csv", index=False)


# =========================================================
# COMPACT FINAL FROZEN SUMMARY
# =========================================================

internal_summary = (
    few_agg.groupby("K_cells")
    .agg(mean_MAE_pp=("MAE_mean_pp","mean"))
    .reset_index()
)

uq_summary = (
    uq_agg.groupby("K_total_labeled_cells")
    .agg(
        mean_MAE_pp=("MAE_mean_pp","mean"),
        mean_PICP=("PICP_mean","mean"),
        mean_MPIW_pp=("MPIW_mean_pp","mean"),
    )
    .reset_index()
)

external_summary = (
    ext_agg.groupby("K_cells")
    .agg(mean_MAE_pp=("MAE_mean_pp","mean"))
    .reset_index()
)

internal_summary.to_csv(OUT / "10_internal_summary.csv", index=False)
uq_summary.to_csv(OUT / "11_uq_summary.csv", index=False)
external_summary.to_csv(OUT / "12_external_summary.csv", index=False)

# Figures
plt.figure(figsize=(7.2,5.0))
plt.plot(internal_summary["K_cells"], internal_summary["mean_MAE_pp"], marker="o")
plt.xlabel("Labeled target cells K")
plt.ylabel("Mean chemistry-level MAE (pp)")
plt.title("Frozen no-state internal few-shot")
plt.xticks(K_VALUES)
plt.tight_layout()
plt.savefig(OUT / "Fig01_Internal_NoState_FewShot.png", dpi=300)
plt.savefig(OUT / "Fig01_Internal_NoState_FewShot.pdf")
plt.close()

plt.figure(figsize=(7.2,5.0))
plt.plot(uq_summary["K_total_labeled_cells"], uq_summary["mean_PICP"]*100, marker="o")
plt.axhline(90, linestyle="--")
plt.xlabel("Total labeled target cells")
plt.ylabel("Mean empirical coverage (%)")
plt.title("Frozen no-state 90% conformal coverage")
plt.xticks(UQ_K_VALUES)
plt.tight_layout()
plt.savefig(OUT / "Fig02_NoState_Conformal_Coverage.png", dpi=300)
plt.savefig(OUT / "Fig02_NoState_Conformal_Coverage.pdf")
plt.close()

plt.figure(figsize=(7.2,5.0))
plt.plot(external_summary["K_cells"], external_summary["mean_MAE_pp"], marker="o")
plt.xlabel("Labeled external target cells K")
plt.ylabel("Mean external MAE (pp)")
plt.title("Frozen no-state external few-shot")
plt.xticks(K_VALUES)
plt.tight_layout()
plt.savefig(OUT / "Fig03_NoState_External_FewShot.png", dpi=300)
plt.savefig(OUT / "Fig03_NoState_External_FewShot.pdf")
plt.close()

run_summary = {
    "day": "Day14",
    "frozen_primary_representation": "REL_RATIO_NO_STATE",
    "definition": "(Ui-U1)/abs(U1), i=2..21",
    "state_variables_used_in_main_predictor": False,
    "reason": (
        "Day13 showed state inclusion changes aggregate MAE by <0.3%, while "
        "removing the SOCR/SOE ambiguity."
    ),
    "stages_replicated": [
        "internal chemistry few-shot",
        "90% conformal UQ",
        "OOD/abstention",
        "overlap-excluded Bipolar709 cross-dataset transfer"
    ],
    "important_note": (
        "This script is intended to freeze one state-free representation for the "
        "final manuscript pipeline."
    ),
    "output_dir": str(OUT),
}
(OUT / "13_run_summary.json").write_text(
    json.dumps(run_summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 14 COMPLETE ===")
print("\nFrozen no-state internal summary:")
print(internal_summary.to_string(index=False))
print("\nFrozen no-state UQ summary:")
print(uq_summary.to_string(index=False))
print("\nFrozen no-state OOD aggregate:")
print(ood_agg.to_string(index=False))
print("\nFrozen no-state external summary:")
print(external_summary.to_string(index=False))
print("\nOverlap summary:")
print(overlap_summary.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("02_internal_fewshot_aggregate.csv")
print("04_uq_aggregate.csv")
print("06_ood_aggregate.csv")
print("08_external_fewshot_aggregate.csv")
print("09_external_overlap_summary.csv")
print("10_internal_summary.csv")
print("11_uq_summary.csv")
print("12_external_summary.csv")
print("13_run_summary.json")
