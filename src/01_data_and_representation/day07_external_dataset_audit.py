r"""
Day 07 — External dataset readiness + schema audit
=================================================

Purpose
-------
Audit the two already-downloaded external datasets before any model transfer,
Digital Twin fitting, or manuscript claim is made.

Expected roots
--------------
D:\SecondLife_Research\Data\External_LFP23
D:\SecondLife_Research\Data\Bipolar709

This script:
1. Recursively inventories all files.
2. Reads supported tabular files safely:
   CSV / TXT / XLS / XLSX / Parquet / JSON / NPZ / NPY.
3. Detects candidate columns for:
   time, voltage, current, temperature, SOC, SOH/capacity, cell ID.
4. Reports row counts, numeric columns, missingness, and time-series readiness.
5. Classifies each file as:
   - MODEL_READY_TABULAR
   - DT_CANDIDATE_RAW_TIMESERIES
   - LABEL_ONLY_OR_METADATA
   - UNSUPPORTED_OR_UNKNOWN
6. Does NOT train a model and does NOT merge protocols.

Output
------
D:\SecondLife_Research\Result\Day07_ExternalDatasetAudit
"""

from pathlib import Path
import json
import re
import warnings
import numpy as np
import pandas as pd

ROOT = Path(r"D:\SecondLife_Research")
DATASETS = {
    "External_LFP23": ROOT / "Data" / "External_LFP23",
    "Bipolar709": ROOT / "Data" / "Bipolar709",
}
OUT = ROOT / "Result" / "Day07_ExternalDatasetAudit"
OUT.mkdir(parents=True, exist_ok=True)

SUPPORTED = {".csv", ".txt", ".tsv", ".xls", ".xlsx", ".parquet", ".json", ".npz", ".npy"}

TIME_PATTERNS = [
    r"^time$", r"time[_\s]*s", r"timestamp", r"elapsed", r"test[_\s]*time",
    r"record[_\s]*time", r"step[_\s]*time"
]
VOLT_PATTERNS = [r"voltage", r"volt", r"^v$", r"terminal[_\s]*v"]
CURR_PATTERNS = [r"current", r"^i$", r"amp", r"amps"]
TEMP_PATTERNS = [r"temperature", r"temp", r"surface[_\s]*t"]
SOC_PATTERNS = [r"^soc$", r"so[cC]r", r"state[_\s]*of[_\s]*charge"]
SOH_PATTERNS = [r"^soh$", r"state[_\s]*of[_\s]*health"]
CAP_PATTERNS = [r"capacity", r"cap[_\s]*ah", r"discharge[_\s]*capacity", r"q[_\s]*actual"]
ID_PATTERNS = [r"cell[_\s]*id", r"battery[_\s]*id", r"^id$", r"cell", r"battery"]


def match_cols(columns, patterns):
    found = []
    for c in columns:
        s = str(c).strip()
        for p in patterns:
            if re.search(p, s, flags=re.I):
                found.append(s)
                break
    return found


def safe_read(path):
    ext = path.suffix.lower()

    if ext == ".csv":
        return pd.read_csv(path, low_memory=False)

    if ext in {".txt", ".tsv"}:
        # try delimiter inference
        return pd.read_csv(path, sep=None, engine="python", low_memory=False)

    if ext in {".xls", ".xlsx"}:
        xl = pd.ExcelFile(path)
        # Use first non-empty sheet; inventory sheet names separately.
        for sheet in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            if not df.dropna(how="all").empty:
                return df
        return pd.DataFrame()

    if ext == ".parquet":
        return pd.read_parquet(path)

    if ext == ".json":
        try:
            return pd.read_json(path)
        except Exception:
            obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(obj, list):
                return pd.DataFrame(obj)
            if isinstance(obj, dict):
                # try top-level records
                for v in obj.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        return pd.DataFrame(v)
                return pd.json_normalize(obj)
            raise

    if ext == ".npz":
        obj = np.load(path, allow_pickle=True)
        cols = {}
        max_len = 0
        for k in obj.files:
            arr = np.asarray(obj[k])
            if arr.ndim == 1:
                cols[k] = arr
                max_len = max(max_len, len(arr))
        if not cols:
            return pd.DataFrame()
        # Only combine equal-length 1D arrays
        common = {k: v for k, v in cols.items() if len(v) == max_len}
        return pd.DataFrame(common)

    if ext == ".npy":
        arr = np.load(path, allow_pickle=True)
        if arr.dtype.names:
            return pd.DataFrame(arr)
        if arr.ndim == 2:
            return pd.DataFrame(arr)
        if arr.ndim == 1:
            return pd.DataFrame({"value": arr})
        return pd.DataFrame()

    raise ValueError(f"Unsupported extension: {ext}")


