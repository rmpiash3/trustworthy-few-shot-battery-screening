r"""
Day 18 — Target calibration-size sensitivity and finite-sample conformal audit
=============================================================================

Purpose
-------
Day17 showed that nominal 90%, 95%, and 97.5% conformal intervals were
identical when only 10 target calibration cells were available.

This is a finite-sample quantile-resolution limitation:

    rank = ceil((n_cal + 1) * (1 - alpha))

With n_cal = 10:
- 90%  -> rank 10/10 = maximum residual
- 95%  -> rank capped at maximum residual
- 97.5% -> rank capped at maximum residual

Therefore Day18 keeps the final model representation and screening thresholds
fixed, uses nominal 90% coverage only, and studies whether increasing the
target calibration-set size changes interval stability and screening safety.

Configurations
--------------
A. 20 total labeled target cells:
   10 adaptation + 10 calibration

B. 30 total labeled target cells:
   10 adaptation + 20 calibration

C. 40 total labeled target cells:
   10 adaptation + 30 calibration

The adaptation set stays fixed at 10 cells.
Only calibration size increases.

Important scope
---------------
This is a sensitivity analysis, not deployment-policy tuning.
Increasing the number of labeled target cells changes the data burden and
reduces the remaining test cohort.

Output
------
D:\SecondLife_Research\Result\Day18_CalibrationSizeSensitivity
"""

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SEED = 42
REPEATS = 10
TARGET_WEIGHT = 8.0
ALPHA = 0.10
ADAPT_CELLS = 10
TOTAL_LABELED_CONFIGS = [20, 30, 40]

DIRECT_REUSE_SOH = 0.80
RECYCLE_SOH = 0.70
EPS = 1e-12

ROOT = Path(r"D:\SecondLife_Research")
DATA_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day18_CalibrationSizeSensitivity"
OUT.mkdir(parents=True, exist_ok=True)

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


def load_data():
    frames = []
    files = sorted(
        f for f in DATA_ROOT.rglob("*.xlsx")
        if f.name in EXPECTED
    )
    if len(files) != 4:
        raise FileNotFoundError(f"Expected 4 PulseBat files; found {len(files)}")

    for f in files:
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(f, sheet_name=sheet).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]

        group, chem = infer_group(f)

        id_col = next(
            c for c in df.columns
            if str(c).strip().lower()
            in {"id", "batteryid", "battery_id", "cellid", "cell_id"}
        )
        soh_col = next(
            c for c in df.columns
            if str(c).strip().lower() == "soh"
        )

        df["_group"] = group
        df["_chemistry"] = chem
        df["_cell_id"] = group + "::" + df[id_col].astype(str).str.strip()

        df["_SOH"] = numeric(df[soh_col])
        if df["_SOH"].dropna().median() > 2:
            df["_SOH"] /= 100.0

        for k in range(1, 22):
            c = f"U{k}"
            if c not in df.columns:
                raise ValueError(f"{f.name}: missing {c}")
            df[c] = numeric(df[c])

        frames.append(df)

    data = pd.concat(frames, ignore_index=True, sort=False)

    u1 = data["U1"].astype(float)
    features = []

    for k in range(2, 22):
        c = f"U{k}"
        name = f"RATIO_U{k}"
        data[name] = (data[c] - u1) / (u1.abs() + EPS)
        features.append(name)

    return data[data["_SOH"].notna()].copy(), features


