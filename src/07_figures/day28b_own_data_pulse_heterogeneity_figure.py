# Filename: day28b_own_data_pulse_heterogeneity_figure.py
# Purpose:
# Create a two-panel publication figure inspired by the REFERENCE layout,
# but using ONLY this project's own PulseBat processed data.
#
# Panel (a):
#   Actual U1-U21 feature values from one representative real PulseBat row
#   + a clearly labeled schematic protocol C-rate guide.
#
# Panel (b):
#   Actual U1-U21 distributions across the four PulseBat domains.
#
# Outputs:
#   PNG 300 dpi + true vector PDF + representative-row CSV + audit CSV
#
# IMPORTANT:
# This script does NOT reconstruct or invent a raw 100 Hz voltage trace.

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(r"D:\SecondLife_Research")
DATA_DIR = ROOT / "Data" / "PulseBat"
OUT_DIR = ROOT / "Result" / "Day28b_OwnData_PulseHeterogeneity"
FIG_DIR = OUT_DIR / "figures"

OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "LFP 35Ah": DATA_DIR / "LFP_35Ah_W_5000.xlsx",
    "LMO 10Ah": DATA_DIR / "LMO_10Ah_W_5000.xlsx",
    "NMC 2.1Ah": DATA_DIR / "NMC_2.1Ah_W_5000.xlsx",
    "NMC 21Ah": DATA_DIR / "NMC_21Ah_W_5000.xlsx",
}

FEATURES = [f"U{i}" for i in range(1, 22)]

# ------------------------------------------------------------
# 1. Load and validate actual PulseBat processed data
# ------------------------------------------------------------
frames = []
audit_rows = []

for domain, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(f"Missing PulseBat file: {path}")

    df = pd.read_excel(path)

    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise RuntimeError(
            f"{domain}: missing required feature columns: {missing}"
        )

    feat = df[FEATURES].apply(pd.to_numeric, errors="coerce")
    valid = feat.notna().all(axis=1)

    clean = feat.loc[valid].copy()
    clean["Domain"] = domain
    clean["SourceRow"] = np.where(valid)[0]

    frames.append(clean)

    audit_rows.append({
        "domain": domain,
        "file": str(path),
        "rows_total": int(len(df)),
        "rows_with_complete_U1_U21": int(valid.sum()),
        "rows_removed_for_missing_feature": int((~valid).sum()),
    })

all_data = pd.concat(frames, ignore_index=True)

if all_data.empty:
    raise RuntimeError("No complete U1-U21 rows were found.")

audit = pd.DataFrame(audit_rows)
audit.to_csv(
    OUT_DIR / "01_data_audit.csv",
    index=False
)

# ------------------------------------------------------------
# 2. Select a REAL representative row for panel (a)
# ------------------------------------------------------------
# Use the NMC 2.1Ah domain as a representative example.
# The selected row is the observed row nearest to the domain median
# in standardized U1-U21 feature space. No synthetic voltage row is created.

REP_DOMAIN = "NMC 2.1Ah"

rep_pool = all_data.loc[
    all_data["Domain"] == REP_DOMAIN,
    FEATURES + ["SourceRow"]
].copy()

if rep_pool.empty:
    raise RuntimeError(f"No complete rows available for {REP_DOMAIN}")

X = rep_pool[FEATURES].to_numpy(dtype=float)
med = np.nanmedian(X, axis=0)
scale = np.nanstd(X, axis=0)
scale[~np.isfinite(scale) | (scale == 0)] = 1.0

dist = np.sqrt(
    np.sum(((X - med) / scale) ** 2, axis=1)
)

rep_i = int(np.argmin(dist))
rep = rep_pool.iloc[rep_i]

representative_csv = pd.DataFrame({
    "feature": FEATURES,
    "voltage_V": [float(rep[u]) for u in FEATURES],
})

representative_csv.to_csv(
    OUT_DIR / "02_representative_real_row_U1_U21.csv",
    index=False
)