def classify(time_cols, volt_cols, curr_cols, soh_cols, cap_cols, soc_cols, n_numeric):
    has_raw = bool(time_cols and volt_cols and curr_cols)
    has_label = bool(soh_cols or cap_cols)

    if has_raw:
        return "DT_CANDIDATE_RAW_TIMESERIES"
    if n_numeric >= 3 and (has_label or soc_cols):
        return "MODEL_READY_TABULAR"
    if has_label or soc_cols:
        return "LABEL_ONLY_OR_METADATA"
    return "UNSUPPORTED_OR_UNKNOWN"


inventory_rows = []
schema_rows = []
errors = []

for dataset_name, dataset_root in DATASETS.items():
    if not dataset_root.exists():
        inventory_rows.append({
            "dataset": dataset_name,
            "path": str(dataset_root),
            "relative_path": "",
            "extension": "",
            "size_MB": np.nan,
            "supported": False,
            "status": "DATASET_ROOT_MISSING",
        })
        continue

    files = sorted(p for p in dataset_root.rglob("*") if p.is_file())

    for p in files:
        rel = p.relative_to(dataset_root)
        ext = p.suffix.lower()
        supported = ext in SUPPORTED

        inventory_rows.append({
            "dataset": dataset_name,
            "path": str(p),
            "relative_path": str(rel),
            "extension": ext,
            "size_MB": p.stat().st_size / (1024**2),
            "supported": supported,
            "status": "FOUND",
        })

        if not supported:
            continue

        try:
            df = safe_read(p)
            df = df.dropna(how="all")
            cols = [str(c).strip() for c in df.columns]
            df.columns = cols

            numeric_df = df.apply(pd.to_numeric, errors="coerce")
            numeric_cols = [
                c for c in cols
                if numeric_df[c].notna().sum() > 0
            ]

            time_cols = match_cols(cols, TIME_PATTERNS)
            volt_cols = match_cols(cols, VOLT_PATTERNS)
            curr_cols = match_cols(cols, CURR_PATTERNS)
            temp_cols = match_cols(cols, TEMP_PATTERNS)
            soc_cols = match_cols(cols, SOC_PATTERNS)
            soh_cols = match_cols(cols, SOH_PATTERNS)
            cap_cols = match_cols(cols, CAP_PATTERNS)
            id_cols = match_cols(cols, ID_PATTERNS)

            cls = classify(
                time_cols, volt_cols, curr_cols,
                soh_cols, cap_cols, soc_cols,
                len(numeric_cols)
            )

            missing_fraction = (
                float(df.isna().mean().mean())
                if df.shape[0] and df.shape[1] else np.nan
            )

            schema_rows.append({
                "dataset": dataset_name,
                "relative_path": str(rel),
                "rows": len(df),
                "columns": len(cols),
                "numeric_columns": len(numeric_cols),
                "missing_fraction": missing_fraction,
                "time_candidates": " | ".join(time_cols),
                "voltage_candidates": " | ".join(volt_cols),
                "current_candidates": " | ".join(curr_cols),
                "temperature_candidates": " | ".join(temp_cols),
                "soc_candidates": " | ".join(soc_cols),
                "soh_candidates": " | ".join(soh_cols),
                "capacity_candidates": " | ".join(cap_cols),
                "id_candidates": " | ".join(id_cols),
                "classification": cls,
                "first_25_columns": " | ".join(cols[:25]),
            })

        except Exception as e:
            errors.append({
                "dataset": dataset_name,
                "relative_path": str(rel),
                "error_type": type(e).__name__,
                "error": str(e),
            })


inventory = pd.DataFrame(inventory_rows)
schema = pd.DataFrame(schema_rows)
error_df = pd.DataFrame(errors)

