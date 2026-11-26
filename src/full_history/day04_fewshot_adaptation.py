r"""
Day 04 — Cell-level few-shot adaptation on unseen PulseBat domains
================================================================

Purpose
-------
Use the Day03-selected physics-normalized REL_RATIO representation and test
whether a few labeled target-domain CELLS can recover SOH prediction accuracy
after domain shift.

Important:
K means number of labeled target BATTERIES/CELLS, not number of pulse rows.

K values:
0, 1, 5, 10, 20 target cells

Target-domain tests:
1. Leave-one-battery-group-out
2. Leave-one-chemistry-out

Adaptation methods:
- ZeroShot: source-only ExtraTrees model
- BiasCal: source model + mean residual correction from K target cells
- WeightedRetrain: re-fit ExtraTrees on source + K target cells with higher target weight

Features:
REL_RATIO_i = (Ui - U1) / |U1|, i = 2...21
+ canonical SOC

Results:
D:\SecondLife_Research\Result\Day04_FewShot
"""

from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

SEED = 42
REPEATS = 10
K_VALUES = [0, 1, 5, 10, 20]
TARGET_WEIGHT = 8.0
EPS = 1e-8

ROOT = Path(r"D:\SecondLife_Research")
PULSEBAT_ROOT = ROOT / "Data" / "PulseBat"
OUT = ROOT / "Result" / "Day04_FewShot"
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
            f"Expected 4 PulseBat processed files under {PULSEBAT_ROOT}; found {len(files)}."
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
        if id_col is None:
            raise ValueError(f"No ID field in {f.name}")

        soh_col = next(
            (c for c in df.columns if str(c).strip().lower() == "soh"),
            None
        )
        if soh_col is None:
            raise ValueError(f"No SOH field in {f.name}")

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

    features = ratio_cols + ["_SOC_CANONICAL"]
    return out, features


def make_model(seed):
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", ExtraTreesRegressor(
            n_estimators=800,
            min_samples_leaf=2,
            max_features=0.8,
            random_state=seed,
            n_jobs=-1,
        ))
    ])


def score(y_true, pred):
    y_true = np.asarray(y_true, dtype=float)
    pred = np.asarray(pred, dtype=float)
    err = pred - y_true
    return {
        "MAE_pp": mean_absolute_error(y_true, pred) * 100,
        "RMSE_pp": mean_squared_error(y_true, pred) ** 0.5 * 100,
        "R2": r2_score(y_true, pred) if len(y_true) > 1 else np.nan,
        "Bias_pp": np.mean(err) * 100,
    }


def weighted_fit_pipeline(X_source, y_source, X_adapt, y_adapt, features, seed):
    imputer = SimpleImputer(strategy="median")
    Xs = imputer.fit_transform(X_source[features])
    Xa = imputer.transform(X_adapt[features])

    X = np.vstack([Xs, Xa])
    y = np.concatenate([np.asarray(y_source), np.asarray(y_adapt)])

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


