from pathlib import Path
import csv
import json
import re
import shutil
import tokenize
from io import BytesIO

ROOT = Path(r"D:\SecondLife_Research")
SUBMIT = ROOT / "SUBMIT"

DIRS = {
    "manuscript": SUBMIT / "01_Manuscript",
    "figures": SUBMIT / "02_Figures",
    "main_figures": SUBMIT / "02_Figures" / "Main_Figures",
    "plot_csv": SUBMIT / "02_Figures" / "Plot_Source_CSV",
    "captions": SUBMIT / "02_Figures" / "Captions_and_Briefs",
    "tables": SUBMIT / "03_Tables",
    "equations": SUBMIT / "04_Equations",
    "models": SUBMIT / "05_Models_and_Code",
    "model_code": SUBMIT / "05_Models_and_Code" / "Code_Only_No_Comments",
    "source_scripts": SUBMIT / "05_Models_and_Code" / "Verified_Source_Scripts",
    "supp": SUBMIT / "06_Supplementary",
    "submission": SUBMIT / "07_Submission_Documents",
    "audit": SUBMIT / "08_Provenance_Audit",
}

if SUBMIT.exists():
    shutil.rmtree(SUBMIT)

for p in DIRS.values():
    p.mkdir(parents=True, exist_ok=True)

copied = []
missing = []
warnings = []

def copy_if_exists(src, dst_dir, new_name=None, required=False):
    src = Path(src)
    if src.exists() and src.is_file():
        dst = Path(dst_dir) / (new_name or src.name)
        shutil.copy2(src, dst)
        copied.append((str(src), str(dst)))
        return dst
    if required:
        missing.append(str(src))
    return None

def copy_tree_files(src_dir, dst_dir, patterns=("*",)):
    src_dir = Path(src_dir)
    if not src_dir.exists():
        return []
    out = []
    for pat in patterns:
        for src in sorted(src_dir.glob(pat)):
            if src.is_file():
                dst = Path(dst_dir) / src.name
                shutil.copy2(src, dst)
                copied.append((str(src), str(dst)))
                out.append(dst)
    return out

def strip_python_comments(source_bytes):
    out = []
    try:
        tokens = list(tokenize.tokenize(BytesIO(source_bytes).readline))
        prev_type = tokenize.INDENT
        last_lineno = -1
        last_col = 0
        for tok in tokens:
            ttype, tstring, start, end, line = tok
            if ttype == tokenize.COMMENT:
                continue
            if ttype == tokenize.STRING and prev_type in (tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT) and start[1] == 0:
                prev_type = ttype
                continue
            if start[0] > last_lineno:
                last_col = 0
            if start[1] > last_col:
                out.append(" " * (start[1] - last_col))
            out.append(tstring)
            prev_type = ttype
            last_lineno = end[0]
            last_col = end[1]
        return "".join(out).encode("utf-8")
    except Exception:
        return source_bytes

def write_text(path, text):
    Path(path).write_text(text.rstrip() + "\n", encoding="utf-8")

DAY21 = ROOT / "Result" / "Day21_FinalEvidenceFreeze"
DAY25 = ROOT / "Result" / "Day25_FinalSubmissionPackage"
DAY27 = ROOT / "Result" / "Day27_FinalPaperArchitecture"
DAY28 = ROOT / "Result" / "Day28_PublicationAssets"
DAY28B = ROOT / "Result" / "Day28b_OwnData_PulseHeterogeneity"
DAY28C = ROOT / "Result" / "Day28c_DegradationRepresentationCorrelation"
DAY28E = ROOT / "Result" / "Day28e_FinalGeneralizationTrustworthiness"

manuscript_candidates = [
    DAY25 / "04_final_manuscript_submission_copy.md",
    ROOT / "Result" / "Day24_LiteratureIntegratedManuscript" / "01_manuscript_literature_integrated.md",
    ROOT / "Result" / "Day23_FullManuscriptDraft" / "01_full_manuscript_draft.md",
]

