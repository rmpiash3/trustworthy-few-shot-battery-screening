r"""
Day 25 — Final submission-package freeze
========================================

Purpose
-------
Assemble the literature-integrated Day24 manuscript with the frozen Day21
tables/figures into one final submission-preparation package.

No model retraining and no metric recomputation.

Inputs
------
D:\SecondLife_Research\Result\Day24_LiteratureIntegratedManuscript
D:\SecondLife_Research\Result\Day21_FinalEvidenceFreeze

Output
------
D:\SecondLife_Research\Result\Day25_FinalSubmissionPackage
"""

from pathlib import Path
import json
import shutil
import pandas as pd

ROOT = Path(r"D:\SecondLife_Research")
DAY24 = ROOT / "Result" / "Day24_LiteratureIntegratedManuscript"
DAY21 = ROOT / "Result" / "Day21_FinalEvidenceFreeze"
OUT = ROOT / "Result" / "Day25_FinalSubmissionPackage"
FIG = OUT / "figures"

OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

manuscript_src = DAY24 / "01_manuscript_literature_integrated.md"
core_table_src = DAY21 / "03_publication_table_core_results.csv"
screen_table_src = DAY21 / "04_publication_table_screening_sensitivity.csv"

required = [manuscript_src, core_table_src, screen_table_src]
missing = [str(p) for p in required if not p.exists()]
if missing:
    raise FileNotFoundError(
        "Missing required frozen files:\n" + "\n".join(missing)
    )

manuscript = manuscript_src.read_text(encoding="utf-8")
core = pd.read_csv(core_table_src)
screen = pd.read_csv(screen_table_src)

# ---------------------------------------------------------
# Publication tables
# ---------------------------------------------------------

core_md = core.to_markdown(index=False)
screen_md = screen.to_markdown(index=False)

tables_text = f"""# Publication Tables

## Table 1. Core predictive and uncertainty results

{core_md}

## Table 2. Protocol-locked screening sensitivity

{screen_md}
"""

(OUT / "01_publication_tables.md").write_text(
    tables_text,
    encoding="utf-8"
)

# ---------------------------------------------------------
# Copy final figures from Day21
# ---------------------------------------------------------

figure_names = [
    "Fig01_FewShot_Internal_External.png",
    "Fig01_FewShot_Internal_External.pdf",
    "Fig02_Conformal_Coverage.png",
    "Fig02_Conformal_Coverage.pdf",
    "Fig03_Screening_Calibration_Tradeoff.png",
    "Fig03_Screening_Calibration_Tradeoff.pdf",
]

copied = []
missing_figures = []

for name in figure_names:
    src = DAY21 / name
    dst = FIG / name

    if src.exists():
        shutil.copy2(src, dst)
        copied.append(name)
    else:
        missing_figures.append(name)

figure_inventory = pd.DataFrame({
    "figure_file": figure_names,
    "copied": [name in copied for name in figure_names],
})

figure_inventory.to_csv(
    OUT / "02_figure_inventory.csv",
    index=False
)

# ---------------------------------------------------------
# Submission statements
# ---------------------------------------------------------

statements = """# Submission Statements — Complete Before Submission

## Data Availability
The study uses public datasets described and cited in the manuscript.
The exact dataset identifiers, exclusions, and derived analysis files should be
reported in the final journal submission.

## Code Availability
The analysis code should be made available through the authors' selected
repository or archive at submission/publication, subject to institutional and
journal requirements.

## Author Contributions
[AUTHOR CONTRIBUTIONS TO BE COMPLETED BY THE AUTHORS]

## Funding
[FUNDING INFORMATION TO BE COMPLETED]

## Conflict of Interest
[CONFLICT OF INTEREST STATEMENT TO BE COMPLETED]

## Acknowledgements
[ACKNOWLEDGEMENTS TO BE COMPLETED IF APPLICABLE]

Important:
Do not invent any author, funding, institutional, or repository information.
"""
(OUT / "03_submission_statements.md").write_text(
    statements,
    encoding="utf-8"
)

