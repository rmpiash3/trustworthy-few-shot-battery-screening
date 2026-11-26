r"""
Day 23 — Full manuscript draft assembly from frozen evidence
============================================================

Purpose
-------
Generate a full evidence-safe manuscript draft from the frozen Day21 evidence
and the Day22 manuscript assembly pack.

This script DOES NOT retrain models and DOES NOT invent literature citations.

Literature-dependent statements are marked with [REF] placeholders so that
references can be added in a later verified literature-integration stage.

Inputs
------
D:\SecondLife_Research\Result\Day21_FinalEvidenceFreeze
D:\SecondLife_Research\Result\Day22_ManuscriptAssembly

Outputs
-------
D:\SecondLife_Research\Result\Day23_FullManuscriptDraft

Files:
01_full_manuscript_draft.md
02_abstract.md
03_conclusion.md
04_literature_citation_placeholders.md
05_manuscript_completion_checklist.md
06_run_summary.json
"""

from pathlib import Path
import json

ROOT = Path(r"D:\SecondLife_Research")
DAY21 = ROOT / "Result" / "Day21_FinalEvidenceFreeze"
DAY22 = ROOT / "Result" / "Day22_ManuscriptAssembly"
OUT = ROOT / "Result" / "Day23_FullManuscriptDraft"
OUT.mkdir(parents=True, exist_ok=True)

required = [
    DAY21 / "05_results_evidence_freeze.md",
    DAY21 / "06_run_summary.json",
    DAY22 / "01_manuscript_outline.md",
    DAY22 / "02_results_section_evidence.md",
    DAY22 / "03_methods_reporting_checklist.md",
    DAY22 / "04_figure_captions.md",
    DAY22 / "05_table_captions.md",
    DAY22 / "06_limitations_and_claim_boundaries.md",
    DAY22 / "07_run_summary.json",
]

missing = [str(p) for p in required if not p.exists()]
if missing:
    raise FileNotFoundError(
        "Missing required frozen manuscript assets:\n" + "\n".join(missing)
    )

day21_summary = json.loads(
    (DAY21 / "06_run_summary.json").read_text(encoding="utf-8")
)

day22_summary = json.loads(
    (DAY22 / "07_run_summary.json").read_text(encoding="utf-8")
)

title = day21_summary["recommended_title"]

results_text = (
    DAY22 / "02_results_section_evidence.md"
).read_text(encoding="utf-8")

limits_text = (
    DAY22 / "06_limitations_and_claim_boundaries.md"
).read_text(encoding="utf-8")

abstract = f"""# Abstract

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
"""

conclusion = """# Conclusion

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
"""

manuscript = f"""# {title}

## Abstract

{abstract.replace("# Abstract\n\n","")}

## Keywords

Second-life lithium-ion battery; state of health; few-shot learning; pulse
diagnostics; conformal prediction; uncertainty quantification; out-of-distribution
detection; selective prediction; battery screening.

## 1. Introduction

The rapid growth of lithium-ion battery deployment is expected to create an
increasing stream of retired cells and modules that may retain sufficient
performance for less demanding second-life applications [REF]. However,
second-life screening is complicated by heterogeneity in chemistry, rated
capacity, ageing trajectory, operating history, and measurement protocol [REF].
Conventional capacity testing can provide reliable SOH information but is
time-consuming, while rapid diagnostic approaches must balance speed,
generalizability, and safety [REF].

Short-pulse voltage responses offer a compact diagnostic signal because the
measured voltage trajectory reflects resistance, polarization, relaxation, and
state-dependent electrochemical behavior [REF]. Yet a predictor trained on one
battery population can fail under chemistry or dataset shift. This problem is
especially important for second-life batteries, where target-domain labels may
be scarce and where unsafe reuse decisions are more consequential than ordinary
regression error [REF].

This study therefore focuses on five linked requirements: transferable pulse
representation, few-shot target adaptation, calibrated predictive uncertainty,
OOD-aware abstention, and conservative reuse screening. Rather than assuming
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

The primary modeling dataset comprised four PulseBat processed battery groups:
2.1 Ah NMC, 10 Ah LMO, 21 Ah NMC, and 35 Ah LFP. The processed representation
contained turning-point voltages U1-U21. The final predictor did not use SOC,
SOCR, or SOE because the source datasets did not use a uniform state variable.

### 2.2 External LFP23 time-series dataset

A separate LFP23 dataset was audited as a potential physics-model source. It
contained raw charging voltage, current, and SOC-like trajectories at 1 s
resolution. However, the current profiles did not provide sufficient pulse,
step, and relaxation excitation for defensible 1RC/2RC electrical parameter
identification. Its SOC trajectory was also found to be overwhelmingly
consistent with Coulomb counting using a common approximately 6 Ah reference,
so it was not treated as independent validation of a state model.

### 2.3 Bipolar709 cross-dataset cohort

The Bipolar709 Step2 cell-level data provided a structurally compatible
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
REL\_RATIO_i = \frac{{U_i-U_1}}{{|U_1|}}, \quad i=2,\ldots,21
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

Target-domain adaptation was evaluated for K={{0,1,5,10,20}} labeled target
cells. Weighted retraining incorporated target adaptation samples with a higher
sample weight while preserving the source-domain training data. Adaptation and
test cells were always disjoint.

### 3.4 Target-aware conformal uncertainty

Split-conformal prediction was applied at the cell level. Source-only
calibration substantially undercovered under chemistry shift, motivating
target-aware calibration. For K>0, labeled target cells were partitioned between
adaptation and calibration subsets. The primary uncertainty target was 90%
empirical coverage.

### 3.5 OOD detection and abstention

OOD detectors were fitted using source-domain cell-level pulse descriptors.
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

The screening architecture used configurable engineering SOH thresholds:
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

{results_text.replace("# Results Section — Frozen Evidence\n\n","")}

## 4.5 OOD detection and abstention

Mahalanobis and KNN detectors achieved perfect AUROC in the tested held-out
chemistry experiments, while the strict source-derived threshold abstained on
all unseen target chemistries. This result demonstrates strong separation of the
tested chemistry shifts, but it should not be generalized to all real-world OOD
conditions or interpreted as a direct estimator of SOH prediction error.

## 4.8 Physics-surrogate ablation

ECM-inspired pulse-response surrogate features were investigated using the
known U1-U21 pulse semantics. These features provided chemistry-specific
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

{conclusion.replace("# Conclusion\n\n","")}
"""

