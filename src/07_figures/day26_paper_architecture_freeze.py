r"""
Day 26 — Final paper architecture freeze
========================================

Purpose
-------
Freeze the main-paper figure, table, and equation architecture before
journal-specific formatting.

No model retraining.
No metric recomputation.
No scientific claim changes.

Inputs
------
D:\SecondLife_Research\Result\Day21_FinalEvidenceFreeze
D:\SecondLife_Research\Result\Day25_FinalSubmissionPackage

Outputs
-------
D:\SecondLife_Research\Result\Day26_PaperArchitectureFreeze

Creates:
01_main_figure_plan.md
02_main_table_plan.md
03_main_equation_plan.md
04_supplementary_plan.md
05_paper_storyboard.md
Fig01_Framework_Schematic.png
Fig01_Framework_Schematic.pdf
paper_figures\ (copies existing frozen Day21 figures with final numbering)
06_run_summary.json
"""

from pathlib import Path
import json
import shutil
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(r"D:\SecondLife_Research")
DAY21 = ROOT / "Result" / "Day21_FinalEvidenceFreeze"
DAY25 = ROOT / "Result" / "Day25_FinalSubmissionPackage"
OUT = ROOT / "Result" / "Day26_PaperArchitectureFreeze"
PAPER_FIG = OUT / "paper_figures"

OUT.mkdir(parents=True, exist_ok=True)
PAPER_FIG.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# Figure 1 — Framework schematic
# ---------------------------------------------------------

fig, ax = plt.subplots(figsize=(14, 4.8))
ax.set_xlim(0, 14)
ax.set_ylim(0, 5)
ax.axis("off")

boxes = [
    (0.4, 2.0, 1.7, 1.0, "Retired battery\npopulation"),
    (2.5, 2.0, 1.8, 1.0, "Short pulse\nU1–U21"),
    (4.7, 2.0, 2.0, 1.0, "State-free feature\nREL_RATIO"),
    (7.1, 2.0, 1.8, 1.0, "Few-shot\nadaptation"),
    (9.3, 2.0, 1.8, 1.0, "Conformal\nuncertainty"),
    (11.5, 2.0, 1.8, 1.0, "Screen / abstain\nA–B–C–D"),
]

for x, y, w, h, label in boxes:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.05",
        linewidth=1.5,
        fill=False,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        label,
        ha="center",
        va="center",
        fontsize=11,
    )

for i in range(len(boxes) - 1):
    x1 = boxes[i][0] + boxes[i][2]
    y1 = boxes[i][1] + boxes[i][3] / 2
    x2 = boxes[i + 1][0]
    y2 = boxes[i + 1][1] + boxes[i + 1][3] / 2

    arrow = FancyArrowPatch(
        (x1 + 0.05, y1),
        (x2 - 0.05, y2),
        arrowstyle="->",
        mutation_scale=16,
        linewidth=1.4,
    )
    ax.add_patch(arrow)

# OOD branch
ood = FancyBboxPatch(
    (8.9, 0.25),
    2.6,
    0.9,
    boxstyle="round,pad=0.05",
    linewidth=1.5,
    fill=False,
)
ax.add_patch(ood)

ax.text(
    10.2,
    0.70,
    "OOD applicability-domain check",
    ha="center",
    va="center",
    fontsize=10.5,
)

ax.add_patch(
    FancyArrowPatch(
        (8.0, 2.0),
        (9.7, 1.15),
        arrowstyle="->",
        mutation_scale=15,
        linewidth=1.3,
    )
)

ax.add_patch(
    FancyArrowPatch(
        (10.7, 1.15),
        (12.0, 2.0),
        arrowstyle="->",
        mutation_scale=15,
        linewidth=1.3,
    )
)

ax.text(
    7.0,
    4.15,
    "Trustworthy few-shot pulse diagnostic pipeline",
    ha="center",
    va="center",
    fontsize=15,
    fontweight="bold",
)

ax.text(
    7.0,
    3.65,
    "Prediction, uncertainty, OOD detection, and screening are evaluated as separate layers",
    ha="center",
    va="center",
    fontsize=10.5,
)

plt.tight_layout()

fig_png = OUT / "Fig01_Framework_Schematic.png"
fig_pdf = OUT / "Fig01_Framework_Schematic.pdf"

plt.savefig(
    fig_png,
    dpi=300,
    bbox_inches="tight",
)

plt.savefig(
    fig_pdf,
    bbox_inches="tight",
)

plt.close()

# ---------------------------------------------------------
# Copy frozen Day21 figures with final paper numbering
# ---------------------------------------------------------

