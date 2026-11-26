# Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries

**Authors:** [AUTHOR NAMES TO BE COMPLETED]  
**Affiliations:** [AFFILIATIONS TO BE COMPLETED]  
**Corresponding author:** [TO BE COMPLETED]

## Abstract

Second-life lithium-ion batteries exhibit substantial heterogeneity in chemistry, rated capacity, ageing history, and measurement domain, making rapid state-of-health (SOH) screening difficult when only limited target-domain labels are available. This study develops a trustworthy few-shot pulse-diagnostic framework that combines a frozen state-free relative pulse representation with target-domain adaptation, target-aware conformal uncertainty calibration, out-of-distribution (OOD) detection, and conservative abstention-oriented screening. The final predictor uses only processed pulse-voltage features and excludes SOC, SOCR, and SOE from the primary input, thereby avoiding ambiguity caused by nonuniform state descriptors across source datasets. Under internal chemistry shift, mean SOH mean absolute error (MAE) decreased from 8.268 percentage points (pp) at K=0 to 3.006 pp at K=20, corresponding to a 63.65% reduction (paired one-sided Wilcoxon p=0.000977). Target-aware split-conformal calibration achieved 90.93% empirical coverage at K=20 with a mean prediction-interval width of 19.90 pp. In overlap-excluded cross-dataset validation, 170 overlapping raw IDs were removed and 539 target cells retained; mean MAE decreased from 8.720 pp at K=0 to 3.468 pp at K=20, a 60.24% reduction (p=0.000977). A conservative uncertainty-aware screening analysis showed an observed false-safe rate of 0.236% with 10 calibration cells and zero observed false-safe events in the tested protocol-locked 20- and 30-cell configurations. These zero observed events are not interpreted as zero deployment risk. The results support few-shot pulse diagnostics with calibrated uncertainty, applicability-domain checking, and abstention for heterogeneous second-life battery screening, while fully independent experimental validation and a validated electrical 1RC/2RC Digital Twin remain future work.

**Keywords:** second-life lithium-ion battery; state of health; few-shot learning; pulse diagnostics; conformal prediction; uncertainty quantification; out-of-distribution detection; selective prediction; battery screening

---

## 1. Introduction

The rapid expansion of lithium-ion battery deployment is increasing the number of retired cells and modules that may retain sufficient performance for less demanding second-life applications [1]. Reuse can potentially extend useful battery life and reduce waste, but practical screening remains difficult because retired batteries are heterogeneous in chemistry, rated capacity, ageing trajectory, operating history, and measurement protocol [1,2]. Conventional full-capacity testing provides direct health information but is time-consuming, while rapid screening methods must trade diagnostic speed against generalizability, uncertainty, and decision safety.

Short-pulse voltage responses provide a compact diagnostic signal because the observed voltage dynamics reflect a combination of ohmic resistance, polarization, relaxation, and state-dependent electrochemical behavior [2,9]. However, a predictor trained in one battery population can fail when chemistry, capacity, or acquisition domain changes. This domain-shift problem is especially important for second-life batteries because target-domain labels are often scarce and because a false-safe reuse decision can be more consequential than an ordinary regression error.

Transfer-learning and domain-adaptation approaches have therefore attracted increasing attention for battery health estimation under limited target-domain information [3,4]. At the same time, prediction accuracy alone is insufficient for trustworthy screening. Conformal prediction provides a finite-sample framework for uncertainty calibration [5,6], while OOD detection and selective prediction motivate abstention when a test battery lies outside the model's supported applicability domain [7,8].

This study addresses these requirements jointly. Rather than assuming that all available state variables are physically equivalent across source datasets, the final model uses a state-free relative pulse representation derived from the processed U1-U21 voltage features. Prediction, uncertainty calibration, OOD detection, and reuse screening are evaluated as separate layers so that each component can be assessed without conflating regression accuracy with decision trustworthiness.

The main contributions are:

1. a frozen state-free relative pulse representation for heterogeneous battery transfer;
2. grouped few-shot target adaptation under chemistry and cross-dataset shift;
3. target-aware split-conformal uncertainty calibration;
4. OOD-aware abstention for tested held-out chemistry domains;
5. overlap-excluded cross-dataset validation with explicit leakage safeguards;
6. conservative A/B/C/D screening with false-safe analysis;
7. repeated-resampling robustness and statistical testing designed to prevent overclaiming.