manuscript_src = next((p for p in manuscript_candidates if p.exists()), None)

if manuscript_src:
    copy_if_exists(
        manuscript_src,
        DIRS["manuscript"],
        "FULL_PAPER_SUBMISSION_MASTER.md",
        required=True
    )
else:
    missing.append("FULL MANUSCRIPT: Day25/Day24/Day23 manuscript not found")

for name in [
    "01_publication_tables.md",
    "03_submission_statements.md",
    "05_final_integrity_audit.csv",
    "06_final_pre_submission_checklist.md",
    "07_run_summary.json",
    "08_integrity_patch_note.md",
]:
    copy_if_exists(DAY25 / name, DIRS["manuscript"])

figure_map = [
    (
        DAY27 / "Fig01_Framework_Schematic_FINAL.png",
        "Figure_1_Framework.png"
    ),
    (
        DAY27 / "Fig01_Framework_Schematic_FINAL.pdf",
        "Figure_1_Framework.pdf"
    ),
    (
        DAY28B / "figures" / "Figure_PulseFeature_Heterogeneity_OwnData.png",
        "Figure_2_PulseFeature_Heterogeneity.png"
    ),
    (
        DAY28B / "figures" / "Figure_PulseFeature_Heterogeneity_OwnData.pdf",
        "Figure_2_PulseFeature_Heterogeneity.pdf"
    ),
    (
        DAY28 / "Main_Figures" / "Figure_2_FewShot_Performance.png",
        "Figure_3_FewShot_LabelBudget.png"
    ),
    (
        DAY28 / "Main_Figures" / "Figure_2_FewShot_Performance.pdf",
        "Figure_3_FewShot_LabelBudget.pdf"
    ),
    (
        DAY28E / "figures" / "Figure_Generalization_Trustworthiness_OwnData.png",
        "Figure_4_Generalization_Trustworthiness.png"
    ),
    (
        DAY28E / "figures" / "Figure_Generalization_Trustworthiness_OwnData.pdf",
        "Figure_4_Generalization_Trustworthiness.pdf"
    ),
    (
        DAY28 / "Main_Figures" / "Figure_4_Screening_Tradeoff.png",
        "Figure_5_Screening_Tradeoff.png"
    ),
    (
        DAY28 / "Main_Figures" / "Figure_4_Screening_Tradeoff.pdf",
        "Figure_5_Screening_Tradeoff.pdf"
    ),
]

for src, name in figure_map:
    copy_if_exists(src, DIRS["main_figures"], name)

expected_main = [
    "Figure_1_Framework.png",
    "Figure_1_Framework.pdf",
    "Figure_2_PulseFeature_Heterogeneity.png",
    "Figure_2_PulseFeature_Heterogeneity.pdf",
    "Figure_3_FewShot_LabelBudget.png",
    "Figure_3_FewShot_LabelBudget.pdf",
    "Figure_4_Generalization_Trustworthiness.png",
    "Figure_4_Generalization_Trustworthiness.pdf",
    "Figure_5_Screening_Tradeoff.png",
    "Figure_5_Screening_Tradeoff.pdf",
]

missing_figures = [
    x for x in expected_main
    if not (DIRS["main_figures"] / x).exists()
]

if missing_figures:
    write_text(
        DIRS["main_figures"] / "PENDING_ASSETS.txt",
        "The following final assets are not present locally and were NOT fabricated:\n\n"
        + "\n".join(f"- {x}" for x in missing_figures)
        + "\n\nRun the corresponding verified plotting stage first, then rerun this builder."
    )

