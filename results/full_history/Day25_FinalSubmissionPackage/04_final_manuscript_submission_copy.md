# Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries

## Abstract

Second-life lithium-ion batteries exhibit substantial heterogeneity in chemistry,
capacity, ageing history, and measurement domain, making rapid state-of-health
(SOH) screening difficult when only limited target-domain labels are available.
This study develops a trustworthy few-shot pulse-diagnostic framework that uses
a frozen state-free relative pulse representation,
`REL_RATIO_NO_STATE = (Ui-U1)/abs(U1)`, combined with target-domain adaptation,
conformal uncertainty calibration, out-of-distribution (OOD) detection, and a
conservative abstention-oriented screening policy. Under internal chemistry
shift, mean SOH MAE decreased from 8.268 pp at K=0 to 3.006 pp at K=20,
corresponding to a 63.65% reduction (paired one-sided Wilcoxon p=0.000977).
Target-aware split-conformal calibration achieved 90.93% empirical coverage at
K=20 with a mean interval width of 19.90 pp. In overlap-excluded cross-dataset
validation, 170 overlapping raw IDs were removed and 539 target cells retained;
mean MAE decreased from 8.720 pp at K=0 to 3.468 pp at K=20, a 60.24%
reduction (p=0.000977). A conservative uncertainty-aware screening sensitivity
analysis showed low observed false-safe rates, with zero true false-safe events
in the tested protocol-locked 20- and 30-cell calibration configurations.
These zero observed events are not interpreted as zero deployment risk. The
results support trustworthy few-shot pulse diagnostics with calibrated
uncertainty and OOD-aware abstention for heterogeneous second-life battery
screening, while fully independent experimental validation and a validated
electrical 1RC/2RC Digital Twin remain future work.


## Keywords

Second-life lithium-ion battery; state of health; few-shot learning; pulse
diagnostics; conformal prediction; uncertainty quantification; out-of-distribution
detection; selective prediction; battery screening.

## 1. Introduction

The rapid growth of lithium-ion battery deployment is expected to create an
increasing stream of retired cells and modules that may retain sufficient
performance for less demanding second-life applications [1]. However,
second-life screening is complicated by heterogeneity in chemistry, rated
capacity, ageing trajectory, operating history, and measurement protocol [1,2].
Conventional capacity testing can provide reliable SOH information but is
time-consuming, while rapid diagnostic approaches must balance speed,
generalizability, and safety [2].

Short-pulse voltage responses offer a compact diagnostic signal because the
measured voltage trajectory reflects resistance, polarization, relaxation, and
state-dependent electrochemical behavior [2,9]. Yet a predictor trained on one
battery population can fail under chemistry or dataset shift. This problem is
especially important for second-life batteries, where target-domain labels may
be scarce and where unsafe reuse decisions are more consequential than ordinary
regression error [3,4].

This study therefore focuses on five linked requirements: transferable pulse
representation, few-shot target adaptation, calibrated predictive uncertainty,
OOD-aware abstention, and conservative reuse screening. Transfer learning and
domain-adaptation methods have been increasingly studied for battery SOH estimation
under limited target-domain labels [3,4], while conformal prediction provides a
general framework for finite-sample uncertainty calibration [5,6]. Selective
prediction and OOD detection further motivate abstention when a model operates
outside its trusted applicability domain [7,8]. Rather than assuming
that all available state variables are physically equivalent, the final model
uses a state-free relative pulse representation. The study further separates
prediction, uncertainty, OOD detection, and screening decisions so that each
layer can be evaluated independently.

The main contributions are:
1. a frozen state-free relative pulse representation for heterogeneous battery
   transfer;
2. grouped few-shot target adaptation under chemistry and cross-dataset shift;
3. target-aware split-conformal uncertainty calibration;
4. OOD-aware abstention for unseen chemistry domains;
5. overlap-excluded cross-dataset validation with explicit leakage safeguards;
6. a conservative A/B/C/D screening sensitivity analysis with false-safe metrics;
7. protocol-locked robustness and statistical analyses designed to prevent
   overclaiming.

## 2. Materials and Data

### 2.1 PulseBat processed pulse-response dataset

The primary modeling dataset was derived from the PulseBat retired-battery pulse-response resource [2]. It comprised four processed battery groups:
2.1 Ah NMC, 10 Ah LMO, 21 Ah NMC, and 35 Ah LFP. The processed representation
contained turning-point voltages U1-U21. The final predictor did not use SOC,
SOCR, or SOE because the source datasets did not use a uniform state variable.

### 2.2 External LFP23 time-series dataset

