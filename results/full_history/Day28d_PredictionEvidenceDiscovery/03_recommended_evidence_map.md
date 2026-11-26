# Recommended Evidence Map

## Why this audit exists

The supplied literature figure evaluates generated-versus-tested data under unseen SOC.
That scientific claim is not part of the frozen current study and must not be reproduced.

The correct own-study analogue should use actual frozen cell-level prediction evidence:

1. true SOH versus predicted SOH;
2. error/residual distributions;
3. domain-wise or K-wise generalization;
4. conformal interval / coverage diagnostics where available.

## Candidate files containing BOTH true target and prediction columns

- score=16: `D:\SecondLife_Research\Result\Day05_Uncertainty\03_uq_cell_predictions.csv` (K=True, domain=True, interval=True, OOD=False)
- score=16: `D:\SecondLife_Research\Result\Day18_CalibrationSizeSensitivity\02_cell_calibration_size_predictions.csv` (K=True, domain=True, interval=True, OOD=False)
- score=16: `D:\SecondLife_Research\Result\Day18_CalibrationSizeSensitivity\07_false_safe_cell_details.csv` (K=True, domain=True, interval=True, OOD=False)
- score=16: `D:\SecondLife_Research\Result\Day19_CorrectedCalibrationSensitivity\01_cell_corrected_calibration_predictions.csv` (K=True, domain=True, interval=True, OOD=False)
- score=16: `D:\SecondLife_Research\Result\Day19_CorrectedCalibrationSensitivity\08_false_safe_cell_details.csv` (K=True, domain=True, interval=True, OOD=False)
- score=14: `D:\SecondLife_Research\Result\Day16_ScreeningDecision\01_cell_screening_predictions.csv` (K=False, domain=True, interval=True, OOD=False)
- score=14: `D:\SecondLife_Research\Result\Day17_ScreeningSafetySensitivity\01_cell_policy_sensitivity_predictions.csv` (K=False, domain=True, interval=True, OOD=False)
- score=14: `D:\SecondLife_Research\Result\Day17_ScreeningSafetySensitivity\06_false_safe_cell_details.csv` (K=False, domain=True, interval=True, OOD=False)
- score=12: `D:\SecondLife_Research\Result\Day02_CrossDomain\04_cross_domain_predictions.csv` (K=False, domain=True, interval=False, OOD=False)
- score=12: `D:\SecondLife_Research\Result\Day03_PhysicsNormalizedFeatures\03_feature_set_predictions.csv` (K=False, domain=True, interval=False, OOD=False)
- score=12: `D:\SecondLife_Research\Result\Day04_FewShot\03_fewshot_predictions.csv` (K=False, domain=True, interval=False, OOD=False)
- score=12: `D:\SecondLife_Research\Result\Day1_PulseBat_Baseline_Results\test_predictions.csv` (K=False, domain=True, interval=False, OOD=False)

## Recommended future figure only after evidence file verification

Panel (a): true SOH vs predicted SOH for frozen K=0 and K=20 cases.
Panel (b): absolute-error distributions across internal and overlap-excluded external evaluation.
Panel (c): chemistry/domain-wise error reduction or conformal interval diagnostics.

This would provide a strong generalization/trustworthiness figure without making
any generative-data or unseen-SOC synthesis claim.