plot_sources = [
    DAY28B / "01_data_audit.csv",
    DAY28B / "02_representative_real_row_U1_U21.csv",
    DAY28C / "01_schema_provenance_audit.csv",
    DAY28C / "02_raw_U1_U21_SOHCorr.csv",
    DAY28C / "03_raw_U1_U21_SOHCorr_n.csv",
    DAY28C / "04_REL_RATIO_SOHCorr.csv",
    DAY28C / "05_REL_RATIO_SOHCorr_n.csv",
    DAY28C / "06_correlation_summary.csv",
    DAY28E / "01_calibration_tradeoff_summary.csv",
    DAY28E / "02_chemistry_error_summary.csv",
    DAY28E / "03_scatter_evidence_used.csv",
    DAY21 / "03_publication_table_core_results.csv",
    DAY21 / "04_publication_table_screening_sensitivity.csv",
]

for p in plot_sources:
    copy_if_exists(p, DIRS["plot_csv"])

caption_sources = [
    DAY28 / "01_final_figure_captions.md",
    DAY28 / "02_final_table_captions.md",
    DAY28B / "03_proposed_caption.md",
    DAY28C / "07_proposed_caption.md",
    DAY28E / "04_proposed_caption.md",
]

for p in caption_sources:
    copy_if_exists(p, DIRS["captions"])

briefs = """# FIGURE BRIEFS

## Figure 1 — Framework
Shows the complete study flow from retired-battery pulse features through the state-free relative representation, few-shot target adaptation, target-aware conformal uncertainty, OOD applicability checking, and A/B/C/D screening. Class C denotes abstention/additional diagnostics.

## Figure 2 — Pulse-feature semantics and domain heterogeneity
Panel (a) uses an actual observed PulseBat U1–U21 row. The C-rate trace is schematic protocol guidance, not reconstructed measured current. Panel (b) shows actual U1–U21 distributions across LFP 35Ah, LMO 10Ah, NMC 2.1Ah, and NMC 21Ah.

## Figure 3 — Few-shot label-budget performance
Shows the reduction of SOH MAE as the number of labeled target cells increases from K=0 to K=20 for internal chemistry shift and overlap-excluded cross-dataset transfer.

## Figure 4 — Generalization and trustworthiness
Uses frozen cell-level prediction evidence only. Shows true-versus-predicted SOH, chemistry-wise absolute-error distributions, and corrected calibration-size trustworthiness diagnostics. No generated/synthetic battery data and no KLD claim.

## Figure 5 — Screening trade-off
Shows the protocol-locked trade-off among calibration size, empirical coverage, decisiveness, and observed false-safe events. Zero observed false-safe events are not interpreted as zero deployment risk.
"""
write_text(DIRS["captions"] / "FIGURE_BRIEFS.txt", briefs)

table_dir = DAY28 / "Main_Tables"
if table_dir.exists():
    copy_tree_files(table_dir, DIRS["tables"], ("*.csv",))

for p in [
    DAY28 / "02_final_table_captions.md",
    DAY25 / "01_publication_tables.md",
]:
    copy_if_exists(p, DIRS["tables"])

equation_sources = [
    DAY27 / "01_final_main_equations.md",
    DAY28 / "03_final_equation_numbering.md",
]

for p in equation_sources:
    copy_if_exists(p, DIRS["equations"])