figure_mapping = {
    DAY21 / "Fig01_FewShot_Internal_External.png":
        PAPER_FIG / "Fig02_FewShot_Internal_External.png",

    DAY21 / "Fig01_FewShot_Internal_External.pdf":
        PAPER_FIG / "Fig02_FewShot_Internal_External.pdf",

    DAY21 / "Fig02_Conformal_Coverage.png":
        PAPER_FIG / "Fig03_Conformal_Coverage.png",

    DAY21 / "Fig02_Conformal_Coverage.pdf":
        PAPER_FIG / "Fig03_Conformal_Coverage.pdf",

    DAY21 / "Fig03_Screening_Calibration_Tradeoff.png":
        PAPER_FIG / "Fig04_Screening_Calibration_Tradeoff.png",

    DAY21 / "Fig03_Screening_Calibration_Tradeoff.pdf":
        PAPER_FIG / "Fig04_Screening_Calibration_Tradeoff.pdf",
}

missing = []

for src, dst in figure_mapping.items():
    if src.exists():
        shutil.copy2(src, dst)
    else:
        missing.append(str(src))

if missing:
    raise FileNotFoundError(
        "Missing frozen Day21 figure(s):\n"
        + "\n".join(missing)
    )

# Also copy Figure 1 into final paper folder.
shutil.copy2(
    fig_png,
    PAPER_FIG / fig_png.name,
)

shutil.copy2(
    fig_pdf,
    PAPER_FIG / fig_pdf.name,
)

# ---------------------------------------------------------
# Main figure plan
# ---------------------------------------------------------

figure_plan = """# Main Figure Plan — FROZEN

## Figure 1 — Trustworthy few-shot pulse-diagnostic framework

Purpose:
Show the complete scientific logic in one figure:

retired battery
→ short pulse U1–U21
→ state-free REL_RATIO representation
→ few-shot target adaptation
→ conformal uncertainty
→ OOD applicability-domain check
→ A/B/C/D screening or abstention

Why main text:
This is the conceptual novelty map of the paper.

Files:
- Fig01_Framework_Schematic.png
- Fig01_Framework_Schematic.pdf


## Figure 2 — Few-shot adaptation performance

Source:
Frozen Day21 figure.

Plot:
Mean SOH MAE versus labeled target-cell budget K.

Series:
- internal chemistry-shift evaluation
- overlap-excluded cross-dataset evaluation

Scientific message:
A small target-domain label budget materially reduces cross-domain SOH error.

Files:
- Fig02_FewShot_Internal_External.png
- Fig02_FewShot_Internal_External.pdf


## Figure 3 — Target-aware conformal coverage

Source:
Frozen Day21 figure.

Plot:
Empirical coverage versus labeled target-cell budget.

Reference:
Nominal 90% coverage line.

Scientific message:
Target-aware calibration approaches nominal coverage as target evidence increases.

Files:
- Fig03_Conformal_Coverage.png
- Fig03_Conformal_Coverage.pdf


## Figure 4 — Screening safety–decisiveness trade-off

Source:
Frozen Day21 figure.

Plot:
- observed false-safe rate
- decisive A/B/D assignment rate

versus target calibration size.

Scientific message:
Safety, interval calibration, and decision yield form a non-monotonic trade-off.

Files:
- Fig04_Screening_Calibration_Tradeoff.png
- Fig04_Screening_Calibration_Tradeoff.pdf


## Do NOT use as a main figure

### OOD ROC curves
Reason:
The tested KNN/Mahalanobis chemistry-separation result is essentially perfect,
while the operational threshold is highly conservative. A full ROC figure would
consume main-text space without adding as much scientific information as the
screening trade-off.

Recommendation:
Report OOD AUROC/AUPRC/FPR95 in a compact table or Supplementary Material.


### 1RC/2RC Digital-Twin plots
Do not include as validated main-paper evidence because defensible electrical
1RC/2RC identification was not achieved from the audited LFP23 profile.
"""

(OUT / "01_main_figure_plan.md").write_text(
    figure_plan,
    encoding="utf-8",
)

# ---------------------------------------------------------
# Table plan
# ---------------------------------------------------------

