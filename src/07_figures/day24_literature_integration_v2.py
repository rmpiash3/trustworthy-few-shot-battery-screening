r"""
Day 24 v2 — Structural manuscript repair + verified literature integration
========================================================================

Fix in v2
---------
The original Day24 failed because re.sub() interpreted backslashes in the
replacement string, especially `\quad`, as regex replacement escapes.

This v2 uses a lambda replacement so the LaTeX string is inserted literally.

This stage DOES NOT retrain any model.

Input
-----
D:\SecondLife_Research\Result\Day23_FullManuscriptDraft\01_full_manuscript_draft.md

Output
------
D:\SecondLife_Research\Result\Day24_LiteratureIntegratedManuscript
"""

from pathlib import Path
import json
import re

ROOT = Path(r"D:\SecondLife_Research")
DAY23 = ROOT / "Result" / "Day23_FullManuscriptDraft"
OUT = ROOT / "Result" / "Day24_LiteratureIntegratedManuscript"
OUT.mkdir(parents=True, exist_ok=True)

src = DAY23 / "01_full_manuscript_draft.md"

if not src.exists():
    raise FileNotFoundError(
        f"Day23 manuscript not found:\n{src}"
    )

text = src.read_text(encoding="utf-8")

# =========================================================
# 1. Repair malformed LaTeX
# =========================================================

# Repair the form-feed corruption created from "\f" in "\frac".
text = text.replace("\x0crac", r"\frac")

latex_equation = (
    r"REL\_RATIO_i = \frac{U_i-U_1}{|U_1|}, "
    r"\quad i=2,\ldots,21"
)

# IMPORTANT:
# Use lambda so Python regex does NOT interpret \frac, \quad, \ldots
# as replacement-string escapes.
text = re.sub(
    r"REL\\_RATIO_i\s*=.*?i=2,\\ldots,21",
    lambda m: latex_equation,
    text,
    flags=re.S,
)

# Fallback for the exact corrupted/multiline equation if regex did not match.
if latex_equation not in text:
    equation_block_pattern = re.compile(
        r"REL\\_RATIO_i\s*=.*?21",
        flags=re.S,
    )
    text, n_sub = equation_block_pattern.subn(
        lambda m: latex_equation,
        text,
        count=1,
    )

    if n_sub == 0:
        raise RuntimeError(
            "Could not locate REL_RATIO equation for repair."
        )

# =========================================================
# 2. Repair Results subsection structure
# =========================================================

heading_replacements = {
    "## Internal few-shot adaptation":
        "### 4.1 Internal few-shot adaptation",

    "## Target-aware uncertainty":
        "### 4.2 Target-aware uncertainty",

    "## Overlap-excluded cross-dataset validation":
        "### 4.3 Overlap-excluded cross-dataset validation",

    "## Screening sensitivity":
        "### 4.4 Screening sensitivity",

    "## 4.5 OOD detection and abstention":
        "### 4.5 OOD detection and abstention",

    "## 4.8 Physics-surrogate ablation":
        "### 4.6 Physics-surrogate ablation",
}

for old, new in heading_replacements.items():
    text = text.replace(old, new)

# =========================================================
# 3. Replace [REF] placeholders with verified citation IDs
# =========================================================

citation_replacements = {
    "less demanding second-life applications [REF].":
        "less demanding second-life applications [1].",

    "measurement protocol [REF].":
        "measurement protocol [1,2].",

    "generalizability, and safety [REF].":
        "generalizability, and safety [2].",

    "state-dependent electrochemical behavior [REF].":
        "state-dependent electrochemical behavior [2,9].",

    "regression error [REF].":
        "regression error [3,4].",
}

for old, new in citation_replacements.items():
    text = text.replace(old, new)

needle = (
    "This study therefore focuses on five linked requirements: transferable pulse\n"
    "representation, few-shot target adaptation, calibrated predictive uncertainty,\n"
    "OOD-aware abstention, and conservative reuse screening."
)