A separate second-life LFP dataset containing 23 cells was obtained from Zenodo (DOI: 10.5281/zenodo.18630889) [10] and audited as a potential physics-model source. It
contained raw charging voltage, current, and SOC-like trajectories at 1 s
resolution. However, the current profiles did not provide sufficient pulse,
step, and relaxation excitation for defensible 1RC/2RC electrical parameter
identification. Its SOC trajectory was also found to be overwhelmingly
consistent with Coulomb counting using a common approximately 6 Ah reference,
so it was not treated as independent validation of a state model.

### 2.3 Bipolar709 cross-dataset cohort

The Bipolar709 resource was obtained from Zenodo (DOI: 10.5281/zenodo.23634967) [11]. Its Step2 cell-level data provided a structurally compatible
cross-dataset target for U1-U21-based transfer evaluation. Because a substantial
subset of raw IDs overlapped with PulseBat, all overlapping raw IDs were
excluded before evaluation. This analysis is therefore described as
**overlap-excluded cross-dataset validation**, not fully independent external
validation.

### 2.4 Leakage safeguards

All adaptation, calibration, and evaluation operations were performed at the
cell level. Target adaptation cells were disjoint from target evaluation cells.
Cross-dataset overlap exclusion was performed using raw cell identifiers before
external transfer metrics were calculated.

## 3. Methods

### 3.1 Frozen state-free pulse representation

The final primary representation was:

\[
REL\_RATIO_i = \frac{U_i-U_1}{|U_1|}, \quad i=2,\ldots,21
\]

where U1 served as the pulse-sequence reference voltage. This representation was
selected after explicit state-sensitivity analysis showed that removing the
mixed SOCR/SOE state feature did not materially degrade cross-domain
performance.

### 3.2 Cross-domain validation

Models were evaluated using grouped holdout designs in which target battery
groups or chemistries were excluded from model training. Cell-level grouping was
used throughout to avoid row-level leakage.

### 3.3 Few-shot target adaptation

Target-domain adaptation was evaluated for K={0,1,5,10,20} labeled target
cells. Weighted retraining incorporated target adaptation samples with a higher
sample weight while preserving the source-domain training data. Adaptation and
test cells were always disjoint.

### 3.4 Target-aware conformal uncertainty

Split-conformal prediction was applied at the cell level following the finite-sample coverage logic of conformal inference [5,6]. Source-only
calibration substantially undercovered under chemistry shift, motivating
target-aware calibration. For K>0, labeled target cells were partitioned between
adaptation and calibration subsets. The primary uncertainty target was 90%
empirical coverage.

### 3.5 OOD detection and abstention

OOD detectors were fitted using source-domain cell-level pulse descriptors, consistent with the broader objective of identifying samples outside the training distribution [7].
Mahalanobis distance, KNN distance, and Isolation Forest were audited. OOD
detection was treated as a domain-shift detector rather than as a universal
predictor of SOH error. Under the conservative decision logic, strong OOD
evidence triggered abstention and additional diagnostics rather than automatic
reuse classification.

### 3.6 Overlap-excluded cross-dataset validation

Before PulseBat-to-Bipolar709 transfer evaluation, target raw IDs overlapping
with the source data were excluded. Zero-shot and few-shot target adaptation
were then evaluated on the retained target cohort.

### 3.7 Conservative A/B/C/D screening sensitivity

The screening architecture used configurable engineering SOH thresholds and a reject/abstain option consistent with selective-prediction principles [8]:
A for direct-reuse candidates, B for restricted-reuse candidates, D for
recycle candidates, and C for additional diagnostics. Prediction intervals that
crossed a screening threshold were assigned to Class C. A false-safe event was
defined as a true SOH below the recycle threshold while the model assigned a
reuse class. These threshold values were treated as engineering assumptions for
method sensitivity, not universal regulatory standards.

### 3.8 Statistical analysis

Repeated cell-level resampling was used to evaluate robustness. K=0 and K=20
performance were compared with paired one-sided Wilcoxon signed-rank tests.
Bootstrap confidence intervals were used for the mean improvement. These
statistics quantify robustness within the repeated-resampling design and do not
replace independent experimental replication.

## 4. Results

### 4.1 Internal few-shot adaptation
Using the frozen state-free relative pulse representation, mean SOH MAE decreased
from **8.268 pp at K=0** to **3.006 pp at K=20**, corresponding to
a **63.65% reduction**. The paired one-sided Wilcoxon signed-rank test
gave **p=0.000977**, while the 95% bootstrap confidence interval for the mean
absolute improvement was **5.130–5.403 pp**.

### 4.2 Target-aware uncertainty
At K=20, the split-conformal procedure achieved **90.93% empirical
coverage** with a mean prediction-interval width of **19.90 pp**.
This should be described as approximately nominal 90% coverage in the tested
target-aware calibration design, not as a universal coverage guarantee.

