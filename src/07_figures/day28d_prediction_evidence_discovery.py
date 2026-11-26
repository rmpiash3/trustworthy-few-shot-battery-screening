# Filename: day28d_prediction_evidence_discovery.py
# Purpose:
# Discover actual frozen cell-level prediction / uncertainty evidence files
# that can support a publication figure analogous in storytelling strength
# (not scientific claim) to the supplied literature figure.
#
# IMPORTANT:
# - No generated-data analysis.
# - No KDE/KLD generated-vs-tested comparison.
# - No fabricated values.
# - No model retraining.
# - No plotting yet.
#
# The script scans D:\SecondLife_Research\Result recursively for CSV files and
# identifies files that contain combinations of:
#   true SOH / target,
#   predicted SOH,
#   error / residual,
#   K / label budget,
#   domain / chemistry,
#   lower/upper prediction interval,
#   OOD / abstention flags.
#
# Outputs:
#   01_candidate_files.csv
#   02_candidate_columns.csv
#   03_recommended_evidence_map.md
#   04_run_summary.json

from pathlib import Path
import json
import re
import pandas as pd

ROOT = Path(r"D:\SecondLife_Research")
RESULT = ROOT / "Result"
OUT = RESULT / "Day28d_PredictionEvidenceDiscovery"

OUT.mkdir(parents=True, exist_ok=True)

if not RESULT.exists():
    raise FileNotFoundError(RESULT)

def norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())

patterns = {
    "true_target": [
        "ytrue", "true", "target", "sohtrue", "truesoh", "actualsoh",
        "sohactual", "groundtruth", "reference"
    ],
    "prediction": [
        "ypred", "pred", "prediction", "predicted", "sohpred",
        "predictedsoh", "estimate", "estimated"
    ],
    "absolute_error": [
        "abserror", "absoluteerror", "ae", "mae", "errorpp"
    ],
    "residual": [
        "residual", "error", "predictionerror"
    ],
    "label_budget": [
        "k", "kshot", "shot", "labelbudget", "targetlabels",
        "adaptationcells", "calibrationcells", "totallabeledcells"
    ],
    "domain": [
        "domain", "chemistry", "batterygroup", "group", "dataset", "cohort"
    ],
    "lower_interval": [
        "lower", "lwr", "lo", "lowerbound", "pi_lower", "pilower"
    ],
    "upper_interval": [
        "upper", "upr", "hi", "upperbound", "pi_upper", "piupper"
    ],
    "ood": [
        "ood", "outofdistribution", "abstain", "abstention", "acceptance"
    ],
    "cell_id": [
        "cell", "cellid", "rawid", "batteryid", "sampleid", "groupid"
    ],
}

def classify_column(col):
    nc = norm(col)
    hits = []

    for category, keys in patterns.items():
        for key in keys:
            nk = norm(key)
            if nc == nk or (len(nk) >= 4 and nk in nc):
                hits.append(category)
                break

    return hits


file_rows = []
column_rows = []

csv_files = sorted(
    p for p in RESULT.rglob("*.csv")
    if OUT not in p.parents
)

for path in csv_files:
    try:
        df = pd.read_csv(path, nrows=5000)
    except Exception as e:
        file_rows.append({
            "file": str(path),
            "read_status": "FAILED",
            "rows_sampled": 0,
            "n_columns": 0,
            "has_true_target": False,
            "has_prediction": False,
            "has_label_budget": False,
            "has_domain": False,
            "has_interval": False,
            "has_ood": False,
            "priority_score": -1,
            "error": str(e)[:300],
        })
        continue

    categories_present = set()

    for col in df.columns:
        hits = classify_column(col)
        for h in hits:
            categories_present.add(h)

        column_rows.append({
            "file": str(path),
            "column": str(col),
            "normalized_column": norm(col),
            "categories": ";".join(hits),
            "non_null_sampled": int(df[col].notna().sum()),
        })

    has_true = "true_target" in categories_present
    has_pred = "prediction" in categories_present
    has_k = "label_budget" in categories_present
    has_domain = "domain" in categories_present
    has_interval = (
        "lower_interval" in categories_present
        and "upper_interval" in categories_present
    )
    has_ood = "ood" in categories_present

    # Priority is high only when true + predicted are both present.
    score = 0
    score += 5 if has_true else 0
    score += 5 if has_pred else 0
    score += 2 if has_k else 0
    score += 2 if has_domain else 0
    score += 2 if has_interval else 0
    score += 1 if has_ood else 0

    file_rows.append({
        "file": str(path),
        "read_status": "OK",
        "rows_sampled": int(len(df)),
        "n_columns": int(len(df.columns)),
        "has_true_target": has_true,
        "has_prediction": has_pred,
        "has_label_budget": has_k,
        "has_domain": has_domain,
        "has_interval": has_interval,
        "has_ood": has_ood,
        "priority_score": score,
        "error": "",
    })