replacement = (
    "This study therefore focuses on five linked requirements: transferable pulse\n"
    "representation, few-shot target adaptation, calibrated predictive uncertainty,\n"
    "OOD-aware abstention, and conservative reuse screening. Transfer learning and\n"
    "domain-adaptation methods have been increasingly studied for battery SOH estimation\n"
    "under limited target-domain labels [3,4], while conformal prediction provides a\n"
    "general framework for finite-sample uncertainty calibration [5,6]. Selective\n"
    "prediction and OOD detection further motivate abstention when a model operates\n"
    "outside its trusted applicability domain [7,8]."
)

text = text.replace(needle, replacement)

# =========================================================
# 4. Add dataset citations / DOI wording
# =========================================================

text = text.replace(
    "The primary modeling dataset comprised four PulseBat processed battery groups:",
    "The primary modeling dataset was derived from the PulseBat retired-battery "
    "pulse-response resource [2]. It comprised four processed battery groups:"
)

text = text.replace(
    "A separate LFP23 dataset was audited as a potential physics-model source.",
    "A separate second-life LFP dataset containing 23 cells was obtained from "
    "Zenodo (DOI: 10.5281/zenodo.18630889) [10] and audited as a potential "
    "physics-model source."
)

text = text.replace(
    "The Bipolar709 Step2 cell-level data provided a structurally compatible",
    "The Bipolar709 resource was obtained from Zenodo "
    "(DOI: 10.5281/zenodo.23634967) [11]. Its Step2 cell-level data provided "
    "a structurally compatible"
)

# =========================================================
# 5. Add methods literature anchors
# =========================================================

text = text.replace(
    "Split-conformal prediction was applied at the cell level.",
    "Split-conformal prediction was applied at the cell level following the "
    "finite-sample coverage logic of conformal inference [5,6]."
)

text = text.replace(
    "OOD detectors were fitted using source-domain cell-level pulse descriptors.",
    "OOD detectors were fitted using source-domain cell-level pulse descriptors, "
    "consistent with the broader objective of identifying samples outside the "
    "training distribution [7]."
)

text = text.replace(
    "The screening architecture used configurable engineering SOH thresholds:",
    "The screening architecture used configurable engineering SOH thresholds "
    "and a reject/abstain option consistent with selective-prediction "
    "principles [8]:"
)

text = text.replace(
    "known U1-U21 pulse semantics.",
    "known U1-U21 pulse semantics. Equivalent-circuit battery models are "
    "commonly evaluated through dynamic excitation and parameter-identification "
    "procedures [9]."
)

# =========================================================
# 6. Reference list
# =========================================================

references = r"""
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
"""

if "\n## References\n" in text:
    text = text.split("\n## References\n")[0].rstrip()

text = text.rstrip() + "\n\n" + references.strip() + "\n"

# =========================================================
# 7. Integrity checks
# =========================================================

remaining_refs = text.count("[REF]")
has_formfeed = "\x0c" in text

required_headings = [
    "### 4.1 Internal few-shot adaptation",
    "### 4.2 Target-aware uncertainty",
    "### 4.3 Overlap-excluded cross-dataset validation",
    "### 4.4 Screening sensitivity",
    "### 4.5 OOD detection and abstention",
    "### 4.6 Physics-surrogate ablation",
]

missing_headings = [
    h for h in required_headings
    if h not in text
]

if remaining_refs != 0:
    raise RuntimeError(
        f"Unresolved [REF] placeholders remain: {remaining_refs}"
    )

if has_formfeed:
    raise RuntimeError(
        "Form-feed corruption still present."
    )

if latex_equation not in text:
    raise RuntimeError(
        "Corrected REL_RATIO equation not found."
    )

if missing_headings:
    raise RuntimeError(
        "Missing repaired Results headings: "
        + "; ".join(missing_headings)
    )

# =========================================================
# 8. Write outputs
# =========================================================

manuscript_path = OUT / "01_manuscript_literature_integrated.md"
manuscript_path.write_text(
    text,
    encoding="utf-8"
)

(OUT / "02_verified_references.md").write_text(
    references.strip() + "\n",
    encoding="utf-8"
)