# ------------------------------------------------------------
# 3. Protocol C-rate guide for panel (a)
# ------------------------------------------------------------
# This is NOT measured current.
# It is a schematic guide based on the known PulseBat feature semantics:
#
# U1      : steady OCV after rest
# U2-U9   : 0.5C positive/negative pulse-rest turning points
# U10-U17 : 1C positive/negative pulse-rest turning points
# U18-U21 : 1.5C positive pulse/rest turning points
#
# A feature-index guide is used because the processed files do not contain
# the raw 100 Hz time/current trace required for a physically reconstructed
# continuous waveform.

x = np.arange(1, 22)
v = representative_csv["voltage_V"].to_numpy()

# Schematic per-feature C-rate guide.
# NaN at U1 because it is the rested reference point.
c_rate = np.array([
    np.nan,          # U1
    +0.5, +0.5, 0,  # U2-U4
    -0.5, -0.5, 0, 0, 0,  # U5-U9
    +1.0, +1.0, 0, 0,      # U10-U13
    -1.0, -1.0, 0, 0,      # U14-U17
    +1.5, +1.5, 0, 0       # U18-U21
], dtype=float)

if len(c_rate) != 21:
    raise RuntimeError("Internal protocol guide length error.")

# ------------------------------------------------------------
# 4. Build publication figure
# ------------------------------------------------------------
fig = plt.figure(figsize=(14.0, 10.5))
gs = fig.add_gridspec(
    2, 1,
    height_ratios=[1.0, 1.35],
    hspace=0.30
)

# =========================
# Panel (a)
# =========================
ax1 = fig.add_subplot(gs[0, 0])
ax1b = ax1.twinx()

ax1.plot(
    x, v,
    marker="o",
    linewidth=1.8,
    markersize=5.5,
    label=f"Actual representative row: {REP_DOMAIN}"
)

# Schematic C-rate guide on secondary axis.
valid_c = np.isfinite(c_rate)
ax1b.step(
    x[valid_c],
    c_rate[valid_c],
    where="mid",
    linewidth=1.7,
    linestyle="--",
    label="Protocol C-rate guide (schematic)"
)

for i, (xi, yi) in enumerate(zip(x, v), start=1):
    ax1.annotate(
        f"U{i}",
        (xi, yi),
        xytext=(0, 7 if i % 2 else -13),
        textcoords="offset points",
        ha="center",
        fontsize=7.5
    )

ax1.axvspan(1.5, 9.5, alpha=0.06)
ax1.axvspan(9.5, 17.5, alpha=0.06)
ax1.axvspan(17.5, 21.5, alpha=0.06)

ax1.text(
    5.5, 0.98, "0.5C feature block",
    transform=ax1.get_xaxis_transform(),
    ha="center", va="top", fontsize=9
)
ax1.text(
    13.5, 0.98, "1C feature block",
    transform=ax1.get_xaxis_transform(),
    ha="center", va="top", fontsize=9
)
ax1.text(
    19.5, 0.98, "1.5C feature block",
    transform=ax1.get_xaxis_transform(),
    ha="center", va="top", fontsize=9
)

ax1.set_xlim(0.5, 21.5)
ax1.set_xticks(x)
ax1.set_xlabel("Pulse feature index")
ax1.set_ylabel("Voltage [V]")
ax1b.set_ylabel("Protocol C-rate [C] (schematic)")
ax1.set_title(
    "(a) Actual PulseBat U1–U21 voltage features and pulse-protocol semantics",
    loc="left",
    fontweight="bold"
)

# Combined legend.
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax1b.get_legend_handles_labels()
ax1.legend(
    h1 + h2,
    l1 + l2,
    loc="best",
    frameon=False
)

ax1.grid(True, axis="y", alpha=0.25)

# =========================
# Panel (b)
# =========================
ax2 = fig.add_subplot(gs[1, 0])

domains = list(FILES.keys())
n_domains = len(domains)
centers = np.arange(1, 22)
width = 0.16
offsets = np.linspace(
    -0.27, 0.27, n_domains
)

cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]

legend_handles = []

