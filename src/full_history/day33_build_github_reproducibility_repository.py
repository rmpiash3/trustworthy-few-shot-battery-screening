from pathlib import Path
import csv, hashlib, json, platform, re, shutil, subprocess, sys
from datetime import datetime, timezone

ROOT = Path(r"D:\SecondLife_Research")
OWNER = "rmpiash"
REPO_NAME = "trustworthy-few-shot-battery-screening"
OUT_BASE = ROOT / "GitHub_Release"
REPO = OUT_BASE / REPO_NAME

INCLUDE_RAW_DATA = False
RESET_EXISTING = True
MAX_FILE_MB = 95

if RESET_EXISTING and REPO.exists():
    shutil.rmtree(REPO)

folders = {
    "src_full": REPO/"src"/"full_history",
    "src_data": REPO/"src"/"01_data_and_representation",
    "src_model": REPO/"src"/"02_models_and_fewshot",
    "src_uq": REPO/"src"/"03_uncertainty",
    "src_ood": REPO/"src"/"04_ood",
    "src_screen": REPO/"src"/"05_screening",
    "src_stats": REPO/"src"/"06_statistics",
    "src_fig": REPO/"src"/"07_figures",
    "src_submit": REPO/"src"/"08_submission_tools",
    "data_raw": REPO/"data"/"raw",
    "data_prov": REPO/"data"/"provenance",
    "results_full": REPO/"results"/"full_history",
    "results_core": REPO/"results"/"frozen_core",
    "fig_main": REPO/"figures"/"main",
    "fig_supp": REPO/"figures"/"supplementary",
    "tables": REPO/"tables",
    "supp": REPO/"supplementary",
    "docs": REPO/"docs",
    "manuscript": REPO/"manuscript_support",
    "env": REPO/"environment",
    "audit": REPO/"audit",
}
for p in folders.values():
    p.mkdir(parents=True, exist_ok=True)

manifest, missing, skipped, warnings = [], [], [], []

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip()+"\n", encoding="utf-8")

def copy_file(src, dst_dir, new_name=None, category=""):
    src = Path(src)
    if not src.exists() or not src.is_file():
        return None
    mb = src.stat().st_size/(1024*1024)
    if mb > MAX_FILE_MB:
        skipped.append({"source":str(src),"size_mb":round(mb,3)})
        return None
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir/(new_name or src.name)
    shutil.copy2(src, dst)
    manifest.append({
        "category": category,
        "source": str(src),
        "repository_path": str(dst.relative_to(REPO)).replace("\\","/"),
        "size_bytes": dst.stat().st_size,
        "sha256": sha256(dst),
    })
    return dst

def norm(s):
    return re.sub(r"[^a-z0-9]+","",str(s).lower())

def route_day_script(name):
    m = re.search(r"day(\d+)", norm(name))
    d = int(m.group(1)) if m else None
    if d in {1,2,3,7,8,9,10,11,12,13}: return folders["src_data"]
    if d in {4,14}: return folders["src_model"]
    if d in {5,17,18,19}: return folders["src_uq"]
    if d == 6: return folders["src_ood"]
    if d == 16: return folders["src_screen"]
    if d in {15,20,21}: return folders["src_stats"]
    if d is not None and 24 <= d <= 28: return folders["src_fig"]
    if d is not None and d >= 29: return folders["src_submit"]
    return folders["src_full"]

def find_figure(root, suffix, keywords):
    if not root.exists():
        return None
    hits=[]
    for p in root.rglob(f"*{suffix}"):
        n=norm(p.name)
        if all(norm(k) in n for k in keywords):
            hits.append(p)
    return sorted(hits, key=lambda x:(len(str(x)),str(x)))[0] if hits else None

# 1) All actual Python scripts
scripts = sorted(set(ROOT.glob("day*.py")) | set(ROOT.glob("Day*.py")))
for s in scripts:
    copy_file(s, folders["src_full"], category="source_full_history")
    routed=route_day_script(s.name)
    if routed != folders["src_full"]:
        copy_file(s, routed, category="source_curated")

# 2) Environment
try:
    r=subprocess.run([sys.executable,"-m","pip","freeze"],capture_output=True,text=True,check=True)
    write_text(folders["env"]/"requirements-lock.txt",r.stdout)
except Exception as e:
    warnings.append(f"pip freeze failed: {e}")

write_text(folders["env"]/"requirements-core.txt",
"""numpy
pandas
scipy
scikit-learn
matplotlib
openpyxl
joblib
""")
write_text(folders["env"]/"environment.json",json.dumps({
    "generated_utc":datetime.now(timezone.utc).isoformat(),
    "python_executable":sys.executable,
    "python_version":sys.version,
    "platform":platform.platform()
},indent=2))

