r"""
Day 21 — Final computational evidence freeze and publication-table package
==========================================================================

Purpose
-------
Freeze the verified computational results into a single manuscript-ready
evidence package.

This stage DOES NOT retrain any model.

It consolidates:
- Day13 state-free representation freeze
- Day14 frozen no-state pipeline
- Day15 statistical robustness
- Day19 corrected screening-safety sensitivity
- Day20 claim-readiness gate

Outputs
-------
D:\SecondLife_Research\Result\Day21_FinalEvidenceFreeze

Files:
01_final_headline_metrics.csv
02_final_claim_boundaries.csv
03_publication_table_core_results.csv
04_publication_table_screening_sensitivity.csv
05_results_evidence_freeze.md
06_run_summary.json

Figures:
Fig01_FewShot_Internal_External.png/.pdf
Fig02_Conformal_Coverage.png/.pdf
Fig03_Screening_Calibration_Tradeoff.png/.pdf
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(r"D:\SecondLife_Research")
RESULT = ROOT / "Result"
OUT = RESULT / "Day21_FinalEvidenceFreeze"
OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    "state_freeze":
        RESULT / "Day13_StateSensitivity" / "06_representation_freeze_summary.csv",

    "internal":
        RESULT / "Day14_Frozen_NoState_Pipeline" / "10_internal_summary.csv",

    "uq":
        RESULT / "Day14_Frozen_NoState_Pipeline" / "11_uq_summary.csv",

    "external":
        RESULT / "Day14_Frozen_NoState_Pipeline" / "12_external_summary.csv",

    "overlap":
        RESULT / "Day14_Frozen_NoState_Pipeline" / "09_external_overlap_summary.csv",

    "paired_stats":
        RESULT / "Day15_FinalStatistics" / "02_overall_paired_statistics.csv",

    "screening":
        RESULT / "Day16_ScreeningDecision" / "04_screening_overall_summary.csv",

    "integrity":
        RESULT / "Day19_CorrectedCalibrationSensitivity" / "06_day16_integrity_gate.csv",

    "calibration":
        RESULT / "Day19_CorrectedCalibrationSensitivity" / "04_corrected_calibration_overall.csv",

    "claims":
        RESULT / "Day20_ClaimReadiness" / "02_claim_readiness_matrix.csv",

    "titles":
        RESULT / "Day20_ClaimReadiness" / "04_title_readiness_options.csv",
}

missing = [
    str(p)
    for p in FILES.values()
    if not p.exists()
]

if missing:
    raise FileNotFoundError(
        "Missing required frozen evidence:\n"
        + "\n".join(missing)
    )

state_freeze = pd.read_csv(FILES["state_freeze"])
internal = pd.read_csv(FILES["internal"])
uq = pd.read_csv(FILES["uq"])
external = pd.read_csv(FILES["external"])
overlap = pd.read_csv(FILES["overlap"])
paired = pd.read_csv(FILES["paired_stats"])
screening = pd.read_csv(FILES["screening"])
integrity = pd.read_csv(FILES["integrity"])
calibration = pd.read_csv(FILES["calibration"])
claims = pd.read_csv(FILES["claims"])
titles = pd.read_csv(FILES["titles"])

# ---------------------------------------------------------------------
# Integrity checks
# ---------------------------------------------------------------------

if not bool(integrity.iloc[0]["reproduction_pass"]):
    raise RuntimeError(
        "Day19 integrity gate did not pass. "
        "Do not freeze manuscript evidence."
    )

def get_row(df, col, value):
    x = df.loc[df[col] == value]
    if x.empty:
        raise KeyError(f"Missing {col}={value}")
    return x.iloc[0]

int_k0 = get_row(internal, "K_cells", 0)
int_k20 = get_row(internal, "K_cells", 20)

ext_k0 = get_row(external, "K_cells", 0)
ext_k20 = get_row(external, "K_cells", 20)

uq_k20 = get_row(
    uq,
    "K_total_labeled_cells",
    20
)

stats_internal = get_row(
    paired,
    "dataset",
    "Internal"
)

stats_external = get_row(
    paired,
    "dataset",
    "External_CrossDataset"
)

overlap_row = overlap.iloc[0]
screen_row = screening.iloc[0]

cal10 = get_row(
    calibration,
    "calibration_cells",
    10
)

cal20 = get_row(
    calibration,
    "calibration_cells",
    20
)

cal30 = get_row(
    calibration,
    "calibration_cells",
    30
)

recommended_title = (
    titles.sort_values("priority")
    .iloc[0]["title"]
)

# ---------------------------------------------------------------------
# 01 — Final headline metrics
# ---------------------------------------------------------------------

headline_rows = [
    {
        "block": "Representation",
        "metric": "Frozen primary representation",
        "value": "REL_RATIO_NO_STATE",
        "unit": "",
    },
    {
        "block": "Internal few-shot",
        "metric": "K0 mean MAE",
        "value": float(int_k0["mean_MAE_pp"]),
        "unit": "pp",
    },
    {
        "block": "Internal few-shot",
        "metric": "K20 mean MAE",
        "value": float(int_k20["mean_MAE_pp"]),
        "unit": "pp",
    },
    {
        "block": "Internal few-shot",
        "metric": "K0->K20 MAE reduction",
        "value": float(
            stats_internal["mean_improvement_percent"]
        ),
        "unit": "%",
    },
    {
        "block": "Internal statistics",
        "metric": "Paired Wilcoxon p",
        "value": float(
            stats_internal["wilcoxon_one_sided_p"]
        ),
        "unit": "",
    },
    {
        "block": "Internal statistics",
        "metric": "Bootstrap CI low improvement",
        "value": float(
            stats_internal["bootstrap_CI95_low_pp"]
        ),
        "unit": "pp",
    },
    {
        "block": "Internal statistics",
        "metric": "Bootstrap CI high improvement",
        "value": float(
            stats_internal["bootstrap_CI95_high_pp"]
        ),
        "unit": "pp",
    },
    {
        "block": "Uncertainty",
        "metric": "K20 empirical coverage",
        "value": float(uq_k20["mean_PICP"]),
        "unit": "fraction",
    },
    {
        "block": "Uncertainty",
        "metric": "K20 mean interval width",
        "value": float(uq_k20["mean_MPIW_pp"]),
        "unit": "pp",
    },
    {
        "block": "External cross-dataset",
        "metric": "K0 mean MAE",
        "value": float(ext_k0["mean_MAE_pp"]),
        "unit": "pp",
    },
    {
        "block": "External cross-dataset",
        "metric": "K20 mean MAE",
        "value": float(ext_k20["mean_MAE_pp"]),
        "unit": "pp",
    },
    {
        "block": "External cross-dataset",
        "metric": "K0->K20 MAE reduction",
        "value": float(
            stats_external["mean_improvement_percent"]
        ),
        "unit": "%",
    },
    {
        "block": "External cross-dataset",
        "metric": "Paired Wilcoxon p",
        "value": float(
            stats_external["wilcoxon_one_sided_p"]
        ),
        "unit": "",
    },
    {
        "block": "External cross-dataset",
        "metric": "Overlap raw IDs excluded",
        "value": int(
            overlap_row["overlapping_raw_ids"]
        ),
        "unit": "IDs",
    },
    {
        "block": "External cross-dataset",
        "metric": "Target cells retained",
        "value": int(
            overlap_row["target_cells_after_exclusion"]
        ),
        "unit": "cells",
    },
    {
        "block": "Screening",
        "metric": "10-cal false-safe rate",
        "value": float(
            cal10["false_safe_rate_mean"]
        ),
        "unit": "fraction",
    },
    {
        "block": "Screening",
        "metric": "20-cal false-safe rate",
        "value": float(
            cal20["false_safe_rate_mean"]
        ),
        "unit": "fraction",
    },
    {
        "block": "Screening",
        "metric": "30-cal false-safe rate",
        "value": float(
            cal30["false_safe_rate_mean"]
        ),
        "unit": "fraction",
    },
    {
        "block": "Screening",
        "metric": "20-cal empirical coverage",
        "value": float(
            cal20["PICP_mean"]
        ),
        "unit": "fraction",
    },
]

headline = pd.DataFrame(headline_rows)

headline.to_csv(
    OUT / "01_final_headline_metrics.csv",
    index=False
)

# ---------------------------------------------------------------------
# 02 — Final claim boundaries
# ---------------------------------------------------------------------

claims_out = claims[
    [
        "claim_id",
        "status",
        "claim",
        "safe_wording",
        "do_not_say",
    ]
].copy()

claims_out.to_csv(
    OUT / "02_final_claim_boundaries.csv",
    index=False
)

# ---------------------------------------------------------------------
# 03 — Publication table: core results
# ---------------------------------------------------------------------

core_table = pd.DataFrame([
    {
        "Evidence block": "Internal few-shot",
        "Condition": "K=0",
        "MAE_pp": float(int_k0["mean_MAE_pp"]),
        "Primary result": "Zero-shot chemistry transfer",
    },
    {
        "Evidence block": "Internal few-shot",
        "Condition": "K=20",
        "MAE_pp": float(int_k20["mean_MAE_pp"]),
        "Primary result": "Few-shot chemistry transfer",
    },
    {
        "Evidence block": "Internal statistics",
        "Condition": "K0 vs K20",
        "MAE_pp": np.nan,
        "Primary result": (
            f"{float(stats_internal['mean_improvement_percent']):.2f}% "
            f"reduction; p={float(stats_internal['wilcoxon_one_sided_p']):.6f}"
        ),
    },
    {
        "Evidence block": "Conformal UQ",
        "Condition": "K=20",
        "MAE_pp": float(uq_k20["mean_MAE_pp"]),
        "Primary result": (
            f"PICP={100*float(uq_k20['mean_PICP']):.2f}%; "
            f"MPIW={float(uq_k20['mean_MPIW_pp']):.2f} pp"
        ),
    },
    {
        "Evidence block": "External cross-dataset",
        "Condition": "K=0",
        "MAE_pp": float(ext_k0["mean_MAE_pp"]),
        "Primary result": "Overlap-excluded zero-shot transfer",
    },
    {
        "Evidence block": "External cross-dataset",
        "Condition": "K=20",
        "MAE_pp": float(ext_k20["mean_MAE_pp"]),
        "Primary result": "Overlap-excluded few-shot transfer",
    },
    {
        "Evidence block": "External statistics",
        "Condition": "K0 vs K20",
        "MAE_pp": np.nan,
        "Primary result": (
            f"{float(stats_external['mean_improvement_percent']):.2f}% "
            f"reduction; p={float(stats_external['wilcoxon_one_sided_p']):.6f}"
        ),
    },
])

core_table.to_csv(
    OUT / "03_publication_table_core_results.csv",
    index=False
)

# ---------------------------------------------------------------------
# 04 — Publication table: screening sensitivity
# ---------------------------------------------------------------------

screen_table = calibration[
    [
        "total_labeled_cells",
        "adaptation_cells",
        "calibration_cells",
        "PICP_mean",
        "MPIW_mean_pp",
        "decisive_rate_mean",
        "Class_C_rate_mean",
        "false_safe_rate_mean",
        "false_direct_reuse_rate_mean",
        "total_false_safe",
        "total_false_direct_reuse",
    ]
].copy()

screen_table.to_csv(
    OUT / "04_publication_table_screening_sensitivity.csv",
    index=False
)

# ---------------------------------------------------------------------
# 05 — Evidence freeze markdown
# ---------------------------------------------------------------------

md = f"""# Day 21 — Final Computational Evidence Freeze

