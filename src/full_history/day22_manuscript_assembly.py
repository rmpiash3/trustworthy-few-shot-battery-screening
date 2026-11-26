r"""
Day 22 — Manuscript / thesis assembly pack from frozen evidence
==============================================================

Purpose
-------
Build a writing-ready package from the frozen Day21 computational evidence.

This stage DOES NOT retrain or recompute the research model.

Inputs
------
D:\SecondLife_Research\Result\Day21_FinalEvidenceFreeze

Outputs
-------
D:\SecondLife_Research\Result\Day22_ManuscriptAssembly

Files:
01_manuscript_outline.md
02_results_section_evidence.md
03_methods_reporting_checklist.md
04_figure_captions.md
05_table_captions.md
06_limitations_and_claim_boundaries.md
07_run_summary.json

Important
---------
All wording is constrained by the Day21 claim-readiness freeze.
"""

from pathlib import Path
import json
import pandas as pd

ROOT = Path(r"D:\SecondLife_Research")
DAY21 = ROOT / "Result" / "Day21_FinalEvidenceFreeze"
OUT = ROOT / "Result" / "Day22_ManuscriptAssembly"
OUT.mkdir(parents=True, exist_ok=True)

required = {
    "headline": DAY21 / "01_final_headline_metrics.csv",
    "claims": DAY21 / "02_final_claim_boundaries.csv",
    "core": DAY21 / "03_publication_table_core_results.csv",
    "screen": DAY21 / "04_publication_table_screening_sensitivity.csv",
    "freeze": DAY21 / "05_results_evidence_freeze.md",
    "summary": DAY21 / "06_run_summary.json",
}

missing = [str(p) for p in required.values() if not p.exists()]
if missing:
    raise FileNotFoundError(
        "Missing Day21 frozen evidence:\n" + "\n".join(missing)
    )

headline = pd.read_csv(required["headline"])
claims = pd.read_csv(required["claims"])
core = pd.read_csv(required["core"])
screen = pd.read_csv(required["screen"])
summary = json.loads(required["summary"].read_text(encoding="utf-8"))

title = summary["recommended_title"]

def metric(name):
    row = headline.loc[headline["metric"] == name]
    if row.empty:
        raise KeyError(name)
    return row.iloc[0]["value"]

int_k0 = float(metric("K0 mean MAE"))
# There are two rows named K0 mean MAE; use blocks explicitly below.
def block_metric(block, name):
    row = headline[
        (headline["block"] == block) &
        (headline["metric"] == name)
    ]
    if row.empty:
        raise KeyError((block, name))
    return row.iloc[0]["value"]

int_k0 = float(block_metric("Internal few-shot", "K0 mean MAE"))
int_k20 = float(block_metric("Internal few-shot", "K20 mean MAE"))
int_red = float(block_metric("Internal few-shot", "K0->K20 MAE reduction"))
int_p = float(block_metric("Internal statistics", "Paired Wilcoxon p"))
int_ci_lo = float(block_metric("Internal statistics", "Bootstrap CI low improvement"))
int_ci_hi = float(block_metric("Internal statistics", "Bootstrap CI high improvement"))

uq_picp = float(block_metric("Uncertainty", "K20 empirical coverage"))
uq_mpiw = float(block_metric("Uncertainty", "K20 mean interval width"))

ext_k0 = float(block_metric("External cross-dataset", "K0 mean MAE"))
ext_k20 = float(block_metric("External cross-dataset", "K20 mean MAE"))
ext_red = float(block_metric("External cross-dataset", "K0->K20 MAE reduction"))
ext_p = float(block_metric("External cross-dataset", "Paired Wilcoxon p"))
overlap_ids = int(float(block_metric("External cross-dataset", "Overlap raw IDs excluded")))
retained_cells = int(float(block_metric("External cross-dataset", "Target cells retained")))

fs10 = float(block_metric("Screening", "10-cal false-safe rate"))
fs20 = float(block_metric("Screening", "20-cal false-safe rate"))
fs30 = float(block_metric("Screening", "30-cal false-safe rate"))
picp20 = float(block_metric("Screening", "20-cal empirical coverage"))

