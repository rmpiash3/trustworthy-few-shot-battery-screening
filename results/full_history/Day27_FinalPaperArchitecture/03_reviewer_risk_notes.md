# Reviewer-Risk Notes

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
