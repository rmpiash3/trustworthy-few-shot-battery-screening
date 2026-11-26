# Final Paper Storyboard

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
