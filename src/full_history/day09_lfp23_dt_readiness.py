r"""
Day 09 — External_LFP23 raw time-series physics / Digital-Twin readiness audit
=============================================================================

Purpose
-------
Inspect the real charging time series in External_LFP23 before attempting a
2RC equivalent-circuit Digital Twin fit.

This stage DOES NOT force a 2RC fit.

It answers:
1. What are the actual column names?
2. Is Date_Time parseable and what is the sampling interval?
3. Are voltage/current/SOC sufficiently complete?
4. Is the current profile constant-current, stepped, pulsed, or irregular?
5. Are there enough current transitions / relaxation windows for 2RC identification?
6. What are the voltage, current, SOC and duration ranges per file?
7. Can filename capacity values be parsed as metadata?

Expected root:
D:\SecondLife_Research\Data\External_LFP23

Output:
D:\SecondLife_Research\Result\Day09_LFP23_DT_Readiness
"""

from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(r"D:\SecondLife_Research")
DATA_ROOT = ROOT / "Data" / "External_LFP23"
OUT = ROOT / "Result" / "Day09_LFP23_DT_Readiness"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

SUPPORTED = {".xlsx", ".xls", ".csv"}

TIME_CANDIDATES = ["Date_Time", "DateTime", "datetime", "Timestamp", "Time", "time"]
VOLT_CANDIDATES = ["Voltage(V)", "Voltage", "voltage", "V"]
CURR_CANDIDATES = ["Current(A)", "Current", "current", "I"]
SOC_CANDIDATES = ["SOC", "SOC_fake", "SOCR", "soc"]

# Heuristics only; this is a readiness audit, not a final pulse detector.
CURRENT_STEP_ABS_A = 0.05
CURRENT_STEP_REL = 0.05
RELAX_CURRENT_ABS_A = 0.05
MIN_RELAX_SAMPLES = 5


def read_first_nonempty(path):
    ext = path.suffix.lower()
    if ext in {".xlsx", ".xls"}:
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            if not df.dropna(how="all").empty:
                return df, sheet
        return pd.DataFrame(), None
    if ext == ".csv":
        return pd.read_csv(path, low_memory=False), None
    raise ValueError(f"Unsupported: {path}")


def first_existing(columns, candidates):
    cols = {str(c).strip(): c for c in columns}
    lower = {str(c).strip().lower(): c for c in columns}
    for name in candidates:
        if name in cols:
            return cols[name]
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def parse_capacity_from_filename(name):
    # Example: 3.422Ah_charge.xlsx
    m = re.search(r"(\d+(?:\.\d+)?)\s*Ah", name, flags=re.I)
    return float(m.group(1)) if m else np.nan


def parse_time_series(s):
    # Prefer datetime parsing.
    dt = pd.to_datetime(s, errors="coerce")
    if dt.notna().mean() >= 0.8:
        t = (dt - dt.iloc[0]).dt.total_seconds()
        return t.astype(float), "datetime"

    # Fallback numeric time.
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() >= 0.8:
        return num.astype(float), "numeric"

    return pd.Series(np.nan, index=s.index), "unparseable"


def consecutive_true_runs(mask):
    mask = np.asarray(mask, dtype=bool)
    runs = []
    start = None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(mask) - 1))
    return runs


files = sorted(
    p for p in DATA_ROOT.rglob("*")
    if p.is_file() and p.suffix.lower() in SUPPORTED
)

if not files:
    raise FileNotFoundError(f"No supported LFP23 files under {DATA_ROOT}")

audit_rows = []
transition_rows = []
error_rows = []
example_plotted = 0

