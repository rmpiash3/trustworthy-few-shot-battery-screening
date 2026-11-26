r"""
Day 17 — Screening safety / conformal-level sensitivity audit
=============================================================

Purpose
-------
Day16 showed a conservative A/B/C/D screening policy with low overall
false-safe rate, but 7 false-safe events occurred, all in 2.1Ah NMC and all
in repeat 3.

This stage does NOT tune a deployment policy on the test labels.

Instead it performs a pre-declared sensitivity analysis over conformal
miscoverage levels:

    alpha = 0.10   -> nominal 90% PI
    alpha = 0.05   -> nominal 95% PI
    alpha = 0.025  -> nominal 97.5% PI

The same frozen representation, model, adaptation protocol, target split,
and screening thresholds are used throughout.

Primary representation
----------------------
REL_RATIO_NO_STATE = (Ui-U1)/abs(U1), i=2..21

Adaptation design
-----------------
K_total = 20 target labeled cells:
- 10 adaptation cells
- 10 calibration cells

Screening thresholds
--------------------
A: direct reuse          SOH >= 0.80
B: restricted reuse      0.70 <= SOH < 0.80
D: recycle               SOH < 0.70
C: additional diagnostic required

Decision rule
-------------
A if interval lower bound >= 0.80
B if interval fully inside [0.70, 0.80)
D if interval upper bound < 0.70
C otherwise

Safety metric
-------------
False-safe:
true SOH < 0.70 but assigned A or B.

Important scope
---------------
This is a sensitivity / safety audit.
Do NOT select a final deployment coverage level solely because it performs
best on these same evaluation cells.

Output
------
D:\SecondLife_Research\Result\Day17_ScreeningSafetySensitivity
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
K_TOTAL = 20
TARGET_WEIGHT = 8.0
SOURCE_CAL_FRACTION = 0.20
ALPHAS = [0.10, 0.05, 0.025]

DIRECT_REUSE_SOH = 0.80
RECYCLE_SOH = 0.70
EPS = 1e-12

ROOT = Path(r"D:\SecondLife_Research")
DATA_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day17_ScreeningSafetySensitivity"
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


def fit_model(source_train, adapt, features, seed):
    imp = SimpleImputer(strategy="median")
    Xs = imp.fit_transform(source_train[features])
    ys = source_train["_SOH"].to_numpy()

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


def conformal_qhat(residuals, alpha):
    r = np.asarray(residuals, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n == 0:
        raise ValueError("No calibration residuals.")

    level = min(1.0, math.ceil((n + 1) * (1 - alpha)) / n)
    try:
        return float(np.quantile(r, level, method="higher"))
    except TypeError:
        return float(np.quantile(r, level, interpolation="higher"))


def decision_from_interval(lower, upper):
    if lower >= DIRECT_REUSE_SOH:
        return "A"
    if lower >= RECYCLE_SOH and upper < DIRECT_REUSE_SOH:
        return "B"
    if upper < RECYCLE_SOH:
        return "D"
    return "C"


data, features = load_data()

prediction_rows = []
repeat_rows = []

for target_chem in sorted(data["_chemistry"].unique()):
    source_all = data[data["_chemistry"] != target_chem].copy()
    target_all = data[data["_chemistry"] == target_chem].copy()

    source_cells_all = np.array(sorted(source_all["_cell_id"].unique()))
    target_cells_all = np.array(sorted(target_all["_cell_id"].unique()))

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED + rep)

        source_cells = source_cells_all.copy()
        rng.shuffle(source_cells)

        n_source_cal = max(
            10,
            int(round(len(source_cells) * SOURCE_CAL_FRACTION))
        )
        source_train_ids = source_cells[n_source_cal:]

        source_train = source_all[
            source_all["_cell_id"].isin(source_train_ids)
        ].copy()

        target_cells = target_cells_all.copy()
        rng.shuffle(target_cells)

        labeled_ids = target_cells[:K_TOTAL]
        test_ids = target_cells[K_TOTAL:]

        n_adapt = int(math.ceil(K_TOTAL / 2))
        adapt_ids = labeled_ids[:n_adapt]
        cal_ids = labeled_ids[n_adapt:]

        adapt = target_all[
            target_all["_cell_id"].isin(adapt_ids)
        ].copy()
        cal = target_all[
            target_all["_cell_id"].isin(cal_ids)
        ].copy()
        test = target_all[
            target_all["_cell_id"].isin(test_ids)
        ].copy()

        imp, model = fit_model(
            source_train,
            adapt,
            features,
            SEED + rep
        )

        cal_pred = model.predict(imp.transform(cal[features]))
        cal_cell = predict_cell(cal, cal_pred)
        cal_res = np.abs(cal_cell["pred_SOH"] - cal_cell["true_SOH"])

        test_pred = model.predict(imp.transform(test[features]))
        base_cell = predict_cell(test, test_pred)

        for alpha in ALPHAS:
            nominal_coverage = 1.0 - alpha
            qhat = conformal_qhat(cal_res, alpha)

            cell = base_cell.copy()
            cell["alpha"] = alpha
            cell["nominal_coverage"] = nominal_coverage
            cell["qhat"] = qhat
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
            cell["repeat"] = rep
            prediction_rows.append(cell)

            repeat_rows.append({
                "target_chemistry": target_chem,
                "repeat": rep,
                "alpha": alpha,
                "nominal_coverage": nominal_coverage,
                "adapt_cells": len(adapt_ids),
                "calibration_cells": len(cal_ids),
                "test_cells": len(cell),
                "qhat_pp": qhat * 100,
                "MAE_pp": mean_absolute_error(
                    cell["true_SOH"], cell["pred_SOH"]
                ) * 100,
                "RMSE_pp": mean_squared_error(
                    cell["true_SOH"], cell["pred_SOH"]
                ) ** 0.5 * 100,
                "R2": r2_score(
                    cell["true_SOH"], cell["pred_SOH"]
                ) if len(cell) > 1 else np.nan,
                "PICP": cell["covered"].mean(),
                "MPIW_pp": 2 * qhat * 100,
                "Class_A_rate": (cell["decision"] == "A").mean(),
                "Class_B_rate": (cell["decision"] == "B").mean(),
                "Class_C_rate": (cell["decision"] == "C").mean(),
                "Class_D_rate": (cell["decision"] == "D").mean(),
                "decisive_rate": cell["decision"].isin(["A", "B", "D"]).mean(),
                "reuse_assignment_rate":
                    cell["decision"].isin(["A", "B"]).mean(),
                "false_safe_rate": cell["false_safe"].mean(),
                "false_direct_reuse_rate":
                    cell["false_direct_reuse"].mean(),
                "false_safe_count": int(cell["false_safe"].sum()),
                "false_direct_reuse_count":
                    int(cell["false_direct_reuse"].sum()),
            })

predictions = pd.concat(prediction_rows, ignore_index=True)
repeat_metrics = pd.DataFrame(repeat_rows)

predictions.to_csv(
    OUT / "01_cell_policy_sensitivity_predictions.csv",
    index=False
)
repeat_metrics.to_csv(
    OUT / "02_policy_sensitivity_repeat_metrics.csv",
    index=False
)

chem_agg = (
    repeat_metrics.groupby(["target_chemistry", "alpha", "nominal_coverage"])
    .agg(
        PICP_mean=("PICP", "mean"),
        PICP_std=("PICP", "std"),
        MPIW_mean_pp=("MPIW_pp", "mean"),
        Class_A_rate_mean=("Class_A_rate", "mean"),
        Class_B_rate_mean=("Class_B_rate", "mean"),
        Class_C_rate_mean=("Class_C_rate", "mean"),
        Class_D_rate_mean=("Class_D_rate", "mean"),
        decisive_rate_mean=("decisive_rate", "mean"),
        reuse_assignment_rate_mean=("reuse_assignment_rate", "mean"),
        false_safe_rate_mean=("false_safe_rate", "mean"),
        false_direct_reuse_rate_mean=("false_direct_reuse_rate", "mean"),
        total_false_safe=("false_safe_count", "sum"),
        total_false_direct_reuse=("false_direct_reuse_count", "sum"),
        qhat_mean_pp=("qhat_pp", "mean"),
        repeats=("repeat", "nunique"),
    )
    .reset_index()
)
chem_agg.to_csv(
    OUT / "03_policy_sensitivity_chemistry.csv",
    index=False
)

overall_by_repeat = (
    repeat_metrics.groupby(["repeat", "alpha", "nominal_coverage"])
    .agg(
        PICP=("PICP", "mean"),
        MPIW_pp=("MPIW_pp", "mean"),
        Class_A_rate=("Class_A_rate", "mean"),
        Class_B_rate=("Class_B_rate", "mean"),
        Class_C_rate=("Class_C_rate", "mean"),
        Class_D_rate=("Class_D_rate", "mean"),
        decisive_rate=("decisive_rate", "mean"),
        reuse_assignment_rate=("reuse_assignment_rate", "mean"),
        false_safe_rate=("false_safe_rate", "mean"),
        false_direct_reuse_rate=("false_direct_reuse_rate", "mean"),
        false_safe_count=("false_safe_count", "sum"),
        false_direct_reuse_count=("false_direct_reuse_count", "sum"),
        qhat_pp=("qhat_pp", "mean"),
    )
    .reset_index()
)

overall = (
    overall_by_repeat.groupby(["alpha", "nominal_coverage"])
    .agg(
        PICP_mean=("PICP", "mean"),
        MPIW_mean_pp=("MPIW_pp", "mean"),
        Class_A_rate_mean=("Class_A_rate", "mean"),
        Class_B_rate_mean=("Class_B_rate", "mean"),
        Class_C_rate_mean=("Class_C_rate", "mean"),
        Class_D_rate_mean=("Class_D_rate", "mean"),
        decisive_rate_mean=("decisive_rate", "mean"),
        reuse_assignment_rate_mean=("reuse_assignment_rate", "mean"),
        false_safe_rate_mean=("false_safe_rate", "mean"),
        false_direct_reuse_rate_mean=("false_direct_reuse_rate", "mean"),
        total_false_safe=("false_safe_count", "sum"),
        total_false_direct_reuse=("false_direct_reuse_count", "sum"),
        qhat_mean_pp=("qhat_pp", "mean"),
        repeats=("repeat", "nunique"),
    )
    .reset_index()
)
overall.to_csv(
    OUT / "04_policy_sensitivity_overall.csv",
    index=False
)

# Isolate the original problematic repeat 3 / NMC behavior.
problem = repeat_metrics[
    (repeat_metrics["target_chemistry"] == "NMC") &
    (repeat_metrics["repeat"] == 3)
].copy()
problem.to_csv(
    OUT / "05_nmc_repeat3_sensitivity.csv",
    index=False
)

# False-safe cell details by coverage level.
false_safe_details = predictions[
    predictions["false_safe"] == True
].copy()
false_safe_details.to_csv(
    OUT / "06_false_safe_cell_details.csv",
    index=False
)

# Policy comparison table.
policy_table = overall[
    [
        "nominal_coverage",
        "PICP_mean",
        "MPIW_mean_pp",
        "decisive_rate_mean",
        "Class_C_rate_mean",
        "reuse_assignment_rate_mean",
        "false_safe_rate_mean",
        "total_false_safe",
        "false_direct_reuse_rate_mean",
        "total_false_direct_reuse",
    ]
].copy()
policy_table.to_csv(
    OUT / "07_policy_tradeoff_table.csv",
    index=False
)

# Figures.
plt.figure(figsize=(7.2, 5.0))
plt.plot(
    overall["nominal_coverage"] * 100,
    overall["false_safe_rate_mean"] * 100,
    marker="o"
)
plt.xlabel("Nominal conformal coverage (%)")
plt.ylabel("False-safe rate (%)")
plt.title("Safety sensitivity to conformal coverage")
plt.tight_layout()
plt.savefig(OUT / "Fig01_FalseSafe_vs_Coverage.png", dpi=300)
plt.savefig(OUT / "Fig01_FalseSafe_vs_Coverage.pdf")
plt.close()

plt.figure(figsize=(7.2, 5.0))
plt.plot(
    overall["nominal_coverage"] * 100,
    overall["decisive_rate_mean"] * 100,
    marker="o"
)
plt.xlabel("Nominal conformal coverage (%)")
plt.ylabel("Decisive A/B/D rate (%)")
plt.title("Decisiveness–coverage trade-off")
plt.tight_layout()
plt.savefig(OUT / "Fig02_DecisiveRate_vs_Coverage.png", dpi=300)
plt.savefig(OUT / "Fig02_DecisiveRate_vs_Coverage.pdf")
plt.close()

plt.figure(figsize=(7.2, 5.0))
plt.plot(
    overall["nominal_coverage"] * 100,
    overall["MPIW_mean_pp"],
    marker="o"
)
plt.xlabel("Nominal conformal coverage (%)")
plt.ylabel("Mean prediction interval width (pp)")
plt.title("Interval-width cost of additional conservatism")
plt.tight_layout()
plt.savefig(OUT / "Fig03_MPIW_vs_Coverage.png", dpi=300)
plt.savefig(OUT / "Fig03_MPIW_vs_Coverage.pdf")
plt.close()

run_summary = {
    "day": "Day17",
    "representation": "REL_RATIO_NO_STATE",
    "coverage_levels": [0.90, 0.95, 0.975],
    "adaptation": {
        "total_target_labeled_cells": 20,
        "adaptation_cells": 10,
        "calibration_cells": 10,
    },
    "screening_thresholds": {
        "A": "SOH >= 0.80",
        "B": "0.70 <= SOH < 0.80",
        "D": "SOH < 0.70",
        "C": "interval crosses a threshold",
    },
    "purpose": (
        "Sensitivity audit of false-safe versus decisiveness across conformal "
        "coverage levels after Day16 identified rare over-confident NMC decisions."
    ),
    "important_scope_note": (
        "This stage must not be used to tune/select a deployment coverage level "
        "on the same evaluation labels. It is a sensitivity analysis. Final "
        "deployment policy requires prespecification and independent validation."
    ),
    "output_dir": str(OUT),
}

(OUT / "08_run_summary.json").write_text(
    json.dumps(run_summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 17 COMPLETE ===")

print("\nOverall policy sensitivity:")
print(overall.to_string(index=False))

print("\nNMC repeat-3 sensitivity:")
print(problem.to_string(index=False))

print("\nFalse-safe cell rows by coverage level:")
print(false_safe_details[
    [
        "_cell_id", "_chemistry", "true_SOH", "pred_SOH",
        "lower", "upper", "decision", "repeat",
        "nominal_coverage", "qhat"
    ]
].to_string(index=False) if not false_safe_details.empty
else "None")

print(f"\nResults saved to:\n{OUT}")

print("\nSend me:")
print("03_policy_sensitivity_chemistry.csv")
print("04_policy_sensitivity_overall.csv")
print("05_nmc_repeat3_sensitivity.csv")
print("06_false_safe_cell_details.csv")
print("07_policy_tradeoff_table.csv")
print("08_run_summary.json")