table_plan = """# Main Table Plan — FROZEN

## Table 1 — Dataset and validation design

Recommended columns:
- Dataset / cohort
- Chemistry
- Rated capacity
- Number of cells / groups
- Available signal representation
- Role in study
- Leakage / overlap handling

Rows:
- PulseBat NMC 2.1 Ah
- PulseBat LMO 10 Ah
- PulseBat NMC 21 Ah
- PulseBat LFP 35 Ah
- LFP23
- Bipolar709 overlap-excluded cohort

Purpose:
Make dataset heterogeneity and validation scope immediately clear.


## Table 2 — Core predictive and uncertainty performance

Use the frozen Day25 publication-table values:
- Internal K=0
- Internal K=20
- Internal K0→K20 reduction + p value
- K20 conformal PICP / MPIW
- External K=0
- External K=20
- External K0→K20 reduction + p value

Purpose:
Compactly report the headline numerical evidence.


## Table 3 — Screening sensitivity

Recommended if the journal allows three main tables.

Rows:
- 10 calibration cells
- 20 calibration cells
- 30 calibration cells

Columns:
- PICP
- MPIW
- decisive rate
- Class-C rate
- false-safe rate
- false-direct-reuse rate
- event counts

If the journal strongly limits tables:
Move Table 3 to Supplementary Material and retain Figure 4 in the main text.
"""

(OUT / "02_main_table_plan.md").write_text(
    table_plan,
    encoding="utf-8",
)

# ---------------------------------------------------------
# Equation plan
# ---------------------------------------------------------

equation_plan = r"""# Main Equation Plan — FROZEN

Use equations only where they define the method.
Do not add equations merely for appearance.

## Equation 1 — Capacity-based SOH definition

\[
SOH = \frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}}
\]

If reported as percent:

\[
SOH(\%) =
100\frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}}
\]

Purpose:
Define the prediction target.


## Equation 2 — Frozen state-free relative pulse representation

\[
r_i =
\frac{U_i-U_1}{|U_1|},
\qquad i=2,\ldots,21
\]

The model input vector is:

\[
\mathbf{x}
=
[r_2,r_3,\ldots,r_{21}]^{\mathsf T}
\]

Purpose:
This is the most important method equation in the paper.


## Equation 3 — Weighted few-shot adaptation objective

For model \(f_\theta\):

\[
\theta^\ast
=
\arg\min_{\theta}
\left[
\sum_{j\in\mathcal{S}}
\ell(f_\theta(\mathbf{x}_j),y_j)
+
\lambda_T
\sum_{k\in\mathcal{T}_K}
\ell(f_\theta(\mathbf{x}_k),y_k)
\right]
\]

where:
- \(\mathcal{S}\) = source training cells
- \(\mathcal{T}_K\) = K labeled target adaptation cells
- \(\lambda_T\) = target weighting factor

For the frozen implementation:
\[
\lambda_T = 8
\]

Purpose:
Mathematically explain weighted target adaptation.


## Equation 4 — Finite-sample conformal residual quantile

Calibration residual:

\[
s_i = |y_i-\hat y_i|
\]

For calibration size \(n_{\mathrm{cal}}\) and miscoverage \(\alpha\):

\[
k =
\min
\left[
n_{\mathrm{cal}},
\left\lceil
(n_{\mathrm{cal}}+1)(1-\alpha)
\right\rceil
\right]
\]

and

\[
\hat q_{1-\alpha}
=
s_{(k)}
\]

where \(s_{(k)}\) is the k-th ordered calibration residual.

Purpose:
This equation is essential because Day17 showed the finite-sample rank-resolution
effect when \(n_{\mathrm{cal}}=10\).


## Equation 5 — Conformal prediction interval

\[
\mathcal{C}_{1-\alpha}(\mathbf{x})
=
\left[
\hat y(\mathbf{x})-\hat q_{1-\alpha},
\;
\hat y(\mathbf{x})+\hat q_{1-\alpha}
\right]
\]

Purpose:
Defines the uncertainty interval used by screening.


## Equation 6 — Conservative screening / abstention rule

Let the interval be:

\[
[L,U] = \mathcal{C}_{1-\alpha}(\mathbf{x})
\]

Using the study's configurable SOH thresholds:

\[
\tau_A = 0.80,
\qquad
\tau_D = 0.70
\]

A compact decision rule is:

\[
g(L,U)=
\begin{cases}
A, & L\ge\tau_A,\\
B, & \tau_D\le L \;\text{and}\; U<\tau_A,\\
D, & U<\tau_D,\\
C, & \text{otherwise}.
\end{cases}
\]

Class C means additional diagnostics / abstention.

Important:
These thresholds are engineering assumptions for sensitivity analysis, not
universal regulatory thresholds.


# Equations NOT recommended in the main paper

## 1RC/2RC electrical equations
Do not present them as part of the validated main framework because the current
study did not obtain defensible identified \(R_0,R_1,C_1,R_2,C_2\) parameters.

If discussed, keep them in background / Supplementary Material and explicitly
state that they motivated surrogate physics auditing rather than a validated
Digital Twin.

## OOD formulas
Mahalanobis/KNN definitions are standard and do not need to occupy main-text
equation space unless the target journal asks for a highly formal Methods section.
They can be described in prose or Supplementary Material.
"""