def run_domain_experiment(data, features, domain_col, experiment_name):
    rows = []
    pred_rows = []

    for target_domain in sorted(data[domain_col].unique()):
        source = data[data[domain_col] != target_domain].copy()
        target = data[data[domain_col] == target_domain].copy()

        target_cells = np.array(sorted(target["_cell_id"].unique()))
        if len(target_cells) <= max(K_VALUES):
            raise RuntimeError(
                f"{target_domain}: only {len(target_cells)} target cells; "
                f"need > {max(K_VALUES)} for disjoint K-shot testing."
            )

        # source model once per repeat to keep deterministic seed structure
        for rep in range(REPEATS):
            rng = np.random.default_rng(SEED + rep)
            shuffled = target_cells.copy()
            rng.shuffle(shuffled)

            source_model = make_model(SEED + rep)
            source_model.fit(source[features], source["_SOH"])

            for K in K_VALUES:
                if K == 0:
                    adapt_ids = np.array([], dtype=object)
                    test_ids = shuffled
                else:
                    adapt_ids = shuffled[:K]
                    test_ids = shuffled[K:]

                test = target[target["_cell_id"].isin(test_ids)].copy()
                y_test = test["_SOH"].to_numpy()

                # ---------------------------------------------------------
                # 1. ZeroShot source model
                # ---------------------------------------------------------
                zero_pred = source_model.predict(test[features])
                s = score(y_test, zero_pred)

                rows.append({
                    "experiment": experiment_name,
                    "target_domain": target_domain,
                    "K_cells": K,
                    "repeat": rep,
                    "method": "ZeroShot",
                    **s,
                    "source_cells": source["_cell_id"].nunique(),
                    "adapt_cells": K,
                    "test_cells": test["_cell_id"].nunique(),
                })

                q = test[["_cell_id", "_group", "_chemistry", "_SOC_CANONICAL", "_SOH"]].copy()
                q["experiment"] = experiment_name
                q["target_domain"] = target_domain
                q["K_cells"] = K
                q["repeat"] = rep
                q["method"] = "ZeroShot"
                q["pred_SOH"] = zero_pred
                pred_rows.append(q)

                if K == 0:
                    continue

                adapt = target[target["_cell_id"].isin(adapt_ids)].copy()

                # ---------------------------------------------------------
                # 2. BiasCal
                # Mean target residual estimated only from K labeled cells.
                # ---------------------------------------------------------
                adapt_pred = source_model.predict(adapt[features])
                correction = np.mean(adapt["_SOH"].to_numpy() - adapt_pred)
                bias_pred = zero_pred + correction
                bias_pred = np.clip(bias_pred, 0.0, 1.2)

                s = score(y_test, bias_pred)
                rows.append({
                    "experiment": experiment_name,
                    "target_domain": target_domain,
                    "K_cells": K,
                    "repeat": rep,
                    "method": "BiasCal",
                    **s,
                    "source_cells": source["_cell_id"].nunique(),
                    "adapt_cells": K,
                    "test_cells": test["_cell_id"].nunique(),
                })

                q = test[["_cell_id", "_group", "_chemistry", "_SOC_CANONICAL", "_SOH"]].copy()
                q["experiment"] = experiment_name
                q["target_domain"] = target_domain
                q["K_cells"] = K
                q["repeat"] = rep
                q["method"] = "BiasCal"
                q["pred_SOH"] = bias_pred
                pred_rows.append(q)

                # ---------------------------------------------------------
                # 3. WeightedRetrain
                # Source + K target cells, target rows receive larger weight.
                # ---------------------------------------------------------
                imputer, model = weighted_fit_pipeline(
                    source, source["_SOH"],
                    adapt, adapt["_SOH"],
                    features,
                    SEED + rep
                )
                Xt = imputer.transform(test[features])
                weighted_pred = model.predict(Xt)

                s = score(y_test, weighted_pred)
                rows.append({
                    "experiment": experiment_name,
                    "target_domain": target_domain,
                    "K_cells": K,
                    "repeat": rep,
                    "method": "WeightedRetrain",
                    **s,
                    "source_cells": source["_cell_id"].nunique(),
                    "adapt_cells": K,
                    "test_cells": test["_cell_id"].nunique(),
                })

                q = test[["_cell_id", "_group", "_chemistry", "_SOC_CANONICAL", "_SOH"]].copy()
                q["experiment"] = experiment_name
                q["target_domain"] = target_domain
                q["K_cells"] = K
                q["repeat"] = rep
                q["method"] = "WeightedRetrain"
                q["pred_SOH"] = weighted_pred
                pred_rows.append(q)

    return pd.DataFrame(rows), pd.concat(pred_rows, ignore_index=True)


data, ucols = load_data()
data, features = add_rel_ratio(data, ucols)
data = data[data["_SOH"].notna()].copy()

# Run group-level and chemistry-level few-shot studies
m_group, p_group = run_domain_experiment(
    data, features, "_group", "LeaveOneGroupOut"
)
m_chem, p_chem = run_domain_experiment(
    data, features, "_chemistry", "LeaveOneChemistryOut"
)

metrics = pd.concat([m_group, m_chem], ignore_index=True)
preds = pd.concat([p_group, p_chem], ignore_index=True)

metrics.to_csv(OUT / "02_fewshot_repeat_metrics.csv", index=False)
preds.to_csv(OUT / "03_fewshot_predictions.csv", index=False)

# Aggregate mean/std
agg = (
    metrics.groupby(["experiment", "target_domain", "K_cells", "method"])
    .agg(
        MAE_mean_pp=("MAE_pp", "mean"),
        MAE_std_pp=("MAE_pp", "std"),
        RMSE_mean_pp=("RMSE_pp", "mean"),
        RMSE_std_pp=("RMSE_pp", "std"),
        R2_mean=("R2", "mean"),
        R2_std=("R2", "std"),
        Bias_mean_pp=("Bias_pp", "mean"),
        Bias_std_pp=("Bias_pp", "std"),
        repeats=("repeat", "nunique"),
    )
    .reset_index()
)
agg.to_csv(OUT / "04_fewshot_aggregate_metrics.csv", index=False)

# Best adaptation method at each target/K, excluding ZeroShot for K>0
best_rows = []
for (exp, target, k), g in agg.groupby(["experiment", "target_domain", "K_cells"]):
    if k == 0:
        candidate = g[g["method"] == "ZeroShot"]
    else:
        candidate = g[g["method"].isin(["BiasCal", "WeightedRetrain"])]
    best_rows.append(candidate.sort_values("MAE_mean_pp").iloc[0])

best = pd.DataFrame(best_rows).reset_index(drop=True)
best.to_csv(OUT / "05_best_fewshot_method_by_domain_K.csv", index=False)

