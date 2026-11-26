r"""
Day 10 — LFP23 charge-balance / SOC-state Digital Twin validation
================================================================

Purpose
-------
Day09 showed that External_LFP23 contains 1 Hz charging time series but does NOT
contain the step/pulse excitation required for defensible 2RC identification.

Therefore Day10 uses a scientifically appropriate physics model:

    dSOC/dt = I / (3600 * Q_eff)

for charging-positive current convention.

The script:
1. Reads each LFP23 charging file.
2. Parses Date_Time, Voltage(V), Current(A), SOC/SOC_fake.
3. Integrates current to cumulative charge throughput Ah.
4. Fits an effective capacity Q_eff from measured SOC vs cumulative Ah.
5. Reconstructs SOC using:
      a) filename capacity Q_filename
      b) fitted effective capacity Q_eff
6. Quantifies:
   - Q_eff
   - filename capacity
   - capacity consistency error
   - SOC RMSE / MAE
   - final SOC error
   - charge throughput
7. Classifies the file-level SOC-state twin as:
   - STRONG
   - MODERATE
   - WEAK

This is a SOC-state / charge-balance Digital Twin, NOT a 2RC electrical twin.

Expected input:
D:\SecondLife_Research\Data\External_LFP23

Output:
D:\SecondLife_Research\Result\Day10_LFP23_SOC_StateTwin
"""

from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(r"D:\SecondLife_Research")
DATA_ROOT = ROOT / "Data" / "External_LFP23"
OUT = ROOT / "Result" / "Day10_LFP23_SOC_StateTwin"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

SUPPORTED = {".xlsx", ".xls", ".csv"}

TIME_CANDIDATES = ["Date_Time", "DateTime", "datetime", "Timestamp", "Time", "time"]
VOLT_CANDIDATES = ["Voltage(V)", "Voltage", "voltage", "V"]
CURR_CANDIDATES = ["Current(A)", "Current", "current", "I"]
SOC_CANDIDATES = ["SOC", "SOC_fake", "SOCR", "soc"]

MIN_VALID_ROWS = 50
EPS = 1e-12


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
    raise ValueError(f"Unsupported file: {path}")


def first_existing(columns, candidates):
    lower = {str(c).strip().lower(): c for c in columns}
    for name in candidates:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def parse_capacity_from_filename(name):
    m = re.search(r"(\d+(?:\.\d+)?)\s*Ah", str(name), flags=re.I)
    return float(m.group(1)) if m else np.nan


def parse_time_seconds(s):
    dt = pd.to_datetime(s, errors="coerce")
    if dt.notna().mean() >= 0.8:
        return (dt - dt.iloc[0]).dt.total_seconds().astype(float), "datetime"

    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() >= 0.8:
        return num.astype(float) - float(num.dropna().iloc[0]), "numeric"

    return pd.Series(np.nan, index=s.index), "unparseable"


def normalize_soc(s):
    s = pd.to_numeric(s, errors="coerce")
    valid = s.dropna()
    if valid.empty:
        return s
    if valid.quantile(0.95) > 1.5:
        return s / 100.0
    return s


def trapezoid_cumulative_ah(time_s, current_a):
    t = np.asarray(time_s, dtype=float)
    i = np.asarray(current_a, dtype=float)

    dt = np.diff(t)
    i_mid = 0.5 * (i[1:] + i[:-1])

    dq = i_mid * dt / 3600.0
    cum = np.concatenate([[0.0], np.cumsum(dq)])
    return cum


