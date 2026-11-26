# Main Figure Plan — FROZEN

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
