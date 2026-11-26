# Filename: day28e_final_generalization_trustworthiness_figure.py
# Purpose:
# Create a 3-panel publication figure using ONLY frozen, verified project outputs.
#
# Scientific analogue of the supplied literature "generated-vs-tested" figure:
#   (a) True vs predicted SOH from the final screening-stage cell predictions.
#   (b) Absolute prediction-error distributions by chemistry.
#   (c) Protocol-locked calibration-size trade-off:
#       empirical coverage, decisive-rate, and observed false-safe rate.
#
# NO generated data.
# NO unseen-SOC synthesis claim.
# NO KLD/KDE generated-vs-tested comparison.
# NO model retraining.
# NO fabricated values.
#
# Inputs:
# D:\SecondLife_Research\Result\Day16_ScreeningDecision\01_cell_screening_predictions.csv
# D:\SecondLife_Research\Result\Day19_CorrectedCalibrationSensitivity\01_cell_corrected_calibration_predictions.csv
#
# Outputs:
# PNG 300 DPI + true vector PDF
# CSV summaries + caption + run summary

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(r"D:\SecondLife_Research")
DAY16 = ROOT / "Result" / "Day16_ScreeningDecision" / "01_cell_screening_predictions.csv"
DAY19 = ROOT / "Result" / "Day19_CorrectedCalibrationSensitivity" / "01_cell_corrected_calibration_predictions.csv"

OUT = ROOT / "Result" / "Day28e_FinalGeneralizationTrustworthiness"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

for p in [DAY16, DAY19]:
    if not p.exists():
        raise FileNotFoundError(p)

d16 = pd.read_csv(DAY16)
d19 = pd.read_csv(DAY19)

required16 = [
    "_chemistry", "true_SOH", "pred_SOH",
    "decision", "false_safe", "repeat"
]
missing16 = [c for c in required16 if c not in d16.columns]
if missing16:
    raise RuntimeError(f"Day16 missing columns: {missing16}")

required19 = [
    "_chemistry", "true_SOH", "pred_SOH",
    "lower", "upper", "covered", "decision", "false_safe",
    "calibration_cells", "adaptation_cells", "repeat"
]
missing19 = [c for c in required19 if c not in d19.columns]
if missing19:
    raise RuntimeError(f"Day19 missing columns: {missing19}")

# ------------------------------------------------------------
# Clean data without inventing anything
# ------------------------------------------------------------

