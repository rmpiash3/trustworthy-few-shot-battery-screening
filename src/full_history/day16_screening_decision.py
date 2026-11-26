r"""
Day 16 — Conservative A/B/C/D screening decision layer
======================================================

Purpose
-------
Convert the frozen no-state predictor + target-aware conformal uncertainty into
an application-facing screening policy.

Primary representation
----------------------
REL_RATIO_NO_STATE = (Ui-U1)/abs(U1), i=2..21

Decision concept
----------------
Pre-adaptation:
    unseen chemistry detected as OOD -> Class C
    (additional diagnostic / target adaptation required)

Post-adaptation (K=20 total labeled target cells):
    use a target-aware 90% conformal interval.

Default configurable SOH bands:
    A: direct reuse          SOH >= 80%
    B: restricted reuse      70% <= SOH < 80%
    D: recycle               SOH < 70%
    C: additional diagnostic required

Conservative interval rule:
    lower >= 0.80                     -> A
    lower >= 0.70 and upper < 0.80   -> B
    upper < 0.70                      -> D
    otherwise                         -> C

Thus C is an uncertainty/ambiguity class, not an SOH ground-truth band.

Safety metric
-------------
False-safe event:
    true SOH < 70% but model assigns A or B.

Important
---------
The 80% / 70% thresholds are configurable engineering screening thresholds.
They are NOT claimed as universal regulatory standards.

Output
------
D:\SecondLife_Research\Result\Day16_ScreeningDecision
"""

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

SEED = 42
REPEATS = 10
K_TOTAL = 20
ALPHA = 0.10
SOURCE_CAL_FRACTION = 0.20
TARGET_WEIGHT = 8.0

DIRECT_REUSE_SOH = 0.80
RECYCLE_SOH = 0.70
EPS = 1e-12