(OUT / "03_main_equation_plan.md").write_text(
    equation_plan,
    encoding="utf-8",
)

# ---------------------------------------------------------
# Supplementary plan
# ---------------------------------------------------------

supp = """# Supplementary Material Plan

Recommended supplementary items:

## Figure S1
Raw-versus-normalized representation comparison from Day03.

## Figure/Table S2
State sensitivity:
REL_RATIO_NO_STATE versus state-containing representation from Day13.

## Table S1
Full chemistry-wise K={0,1,5,10,20} few-shot results.

## Table S2
Bootstrap confidence intervals and paired Wilcoxon statistics from Day15.

## Table S3
OOD AUROC, AUPRC, FPR95, acceptance, and abstention rates.

## Table S4
Day16 cell-level false-safe / false-direct-reuse forensic details.

## Table S5
Day17 finite-sample conformal rank audit.

## Table S6
Day19 corrected calibration-size sensitivity by chemistry and repeat.

## Figure/Table S7
ECM-inspired feature ablation from Day12.

## Supplementary Methods
- exact ExtraTrees hyperparameters
- source/target weighting
- repeated-seed protocol
- calibration allocation
- overlap-exclusion logic
- OOD threshold derivation

Keep LFP23 SOC-provenance / non-identifiability diagnostics supplementary unless
the journal reviewer specifically asks for the Digital-Twin investigation history.
"""

(OUT / "04_supplementary_plan.md").write_text(
    supp,
    encoding="utf-8",
)

# ---------------------------------------------------------
# Storyboard
# ---------------------------------------------------------

storyboard = """# Final Paper Storyboard

## Introduction
Problem:
Second-life batteries are heterogeneous and rapid screening must work with few
target labels.

Gap:
Prediction accuracy alone is insufficient under chemistry/dataset shift because
uncertainty, OOD behavior, and unsafe reuse decisions matter.

Contribution:
State-free pulse representation + few-shot adaptation + calibrated uncertainty +
OOD-aware abstention + conservative screening.


## Methods flow
Figure 1 → Eq. 1–6 → Table 1.


## Results flow

### Result 1
Normalized state-free pulse representation is the frozen transferable input.

### Result 2
Figure 2 + Table 2:
Few-shot adaptation reduces MAE internally and in overlap-excluded cross-dataset
evaluation.

### Result 3
Figure 3:
Target-aware conformal calibration recovers approximately nominal coverage.

### Result 4
OOD evidence:
Strong tested chemistry separation, but strict threshold is conservative.
Keep compact; do not oversell perfect AUROC.

### Result 5
Figure 4 + Table 3:
Screening demonstrates a safety–coverage–decisiveness trade-off.

### Result 6
Supplementary physics ablation:
ECM-inspired features are interpretable but do not outperform the frozen
REL_RATIO representation overall.


## Discussion
Emphasize:
- transferable normalized pulse shape
- value of small target label budgets
- target-aware uncertainty
- abstention as a safety mechanism
- calibration-size limitations
- overlap-excluded external scope
- no validated electrical Digital Twin

## Conclusion
Trustworthy few-shot pulse screening is supported.
Deployment certification and fully independent experimental validation remain
future work.
"""

(OUT / "05_paper_storyboard.md").write_text(
    storyboard,
    encoding="utf-8",
)

summary = {
    "day": "Day26",
    "purpose": "Freeze paper figure, table, equation, and supplementary architecture before journal formatting.",
    "model_retraining": False,
    "computational_results_status": "FROZEN",
    "main_figures": 4,
    "main_equations": 6,
    "recommended_main_tables": 3,
    "digital_twin_equations_main_text": False,
    "paper_architecture_status": "FROZEN_PENDING_USER_REVIEW",
    "output_dir": str(OUT),
}

(OUT / "06_run_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8",
)

print("\n=== DAY 26 COMPLETE ===")
print("Paper architecture freeze package created.")
print("Main figures: 4")
print("Main equations: 6")
print("Recommended main tables: 3")
print("1RC/2RC equations in main text: NO")
print("\nResults saved to:")
print(OUT)
print("\nSend me:")
print("01_main_figure_plan.md")
print("02_main_table_plan.md")
print("03_main_equation_plan.md")
print("04_supplementary_plan.md")
print("05_paper_storyboard.md")
print("06_run_summary.json")
print("and the terminal output.")