outline = f"""# Manuscript Outline

## Proposed Title
**{title}**

## 1. Introduction
1. Motivation: heterogeneous second-life lithium-ion battery screening.
2. Limitation of full-cycle diagnostics for rapid reuse decisions.
3. Domain shift across chemistry, capacity, dataset, and ageing history.
4. Need for few-shot adaptation, calibrated uncertainty, OOD awareness, and abstention.
5. Study objective and contributions.

## 2. Materials and Data
### 2.1 PulseBat processed pulse-response dataset
### 2.2 External LFP23 time-series dataset
### 2.3 Bipolar709 cross-dataset cohort
### 2.4 Overlap exclusion and leakage safeguards

## 3. Methods
### 3.1 Frozen state-free pulse representation
`REL_RATIO_NO_STATE = (Ui-U1)/abs(U1), i=2..21`

### 3.2 Grouped cross-domain validation
### 3.3 Few-shot target adaptation
### 3.4 Target-aware conformal uncertainty
### 3.5 OOD detection and abstention
### 3.6 Overlap-excluded cross-dataset validation
### 3.7 Conservative A/B/C/D screening sensitivity
### 3.8 Statistical analysis

## 4. Results
### 4.1 Raw cross-domain failure motivates normalized representation
### 4.2 State-free representation robustness
### 4.3 Internal few-shot improvement
### 4.4 Calibrated uncertainty
### 4.5 OOD detection and abstention
### 4.6 Overlap-excluded cross-dataset transfer
### 4.7 Screening safety / calibration-size sensitivity
### 4.8 Physics-surrogate ablation

## 5. Discussion
1. Why relative pulse shape transfers better than raw absolute voltage.
2. Why small target adaptation sets correct domain bias.
3. Why uncertainty calibration needs target-domain evidence.
4. Why OOD and prediction accuracy must not be conflated.
5. Safety–coverage–decisiveness trade-off.
6. Finite-sample conformal limitations.
7. External-validation scope.
8. Why the current evidence is not yet a validated electrical Digital Twin.

## 6. Limitations
- public / processed datasets
- overlap-excluded rather than fully independent external validation
- no validated 1RC/2RC electrical twin
- repeated-resampling evidence is not deployment certification
- Chroma proof-of-concept pending

## 7. Conclusion
Summarize trustworthy few-shot pulse diagnostics, calibrated uncertainty,
OOD-aware abstention, and conservative screening without overclaiming.
"""
(OUT / "01_manuscript_outline.md").write_text(outline, encoding="utf-8")

results = f"""# Results Section — Frozen Evidence

## Internal few-shot adaptation
Using the frozen state-free relative pulse representation, mean SOH MAE decreased
from **{int_k0:.3f} pp at K=0** to **{int_k20:.3f} pp at K=20**, corresponding to
a **{int_red:.2f}% reduction**. The paired one-sided Wilcoxon signed-rank test
gave **p={int_p:.6f}**, while the 95% bootstrap confidence interval for the mean
absolute improvement was **{int_ci_lo:.3f}–{int_ci_hi:.3f} pp**.

## Target-aware uncertainty
At K=20, the split-conformal procedure achieved **{100*uq_picp:.2f}% empirical
coverage** with a mean prediction-interval width of **{uq_mpiw:.2f} pp**.
This should be described as approximately nominal 90% coverage in the tested
target-aware calibration design, not as a universal coverage guarantee.

## Overlap-excluded cross-dataset validation
After excluding **{overlap_ids} overlapping raw IDs**, **{retained_cells} target
cells** remained for Bipolar709 evaluation. Mean MAE decreased from
**{ext_k0:.3f} pp at K=0** to **{ext_k20:.3f} pp at K=20**, a
**{ext_red:.2f}% reduction** with paired one-sided Wilcoxon
**p={ext_p:.6f}**.

Use the wording:
**overlap-excluded cross-dataset validation**

Do not write:
**fully independent external validation**

## Screening sensitivity
The conservative interval-based screening policy exhibited an observed
false-safe rate of **{100*fs10:.3f}%** with 10 target calibration cells.
In the protocol-locked sensitivity analysis, the observed true false-safe rate
was **{100*fs20:.3f}%** with 20 calibration cells and **{100*fs30:.3f}%** with
30 calibration cells. At 20 calibration cells, empirical coverage was
**{100*picp20:.2f}%**.

These zero observed false-safe counts must not be interpreted as zero deployment
risk. The screening analysis is sensitivity evidence rather than certification.
"""
(OUT / "02_results_section_evidence.md").write_text(results, encoding="utf-8")