for file_index, p in enumerate(files, 1):
    try:
        df, sheet = read_first_nonempty(p)
        df = df.dropna(how="all").copy()
        df.columns = [str(c).strip() for c in df.columns]

        time_col = first_existing(df.columns, TIME_CANDIDATES)
        volt_col = first_existing(df.columns, VOLT_CANDIDATES)
        curr_col = first_existing(df.columns, CURR_CANDIDATES)
        soc_col = first_existing(df.columns, SOC_CANDIDATES)

        if not (time_col and volt_col and curr_col):
            audit_rows.append({
                "file": p.name,
                "relative_path": str(p.relative_to(DATA_ROOT)),
                "rows": len(df),
                "sheet": sheet,
                "capacity_from_filename_Ah": parse_capacity_from_filename(p.name),
                "time_col": time_col,
                "voltage_col": volt_col,
                "current_col": curr_col,
                "soc_col": soc_col,
                "classification": "MISSING_CORE_COLUMN",
            })
            continue

        t, time_mode = parse_time_series(df[time_col])
        v = pd.to_numeric(df[volt_col], errors="coerce")
        i = pd.to_numeric(df[curr_col], errors="coerce")
        soc = (
            pd.to_numeric(df[soc_col], errors="coerce")
            if soc_col else pd.Series(np.nan, index=df.index)
        )

        good = t.notna() & v.notna() & i.notna()
        t = t[good].reset_index(drop=True)
        v = v[good].reset_index(drop=True)
        i = i[good].reset_index(drop=True)
        soc = soc[good].reset_index(drop=True)

        if len(t) < 10:
            raise ValueError("Too few valid time-voltage-current samples")

        # Ensure increasing order if needed.
        order = np.argsort(t.to_numpy())
        t = t.iloc[order].reset_index(drop=True)
        v = v.iloc[order].reset_index(drop=True)
        i = i.iloc[order].reset_index(drop=True)
        soc = soc.iloc[order].reset_index(drop=True)

        dt = np.diff(t.to_numpy(dtype=float))
        dt_pos = dt[np.isfinite(dt) & (dt > 0)]
        dt_median = float(np.median(dt_pos)) if len(dt_pos) else np.nan
        dt_p10 = float(np.quantile(dt_pos, 0.10)) if len(dt_pos) else np.nan
        dt_p90 = float(np.quantile(dt_pos, 0.90)) if len(dt_pos) else np.nan

        current = i.to_numpy(dtype=float)
        voltage = v.to_numpy(dtype=float)
        current_diff = np.diff(current)

        current_scale = max(float(np.nanmedian(np.abs(current))), 1e-6)
        step_threshold = max(CURRENT_STEP_ABS_A, CURRENT_STEP_REL * current_scale)
        step_idx = np.where(np.abs(current_diff) >= step_threshold)[0] + 1

        # Near-zero-current relaxation windows.
        relax_mask = np.abs(current) <= RELAX_CURRENT_ABS_A
        relax_runs = [
            (a, b) for a, b in consecutive_true_runs(relax_mask)
            if (b - a + 1) >= MIN_RELAX_SAMPLES
        ]

        # Coarse profile classification.
        current_std = float(np.nanstd(current))
        current_range = float(np.nanmax(current) - np.nanmin(current))
        zero_fraction = float(np.mean(relax_mask))

        if len(step_idx) >= 4 and len(relax_runs) >= 1:
            classification = "PULSE_OR_STEP_RICH"
        elif len(step_idx) >= 1:
            classification = "STEPPED_CURRENT"
        elif current_std <= max(0.02, 0.03 * current_scale):
            classification = "NEAR_CONSTANT_CURRENT"
        else:
            classification = "VARIABLE_CURRENT"

        # 2RC readiness heuristic.
        if len(step_idx) >= 4 and len(relax_runs) >= 2 and np.isfinite(dt_median):
            dt_readiness = "STRONG_2RC_CANDIDATE"
        elif len(step_idx) >= 1 and np.isfinite(dt_median):
            dt_readiness = "LIMITED_DYNAMIC_IDENTIFIABILITY"
        else:
            dt_readiness = "POOR_FOR_2RC_FROM_THIS_PROFILE"

        duration_s = float(t.iloc[-1] - t.iloc[0])
        filename_cap = parse_capacity_from_filename(p.name)

        audit_rows.append({
            "file": p.name,
            "relative_path": str(p.relative_to(DATA_ROOT)),
            "rows": len(df),
            "valid_tvi_rows": len(t),
            "sheet": sheet,
            "capacity_from_filename_Ah": filename_cap,
            "time_col": str(time_col),
            "time_mode": time_mode,
            "voltage_col": str(volt_col),
            "current_col": str(curr_col),
            "soc_col": str(soc_col) if soc_col else "",
            "duration_s": duration_s,
            "dt_median_s": dt_median,
            "dt_p10_s": dt_p10,
            "dt_p90_s": dt_p90,
            "voltage_min_V": float(np.nanmin(voltage)),
            "voltage_max_V": float(np.nanmax(voltage)),
            "current_min_A": float(np.nanmin(current)),
            "current_max_A": float(np.nanmax(current)),
            "current_mean_A": float(np.nanmean(current)),
            "current_std_A": current_std,
            "current_range_A": current_range,
            "current_step_threshold_A": step_threshold,
            "detected_current_steps": int(len(step_idx)),
            "relaxation_windows": int(len(relax_runs)),
            "zero_current_fraction": zero_fraction,
            "soc_min": float(np.nanmin(soc)) if soc.notna().any() else np.nan,
            "soc_max": float(np.nanmax(soc)) if soc.notna().any() else np.nan,
            "profile_classification": classification,
            "dt_readiness": dt_readiness,
        })

        for idx in step_idx[:200]:
            transition_rows.append({
                "file": p.name,
                "sample_index": int(idx),
                "time_s": float(t.iloc[idx]),
                "current_before_A": float(current[idx-1]),
                "current_after_A": float(current[idx]),
                "delta_current_A": float(current[idx] - current[idx-1]),
                "voltage_before_V": float(voltage[idx-1]),
                "voltage_after_V": float(voltage[idx]),
                "delta_voltage_V": float(voltage[idx] - voltage[idx-1]),
            })

        # Save a few diagnostic figures.
        if example_plotted < 6:
            fig = plt.figure(figsize=(9, 5.5))
            ax1 = fig.add_subplot(111)
            ax1.plot(t / 3600.0, voltage, label="Voltage")
            ax1.set_xlabel("Elapsed time (h)")
            ax1.set_ylabel("Voltage (V)")
            ax2 = ax1.twinx()
            ax2.plot(t / 3600.0, current, alpha=0.65, label="Current")
            ax2.set_ylabel("Current (A)")
            ax1.set_title(f"{p.name} — {classification}")
            fig.tight_layout()
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", p.stem)
            fig.savefig(FIG / f"{safe}.png", dpi=300)
            fig.savefig(FIG / f"{safe}.pdf")
            plt.close(fig)
            example_plotted += 1

    except Exception as e:
        error_rows.append({
            "file": str(p.relative_to(DATA_ROOT)),
            "error_type": type(e).__name__,
            "error": str(e),
        })

