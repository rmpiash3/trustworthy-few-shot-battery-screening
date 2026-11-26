r"""
Day 05 — Cell-level conformal uncertainty calibration
=====================================================

Goal
----
Add calibrated uncertainty to the few-shot SOH framework.

Key design:
- Primary representation: REL_RATIO + canonical SOC
- Model: ExtraTrees
- Evaluation is CELL-LEVEL, not pulse-row-level
- 90% split-conformal prediction intervals
- Source-only conformal baseline (K=0)
- Target-aware few-shot conformal at K_total = 5, 10, 20 labeled target cells

For target-aware few-shot:
- labeled target cells are split into adaptation cells and calibration cells
- adaptation cells update the model
- calibration cells estimate conformal residual quantile
- evaluation cells are completely disjoint

Results:
D:\SecondLife_Research\Result\Day05_Uncertainty
"""

from pathlib import Path
import json
import re
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SEED = 42
REPEATS = 10
ALPHA = 0.10
TARGET_COVERAGE = 1.0 - ALPHA
K_TOTAL_VALUES = [0, 5, 10, 20]
TARGET_WEIGHT = 8.0
SOURCE_CAL_FRACTION = 0.20
EPS = 1e-8

ROOT = Path(r"D:\SecondLife_Research")
PULSEBAT_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day05_Uncertainty"
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
            f"Expected 4 processed PulseBat files under {PULSEBAT_ROOT}; "
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
    return out, ratio_cols + ["_SOC_CANONICAL"]


def fit_model(train_df, features, seed, adapt_df=None):
    imputer = SimpleImputer(strategy="median")
    Xs = imputer.fit_transform(train_df[features])
    ys = train_df["_SOH"].to_numpy()

    if adapt_df is None or len(adapt_df) == 0:
        X = Xs
        y = ys
        weights = np.ones(len(X), dtype=float)
    else:
        Xa = imputer.transform(adapt_df[features])
        ya = adapt_df["_SOH"].to_numpy()
        X = np.vstack([Xs, Xa])
        y = np.concatenate([ys, ya])
        weights = np.concatenate([
            np.ones(len(Xs), dtype=float),
            np.full(len(Xa), TARGET_WEIGHT, dtype=float)
        ])

    model = ExtraTreesRegressor(
        n_estimators=800,
        min_samples_leaf=2,
        max_features=0.8,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X, y, sample_weight=weights)
    return imputer, model


def predict_rows(imputer, model, df, features):
    return model.predict(imputer.transform(df[features]))


def cell_level_table(df, row_pred):
    temp = df[["_cell_id", "_group", "_chemistry", "_SOH"]].copy()
    temp["row_pred"] = row_pred

    # SOH should be cell-constant in this dataset. Median provides robustness.
    cell = (
        temp.groupby(["_cell_id", "_group", "_chemistry"], as_index=False)
        .agg(
            true_SOH=("_SOH", "median"),
            pred_SOH=("row_pred", "mean"),
            n_pulse_rows=("row_pred", "size"),
        )
    )
    cell["abs_error"] = np.abs(cell["pred_SOH"] - cell["true_SOH"])
    return cell


