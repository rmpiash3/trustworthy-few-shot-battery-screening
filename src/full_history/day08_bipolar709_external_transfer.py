r"""
Day 08 — Bipolar709 external harmonization + overlap-safe transfer validation
============================================================================

Purpose
-------
Use PulseBat as the source domain and Bipolar709 Step2_CellLevel as an external
target domain, while explicitly auditing source-target cell-ID overlap.

Critical rule
-------------
Any target cell ID that overlaps with PulseBat source IDs is EXCLUDED from
external evaluation. This prevents false "external validation" claims.

Source:
D:\SecondLife_Research\Data\PulseBat

Target:
D:\SecondLife_Research\Data\Bipolar709\Data_Process_Output\Step2_CellLevel

Outputs:
D:\SecondLife_Research\Result\Day08_Bipolar709_ExternalTransfer

Primary representation:
REL_RATIO_i = (Ui-U1)/abs(U1), i = 2..common_U
+ canonical SOC

Evaluation:
1. Zero-shot source -> external target
2. Cell-level few-shot target adaptation K={1,5,10,20}, 10 repeats
3. Chemistry-wise metrics
4. overlap audit
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
K_VALUES = [0, 1, 5, 10, 20]
TARGET_WEIGHT = 8.0
EPS = 1e-8

ROOT = Path(r"D:\SecondLife_Research")
SOURCE_ROOT = ROOT / "Data" / "PulseBat"
TARGET_ROOT = (
    ROOT / "Data" / "Bipolar709" / "Data_Process_Output" / "Step2_CellLevel"
)
OUT = ROOT / "Result" / "Day08_Bipolar709_ExternalTransfer"
OUT.mkdir(parents=True, exist_ok=True)

CACHE = OUT / "Bipolar709_harmonized_cache.csv"

SOURCE_EXPECTED = {
    "NMC_2.1Ah_W_5000.xlsx",
    "LMO_10Ah_W_5000.xlsx",
    "NMC_21Ah_W_5000.xlsx",
    "LFP_35Ah_W_5000.xlsx",
}


def numeric(s):
    return pd.to_numeric(s, errors="coerce")


def norm_soc(s):
    s = numeric(s)
    v = s.dropna()
    if v.empty:
        return s
    return s / 100.0 if v.quantile(0.95) > 1.5 else s


def chemistry_from_text(text):
    s = str(text).upper()
    if "NMC" in s:
        return "NMC"
    if "LMO" in s:
        return "LMO"
    if "LFP" in s:
        return "LFP"
    return "UNKNOWN"


def infer_source_group(f):
    n = f.name.upper()
    if "2.1AH" in n and "NMC" in n:
        return "2.1Ah NMC"
    if "10AH" in n and "LMO" in n:
        return "10Ah LMO"
    if "21AH" in n and "NMC" in n:
        return "21Ah NMC"
    if "35AH" in n and "LFP" in n:
        return "35Ah LFP"
    return f.parent.name


def find_u_cols(columns):
    pairs = []
    for c in columns:
        m = re.fullmatch(r"U(\d+)", str(c).strip(), flags=re.I)
        if m:
            pairs.append((int(m.group(1)), str(c).strip()))
    return [c for _, c in sorted(pairs)]


def load_source():
    files = sorted(
        f for f in SOURCE_ROOT.rglob("*.xlsx")
        if f.name in SOURCE_EXPECTED
    )
    if len(files) != 4:
        raise FileNotFoundError(
            f"Expected 4 PulseBat source files; found {len(files)}."
        )

    frames = []
    for f in files:
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(f, sheet_name=sheet).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]

        id_col = next(
            c for c in df.columns
            if str(c).strip().lower() in {"id","batteryid","battery_id","cellid","cell_id"}
        )
        soh_col = next(c for c in df.columns if str(c).strip().lower() == "soh")

        group = infer_source_group(f)
        chem = chemistry_from_text(group)

        df["_source_dataset"] = "PulseBat"
        df["_group"] = group
        df["_chemistry"] = chem
        df["_raw_id"] = df[id_col].astype(str).str.strip()
        df["_cell_id"] = group + "::" + df["_raw_id"]

        df["_SOH"] = numeric(df[soh_col])
        if df["_SOH"].dropna().median() > 2:
            df["_SOH"] /= 100.0

        if "SOCR" in df.columns and numeric(df["SOCR"]).notna().any():
            df["_SOC_CANONICAL"] = norm_soc(df["SOCR"])
        elif "SOE" in df.columns and numeric(df["SOE"]).notna().any():
            df["_SOC_CANONICAL"] = norm_soc(df["SOE"])
        elif "SOC" in df.columns and numeric(df["SOC"]).notna().any():
            df["_SOC_CANONICAL"] = norm_soc(df["SOC"])
        else:
            df["_SOC_CANONICAL"] = np.nan

        for c in find_u_cols(df.columns):
            df[c] = numeric(df[c])

        frames.append(df)

    return pd.concat(frames, ignore_index=True, sort=False)


def parse_target_group_from_path(path):
    # first child directory under Step2_CellLevel normally encodes chemistry/capacity
    try:
        rel = path.relative_to(TARGET_ROOT)
        if len(rel.parts) > 1:
            return rel.parts[0]
    except Exception:
        pass
    return path.parent.name


def build_target_cache():
    files = sorted(TARGET_ROOT.rglob("*.xlsx"))
    if not files:
        raise FileNotFoundError(
            f"No Bipolar709 Step2 .xlsx files found under:\n{TARGET_ROOT}"
        )

    rows = []
    failed = []

    for i, f in enumerate(files, 1):
        try:
            xl = pd.ExcelFile(f)
            sheet = xl.sheet_names[0]
            df = pd.read_excel(f, sheet_name=sheet).dropna(how="all")
            df.columns = [str(c).strip() for c in df.columns]

            required = {"ID", "SOH"}
            if not required.issubset(df.columns):
                failed.append((str(f), "missing ID/SOH"))
                continue

            group = parse_target_group_from_path(f)
            chem = chemistry_from_text(group + " " + f.name)

            df["_source_dataset"] = "Bipolar709"
            df["_group"] = group
            df["_chemistry"] = chem
            df["_raw_id"] = df["ID"].astype(str).str.strip()
            df["_cell_id"] = group + "::" + df["_raw_id"]
            df["_source_file"] = str(f)

            df["_SOH"] = numeric(df["SOH"])
            if df["_SOH"].dropna().median() > 2:
                df["_SOH"] /= 100.0

            if "SOCR" in df.columns and numeric(df["SOCR"]).notna().any():
                df["_SOC_CANONICAL"] = norm_soc(df["SOCR"])
            elif "SOC" in df.columns and numeric(df["SOC"]).notna().any():
                df["_SOC_CANONICAL"] = norm_soc(df["SOC"])
            else:
                df["_SOC_CANONICAL"] = np.nan

            for c in find_u_cols(df.columns):
                df[c] = numeric(df[c])

            # Keep only columns needed downstream
            keep = [
                "_source_dataset","_group","_chemistry","_raw_id","_cell_id",
                "_source_file","_SOH","_SOC_CANONICAL"
            ] + find_u_cols(df.columns)
            rows.append(df[keep].copy())

            if i % 100 == 0:
                print(f"Read target files: {i}/{len(files)}")

        except Exception as e:
            failed.append((str(f), f"{type(e).__name__}: {e}"))

    if not rows:
        raise RuntimeError("No usable Bipolar709 Step2 files were parsed.")

    target = pd.concat(rows, ignore_index=True, sort=False)
    target.to_csv(CACHE, index=False)

    pd.DataFrame(failed, columns=["file","error"]).to_csv(
        OUT / "01_target_read_failures.csv", index=False
    )
    return target


def load_target():
    if CACHE.exists():
        print(f"Using cache: {CACHE}")
        return pd.read_csv(CACHE, low_memory=False)
    return build_target_cache()


def add_rel_ratio(df, ucols):
    out = df.copy()
    u1 = numeric(out[ucols[0]])
    features = []
    for c in ucols[1:]:
        name = f"RATIO_{c}"
        out[name] = (numeric(out[c]) - u1) / (u1.abs() + EPS)
        features.append(name)
    return out, features + ["_SOC_CANONICAL"]


def fit_source_model(source, features, seed):
    imp = SimpleImputer(strategy="median")
    X = imp.fit_transform(source[features])
    y = source["_SOH"].to_numpy()

    model = ExtraTreesRegressor(
        n_estimators=800,
        min_samples_leaf=2,
        max_features=0.8,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X, y)
    return imp, model


def weighted_retrain(source, adapt, features, seed):
    imp = SimpleImputer(strategy="median")
    Xs = imp.fit_transform(source[features])
    Xa = imp.transform(adapt[features])

    X = np.vstack([Xs, Xa])
    y = np.concatenate([source["_SOH"].to_numpy(), adapt["_SOH"].to_numpy()])
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


def predict_cell_level(df, pred):
    t = df[["_cell_id","_chemistry","_group","_SOH"]].copy()
    t["pred"] = pred
    return (
        t.groupby(["_cell_id","_chemistry","_group"], as_index=False)
        .agg(
            true_SOH=("_SOH","median"),
            pred_SOH=("pred","mean"),
            pulse_rows=("pred","size")
        )
    )


def metrics_from_cell(cell):
    return {
        "MAE_pp": mean_absolute_error(cell["true_SOH"], cell["pred_SOH"]) * 100,
        "RMSE_pp": mean_squared_error(cell["true_SOH"], cell["pred_SOH"]) ** 0.5 * 100,
        "R2": r2_score(cell["true_SOH"], cell["pred_SOH"]) if len(cell) > 1 else np.nan,
        "Bias_pp": np.mean(cell["pred_SOH"] - cell["true_SOH"]) * 100,
    }


source = load_source()
target = load_target()

source_u = find_u_cols(source.columns)
target_u = find_u_cols(target.columns)
common_u = sorted(
    set(source_u).intersection(target_u),
    key=lambda c: int(re.findall(r"\d+", c)[0])
)

if len(common_u) < 10:
    raise RuntimeError(
        f"Only {len(common_u)} common U features between source and target: {common_u}"
    )

# Keep common raw features and create REL_RATIO representation
source, features = add_rel_ratio(source, common_u)
target, _ = add_rel_ratio(target, common_u)

# ----------------------------------------------------------
# OVERLAP AUDIT
# ----------------------------------------------------------
source_raw_ids = set(source["_raw_id"].dropna().astype(str).str.strip().unique())
target_raw_ids = set(target["_raw_id"].dropna().astype(str).str.strip().unique())
overlap_raw_ids = sorted(source_raw_ids.intersection(target_raw_ids))

overlap_df = pd.DataFrame({"overlapping_raw_id": overlap_raw_ids})
overlap_df.to_csv(OUT / "02_source_target_overlap_ids.csv", index=False)

# Exclude ALL target rows whose raw ID appears in source
target["_overlap_with_source"] = target["_raw_id"].astype(str).isin(source_raw_ids)
target_clean = target[~target["_overlap_with_source"]].copy()

overlap_summary = pd.DataFrame([{
    "source_unique_raw_ids": len(source_raw_ids),
    "target_unique_raw_ids_before_exclusion": len(target_raw_ids),
    "overlapping_raw_ids": len(overlap_raw_ids),
    "target_unique_cells_before_exclusion": target["_cell_id"].nunique(),
    "target_unique_cells_after_exclusion": target_clean["_cell_id"].nunique(),
    "target_rows_before_exclusion": len(target),
    "target_rows_after_exclusion": len(target_clean),
    "common_u_feature_count": len(common_u),
    "common_u_first": common_u[0],
    "common_u_last": common_u[-1],
}]
)
overlap_summary.to_csv(OUT / "03_overlap_summary.csv", index=False)

if target_clean["_cell_id"].nunique() < 20:
    raise RuntimeError(
        "Too few non-overlapping Bipolar709 target cells remain for external validation."
    )

# ----------------------------------------------------------
# ZERO-SHOT EXTERNAL VALIDATION
# ----------------------------------------------------------
imp0, model0 = fit_source_model(source, features, SEED)
pred0 = model0.predict(imp0.transform(target_clean[features]))
cell0 = predict_cell_level(target_clean, pred0)

zero_rows = []
for chem, g in cell0.groupby("_chemistry"):
    zero_rows.append({
        "chemistry": chem,
        "cells": len(g),
        **metrics_from_cell(g)
    })
zero_rows.append({
    "chemistry": "ALL",
    "cells": len(cell0),
    **metrics_from_cell(cell0)
})
zero = pd.DataFrame(zero_rows)
zero.to_csv(OUT / "04_external_zeroshot_metrics.csv", index=False)

# ----------------------------------------------------------
# FEW-SHOT EXTERNAL VALIDATION — chemistry-stratified
# K cells TOTAL within each target chemistry
# ----------------------------------------------------------
fewshot_rows = []

for chem in sorted(target_clean["_chemistry"].dropna().unique()):
    target_chem = target_clean[target_clean["_chemistry"] == chem].copy()
    cells = np.array(sorted(target_chem["_cell_id"].unique()))

    if len(cells) <= max(K_VALUES):
        print(f"Skipping few-shot for {chem}: only {len(cells)} cells")
        continue

    for rep in range(REPEATS):
        rng = np.random.default_rng(SEED + rep)
        shuffled = cells.copy()
        rng.shuffle(shuffled)

        for K in K_VALUES:
            if K == 0:
                adapt_ids = np.array([], dtype=object)
                test_ids = shuffled
                imp, model = fit_source_model(source, features, SEED + rep)
            else:
                adapt_ids = shuffled[:K]
                test_ids = shuffled[K:]
                adapt = target_chem[target_chem["_cell_id"].isin(adapt_ids)].copy()
                imp, model = weighted_retrain(
                    source, adapt, features, SEED + rep
                )

            test = target_chem[target_chem["_cell_id"].isin(test_ids)].copy()
            pred = model.predict(imp.transform(test[features]))
            cell = predict_cell_level(test, pred)
            m = metrics_from_cell(cell)

            fewshot_rows.append({
                "chemistry": chem,
                "repeat": rep,
                "K_cells": K,
                "adapt_cells": len(adapt_ids),
                "test_cells": len(cell),
                **m
            })

fewshot = pd.DataFrame(fewshot_rows)
fewshot.to_csv(OUT / "05_external_fewshot_repeat_metrics.csv", index=False)

if not fewshot.empty:
    agg = (
        fewshot.groupby(["chemistry","K_cells"])
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
else:
    agg = pd.DataFrame()

agg.to_csv(OUT / "06_external_fewshot_aggregate.csv", index=False)

# ----------------------------------------------------------
# Target chemistry/group summary
# ----------------------------------------------------------
target_summary = (
    target_clean.groupby(["_chemistry","_group"])
    .agg(
        rows=("_SOH","size"),
        cells=("_cell_id","nunique"),
        soh_mean=("_SOH","mean"),
        soh_min=("_SOH","min"),
        soh_max=("_SOH","max"),
        soc_min=("_SOC_CANONICAL","min"),
        soc_max=("_SOC_CANONICAL","max"),
    )
    .reset_index()
)
target_summary.to_csv(OUT / "07_external_target_summary.csv", index=False)

# Figure: zero-shot chemistry MAE
z = zero[zero["chemistry"] != "ALL"].copy()
plt.figure(figsize=(7.2,5.0))
x = np.arange(len(z))
plt.bar(x, z["MAE_pp"])
plt.xticks(x, z["chemistry"])
plt.ylabel("External zero-shot SOH MAE (pp)")
plt.title("PulseBat -> Bipolar709 external transfer")
plt.tight_layout()
plt.savefig(OUT / "Fig01_External_ZeroShot_MAE.png", dpi=300)
plt.savefig(OUT / "Fig01_External_ZeroShot_MAE.pdf")
plt.close()

# Figure: few-shot curves
if not agg.empty:
    plt.figure(figsize=(7.8,5.3))
    for chem in sorted(agg["chemistry"].unique()):
        d = agg[agg["chemistry"] == chem].sort_values("K_cells")
        plt.errorbar(
            d["K_cells"], d["MAE_mean_pp"],
            yerr=d["MAE_std_pp"].fillna(0),
            marker="o", capsize=3, label=chem
        )
    plt.xlabel("Labeled external target cells (K)")
    plt.ylabel("SOH MAE (pp)")
    plt.title("External few-shot adaptation: Bipolar709")
    plt.xticks(K_VALUES)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "Fig02_External_FewShot_MAE.png", dpi=300)
    plt.savefig(OUT / "Fig02_External_FewShot_MAE.pdf")
    plt.close()

summary = {
    "day": "Day08",
    "source_dataset": "PulseBat",
    "target_dataset": "Bipolar709 Step2_CellLevel",
    "source_root": str(SOURCE_ROOT),
    "target_root": str(TARGET_ROOT),
    "overlap_exclusion_rule": "Any target raw ID appearing in PulseBat source is excluded.",
    "common_u_features": common_u,
    "common_u_feature_count": len(common_u),
    "feature_representation": "REL_RATIO + canonical SOC",
    "fewshot_K_cells": K_VALUES,
    "repeats": REPEATS,
    "important_note": (
        "This is only a valid external transfer result for the non-overlapping target cells. "
        "If overlap is substantial or protocols are strongly related, manuscript wording must "
        "use cross-dataset validation rather than fully independent external validation."
    )
}
(OUT / "08_run_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 08 COMPLETE ===")
print("\nOverlap summary:")
print(overlap_summary.to_string(index=False))
print("\nExternal zero-shot metrics:")
print(zero.to_string(index=False))
if not agg.empty:
    print("\nExternal few-shot aggregate:")
    print(agg.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("03_overlap_summary.csv")
print("04_external_zeroshot_metrics.csv")
print("06_external_fewshot_aggregate.csv")
print("07_external_target_summary.csv")
print("08_run_summary.json")
