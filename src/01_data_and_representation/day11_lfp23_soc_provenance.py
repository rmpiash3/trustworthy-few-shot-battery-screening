r"""
Day 11 — LFP23 SOC-label provenance and nominal-capacity audit
==============================================================

Why this stage exists
---------------------
Day10 found:
- fitted Q_eff ~= 5.9934–5.9941 Ah for all 23 files
- filename capacities range 3.422–5.596 Ah
- SOC reconstructed with fitted Q_eff has near-zero error

This strongly suggests the supplied SOC column was itself generated from current
integration using a common nominal/reference capacity near 6 Ah.

Therefore Day11 audits whether:
1. A single common Q_ref explains all SOC trajectories.
2. Q_ref is effectively ~6 Ah.
3. The filename capacity values are likely actual measured capacities / health labels.
4. SOH can be represented as Q_actual / Q_ref.
5. The SOC column must NOT be used as independent validation evidence.

This is a provenance/leakage audit, not a new model benchmark.

Input
-----
D:\SecondLife_Research\Data\External_LFP23

Output
------
D:\SecondLife_Research\Result\Day11_LFP23_SOC_Provenance
"""

from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(r"D:\SecondLife_Research")
DATA_ROOT = ROOT / "Data" / "External_LFP23"
OUT = ROOT / "Result" / "Day11_LFP23_SOC_Provenance"
OUT.mkdir(parents=True, exist_ok=True)

TIME_CANDIDATES = ["Date_Time", "DateTime", "datetime", "Timestamp", "Time", "time"]
CURR_CANDIDATES = ["Current(A)", "Current", "current", "I"]
SOC_CANDIDATES = ["SOC", "SOC_fake", "SOCR", "soc"]
SUPPORTED = {".xlsx", ".xls", ".csv"}

Q_REFERENCE_CANDIDATES_AH = [5.5, 5.8, 5.9, 5.95, 5.99, 6.0, 6.05, 6.1, 6.2]
EPS = 1e-12


def read_first_nonempty(path):
    ext = path.suffix.lower()
    if ext in {".xlsx", ".xls"}:
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            if not df.dropna(how="all").empty:
                return df
        return pd.DataFrame()
    if ext == ".csv":
        return pd.read_csv(path, low_memory=False)
    raise ValueError(path)


def first_existing(columns, candidates):
    lower = {str(c).strip().lower(): c for c in columns}
    for x in candidates:
        if x.lower() in lower:
            return lower[x.lower()]
    return None


def parse_capacity_from_filename(name):
    m = re.search(r"(\d+(?:\.\d+)?)\s*Ah", str(name), flags=re.I)
    return float(m.group(1)) if m else np.nan


def parse_time_seconds(s):
    dt = pd.to_datetime(s, errors="coerce")
    if dt.notna().mean() >= 0.8:
        return (dt - dt.iloc[0]).dt.total_seconds().astype(float)

    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() >= 0.8:
        num = num.astype(float)
        return num - float(num.dropna().iloc[0])

    return pd.Series(np.nan, index=s.index)


def normalize_soc(s):
    s = pd.to_numeric(s, errors="coerce")
    v = s.dropna()
    if v.empty:
        return s
    return s / 100.0 if v.quantile(0.95) > 1.5 else s


def cumulative_ah(t, current):
    t = np.asarray(t, dtype=float)
    current = np.asarray(current, dtype=float)
    dt = np.diff(t)
    i_mid = 0.5 * (current[:-1] + current[1:])
    dq = i_mid * dt / 3600.0
    return np.concatenate([[0.0], np.cumsum(dq)])


files = sorted(
    p for p in DATA_ROOT.rglob("*")
    if p.is_file() and p.suffix.lower() in SUPPORTED
)
if not files:
    raise FileNotFoundError(DATA_ROOT)

file_rows = []
candidate_rows = []
errors = []