def conformal_qhat(abs_residuals, alpha=ALPHA):
    r = np.asarray(abs_residuals, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        raise ValueError("No calibration residuals.")

    # Standard finite-sample split-conformal quantile:
    # ceil((n+1)*(1-alpha))/n with 'higher' interpolation.
    n = len(r)
    level = min(1.0, math.ceil((n + 1) * (1 - alpha)) / n)
    try:
        return float(np.quantile(r, level, method="higher"))
    except TypeError:
        return float(np.quantile(r, level, interpolation="higher"))


def evaluate_interval(cell_df, qhat):
    y = cell_df["true_SOH"].to_numpy()
    p = cell_df["pred_SOH"].to_numpy()

    lower = p - qhat
    upper = p + qhat
    covered = (y >= lower) & (y <= upper)

    mae = mean_absolute_error(y, p) * 100
    rmse = mean_squared_error(y, p) ** 0.5 * 100
    r2 = r2_score(y, p) if len(y) > 1 else np.nan

    return {
        "MAE_pp": mae,
        "RMSE_pp": rmse,
        "R2": r2,
        "PICP": covered.mean(),
        "MPIW_pp": np.mean(upper - lower) * 100,
        "coverage_error_pp": (covered.mean() - TARGET_COVERAGE) * 100,
        "qhat_pp": qhat * 100,
    }, lower, upper, covered


data, ucols = load_data()
data, features = add_rel_ratio(data, ucols)
data = data[data["_SOH"].notna()].copy()

metric_rows = []
prediction_rows = []

for target_chem in sorted(data["_chemistry"].unique()):
    source_all = data[data["_chemistry"] != target_chem].copy()
    target_all = data[data["_chemistry"] == target_chem].copy()

    source_cells_all = np.array(sorted(source_all["_cell_id"].unique()))
    target_cells_all = np.array(sorted(target_all["_cell_id"].unique()))

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED + rep)

        # ----------------------------------------------------------
        # Source train/cal split by unique cell
        # ----------------------------------------------------------
        source_cells = source_cells_all.copy()
        rng.shuffle(source_cells)

        n_src_cal = max(10, int(round(len(source_cells) * SOURCE_CAL_FRACTION)))
        src_cal_ids = source_cells[:n_src_cal]
        src_train_ids = source_cells[n_src_cal:]

        src_train = source_all[source_all["_cell_id"].isin(src_train_ids)].copy()
        src_cal = source_all[source_all["_cell_id"].isin(src_cal_ids)].copy()

        # ----------------------------------------------------------
        # Target shuffle
        # ----------------------------------------------------------
        target_cells = target_cells_all.copy()
        rng.shuffle(target_cells)

        for K_total in K_TOTAL_VALUES:
            if K_total == 0:
                adapt_ids = np.array([], dtype=object)
                tgt_cal_ids = np.array([], dtype=object)
                test_ids = target_cells
                method = "SourceConformal"

                imputer, model = fit_model(
                    src_train, features, SEED + rep, adapt_df=None
                )

                src_cal_pred_rows = predict_rows(
                    imputer, model, src_cal, features
                )
                src_cal_cells = cell_level_table(src_cal, src_cal_pred_rows)
                qhat = conformal_qhat(src_cal_cells["abs_error"].to_numpy())

            else:
                if K_total >= len(target_cells):
                    continue

                labeled_ids = target_cells[:K_total]
                test_ids = target_cells[K_total:]

                # Split labeled target cells into model-adaptation and
                # uncertainty-calibration subsets.
                n_adapt = int(math.ceil(K_total / 2))
                n_cal = K_total - n_adapt

                if n_cal < 2:
                    continue

                adapt_ids = labeled_ids[:n_adapt]
                tgt_cal_ids = labeled_ids[n_adapt:]

                adapt = target_all[
                    target_all["_cell_id"].isin(adapt_ids)
                ].copy()
                tgt_cal = target_all[
                    target_all["_cell_id"].isin(tgt_cal_ids)
                ].copy()

                method = "TargetFewShotConformal"

                imputer, model = fit_model(
                    src_train,
                    features,
                    SEED + rep,
                    adapt_df=adapt
                )

                tgt_cal_pred_rows = predict_rows(
                    imputer, model, tgt_cal, features
                )
                tgt_cal_cells = cell_level_table(
                    tgt_cal, tgt_cal_pred_rows
                )
                qhat = conformal_qhat(
                    tgt_cal_cells["abs_error"].to_numpy()
                )

            test = target_all[target_all["_cell_id"].isin(test_ids)].copy()
            test_pred_rows = predict_rows(imputer, model, test, features)
            test_cells = cell_level_table(test, test_pred_rows)

            stats, lower, upper, covered = evaluate_interval(
                test_cells, qhat
            )

            metric_rows.append({
                "target_chemistry": target_chem,
                "repeat": rep,
                "K_total_labeled_cells": K_total,
                "K_adaptation_cells": len(adapt_ids),
                "K_calibration_cells": len(tgt_cal_ids),
                "method": method,
                "source_train_cells": len(src_train_ids),
                "source_cal_cells": len(src_cal_ids),
                "test_cells": len(test_ids),
                **stats,
            })

            pred_out = test_cells.copy()
            pred_out["target_chemistry"] = target_chem
            pred_out["repeat"] = rep
            pred_out["K_total_labeled_cells"] = K_total
            pred_out["K_adaptation_cells"] = len(adapt_ids)
            pred_out["K_calibration_cells"] = len(tgt_cal_ids)
            pred_out["method"] = method
            pred_out["lower_SOH"] = lower
            pred_out["upper_SOH"] = upper
            pred_out["covered"] = covered
            prediction_rows.append(pred_out)

metrics = pd.DataFrame(metric_rows)
predictions = pd.concat(prediction_rows, ignore_index=True)

metrics.to_csv(OUT / "02_uq_repeat_metrics.csv", index=False)
predictions.to_csv(OUT / "03_uq_cell_predictions.csv", index=False)