file_df = pd.DataFrame(file_rows)
col_df = pd.DataFrame(column_rows)

if not file_df.empty:
    file_df = file_df.sort_values(
        ["priority_score", "file"],
        ascending=[False, True]
    )

file_df.to_csv(
    OUT / "01_candidate_files.csv",
    index=False
)

col_df.to_csv(
    OUT / "02_candidate_columns.csv",
    index=False
)

top = file_df[
    (file_df["read_status"] == "OK")
    & (file_df["has_true_target"] == True)
    & (file_df["has_prediction"] == True)
].head(20)

lines = [
    "# Recommended Evidence Map",
    "",
    "## Why this audit exists",
    "",
    "The supplied literature figure evaluates generated-versus-tested data under unseen SOC.",
    "That scientific claim is not part of the frozen current study and must not be reproduced.",
    "",
    "The correct own-study analogue should use actual frozen cell-level prediction evidence:",
    "",
    "1. true SOH versus predicted SOH;",
    "2. error/residual distributions;",
    "3. domain-wise or K-wise generalization;",
    "4. conformal interval / coverage diagnostics where available.",
    "",
    "## Candidate files containing BOTH true target and prediction columns",
    "",
]

if top.empty:
    lines += [
        "No CSV with confidently detected true-target + prediction columns was found.",
        "",
        "Do NOT fabricate the requested figure.",
        "Use the audit CSVs to inspect alternative column names or regenerate a frozen",
        "cell-level prediction export from the existing pipeline only if required.",
    ]
else:
    for _, row in top.iterrows():
        lines.append(
            f"- score={int(row['priority_score'])}: `{row['file']}` "
            f"(K={row['has_label_budget']}, domain={row['has_domain']}, "
            f"interval={row['has_interval']}, OOD={row['has_ood']})"
        )

lines += [
    "",
    "## Recommended future figure only after evidence file verification",
    "",
    "Panel (a): true SOH vs predicted SOH for frozen K=0 and K=20 cases.",
    "Panel (b): absolute-error distributions across internal and overlap-excluded external evaluation.",
    "Panel (c): chemistry/domain-wise error reduction or conformal interval diagnostics.",
    "",
    "This would provide a strong generalization/trustworthiness figure without making",
    "any generative-data or unseen-SOC synthesis claim.",
]

(OUT / "03_recommended_evidence_map.md").write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8"
)

summary = {
    "stage": "Day28d",
    "purpose": "Discover frozen prediction evidence for a non-fabricated generalization figure.",
    "csv_files_scanned": int(len(csv_files)),
    "files_with_true_and_prediction": int(
        (
            (file_df["read_status"] == "OK")
            & (file_df["has_true_target"] == True)
            & (file_df["has_prediction"] == True)
        ).sum()
    ) if not file_df.empty else 0,
    "generated_data_analysis_allowed": False,
    "kld_generated_vs_tested_allowed": False,
    "model_retraining": False,
    "plot_created": False,
    "next_step": (
        "Inspect candidate evidence files, then create an own-data "
        "true-vs-predicted/error/generalization figure only from verified frozen outputs."
    ),
    "output_dir": str(OUT),
}

(OUT / "04_run_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 28d COMPLETE ===")
print("CSV files scanned:", len(csv_files))
print(
    "Files with detected true-target + prediction:",
    summary["files_with_true_and_prediction"]
)
print("Generated-data/KLD analysis created: NO")
print("Plot created: NO")
print("\nSaved:")
print(OUT / "01_candidate_files.csv")
print(OUT / "02_candidate_columns.csv")
print(OUT / "03_recommended_evidence_map.md")
print(OUT / "04_run_summary.json")