equations = r"""# COMPLETE VERIFIED EQUATION INVENTORY

## Primary target
\[
y \equiv SOH=\frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}}
\]

\[
SOH(\%)=100y
\]

## State-free relative pulse representation
\[
r_i=\frac{U_i-U_1}{|U_1|},\qquad i=2,\ldots,21
\]

\[
\mathbf{x}=[r_2,r_3,\ldots,r_{21}]^{\mathsf T}
\]

## Weighted few-shot target adaptation
\[
\theta^\ast=
\arg\min_\theta
\left[
\sum_{j\in\mathcal S}\ell(f_\theta(\mathbf x_j),y_j)
+\lambda_T
\sum_{k\in\mathcal T_K}\ell(f_\theta(\mathbf x_k),y_k)
\right]
\]

\[
\lambda_T=8
\]

## Conformal residual
\[
s_i=|y_i-\hat y_i|
\]

## Finite-sample conformal rank
\[
k=
\min\left\{
n_{\mathrm{cal}},
\left\lceil(n_{\mathrm{cal}}+1)(1-\alpha)\right\rceil
\right\}
\]

\[
\hat q_{1-\alpha}=s_{(k)}
\]

## Conformal interval
\[
[L,U]=
[\hat y(\mathbf x)-\hat q_{1-\alpha},
\hat y(\mathbf x)+\hat q_{1-\alpha}]
\]

## Screening rule
\[
g(L,U)=
\begin{cases}
A,&L\ge0.80,\\
B,&L\ge0.70\ \mathrm{and}\ U<0.80,\\
D,&U<0.70,\\
C,&\mathrm{otherwise}.
\end{cases}
\]

## Mean absolute error
\[
MAE=\frac1N\sum_{i=1}^N|y_i-\hat y_i|
\]

## Root mean squared error
\[
RMSE=\sqrt{\frac1N\sum_{i=1}^N(y_i-\hat y_i)^2}
\]

## Coefficient of determination
\[
R^2=1-\frac{\sum_i(y_i-\hat y_i)^2}{\sum_i(y_i-\bar y)^2}
\]

## Relative MAE reduction
\[
\mathrm{Reduction}(\%)=
100\frac{MAE_{K=0}-MAE_{K}}{MAE_{K=0}}
\]

## Prediction interval coverage probability
\[
PICP=\frac1N\sum_{i=1}^N\mathbf 1(y_i\in[L_i,U_i])
\]

## Mean prediction interval width
\[
MPIW=\frac1N\sum_{i=1}^N(U_i-L_i)
\]

## False-safe rate
\[
FSR=
\frac{N(\mathrm{true\ SOH}<\tau_D\ \mathrm{and\ decision}\in\{A,B\})}
{N(\mathrm{evaluated})}
\]

## Pearson correlation used in the optional degradation-representation audit
\[
\rho_{XY}=
\frac{\mathrm{cov}(X,Y)}{\sigma_X\sigma_Y}
\]

## Mahalanobis distance used in OOD auditing
\[
D_M(\mathbf x)=
\sqrt{(\mathbf x-\boldsymbol\mu)^{\mathsf T}
\mathbf\Sigma^{-1}
(\mathbf x-\boldsymbol\mu)}
\]

No validated 1RC/2RC electrical Digital-Twin state equations are part of the supported main framework.
"""
write_text(DIRS["equations"] / "ALL_VERIFIED_RESEARCH_EQUATIONS.md", equations)

model_inventory = """# VERIFIED MODEL AND METHOD INVENTORY

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
"""
write_text(DIRS["models"] / "MODEL_METHOD_INVENTORY.md", model_inventory)

code_extra = """from sklearn.ensemble import ExtraTreesRegressor
model=ExtraTreesRegressor(n_estimators=800,random_state=42,n_jobs=-1,min_samples_leaf=2,max_features=0.8)
"""
write_text(DIRS["model_code"] / "extratrees_verified_day02.py", code_extra)

code_rf = """from sklearn.ensemble import RandomForestRegressor
model=RandomForestRegressor(n_estimators=600,random_state=42,n_jobs=-1,min_samples_leaf=2,max_features=0.8)
"""
write_text(DIRS["model_code"] / "random_forest_verified_day02.py", code_rf)

code_hgb = """from sklearn.ensemble import HistGradientBoostingRegressor
model=HistGradientBoostingRegressor(learning_rate=0.05,max_iter=600,l2_regularization=1e-3,random_state=42)
"""
write_text(DIRS["model_code"] / "hist_gradient_boosting_verified_day02.py", code_hgb)

code_features = """import numpy as np
def rel_ratio_no_state(X):
    X=np.asarray(X,dtype=float)
    u1=X[:,[0]]
    return (X[:,1:]-u1)/np.abs(u1)
"""
write_text(DIRS["model_code"] / "rel_ratio_no_state.py", code_features)

