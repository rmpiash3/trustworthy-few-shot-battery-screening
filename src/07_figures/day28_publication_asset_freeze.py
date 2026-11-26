r"""
Day 28 — Publication asset pack freeze
======================================

Purpose
-------
Create the final paper-ready figure/table/equation asset pack from already
verified frozen evidence.

No model retraining.
No metric recomputation.
No new scientific claims.

Inputs
------
D:\SecondLife_Research\Result\Day21_FinalEvidenceFreeze
D:\SecondLife_Research\Result\Day25_FinalSubmissionPackage
D:\SecondLife_Research\Result\Day27_FinalPaperArchitecture

Output
------
D:\SecondLife_Research\Result\Day28_PublicationAssets
"""

from pathlib import Path
import json
import shutil
import pandas as pd

ROOT = Path(r"D:\SecondLife_Research")
DAY21 = ROOT / "Result" / "Day21_FinalEvidenceFreeze"
DAY25 = ROOT / "Result" / "Day25_FinalSubmissionPackage"
DAY27 = ROOT / "Result" / "Day27_FinalPaperArchitecture"

OUT = ROOT / "Result" / "Day28_PublicationAssets"
FIG = OUT / "Main_Figures"
TAB = OUT / "Main_Tables"
SUPP = OUT / "Supplementary"

for p in [OUT, FIG, TAB, SUPP]:
    p.mkdir(parents=True, exist_ok=True)

required = [
    DAY27 / "Fig01_Framework_Schematic_FINAL.png",
    DAY27 / "Fig01_Framework_Schematic_FINAL.pdf",
    DAY27 / "01_final_main_equations.md",
    DAY27 / "02_final_paper_architecture.md",
    DAY25 / "01_publication_tables.md",
    DAY21 / "03_publication_table_core_results.csv",
    DAY21 / "04_publication_table_screening_sensitivity.csv",
]

missing = [str(p) for p in required if not p.exists()]
if missing:
    raise FileNotFoundError(
        "Missing required frozen asset(s):\n" + "\n".join(missing)
    )

# ---------------------------------------------------------
# Copy four final main figures
# ---------------------------------------------------------

figure_sources = {
    DAY27 / "Fig01_Framework_Schematic_FINAL.png":
        FIG / "Figure_1_Framework.png",
    DAY27 / "Fig01_Framework_Schematic_FINAL.pdf":
        FIG / "Figure_1_Framework.pdf",

    DAY27 / "paper_figures" / "Fig02_FewShot_Internal_External.png":
        FIG / "Figure_2_FewShot_Performance.png",
    DAY27 / "paper_figures" / "Fig02_FewShot_Internal_External.pdf":
        FIG / "Figure_2_FewShot_Performance.pdf",

    DAY27 / "paper_figures" / "Fig03_Conformal_Coverage.png":
        FIG / "Figure_3_Conformal_Coverage.png",
    DAY27 / "paper_figures" / "Fig03_Conformal_Coverage.pdf":
        FIG / "Figure_3_Conformal_Coverage.pdf",

    DAY27 / "paper_figures" / "Fig04_Screening_Calibration_Tradeoff.png":
        FIG / "Figure_4_Screening_Tradeoff.png",
    DAY27 / "paper_figures" / "Fig04_Screening_Calibration_Tradeoff.pdf":
        FIG / "Figure_4_Screening_Tradeoff.pdf",
}

for src, dst in figure_sources.items():
    if not src.exists():
        raise FileNotFoundError(src)
    shutil.copy2(src, dst)

# ---------------------------------------------------------
# Figure captions
# ---------------------------------------------------------