ROOT = Path(r"D:\SecondLife_Research")
DATA_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day16_ScreeningDecision"
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
        raise FileNotFoundError(
            f"Expected 4 PulseBat files; found {len(files)}"
        )

    for f in files:
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(f, sheet_name=sheet).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]

        group, chem = infer_group(f)

        id_col = next(
            c for c in df.columns
            if str(c).strip().lower()
            in {"id","batteryid","battery_id","cellid","cell_id"}
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

    data = data[data["_SOH"].notna()].copy()
    return data, features


def fit_model(source_train, adapt, features, seed):
    imp = SimpleImputer(strategy="median")

    Xs = imp.fit_transform(source_train[features])
    ys = source_train["_SOH"].to_numpy()

    if adapt is not None and len(adapt) > 0:
        Xa = imp.transform(adapt[features])
        ya = adapt["_SOH"].to_numpy()

        X = np.vstack([Xs, Xa])
        y = np.concatenate([ys, ya])
        w = np.concatenate([
            np.ones(len(Xs)),
            np.full(len(Xa), TARGET_WEIGHT)
        ])
    else:
        X = Xs
        y = ys
        w = np.ones(len(Xs))

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
    t = df[["_cell_id","_chemistry","_group","_SOH"]].copy()
    t["pred"] = pred

    return (
        t.groupby(["_cell_id","_chemistry","_group"], as_index=False)
        .agg(
            true_SOH=("_SOH","median"),
            pred_SOH=("pred","mean"),
            pulse_rows=("pred","size"),
        )
    )


def conformal_qhat(residuals, alpha=ALPHA):
    r = np.asarray(residuals, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)

    if n == 0:
        raise ValueError("No calibration residuals.")

    level = min(
        1.0,
        math.ceil((n + 1) * (1 - alpha)) / n
    )

    try:
        return float(np.quantile(r, level, method="higher"))
    except TypeError:
        return float(np.quantile(r, level, interpolation="higher"))


def true_soh_band(y):
    if y >= DIRECT_REUSE_SOH:
        return "A_true_direct"
    if y >= RECYCLE_SOH:
        return "B_true_restricted"
    return "D_true_recycle"


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

    source_cells_all = np.array(
        sorted(source_all["_cell_id"].unique())
    )
    target_cells_all = np.array(
        sorted(target_all["_cell_id"].unique())
    )

    if len(target_cells_all) <= K_TOTAL:
        raise RuntimeError(
            f"{target_chem}: only {len(target_cells_all)} cells; "
            f"K_TOTAL={K_TOTAL}"
        )

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED + rep)

        # Source split: train vs calibration reserve
        source_cells = source_cells_all.copy()
        rng.shuffle(source_cells)

        n_source_cal = max(
            10,
            int(round(
                len(source_cells) * SOURCE_CAL_FRACTION
            ))
        )

        source_cal_ids = source_cells[:n_source_cal]
        source_train_ids = source_cells[n_source_cal:]

        source_train = source_all[
            source_all["_cell_id"].isin(source_train_ids)
        ].copy()

        # Target K=20 labeled cells:
        # half-ish adaptation, half calibration
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

        # Target-aware conformal calibration
        cal_pred = model.predict(
            imp.transform(cal[features])
        )
        cal_cell = predict_cell(cal, cal_pred)
        cal_res = np.abs(
            cal_cell["pred_SOH"] -
            cal_cell["true_SOH"]
        )
        qhat = conformal_qhat(cal_res)

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

        cell["true_band"] = cell["true_SOH"].apply(
            true_soh_band
        )

        cell["decision"] = [
            decision_from_interval(lo, hi)
            for lo, hi in zip(cell["lower"], cell["upper"])
        ]

        cell["false_safe"] = (
            (cell["true_SOH"] < RECYCLE_SOH) &
            (cell["decision"].isin(["A","B"]))
        )

        cell["direct_reuse_false_safe"] = (
            (cell["true_SOH"] < DIRECT_REUSE_SOH) &
            (cell["decision"] == "A")
        )

        cell["repeat"] = rep
        cell["qhat"] = qhat

        prediction_rows.append(cell)

        accepted = cell["decision"].isin(["A","B","D"])
        safe_reuse = cell["decision"].isin(["A","B"])

        repeat_rows.append({
            "target_chemistry": target_chem,
            "repeat": rep,
            "adapt_cells": len(adapt_ids),
            "calibration_cells": len(cal_ids),
            "test_cells": len(cell),
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
            "MPIW_pp": (2*qhat) * 100,
            "Class_A_rate": (cell["decision"] == "A").mean(),
            "Class_B_rate": (cell["decision"] == "B").mean(),
            "Class_C_rate": (cell["decision"] == "C").mean(),
            "Class_D_rate": (cell["decision"] == "D").mean(),
            "decisive_rate": accepted.mean(),
            "additional_diagnostic_rate":
                (cell["decision"] == "C").mean(),
            "reuse_assignment_rate": safe_reuse.mean(),
            "false_safe_rate_all":
                cell["false_safe"].mean(),
            "false_direct_reuse_rate_all":
                cell["direct_reuse_false_safe"].mean(),
            "false_safe_count":
                int(cell["false_safe"].sum()),
            "false_direct_reuse_count":
                int(cell["direct_reuse_false_safe"].sum()),
        })


predictions = pd.concat(
    prediction_rows,
    ignore_index=True
)

repeat_metrics = pd.DataFrame(repeat_rows)

predictions.to_csv(
    OUT / "01_cell_screening_predictions.csv",
    index=False
)

repeat_metrics.to_csv(
    OUT / "02_screening_repeat_metrics.csv",
    index=False
)