for p in files:
    try:
        df = read_first_nonempty(p).dropna(how="all").copy()
        df.columns = [str(c).strip() for c in df.columns]

        tcol = first_existing(df.columns, TIME_CANDIDATES)
        icol = first_existing(df.columns, CURR_CANDIDATES)
        scol = first_existing(df.columns, SOC_CANDIDATES)

        if not all([tcol, icol, scol]):
            raise ValueError(f"Missing required column(s): time={tcol}, current={icol}, soc={scol}")

        t = parse_time_seconds(df[tcol])
        i = pd.to_numeric(df[icol], errors="coerce")
        soc = normalize_soc(df[scol])

        good = t.notna() & i.notna() & soc.notna()
        t = t[good].reset_index(drop=True)
        i = i[good].reset_index(drop=True)
        soc = soc[good].reset_index(drop=True)

        order = np.argsort(t.to_numpy(dtype=float))
        t = t.iloc[order].reset_index(drop=True)
        i = i.iloc[order].reset_index(drop=True)
        soc = soc.iloc[order].reset_index(drop=True)

        q = cumulative_ah(t, i)
        delta_soc = float(soc.iloc[-1] - soc.iloc[0])

        if np.sign(q[-1]) != np.sign(delta_soc):
            i = -i
            q = cumulative_ah(t, i)

        x = q - q[0]
        y = soc.to_numpy(dtype=float) - float(soc.iloc[0])

        denom = float(np.dot(x, x))
        if denom <= EPS:
            raise ValueError("No charge-throughput variation")

        beta = float(np.dot(x, y) / denom)
        if beta <= 0:
            raise ValueError("Non-positive SOC/Ah slope")

        q_eff = 1.0 / beta
        q_actual = parse_capacity_from_filename(p.name)

        # Test candidate common reference capacities against the measured SOC trajectory.
        candidate_errors = {}
        for qref in Q_REFERENCE_CANDIDATES_AH:
            soc_hat = float(soc.iloc[0]) + x / qref
            rmse = float(np.sqrt(np.mean((soc_hat - soc.to_numpy(dtype=float)) ** 2)))
            candidate_errors[qref] = rmse
            candidate_rows.append({
                "file": p.name,
                "Q_reference_candidate_Ah": qref,
                "SOC_RMSE": rmse,
            })

        best_candidate = min(candidate_errors, key=candidate_errors.get)
        best_candidate_rmse = candidate_errors[best_candidate]

        # Explicit 6 Ah reconstruction
        soc_6 = float(soc.iloc[0]) + x / 6.0
        rmse_6 = float(np.sqrt(np.mean((soc_6 - soc.to_numpy(dtype=float)) ** 2)))
        mae_6 = float(np.mean(np.abs(soc_6 - soc.to_numpy(dtype=float))))
        final_err_6 = float(soc_6[-1] - soc.iloc[-1])

        soh_if_6 = q_actual / 6.0 if np.isfinite(q_actual) else np.nan
        soh_if_qeff = q_actual / q_eff if np.isfinite(q_actual) else np.nan

        file_rows.append({
            "file": p.name,
            "Q_actual_from_filename_Ah": q_actual,
            "Q_eff_from_SOC_Ah": q_eff,
            "distance_Qeff_to_6Ah_Ah": abs(q_eff - 6.0),
            "distance_Qeff_to_6Ah_percent": abs(q_eff - 6.0) / 6.0 * 100,
            "best_reference_candidate_Ah": best_candidate,
            "best_candidate_SOC_RMSE": best_candidate_rmse,
            "SOC_RMSE_using_6Ah": rmse_6,
            "SOC_MAE_using_6Ah": mae_6,
            "SOC_final_error_using_6Ah": final_err_6,
            "SOH_if_Qref_6Ah": soh_if_6,
            "SOH_if_Qref_Qeff": soh_if_qeff,
        })

    except Exception as e:
        errors.append({
            "file": p.name,
            "error_type": type(e).__name__,
            "error": str(e),
        })

metrics = pd.DataFrame(file_rows)
candidate_df = pd.DataFrame(candidate_rows)
error_df = pd.DataFrame(errors)

metrics.to_csv(OUT / "01_soc_provenance_file_metrics.csv", index=False)
candidate_df.to_csv(OUT / "02_reference_capacity_candidate_scan.csv", index=False)
error_df.to_csv(OUT / "03_errors.csv", index=False)

if metrics.empty:
    raise RuntimeError("No valid file metrics produced.")

candidate_summary = (
    candidate_df.groupby("Q_reference_candidate_Ah")
    .agg(
        mean_SOC_RMSE=("SOC_RMSE", "mean"),
        median_SOC_RMSE=("SOC_RMSE", "median"),
        max_SOC_RMSE=("SOC_RMSE", "max"),
    )
    .reset_index()
    .sort_values("mean_SOC_RMSE")
)
candidate_summary.to_csv(OUT / "04_reference_capacity_rank.csv", index=False)

qeff_mean = float(metrics["Q_eff_from_SOC_Ah"].mean())
qeff_std = float(metrics["Q_eff_from_SOC_Ah"].std(ddof=1))
qeff_min = float(metrics["Q_eff_from_SOC_Ah"].min())
qeff_max = float(metrics["Q_eff_from_SOC_Ah"].max())
qeff_cv_pct = qeff_std / qeff_mean * 100.0