**[Insert Figure 1 here]**

**Figure 1.** Trustworthy few-shot pulse-diagnostic framework for heterogeneous second-life lithium-ion batteries. Short-pulse turning-point voltages are transformed into the frozen state-free relative representation, followed by few-shot target adaptation, target-aware conformal calibration, OOD applicability-domain checking, and conservative A/B/C/D screening. Class C denotes abstention or additional diagnostics.

---

## 2. Materials and Data

### 2.1 PulseBat processed pulse-response dataset

The primary modeling resource was derived from the PulseBat retired-battery pulse-response dataset [2]. Four processed battery groups were used: 2.1 Ah NMC, 10 Ah LMO, 21 Ah NMC, and 35 Ah LFP. The processed files contain turning-point voltage features U1-U21. These U1-U21 labels are dataset-provided processed features; they were not newly defined by the present study.

The available state descriptor was not uniform across the four source groups: some files used SOCR while another used SOE. Because these variables cannot be assumed to be physically interchangeable, the frozen main predictor excludes SOC/SOCR/SOE and uses only the state-free pulse representation defined in Section 3.2.

**[Insert Figure 2 here]**

**Figure 2.** Pulse-feature semantics and cross-domain voltage heterogeneity in the study data. (a) Actual U1-U21 voltage features from an observed representative PulseBat sample; the secondary C-rate guide is schematic protocol information rather than reconstructed raw current. (b) Actual U1-U21 feature distributions across the four PulseBat domains, illustrating substantial domain heterogeneity in absolute voltage response.

### 2.2 External LFP23 time-series dataset

A separate second-life LFP dataset containing 23 cells was obtained from Zenodo (DOI: 10.5281/zenodo.18630889) [10] and audited as a potential physics-model source. It contains voltage, current, temperature, and SOC-like trajectories at approximately 1 s resolution. The current profiles did not provide sufficient pulse, step, and relaxation excitation for defensible identification of electrical 1RC/2RC parameters. The SOC trajectory was also found to be overwhelmingly consistent with Coulomb counting using a common approximately 6 Ah reference, so it was not treated as independent validation of an electrochemical state model.

### 2.3 Bipolar709 cross-dataset cohort

The Bipolar709 resource was obtained from Zenodo (DOI: 10.5281/zenodo.23634967) [11]. Its Step2 cell-level data provide a structurally compatible U1-U21-based target cohort for cross-dataset transfer. Because a substantial subset of raw IDs overlapped with the PulseBat source data, all overlapping raw IDs were removed before transfer evaluation. The resulting analysis is therefore described as **overlap-excluded cross-dataset validation**, not fully independent external validation.

### 2.4 Dataset roles and leakage safeguards

All adaptation, calibration, and evaluation operations were performed at the cell level. Target adaptation cells were disjoint from target evaluation cells. Cross-dataset overlap exclusion was performed using raw cell identifiers before external transfer metrics were calculated.

**[Insert Table 1 here]**

**Table 1.** Datasets, cohort roles, and validation safeguards. The table summarizes the PulseBat source cohort, the second-life LFP23 audit cohort, and the overlap-excluded Bipolar709 transfer cohort, including signal type, study role, and leakage/overlap controls.

---

## 3. Methods

### 3.1 SOH target

Fractional SOH was defined as

\[
y \equiv SOH =
\frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}}
\tag{1}
\]

and percentage SOH was reported as

\[
SOH(\%) = 100y.
\]

Prediction errors are reported in percentage points where appropriate.

### 3.2 Frozen state-free pulse representation

The final primary representation was

\[
r_i =
\frac{U_i-U_1}{|U_1|},
\qquad i=2,\ldots,21
\tag{2}
\]

with feature vector

\[
\mathbf{x}
=
[r_2,r_3,\ldots,r_{21}]^{\mathsf T}.
\]

Here, U1 serves as the pulse-sequence reference voltage. The representation removes the mixed SOCR/SOE state-variable ambiguity while retaining cross-domain predictive performance.

