r"""
Day 20 — Manuscript claim-readiness and evidence-freeze gate
============================================================

Purpose
-------
Consolidate the verified research chain into a claim-readiness matrix before
manuscript/thesis writing.

This script does NOT retrain models.

It checks the existence of the key result files from Days 13–19, reads their
headline outputs, and classifies major manuscript claims as:

- SUPPORTED_PRIMARY
- SUPPORTED_WITH_SCOPE
- SUPPLEMENTARY_ONLY
- NOT_YET_SUPPORTED

Critical goal
-------------
Prevent overclaiming.

In particular:
- "Digital-Twin-Assisted" requires a defensible electrical/state DT contribution.
- "fully independent external validation" is not allowed because Bipolar709 had
  170 overlapping raw IDs that were explicitly excluded.
- screening safety results are sensitivity evidence, not deployment certification.

Output
------
D:\SecondLife_Research\Result\Day20_ClaimReadiness
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(r"D:\SecondLife_Research")
RESULT = ROOT / "Result"
OUT = RESULT / "Day20_ClaimReadiness"
OUT.mkdir(parents=True, exist_ok=True)

paths = {
    "day13": RESULT / "Day13_StateSensitivity" / "06_representation_freeze_summary.csv",
    "day14_internal": RESULT / "Day14_Frozen_NoState_Pipeline" / "10_internal_summary.csv",
    "day14_uq": RESULT / "Day14_Frozen_NoState_Pipeline" / "11_uq_summary.csv",
    "day14_external": RESULT / "Day14_Frozen_NoState_Pipeline" / "12_external_summary.csv",
    "day14_overlap": RESULT / "Day14_Frozen_NoState_Pipeline" / "09_external_overlap_summary.csv",
    "day15_stats": RESULT / "Day15_FinalStatistics" / "02_overall_paired_statistics.csv",
    "day16_screen": RESULT / "Day16_ScreeningDecision" / "04_screening_overall_summary.csv",
    "day19_gate": RESULT / "Day19_CorrectedCalibrationSensitivity" / "06_day16_integrity_gate.csv",
    "day19_safety": RESULT / "Day19_CorrectedCalibrationSensitivity" / "04_corrected_calibration_overall.csv",
}

inventory = []
for key, path in paths.items():
    inventory.append({
        "evidence_key": key,
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    })

inventory_df = pd.DataFrame(inventory)
inventory_df.to_csv(OUT / "01_evidence_inventory.csv", index=False)

missing = inventory_df.loc[~inventory_df["exists"], "evidence_key"].tolist()
if missing:
    raise FileNotFoundError(
        "Missing required verified evidence: " + ", ".join(missing)
    )

day13 = pd.read_csv(paths["day13"])
internal = pd.read_csv(paths["day14_internal"])
uq = pd.read_csv(paths["day14_uq"])
external = pd.read_csv(paths["day14_external"])
overlap = pd.read_csv(paths["day14_overlap"])
stats = pd.read_csv(paths["day15_stats"])
screen = pd.read_csv(paths["day16_screen"])
gate = pd.read_csv(paths["day19_gate"])
safety = pd.read_csv(paths["day19_safety"])

# Headline values
int_k0 = float(internal.loc[internal["K_cells"] == 0, "mean_MAE_pp"].iloc[0])
int_k20 = float(internal.loc[internal["K_cells"] == 20, "mean_MAE_pp"].iloc[0])
ext_k0 = float(external.loc[external["K_cells"] == 0, "mean_MAE_pp"].iloc[0])
ext_k20 = float(external.loc[external["K_cells"] == 20, "mean_MAE_pp"].iloc[0])

uq_k20 = uq.loc[uq["K_total_labeled_cells"] == 20].iloc[0]
overlap_row = overlap.iloc[0]
screen_row = screen.iloc[0]
gate_row = gate.iloc[0]

safety_10 = safety.loc[safety["calibration_cells"] == 10].iloc[0]
safety_20 = safety.loc[safety["calibration_cells"] == 20].iloc[0]
safety_30 = safety.loc[safety["calibration_cells"] == 30].iloc[0]

stats_internal = stats.loc[stats["dataset"] == "Internal"].iloc[0]
stats_external = stats.loc[stats["dataset"] == "External_CrossDataset"].iloc[0]

claim_rows = [
    {
        "claim_id": "C01",
        "claim": "A state-free REL_RATIO pulse representation transfers across chemistries/groups.",
        "status": "SUPPORTED_PRIMARY",
        "evidence": "Day13 + Day14",
        "safe_wording": (
            "The state-free relative pulse representation retained cross-domain "
            "performance while removing the SOCR/SOE ambiguity."
        ),
        "do_not_say": "SOCR and SOE are physically equivalent.",
    },
    {
        "claim_id": "C02",
        "claim": "Few-shot target adaptation materially improves SOH prediction.",
        "status": "SUPPORTED_PRIMARY",
        "evidence": (
            f"Internal MAE {int_k0:.3f}->{int_k20:.3f} pp; "
            f"external {ext_k0:.3f}->{ext_k20:.3f} pp; "
            f"paired Wilcoxon p={stats_internal['wilcoxon_one_sided_p']:.6f} internal "
            f"and p={stats_external['wilcoxon_one_sided_p']:.6f} external."
        ),
        "safe_wording": (
            "Few-shot target adaptation consistently reduced SOH error in both "
            "internal chemistry-shift and overlap-excluded cross-dataset evaluation."
        ),
        "do_not_say": "Few-shot adaptation guarantees accurate performance on any unseen battery.",
    },
    {
        "claim_id": "C03",
        "claim": "Target-aware conformal calibration recovers approximately nominal 90% coverage.",
        "status": "SUPPORTED_PRIMARY",
        "evidence": (
            f"K20 PICP={float(uq_k20['mean_PICP']):.4f}, "
            f"MPIW={float(uq_k20['mean_MPIW_pp']):.3f} pp."
        ),
        "safe_wording": (
            "With target-aware calibration at K=20, empirical coverage approached "
            "the nominal 90% level."
        ),
        "do_not_say": "The conformal interval is universally valid under arbitrary domain shift.",
    },
    {
        "claim_id": "C04",
        "claim": "OOD detection identifies held-out chemistry shift.",
        "status": "SUPPORTED_WITH_SCOPE",
        "evidence": "Day14 Mahalanobis/KNN AUROC=1.0 in the tested held-out chemistry design.",
        "safe_wording": (
            "OOD scores strongly separated the tested held-out chemistry domains "
            "from source domains."
        ),
        "do_not_say": "OOD score universally predicts SOH error or all real-world distribution shifts.",
    },
    {
        "claim_id": "C05",
        "claim": "External validation is independent.",
        "status": "NOT_YET_SUPPORTED",
        "evidence": (
            f"{int(overlap_row['overlapping_raw_ids'])} overlapping raw IDs were excluded; "
            f"{int(overlap_row['target_cells_after_exclusion'])} target cells remained."
        ),
        "safe_wording": "overlap-excluded cross-dataset validation",
        "do_not_say": "fully independent external validation",
    },
    {
        "claim_id": "C06",
        "claim": "The uncertainty-aware screening layer reduces unsafe reuse decisions.",
        "status": "SUPPORTED_WITH_SCOPE",
        "evidence": (
            f"Day16 observed false-safe rate={float(screen_row['false_safe_rate_mean']):.6f}; "
            f"Day19 protocol-locked sensitivity observed 0 false-safe rows at "
            f"20 and 30 calibration cells in the tested repeats."
        ),
        "safe_wording": (
            "The conservative interval-based policy routed most ambiguous cells to "
            "additional diagnostics and showed low observed false-safe rates in the "
            "tested repeated-resampling design."
        ),
        "do_not_say": "The screening system is deployment-certified or zero-risk.",
    },
    {
        "claim_id": "C07",
        "claim": "Increasing target calibration size improves safety.",
        "status": "SUPPORTED_WITH_SCOPE",
        "evidence": (
            f"10-cal: false-safe={float(safety_10['false_safe_rate_mean']):.6f}, "
            f"PICP={float(safety_10['PICP_mean']):.4f}; "
            f"20-cal: false-safe={float(safety_20['false_safe_rate_mean']):.6f}, "
            f"PICP={float(safety_20['PICP_mean']):.4f}; "
            f"30-cal: false-safe={float(safety_30['false_safe_rate_mean']):.6f}, "
            f"PICP={float(safety_30['PICP_mean']):.4f}."
        ),
        "safe_wording": (
            "Larger calibration sets removed observed true false-safe events in this "
            "protocol-locked sensitivity analysis, but safety, coverage, interval width, "
            "and decisiveness did not improve monotonically."
        ),
        "do_not_say": "More calibration cells always improve performance.",
    },
    {
        "claim_id": "C08",
        "claim": "ECM-inspired pulse physics features provide a universal transferable representation.",
        "status": "SUPPLEMENTARY_ONLY",
        "evidence": "Day12 showed PHYSICS and REL_PLUS_PHYSICS were worse overall than REL_RATIO.",
        "safe_wording": (
            "ECM-inspired surrogates provided chemistry-specific interpretability "
            "and limited domain-specific gains, but were not the best universal predictor."
        ),
        "do_not_say": "Physics surrogate features universally improve cross-domain SOH prediction.",
    },
    {
        "claim_id": "C09",
        "claim": "A fitted electrical 1RC/2RC Digital Twin has been validated.",
        "status": "NOT_YET_SUPPORTED",
        "evidence": (
            "Day09 found no pulse/relaxation excitation in LFP23 for defensible 2RC "
            "identification; Day10-11 became SOC-label provenance evidence; Day12 "
            "used ECM-inspired surrogates only."
        ),
        "safe_wording": (
            "The present computational evidence is physics-guided / pulse-physics-informed, "
            "not a validated electrical 2RC Digital Twin."
        ),
        "do_not_say": "Validated 2RC Digital Twin" ,
    },
    {
        "claim_id": "C10",
        "claim": "The current computational study alone supports 'Digital-Twin-Assisted' in the title.",
        "status": "NOT_YET_SUPPORTED",
        "evidence": "No validated electrical 1RC/2RC or independent state-twin evidence currently exists.",
        "safe_wording": (
            "Remove 'Digital-Twin-Assisted' from the current paper title unless a "
            "separate raw pulse/HPPC or Chroma-based DT identification/validation stage is added."
        ),
        "do_not_say": "Digital-Twin-Assisted based only on U1-U21 surrogate features.",
    },
    {
        "claim_id": "C11",
        "claim": "The study is fully experimentally validated.",
        "status": "NOT_YET_SUPPORTED",
        "evidence": "Independent Chroma proof-of-concept remains pending.",
        "safe_wording": "computational cross-domain and cross-dataset validation",
        "do_not_say": "full experimental validation",
    },
]

claims = pd.DataFrame(claim_rows)
claims.to_csv(OUT / "02_claim_readiness_matrix.csv", index=False)

status_counts = (
    claims["status"]
    .value_counts()
    .rename_axis("status")
    .reset_index(name="count")
)
status_counts.to_csv(OUT / "03_claim_status_counts.csv", index=False)

recommended_titles = pd.DataFrame([
    {
        "priority": 1,
        "title": (
            "Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty "
            "and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries"
        ),
        "status": "CURRENTLY_DEFENSIBLE",
        "reason": "Matches verified few-shot, UQ, OOD, screening, and cross-domain evidence.",
    },
    {
        "priority": 2,
        "title": (
            "Physics-Guided Few-Shot Pulse Diagnostics for Uncertainty-Aware "
            "Screening of Heterogeneous Second-Life Lithium-Ion Batteries"
        ),
        "status": "CURRENTLY_DEFENSIBLE_WITH_CARE",
        "reason": (
            "Physics-guided is safer than Digital-Twin-Assisted because pulse normalization "
            "and ECM-inspired surrogate audits exist, but a fitted electrical DT does not."
        ),
    },
    {
        "priority": 3,
        "title": (
            "Trustworthy Digital-Twin-Assisted Few-Shot Pulse Diagnostics for "
            "Second-Life Lithium-Ion Battery Screening"
        ),
        "status": "NOT_YET_DEFENSIBLE",
        "reason": "Requires validated electrical/state Digital Twin evidence first.",
    },
])
recommended_titles.to_csv(OUT / "04_title_readiness_options.csv", index=False)

# Compact manuscript evidence snapshot
snapshot = pd.DataFrame([
    {"metric": "Frozen representation", "value": "REL_RATIO_NO_STATE"},
    {"metric": "Internal K0 MAE (pp)", "value": int_k0},
    {"metric": "Internal K20 MAE (pp)", "value": int_k20},
    {"metric": "External K0 MAE (pp)", "value": ext_k0},
    {"metric": "External K20 MAE (pp)", "value": ext_k20},
    {"metric": "K20 conformal PICP", "value": float(uq_k20["mean_PICP"])},
    {"metric": "K20 conformal MPIW (pp)", "value": float(uq_k20["mean_MPIW_pp"])},
    {"metric": "Overlap IDs excluded", "value": int(overlap_row["overlapping_raw_ids"])},
    {"metric": "External cells retained", "value": int(overlap_row["target_cells_after_exclusion"])},
    {"metric": "Day19 integrity gate", "value": bool(gate_row["reproduction_pass"])},
    {"metric": "10-cal false-safe rate", "value": float(safety_10["false_safe_rate_mean"])},
    {"metric": "20-cal false-safe rate", "value": float(safety_20["false_safe_rate_mean"])},
    {"metric": "30-cal false-safe rate", "value": float(safety_30["false_safe_rate_mean"])},
])
snapshot.to_csv(OUT / "05_final_evidence_snapshot.csv", index=False)

run_summary = {
    "day": "Day20",
    "purpose": "Freeze manuscript claim boundaries before writing.",
    "primary_representation": "REL_RATIO_NO_STATE",
    "recommended_current_title": recommended_titles.iloc[0]["title"],
    "digital_twin_title_status": "NOT_YET_DEFENSIBLE",
    "external_validation_wording": "overlap-excluded cross-dataset validation",
    "screening_status": "promising conservative sensitivity evidence; not deployment certification",
    "independent_chroma_validation": "PENDING",
    "output_dir": str(OUT),
}

(OUT / "06_run_summary.json").write_text(
    json.dumps(run_summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 20 COMPLETE ===")
print("\nClaim readiness:")
print(claims[["claim_id", "status", "claim"]].to_string(index=False))

print("\nRecommended titles:")
print(recommended_titles.to_string(index=False))

print("\nEvidence snapshot:")
print(snapshot.to_string(index=False))

print(f"\nResults saved to:\n{OUT}")

print("\nSend me:")
print("02_claim_readiness_matrix.csv")
print("04_title_readiness_options.csv")
print("05_final_evidence_snapshot.csv")
print("06_run_summary.json")
