from pathlib import Path
import shutil

ROOT=Path(r"D:\SecondLife_Research")
SRC=ROOT/"Result"/"Day30_FullPaperFinalAssembly"
SUBMIT=ROOT/"SUBMIT"/"01_Manuscript"
SRC.mkdir(parents=True,exist_ok=True)
SUBMIT.mkdir(parents=True,exist_ok=True)

paper=SRC/"DAY30_FULL_PAPER_FINAL_ASSEMBLY.md"

if not paper.exists():
    raise FileNotFoundError(
        "Place DAY30_FULL_PAPER_FINAL_ASSEMBLY.md in "
        r"D:\SecondLife_Research\Result\Day30_FullPaperFinalAssembly"
    )

text=paper.read_text(encoding="utf-8")

required=[
    "## Abstract",
    "## 1. Introduction",
    "## 2. Materials and Data",
    "## 3. Methods",
    "## 4. Results",
    "## 5. Discussion",
    "## 6. Limitations",
    "## 7. Conclusion",
    "## Data Availability",
    "## Code Availability",
    "## References",
]

missing=[x for x in required if x not in text]
if missing:
    raise RuntimeError("Missing manuscript sections: "+", ".join(missing))

checks={
    "digital_twin_in_title":"digital-twin" in text.splitlines()[0].lower(),
    "fully_independent_external_claim":"constitutes fully independent external validation" in text.lower(),
    "zero_risk_claim":"zero deployment risk is guaranteed" in text.lower(),
    "figure_callouts":sum(text.count(f"[Insert Figure {i} here]") for i in range(1,6)),
    "table_callouts":sum(text.count(f"[Insert Table {i} here]") for i in range(1,4)),
    "equation_tags":sum(text.count(f"tag{{{i}}}") for i in range(1,7)),
}

if checks["digital_twin_in_title"]:
    raise RuntimeError("Unsupported Digital-Twin wording found in title.")

if checks["fully_independent_external_claim"]:
    raise RuntimeError("Unsafe independent-validation wording detected.")

if checks["zero_risk_claim"]:
    raise RuntimeError("Unsafe zero-risk wording detected.")

shutil.copy2(
    paper,
    SUBMIT/"FULL_PAPER_SUBMISSION_MASTER_DAY30.md"
)

(ROOT/"Result"/"Day30_FullPaperFinalAssembly"/"run_summary.txt").write_text(
    "\n".join([
        "DAY30 COMPLETE",
        f"Figure callouts: {checks['figure_callouts']}/5",
        f"Table callouts: {checks['table_callouts']}/3",
        f"Equation tags: {checks['equation_tags']}/6",
        "Digital-Twin title wording: NO",
        "Fully-independent external-validation claim: NO",
        "Zero-risk claim: NO",
        "Computational results changed: NO",
    ])+"\n",
    encoding="utf-8"
)

print("=== DAY30 COMPLETE ===")
print("Full manuscript assembled.")
print("Figures:",checks["figure_callouts"],"/ 5")
print("Tables:",checks["table_callouts"],"/ 3")
print("Equations:",checks["equation_tags"],"/ 6")
print("Copied to:",SUBMIT/"FULL_PAPER_SUBMISSION_MASTER_DAY30.md")
