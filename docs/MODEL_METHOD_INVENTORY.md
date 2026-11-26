# VERIFIED MODEL AND METHOD INVENTORY

## Supervised regression models explicitly evaluated
1. ExtraTreesRegressor
2. RandomForestRegressor
3. HistGradientBoostingRegressor

## Verified Day02 hyperparameters
ExtraTreesRegressor:
- n_estimators = 800
- random_state = 42
- n_jobs = -1
- min_samples_leaf = 2
- max_features = 0.8

RandomForestRegressor:
- n_estimators = 600
- random_state = 42
- n_jobs = -1
- min_samples_leaf = 2
- max_features = 0.8

HistGradientBoostingRegressor:
- learning_rate = 0.05
- max_iter = 600
- l2_regularization = 1e-3
- random_state = 42

## Few-shot adaptation methods explicitly audited
1. ZeroShot
2. BiasCal
3. WeightedRetrain

WeightedRetrain verified target sample weight:
8.0

K values:
0, 1, 5, 10, 20 unique labeled target cells.

## Uncertainty
Target-aware split conformal calibration.

## OOD methods explicitly audited
1. Mahalanobis distance
2. KNN distance
3. Isolation Forest

## Statistical analysis
- 10,000 bootstrap resamples
- paired one-sided Wilcoxon signed-rank test for K0 > K20

## Final representation
REL_RATIO_NO_STATE = (Ui-U1)/abs(U1), i=2..21

## Critical provenance rule
The exact final Day14 implementation source must come from the actual local Day14 script if present. This package does not invent missing final-pipeline source code.
