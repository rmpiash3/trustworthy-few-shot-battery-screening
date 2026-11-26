# Day 21 — Final Computational Evidence Freeze

## Recommended current title

**Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries**

## Frozen primary representation

`REL_RATIO_NO_STATE = (Ui-U1)/abs(U1), i=2..21`

No SOC/SOCR/SOE is used in the main predictor.

## Internal few-shot evidence

- K=0 mean MAE: 8.268 pp
- K=20 mean MAE: 3.006 pp
- Mean K0→K20 reduction: 63.65%
- Paired one-sided Wilcoxon p: 0.000977
- 95% bootstrap improvement CI:
  5.130–
  5.403 pp

## Target-aware uncertainty

- K=20 empirical coverage:
  90.93%
- K=20 mean interval width:
  19.90 pp

## Overlap-excluded cross-dataset evidence

- Overlapping raw IDs excluded:
  170
- Target cells retained:
  539
- K=0 mean MAE:
  8.720 pp
- K=20 mean MAE:
  3.468 pp
- Mean K0→K20 reduction:
  60.24%
- Paired one-sided Wilcoxon p:
  0.000977

Correct wording:
**overlap-excluded cross-dataset validation**

Do not write:
**fully independent external validation**

## Screening sensitivity

### 10 calibration cells
- PICP: 90.93%
- false-safe rate: 0.236%
- total false-safe events: 7
- decisive rate: 26.03%

### 20 calibration cells
- PICP: 91.27%
- false-safe rate: 0.000%
- total false-safe events: 0
- decisive rate: 22.33%

### 30 calibration cells
- PICP: 89.02%
- false-safe rate: 0.000%
- total false-safe events: 0
- decisive rate: 29.16%

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