# Chemistry aggregate
aggregate = (
    repeat_metrics.groupby("target_chemistry")
    .agg(
        MAE_mean_pp=("MAE_pp","mean"),
        MAE_std_pp=("MAE_pp","std"),
        PICP_mean=("PICP","mean"),
        MPIW_mean_pp=("MPIW_pp","mean"),
        Class_A_rate_mean=("Class_A_rate","mean"),
        Class_B_rate_mean=("Class_B_rate","mean"),
        Class_C_rate_mean=("Class_C_rate","mean"),
        Class_D_rate_mean=("Class_D_rate","mean"),
        decisive_rate_mean=("decisive_rate","mean"),
        reuse_assignment_rate_mean=("reuse_assignment_rate","mean"),
        false_safe_rate_mean=("false_safe_rate_all","mean"),
        false_direct_reuse_rate_mean=("false_direct_reuse_rate_all","mean"),
        total_false_safe=("false_safe_count","sum"),
        total_false_direct_reuse=("false_direct_reuse_count","sum"),
        repeats=("repeat","nunique"),
    )
    .reset_index()
)

aggregate.to_csv(
    OUT / "03_screening_chemistry_aggregate.csv",
    index=False
)


# Overall repeat-level averaging over chemistries
overall_by_repeat = (
    repeat_metrics.groupby("repeat")
    .agg(
        MAE_pp=("MAE_pp","mean"),
        PICP=("PICP","mean"),
        MPIW_pp=("MPIW_pp","mean"),
        Class_A_rate=("Class_A_rate","mean"),
        Class_B_rate=("Class_B_rate","mean"),
        Class_C_rate=("Class_C_rate","mean"),
        Class_D_rate=("Class_D_rate","mean"),
        decisive_rate=("decisive_rate","mean"),
        reuse_assignment_rate=("reuse_assignment_rate","mean"),
        false_safe_rate=("false_safe_rate_all","mean"),
        false_direct_reuse_rate=("false_direct_reuse_rate_all","mean"),
        false_safe_count=("false_safe_count","sum"),
        false_direct_reuse_count=("false_direct_reuse_count","sum"),
    )
    .reset_index()
)

overall_summary = pd.DataFrame([{
    "repeats": len(overall_by_repeat),
    "MAE_mean_pp": overall_by_repeat["MAE_pp"].mean(),
    "PICP_mean": overall_by_repeat["PICP"].mean(),
    "MPIW_mean_pp": overall_by_repeat["MPIW_pp"].mean(),
    "Class_A_rate_mean": overall_by_repeat["Class_A_rate"].mean(),
    "Class_B_rate_mean": overall_by_repeat["Class_B_rate"].mean(),
    "Class_C_rate_mean": overall_by_repeat["Class_C_rate"].mean(),
    "Class_D_rate_mean": overall_by_repeat["Class_D_rate"].mean(),
    "decisive_rate_mean": overall_by_repeat["decisive_rate"].mean(),
    "reuse_assignment_rate_mean":
        overall_by_repeat["reuse_assignment_rate"].mean(),
    "false_safe_rate_mean":
        overall_by_repeat["false_safe_rate"].mean(),
    "false_direct_reuse_rate_mean":
        overall_by_repeat["false_direct_reuse_rate"].mean(),
    "total_false_safe_over_all_repeats":
        int(overall_by_repeat["false_safe_count"].sum()),
    "total_false_direct_reuse_over_all_repeats":
        int(overall_by_repeat["false_direct_reuse_count"].sum()),
}])

overall_summary.to_csv(
    OUT / "04_screening_overall_summary.csv",
    index=False
)


# Ground-truth vs decision counts
matrix = pd.crosstab(
    predictions["true_band"],
    predictions["decision"]
)

matrix.to_csv(
    OUT / "05_true_band_vs_decision_matrix.csv"
)


# Policy table for manuscript
policy = pd.DataFrame([
    {
        "condition": "Pre-adaptation OOD detected",
        "decision": "C",
        "meaning": "Additional diagnostic / target adaptation required"
    },
    {
        "condition": f"90% PI lower bound >= {DIRECT_REUSE_SOH:.2f}",
        "decision": "A",
        "meaning": "Direct reuse candidate"
    },
    {
        "condition": (
            f"90% PI fully inside "
            f"[{RECYCLE_SOH:.2f}, {DIRECT_REUSE_SOH:.2f})"
        ),
        "decision": "B",
        "meaning": "Restricted / lower-power reuse candidate"
    },
    {
        "condition": f"90% PI upper bound < {RECYCLE_SOH:.2f}",
        "decision": "D",
        "meaning": "Recycle candidate"
    },
    {
        "condition": "Prediction interval crosses a screening threshold",
        "decision": "C",
        "meaning": "Additional diagnostic required"
    },
])