### 4.3 Overlap-excluded cross-dataset validation
After excluding **170 overlapping raw IDs**, **539 target
cells** remained for Bipolar709 evaluation. Mean MAE decreased from
**8.720 pp at K=0** to **3.468 pp at K=20**, a
**60.24% reduction** with paired one-sided Wilcoxon
**p=0.000977**.

Use the wording:
**overlap-excluded cross-dataset validation**

Do not write:
**fully independent external validation**

### 4.4 Screening sensitivity
The conservative interval-based screening policy exhibited an observed
false-safe rate of **0.236%** with 10 target calibration cells.
In the protocol-locked sensitivity analysis, the observed true false-safe rate
was **0.000%** with 20 calibration cells and **0.000%** with
30 calibration cells. At 20 calibration cells, empirical coverage was
**91.27%**.

These zero observed false-safe counts must not be interpreted as zero deployment
risk. The screening analysis is sensitivity evidence rather than certification.


### 4.5 OOD detection and abstention

Mahalanobis and KNN detectors achieved perfect AUROC in the tested held-out
chemistry experiments, while the strict source-derived threshold abstained on
all unseen target chemistries. This result demonstrates strong separation of the
tested chemistry shifts, but it should not be generalized to all real-world OOD
conditions or interpreted as a direct estimator of SOH prediction error.

### 4.6 Physics-surrogate ablation

ECM-inspired pulse-response surrogate features were investigated using the
known U1-U21 pulse semantics. Equivalent-circuit battery models are commonly evaluated through dynamic excitation and parameter-identification procedures [9]. These features provided chemistry-specific
interpretability and modest benefit in selected domains, but they performed
worse than the REL_RATIO representation on average. They were therefore retained
as supplementary physics-guided evidence rather than used as the primary
transfer representation. The surrogate quantities are not identified
R0/R1/C1/R2/C2 parameters and do not constitute a validated electrical Digital
Twin.

## 5. Discussion

### 5.1 Transferability of relative pulse shape

The raw voltage representation showed substantial cross-domain error, whereas
the relative pulse representation reduced sensitivity to absolute voltage
offsets associated with chemistry, capacity, and operating domain. This suggests
that normalized pulse shape contains more transferable degradation information
than absolute voltage level alone.

### 5.2 Few-shot adaptation as domain-bias correction

The strong K=0 to K=20 improvement indicates that a small number of labeled
target cells can materially correct systematic source-to-target bias. The result
was reproduced in both internal chemistry-shift and overlap-excluded
cross-dataset evaluation. The benefit should therefore be interpreted as
evidence for limited-label domain adaptation rather than universal
generalization without target labels.

### 5.3 Target-aware uncertainty calibration

Source-only conformal calibration undercovered substantially under chemistry
shift, demonstrating that nominal source-domain uncertainty does not
automatically transfer. Target-aware calibration restored approximately nominal
coverage by K=20. The finite-sample audits further showed that small calibration
sets have limited quantile resolution and can occasionally produce unstable
interval widths.

### 5.4 OOD-aware abstention

The OOD layer serves a different role from SOH regression. Strong OOD separation
identified when a target chemistry was outside the modeled source distribution,
allowing the pipeline to abstain rather than force a reuse decision. This
separation between prediction and applicability-domain assessment is important
for safety-oriented battery screening.

### 5.5 Safety–coverage–decisiveness trade-off

The conservative screening architecture routed a large fraction of ambiguous
cells to Class C. Increasing the target calibration set removed observed true
false-safe events in the tested protocol-locked sensitivity analysis, but
coverage, interval width, and decisiveness did not improve monotonically.
Therefore calibration size should be treated as a label-burden and safety
trade-off rather than a monotonic performance knob.

### 5.6 Scope of the physics-guided evidence

The available data supported pulse-physics-inspired representation and
ECM-surrogate audits, but not a validated electrical 1RC/2RC Digital Twin.
Accordingly, stronger Digital-Twin wording is intentionally excluded from the
current title and primary claims.

## 6. Limitations

The study has several important limitations. First, the main predictive
evaluation relies on public or processed datasets rather than a fully original
experimental cohort. Second, the Bipolar709 analysis required explicit removal
of overlapping raw IDs and therefore constitutes overlap-excluded cross-dataset
validation rather than fully independent external validation. Third, the
screening policy was evaluated through repeated-resampling sensitivity and is
not deployment certification. Fourth, the LFP23 time-series profile lacked
sufficient excitation for defensible electrical 1RC/2RC identification, and no
validated electrical Digital Twin is claimed. Finally, independent Chroma-based
proof-of-concept validation remains pending.

## 7. Conclusion

