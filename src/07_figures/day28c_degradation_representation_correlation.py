# Filename: day28c_degradation_representation_correlation.py
# Purpose:
# Create a publication-quality degradation-representation correlation figure
# using ONLY this project's actual PulseBat processed data.
#
# This is an honest analogue of a literature correlation figure.
# It does NOT reproduce "Grouped by SOC / Mixed SOC", because the project source
# datasets do not share a uniform validated state variable (SOCR vs SOE).
#
# Instead:
# Panel (a): Pearson correlation between RAW U1-U21 features and SOH by domain.
# Panel (b): Pearson correlation between state-free REL_RATIO_NO_STATE features
#            and SOH by domain.
#
# This directly tests whether the final state-free representation retains
# degradation information across heterogeneous battery domains.
#
# Outputs:
# - PNG 300 dpi
# - true vector PDF
# - raw correlation CSV
# - REL_RATIO correlation CSV
# - schema/provenance audit CSV
# - caption
# - run summary
#
# No fabricated values are allowed.

from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(r"D:\SecondLife_Research")
DATA_DIR = ROOT / "Data" / "PulseBat"
OUT_DIR = ROOT / "Result" / "Day28c_DegradationRepresentationCorrelation"
FIG_DIR = OUT_DIR / "figures"

OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "LFP 35Ah": DATA_DIR / "LFP_35Ah_W_5000.xlsx",
    "LMO 10Ah": DATA_DIR / "LMO_10Ah_W_5000.xlsx",
    "NMC 2.1Ah": DATA_DIR / "NMC_2.1Ah_W_5000.xlsx",
    "NMC 21Ah": DATA_DIR / "NMC_21Ah_W_5000.xlsx",
}

RAW_FEATURES = [f"U{i}" for i in range(1, 22)]
REL_FEATURES = [f"R{i}" for i in range(2, 22)]

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def norm_name(x):
    return re.sub(r"[^a-z0-9]+", "", str(x).strip().lower())


SOH_CANDIDATES = [
    "SOH",
    "SOH_percent",
    "SOH(%)",
    "State of Health",
    "State_of_Health",
    "capacity_soh",
    "health",
]

def find_soh_column(df):
    normalized = {norm_name(c): c for c in df.columns}

    # Exact candidate match after normalization.
    for cand in SOH_CANDIDATES:
        key = norm_name(cand)
        if key in normalized:
            return normalized[key]

    # Safe fallback: column containing "soh".
    hits = [
        c for c in df.columns
        if "soh" in norm_name(c)
    ]

    if len(hits) == 1:
        return hits[0]

    raise RuntimeError(
        "Could not uniquely identify SOH column. "
        f"SOH-like candidates found: {hits}\n"
        f"Columns: {list(df.columns)}"
    )


def to_fractional_soh(series):
    s = pd.to_numeric(series, errors="coerce")

    finite = s[np.isfinite(s)]
    if finite.empty:
        return s, "unresolved"

    med = float(np.nanmedian(finite))

    # If median SOH is > 1.5, assume percentage scale (e.g. 80 means 80%).
    if med > 1.5:
        return s / 100.0, "percent_to_fraction"

    return s, "already_fraction"


def pearson_safe(x, y, min_n=8):
    x = pd.to_numeric(x, errors="coerce")
    y = pd.to_numeric(y, errors="coerce")

    mask = np.isfinite(x) & np.isfinite(y)
    n = int(mask.sum())

    if n < min_n:
        return np.nan, n

    xv = x[mask].to_numpy(dtype=float)
    yv = y[mask].to_numpy(dtype=float)

    if np.nanstd(xv) == 0 or np.nanstd(yv) == 0:
        return np.nan, n

    r = float(np.corrcoef(xv, yv)[0, 1])
    return r, n


# ------------------------------------------------------------
# Load + provenance audit
# ------------------------------------------------------------

all_frames = []
audit_rows = []