code_conformal = """import numpy as np
def conformal_quantile(y_true,y_pred,alpha=0.1):
    s=np.abs(np.asarray(y_true)-np.asarray(y_pred))
    n=len(s)
    k=min(n,int(np.ceil((n+1)*(1-alpha))))
    return np.sort(s)[k-1]
def conformal_interval(pred,q):
    pred=np.asarray(pred)
    return pred-q,pred+q
"""
write_text(DIRS["model_code"] / "split_conformal_core.py", code_conformal)

code_screen = """def screen_interval(lower,upper,tau_a=0.80,tau_d=0.70,ood=False):
    if ood:
        return "C"
    if lower>=tau_a:
        return "A"
    if lower>=tau_d and upper<tau_a:
        return "B"
    if upper<tau_d:
        return "D"
    return "C"
"""
write_text(DIRS["model_code"] / "screening_rule.py", code_screen)

source_patterns = [
    "day01*.py",
    "day02*.py",
    "day03*.py",
    "day04*.py",
    "day05*.py",
    "day06*.py",
    "day08*.py",
    "day12*.py",
    "day13*.py",
    "day14*.py",
    "day15*.py",
    "day16*.py",
    "day17*.py",
    "day18*.py",
    "day19*.py",
    "day20*.py",
    "day21*.py",
    "day24*.py",
    "day25*.py",
    "day26*.py",
    "day27*.py",
    "day28*.py",
]

found_scripts = []
for pat in source_patterns:
    for src in sorted(ROOT.glob(pat)):
        if not src.is_file():
            continue
        dst = DIRS["source_scripts"] / src.name
        shutil.copy2(src, dst)
        copied.append((str(src), str(dst)))
        found_scripts.append(src.name)
        try:
            stripped = strip_python_comments(src.read_bytes())
            (DIRS["model_code"] / src.name).write_bytes(stripped)
        except Exception as e:
            warnings.append(f"Could not strip comments from {src}: {e}")

if not any("day14" in x.lower() for x in found_scripts):
    write_text(
        DIRS["models"] / "FINAL_PIPELINE_SOURCE_REQUIRED.txt",
        "No Day14 final frozen-pipeline Python source was found in D:\\SecondLife_Research root.\n"
        "The final implementation is NOT reconstructed or fabricated here.\n"
        "Place the actual Day14 source script in the project root and rerun the SUBMIT builder."
    )

supp_sources = [
    ROOT / "Result" / "Day03_PhysicsNormalizedFeatures",
    ROOT / "Result" / "Day12_ECMInspired",
    ROOT / "Result" / "Day13_StateFreeRepresentation",
    ROOT / "Result" / "Day15_FinalStatistics",
    ROOT / "Result" / "Day16_ScreeningDecision",
    ROOT / "Result" / "Day17_ScreeningSafetySensitivity",
    ROOT / "Result" / "Day19_CorrectedCalibrationSensitivity",
]

supp_index = []
for sdir in supp_sources:
    if not sdir.exists():
        continue
    for src in sorted(sdir.glob("*.csv")):
        dst = DIRS["supp"] / f"{sdir.name}__{src.name}"
        shutil.copy2(src, dst)
        copied.append((str(src), str(dst)))
        supp_index.append(dst.name)
    for src in sorted(sdir.glob("*.json")):
        dst = DIRS["supp"] / f"{sdir.name}__{src.name}"
        shutil.copy2(src, dst)
        copied.append((str(src), str(dst)))
        supp_index.append(dst.name)

copy_if_exists(
    ROOT / "Result" / "Day26_PaperArchitectureFreeze" / "04_supplementary_plan.md",
    DIRS["supp"],
    "SUPPLEMENTARY_PLAN.md"
)