# Improvement over K=0 zero-shot baseline
improvement_rows = []
for (exp, target), g in agg.groupby(["experiment", "target_domain"]):
    base = g[(g["K_cells"] == 0) & (g["method"] == "ZeroShot")]
    if base.empty:
        continue
    base_mae = float(base.iloc[0]["MAE_mean_pp"])

    for _, row in g[g["K_cells"] > 0].iterrows():
        improvement_rows.append({
            "experiment": exp,
            "target_domain": target,
            "K_cells": int(row["K_cells"]),
            "method": row["method"],
            "zero_shot_MAE_pp": base_mae,
            "fewshot_MAE_pp": row["MAE_mean_pp"],
            "absolute_improvement_pp": base_mae - row["MAE_mean_pp"],
            "relative_improvement_percent":
                100 * (base_mae - row["MAE_mean_pp"]) / base_mae,
        })

improvement = pd.DataFrame(improvement_rows)
improvement.to_csv(OUT / "06_improvement_vs_zeroshot.csv", index=False)

# --------------------------------------------------------------
# Figures
# --------------------------------------------------------------

# Plot chemistry-level MAE curves
chem_agg = agg[agg["experiment"] == "LeaveOneChemistryOut"].copy()

for target in sorted(chem_agg["target_domain"].unique()):
    d = chem_agg[chem_agg["target_domain"] == target].copy()

    plt.figure(figsize=(7.5, 5.2))
    for method in ["ZeroShot", "BiasCal", "WeightedRetrain"]:
        q = d[d["method"] == method].sort_values("K_cells")
        if q.empty:
            continue
        plt.errorbar(
            q["K_cells"],
            q["MAE_mean_pp"],
            yerr=q["MAE_std_pp"].fillna(0),
            marker="o",
            capsize=3,
            label=method,
        )

    plt.xlabel("Number of labeled target cells (K)")
    plt.ylabel("SOH MAE (percentage points)")
    plt.title(f"Few-shot adaptation — held-out {target}")
    plt.xticks(K_VALUES)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / f"Fig01_FewShot_{target}_MAE.png", dpi=300)
    plt.savefig(OUT / f"Fig01_FewShot_{target}_MAE.pdf")
    plt.close()

# Overall chemistry-average curves
chem_avg = (
    chem_agg.groupby(["K_cells", "method"])
    .agg(
        MAE_mean_pp=("MAE_mean_pp", "mean"),
        MAE_std_across_domains=("MAE_mean_pp", "std"),
    )
    .reset_index()
)

plt.figure(figsize=(7.5, 5.2))
for method in ["ZeroShot", "BiasCal", "WeightedRetrain"]:
    q = chem_avg[chem_avg["method"] == method].sort_values("K_cells")
    if q.empty:
        continue
    plt.errorbar(
        q["K_cells"],
        q["MAE_mean_pp"],
        yerr=q["MAE_std_across_domains"].fillna(0),
        marker="o",
        capsize=3,
        label=method,
    )

plt.xlabel("Number of labeled target cells (K)")
plt.ylabel("Mean SOH MAE across held-out chemistries (pp)")
plt.title("Few-shot chemistry adaptation")
plt.xticks(K_VALUES)
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig02_ChemistryAverage_FewShot_MAE.png", dpi=300)
plt.savefig(OUT / "Fig02_ChemistryAverage_FewShot_MAE.pdf")
plt.close()

# Bias curves
plt.figure(figsize=(7.5, 5.2))
for method in ["ZeroShot", "BiasCal", "WeightedRetrain"]:
    q = chem_agg.groupby(["K_cells", "method"])["Bias_mean_pp"].mean().reset_index()
    q = q[q["method"] == method].sort_values("K_cells")
    if q.empty:
        continue
    plt.plot(q["K_cells"], q["Bias_mean_pp"], marker="o", label=method)

plt.axhline(0, linestyle="--", linewidth=1)
plt.xlabel("Number of labeled target cells (K)")
plt.ylabel("Mean prediction bias across chemistries (pp)")
plt.title("Few-shot bias correction")
plt.xticks(K_VALUES)
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig03_ChemistryAverage_Bias.png", dpi=300)
plt.savefig(OUT / "Fig03_ChemistryAverage_Bias.pdf")
plt.close()

summary = {
    "day": "Day04",
    "feature_representation": "REL_RATIO + canonical SOC",
    "feature_definition": "(Ui-U1)/abs(U1), i=2..21",
    "K_values_cells": K_VALUES,
    "repeats": REPEATS,
    "adaptation_methods": ["ZeroShot", "BiasCal", "WeightedRetrain"],
    "target_weight_for_weighted_retrain": TARGET_WEIGHT,
    "validation": ["LeaveOneGroupOut", "LeaveOneChemistryOut"],
    "important_note": (
        "K counts unique labeled target cells. Adaptation and test cells are disjoint "
        "within each repeat, preventing pulse-row leakage."
    ),
}
(OUT / "07_run_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 04 COMPLETE ===")
print("\nBest few-shot method by target and K:")
print(best.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("04_fewshot_aggregate_metrics.csv")
print("05_best_fewshot_method_by_domain_K.csv")
print("06_improvement_vs_zeroshot.csv")
print("07_run_summary.json")