audit = pd.DataFrame(audit_rows)
transitions = pd.DataFrame(transition_rows)
errors = pd.DataFrame(error_rows)

audit.to_csv(OUT / "01_lfp23_timeseries_audit.csv", index=False)
transitions.to_csv(OUT / "02_current_transition_candidates.csv", index=False)
errors.to_csv(OUT / "03_read_errors.csv", index=False)

if audit.empty:
    raise RuntimeError("No usable LFP23 files were audited.")

summary_by_profile = (
    audit.groupby(["profile_classification", "dt_readiness"], dropna=False)
    .agg(
        files=("file", "count"),
        median_rows=("valid_tvi_rows", "median"),
        median_dt_s=("dt_median_s", "median"),
        median_duration_h=("duration_s", lambda x: np.nanmedian(x) / 3600.0),
        median_current_steps=("detected_current_steps", "median"),
        median_relax_windows=("relaxation_windows", "median"),
    )
    .reset_index()
)
summary_by_profile.to_csv(OUT / "04_profile_readiness_summary.csv", index=False)

dataset_summary = pd.DataFrame([{
    "files_discovered": len(files),
    "files_audited": len(audit),
    "files_with_errors": len(errors),
    "files_strong_2rc_candidate":
        int((audit["dt_readiness"] == "STRONG_2RC_CANDIDATE").sum()),
    "files_limited_dynamic":
        int((audit["dt_readiness"] == "LIMITED_DYNAMIC_IDENTIFIABILITY").sum()),
    "files_poor_for_2rc":
        int((audit["dt_readiness"] == "POOR_FOR_2RC_FROM_THIS_PROFILE").sum()),
    "files_pulse_or_step_rich":
        int((audit["profile_classification"] == "PULSE_OR_STEP_RICH").sum()),
    "files_near_constant_current":
        int((audit["profile_classification"] == "NEAR_CONSTANT_CURRENT").sum()),
    "median_sampling_interval_s": float(audit["dt_median_s"].median()),
    "median_duration_h": float(audit["duration_s"].median() / 3600.0),
    "capacity_metadata_min_Ah": float(audit["capacity_from_filename_Ah"].min()),
    "capacity_metadata_max_Ah": float(audit["capacity_from_filename_Ah"].max()),
}])
dataset_summary.to_csv(OUT / "05_dataset_dt_readiness_summary.csv", index=False)

run_summary = {
    "day": "Day09",
    "dataset": "External_LFP23",
    "data_root": str(DATA_ROOT),
    "output_root": str(OUT),
    "purpose": "Raw time-series physics audit before any 2RC Digital Twin identification.",
    "heuristic_step_threshold": "max(0.05 A, 5% of median absolute current)",
    "relaxation_definition": "abs(current) <= 0.05 A for >=5 samples",
    "important_note": (
        "This stage does not certify 2RC parameter identifiability. "
        "It only assesses whether the measured current profile contains enough dynamic excitation "
        "to justify a subsequent equivalent-circuit identification experiment."
    )
}
(OUT / "06_run_summary.json").write_text(
    json.dumps(run_summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 09 COMPLETE ===")
print("\nDataset DT readiness:")
print(dataset_summary.to_string(index=False))
print("\nProfile/readiness summary:")
print(summary_by_profile.to_string(index=False))
print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("01_lfp23_timeseries_audit.csv")
print("04_profile_readiness_summary.csv")
print("05_dataset_dt_readiness_summary.csv")
print("06_run_summary.json")