# 3) Data provenance; raw data excluded by default
DATA=ROOT/"Data"
records=[]
if DATA.exists():
    for p in sorted(DATA.rglob("*")):
        if p.is_file():
            try:
                records.append({
                    "relative_local_path":str(p.relative_to(ROOT)).replace("\\","/"),
                    "size_bytes":p.stat().st_size,
                    "sha256":sha256(p)
                })
            except Exception as e:
                warnings.append(f"dataset hash failed {p}: {e}")
with (folders["data_prov"]/"raw_file_inventory_sha256.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=["relative_local_path","size_bytes","sha256"])
    w.writeheader(); w.writerows(records)

write_text(REPO/"data"/"README_DATA_ACCESS.md",
"""# Data Access and Provenance

Third-party raw data are not redistributed by default.

## PulseBat processed data
Local source during the study: `Data/PulseBat/`.
The primary model used processed U1-U21 pulse-voltage features from:
LFP 35Ah, LMO 10Ah, NMC 2.1Ah, and NMC 21Ah.

Use the dataset citation in the manuscript and respect its original license.

## Second-life LFP23
DOI: https://doi.org/10.5281/zenodo.18630889

## Bipolar709
DOI: https://doi.org/10.5281/zenodo.23634967

170 overlapping raw IDs were excluded before cross-dataset evaluation,
leaving 539 target cells.

`data/provenance/raw_file_inventory_sha256.csv` records local file identity.

Set `INCLUDE_RAW_DATA = True` only after confirming redistribution permission.
""")
write_text(folders["data_raw"]/".gitkeep","")

if INCLUDE_RAW_DATA and DATA.exists():
    for p in sorted(DATA.rglob("*")):
        if p.is_file():
            rel=p.relative_to(DATA)
            copy_file(p, folders["data_raw"]/rel.parent, rel.name, "raw_data")

# 4) Full result evidence: CSV/JSON/MD/TXT
RESULT=ROOT/"Result"
text_ext={".csv",".json",".md",".txt"}
if RESULT.exists():
    for d in sorted(RESULT.glob("Day*")):
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.suffix.lower() in text_ext:
                    rel=p.relative_to(d)
                    copy_file(p, folders["results_full"]/d.name/rel.parent, rel.name, "result_full_history")

# 5) Frozen core evidence
core_prefixes=["day13","day14","day15","day16","day17","day18","day19","day20","day21","day28b","day28c","day28d","day28e"]
if RESULT.exists():
    for d in sorted(RESULT.glob("Day*")):
        if d.is_dir() and any(d.name.lower().startswith(x) for x in core_prefixes):
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.suffix.lower() in text_ext:
                    rel=p.relative_to(d)
                    copy_file(p, folders["results_core"]/d.name/rel.parent, rel.name, "frozen_core_result")

# 6) Main figures
specs={
    "Figure_1_Framework":["framework"],
    "Figure_2_PulseFeature_Heterogeneity":["pulsefeature","heterogeneity"],
    "Figure_3_FewShot_LabelBudget":["fewshot","performance"],
    "Figure_4_Generalization_Trustworthiness":["generalization","trustworthiness"],
    "Figure_5_Screening_Tradeoff":["screening","tradeoff"],
}
main_sources=set()
for stem,keys in specs.items():
    for ext in [".png",".pdf"]:
        p=find_figure(RESULT,ext,keys)
        if p:
            copy_file(p,folders["fig_main"],stem+ext,"main_figure")
            main_sources.add(str(p))
        else:
            missing.append(f"{stem}{ext}")

# all additional figures as supplementary
if RESULT.exists():
    for p in sorted(RESULT.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".png",".pdf"} and str(p) not in main_sources:
            copy_file(p,folders["fig_supp"],f"{p.parent.name}__{p.name}","supplementary_figure")

# 7) Publication tables
table_terms=["table1","table2","table3","publicationtable","screeningsensitivity","coreresults","datasetvalidation"]
if RESULT.exists():
    for p in sorted(RESULT.rglob("*.csv")):
        if any(t in norm(p.name) for t in table_terms):
            copy_file(p,folders["tables"],category="publication_table")

# 8) Supplementary evidence
supp_prefixes=["day03","day06","day08","day12","day13","day15","day16","day17","day18","day19"]
if RESULT.exists():
    for d in sorted(RESULT.glob("Day*")):
        if d.is_dir() and any(d.name.lower().startswith(x) for x in supp_prefixes):
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.suffix.lower() in text_ext:
                    copy_file(p,folders["supp"],f"{d.name}__{p.name}","supplementary_evidence")

# 9) Manuscript and support docs if present locally
for p in ROOT.rglob("FINAL_MANUSCRIPT_SUPERVISOR_UPDATED.docx"):
    copy_file(p,folders["manuscript"],category="manuscript_support")
    break

for wanted in ["MODEL_METHOD_INVENTORY.md","ALL_VERIFIED_RESEARCH_EQUATIONS.md","FIGURE_BRIEFS.txt","CLAIM_BOUNDARY.md"]:
    hits=list(ROOT.rglob(wanted))
    if hits:
        copy_file(hits[0],folders["docs"],category="documentation")

# 10) Documentation
write_text(folders["docs"]/"LABEL_ALLOCATION_PROTOCOL.md",
"""# Target-Label Allocation Protocol

## Prediction benchmark
K means adaptation cells only: K = 0, 1, 5, 10, 20.
K=20 therefore means 20 adaptation cells.

## Trustworthy screening
B = K_adapt + n_cal

Primary:
10 adaptation + 10 calibration = 20 total labels.

Sensitivity:
10 adaptation fixed +
10/20/30 calibration =
20/30/40 total labels.

Adaptation, calibration, and evaluation cells are mutually disjoint.
""")

write_text(folders["docs"]/"CLAIM_BOUNDARY.md",
"""# Claim Boundary

Supported:
- state-free relative pulse representation
- few-shot target adaptation
- target-aware conformal uncertainty
- tested held-out-chemistry OOD separation
- OOD-aware abstention
- overlap-excluded cross-dataset validation
- conservative uncertainty-aware screening
- repeated-resampling robustness

Not claimed:
- fully independent external validation
- validated electrical 1RC/2RC Digital Twin
- deployment certification
- zero deployment risk
- VAE/generated-data validation
- unseen-SOC synthesis
""")

write_text(folders["docs"]/"CODE_MAP.md",
"""# Code Map

`src/full_history/` contains every discovered local `day*.py` source file.

Topic copies:
- 01_data_and_representation
- 02_models_and_fewshot
- 03_uncertainty
- 04_ood
- 05_screening
- 06_statistics
- 07_figures
- 08_submission_tools

No missing research script is reconstructed or fabricated.
""")

write_text(REPO/"REPRODUCE.md",
"""# Reproduction Guide

## Environment
```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r environment/requirements-lock.txt
```

If exact lock installation is platform-specific:
```powershell
pip install -r environment/requirements-core.txt
```

## Data
See `data/README_DATA_ACCESS.md`.

## Code
Complete discovered source history: `src/full_history/`.

## Evidence
Frozen/archived outputs:
- `results/frozen_core/`
- `results/full_history/`

Publication assets:
- `figures/main/`
- `figures/supplementary/`
- `tables/`

Audit:
- `audit/repository_manifest.csv`
- `audit/checksums_sha256.csv`
- `audit/missing_expected_assets.txt`

Missing assets are never fabricated.
""")

# 11) README and metadata templates
write_text(REPO/"README.md",f"""# Trustworthy Few-Shot Pulse Diagnostics for Heterogeneous Second-Life Batteries

Reproducibility repository for:

**Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries**

## Core method

State-free pulse representation:

`r_i = (U_i - U_1) / |U_1|`, i=2,...,21

combined with:
- few-shot target adaptation
- target-aware split-conformal uncertainty
- OOD applicability-domain checking
- A/B/C/D screening with abstention

## Frozen headline evidence

Internal chemistry shift:
8.268 pp at K=0 -> 3.006 pp at K=20
(63.65% MAE reduction; p=0.000977)

Overlap-excluded cross-dataset:
8.720 pp at K=0 -> 3.468 pp at K=20
(60.24% reduction; p=0.000977)

Primary trustworthy screening:
10 adaptation + 10 calibration = 20 total target labels
PICP=90.93%, MPIW=19.90 pp

## Structure

- `src/`
- `data/`
- `results/`
- `figures/`
- `tables/`
- `supplementary/`
- `docs/`
- `environment/`
- `manuscript_support/`
- `audit/`

See `REPRODUCE.md`.

## Data
Third-party raw datasets are not redistributed by default.
See `data/README_DATA_ACCESS.md`.

## Repository
https://github.com/{OWNER}/{REPO_NAME}

## Zenodo DOI
TO BE ADDED AFTER v1.0.0 ARCHIVE
""")

write_text(REPO/"CITATION.cff.template",f"""cff-version: 1.2.0
message: "Please cite the associated manuscript and this software release."
title: "Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries"
type: software
version: 1.0.0
date-released: "2026-11-13"
repository-code: "https://github.com/{OWNER}/{REPO_NAME}"
authors:
  - family-names: "TO_BE_COMPLETED"
    given-names: "TO_BE_COMPLETED"
doi: "TO_BE_ADDED_AFTER_ZENODO_ARCHIVE"
""")

write_text(REPO/".zenodo.json.template",json.dumps({
    "title":"Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries",
    "upload_type":"software",
    "description":"Reproducibility package containing code, frozen results, publication figures/tables, supplementary evidence, and provenance documentation.",
    "creators":[{"name":"TO_BE_COMPLETED"}],
    "keywords":["lithium-ion battery","second-life battery","state of health","few-shot learning","conformal prediction","out-of-distribution detection","battery screening"],
    "license":"TO_BE_SELECTED"
},indent=2))

write_text(REPO/".gitignore",
"""__pycache__/
*.py[cod]
.venv/
venv/
env/
.vscode/
.idea/
Thumbs.db
.DS_Store
~$*.docx
~$*.xlsx
~$*.pptx
*.tmp
*.bak
*.log
data/raw/*
!data/raw/.gitkeep
.env
*.pem
*.key
""")

write_text(REPO/"LICENSE_TO_CHOOSE.txt",
"""Select a repository license only after author/institution approval.
Third-party datasets retain their original licenses and are not relicensed here.
""")
write_text(REPO/"VERSION","1.0.0-prepublication")
write_text(REPO/"CHANGELOG.md",
"""# Changelog

## 1.0.0-prepublication
Initial reproducibility package assembled from the frozen research project.
""")

# 12) Audit
with (folders["audit"]/"repository_manifest.csv").open("w",newline="",encoding="utf-8") as f:
    fields=["category","source","repository_path","size_bytes","sha256"]
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(manifest)

checks=[]
for p in sorted(REPO.rglob("*")):
    if p.is_file():
        checks.append({
            "repository_path":str(p.relative_to(REPO)).replace("\\","/"),
            "size_bytes":p.stat().st_size,
            "sha256":sha256(p)
        })
with (folders["audit"]/"checksums_sha256.csv").open("w",newline="",encoding="utf-8") as f:
    fields=["repository_path","size_bytes","sha256"]
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(checks)

write_text(folders["audit"]/"missing_expected_assets.txt",
           "Missing expected assets were NOT fabricated.\n\n"+
           ("\n".join(f"- {x}" for x in missing) if missing else "None"))
write_text(folders["audit"]/"skipped_large_files.json",json.dumps(skipped,indent=2))
write_text(folders["audit"]/"builder_warnings.txt","\n".join(warnings) if warnings else "None")

summary={
    "repository_name":REPO_NAME,
    "github_owner":OWNER,
    "repository_url":f"https://github.com/{OWNER}/{REPO_NAME}",
    "generated_utc":datetime.now(timezone.utc).isoformat(),
    "raw_data_included":INCLUDE_RAW_DATA,
    "source_scripts_found":len(scripts),
    "manifest_entries":len(manifest),
    "files_in_repository":len(checks),
    "missing_expected_assets":len(missing),
    "skipped_large_files":len(skipped),
    "max_file_mb_threshold":MAX_FILE_MB,
    "scientific_results_changed":False
}
write_text(folders["audit"]/"repository_build_summary.json",json.dumps(summary,indent=2))

# 13) ZIP backup
OUT_BASE.mkdir(parents=True,exist_ok=True)
zip_base=OUT_BASE/REPO_NAME
zip_path=zip_base.with_suffix(".zip")
if zip_path.exists(): zip_path.unlink()
shutil.make_archive(str(zip_base),"zip",root_dir=OUT_BASE,base_dir=REPO_NAME)

print("\n=== GITHUB REPOSITORY PACKAGE COMPLETE ===")
print("Folder:",REPO)
print("ZIP:",zip_path)
print("GitHub owner:",OWNER)
print("Repository:",REPO_NAME)
print("Source scripts found:",len(scripts))
print("Manifest entries:",len(manifest))
print("Missing expected assets:",len(missing))
print("Skipped >95 MB:",len(skipped))
print("Raw third-party data copied:",INCLUDE_RAW_DATA)
print("\nReview first:")
print(REPO/"README.md")
print(REPO/"REPRODUCE.md")
print(folders["audit"]/"missing_expected_assets.txt")
print(folders["audit"]/"repository_build_summary.json")