figure_captions = """# Final Main-Figure Captions

## Figure 1
**Trustworthy few-shot pulse-diagnostic framework for heterogeneous second-life
lithium-ion batteries.** Short-pulse turning-point voltages U1–U21 are converted
to the frozen state-free relative pulse representation. A small labeled
target-domain set supports few-shot model adaptation and target-aware conformal
calibration. An applicability-domain/OOD layer is evaluated separately from SOH
regression. The final interval-aware A/B/C/D screening layer assigns decisive
reuse/recycle classes only when uncertainty is sufficiently bounded; Class C
denotes abstention or additional diagnostics.

## Figure 2
**Few-shot adaptation under internal chemistry shift and overlap-excluded
cross-dataset transfer.** Mean SOH MAE is shown versus labeled target-cell
budget K using the frozen REL_RATIO_NO_STATE representation. The figure
summarizes both internal chemistry-shift evaluation and overlap-excluded
cross-dataset transfer, illustrating the reduction in target-domain error as
limited labeled target information is introduced.

## Figure 3
**Target-aware split-conformal coverage versus labeled target-cell budget.**
Empirical prediction-interval coverage is shown relative to the nominal 90%
target. The result demonstrates that target-aware calibration approaches
nominal empirical coverage as target-domain calibration evidence increases.
Coverage is reported for the tested calibration protocol and is not a universal
distribution-shift guarantee.

## Figure 4
**Safety–decisiveness sensitivity to target calibration-set size.** Observed
false-safe rate and decisive A/B/D assignment rate are shown for the
protocol-locked calibration-size sensitivity analysis. The results illustrate a
non-monotonic safety–coverage–decisiveness trade-off. Zero observed false-safe
events in selected calibration configurations must not be interpreted as zero
deployment risk.
"""

(OUT / "01_final_figure_captions.md").write_text(
    figure_captions, encoding="utf-8"
)

# ---------------------------------------------------------
# Main tables
# ---------------------------------------------------------

table1 = pd.DataFrame([
    {
        "Cohort": "PulseBat processed pulse-response data",
        "Chemistry / capacity": "NMC 2.1 Ah; LMO 10 Ah; NMC 21 Ah; LFP 35 Ah",
        "Cells / groups used": "270 grouped source cells",
        "Signal": "U1–U21 processed pulse turning points",
        "Role": "Primary source and internal chemistry-shift evaluation",
        "Leakage / scope control": "Cell/group-aware splits; no row-level leakage",
    },
    {
        "Cohort": "Second-life LFP23",
        "Chemistry / capacity": "LFP; 23 second-life cells",
        "Cells / groups used": "23 audited; 21 SOC-ready",
        "Signal": "Voltage, current, temperature, SOC-like trajectory (~1 s)",
        "Role": "SOC provenance / electrical-model readiness audit",
        "Leakage / scope control": "Not used as independent validation of the main SOH model",
    },
    {
        "Cohort": "Bipolar709 overlap-excluded target",
        "Chemistry / capacity": "LFP / LMO / NMC target cohort",
        "Cells / groups used": "539 retained target cells",
        "Signal": "Step2 U1–U21-compatible processed representation",
        "Role": "Overlap-excluded cross-dataset transfer evaluation",
        "Leakage / scope control": "170 overlapping raw IDs excluded before evaluation",
    },
])

table1.to_csv(TAB / "Table_1_Dataset_Validation_Design.csv", index=False)

core = pd.read_csv(DAY21 / "03_publication_table_core_results.csv")
core.to_csv(TAB / "Table_2_Core_Predictive_UQ_Results.csv", index=False)

screen = pd.read_csv(DAY21 / "04_publication_table_screening_sensitivity.csv")
screen.to_csv(TAB / "Table_3_Screening_Sensitivity.csv", index=False)

table_captions = """# Final Main-Table Captions

## Table 1
**Datasets, cohort roles, and validation safeguards.** The table summarizes the
primary PulseBat source cohort, the second-life LFP23 audit cohort, and the
overlap-excluded Bipolar709 transfer cohort, including signal type, study role,
and leakage/overlap controls.

## Table 2
**Core predictive and uncertainty results using the frozen state-free pulse
representation.** Internal chemistry-shift and overlap-excluded cross-dataset
results are reported for zero-shot and few-shot adaptation together with the
primary target-aware conformal uncertainty result.

## Table 3
**Protocol-locked screening sensitivity to target calibration-set size.**
Coverage, interval width, decisive rate, Class-C rate, observed false-safe rate,
false-direct-reuse rate, and event counts are reported while holding the
source-training and adaptation protocol fixed.
"""