# ---------------------------------------------------------
# Submission-ready manuscript copy with table/figure callouts
# ---------------------------------------------------------

appendix = """

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
"""

final_manuscript = manuscript.rstrip() + appendix + "\n"

(OUT / "04_final_manuscript_submission_copy.md").write_text(
    final_manuscript,
    encoding="utf-8"
)

# ---------------------------------------------------------
# Final integrity audit
# ---------------------------------------------------------

checks = {
    "unresolved_REF_placeholders": final_manuscript.count("[REF]"),
    "formfeed_present": "\x0c" in final_manuscript,
    "digital_twin_title_used": (
        final_manuscript.splitlines()[0].lower().find("digital-twin") >= 0
    ),
    "fully_independent_external_claim_present": (
        "fully independent external validation" in final_manuscript
        and "not fully independent external validation" not in final_manuscript
    ),
    "publication_tables_created": (
        (OUT / "01_publication_tables.md").exists()
    ),
    "all_six_figures_copied": len(copied) == 6,
}

audit = pd.DataFrame(
    [{"check": k, "value": v} for k, v in checks.items()]
)

audit.to_csv(
    OUT / "05_final_integrity_audit.csv",
    index=False
)

if checks["unresolved_REF_placeholders"] != 0:
    raise RuntimeError("Unresolved [REF] placeholders remain.")

if checks["formfeed_present"]:
    raise RuntimeError("Form-feed corruption detected.")

if checks["digital_twin_title_used"]:
    raise RuntimeError("Digital-Twin wording unexpectedly present in title.")

# Missing figures are reported, not fatal, because they can be copied manually.
checklist = f"""# Final Pre-Submission Checklist

- [x] Computational results frozen.
- [x] Literature-integrated manuscript available.
- [x] Publication tables generated.
- [{'x' if len(copied) == 6 else ' '}] Six Day21 figure files copied.
- [x] No [REF] placeholders.
- [x] No malformed form-feed equation.
- [x] Digital-Twin wording excluded from title.
- [ ] Choose final target journal.
- [ ] Apply journal-specific reference style.
- [ ] Apply journal-specific manuscript template.
- [ ] Fill Author Contributions.
- [ ] Fill Funding.
- [ ] Fill Conflict of Interest.
- [ ] Fill Acknowledgements if applicable.
- [ ] Final grammar/style review.
- [ ] Final similarity/originality check if required by institution/journal.
- [ ] Optional Chroma proof-of-concept before submission.

Missing figure files detected:
{chr(10).join(missing_figures) if missing_figures else "None"}
"""

(OUT / "06_final_pre_submission_checklist.md").write_text(
    checklist,
    encoding="utf-8"
)

summary = {
    "day": "Day25",
    "purpose": "Freeze final submission-preparation package.",
    "computational_results_status": "FROZEN",
    "model_retraining": False,
    "publication_tables_created": True,
    "figure_files_copied": copied,
    "missing_figure_files": missing_figures,
    "unresolved_REF_placeholders": checks["unresolved_REF_placeholders"],
    "digital_twin_title_status": "EXCLUDED",
    "remaining_work": (
        "journal selection, journal formatting, author declarations, final language review"
    ),
    "output_dir": str(OUT),
}

(OUT / "07_run_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 25 COMPLETE ===")
print("Final submission package assembled.")
print("Unresolved [REF] placeholders:", checks["unresolved_REF_placeholders"])
print("Form-feed corruption present:", checks["formfeed_present"])
print("Figures copied:", len(copied), "/ 6")
print("\nResults saved to:")
print(OUT)
print("\nSend me:")
print("01_publication_tables.md")
print("02_figure_inventory.csv")
print("03_submission_statements.md")
print("04_final_manuscript_submission_copy.md")
print("05_final_integrity_audit.csv")
print("06_final_pre_submission_checklist.md")
print("07_run_summary.json")
