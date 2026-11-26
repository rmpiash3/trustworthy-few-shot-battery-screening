# Methods Reporting Checklist

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