### 3.3 Model benchmarking

Three tree-based regressors were explicitly evaluated during model development: Extra Trees, Random Forest, and Histogram Gradient Boosting. The verified benchmark configurations included ExtraTreesRegressor with 800 trees, minimum leaf size 2, and max_features=0.8; RandomForestRegressor with 600 trees, minimum leaf size 2, and max_features=0.8; and HistGradientBoostingRegressor with learning rate 0.05, 600 iterations, and L2 regularization of 10^-3. Model development used cell/group-aware validation to prevent row-level leakage.

### 3.4 Grouped cross-domain validation

Models were evaluated under grouped holdout designs in which target battery groups or chemistries were excluded from source training. Grouping was performed at cell level so that repeated rows from the same cell could not be split across training and test sets.

### 3.5 Few-shot target adaptation

Target-domain adaptation was evaluated for

\[
K\in\{0,1,5,10,20\}
\]

unique labeled target cells. Development-stage strategies included zero-shot prediction, bias calibration, and weighted retraining. The frozen weighted target-adaptation formulation can be written as

\[
\theta^\ast
=
\arg\min_{\theta}
\left[
\sum_{j\in\mathcal{S}}
\ell(f_\theta(\mathbf{x}_j),y_j)
+
\lambda_T
\sum_{k\in\mathcal{T}_K}
\ell(f_\theta(\mathbf{x}_k),y_k)
\right]
\tag{3}
\]

where \(\mathcal{S}\) denotes source training cells, \(\mathcal{T}_K\) denotes the K labeled target adaptation cells, and the verified target sample weight was

\[
\lambda_T=8.
\]

Adaptation and evaluation cells were always disjoint.

### 3.6 Target-aware conformal uncertainty

Split-conformal prediction was applied at cell level. Calibration residuals were defined as

\[
s_i = |y_i-\hat y_i|.
\]

For \(n_{\mathrm{cal}}\) calibration samples and miscoverage level \(\alpha\), the finite-sample rank was

\[
k=
\min\left\{
n_{\mathrm{cal}},
\left\lceil
(n_{\mathrm{cal}}+1)(1-\alpha)
\right\rceil
\right\},
\qquad
\hat q_{1-\alpha}=s_{(k)}
\tag{4}
\]

where \(s_{(k)}\) denotes the k-th ordered residual. The resulting prediction interval was

\[
[L,U]
=
\left[
\hat y(\mathbf{x})-\hat q_{1-\alpha},
\hat y(\mathbf{x})+\hat q_{1-\alpha}
\right].
\tag{5}
\]

The primary uncertainty target was 90% empirical coverage. Source-only calibration substantially undercovered under chemistry shift, motivating target-aware calibration.

### 3.7 OOD detection and abstention

Mahalanobis distance, K-nearest-neighbor distance, and Isolation Forest were audited using source-domain cell-level pulse descriptors. OOD detection was treated as an applicability-domain test rather than as a direct estimator of SOH prediction error. Strong OOD evidence triggered abstention and additional diagnostics.

### 3.8 Overlap-excluded cross-dataset validation

Before PulseBat-to-Bipolar709 transfer evaluation, target raw IDs overlapping with the source cohort were excluded. Zero-shot and few-shot target adaptation were then evaluated on the retained 539-cell target cohort.

### 3.9 Conservative A/B/C/D screening

The screening policy used study-specific engineering thresholds

\[
\tau_A=0.80,
\qquad
\tau_D=0.70,
\]

with the decision rule

\[
g(L,U)=
\begin{cases}
A, & L\ge\tau_A,\\
B, & L\ge\tau_D \;\text{and}\; U<\tau_A,\\
D, & U<\tau_D,\\
C, & \text{otherwise}.
\end{cases}
\tag{6}
\]

Class A denotes direct-reuse candidates, B restricted-reuse candidates, D recycle candidates, and C additional diagnostics/abstention. An OOD trigger also routes the case to Class C. A false-safe event was defined as a true SOH below the recycle threshold while the model assigned a reuse class. The thresholds are sensitivity-analysis assumptions, not universal regulatory standards.