A trustworthy state-free few-shot pulse-diagnostic framework was developed for
heterogeneous second-life lithium-ion battery SOH screening. The frozen
REL_RATIO_NO_STATE representation removed the SOCR/SOE ambiguity while
retaining cross-domain performance. Few-shot adaptation substantially reduced
SOH prediction error in both internal chemistry-shift and overlap-excluded
cross-dataset evaluation, while target-aware conformal calibration recovered
approximately nominal 90% empirical coverage at K=20. OOD detection provided a
strong abstention signal for the tested held-out chemistry domains, and the
conservative screening layer routed a large fraction of uncertain cases to
additional diagnostics rather than forcing reuse decisions.

The study also identified important limitations. Cross-dataset validation was
overlap-excluded rather than fully independent, screening safety was assessed
through repeated-resampling sensitivity rather than deployment validation, and
no defensible electrical 1RC/2RC Digital Twin was identified from the available
time-series data. Accordingly, the current contribution is best described as a
trustworthy few-shot pulse-diagnostic and uncertainty-aware screening framework,
not as a deployment-certified or Digital-Twin-validated system. Future work
should include independent Chroma-based validation and raw pulse/HPPC testing
with identifiable electrical parameters before stronger experimental or
Digital-Twin claims are made.

## References

[1] E. Martinez-Laserna, I. Gandiaga, E. Sarasketa-Zabala, J. Badeda,
D.-I. Stroe, M. J. Swierczynski, and A. Goikoetxea, “Battery second life:
Hype, hope or reality? A critical review of the state of the art,”
*Renewable and Sustainable Energy Reviews*, vol. 93, pp. 701–718, 2018.
doi:10.1016/j.rser.2018.04.035.

[2] S. Tao, G. Ma, H. Yang, M. Lu, G. Wei, G. Zhou, and X. Zhang,
“Generative learning assisted state-of-health estimation for sustainable
battery recycling with random retirement conditions,”
*Nature Communications*, vol. 15, art. 10154, 2024.
doi:10.1038/s41467-024-54454-0.

[3] G. Ma, S. Xu, T. Yang, Z. Du, L. Zhu, H. Ding, and Y. Yuan,
“A Transfer Learning-Based Method for Personalized State of Health Estimation
of Lithium-Ion Batteries,”
*IEEE Transactions on Neural Networks and Learning Systems*, 2022.
doi:10.1109/TNNLS.2022.3176925.

[4] H. Li, X. Li, Y. Dong, H. Hang, Y. Tian, and J. Tian,
“A cross-material lithium-ion battery state of health estimation method based
on three-stage domain adaptation,” *Energy*, article 139376, 2025.
doi:10.1016/j.energy.2025.139376.

[5] A. N. Angelopoulos and S. Bates,
“Conformal Prediction: A Gentle Introduction,”
*Foundations and Trends in Machine Learning*, vol. 16,
pp. 494–591, 2023.
doi:10.1561/2200000101.

[6] Y. Romano, E. Patterson, and E. J. Candès,
“Conformalized Quantile Regression,”
*Advances in Neural Information Processing Systems*,
vol. 32, pp. 3543–3553, 2019.

[7] D. Hendrycks and K. Gimpel,
“A Baseline for Detecting Misclassified and Out-of-Distribution Examples
in Neural Networks,”
*International Conference on Learning Representations (ICLR)*, 2017.

[8] Y. Geifman and R. El-Yaniv,
“Selective Classification for Deep Neural Networks,”
*Advances in Neural Information Processing Systems*,
vol. 30, pp. 4878–4887, 2017.

[9] X. Hu, S. Li, and H. Peng,
“A comparative study of equivalent circuit models for Li-ion batteries,”
*Journal of Power Sources*, vol. 198, pp. 359–367, 2012.
doi:10.1016/j.jpowsour.2011.10.013.

[10] M. Ji, H. Yue, Y. Shao, and Q. Zhu,
“Second-life LFP battery dataset,” Zenodo, 2026.
doi:10.5281/zenodo.18630889.

[11] S. Tao, C. Xia, C. Liang, M. Lu, X. Zhang, G. Zhou, and C. Zou,
“A rapid and scalable observable for battery capacity loss detection enabled
by symmetric bipolar pulse perturbations,” Zenodo dataset, 2026.
doi:10.5281/zenodo.23634967.

---

## Submission Package Notes

### Frozen publication tables
See `01_publication_tables.md`.

### Frozen publication figures
See the `figures/` folder.

### Required author-supplied declarations
See `03_submission_statements.md`.

### Claim boundary
The manuscript must continue to avoid:
- fully independent external-validation wording,
- validated electrical 1RC/2RC Digital Twin wording,
- deployment-certification wording,
- zero-risk screening claims.

