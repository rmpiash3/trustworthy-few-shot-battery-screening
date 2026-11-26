r"""
Day 15 — Final statistical robustness and manuscript-table freeze
================================================================

Purpose
-------
Use the frozen Day14 no-state pipeline outputs to create:
1. paired statistical comparisons of K=0 vs K=20,
2. bootstrap confidence intervals,
3. chemistry-wise effect sizes,
4. calibration summaries,
5. OOD summary,
6. a compact manuscript-ready master table.

This stage does NOT retrain models. It analyzes the already-frozen Day14 results.

Expected input folder:
D:\SecondLife_Research\Result\Day14_Frozen_NoState_Pipeline

Output:
D:\SecondLife_Research\Result\Day15_FinalStatistics
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import wilcoxon

SEED = 42
N_BOOT = 10000

ROOT = Path(r"D:\SecondLife_Research")
DAY14 = ROOT / "Result" / "Day14_Frozen_NoState_Pipeline"
OUT = ROOT / "Result" / "Day15_FinalStatistics"
OUT.mkdir(parents=True, exist_ok=True)

REQ = {
    "internal_repeat": DAY14 / "01_internal_fewshot_repeat_metrics.csv",
    "internal_agg": DAY14 / "02_internal_fewshot_aggregate.csv",
    "uq_repeat": DAY14 / "03_uq_repeat_metrics.csv",
    "uq_agg": DAY14 / "04_uq_aggregate.csv",
    "ood_agg": DAY14 / "06_ood_aggregate.csv",
    "external_repeat": DAY14 / "07_external_fewshot_repeat_metrics.csv",
    "external_agg": DAY14 / "08_external_fewshot_aggregate.csv",
    "overlap": DAY14 / "09_external_overlap_summary.csv",
    "internal_summary": DAY14 / "10_internal_summary.csv",
    "uq_summary": DAY14 / "11_uq_summary.csv",
    "external_summary": DAY14 / "12_external_summary.csv",
}

missing = [str(p) for p in REQ.values() if not p.exists()]
if missing:
    raise FileNotFoundError(
        "Missing Day14 output(s):\n" + "\n".join(missing)
    )

internal = pd.read_csv(REQ["internal_repeat"])
internal_agg = pd.read_csv(REQ["internal_agg"])
uq = pd.read_csv(REQ["uq_repeat"])
uq_agg = pd.read_csv(REQ["uq_agg"])
ood = pd.read_csv(REQ["ood_agg"])
external = pd.read_csv(REQ["external_repeat"])
external_agg = pd.read_csv(REQ["external_agg"])
overlap = pd.read_csv(REQ["overlap"])
internal_summary = pd.read_csv(REQ["internal_summary"])
uq_summary = pd.read_csv(REQ["uq_summary"])
external_summary = pd.read_csv(REQ["external_summary"])


def bootstrap_mean_ci(values, n_boot=N_BOOT, seed=SEED, alpha=0.05):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return np.nan, np.nan, np.nan

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    means = x[idx].mean(axis=1)
    return (
        float(x.mean()),
        float(np.quantile(means, alpha/2)),
        float(np.quantile(means, 1-alpha/2)),
    )


def paired_k0_k20_stats(df, dataset_label):
    rows = []

    for chem in sorted(df["target_chemistry"].unique()):
        d = df[df["target_chemistry"] == chem].copy()

        a = (
            d[d["K_cells"] == 0][["repeat","MAE_pp"]]
            .rename(columns={"MAE_pp":"MAE_K0"})
        )
        b = (
            d[d["K_cells"] == 20][["repeat","MAE_pp"]]
            .rename(columns={"MAE_pp":"MAE_K20"})
        )
        p = a.merge(b, on="repeat", how="inner")
        p["delta_pp"] = p["MAE_K20"] - p["MAE_K0"]
        p["improvement_pp"] = p["MAE_K0"] - p["MAE_K20"]
        p["improvement_percent"] = (
            p["improvement_pp"] / p["MAE_K0"] * 100.0
        )

        if len(p) > 0:
            mean_delta, ci_lo, ci_hi = bootstrap_mean_ci(
                p["improvement_pp"].to_numpy(),
                seed=SEED + len(rows)
            )

            try:
                stat, pval = wilcoxon(
                    p["MAE_K0"],
                    p["MAE_K20"],
                    alternative="greater",
                    zero_method="wilcox"
                )
            except ValueError:
                stat, pval = np.nan, np.nan

            rows.append({
                "dataset": dataset_label,
                "chemistry": chem,
                "paired_repeats": len(p),
                "K0_MAE_mean_pp": p["MAE_K0"].mean(),
                "K20_MAE_mean_pp": p["MAE_K20"].mean(),
                "mean_improvement_pp": p["improvement_pp"].mean(),
                "mean_improvement_percent": p["improvement_percent"].mean(),
                "bootstrap_improvement_mean_pp": mean_delta,
                "bootstrap_CI95_low_pp": ci_lo,
                "bootstrap_CI95_high_pp": ci_hi,
                "wilcoxon_statistic": stat,
                "wilcoxon_one_sided_p": pval,
            })

    return pd.DataFrame(rows)


internal_stats = paired_k0_k20_stats(internal, "Internal")
external_stats = paired_k0_k20_stats(external, "External_CrossDataset")
paired_stats = pd.concat(
    [internal_stats, external_stats],
    ignore_index=True
)
paired_stats.to_csv(OUT / "01_paired_k0_k20_statistics.csv", index=False)


# ---------------------------------------------------------
# Overall pooled repeat-level summaries
# ---------------------------------------------------------

def pooled_by_repeat(df, label):
    pooled = (
        df.groupby(["repeat","K_cells"])
        .agg(mean_MAE_pp=("MAE_pp","mean"))
        .reset_index()
    )

    a = pooled[pooled["K_cells"] == 0][["repeat","mean_MAE_pp"]].rename(
        columns={"mean_MAE_pp":"K0"}
    )
    b = pooled[pooled["K_cells"] == 20][["repeat","mean_MAE_pp"]].rename(
        columns={"mean_MAE_pp":"K20"}
    )
    p = a.merge(b, on="repeat")
    p["improvement_pp"] = p["K0"] - p["K20"]
    p["improvement_percent"] = p["improvement_pp"] / p["K0"] * 100.0

    mean_imp, lo, hi = bootstrap_mean_ci(
        p["improvement_pp"].to_numpy(),
        seed=SEED + (1 if label == "Internal" else 2)
    )

    try:
        stat, pval = wilcoxon(
            p["K0"], p["K20"],
            alternative="greater",
            zero_method="wilcox"
        )
    except ValueError:
        stat, pval = np.nan, np.nan

    return {
        "dataset": label,
        "paired_repeats": len(p),
        "K0_mean_MAE_pp": p["K0"].mean(),
        "K20_mean_MAE_pp": p["K20"].mean(),
        "mean_improvement_pp": p["improvement_pp"].mean(),
        "mean_improvement_percent": p["improvement_percent"].mean(),
        "bootstrap_CI95_low_pp": lo,
        "bootstrap_CI95_high_pp": hi,
        "wilcoxon_one_sided_p": pval,
    }


overall_stats = pd.DataFrame([
    pooled_by_repeat(internal, "Internal"),
    pooled_by_repeat(external, "External_CrossDataset"),
])
overall_stats.to_csv(OUT / "02_overall_paired_statistics.csv", index=False)


# ---------------------------------------------------------
# UQ calibration statistics
# ---------------------------------------------------------

uq_rows = []

for K in sorted(uq["K_total_labeled_cells"].unique()):
    d = uq[uq["K_total_labeled_cells"] == K].copy()

    picp_mean, picp_lo, picp_hi = bootstrap_mean_ci(
        d["PICP"].to_numpy(),
        seed=SEED + 100 + int(K)
    )
    mae_mean, mae_lo, mae_hi = bootstrap_mean_ci(
        d["MAE_pp"].to_numpy(),
        seed=SEED + 200 + int(K)
    )
    mpiw_mean, mpiw_lo, mpiw_hi = bootstrap_mean_ci(
        d["MPIW_pp"].to_numpy(),
        seed=SEED + 300 + int(K)
    )

    uq_rows.append({
        "K_total_labeled_cells": K,
        "MAE_mean_pp": mae_mean,
        "MAE_CI95_low_pp": mae_lo,
        "MAE_CI95_high_pp": mae_hi,
        "PICP_mean": picp_mean,
        "PICP_CI95_low": picp_lo,
        "PICP_CI95_high": picp_hi,
        "coverage_target": 0.90,
        "coverage_error_pp": abs(picp_mean - 0.90) * 100,
        "MPIW_mean_pp": mpiw_mean,
        "MPIW_CI95_low_pp": mpiw_lo,
        "MPIW_CI95_high_pp": mpiw_hi,
    })

uq_stats = pd.DataFrame(uq_rows)
uq_stats.to_csv(OUT / "03_uq_bootstrap_statistics.csv", index=False)


# ---------------------------------------------------------
# OOD compact table
# ---------------------------------------------------------

ood_primary = ood[
    ood["detector"].isin(["Mahalanobis","KNN"])
].copy()

ood_primary.to_csv(OUT / "04_ood_primary_statistics.csv", index=False)


# ---------------------------------------------------------
# Manuscript-ready integrated master table
# ---------------------------------------------------------

internal_k0 = float(
    internal_summary.loc[
        internal_summary["K_cells"] == 0,
        "mean_MAE_pp"
    ].iloc[0]
)
internal_k20 = float(
    internal_summary.loc[
        internal_summary["K_cells"] == 20,
        "mean_MAE_pp"
    ].iloc[0]
)

external_k0 = float(
    external_summary.loc[
        external_summary["K_cells"] == 0,
        "mean_MAE_pp"
    ].iloc[0]
)
external_k20 = float(
    external_summary.loc[
        external_summary["K_cells"] == 20,
        "mean_MAE_pp"
    ].iloc[0]
)

uq_k20 = uq_summary[
    uq_summary["K_total_labeled_cells"] == 20
].iloc[0]

overlap_row = overlap.iloc[0]

primary_ood = ood[
    (ood["detector"] == "Mahalanobis")
].copy()

master_rows = [
    {
        "evidence_block": "Frozen representation",
        "metric": "Representation",
        "value": "REL_RATIO_NO_STATE",
        "interpretation": "No SOC/SOCR/SOE in main predictor"
    },
    {
        "evidence_block": "Internal few-shot",
        "metric": "K0 mean MAE (pp)",
        "value": internal_k0,
        "interpretation": "Unadapted chemistry transfer"
    },
    {
        "evidence_block": "Internal few-shot",
        "metric": "K20 mean MAE (pp)",
        "value": internal_k20,
        "interpretation": "Few-shot adapted chemistry transfer"
    },
    {
        "evidence_block": "Internal few-shot",
        "metric": "K0->K20 improvement (%)",
        "value": (internal_k0-internal_k20)/internal_k0*100,
        "interpretation": "Average chemistry-level gain"
    },
    {
        "evidence_block": "Uncertainty",
        "metric": "K20 PICP",
        "value": float(uq_k20["mean_PICP"]),
        "interpretation": "Target 0.90"
    },
    {
        "evidence_block": "Uncertainty",
        "metric": "K20 MPIW (pp)",
        "value": float(uq_k20["mean_MPIW_pp"]),
        "interpretation": "Mean interval width"
    },
    {
        "evidence_block": "OOD",
        "metric": "Mahalanobis mean AUROC",
        "value": float(primary_ood["AUROC_mean"].mean()),
        "interpretation": "Held-out chemistry detection"
    },
    {
        "evidence_block": "OOD",
        "metric": "Mahalanobis target abstention rate",
        "value": float(primary_ood["abstention_rate_mean"].mean()),
        "interpretation": "Strict unseen-chemistry safety gate"
    },
    {
        "evidence_block": "Cross-dataset",
        "metric": "Non-overlapping target cells",
        "value": int(overlap_row["target_cells_after_exclusion"]),
        "interpretation": "Bipolar709 evaluation cohort"
    },
    {
        "evidence_block": "Cross-dataset",
        "metric": "Overlapping raw IDs excluded",
        "value": int(overlap_row["overlapping_raw_ids"]),
        "interpretation": "Leakage safeguard"
    },
    {
        "evidence_block": "Cross-dataset",
        "metric": "K0 mean MAE (pp)",
        "value": external_k0,
        "interpretation": "Overlap-excluded zero-shot transfer"
    },
    {
        "evidence_block": "Cross-dataset",
        "metric": "K20 mean MAE (pp)",
        "value": external_k20,
        "interpretation": "Overlap-excluded few-shot transfer"
    },
    {
        "evidence_block": "Cross-dataset",
        "metric": "K0->K20 improvement (%)",
        "value": (external_k0-external_k20)/external_k0*100,
        "interpretation": "Average external few-shot gain"
    },
]

master = pd.DataFrame(master_rows)
master.to_csv(OUT / "05_manuscript_master_evidence_table.csv", index=False)


# ---------------------------------------------------------
# Figures
# ---------------------------------------------------------

plt.figure(figsize=(7.5,5.2))
for label, df in [
    ("Internal", internal_summary),
    ("Cross-dataset", external_summary),
]:
    plt.plot(
        df["K_cells"],
        df["mean_MAE_pp"],
        marker="o",
        label=label
    )
plt.xlabel("Labeled target cells K")
plt.ylabel("Mean SOH MAE (pp)")
plt.title("Frozen no-state few-shot benefit")
plt.xticks([0,1,5,10,20])
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig01_Final_FewShot_Comparison.png", dpi=300)
plt.savefig(OUT / "Fig01_Final_FewShot_Comparison.pdf")
plt.close()

plt.figure(figsize=(7.2,5.0))
plt.errorbar(
    uq_stats["K_total_labeled_cells"],
    uq_stats["PICP_mean"]*100,
    yerr=[
        (uq_stats["PICP_mean"]-uq_stats["PICP_CI95_low"])*100,
        (uq_stats["PICP_CI95_high"]-uq_stats["PICP_mean"])*100,
    ],
    marker="o",
    capsize=4
)
plt.axhline(90, linestyle="--")
plt.xlabel("Total labeled target cells")
plt.ylabel("Empirical coverage (%)")
plt.title("90% conformal calibration with bootstrap CI")
plt.xticks([0,5,10,20])
plt.tight_layout()
plt.savefig(OUT / "Fig02_Final_Conformal_Coverage_CI.png", dpi=300)
plt.savefig(OUT / "Fig02_Final_Conformal_Coverage_CI.pdf")
plt.close()

plt.figure(figsize=(8.0,5.2))
plot = overall_stats.copy()
x = np.arange(len(plot))
plt.bar(x, plot["mean_improvement_percent"])
plt.xticks(x, plot["dataset"])
plt.ylabel("K0→K20 MAE reduction (%)")
plt.title("Few-shot adaptation effect size")
plt.tight_layout()
plt.savefig(OUT / "Fig03_Final_Improvement_Percent.png", dpi=300)
plt.savefig(OUT / "Fig03_Final_Improvement_Percent.pdf")
plt.close()


run_summary = {
    "day": "Day15",
    "input_stage": "Day14_Frozen_NoState_Pipeline",
    "frozen_representation": "REL_RATIO_NO_STATE",
    "bootstrap_resamples": N_BOOT,
    "statistical_test": "paired one-sided Wilcoxon signed-rank, K0 > K20",
    "purpose": (
        "Create final statistical robustness evidence and manuscript-ready "
        "summary tables without retraining or changing the frozen pipeline."
    ),
    "important_note": (
        "Statistical inference is based on the repeated Day14 resampling design. "
        "It should be reported as robustness evidence, not as a substitute for "
        "a larger genuinely independent experimental cohort."
    ),
    "output_dir": str(OUT),
}
(OUT / "06_run_summary.json").write_text(
    json.dumps(run_summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 15 COMPLETE ===")
print("\nOverall paired K0 vs K20:")
print(overall_stats.to_string(index=False))
print("\nUQ bootstrap statistics:")
print(uq_stats.to_string(index=False))
print("\nManuscript master evidence table:")
print(master.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("01_paired_k0_k20_statistics.csv")
print("02_overall_paired_statistics.csv")
print("03_uq_bootstrap_statistics.csv")
print("04_ood_primary_statistics.csv")
print("05_manuscript_master_evidence_table.csv")
print("06_run_summary.json")