methods = """# Methods Reporting Checklist

- State explicitly that the frozen main predictor uses no SOC/SOCR/SOE feature.
- Define REL_RATIO_NO_STATE exactly.
- Report cell/group-aware splits to avoid row-level leakage.
- State K={0,1,5,10,20} where applicable.
- Explain adaptation/test disjointness at cell level.
- Report target weighting used in weighted retraining.
- Explain split-conformal calibration at cell level.
- State that source-only conformal calibration undercovered under chemistry shift.
- Explain OOD detector and source-derived threshold.
- Distinguish OOD detection from SOH-error prediction.
- Report overlap-exclusion rule for Bipolar709.
- Use repeated seeds and paired statistics.
- Report bootstrap CI and Wilcoxon test.
- State screening thresholds are configurable engineering assumptions, not universal standards.
- State that screening results are sensitivity evidence, not deployment certification.
- State that no validated electrical 1RC/2RC Digital Twin is claimed.
"""
(OUT / "03_methods_reporting_checklist.md").write_text(methods, encoding="utf-8")

figcaps = """# Figure Captions

## Figure 1
**Few-shot adaptation under internal chemistry shift and overlap-excluded
cross-dataset transfer.** Mean SOH MAE is shown as a function of the number of
labeled target cells K using the frozen REL_RATIO_NO_STATE representation.

## Figure 2
**Target-aware split-conformal coverage versus labeled target-cell budget.**
Empirical prediction-interval coverage approaches the nominal 90% level as
target-domain calibration evidence increases.

## Figure 3
**Safety–decisiveness sensitivity to target calibration-set size.**
Observed false-safe rate and decisive A/B/D assignment rate are shown for
protocol-locked calibration-size sensitivity. Zero observed false-safe events
must not be interpreted as zero deployment risk.
"""
(OUT / "04_figure_captions.md").write_text(figcaps, encoding="utf-8")

tablecaps = """# Table Captions

## Table 1
**Core predictive and uncertainty results using the frozen state-free pulse
representation.** Internal chemistry-shift and overlap-excluded cross-dataset
results are reported for zero-shot and few-shot adaptation.

## Table 2
**Protocol-locked screening sensitivity to target calibration-set size.**
Coverage, interval width, decisive rate, Class-C rate, observed false-safe rate,
and false-direct-reuse rate are reported while holding the Day16 model and
source-training protocol fixed.
"""
(OUT / "05_table_captions.md").write_text(tablecaps, encoding="utf-8")

limits = """# Limitations and Claim Boundaries

## Safe primary claims
- State-free relative pulse representation supports cross-domain screening.
- Few-shot target adaptation materially reduces SOH error.
- Target-aware conformal calibration approaches nominal 90% empirical coverage.

## Safe only with scope
- OOD detection strongly separates the tested held-out chemistries.
- Conservative screening shows low observed false-safe rates in repeated-resampling sensitivity.
- Larger calibration sets removed observed true false-safe events in the tested protocol-locked analysis.

## Supplementary only
- ECM-inspired pulse-physics surrogate features provide interpretability and some chemistry-specific value.

## Do not claim yet
- Fully independent external validation.
- Validated electrical 1RC/2RC Digital Twin.
- Digital-Twin-Assisted title.
- Full experimental validation.
- Deployment certification.
- Zero-risk screening.

## Required future evidence for Digital-Twin wording
A raw pulse/HPPC or Chroma stage with identifiable and bounded electrical
parameters such as R0, R1, C1, R2, C2, residual diagnostics, held-out validation,
and a demonstrable contribution beyond the ML representation.
"""
(OUT / "06_limitations_and_claim_boundaries.md").write_text(limits, encoding="utf-8")

run_summary = {
    "day": "Day22",
    "purpose": "Build manuscript/thesis writing assets from the frozen Day21 evidence.",
    "recommended_title": title,
    "computational_results_status": "FROZEN",
    "model_retraining": False,
    "digital_twin_title_status": "NOT_YET_DEFENSIBLE",
    "independent_chroma_validation": "PENDING",
    "output_dir": str(OUT),
}

(OUT / "07_run_summary.json").write_text(
    json.dumps(run_summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 22 COMPLETE ===")
print("\nRecommended title:")
print(title)
print("\nComputational results status: FROZEN")
print("\nFiles saved to:")
print(OUT)
print("\nSend me:")
print("01_manuscript_outline.md")
print("02_results_section_evidence.md")
print("03_methods_reporting_checklist.md")
print("04_figure_captions.md")
print("05_table_captions.md")
print("06_limitations_and_claim_boundaries.md")
print("07_run_summary.json")