for df in [d16, d19]:
    for c in ["true_SOH", "pred_SOH"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

d16 = d16[
    np.isfinite(d16["true_SOH"])
    & np.isfinite(d16["pred_SOH"])
].copy()

d19 = d19[
    np.isfinite(d19["true_SOH"])
    & np.isfinite(d19["pred_SOH"])
].copy()

if d16.empty or d19.empty:
    raise RuntimeError("No valid frozen prediction rows available.")

# Detect scale, preserving source values.
def scale_label(series):
    med = float(np.nanmedian(series))
    return "fraction" if med <= 1.5 else "percent"

scale16 = scale_label(d16["true_SOH"])
scale19 = scale_label(d19["true_SOH"])

if scale16 != scale19:
    raise RuntimeError(
        f"SOH scale mismatch: Day16={scale16}, Day19={scale19}"
    )

SOH_SCALE = scale16

if SOH_SCALE == "fraction":
    # Convert only for display in percent units.
    for df in [d16, d19]:
        df["true_plot"] = 100.0 * df["true_SOH"]
        df["pred_plot"] = 100.0 * df["pred_SOH"]
else:
    for df in [d16, d19]:
        df["true_plot"] = df["true_SOH"]
        df["pred_plot"] = df["pred_SOH"]

d16["abs_error_pp"] = np.abs(
    d16["pred_plot"] - d16["true_plot"]
)

# ------------------------------------------------------------
# Reduce repeated-prediction overplotting WITHOUT changing evidence:
# aggregate to cell x chemistry x repeat medians where cell id exists.
# ------------------------------------------------------------

id_col = "_cell_id" if "_cell_id" in d16.columns else None

if id_col:
    scatter_df = (
        d16.groupby(
            [id_col, "_chemistry", "repeat"],
            as_index=False
        )[["true_plot", "pred_plot", "abs_error_pp"]]
        .median()
    )
else:
    scatter_df = d16.copy()

# ------------------------------------------------------------
# Panel (c) summary from Day19
# ------------------------------------------------------------

def bool_mean(series):
    if series.dtype == bool:
        return float(series.mean())

    mapping = {
        "true": True, "false": False,
        "1": True, "0": False,
        "yes": True, "no": False
    }

    vals = series.astype(str).str.strip().str.lower().map(mapping)

    if vals.notna().any():
        return float(vals.mean())

    return float(pd.to_numeric(series, errors="coerce").mean())

rows = []

for cal, g in d19.groupby("calibration_cells"):
    decisions = g["decision"].astype(str).str.strip().str.upper()
    decisive = ~decisions.eq("C")

    rows.append({
        "calibration_cells": int(cal),
        "n_rows": int(len(g)),
        "coverage": bool_mean(g["covered"]),
        "decisive_rate": float(decisive.mean()),
        "false_safe_rate": bool_mean(g["false_safe"]),
        "mean_abs_error_pp": float(
            np.mean(np.abs(g["pred_plot"] - g["true_plot"]))
        ),
    })

trade = pd.DataFrame(rows).sort_values("calibration_cells")
trade.to_csv(
    OUT / "01_calibration_tradeoff_summary.csv",
    index=False
)

# ------------------------------------------------------------
# Chemistry error summary
# ------------------------------------------------------------

chem_summary = (
    scatter_df.groupby("_chemistry")["abs_error_pp"]
    .agg(["count", "mean", "median", "std"])
    .reset_index()
    .rename(columns={
        "count": "n",
        "mean": "mean_abs_error_pp",
        "median": "median_abs_error_pp",
        "std": "std_abs_error_pp"
    })
)

chem_summary.to_csv(
    OUT / "02_chemistry_error_summary.csv",
    index=False
)

# ------------------------------------------------------------
# Plot
# ------------------------------------------------------------

fig = plt.figure(figsize=(15, 5.3))
gs = fig.add_gridspec(
    1, 3,
    width_ratios=[1.05, 1.0, 1.15],
    wspace=0.28
)

chemistries = sorted(
    scatter_df["_chemistry"].dropna().astype(str).unique()
)

# (a) True vs predicted
ax1 = fig.add_subplot(gs[0, 0])

for chem in chemistries:
    g = scatter_df[
        scatter_df["_chemistry"].astype(str) == chem
    ]

    ax1.scatter(
        g["true_plot"],
        g["pred_plot"],
        s=17,
        alpha=0.45,
        label=chem
    )

lims = [
    min(scatter_df["true_plot"].min(), scatter_df["pred_plot"].min()),
    max(scatter_df["true_plot"].max(), scatter_df["pred_plot"].max())
]
pad = 0.03 * (lims[1] - lims[0]) if lims[1] > lims[0] else 1.0
lims = [lims[0] - pad, lims[1] + pad]

ax1.plot(
    lims, lims,
    linestyle="--",
    linewidth=1.2,
    label="Ideal prediction"
)

ax1.set_xlim(lims)
ax1.set_ylim(lims)
ax1.set_xlabel("True SOH [%]")
ax1.set_ylabel("Predicted SOH [%]")
ax1.set_title(
    "(a) Frozen cell-level SOH predictions",
    loc="left",
    fontweight="bold"
)
ax1.grid(True, alpha=0.22)
ax1.legend(
    frameon=False,
    fontsize=8,
    loc="best"
)

# (b) Absolute-error distributions
ax2 = fig.add_subplot(gs[0, 1])

groups = [
    scatter_df.loc[
        scatter_df["_chemistry"].astype(str) == chem,
        "abs_error_pp"
    ].dropna().to_numpy()
    for chem in chemistries
]

bp = ax2.boxplot(
    groups,
    labels=chemistries,
    patch_artist=True,
    showfliers=False,
    whis=(5, 95)
)

cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]

for i, patch in enumerate(bp["boxes"]):
    patch.set_facecolor(cycle[i % len(cycle)])
    patch.set_alpha(0.45)

for med in bp["medians"]:
    med.set_color("black")

ax2.set_ylabel("Absolute SOH error [pp]")
ax2.set_title(
    "(b) Error distribution by chemistry",
    loc="left",
    fontweight="bold"
)
ax2.tick_params(
    axis="x",
    rotation=35
)
ax2.grid(True, axis="y", alpha=0.22)