def rmse(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return float(np.sqrt(np.mean((a - b) ** 2)))


def mae(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return float(np.mean(np.abs(a - b)))


def classify_twin(cap_error_pct, soc_rmse_eff):
    if cap_error_pct <= 5 and soc_rmse_eff <= 0.02:
        return "STRONG"
    if cap_error_pct <= 10 and soc_rmse_eff <= 0.04:
        return "MODERATE"
    return "WEAK"


files = sorted(
    p for p in DATA_ROOT.rglob("*")
    if p.is_file() and p.suffix.lower() in SUPPORTED
)

if not files:
    raise FileNotFoundError(f"No supported files under {DATA_ROOT}")

summary_rows = []
trajectory_rows = []
errors = []

for idx_file, p in enumerate(files, 1):
    try:
        df, sheet = read_first_nonempty(p)
        df = df.dropna(how="all").copy()
        df.columns = [str(c).strip() for c in df.columns]

        time_col = first_existing(df.columns, TIME_CANDIDATES)
        volt_col = first_existing(df.columns, VOLT_CANDIDATES)
        curr_col = first_existing(df.columns, CURR_CANDIDATES)
        soc_col = first_existing(df.columns, SOC_CANDIDATES)

        if not all([time_col, curr_col, soc_col]):
            raise ValueError(
                f"Missing core column(s): time={time_col}, current={curr_col}, soc={soc_col}"
            )

        t, time_mode = parse_time_seconds(df[time_col])
        current = pd.to_numeric(df[curr_col], errors="coerce")
        soc = normalize_soc(df[soc_col])
        voltage = (
            pd.to_numeric(df[volt_col], errors="coerce")
            if volt_col is not None
            else pd.Series(np.nan, index=df.index)
        )

        good = t.notna() & current.notna() & soc.notna()
        t = t[good].reset_index(drop=True)
        current = current[good].reset_index(drop=True)
        soc = soc[good].reset_index(drop=True)
        voltage = voltage[good].reset_index(drop=True)

        if len(t) < MIN_VALID_ROWS:
            raise ValueError(f"Only {len(t)} valid rows")

        # Sort by time.
        order = np.argsort(t.to_numpy(dtype=float))
        t = t.iloc[order].reset_index(drop=True)
        current = current.iloc[order].reset_index(drop=True)
        soc = soc.iloc[order].reset_index(drop=True)
        voltage = voltage.iloc[order].reset_index(drop=True)

        # Determine charging sign from SOC trend and net current throughput.
        raw_q = trapezoid_cumulative_ah(t, current)
        delta_soc = float(soc.iloc[-1] - soc.iloc[0])

        if abs(delta_soc) < 1e-4:
            raise ValueError("SOC change too small for capacity identification")

        # If current integration and SOC move in opposite directions, flip current sign.
        if np.sign(raw_q[-1]) != np.sign(delta_soc):
            current = -current
            sign_flipped = True
        else:
            sign_flipped = False

        q_ah = trapezoid_cumulative_ah(t, current)

        # Define x=charge throughput relative to first sample, y=SOC increment.
        x = q_ah - q_ah[0]
        y = soc.to_numpy(dtype=float) - float(soc.iloc[0])

        # Fit y = beta * x through origin. Q_eff = 1/beta.
        denom = float(np.dot(x, x))
        if denom <= EPS:
            raise ValueError("Insufficient charge-throughput variation")

        beta = float(np.dot(x, y) / denom)
        if beta <= 0:
            raise ValueError(f"Non-positive fitted SOC/Ah slope: {beta}")

        q_eff = 1.0 / beta
        q_filename = parse_capacity_from_filename(p.name)

        soc0 = float(soc.iloc[0])

        # SOC twin with fitted effective capacity.
        soc_eff = soc0 + x / q_eff

        # SOC twin with filename capacity.
        if np.isfinite(q_filename) and q_filename > 0:
            soc_file = soc0 + x / q_filename
            soc_rmse_file = rmse(soc, soc_file)
            soc_mae_file = mae(soc, soc_file)
            final_error_file = float(soc_file[-1] - soc.iloc[-1])
            cap_error_pct = abs(q_eff - q_filename) / q_filename * 100.0
        else:
            soc_file = np.full(len(soc), np.nan)
            soc_rmse_file = np.nan
            soc_mae_file = np.nan
            final_error_file = np.nan
            cap_error_pct = np.nan

        soc_rmse_eff = rmse(soc, soc_eff)
        soc_mae_eff = mae(soc, soc_eff)
        final_error_eff = float(soc_eff[-1] - soc.iloc[-1])

        classification = classify_twin(
            cap_error_pct if np.isfinite(cap_error_pct) else np.inf,
            soc_rmse_eff
        )

        dt = np.diff(t.to_numpy(dtype=float))
        dt_pos = dt[dt > 0]

        summary_rows.append({
            "file": p.name,
            "sheet": sheet,
            "time_mode": time_mode,
            "time_col": str(time_col),
            "current_col": str(curr_col),
            "soc_col": str(soc_col),
            "voltage_col": str(volt_col) if volt_col else "",
            "rows_valid": len(t),
            "duration_h": float((t.iloc[-1] - t.iloc[0]) / 3600.0),
            "median_dt_s": float(np.median(dt_pos)) if len(dt_pos) else np.nan,
            "current_sign_flipped": sign_flipped,
            "soc_initial": float(soc.iloc[0]),
            "soc_final": float(soc.iloc[-1]),
            "delta_soc": delta_soc,
            "charge_throughput_Ah": float(x[-1]),
            "Q_filename_Ah": q_filename,
            "Q_eff_fit_Ah": q_eff,
            "capacity_abs_error_Ah":
                abs(q_eff - q_filename) if np.isfinite(q_filename) else np.nan,
            "capacity_error_percent": cap_error_pct,
            "SOC_RMSE_filename": soc_rmse_file,
            "SOC_MAE_filename": soc_mae_file,
            "SOC_final_error_filename": final_error_file,
            "SOC_RMSE_Qeff": soc_rmse_eff,
            "SOC_MAE_Qeff": soc_mae_eff,
            "SOC_final_error_Qeff": final_error_eff,
            "state_twin_classification": classification,
        })

        # Save downsampled trajectories for pooled inspection.
        step = max(1, len(t) // 500)
        take = np.arange(0, len(t), step)
        for j in take:
            trajectory_rows.append({
                "file": p.name,
                "time_s": float(t.iloc[j]),
                "voltage_V": float(voltage.iloc[j]) if np.isfinite(voltage.iloc[j]) else np.nan,
                "current_A": float(current.iloc[j]),
                "SOC_measured": float(soc.iloc[j]),
                "SOC_twin_filename": float(soc_file[j]) if np.isfinite(soc_file[j]) else np.nan,
                "SOC_twin_Qeff": float(soc_eff[j]),
            })

        # Per-file figure.
        fig = plt.figure(figsize=(8.5, 5.4))
        ax = fig.add_subplot(111)
        ax.plot(t / 3600.0, soc, label="Measured SOC")
        if np.isfinite(soc_file).any():
            ax.plot(t / 3600.0, soc_file, linestyle="--", label="Twin using filename Q")
        ax.plot(t / 3600.0, soc_eff, linestyle=":", label="Twin using fitted Qeff")
        ax.set_xlabel("Elapsed time (h)")
        ax.set_ylabel("SOC")
        ax.set_title(
            f"{p.stem}: Qfile={q_filename:.3f} Ah, Qeff={q_eff:.3f} Ah"
            if np.isfinite(q_filename)
            else f"{p.stem}: Qeff={q_eff:.3f} Ah"
        )
        ax.legend()
        fig.tight_layout()

        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", p.stem)
        fig.savefig(FIG / f"{safe}_SOC_Twin.png", dpi=300)
        fig.savefig(FIG / f"{safe}_SOC_Twin.pdf")
        plt.close(fig)

    except Exception as e:
        errors.append({
            "file": str(p.relative_to(DATA_ROOT)),
            "error_type": type(e).__name__,
            "error": str(e),
        })

results = pd.DataFrame(summary_rows)
trajectories = pd.DataFrame(trajectory_rows)
error_df = pd.DataFrame(errors)

results.to_csv(OUT / "01_soc_state_twin_file_metrics.csv", index=False)
trajectories.to_csv(OUT / "02_soc_state_twin_trajectories.csv", index=False)
error_df.to_csv(OUT / "03_read_or_fit_errors.csv", index=False)

if results.empty:
    raise RuntimeError("No LFP23 files produced valid SOC-state twin metrics.")

# Aggregate statistics.
aggregate = pd.DataFrame([{
    "files_successful": len(results),
    "files_failed": len(error_df),
    "Q_filename_mean_Ah": float(results["Q_filename_Ah"].mean()),
    "Q_eff_mean_Ah": float(results["Q_eff_fit_Ah"].mean()),
    "capacity_error_median_percent": float(results["capacity_error_percent"].median()),
    "capacity_error_p90_percent": float(results["capacity_error_percent"].quantile(0.90)),
    "SOC_RMSE_filename_mean": float(results["SOC_RMSE_filename"].mean()),
    "SOC_RMSE_Qeff_mean": float(results["SOC_RMSE_Qeff"].mean()),
    "SOC_MAE_Qeff_mean": float(results["SOC_MAE_Qeff"].mean()),
    "strong_twins":
        int((results["state_twin_classification"] == "STRONG").sum()),
    "moderate_twins":
        int((results["state_twin_classification"] == "MODERATE").sum()),
    "weak_twins":
        int((results["state_twin_classification"] == "WEAK").sum()),
}])
aggregate.to_csv(OUT / "04_soc_state_twin_aggregate.csv", index=False)

# Capacity agreement figure.
valid = results[
    results["Q_filename_Ah"].notna() & results["Q_eff_fit_Ah"].notna()
].copy()

plt.figure(figsize=(6.2, 5.6))
plt.scatter(valid["Q_filename_Ah"], valid["Q_eff_fit_Ah"])
lo = min(valid["Q_filename_Ah"].min(), valid["Q_eff_fit_Ah"].min())
hi = max(valid["Q_filename_Ah"].max(), valid["Q_eff_fit_Ah"].max())
plt.plot([lo, hi], [lo, hi], linestyle="--")
plt.xlabel("Filename capacity (Ah)")
plt.ylabel("Physics-fitted Qeff (Ah)")
plt.title("Charge-balance capacity consistency")
plt.tight_layout()
plt.savefig(OUT / "Fig01_Qfilename_vs_Qeff.png", dpi=300)
plt.savefig(OUT / "Fig01_Qfilename_vs_Qeff.pdf")
plt.close()

# Capacity error distribution.
plt.figure(figsize=(7.0, 4.8))
plt.hist(valid["capacity_error_percent"], bins=min(12, max(5, len(valid)//2)))
plt.xlabel("|Qeff - Qfilename| / Qfilename (%)")
plt.ylabel("Files")
plt.title("Capacity consistency error across LFP23")
plt.tight_layout()
plt.savefig(OUT / "Fig02_Capacity_Error_Distribution.png", dpi=300)
plt.savefig(OUT / "Fig02_Capacity_Error_Distribution.pdf")
plt.close()

# SOC RMSE comparison.
plt.figure(figsize=(7.0, 4.8))
x = np.arange(len(results))
plt.plot(x, results["SOC_RMSE_filename"], marker="o", label="Filename Q")
plt.plot(x, results["SOC_RMSE_Qeff"], marker="o", label="Fitted Qeff")
plt.xlabel("LFP23 file index")
plt.ylabel("SOC RMSE")
plt.title("SOC-state twin reconstruction error")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "Fig03_SOC_RMSE_Comparison.png", dpi=300)
plt.savefig(OUT / "Fig03_SOC_RMSE_Comparison.pdf")
plt.close()

run_summary = {
    "day": "Day10",
    "dataset": "External_LFP23",
    "digital_twin_scope": "SOC-state / charge-balance twin",
    "governing_equation": "dSOC/dt = I/(3600*Q_eff)",
    "important_scope_boundary": (
        "This is NOT a 1RC/2RC electrical Digital Twin. Day09 showed that the "
        "LFP23 charge profiles lack pulse/relaxation excitation required for "
        "defensible 2RC identification."
    ),
    "output_dir": str(OUT),
}
(OUT / "05_run_summary.json").write_text(
    json.dumps(run_summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 10 COMPLETE ===")
print("\nSOC-state twin aggregate:")
print(aggregate.to_string(index=False))

print("\nClassification counts:")
print(results["state_twin_classification"].value_counts().to_string())

print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("01_soc_state_twin_file_metrics.csv")
print("04_soc_state_twin_aggregate.csv")
print("05_run_summary.json")
