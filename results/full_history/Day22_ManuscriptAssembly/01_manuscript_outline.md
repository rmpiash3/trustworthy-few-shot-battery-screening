# Manuscript Outline

## Proposed Title
**Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries**

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