### 3.10 Statistical analysis

Repeated cell-level resampling was used to evaluate robustness. K=0 and K=20 performance were compared with paired one-sided Wilcoxon signed-rank tests. Bootstrap confidence intervals were obtained using 10,000 resamples. These statistics quantify robustness within the repeated-resampling design and do not substitute for independent experimental replication.

---

## 4. Results

### 4.1 Pulse-feature heterogeneity motivates a relative representation

The absolute U1-U21 feature distributions differed substantially across battery domains, reflecting chemistry-, capacity-, and dataset-dependent voltage offsets and response amplitudes. This heterogeneity explains the poor transferability of raw voltage features observed in early cross-domain testing. Normalizing each pulse feature relative to U1 reduced sensitivity to the absolute voltage level and provided a transferable state-free representation.

The final no-state representation was selected after explicit state-sensitivity analysis showed that removing the mixed SOCR/SOE descriptor did not materially degrade aggregate cross-domain accuracy. This result supports the use of relative pulse shape rather than a heterogeneous state label as the primary transfer feature.

### 4.2 Few-shot target adaptation

Using the frozen state-free representation, internal chemistry-shift mean SOH MAE decreased from **8.268 pp at K=0** to **3.006 pp at K=20**, corresponding to a **63.65% reduction**. The paired one-sided Wilcoxon signed-rank test gave **p=0.000977**, and the 95% bootstrap confidence interval for the mean absolute improvement was **5.130-5.403 pp**.

The full label-budget trend showed a progressive reduction in internal mean MAE from K=0 through K=20, indicating that even limited labeled target information can materially reduce source-to-target bias.

**[Insert Figure 3 here]**

**Figure 3.** Few-shot label-budget performance under internal chemistry shift and overlap-excluded cross-dataset transfer. Mean SOH MAE is shown versus the number of labeled target cells K. Limited target-domain labels substantially reduce cross-domain prediction error.

### 4.3 Target-aware uncertainty calibration

At K=20, target-aware split conformal calibration achieved **90.93% empirical coverage** with a mean prediction-interval width of **19.90 pp**. This result should be interpreted as approximately nominal 90% empirical coverage in the tested target-aware calibration design rather than as a universal coverage guarantee under arbitrary distribution shift.

Finite-sample audits further showed that small calibration sets can have coarse quantile resolution. In particular, different nominal confidence targets may collapse to the same empirical residual rank when the calibration set is very small.

### 4.4 Overlap-excluded cross-dataset transfer

After excluding **170 overlapping raw IDs**, **539 target cells** remained for Bipolar709 evaluation. Mean MAE decreased from **8.720 pp at K=0** to **3.468 pp at K=20**, corresponding to a **60.24% reduction**. The paired one-sided Wilcoxon test again gave **p=0.000977**.

These results demonstrate cross-dataset benefit from limited target adaptation after explicit overlap removal. They do not constitute fully independent external validation because the source and target resources are historically related.

**[Insert Table 2 here]**

**Table 2.** Core predictive and uncertainty results using the frozen state-free pulse representation. Internal chemistry-shift and overlap-excluded cross-dataset results are reported for zero-shot and few-shot adaptation together with the primary target-aware conformal uncertainty result.

### 4.5 Cell-level prediction and error structure

Cell-level predictions from the frozen screening-stage pipeline showed a strong relationship between predicted and true SOH while retaining chemistry-dependent error structure. Chemistry-wise absolute-error distributions provide a more informative view than a single aggregate MAE because they reveal whether residual error is concentrated in particular domains.

**[Insert Figure 4 here]**

**Figure 4.** Generalization and trustworthiness evidence from frozen cell-level predictions. (a) True versus predicted SOH by chemistry; the dashed diagonal denotes ideal agreement. (b) Chemistry-wise absolute SOH-error distributions. (c) Protocol-locked calibration-size sensitivity showing empirical coverage, decisiveness, and observed false-safe rate. The figure contains no generated or synthetic battery data and makes no unseen-SOC generative-generalization claim.

### 4.6 OOD detection and abstention

