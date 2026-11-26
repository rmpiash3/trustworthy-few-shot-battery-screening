# Results Section — Frozen Evidence

## Internal few-shot adaptation
Using the frozen state-free relative pulse representation, mean SOH MAE decreased
from **8.268 pp at K=0** to **3.006 pp at K=20**, corresponding to
a **63.65% reduction**. The paired one-sided Wilcoxon signed-rank test
gave **p=0.000977**, while the 95% bootstrap confidence interval for the mean
absolute improvement was **5.130–5.403 pp**.

## Target-aware uncertainty
At K=20, the split-conformal procedure achieved **90.93% empirical
coverage** with a mean prediction-interval width of **19.90 pp**.
This should be described as approximately nominal 90% coverage in the tested
target-aware calibration design, not as a universal coverage guarantee.

## Overlap-excluded cross-dataset validation
After excluding **170 overlapping raw IDs**, **539 target
cells** remained for Bipolar709 evaluation. Mean MAE decreased from
**8.720 pp at K=0** to **3.468 pp at K=20**, a
**60.24% reduction** with paired one-sided Wilcoxon
**p=0.000977**.

Use the wording:
**overlap-excluded cross-dataset validation**

Do not write:
**fully independent external validation**

## Screening sensitivity
The conservative interval-based screening policy exhibited an observed
false-safe rate of **0.236%** with 10 target calibration cells.
In the protocol-locked sensitivity analysis, the observed true false-safe rate
was **0.000%** with 20 calibration cells and **0.000%** with
30 calibration cells. At 20 calibration cells, empirical coverage was
**91.27%**.

These zero observed false-safe counts must not be interpreted as zero deployment
risk. The screening analysis is sensitivity evidence rather than certification.
