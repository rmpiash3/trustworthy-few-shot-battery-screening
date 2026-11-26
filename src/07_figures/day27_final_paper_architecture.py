r"""
Day 27 — Final paper architecture refinement and freeze
======================================================

Purpose
-------
Refine the Day26 paper architecture before journal-specific formatting.

Changes
-------
1. Clarify SOH fraction versus SOH percent notation.
2. Clarify the conservative interval-based A/B/C/D screening rule.
3. Refine Figure 1 so target-label adaptation/calibration and OOD abstention
   are explicit.
4. Freeze the final main-paper figure/table/equation architecture.

No model retraining.
No metric recomputation.
No claim expansion.

Input
-----
D:\SecondLife_Research\Result\Day26_PaperArchitectureFreeze

Output
------
D:\SecondLife_Research\Result\Day27_FinalPaperArchitecture
"""

from pathlib import Path
import json
import shutil
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(r"D:\SecondLife_Research")
DAY26 = ROOT / "Result" / "Day26_PaperArchitectureFreeze"
OUT = ROOT / "Result" / "Day27_FinalPaperArchitecture"
FIG = OUT / "paper_figures"

OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

required = [
    DAY26 / "01_main_figure_plan.md",
    DAY26 / "02_main_table_plan.md",
    DAY26 / "03_main_equation_plan.md",
    DAY26 / "04_supplementary_plan.md",
    DAY26 / "05_paper_storyboard.md",
]

missing = [str(p) for p in required if not p.exists()]
if missing:
    raise FileNotFoundError(
        "Missing Day26 architecture file(s):\n" + "\n".join(missing)
    )

# =========================================================
# Refined Figure 1
# =========================================================

fig, ax = plt.subplots(figsize=(15, 6.0))
ax.set_xlim(0, 15)
ax.set_ylim(0, 6)
ax.axis("off")

boxes = [
    (0.35, 3.0, 1.75, 1.05, "Retired battery\npopulation"),
    (2.45, 3.0, 1.8, 1.05, "Short pulse\nU1–U21"),
    (4.60, 3.0, 2.1, 1.05, "State-free feature\nREL_RATIO"),
    (7.05, 3.0, 2.05, 1.05, "Few-shot SOH model\n+ target adaptation"),
    (9.45, 3.0, 2.05, 1.05, "Target-aware\nconformal interval"),
    (12.0, 3.0, 2.2, 1.05, "Screening decision\nA / B / C / D"),
]

for x, y, w, h, label in boxes:
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.05",
        linewidth=1.5,
        fill=False,
    )
    ax.add_patch(p)
    ax.text(
        x + w/2, y + h/2, label,
        ha="center", va="center", fontsize=10.7
    )

for i in range(len(boxes) - 1):
    x1 = boxes[i][0] + boxes[i][2]
    y1 = boxes[i][1] + boxes[i][3] / 2
    x2 = boxes[i+1][0]
    y2 = boxes[i+1][1] + boxes[i+1][3] / 2
    ax.add_patch(
        FancyArrowPatch(
            (x1 + 0.04, y1),
            (x2 - 0.04, y2),
            arrowstyle="->",
            mutation_scale=15,
            linewidth=1.35,
        )
    )

# Target-label branch
target_box = FancyBboxPatch(
    (6.95, 1.15), 2.25, 0.95,
    boxstyle="round,pad=0.05",
    linewidth=1.4,
    fill=False,
)
ax.add_patch(target_box)
ax.text(
    8.075, 1.625,
    "Few labeled target cells\nadaptation + calibration",
    ha="center", va="center", fontsize=10
)

ax.add_patch(
    FancyArrowPatch(
        (8.05, 2.10),
        (8.05, 2.95),
        arrowstyle="->",
        mutation_scale=14,
        linewidth=1.25,
    )
)
ax.add_patch(
    FancyArrowPatch(
        (8.75, 1.70),
        (10.15, 2.95),
        arrowstyle="->",
        mutation_scale=14,
        linewidth=1.25,
    )
)

# OOD branch
ood_box = FancyBboxPatch(
    (9.55, 0.25), 2.75, 0.9,
    boxstyle="round,pad=0.05",
    linewidth=1.4,
    fill=False,
)
ax.add_patch(ood_box)
ax.text(
    10.925, 0.70,
    "OOD applicability-domain check",
    ha="center", va="center", fontsize=10
)