## Recommended current title

**{recommended_title}**

## Frozen primary representation

`REL_RATIO_NO_STATE = (Ui-U1)/abs(U1), i=2..21`

No SOC/SOCR/SOE is used in the main predictor.

## Internal few-shot evidence

- K=0 mean MAE: {float(int_k0['mean_MAE_pp']):.3f} pp
- K=20 mean MAE: {float(int_k20['mean_MAE_pp']):.3f} pp
- Mean K0→K20 reduction: {float(stats_internal['mean_improvement_percent']):.2f}%
- Paired one-sided Wilcoxon p: {float(stats_internal['wilcoxon_one_sided_p']):.6f}
- 95% bootstrap improvement CI:
  {float(stats_internal['bootstrap_CI95_low_pp']):.3f}–
  {float(stats_internal['bootstrap_CI95_high_pp']):.3f} pp

## Target-aware uncertainty

- K=20 empirical coverage:
  {100*float(uq_k20['mean_PICP']):.2f}%
- K=20 mean interval width:
  {float(uq_k20['mean_MPIW_pp']):.2f} pp

## Overlap-excluded cross-dataset evidence

- Overlapping raw IDs excluded:
  {int(overlap_row['overlapping_raw_ids'])}
- Target cells retained:
  {int(overlap_row['target_cells_after_exclusion'])}