Mahalanobis and KNN detectors achieved perfect AUROC in the tested held-out chemistry experiments, while the strict source-derived threshold abstained on all unseen target chemistries. Isolation Forest also showed strong separation. These results demonstrate strong separation for the tested chemistry shifts but should not be generalized to all possible real-world OOD conditions or interpreted as direct estimators of SOH prediction error.

### 4.7 Screening sensitivity and calibration-size trade-off

With 10 target calibration cells, the conservative interval-based screening policy produced an observed false-safe rate of **0.236%**, corresponding to seven events. Under the protocol-locked 20-cell and 30-cell calibration configurations, the observed true false-safe count was zero. At 20 calibration cells, empirical coverage was **91.27%**; at 30 calibration cells, coverage was **89.02%**. Decisive A/B/D assignment rates were approximately **26.03%**, **22.33%**, and **29.16%** for 10, 20, and 30 calibration cells, respectively.

The trade-off was not monotonic: increasing the calibration set did not uniformly increase coverage, reduce interval width, and increase decisiveness at the same time. Therefore, calibration size should be interpreted as a label-burden, uncertainty, and screening-safety trade-off.

**[Insert Figure 5 here]**

**Figure 5.** Protocol-locked screening trustworthiness trade-off. Calibration size is compared with empirical coverage, decision yield, and observed false-safe behavior. Zero observed false-safe events in selected configurations are not interpreted as zero deployment risk.

**[Insert Table 3 here]**

**Table 3.** Protocol-locked screening sensitivity to target calibration-set size. Coverage, interval width, decisive rate, Class-C rate, observed false-safe rate, false-direct-reuse rate, and event counts are reported while holding the source-training and adaptation protocol fixed.

### 4.8 Physics-surrogate ablation

ECM-inspired pulse-response surrogate features were investigated using the known U1-U21 pulse semantics. These features provided chemistry-specific interpretability but performed worse than the frozen relative representation on average. They were therefore retained only as supplementary physics-guided evidence. The surrogate quantities are not identified \(R_0,R_1,C_1,R_2,C_2\) parameters and do not constitute a validated electrical Digital Twin.

---

## 5. Discussion

### 5.1 Why relative pulse shape transfers better than raw voltage

The central representation result is that absolute voltage level is strongly domain dependent, whereas relative pulse shape is more transferable. The U1-referenced normalization removes much of the chemistry- and capacity-dependent offset while preserving intra-pulse response structure. This reduces sensitivity to heterogeneous absolute voltage ranges and explains why the frozen REL_RATIO_NO_STATE representation outperformed raw cross-domain transfer.

### 5.2 Few-shot adaptation as domain-bias correction

The large K=0-to-K=20 improvement shows that only a small number of labeled target cells can materially correct systematic source-to-target bias. The same qualitative benefit appeared in both internal chemistry-shift and overlap-excluded cross-dataset evaluation. This supports limited-label adaptation, but it does not imply universal generalization without target data.

The label-budget curve is also operationally relevant. It shows the marginal value of collecting a small number of target labels rather than requiring a large fully labeled target cohort before useful screening is possible.

### 5.3 Why target-aware uncertainty is necessary

Source-only uncertainty calibration did not transfer reliably under chemistry shift. This is expected because prediction residuals change when the target domain differs from the source domain. Target-aware conformal calibration substantially improved empirical coverage, but the finite-sample rank audit showed that very small calibration sets have coarse uncertainty resolution. Thus, uncertainty calibration itself requires target evidence, not merely a source-trained predictor.

### 5.4 OOD detection and prediction accuracy are different questions

OOD detection answers whether a test battery resembles the model's supported source domain; it does not directly answer whether the numerical SOH error is small. The strong held-out-chemistry separation observed here therefore supports an abstention mechanism rather than a claim of universal error detection. This separation is important for safety-oriented screening because a model should be allowed to reject unsupported cases.

### 5.5 Safety, coverage, and decisiveness form a trade-off

The conservative screening rule routes uncertain cases to Class C instead of forcing a reuse/recycle decision. This reduces the risk of false-safe assignments but also lowers decisiveness. The calibration-size sensitivity analysis showed that coverage, interval width, observed false-safe behavior, and decision yield do not improve monotonically together. A practical screening system must therefore select calibration effort based on acceptable uncertainty and testing burden rather than maximizing a single metric.