def fit_model(source, adapt, features, seed):
    imp = SimpleImputer(strategy="median")

    Xs = imp.fit_transform(source[features])
    ys = source["_SOH"].to_numpy()

    Xa = imp.transform(adapt[features])
    ya = adapt["_SOH"].to_numpy()

    X = np.vstack([Xs, Xa])
    y = np.concatenate([ys, ya])
    w = np.concatenate([
        np.ones(len(Xs)),
        np.full(len(Xa), TARGET_WEIGHT),
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


def predict_cell(df, pred):
    t = df[["_cell_id", "_chemistry", "_group", "_SOH"]].copy()
    t["pred"] = pred

    return (
        t.groupby(["_cell_id", "_chemistry", "_group"], as_index=False)
        .agg(
            true_SOH=("_SOH", "median"),
            pred_SOH=("pred", "mean"),
            pulse_rows=("pred", "size"),
        )
    )


def conformal_rank(n_cal, alpha):
    raw_rank = math.ceil((n_cal + 1) * (1 - alpha))
    used_rank = min(n_cal, raw_rank)
    return raw_rank, used_rank


def conformal_qhat(residuals, alpha=ALPHA):
    r = np.sort(np.asarray(residuals, dtype=float))
    r = r[np.isfinite(r)]

    n = len(r)
    if n == 0:
        raise ValueError("No calibration residuals.")

    _, rank = conformal_rank(n, alpha)

    # rank is 1-indexed.
    return float(r[rank - 1])


def decision_from_interval(lower, upper):
    if lower >= DIRECT_REUSE_SOH:
        return "A"

    if lower >= RECYCLE_SOH and upper < DIRECT_REUSE_SOH:
        return "B"

    if upper < RECYCLE_SOH:
        return "D"

    return "C"


def min_n_for_nonmax(alpha, limit=10000):
    for n in range(1, limit + 1):
        raw_rank = math.ceil((n + 1) * (1 - alpha))
        if raw_rank < n:
            return n
    return None


data, features = load_data()

# Finite-sample rank audit.
rank_rows = []

for alpha in [0.10, 0.05, 0.025]:
    for n in [10, 20, 30, 40, 50]:
        raw_rank, used_rank = conformal_rank(n, alpha)
        rank_rows.append({
            "alpha": alpha,
            "nominal_coverage": 1 - alpha,
            "n_calibration": n,
            "raw_rank": raw_rank,
            "used_rank": used_rank,
            "uses_maximum_residual": used_rank == n,
            "minimum_n_for_nonmax_rank": min_n_for_nonmax(alpha),
        })

rank_audit = pd.DataFrame(rank_rows)
rank_audit.to_csv(
    OUT / "01_finite_sample_conformal_rank_audit.csv",
    index=False
)

prediction_rows = []
repeat_rows = []

for target_chem in sorted(data["_chemistry"].unique()):
    source = data[data["_chemistry"] != target_chem].copy()
    target = data[data["_chemistry"] == target_chem].copy()

    target_cells_all = np.array(sorted(target["_cell_id"].unique()))

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED + rep)

        shuffled = target_cells_all.copy()
        rng.shuffle(shuffled)

        # The first 10 labeled target cells are always the adaptation cells.
        adapt_ids = shuffled[:ADAPT_CELLS]

        adapt = target[
            target["_cell_id"].isin(adapt_ids)
        ].copy()

        imp, model = fit_model(
            source,
            adapt,
            features,
            SEED + rep
        )

        for total_labeled in TOTAL_LABELED_CONFIGS:
            if total_labeled >= len(shuffled):
                continue

            n_cal = total_labeled - ADAPT_CELLS

            cal_ids = shuffled[
                ADAPT_CELLS:total_labeled
            ]
            test_ids = shuffled[total_labeled:]

            cal = target[
                target["_cell_id"].isin(cal_ids)
            ].copy()

            test = target[
                target["_cell_id"].isin(test_ids)
            ].copy()

            cal_pred = model.predict(
                imp.transform(cal[features])
            )
            cal_cell = predict_cell(cal, cal_pred)

            cal_res = np.abs(
                cal_cell["pred_SOH"] -
                cal_cell["true_SOH"]
            )

            qhat = conformal_qhat(cal_res, ALPHA)
            raw_rank, used_rank = conformal_rank(len(cal_cell), ALPHA)

            test_pred = model.predict(
                imp.transform(test[features])
            )
            cell = predict_cell(test, test_pred)

            cell["lower"] = cell["pred_SOH"] - qhat
            cell["upper"] = cell["pred_SOH"] + qhat
            cell["covered"] = (
                (cell["true_SOH"] >= cell["lower"]) &
                (cell["true_SOH"] <= cell["upper"])
            )
            cell["decision"] = [
                decision_from_interval(lo, hi)
                for lo, hi in zip(cell["lower"], cell["upper"])
            ]
            cell["false_safe"] = (
                (cell["true_SOH"] < RECYCLE_SOH) &
                (cell["decision"].isin(["A", "B"]))
            )
            cell["false_direct_reuse"] = (
                (cell["true_SOH"] < DIRECT_REUSE_SOH) &
                (cell["decision"] == "A")
            )

            cell["target_chemistry"] = target_chem
            cell["repeat"] = rep
            cell["total_labeled_cells"] = total_labeled
            cell["adaptation_cells"] = ADAPT_CELLS
            cell["calibration_cells"] = len(cal_cell)
            cell["qhat"] = qhat

            prediction_rows.append(cell)

            repeat_rows.append({
                "target_chemistry": target_chem,
                "repeat": rep,
                "total_labeled_cells": total_labeled,
                "adaptation_cells": ADAPT_CELLS,
                "calibration_cells": len(cal_cell),
                "test_cells": len(cell),
                "raw_conformal_rank": raw_rank,
                "used_conformal_rank": used_rank,
                "uses_maximum_residual": used_rank == len(cal_cell),
                "qhat_pp": qhat * 100,
                "MAE_pp": mean_absolute_error(
                    cell["true_SOH"],
                    cell["pred_SOH"]
                ) * 100,
                "RMSE_pp": mean_squared_error(
                    cell["true_SOH"],
                    cell["pred_SOH"]
                ) ** 0.5 * 100,
                "R2": r2_score(
                    cell["true_SOH"],
                    cell["pred_SOH"]
                ) if len(cell) > 1 else np.nan,
                "PICP": cell["covered"].mean(),
                "MPIW_pp": 2 * qhat * 100,
                "Class_A_rate": (cell["decision"] == "A").mean(),
                "Class_B_rate": (cell["decision"] == "B").mean(),
                "Class_C_rate": (cell["decision"] == "C").mean(),
                "Class_D_rate": (cell["decision"] == "D").mean(),
                "decisive_rate":
                    cell["decision"].isin(["A", "B", "D"]).mean(),
                "reuse_assignment_rate":
                    cell["decision"].isin(["A", "B"]).mean(),
                "false_safe_rate":
                    cell["false_safe"].mean(),
                "false_direct_reuse_rate":
                    cell["false_direct_reuse"].mean(),
                "false_safe_count":
                    int(cell["false_safe"].sum()),
                "false_direct_reuse_count":
                    int(cell["false_direct_reuse"].sum()),
            })

predictions = pd.concat(prediction_rows, ignore_index=True)
repeat_metrics = pd.DataFrame(repeat_rows)

predictions.to_csv(
    OUT / "02_cell_calibration_size_predictions.csv",
    index=False
)

repeat_metrics.to_csv(
    OUT / "03_calibration_size_repeat_metrics.csv",
    index=False
)

chem_agg = (
    repeat_metrics.groupby(
        [
            "target_chemistry",
            "total_labeled_cells",
            "adaptation_cells",
            "calibration_cells",
        ]
    )
    .agg(
        qhat_mean_pp=("qhat_pp", "mean"),
        qhat_std_pp=("qhat_pp", "std"),
        PICP_mean=("PICP", "mean"),
        PICP_std=("PICP", "std"),
        MPIW_mean_pp=("MPIW_pp", "mean"),
        decisive_rate_mean=("decisive_rate", "mean"),
        Class_C_rate_mean=("Class_C_rate", "mean"),
        reuse_assignment_rate_mean=("reuse_assignment_rate", "mean"),
        false_safe_rate_mean=("false_safe_rate", "mean"),
        false_direct_reuse_rate_mean=("false_direct_reuse_rate", "mean"),
        total_false_safe=("false_safe_count", "sum"),
        total_false_direct_reuse=("false_direct_reuse_count", "sum"),
        mean_test_cells=("test_cells", "mean"),
        repeats=("repeat", "nunique"),
    )
    .reset_index()
)

chem_agg.to_csv(
    OUT / "04_calibration_size_chemistry_aggregate.csv",
    index=False
)

overall_by_repeat = (
    repeat_metrics.groupby(
        ["repeat", "total_labeled_cells", "adaptation_cells", "calibration_cells"]
    )
    .agg(
        qhat_pp=("qhat_pp", "mean"),
        PICP=("PICP", "mean"),
        MPIW_pp=("MPIW_pp", "mean"),
        decisive_rate=("decisive_rate", "mean"),
        Class_C_rate=("Class_C_rate", "mean"),
        reuse_assignment_rate=("reuse_assignment_rate", "mean"),
        false_safe_rate=("false_safe_rate", "mean"),
        false_direct_reuse_rate=("false_direct_reuse_rate", "mean"),
        false_safe_count=("false_safe_count", "sum"),
        false_direct_reuse_count=("false_direct_reuse_count", "sum"),
    )
    .reset_index()
)

overall = (
    overall_by_repeat.groupby(
        ["total_labeled_cells", "adaptation_cells", "calibration_cells"]
    )
    .agg(
        qhat_mean_pp=("qhat_pp", "mean"),
        qhat_std_pp=("qhat_pp", "std"),
        PICP_mean=("PICP", "mean"),
        PICP_std=("PICP", "std"),
        MPIW_mean_pp=("MPIW_pp", "mean"),
        decisive_rate_mean=("decisive_rate", "mean"),
        Class_C_rate_mean=("Class_C_rate", "mean"),
        reuse_assignment_rate_mean=("reuse_assignment_rate", "mean"),
        false_safe_rate_mean=("false_safe_rate", "mean"),
        false_direct_reuse_rate_mean=("false_direct_reuse_rate", "mean"),
        total_false_safe=("false_safe_count", "sum"),
        total_false_direct_reuse=("false_direct_reuse_count", "sum"),
        repeats=("repeat", "nunique"),
    )
    .reset_index()
)

overall.to_csv(
    OUT / "05_calibration_size_overall.csv",
    index=False
)

# NMC repeat 3 forensic comparison.
nmc_rep3 = repeat_metrics[
    (repeat_metrics["target_chemistry"] == "NMC") &
    (repeat_metrics["repeat"] == 3)
].copy()

nmc_rep3.to_csv(
    OUT / "06_nmc_repeat3_calibration_size.csv",
    index=False
)

false_safe_details = predictions[
    predictions["false_safe"] == True
].copy()

false_safe_details.to_csv(
    OUT / "07_false_safe_cell_details.csv",
    index=False
)

# Figures
plt.figure(figsize=(7.2, 5.0))
plt.errorbar(
    overall["calibration_cells"],
    overall["qhat_mean_pp"],
    yerr=overall["qhat_std_pp"],
    marker="o",
    capsize=4
)
plt.xlabel("Target calibration cells")
plt.ylabel("Mean conformal half-width qhat (pp)")
plt.title("Calibration-size effect on interval half-width")
plt.tight_layout()
plt.savefig(OUT / "Fig01_Qhat_vs_CalibrationSize.png", dpi=300)
plt.savefig(OUT / "Fig01_Qhat_vs_CalibrationSize.pdf")
plt.close()

plt.figure(figsize=(7.2, 5.0))
plt.plot(
    overall["calibration_cells"],
    overall["PICP_mean"] * 100,
    marker="o"
)
plt.axhline(90, linestyle="--")
plt.xlabel("Target calibration cells")
plt.ylabel("Empirical coverage (%)")
plt.title("Coverage vs target calibration size")
plt.tight_layout()
plt.savefig(OUT / "Fig02_PICP_vs_CalibrationSize.png", dpi=300)
plt.savefig(OUT / "Fig02_PICP_vs_CalibrationSize.pdf")
plt.close()

plt.figure(figsize=(7.2, 5.0))
plt.plot(
    overall["calibration_cells"],
    overall["false_safe_rate_mean"] * 100,
    marker="o",
    label="False-safe"
)
plt.plot(
    overall["calibration_cells"],
    overall["decisive_rate_mean"] * 100,
    marker="o",
    label="Decisive A/B/D"
)
plt.xlabel("Target calibration cells")
plt.ylabel("Rate (%)")
plt.title("Safety–decisiveness vs calibration size")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig03_Safety_Decisiveness_vs_CalibrationSize.png", dpi=300)
plt.savefig(OUT / "Fig03_Safety_Decisiveness_vs_CalibrationSize.pdf")
plt.close()

run_summary = {
    "day": "Day18",
    "representation": "REL_RATIO_NO_STATE",
    "nominal_coverage": 0.90,
    "adaptation_cells_fixed": ADAPT_CELLS,
    "total_labeled_configs": TOTAL_LABELED_CONFIGS,
    "calibration_sizes": [
        x - ADAPT_CELLS for x in TOTAL_LABELED_CONFIGS
    ],
    "finite_sample_note": (
        "Day17's 90/95/97.5% intervals were identical because n_cal=10 "
        "forces all those split-conformal quantiles to the maximum calibration residual."
    ),
    "purpose": (
        "Quantify interval stability, empirical coverage, false-safe rate, and "
        "decisiveness as the target calibration set grows while keeping the "
        "adaptation set fixed at 10 cells."
    ),
    "scope_note": (
        "This is a sensitivity analysis. Larger calibration sets increase label burden "
        "and reduce the remaining test cohort; results must not be used as deployment "
        "policy selection without independent validation."
    ),
    "output_dir": str(OUT),
}

(OUT / "08_run_summary.json").write_text(
    json.dumps(run_summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 18 COMPLETE ===")

print("\nFinite-sample conformal rank audit:")
print(rank_audit.to_string(index=False))

print("\nOverall calibration-size sensitivity:")
print(overall.to_string(index=False))

print("\nNMC repeat-3 calibration-size sensitivity:")
print(nmc_rep3.to_string(index=False))

print(f"\nResults saved to:\n{OUT}")

print("\nSend me:")
print("01_finite_sample_conformal_rank_audit.csv")
print("04_calibration_size_chemistry_aggregate.csv")
print("05_calibration_size_overall.csv")
print("06_nmc_repeat3_calibration_size.csv")
print("07_false_safe_cell_details.csv")
print("08_run_summary.json")