- K=0 mean MAE:
  {float(ext_k0['mean_MAE_pp']):.3f} pp
- K=20 mean MAE:
  {float(ext_k20['mean_MAE_pp']):.3f} pp
- Mean K0→K20 reduction:
  {float(stats_external['mean_improvement_percent']):.2f}%
- Paired one-sided Wilcoxon p:
  {float(stats_external['wilcoxon_one_sided_p']):.6f}

Correct wording:
**overlap-excluded cross-dataset validation**

Do not write:
**fully independent external validation**

## Screening sensitivity

### 10 calibration cells
- PICP: {100*float(cal10['PICP_mean']):.2f}%
- false-safe rate: {100*float(cal10['false_safe_rate_mean']):.3f}%
- total false-safe events: {int(cal10['total_false_safe'])}
- decisive rate: {100*float(cal10['decisive_rate_mean']):.2f}%

### 20 calibration cells
- PICP: {100*float(cal20['PICP_mean']):.2f}%
- false-safe rate: {100*float(cal20['false_safe_rate_mean']):.3f}%
- total false-safe events: {int(cal20['total_false_safe'])}
- decisive rate: {100*float(cal20['decisive_rate_mean']):.2f}%

### 30 calibration cells
- PICP: {100*float(cal30['PICP_mean']):.2f}%
- false-safe rate: {100*float(cal30['false_safe_rate_mean']):.3f}%
- total false-safe events: {int(cal30['total_false_safe'])}
- decisive rate: {100*float(cal30['decisive_rate_mean']):.2f}%