citation_map = """# Citation Map

[1] Second-life reuse context / heterogeneity / circular-economy motivation.
[2] PulseBat dataset and retired-battery pulse diagnostics.
[3] Battery SOH transfer learning with limited target information.
[4] Cross-material/domain adaptation for lithium-ion battery SOH.
[5] General conformal prediction and finite-sample uncertainty quantification.
[6] Conformalized prediction intervals / quantile-regression framework.
[7] Out-of-distribution detection.
[8] Selective prediction / reject option.
[9] Li-ion equivalent-circuit modeling and dynamic parameter identification.
[10] Second-life LFP23 dataset DOI.
[11] Bipolar709 / symmetric bipolar perturbation dataset DOI.
"""

(OUT / "03_citation_map.md").write_text(
    citation_map,
    encoding="utf-8"
)

repairs = r"""# Structural Repairs Applied

1. Repaired corrupted LaTeX:
   `REL_RATIO_i = \frac{U_i-U_1}{|U_1|}, \quad i=2,\ldots,21`

2. Repaired Results subsection numbering:
   - 4.1 Internal few-shot adaptation
   - 4.2 Target-aware uncertainty
   - 4.3 Overlap-excluded cross-dataset validation
   - 4.4 Screening sensitivity
   - 4.5 OOD detection and abstention
   - 4.6 Physics-surrogate ablation

3. Replaced all `[REF]` placeholders with numbered citations.

4. Added dataset DOI wording:
   - LFP23: 10.5281/zenodo.18630889
   - Bipolar709: 10.5281/zenodo.23634967

5. Preserved frozen claim boundaries:
   - no validated electrical 1RC/2RC Digital Twin claim,
   - no fully independent external-validation claim,
   - no deployment-certification claim.
"""

(OUT / "04_structural_repairs.md").write_text(
    repairs,
    encoding="utf-8"
)

checklist = """# Remaining Submission Checklist

- [x] Computational evidence frozen.
- [x] Manuscript structure created.
- [x] Abstract and conclusion drafted.
- [x] Core literature citations integrated.
- [x] Dataset DOI wording integrated.
- [x] Equation rendering repaired.
- [x] Results subsection numbering repaired.
- [ ] Confirm exact bibliographic style of target journal.
- [ ] Insert final Day21 figures into manuscript.
- [ ] Insert publication tables.
- [ ] Add Data Availability statement.
- [ ] Add Code Availability statement.
- [ ] Add Author Contributions statement.
- [ ] Add Funding statement.
- [ ] Add Conflict of Interest statement.
- [ ] Add acknowledgements where applicable.
- [ ] Run final grammar/style review.
- [ ] Optional independent Chroma proof-of-concept before submission.
- [ ] Only restore Digital-Twin wording if new validated DT evidence is added.
"""

(OUT / "05_submission_remaining_checklist.md").write_text(
    checklist,
    encoding="utf-8"
)

summary = {
    "day": "Day24_v2",
    "purpose": (
        "Repair manuscript structure and integrate literature citations."
    ),
    "source": str(src),
    "regex_replacement_fix": (
        "lambda replacement used so LaTeX backslashes are literal"
    ),
    "unresolved_REF_placeholders": remaining_refs,
    "equation_formfeed_present": has_formfeed,
    "results_numbering_repaired": True,
    "reference_count": 11,
    "dataset_dois_added": [
        "10.5281/zenodo.18630889",
        "10.5281/zenodo.23634967",
    ],
    "computational_results_status": "FROZEN",
    "digital_twin_title_status": "NOT_YET_DEFENSIBLE",
    "output_dir": str(OUT),
}

(OUT / "06_run_summary.json").write_text(
    json.dumps(
        summary,
        indent=2
    ),
    encoding="utf-8"
)

print("\n=== DAY 24 v2 COMPLETE ===")
print("Regex replacement bug: FIXED")
print("Structural repair: PASS")
print("Remaining [REF] placeholders:", remaining_refs)
print("Malformed form-feed equation present:", has_formfeed)
print("Results headings repaired:", len(required_headings))
print("References integrated:", 11)

print("\nResults saved to:")
print(OUT)

print("\nSend me:")
print("01_manuscript_literature_integrated.md")
print("02_verified_references.md")
print("03_citation_map.md")
print("04_structural_repairs.md")
print("05_submission_remaining_checklist.md")
print("06_run_summary.json")