for d_idx, domain in enumerate(domains):
    d = all_data.loc[
        all_data["Domain"] == domain,
        FEATURES
    ]

    series = [
        d[u].dropna().to_numpy(dtype=float)
        for u in FEATURES
    ]

    positions = centers + offsets[d_idx]

    bp = ax2.boxplot(
        series,
        positions=positions,
        widths=width,
        patch_artist=True,
        showfliers=False,
        whis=(5, 95),
        manage_ticks=False,
        medianprops={"linewidth": 1.1},
        boxprops={"linewidth": 0.9},
        whiskerprops={"linewidth": 0.8},
        capprops={"linewidth": 0.8},
    )

    color = cycle[d_idx % len(cycle)]

    for patch in bp["boxes"]:
        patch.set_facecolor(color)
        patch.set_alpha(0.45)

    for medline in bp["medians"]:
        medline.set_color("black")

    legend_handles.append(
        Line2D(
            [0], [0],
            marker="s",
            linestyle="None",
            markersize=9,
            markerfacecolor=color,
            markeredgecolor="none",
            alpha=0.55,
            label=domain
        )
    )

ax2.set_xlim(0.5, 21.5)
ax2.set_xticks(centers)
ax2.set_xticklabels(
    FEATURES,
    rotation=45,
    ha="right"
)
ax2.set_xlabel("Pulse feature dimension")
ax2.set_ylabel("Voltage [V]")
ax2.set_title(
    "(b) Cross-domain heterogeneity of actual U1–U21 voltage features",
    loc="left",
    fontweight="bold"
)
ax2.legend(
    handles=legend_handles,
    title="PulseBat domain",
    ncol=2,
    frameon=False,
    loc="upper left"
)
ax2.grid(True, axis="y", alpha=0.25)

fig.suptitle(
    "Pulse-feature semantics and cross-domain voltage heterogeneity in the study data",
    fontsize=14,
    fontweight="bold",
    y=0.995
)

# ------------------------------------------------------------
# 5. Save publication-quality outputs
# ------------------------------------------------------------
png = FIG_DIR / "Figure_PulseFeature_Heterogeneity_OwnData.png"
pdf = FIG_DIR / "Figure_PulseFeature_Heterogeneity_OwnData.pdf"

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
# 6. Save caption + run summary
# ------------------------------------------------------------
caption = f"""# Proposed Main-Figure Caption

**Pulse-feature semantics and cross-domain voltage heterogeneity in the study
data.** (a) Actual U1–U21 voltage features from a representative observed
{REP_DOMAIN} PulseBat sample. The dashed secondary-axis trace is a schematic
guide to the known PulseBat C-rate blocks and is not a reconstructed raw-current
measurement. U1 is the rested voltage reference, while the subsequent feature
points summarize turning-point responses associated with the 0.5C, 1C, and 1.5C
pulse blocks. (b) Distribution of the actual U1–U21 processed voltage features
across the four PulseBat source domains (LFP 35Ah, LMO 10Ah, NMC 2.1Ah, and
NMC 21Ah). The cross-domain shifts motivate the state-free normalization and
few-shot target adaptation evaluated in this study.
"""

(OUT_DIR / "03_proposed_caption.md").write_text(
    caption,
    encoding="utf-8"
)

summary = {
    "stage": "Day28b",
    "purpose": "Create reference-inspired two-panel figure using only project data.",
    "reference_image_used_as_data": False,
    "panel_a_source": f"Actual observed row from {REP_DOMAIN}",
    "panel_a_raw_trace_reconstructed": False,
    "panel_a_current_axis": "Schematic protocol C-rate guide only",
    "panel_b_source": "Actual U1-U21 distributions from all four PulseBat processed files",
    "domains": domains,
    "representative_source_row": int(rep["SourceRow"]),
    "png_300dpi": str(png),
    "vector_pdf": str(pdf),
    "scientific_results_changed": False,
}

(OUT_DIR / "04_run_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("\n=== DAY 28b COMPLETE ===")
print("Reference image copied/reused as research evidence: NO")
print("Panel (a): actual PulseBat representative U1-U21 row")
print("Panel (b): actual four-domain U1-U21 distributions")
print("Raw 100 Hz voltage trace reconstructed: NO")
print("Protocol C-rate shown only as schematic: YES")
print("\nRepresentative domain:", REP_DOMAIN)
print("Representative original row:", int(rep["SourceRow"]))
print("\nSaved:")
print(png)
print(pdf)
print(OUT_DIR / "03_proposed_caption.md")
print(OUT_DIR / "04_run_summary.json")