## Final claim boundary

Primary-supported:
- state-free relative pulse representation
- few-shot adaptation
- target-aware uncertainty calibration

Supported with scope:
- tested chemistry OOD detection
- conservative screening sensitivity
- calibration-size safety benefit in repeated-resampling analysis

Supplementary:
- ECM-inspired pulse-physics surrogate analysis

Not yet supported:
- fully independent external validation
- validated electrical 1RC/2RC Digital Twin
- `Digital-Twin-Assisted` in the current title
- full experimental validation
- deployment certification

## Manuscript rule

All future paper/thesis tables should use this frozen evidence package unless
a later independently verified stage explicitly supersedes it.
"""

(OUT / "05_results_evidence_freeze.md").write_text(
    md,
    encoding="utf-8"
)

# ---------------------------------------------------------------------
# Figures — PNG 300 dpi + true vector PDF
# ---------------------------------------------------------------------

plt.figure(figsize=(7.4, 5.0))

plt.plot(
    internal["K_cells"],
    internal["mean_MAE_pp"],
    marker="o",
    label="Internal chemistry shift"
)

plt.plot(
    external["K_cells"],
    external["mean_MAE_pp"],
    marker="o",
    label="Overlap-excluded cross-dataset"
)

plt.xlabel("Labeled target cells K")
plt.ylabel("Mean SOH MAE (pp)")
plt.title("Few-shot adaptation with frozen state-free representation")
plt.xticks([0, 1, 5, 10, 20])
plt.legend()
plt.tight_layout()

plt.savefig(
    OUT / "Fig01_FewShot_Internal_External.png",
    dpi=300
)

plt.savefig(
    OUT / "Fig01_FewShot_Internal_External.pdf"
)

plt.close()


plt.figure(figsize=(7.2, 5.0))

plt.plot(
    uq["K_total_labeled_cells"],
    uq["mean_PICP"] * 100,
    marker="o"
)

plt.axhline(
    90,
    linestyle="--"
)

plt.xlabel("Total labeled target cells")
plt.ylabel("Empirical coverage (%)")
plt.title("Target-aware conformal calibration")
plt.xticks([0, 5, 10, 20])
plt.tight_layout()

plt.savefig(
    OUT / "Fig02_Conformal_Coverage.png",
    dpi=300
)

plt.savefig(
    OUT / "Fig02_Conformal_Coverage.pdf"
)

plt.close()


plt.figure(figsize=(7.4, 5.0))

plt.plot(
    calibration["calibration_cells"],
    calibration["false_safe_rate_mean"] * 100,
    marker="o",
    label="False-safe rate"
)

plt.plot(
    calibration["calibration_cells"],
    calibration["decisive_rate_mean"] * 100,
    marker="o",
    label="Decisive A/B/D rate"
)

plt.xlabel("Target calibration cells")
plt.ylabel("Rate (%)")
plt.title("Screening safety–decisiveness sensitivity")
plt.legend()
plt.tight_layout()

plt.savefig(
    OUT / "Fig03_Screening_Calibration_Tradeoff.png",
    dpi=300
)

plt.savefig(
    OUT / "Fig03_Screening_Calibration_Tradeoff.pdf"
)

plt.close()

# ---------------------------------------------------------------------
# Run summary
# ---------------------------------------------------------------------

run_summary = {
    "day": "Day21",
    "purpose": (
        "Freeze all verified computational evidence into a single "
        "manuscript-ready package without retraining."
    ),
    "recommended_title": recommended_title,
    "primary_representation": "REL_RATIO_NO_STATE",
    "day19_integrity_gate": True,
    "digital_twin_title_status": "NOT_YET_DEFENSIBLE",
    "external_validation_wording":
        "overlap-excluded cross-dataset validation",
    "independent_chroma_validation": "PENDING",
    "output_dir": str(OUT),
}

(OUT / "06_run_summary.json").write_text(
    json.dumps(
        run_summary,
        indent=2
    ),
    encoding="utf-8"
)

print("\n=== DAY 21 COMPLETE ===")

print("\nFinal headline metrics:")
print(headline.to_string(index=False))

print("\nFinal recommended title:")
print(recommended_title)

print("\nClaim status counts:")
print(
    claims["status"]
    .value_counts()
    .to_string()
)

print(f"\nResults saved to:\n{OUT}")

print("\nSend me:")
print("01_final_headline_metrics.csv")
print("02_final_claim_boundaries.csv")
print("03_publication_table_core_results.csv")
print("04_publication_table_screening_sensitivity.csv")
print("05_results_evidence_freeze.md")
print("06_run_summary.json")