best_global_candidate = float(candidate_summary.iloc[0]["Q_reference_candidate_Ah"])

aggregate = pd.DataFrame([{
    "files_successful": len(metrics),
    "files_failed": len(error_df),
    "Qeff_mean_Ah": qeff_mean,
    "Qeff_std_Ah": qeff_std,
    "Qeff_min_Ah": qeff_min,
    "Qeff_max_Ah": qeff_max,
    "Qeff_CV_percent": qeff_cv_pct,
    "mean_abs_distance_to_6Ah_percent":
        float(metrics["distance_Qeff_to_6Ah_percent"].mean()),
    "mean_SOC_RMSE_using_6Ah":
        float(metrics["SOC_RMSE_using_6Ah"].mean()),
    "max_SOC_RMSE_using_6Ah":
        float(metrics["SOC_RMSE_using_6Ah"].max()),
    "best_global_reference_candidate_Ah": best_global_candidate,
    "filename_capacity_min_Ah":
        float(metrics["Q_actual_from_filename_Ah"].min()),
    "filename_capacity_max_Ah":
        float(metrics["Q_actual_from_filename_Ah"].max()),
    "SOH_if_6Ah_min":
        float(metrics["SOH_if_Qref_6Ah"].min()),
    "SOH_if_6Ah_max":
        float(metrics["SOH_if_Qref_6Ah"].max()),
}])
aggregate.to_csv(OUT / "05_soc_provenance_aggregate.csv", index=False)

# Figure 1: Qeff per file
plt.figure(figsize=(9.0, 5.0))
x = np.arange(len(metrics))
plt.plot(x, metrics["Q_eff_from_SOC_Ah"], marker="o", label="Qeff inferred from SOC/current")
plt.axhline(6.0, linestyle="--", label="6 Ah reference")
plt.xlabel("LFP23 file index")
plt.ylabel("Inferred reference capacity (Ah)")
plt.title("Common SOC reference-capacity signature")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig01_Qeff_Across_Files.png", dpi=300)
plt.savefig(OUT / "Fig01_Qeff_Across_Files.pdf")
plt.close()

# Figure 2: candidate reference capacity scan
plt.figure(figsize=(7.2, 5.0))
plt.plot(
    candidate_summary["Q_reference_candidate_Ah"],
    candidate_summary["mean_SOC_RMSE"],
    marker="o"
)
plt.xlabel("Candidate common reference capacity (Ah)")
plt.ylabel("Mean SOC reconstruction RMSE")
plt.title("Reference-capacity scan")
plt.tight_layout()
plt.savefig(OUT / "Fig02_Reference_Capacity_Scan.png", dpi=300)
plt.savefig(OUT / "Fig02_Reference_Capacity_Scan.pdf")
plt.close()

# Figure 3: implied SOH if 6 Ah reference
plt.figure(figsize=(8.0, 5.0))
plt.hist(metrics["SOH_if_Qref_6Ah"] * 100, bins=10)
plt.xlabel("Implied SOH = filename capacity / 6 Ah (%)")
plt.ylabel("Files")
plt.title("Implied second-life SOH distribution")
plt.tight_layout()
plt.savefig(OUT / "Fig03_Implied_SOH_Distribution.png", dpi=300)
plt.savefig(OUT / "Fig03_Implied_SOH_Distribution.pdf")
plt.close()

run_summary = {
    "day": "Day11",
    "dataset": "External_LFP23",
    "purpose": "Audit whether the supplied SOC column is derived from current integration using a common nominal/reference capacity near 6 Ah.",
    "key_hypothesis": "SOC is not an independent measurement; it is likely Coulomb-counted using an approximately 6 Ah reference capacity.",
    "manuscript_implication": (
        "If the common-reference hypothesis is confirmed, SOC must not be used as independent validation of the charge-balance twin. "
        "Instead, the finding should be reported as label-provenance / physics-consistency evidence."
    ),
    "output_dir": str(OUT),
}
(OUT / "06_run_summary.json").write_text(
    json.dumps(run_summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 11 COMPLETE ===")
print("\nSOC provenance aggregate:")
print(aggregate.to_string(index=False))
print("\nReference-capacity ranking:")
print(candidate_summary.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("01_soc_provenance_file_metrics.csv")
print("04_reference_capacity_rank.csv")
print("05_soc_provenance_aggregate.csv")
print("06_run_summary.json")
