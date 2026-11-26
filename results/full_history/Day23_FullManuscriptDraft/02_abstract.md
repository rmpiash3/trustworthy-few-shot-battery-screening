# Abstract

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