aggregate = (
    metrics.groupby([
        "target_chemistry",
        "K_total_labeled_cells",
        "method"
    ])
    .agg(
        MAE_mean_pp=("MAE_pp", "mean"),
        MAE_std_pp=("MAE_pp", "std"),
        PICP_mean=("PICP", "mean"),
        PICP_std=("PICP", "std"),
        MPIW_mean_pp=("MPIW_pp", "mean"),
        MPIW_std_pp=("MPIW_pp", "std"),
        coverage_error_mean_pp=("coverage_error_pp", "mean"),
        qhat_mean_pp=("qhat_pp", "mean"),
        R2_mean=("R2", "mean"),
        repeats=("repeat", "nunique"),
    )
    .reset_index()
)
aggregate.to_csv(OUT / "04_uq_aggregate_metrics.csv", index=False)

overall = (
    aggregate.groupby([
        "K_total_labeled_cells",
        "method"
    ])
    .agg(
        mean_MAE_pp=("MAE_mean_pp", "mean"),
        mean_PICP=("PICP_mean", "mean"),
        mean_MPIW_pp=("MPIW_mean_pp", "mean"),
        mean_abs_coverage_error_pp=(
            "coverage_error_mean_pp",
            lambda x: np.mean(np.abs(x))
        ),
        mean_R2=("R2_mean", "mean"),
    )
    .reset_index()
)
overall.to_csv(OUT / "05_uq_overall_summary.csv", index=False)

# ----------------------------------------------------------
# Figures
# ----------------------------------------------------------

# Coverage
plt.figure(figsize=(7.5, 5.2))
for chem in sorted(aggregate["target_chemistry"].unique()):
    d = aggregate[
        aggregate["target_chemistry"] == chem
    ].sort_values("K_total_labeled_cells")
    plt.plot(
        d["K_total_labeled_cells"],
        d["PICP_mean"] * 100,
        marker="o",
        label=chem
    )
plt.axhline(TARGET_COVERAGE * 100, linestyle="--", linewidth=1)
plt.xlabel("Total labeled target cells")
plt.ylabel("Empirical coverage PICP (%)")
plt.title("90% conformal interval coverage")
plt.xticks(K_TOTAL_VALUES)
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig01_Conformal_Coverage.png", dpi=300)
plt.savefig(OUT / "Fig01_Conformal_Coverage.pdf")
plt.close()

# Width
plt.figure(figsize=(7.5, 5.2))
for chem in sorted(aggregate["target_chemistry"].unique()):
    d = aggregate[
        aggregate["target_chemistry"] == chem
    ].sort_values("K_total_labeled_cells")
    plt.plot(
        d["K_total_labeled_cells"],
        d["MPIW_mean_pp"],
        marker="o",
        label=chem
    )
plt.xlabel("Total labeled target cells")
plt.ylabel("Mean prediction interval width (SOH pp)")
plt.title("Conformal interval sharpness")
plt.xticks(K_TOTAL_VALUES)
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig02_Conformal_Width.png", dpi=300)
plt.savefig(OUT / "Fig02_Conformal_Width.pdf")
plt.close()

# MAE
plt.figure(figsize=(7.5, 5.2))
for chem in sorted(aggregate["target_chemistry"].unique()):
    d = aggregate[
        aggregate["target_chemistry"] == chem
    ].sort_values("K_total_labeled_cells")
    plt.plot(
        d["K_total_labeled_cells"],
        d["MAE_mean_pp"],
        marker="o",
        label=chem
    )
plt.xlabel("Total labeled target cells")
plt.ylabel("Cell-level SOH MAE (pp)")
plt.title("Few-shot SOH accuracy with uncertainty calibration")
plt.xticks(K_TOTAL_VALUES)
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig03_CellLevel_MAE.png", dpi=300)
plt.savefig(OUT / "Fig03_CellLevel_MAE.pdf")
plt.close()

summary = {
    "day": "Day05",
    "feature_representation": "REL_RATIO + canonical SOC",
    "uncertainty_method": "90% split conformal prediction",
    "alpha": ALPHA,
    "target_coverage": TARGET_COVERAGE,
    "K_total_labeled_cells": K_TOTAL_VALUES,
    "repeats": REPEATS,
    "source_calibration_fraction": SOURCE_CAL_FRACTION,
    "target_weight": TARGET_WEIGHT,
    "evaluation_grain": "cell-level",
    "important_method_note": (
        "For K>0, labeled target cells are split into disjoint adaptation and "
        "conformal-calibration subsets; test cells are disjoint from both. "
        "For K=0, calibration residuals come from held-out source cells."
    )
}
(OUT / "06_run_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 05 COMPLETE ===")
print("\nOverall UQ summary:")
print(overall.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("04_uq_aggregate_metrics.csv")
print("05_uq_overall_summary.csv")
print("06_run_summary.json")