### 5.6 Relation to prior transfer-learning studies

Previous battery transfer-learning studies have demonstrated that domain adaptation can improve SOH prediction across batteries with different characteristics [3,4]. The present work extends this direction by combining limited-label adaptation with state-free pulse normalization, target-aware conformal uncertainty, explicit OOD detection, abstention, overlap exclusion, and false-safe screening analysis. The contribution is therefore not simply another regression model, but a layered trustworthiness framework for second-life screening.

### 5.7 Scope of the physics-guided evidence

The present data support pulse-physics-inspired representation and ECM-surrogate analysis but not a validated electrical 1RC/2RC Digital Twin. The LFP23 time-series audit did not provide sufficient excitation for defensible electrical parameter identification. Accordingly, stronger Digital-Twin wording is intentionally excluded from the title and primary claims.

---

## 6. Limitations

This study has several important limitations.

First, the main predictive analysis relies on public or processed datasets rather than a fully original experimental cohort. This limits control over the original measurement protocol and prevents the present work from being described as fully independent experimental validation.

Second, the Bipolar709 transfer analysis required explicit removal of overlapping raw IDs. Although the retained 539-cell cohort provides meaningful cross-dataset evidence, it is appropriately described as overlap-excluded cross-dataset validation rather than fully independent external validation.

Third, the screening policy was evaluated through repeated-resampling sensitivity and not through deployment in an operational reuse facility. The low observed false-safe rate and the zero observed false-safe events in selected calibration configurations therefore do not establish zero risk or deployment certification.

Fourth, the available LFP23 profile lacked sufficient dynamic excitation for defensible electrical 1RC/2RC identification. No validated electrical Digital Twin is claimed.

Fifth, the screening thresholds of 0.80 and 0.70 SOH are configurable engineering assumptions used for method sensitivity. They should not be interpreted as universal regulatory or application standards.

Finally, independent Chroma-based proof-of-concept validation remains pending. Such testing would materially strengthen the evidence by adding an independently acquired experimental cohort.

---

## 7. Conclusion

A trustworthy state-free few-shot pulse-diagnostic framework was developed for heterogeneous second-life lithium-ion battery SOH screening. The frozen REL_RATIO_NO_STATE representation removed the SOCR/SOE ambiguity while retaining cross-domain predictive performance. Few-shot target adaptation substantially reduced SOH error under both internal chemistry shift and overlap-excluded cross-dataset transfer. Target-aware split-conformal calibration recovered approximately nominal 90% empirical coverage at K=20, while OOD detection provided an explicit abstention signal for the tested held-out chemistry domains.

The screening layer translated prediction intervals into conservative A/B/C/D decisions and routed ambiguous or unsupported cases to additional diagnostics rather than forcing a reuse assignment. Calibration-size sensitivity further demonstrated that coverage, decisiveness, interval width, and observed false-safe behavior form a non-monotonic trade-off.

The present contribution is best described as a trustworthy few-shot pulse-diagnostic and uncertainty-aware screening framework. It is not a deployment-certified system, a fully independent experimental validation, or a validated electrical Digital Twin. Future work should add independent experimental validation, raw pulse/HPPC testing with identifiable electrical parameters, and prospective screening evaluation before stronger deployment or Digital-Twin claims are made.

---

## Data Availability

The study uses public battery datasets described and cited in the manuscript. PulseBat-derived processed data were used for the primary modeling analysis. The LFP23 dataset is available through Zenodo under DOI 10.5281/zenodo.18630889, and the Bipolar709 resource is available through Zenodo under DOI 10.5281/zenodo.23634967. Derived analysis tables and figure-source CSV files should be archived with the final code release or supplementary repository at submission.

## Code Availability

The analysis pipeline, figure-generation scripts, final model/method inventory, and reproducibility assets should be archived in the authors' selected repository at submission or publication. The final repository identifier/DOI is **[TO BE COMPLETED]**.

## Author Contributions

[AUTHOR CONTRIBUTIONS TO BE COMPLETED BY THE AUTHORS]