submission_docs = """# SUBMISSION DOCUMENTS STATUS

## Included or expected
- Full manuscript
- Main figures PNG
- Main figures vector PDF
- Plot source CSV
- Main tables CSV
- Figure captions and briefs
- Equation inventory
- Model/method inventory
- Verified source scripts
- Comment-free code copies
- Supplementary evidence
- Provenance audit

## To finalize after target journal is selected
- journal-formatted manuscript DOCX/PDF
- cover letter
- highlights if required
- graphical abstract if required
- author contribution statement
- funding statement
- conflict-of-interest declaration
- acknowledgements
- data availability statement
- code availability statement
- suggested reviewers if requested
"""
write_text(DIRS["submission"] / "SUBMISSION_DOCUMENTS_STATUS.md", submission_docs)

copy_if_exists(DAY25 / "03_submission_statements.md", DIRS["submission"])
copy_if_exists(DAY25 / "06_final_pre_submission_checklist.md", DIRS["submission"])

claim_boundary = """# CLAIM BOUNDARY

Allowed:
- state-free relative pulse representation
- few-shot target adaptation
- target-aware conformal uncertainty
- tested held-out-chemistry OOD separation
- OOD-aware abstention
- overlap-excluded cross-dataset validation
- conservative screening sensitivity
- repeated-resampling robustness

Do not claim:
- fully independent external validation
- validated electrical 1RC/2RC Digital Twin
- Digital-Twin-Assisted current title
- deployment certification
- zero deployment risk
- generated-data validation
- unseen-SOC generative synthesis
- VAE/KLD generative evidence
- fully original experimental validation
"""
write_text(DIRS["audit"] / "CLAIM_BOUNDARY.md", claim_boundary)

with (DIRS["audit"] / "copied_file_manifest.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["source", "submit_copy"])
    w.writerows(copied)

write_text(
    DIRS["audit"] / "missing_or_pending_assets.txt",
    "Missing/pending items were NOT fabricated.\n\n"
    + ("\n".join(f"- {x}" for x in missing + missing_figures) if (missing or missing_figures) else "None")
)

if warnings:
    write_text(
        DIRS["audit"] / "builder_warnings.txt",
        "\n".join(warnings)
    )
else:
    write_text(DIRS["audit"] / "builder_warnings.txt", "None")

readme = """# SUBMIT — MASTER SUBMISSION AND REPRODUCIBILITY PACKAGE

Project:
Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries

Folder map:
01_Manuscript
02_Figures
03_Tables
04_Equations
05_Models_and_Code
06_Supplementary
07_Submission_Documents
08_Provenance_Audit

Scientific status:
Computational results are frozen.

Important:
Any missing figure or final-pipeline source file is listed as pending and is not fabricated.
The package should be rebuilt after any pending verified asset is generated.
"""
write_text(SUBMIT / "00_README_FIRST.md", readme)

summary = {
    "package": "SUBMIT",
    "root": str(SUBMIT),
    "computational_results_status": "FROZEN",
    "copied_file_count": len(copied),
    "missing_required_or_pending_count": len(missing) + len(missing_figures),
    "found_source_scripts": found_scripts,
    "main_figure_expected_files": expected_main,
    "missing_main_figure_files": missing_figures,
    "model_code_policy": "verified exact snippets or actual local source only; no fabricated final pipeline code",
}

write_text(
    DIRS["audit"] / "package_summary.json",
    json.dumps(summary, indent=2)
)

zip_path = ROOT / "SUBMIT.zip"
if zip_path.exists():
    zip_path.unlink()

shutil.make_archive(
    str(zip_path.with_suffix("")),
    "zip",
    root_dir=ROOT,
    base_dir="SUBMIT"
)

print("\n=== SUBMIT PACKAGE COMPLETE ===")
print("Folder:", SUBMIT)
print("ZIP:", zip_path)
print("Copied files:", len(copied))
print("Pending/missing assets:", len(missing) + len(missing_figures))
print("Verified source scripts found:", len(found_scripts))
print("\nOpen first:")
print(SUBMIT / "00_README_FIRST.md")
print(DIRS["audit"] / "missing_or_pending_assets.txt")
print(DIRS["models"] / "MODEL_METHOD_INVENTORY.md")