(OUT / "02_final_table_captions.md").write_text(
    table_captions, encoding="utf-8"
)

# ---------------------------------------------------------
# Equation numbering / manuscript placement map
# ---------------------------------------------------------

equation_map = r"""# Final Equation Numbering and Placement

## Eq. (1) — SOH target
Place in Methods, immediately after defining ground-truth capacity.

\[
y \equiv SOH = \frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}},
\qquad
SOH(\%)=100y
\]

## Eq. (2) — State-free pulse representation
Place in the primary representation subsection.

\[
r_i=\frac{U_i-U_1}{|U_1|},
\qquad i=2,\ldots,21
\]

with

\[
\mathbf{x}=[r_2,r_3,\ldots,r_{21}]^{\mathsf T}
\]

## Eq. (3) — Weighted few-shot adaptation
Place in the few-shot adaptation subsection.

\[
\theta^\ast=
\arg\min_\theta
\left[
\sum_{j\in\mathcal{S}}\ell(f_\theta(\mathbf{x}_j),y_j)
+
\lambda_T
\sum_{k\in\mathcal{T}_K}\ell(f_\theta(\mathbf{x}_k),y_k)
\right]
\]

with \(\lambda_T=8\).

## Eq. (4) — Finite-sample conformal quantile
Place in the conformal-calibration subsection.

\[
s_i=|y_i-\hat y_i|
\]

\[
k=
\min\left\{
n_{\mathrm{cal}},
\left\lceil(n_{\mathrm{cal}}+1)(1-\alpha)\right\rceil
\right\},
\qquad
\hat q_{1-\alpha}=s_{(k)}
\]

## Eq. (5) — Conformal interval
Place immediately after Eq. (4).

\[
[L,U]=
[\hat y(\mathbf{x})-\hat q_{1-\alpha},
\hat y(\mathbf{x})+\hat q_{1-\alpha}]
\]

## Eq. (6) — Screening / abstention rule
Place in the screening subsection.

\[
g(L,U)=
\begin{cases}
A, & L\ge0.80,\\
B, & L\ge0.70 \;\text{and}\; U<0.80,\\
D, & U<0.70,\\
C, & \text{otherwise}.
\end{cases}
\]

Class C denotes abstention/additional diagnostics and also applies when the OOD
gate rejects the target as outside the tested applicability domain.

Important:
The 0.80 and 0.70 thresholds are study-specific engineering assumptions for
sensitivity analysis, not universal regulatory standards.
"""

(OUT / "03_final_equation_numbering.md").write_text(
    equation_map, encoding="utf-8"
)

# ---------------------------------------------------------
# Asset manifest
# ---------------------------------------------------------

manifest = {
    "day": "Day28",
    "purpose": "Freeze publication-ready main figures, tables, captions, and equation numbering.",
    "computational_results_status": "FROZEN",
    "model_retraining": False,
    "main_figures": 4,
    "figure_file_pairs_png_pdf": 4,
    "main_tables": 3,
    "main_equations": 6,
    "digital_twin_equations_main_text": False,
    "publication_assets_status": "FINAL_FROZEN",
    "next_stage": "target journal selection and journal-specific formatting",
    "output_dir": str(OUT),
}

(OUT / "04_run_summary.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)

print("\n=== DAY 28 COMPLETE ===")
print("Publication asset pack: FINAL FROZEN")
print("Main figures: 4 (PNG + vector PDF)")
print("Main tables: 3")
print("Main equations: 6")
print("Model retraining: NO")
print("\nResults saved to:")
print(OUT)
print("\nSend me:")
print("01_final_figure_captions.md")
print("02_final_table_captions.md")
print("03_final_equation_numbering.md")
print("04_run_summary.json")
print("Main_Tables folder CSVs")
print("and terminal output.")