## Funding

[FUNDING INFORMATION TO BE COMPLETED]

## Conflict of Interest

[CONFLICT-OF-INTEREST STATEMENT TO BE COMPLETED]

## Acknowledgements

[ACKNOWLEDGEMENTS TO BE COMPLETED IF APPLICABLE]

---

## References

[1] E. Martinez-Laserna, I. Gandiaga, E. Sarasketa-Zabala, J. Badeda, D.-I. Stroe, M. J. Swierczynski, and A. Goikoetxea, "Battery second life: Hype, hope or reality? A critical review of the state of the art," *Renewable and Sustainable Energy Reviews*, vol. 93, pp. 701-718, 2018. doi:10.1016/j.rser.2018.04.035.

[2] S. Tao, G. Ma, H. Yang, M. Lu, G. Wei, G. Zhou, and X. Zhang, "Generative learning assisted state-of-health estimation for sustainable battery recycling with random retirement conditions," *Nature Communications*, vol. 15, art. 10154, 2024. doi:10.1038/s41467-024-54454-0.

[3] G. Ma, S. Xu, T. Yang, Z. Du, L. Zhu, H. Ding, and Y. Yuan, "A Transfer Learning-Based Method for Personalized State of Health Estimation of Lithium-Ion Batteries," *IEEE Transactions on Neural Networks and Learning Systems*, 2022. doi:10.1109/TNNLS.2022.3176925.

[4] H. Li, X. Li, Y. Dong, H. Hang, Y. Tian, and J. Tian, "A cross-material lithium-ion battery state of health estimation method based on three-stage domain adaptation," *Energy*, article 139376, 2025. doi:10.1016/j.energy.2025.139376.

[5] A. N. Angelopoulos and S. Bates, "Conformal Prediction: A Gentle Introduction," *Foundations and Trends in Machine Learning*, vol. 16, pp. 494-591, 2023. doi:10.1561/2200000101.

[6] Y. Romano, E. Patterson, and E. J. Candès, "Conformalized Quantile Regression," *Advances in Neural Information Processing Systems*, vol. 32, pp. 3543-3553, 2019.

[7] D. Hendrycks and K. Gimpel, "A Baseline for Detecting Misclassified and Out-of-Distribution Examples in Neural Networks," *International Conference on Learning Representations (ICLR)*, 2017.

[8] Y. Geifman and R. El-Yaniv, "Selective Classification for Deep Neural Networks," *Advances in Neural Information Processing Systems*, vol. 30, pp. 4878-4887, 2017.

[9] X. Hu, S. Li, and H. Peng, "A comparative study of equivalent circuit models for Li-ion batteries," *Journal of Power Sources*, vol. 198, pp. 359-367, 2012. doi:10.1016/j.jpowsour.2011.10.013.

[10] M. Ji, H. Yue, Y. Shao, and Q. Zhu, "Second-life LFP battery dataset," Zenodo, 2026. doi:10.5281/zenodo.18630889.

[11] S. Tao, C. Xia, C. Liang, M. Lu, X. Zhang, G. Zhou, and C. Zou, "A rapid and scalable observable for battery capacity loss detection enabled by symmetric bipolar pulse perturbations," Zenodo dataset, 2026. doi:10.5281/zenodo.23634967.

---

## Supplementary Material Plan

The recommended supplementary package includes:

- Figure S1: raw-versus-normalized representation comparison;
- Figure/Table S2: state-sensitivity analysis comparing state-free and state-containing representations;
- Table S1: full chemistry-wise K={0,1,5,10,20} few-shot results;
- Table S2: bootstrap confidence intervals and paired Wilcoxon statistics;
- Table S3: OOD AUROC, AUPRC, FPR95, acceptance, and abstention rates;
- Table S4: false-safe / false-direct-reuse forensic details;
- Table S5: finite-sample conformal rank audit;
- Table S6: corrected calibration-size sensitivity by chemistry and repeat;
- Figure/Table S7: ECM-inspired feature ablation;
- Supplementary Methods: exact model hyperparameters, source/target weighting, repeated-seed protocol, calibration allocation, overlap-exclusion logic, and OOD threshold derivation.