# (c) Calibration-size trade-off
ax3 = fig.add_subplot(gs[0, 2])

x = trade["calibration_cells"].to_numpy(dtype=float)

ax3.plot(
    x,
    100 * trade["coverage"],
    marker="o",
    linewidth=1.8,
    label="Empirical coverage"
)

ax3.plot(
    x,
    100 * trade["decisive_rate"],
    marker="s",
    linewidth=1.8,
    label="Decisive A/B/D rate"
)

ax3.plot(
    x,
    100 * trade["false_safe_rate"],
    marker="^",
    linewidth=1.8,
    label="Observed false-safe rate"
)

ax3.axhline(
    90,
    linestyle="--",
    linewidth=1.0,
    label="Nominal 90% coverage"
)

ax3.set_xlabel("Target calibration cells")
ax3.set_ylabel("Rate [%]")
ax3.set_title(
    "(c) Calibration-size trustworthiness trade-off",
    loc="left",
    fontweight="bold"
)
ax3.set_xticks(x)
ax3.grid(True, alpha=0.22)
ax3.legend(
    frameon=False,
    fontsize=8,
    loc="best"
)

fig.suptitle(
    "Generalization and trustworthiness evidence from frozen second-life battery predictions",
    fontsize=14,
    fontweight="bold",
    y=1.02
)

png = FIG / "Figure_Generalization_Trustworthiness_OwnData.png"
pdf = FIG / "Figure_Generalization_Trustworthiness_OwnData.pdf"

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
# Save exact scatter evidence used
# ------------------------------------------------------------

scatter_df.to_csv(
    OUT / "03_scatter_evidence_used.csv",
    index=False
)

caption = """# Proposed Figure Caption

**Generalization and trustworthiness evidence from frozen second-life battery
predictions.** (a) True versus predicted SOH for cell-level predictions from
the frozen screening-stage evaluation, separated by battery chemistry; the
dashed line denotes ideal agreement. (b) Corresponding absolute SOH-error
distributions by chemistry, shown using the same observed prediction records.
(c) Protocol-locked calibration-size sensitivity computed from the corrected
frozen calibration analysis, showing empirical coverage, decisive A/B/D
assignment rate, and observed false-safe rate as the number of target
calibration cells changes. The figure contains no generated or synthetic
battery data and does not make an unseen-SOC generative-generalization claim.
Zero observed false-safe events in selected configurations are not interpreted
as zero deployment risk.
"""

(OUT / "04_proposed_caption.md").write_text(
    caption,
    encoding="utf-8"
)

summary = {
    "stage": "Day28e",
    "purpose": "Create a non-fabricated generalization/trustworthiness figure from frozen prediction evidence.",
    "panel_a_source": str(DAY16),
    "panel_b_source": str(DAY16),
    "panel_c_source": str(DAY19),
    "generated_data_used": False,
    "kld_analysis_used": False,
    "model_retraining": False,
    "soh_display_scale": "percent",
    "chemistries": chemistries,
    "n_scatter_records": int(len(scatter_df)),
    "calibration_sizes": trade["calibration_cells"].astype(int).tolist(),
    "png_300dpi": str(png),
    "vector_pdf": str(pdf),
    "scientific_results_changed": False,
}

(OUT / "05_run_summary.json").write_text(
    json.dumps(
        summary,
        indent=2
    ),
    encoding="utf-8"
)

print("\n=== DAY 28e COMPLETE ===")
print("Generated/synthetic data used: NO")
print("KLD generated-vs-tested analysis: NO")
print("Model retraining: NO")
print("Panel (a): frozen true vs predicted SOH")
print("Panel (b): frozen chemistry-wise error distributions")
print("Panel (c): corrected calibration-size trustworthiness trade-off")
print("SOH display scale: percent")
print("Scatter records used:", len(scatter_df))
print("Calibration sizes:", trade["calibration_cells"].astype(int).tolist())

print("\nSaved:")
print(png)
print(pdf)
print(OUT / "01_calibration_tradeoff_summary.csv")
print(OUT / "02_chemistry_error_summary.csv")
print(OUT / "03_scatter_evidence_used.csv")
print(OUT / "04_proposed_caption.md")
print(OUT / "05_run_summary.json")