inventory.to_csv(OUT / "01_external_file_inventory.csv", index=False)
schema.to_csv(OUT / "02_external_schema_audit.csv", index=False)
error_df.to_csv(OUT / "03_read_errors.csv", index=False)

# Dataset-level readiness summary
summary_rows = []

for dataset_name in DATASETS:
    inv = inventory[inventory["dataset"] == dataset_name].copy()
    sch = schema[schema["dataset"] == dataset_name].copy()

    dt_candidates = (
        sch["classification"].eq("DT_CANDIDATE_RAW_TIMESERIES").sum()
        if not sch.empty else 0
    )
    model_candidates = (
        sch["classification"].eq("MODEL_READY_TABULAR").sum()
        if not sch.empty else 0
    )
    label_only = (
        sch["classification"].eq("LABEL_ONLY_OR_METADATA").sum()
        if not sch.empty else 0
    )

    if dt_candidates > 0:
        recommendation = "PROCEED_TO_RAW_TIMESERIES_DT_AUDIT"
    elif model_candidates > 0:
        recommendation = "PROCEED_TO_EXTERNAL_ML_HARMONIZATION"
    elif label_only > 0:
        recommendation = "MANUAL_SCHEMA_REVIEW_REQUIRED"
    else:
        recommendation = "NOT_READY_OR_UNSUPPORTED"

    summary_rows.append({
        "dataset": dataset_name,
        "files_found": int(len(inv)),
        "supported_files_read": int(len(sch)),
        "total_size_MB": float(inv["size_MB"].sum()) if not inv.empty else 0.0,
        "dt_candidate_files": int(dt_candidates),
        "model_ready_files": int(model_candidates),
        "label_or_metadata_files": int(label_only),
        "read_errors": int((error_df["dataset"] == dataset_name).sum()) if not error_df.empty else 0,
        "recommended_next_action": recommendation,
    })

readiness = pd.DataFrame(summary_rows)
readiness.to_csv(OUT / "04_external_dataset_readiness.csv", index=False)

# Compact DT candidate list
dt_candidates = schema[
    schema["classification"] == "DT_CANDIDATE_RAW_TIMESERIES"
].copy()
dt_candidates.to_csv(OUT / "05_dt_candidate_files.csv", index=False)

# Compact model-ready list
model_ready = schema[
    schema["classification"] == "MODEL_READY_TABULAR"
].copy()
model_ready.to_csv(OUT / "06_model_ready_external_files.csv", index=False)

run_summary = {
    "day": "Day07",
    "purpose": "External dataset readiness and DT feasibility audit before protocol harmonization.",
    "datasets": {k: str(v) for k, v in DATASETS.items()},
    "supported_extensions": sorted(SUPPORTED),
    "output_dir": str(OUT),
    "important_method_note": (
        "This stage only inventories and classifies external files. "
        "No datasets are merged, no protocol equivalence is assumed, "
        "and no model is trained."
    ),
}
(OUT / "07_run_summary.json").write_text(
    json.dumps(run_summary, indent=2), encoding="utf-8"
)

print("\n=== DAY 07 EXTERNAL DATASET AUDIT COMPLETE ===")
print("\nReadiness summary:")
print(readiness.to_string(index=False))

if not dt_candidates.empty:
    print("\nDT candidate raw time-series files:")
    print(
        dt_candidates[
            [
                "dataset", "relative_path", "rows",
                "time_candidates", "voltage_candidates", "current_candidates"
            ]
        ].head(30).to_string(index=False)
    )
else:
    print("\nNo automatic DT candidate files detected.")

if not model_ready.empty:
    print("\nModel-ready external files:")
    print(
        model_ready[
            ["dataset", "relative_path", "rows", "classification"]
        ].head(30).to_string(index=False)
    )

if not error_df.empty:
    print("\nSome supported files could not be read:")
    print(error_df.head(20).to_string(index=False))

print(f"\nResults saved to:\n{OUT}")
print("\nSend me:")
print("02_external_schema_audit.csv")
print("04_external_dataset_readiness.csv")
print("05_dt_candidate_files.csv")
print("06_model_ready_external_files.csv")
print("07_run_summary.json")