for domain, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    df = pd.read_excel(path)

    missing_features = [
        c for c in RAW_FEATURES
        if c not in df.columns
    ]
    if missing_features:
        raise RuntimeError(
            f"{domain}: missing U1-U21 columns: {missing_features}"
        )

    soh_col = find_soh_column(df)

    feat = df[RAW_FEATURES].apply(
        pd.to_numeric,
        errors="coerce"
    )

    soh_frac, soh_scale = to_fractional_soh(
        df[soh_col]
    )

    valid = (
        feat.notna().all(axis=1)
        & np.isfinite(soh_frac)
    )

    clean = feat.loc[valid].copy()
    clean["SOH_fraction"] = soh_frac.loc[valid].astype(float).values
    clean["Domain"] = domain

    # Derive the final state-free relative representation.
    u1 = clean["U1"].astype(float)

    if np.any(np.isclose(u1, 0.0)):
        raise RuntimeError(
            f"{domain}: U1 contains zero values; REL_RATIO undefined."
        )

    for i in range(2, 22):
        clean[f"R{i}"] = (
            clean[f"U{i}"] - clean["U1"]
        ) / clean["U1"].abs()

    all_frames.append(clean)

    audit_rows.append({
        "domain": domain,
        "file": str(path),
        "rows_total": int(len(df)),
        "rows_used": int(valid.sum()),
        "soh_column": str(soh_col),
        "soh_scale_handling": soh_scale,
        "soh_min_fraction": float(clean["SOH_fraction"].min()),
        "soh_max_fraction": float(clean["SOH_fraction"].max()),
        "all_U1_U21_present": True,
        "state_variable_used": False,
    })

audit = pd.DataFrame(audit_rows)
audit.to_csv(
    OUT_DIR / "01_schema_provenance_audit.csv",
    index=False
)

data = pd.concat(
    all_frames,
    ignore_index=True
)

# ------------------------------------------------------------
# Correlation matrices
# ------------------------------------------------------------

domains = list(FILES.keys())

raw_corr = pd.DataFrame(
    index=RAW_FEATURES,
    columns=domains,
    dtype=float
)

raw_n = pd.DataFrame(
    index=RAW_FEATURES,
    columns=domains,
    dtype=float
)

for domain in domains:
    d = data[data["Domain"] == domain]

    for feat in RAW_FEATURES:
        r, n = pearson_safe(
            d[feat],
            d["SOH_fraction"]
        )
        raw_corr.loc[feat, domain] = r
        raw_n.loc[feat, domain] = n

rel_corr = pd.DataFrame(
    index=REL_FEATURES,
    columns=domains,
    dtype=float
)

rel_n = pd.DataFrame(
    index=REL_FEATURES,
    columns=domains,
    dtype=float
)

for domain in domains:
    d = data[data["Domain"] == domain]

    for feat in REL_FEATURES:
        r, n = pearson_safe(
            d[feat],
            d["SOH_fraction"]
        )
        rel_corr.loc[feat, domain] = r
        rel_n.loc[feat, domain] = n

raw_corr.to_csv(
    OUT_DIR / "02_raw_U1_U21_SOHCorr.csv"
)
raw_n.to_csv(
    OUT_DIR / "03_raw_U1_U21_SOHCorr_n.csv"
)
rel_corr.to_csv(
    OUT_DIR / "04_REL_RATIO_SOHCorr.csv"
)
rel_n.to_csv(
    OUT_DIR / "05_REL_RATIO_SOHCorr_n.csv"
)

# ------------------------------------------------------------
# Summary statistics
# ------------------------------------------------------------

summary_rows = []

for domain in domains:
    raw_vals = raw_corr[domain].dropna().to_numpy(dtype=float)
    rel_vals = rel_corr[domain].dropna().to_numpy(dtype=float)

    summary_rows.append({
        "domain": domain,
        "raw_mean_abs_corr": (
            float(np.mean(np.abs(raw_vals)))
            if len(raw_vals)
            else np.nan
        ),
        "raw_max_abs_corr": (
            float(np.max(np.abs(raw_vals)))
            if len(raw_vals)
            else np.nan
        ),
        "rel_mean_abs_corr": (
            float(np.mean(np.abs(rel_vals)))
            if len(rel_vals)
            else np.nan
        ),
        "rel_max_abs_corr": (
            float(np.max(np.abs(rel_vals)))
            if len(rel_vals)
            else np.nan
        ),
    })

pd.DataFrame(summary_rows).to_csv(
    OUT_DIR / "06_correlation_summary.csv",
    index=False
)

# ------------------------------------------------------------
# Plot
# ------------------------------------------------------------

fig, axes = plt.subplots(
    1, 2,
    figsize=(10.5, 9.2),
    constrained_layout=True
)

cmap = "coolwarm"
vmin = -1.0
vmax = 1.0

im1 = axes[0].imshow(
    raw_corr.to_numpy(dtype=float),
    aspect="auto",
    cmap=cmap,
    vmin=vmin,
    vmax=vmax
)