policy.to_csv(
    OUT / "06_screening_policy_table.csv",
    index=False
)


# Figures
decision_order = ["A","B","C","D"]

decision_counts = (
    predictions["decision"]
    .value_counts()
    .reindex(decision_order, fill_value=0)
)

plt.figure(figsize=(7.0,5.0))
plt.bar(decision_order, decision_counts.values)
plt.xlabel("Screening decision")
plt.ylabel("Cell-decisions across repeats")
plt.title("Conservative uncertainty-aware screening decisions")
plt.tight_layout()
plt.savefig(
    OUT / "Fig01_Screening_Decision_Distribution.png",
    dpi=300
)
plt.savefig(
    OUT / "Fig01_Screening_Decision_Distribution.pdf"
)
plt.close()


chem = aggregate.copy()
plt.figure(figsize=(7.5,5.0))
x = np.arange(len(chem))
plt.bar(x, chem["Class_C_rate_mean"] * 100)
plt.xticks(x, chem["target_chemistry"])
plt.ylabel("Additional-diagnostic rate (%)")
plt.title("Class C rate after K20 target adaptation")
plt.tight_layout()
plt.savefig(
    OUT / "Fig02_ClassC_Rate_By_Chemistry.png",
    dpi=300
)
plt.savefig(
    OUT / "Fig02_ClassC_Rate_By_Chemistry.pdf"
)
plt.close()


plt.figure(figsize=(7.5,5.0))
x = np.arange(len(chem))
plt.bar(x, chem["false_safe_rate_mean"] * 100)
plt.xticks(x, chem["target_chemistry"])
plt.ylabel("False-safe rate (%)")
plt.title("False-safe reuse assignments")
plt.tight_layout()
plt.savefig(
    OUT / "Fig03_FalseSafe_Rate_By_Chemistry.png",
    dpi=300
)
plt.savefig(
    OUT / "Fig03_FalseSafe_Rate_By_Chemistry.pdf"
)
plt.close()


run_summary = {
    "day": "Day16",
    "representation": "REL_RATIO_NO_STATE",
    "adaptation": {
        "total_labeled_target_cells": K_TOTAL,
        "adaptation_cells": 10,
        "calibration_cells": 10,
    },
    "conformal_alpha": ALPHA,
    "screening_thresholds": {
        "direct_reuse_A": f"SOH >= {DIRECT_REUSE_SOH}",
        "restricted_reuse_B":
            f"{RECYCLE_SOH} <= SOH < {DIRECT_REUSE_SOH}",
        "recycle_D": f"SOH < {RECYCLE_SOH}",
        "additional_diagnostic_C":
            "OOD pre-adaptation or interval crosses a threshold",
    },
    "false_safe_definition":
        "true SOH < 0.70 but assigned A or B",
    "important_scope_note": (
        "The 80% and 70% SOH thresholds are configurable engineering "
        "screening assumptions, not universal regulatory standards. "
        "The experiment evaluates the safety behavior of the interval-based "
        "decision architecture under those assumed thresholds."
    ),
    "output_dir": str(OUT),
}

(OUT / "07_run_summary.json").write_text(
    json.dumps(run_summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 16 COMPLETE ===")

print("\nScreening chemistry aggregate:")
print(aggregate.to_string(index=False))

print("\nOverall screening summary:")
print(overall_summary.to_string(index=False))

print("\nTrue band vs decision matrix:")
print(matrix.to_string())

print(f"\nResults saved to:\n{OUT}")

print("\nSend me:")
print("03_screening_chemistry_aggregate.csv")
print("04_screening_overall_summary.csv")
print("05_true_band_vs_decision_matrix.csv")
print("06_screening_policy_table.csv")
print("07_run_summary.json")