(OUT / "01_full_manuscript_draft.md").write_text(
    manuscript,
    encoding="utf-8"
)

(OUT / "02_abstract.md").write_text(
    abstract,
    encoding="utf-8"
)

(OUT / "03_conclusion.md").write_text(
    conclusion,
    encoding="utf-8"
)

refs = """# Literature Citation Placeholders

The following manuscript statements require externally verified literature
references before submission.

1. Growth of retired/second-life lithium-ion battery availability. [REF]
2. Typical second-life reuse motivation and circular-economy context. [REF]
3. Time/cost limitations of full capacity testing. [REF]
4. Short-pulse diagnostics and voltage-response interpretation. [REF]
5. Cross-chemistry/domain-shift challenges in battery ML. [REF]
6. Few-shot/domain-adaptation methods in battery health estimation. [REF]
7. Conformal prediction for uncertainty quantification under distribution shift. [REF]
8. OOD detection/selective prediction in safety-critical ML. [REF]
9. Existing second-life battery screening thresholds and reuse criteria, if cited. [REF]
10. Electrical ECM/1RC/2RC identification requirements and HPPC methodology. [REF]

Do not invent references. Add only verified literature in the next literature
integration stage.
"""
(OUT / "04_literature_citation_placeholders.md").write_text(
    refs,
    encoding="utf-8"
)

checklist = """# Manuscript Completion Checklist

- [x] Computational results frozen.
- [x] Final primary representation frozen.
- [x] Internal few-shot result frozen.
- [x] Target-aware UQ result frozen.
- [x] OOD claim boundary frozen.
- [x] Cross-dataset overlap exclusion frozen.
- [x] Screening sensitivity frozen.
- [x] Claim-readiness gate frozen.
- [x] Current defensible title selected.
- [ ] Add verified literature references.
- [ ] Add final dataset citations / DOIs.
- [ ] Add manuscript tables in journal format.
- [ ] Insert final Day21 figures.
- [ ] Add Data Availability statement.
- [ ] Add Code Availability statement.
- [ ] Add Author Contributions.
- [ ] Add Funding / Conflict of Interest statements.
- [ ] Select target journal and apply formatting.
- [ ] Independent Chroma proof-of-concept if available before submission.
- [ ] Only restore Digital-Twin wording if independently validated DT evidence is added.
"""
(OUT / "05_manuscript_completion_checklist.md").write_text(
    checklist,
    encoding="utf-8"
)

run_summary = {
    "day": "Day23",
    "purpose": "Generate a full evidence-safe manuscript draft from frozen Day21/Day22 assets.",
    "recommended_title": title,
    "computational_results_status": "FROZEN",
    "literature_references_status": "PLACEHOLDERS_ONLY",
    "model_retraining": False,
    "digital_twin_title_status": "NOT_YET_DEFENSIBLE",
    "independent_chroma_validation": "PENDING",
    "output_dir": str(OUT),
}

(OUT / "06_run_summary.json").write_text(
    json.dumps(run_summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 23 COMPLETE ===")
print("\nFull manuscript draft created.")
print("\nTitle:")
print(title)
print("\nLiterature citations: placeholders only; external verification still required.")
print("\nResults saved to:")
print(OUT)
print("\nSend me:")
print("01_full_manuscript_draft.md")
print("02_abstract.md")
print("03_conclusion.md")
print("04_literature_citation_placeholders.md")
print("05_manuscript_completion_checklist.md")
print("06_run_summary.json")