axes[0].set_title(
    "(a) Raw processed voltage features",
    loc="left",
    fontweight="bold"
)
axes[0].set_xticks(
    np.arange(len(domains))
)
axes[0].set_xticklabels(
    domains,
    rotation=35,
    ha="right"
)
axes[0].set_yticks(
    np.arange(len(RAW_FEATURES))
)
axes[0].set_yticklabels(
    RAW_FEATURES
)
axes[0].set_xlabel("PulseBat domain")
axes[0].set_ylabel("Feature dimension")

im2 = axes[1].imshow(
    rel_corr.to_numpy(dtype=float),
    aspect="auto",
    cmap=cmap,
    vmin=vmin,
    vmax=vmax
)

axes[1].set_title(
    "(b) State-free REL_RATIO features",
    loc="left",
    fontweight="bold"
)
axes[1].set_xticks(
    np.arange(len(domains))
)
axes[1].set_xticklabels(
    domains,
    rotation=35,
    ha="right"
)
axes[1].set_yticks(
    np.arange(len(REL_FEATURES))
)
axes[1].set_yticklabels(
    [f"R{i}" for i in range(2, 22)]
)
axes[1].set_xlabel("PulseBat domain")
axes[1].set_ylabel("Derived feature dimension")

cbar = fig.colorbar(
    im2,
    ax=axes,
    shrink=0.82,
    pad=0.03
)
cbar.set_label("Pearson correlation with SOH")

fig.suptitle(
    "Degradation-representation correlation across heterogeneous PulseBat domains",
    fontsize=14,
    fontweight="bold"
)

png = FIG_DIR / "Figure_DegradationRepresentationCorrelation.png"
pdf = FIG_DIR / "Figure_DegradationRepresentationCorrelation.pdf"

fig.savefig(
    png,
    dpi=300,
    bbox_inches="tight"
)
fig.savefig(
    pdf,
    bbox_inches="tight"
)
plt.close(fig)

# ------------------------------------------------------------
# Caption and run summary
# ------------------------------------------------------------

caption = """# Proposed Figure Caption

**Degradation-representation correlation across heterogeneous PulseBat
domains.** Pearson correlation coefficients between state of health (SOH) and
the processed pulse-response dimensions are shown separately for the four
PulseBat battery domains. (a) Correlation of the raw processed U1–U21 voltage
features with SOH. (b) Correlation of the state-free relative representation,
\(r_i=(U_i-U_1)/|U_1|\), \(i=2,\ldots,21\), with SOH. The analysis uses only
observed PulseBat records with valid U1–U21 and SOH values; no SOC/SOCR/SOE
variable is used. The comparison evaluates whether the state-free
normalization retains degradation-related signal while reducing dependence on
absolute voltage level. Correlation is descriptive and is not interpreted as
causal evidence.
"""

(OUT_DIR / "07_proposed_caption.md").write_text(
    caption,
    encoding="utf-8"
)

run_summary = {
    "stage": "Day28c",
    "purpose": (
        "Own-data degradation-representation correlation analysis."
    ),
    "reference_figure_data_used": False,
    "soc_grouping_used": False,
    "reason_soc_grouping_not_used": (
        "Source datasets do not share a uniform validated state variable; "
        "final predictor is state-free."
    ),
    "panel_a": "Raw U1-U21 feature correlations with SOH by PulseBat domain",
    "panel_b": "REL_RATIO_NO_STATE feature correlations with SOH by PulseBat domain",
    "pearson_only_observed_data": True,
    "model_retraining": False,
    "scientific_results_changed": False,
    "png_300dpi": str(png),
    "vector_pdf": str(pdf),
}

(OUT_DIR / "08_run_summary.json").write_text(
    json.dumps(
        run_summary,
        indent=2
    ),
    encoding="utf-8"
)

print("\n=== DAY 28c COMPLETE ===")
print("Reference figure data used: NO")
print("SOC grouping used: NO")
print("Reason: state variable is not uniform/validated across source datasets")
print("Panel (a): actual RAW U1-U21 vs SOH correlations")
print("Panel (b): actual REL_RATIO_NO_STATE vs SOH correlations")
print("Model retraining: NO")
print("\nSaved:")
print(png)
print(pdf)
print(OUT_DIR / "01_schema_provenance_audit.csv")
print(OUT_DIR / "02_raw_U1_U21_SOHCorr.csv")
print(OUT_DIR / "04_REL_RATIO_SOHCorr.csv")
print(OUT_DIR / "06_correlation_summary.csv")
print(OUT_DIR / "07_proposed_caption.md")
print(OUT_DIR / "08_run_summary.json")