ax.add_patch(
    FancyArrowPatch(
        (8.70, 3.0),
        (10.20, 1.15),
        arrowstyle="->",
        mutation_scale=14,
        linewidth=1.2,
    )
)

ax.add_patch(
    FancyArrowPatch(
        (11.60, 1.15),
        (12.85, 2.95),
        arrowstyle="->",
        mutation_scale=14,
        linewidth=1.2,
    )
)

ax.text(
    13.10, 2.35,
    "Class C = abstain /\nadditional diagnostics",
    ha="center", va="center", fontsize=9.5
)

ax.text(
    7.5, 5.35,
    "Trustworthy few-shot pulse diagnostics for heterogeneous second-life batteries",
    ha="center", va="center",
    fontsize=15, fontweight="bold",
)

ax.text(
    7.5, 4.85,
    "Prediction, calibration, applicability-domain checking, and reuse screening are evaluated separately",
    ha="center", va="center", fontsize=10.5
)

plt.tight_layout()

png = OUT / "Fig01_Framework_Schematic_FINAL.png"
pdf = OUT / "Fig01_Framework_Schematic_FINAL.pdf"

plt.savefig(png, dpi=300, bbox_inches="tight")
plt.savefig(pdf, bbox_inches="tight")
plt.close()

shutil.copy2(png, FIG / png.name)
shutil.copy2(pdf, FIG / pdf.name)

# Copy Day26 paper figures 2–4.
day26_fig = DAY26 / "paper_figures"

for name in [
    "Fig02_FewShot_Internal_External.png",
    "Fig02_FewShot_Internal_External.pdf",
    "Fig03_Conformal_Coverage.png",
    "Fig03_Conformal_Coverage.pdf",
    "Fig04_Screening_Calibration_Tradeoff.png",
    "Fig04_Screening_Calibration_Tradeoff.pdf",
]:
    src = day26_fig / name
    if not src.exists():
        raise FileNotFoundError(src)
    shutil.copy2(src, FIG / name)

# =========================================================
# Final equation plan
# =========================================================

equations = r"""# Final Main Equation Plan — APPROVED

Use only equations that define the implemented method.

## Equation 1 — SOH target

Use fractional SOH internally:

\[
y \equiv SOH =
\frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}}
\]

and report percentage SOH, when needed, as:

\[
SOH(\%) = 100y
\]

This avoids mixing a fraction-valued target with percentage-point error metrics.


## Equation 2 — State-free relative pulse representation

\[
r_i =
\frac{U_i-U_1}{|U_1|},
\qquad i=2,\ldots,21
\]

with input vector

\[
\mathbf{x}
=
[r_2,r_3,\ldots,r_{21}]^{\mathsf T}
\]


## Equation 3 — Weighted few-shot target adaptation

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

where the frozen implementation uses

\[
\lambda_T = 8
\]

This notation represents the implemented sample weighting:
source weight = 1, target-adaptation weight = 8.


## Equation 4 — Finite-sample conformal calibration

Calibration residual:

\[
s_i = |y_i-\hat y_i|
\]

For \(n_{\mathrm{cal}}\) calibration samples and miscoverage \(\alpha\),

\[
k =
\min\left\{
n_{\mathrm{cal}},
\left\lceil
(n_{\mathrm{cal}}+1)(1-\alpha)
\right\rceil
\right\}
\]

and

\[
\hat q_{1-\alpha}=s_{(k)}
\]

where \(s_{(k)}\) denotes the k-th ordered residual.


## Equation 5 — Conformal prediction interval

\[
[L,U]
=
\left[
\hat y(\mathbf{x})-\hat q_{1-\alpha},
\;
\hat y(\mathbf{x})+\hat q_{1-\alpha}
\right]
\]


## Equation 6 — Conservative screening / abstention rule

Using

\[
\tau_A=0.80,
\qquad
\tau_D=0.70,
\]

the interval-based decision rule is

\[
g(L,U)=
\begin{cases}
A, & L\ge\tau_A,\\
B, & L\ge\tau_D \;\text{and}\; U<\tau_A,\\
D, & U<\tau_D,\\
C, & \text{otherwise}.
\end{cases}
\]

Interpretation:

- A: interval entirely in the direct-reuse region;
- B: interval entirely in the restricted-reuse region;
- D: interval entirely below the recycle threshold;
- C: threshold-crossing uncertainty, OOD condition, or otherwise insufficient
  evidence for a decisive reuse/recycle assignment.

Important:
The screening thresholds are study-specific engineering assumptions for
sensitivity analysis, not universal regulatory standards.


# Excluded from the validated main framework

Do not use 1RC/2RC state equations as validated study equations.
The current evidence does not support identified electrical parameters
\(R_0,R_1,C_1,R_2,C_2\).

Mahalanobis and KNN formulas can remain in Supplementary Methods if desired.
"""

(OUT / "01_final_main_equations.md").write_text(
    equations,
    encoding="utf-8"
)

# =========================================================
# Final figure/table architecture
# =========================================================

architecture = """# Final Figure–Table Architecture — APPROVED

## Main Figures

### Figure 1
Final framework schematic.
Shows:
- retired battery population
- U1–U21 short pulse
- state-free REL_RATIO
- few-shot adaptation
- target-domain calibration
- conformal uncertainty
- OOD applicability-domain check
- A/B/C/D screening
- Class C abstention/additional diagnostics

### Figure 2
Few-shot SOH MAE versus K:
internal chemistry shift + overlap-excluded cross-dataset evaluation.

### Figure 3
Target-aware conformal empirical coverage versus target-label budget.

### Figure 4
Calibration-size safety–decisiveness trade-off.

Do not add more main figures unless journal layout requires restructuring.


## Main Tables

### Table 1
Dataset and validation design.

### Table 2
Core predictive + uncertainty performance.

### Table 3
Screening sensitivity.

If journal table limits are strict, move Table 3 to Supplementary Material.


## Main Equations
Six approved equations:
1. SOH target
2. REL_RATIO representation
3. weighted target adaptation
4. conformal residual quantile
5. conformal interval
6. screening/abstention rule


## Supplementary
Retain:
- raw vs normalized representation
- state-sensitivity ablation
- full K-shot chemistry-wise results
- bootstrap/Wilcoxon results
- OOD metrics
- false-safe forensic audit
- conformal rank-resolution audit
- corrected calibration-size sensitivity
- ECM-inspired feature ablation
- exact hyperparameters and protocol details
"""

(OUT / "02_final_paper_architecture.md").write_text(
    architecture,
    encoding="utf-8"
)

# =========================================================
# Reviewer-risk notes
# =========================================================

reviewer = """# Reviewer-Risk Notes

## 1. SOH notation
Use fractional SOH consistently in equations and percentage points only for
absolute SOH errors.

## 2. Few-shot objective
State explicitly that the mathematical weighting corresponds to sample weights
of 1 for source and 8 for target-adaptation samples.

## 3. Conformal validity
Do not claim universal 90% coverage under arbitrary distribution shift.
Use:
"approximately nominal empirical coverage in the tested target-aware
calibration design."

## 4. Screening thresholds
Do not describe 0.80 and 0.70 as universal standards.
They are configurable engineering thresholds used for sensitivity analysis.

## 5. Class C
Define Class C consistently as abstention/additional diagnostics, including
interval-threshold crossing and OOD-triggered abstention.

## 6. OOD
Do not over-emphasize perfect AUROC.
State that tested held-out chemistry separation was strong but the strict
operational threshold was conservative.

## 7. Digital Twin
Do not place 1RC/2RC equations in the validated method framework.
No validated electrical Digital Twin is claimed.
"""

(OUT / "03_reviewer_risk_notes.md").write_text(
    reviewer,
    encoding="utf-8"
)

summary = {
    "day": "Day27",
    "purpose": "Refine and approve final paper architecture before journal selection.",
    "model_retraining": False,
    "computational_results_status": "FROZEN",
    "main_figures": 4,
    "main_equations": 6,
    "main_tables": 3,
    "framework_schematic_refined": True,
    "soh_notation_clarified": True,
    "screening_rule_clarified": True,
    "digital_twin_equations_main_text": False,
    "paper_architecture_status": "FINAL_FROZEN",
    "next_stage": "target journal selection and journal-specific formatting",
    "output_dir": str(OUT),
}

(OUT / "04_run_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 27 COMPLETE ===")
print("Final paper architecture: FROZEN")
print("Main figures: 4")
print("Main equations: 6")
print("Main tables: 3")
print("Framework schematic refined: YES")
print("SOH notation clarified: YES")
print("Screening rule clarified: YES")
print("1RC/2RC equations in validated main framework: NO")
print("\nResults saved to:")
print(OUT)
print("\nSend me:")
print("01_final_main_equations.md")
print("02_final_paper_architecture.md")
print("03_reviewer_risk_notes.md")
print("04_run_summary.json")
print("and terminal output.")
