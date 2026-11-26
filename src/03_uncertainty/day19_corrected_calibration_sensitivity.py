r"""
Day 19 — Corrected calibration-size sensitivity with Day16 protocol lock
========================================================================

Purpose
-------
Day18 correctly identified the finite-sample conformal rank limitation, but its
screening-safety comparison changed the source-training protocol relative to
Day16: Day18 trained on all source cells, while Day16 reserved 20% of source
cells before fitting the model.

Therefore Day18 safety changes cannot be attributed uniquely to target
calibration-set size.

Day19 fixes this by locking the Day16 protocol EXACTLY and varying ONLY target
calibration size.

Integrity gate
--------------
For total_labeled_cells = 20:
- source split must match Day16
- adaptation cells = 10
- calibration cells = 10
- target test cohort must match Day16
- model and qhat must therefore reproduce Day16 results

Only after this reproduction passes are the 20- and 30-calibration-cell
sensitivity results interpreted.

Frozen representation
----------------------
REL_RATIO_NO_STATE = (Ui-U1)/abs(U1), i=2..21

Fixed Day16 protocol
--------------------
- SEED = 42
- repeats = 10
- source reserve fraction = 20%
- target weight = 8
- adaptation cells = 10
- nominal conformal coverage = 90%
- ExtraTrees settings unchanged
- same RNG sequence: source shuffle first, target shuffle second

Calibration-size configurations
-------------------------------
A. 20 total labels = 10 adapt + 10 calibration
B. 30 total labels = 10 adapt + 20 calibration
C. 40 total labels = 10 adapt + 30 calibration

Screening thresholds
--------------------
A: lower >= 0.80
B: lower >= 0.70 and upper < 0.80
D: upper < 0.70
C: otherwise

False-safe
----------
true SOH < 0.70 but assigned A or B

Important
---------
This remains a sensitivity analysis, not deployment-policy tuning.

Output
------
D:\SecondLife_Research\Result\Day19_CorrectedCalibrationSensitivity
"""

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SEED = 42
REPEATS = 10
TARGET_WEIGHT = 8.0
SOURCE_CAL_FRACTION = 0.20
ALPHA = 0.10
ADAPT_CELLS = 10
TOTAL_LABELED_CONFIGS = [20, 30, 40]

DIRECT_REUSE_SOH = 0.80
RECYCLE_SOH = 0.70
EPS = 1e-12

ROOT = Path(r"D:\SecondLife_Research")
DATA_ROOT = ROOT / "Data" / "PulseBat"
DAY16_ROOT = ROOT / "Result" / "Day16_ScreeningDecision"
OUT = ROOT / "Result" / "Day19_CorrectedCalibrationSensitivity"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED = {
    "NMC_2.1Ah_W_5000.xlsx",
    "LMO_10Ah_W_5000.xlsx",
    "NMC_21Ah_W_5000.xlsx",
    "LFP_35Ah_W_5000.xlsx",
}


def numeric(s):
    return pd.to_numeric(s, errors="coerce")


def infer_group(f):
    n = f.name.upper()
    if "2.1AH" in n and "NMC" in n:
        return "2.1Ah NMC", "NMC"
    if "10AH" in n and "LMO" in n:
        return "10Ah LMO", "LMO"
    if "21AH" in n and "NMC" in n:
        return "21Ah NMC", "NMC"
    if "35AH" in n and "LFP" in n:
        return "35Ah LFP", "LFP"
    raise ValueError(f"Unknown group: {f.name}")


def load_data():
    frames = []
    files = sorted(
        f for f in DATA_ROOT.rglob("*.xlsx")
        if f.name in EXPECTED
    )

    if len(files) != 4:
        raise FileNotFoundError(
            f"Expected 4 PulseBat files; found {len(files)}"
        )

    for f in files:
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]

        df = pd.read_excel(
            f,
            sheet_name=sheet
        ).dropna(how="all")

        df.columns = [
            str(c).strip()
            for c in df.columns
        ]

        group, chem = infer_group(f)

        id_col = next(
            c for c in df.columns
            if str(c).strip().lower()
            in {"id", "batteryid", "battery_id", "cellid", "cell_id"}
        )

        soh_col = next(
            c for c in df.columns
            if str(c).strip().lower() == "soh"
        )

        df["_group"] = group
        df["_chemistry"] = chem
        df["_cell_id"] = (
            group
            + "::"
            + df[id_col].astype(str).str.strip()
        )

        df["_SOH"] = numeric(df[soh_col])

        if df["_SOH"].dropna().median() > 2:
            df["_SOH"] /= 100.0

        for k in range(1, 22):
            c = f"U{k}"
            if c not in df.columns:
                raise ValueError(
                    f"{f.name}: missing {c}"
                )
            df[c] = numeric(df[c])

        frames.append(df)

    data = pd.concat(
        frames,
        ignore_index=True,
        sort=False
    )

    u1 = data["U1"].astype(float)

    features = []

    for k in range(2, 22):
        c = f"U{k}"
        name = f"RATIO_U{k}"

        data[name] = (
            (data[c] - u1)
            / (u1.abs() + EPS)
        )

        features.append(name)

    data = data[
        data["_SOH"].notna()
    ].copy()

    return data, features


def fit_model(
    source_train,
    adapt,
    features,
    seed
):
    imp = SimpleImputer(
        strategy="median"
    )

    Xs = imp.fit_transform(
        source_train[features]
    )

    ys = source_train[
        "_SOH"
    ].to_numpy()

    Xa = imp.transform(
        adapt[features]
    )

    ya = adapt[
        "_SOH"
    ].to_numpy()

    X = np.vstack([
        Xs,
        Xa
    ])

    y = np.concatenate([
        ys,
        ya
    ])

    w = np.concatenate([
        np.ones(len(Xs)),
        np.full(
            len(Xa),
            TARGET_WEIGHT
        ),
    ])

    model = ExtraTreesRegressor(
        n_estimators=800,
        min_samples_leaf=2,
        max_features=0.8,
        random_state=seed,
        n_jobs=-1,
    )

    model.fit(
        X,
        y,
        sample_weight=w
    )

    return imp, model


def predict_cell(
    df,
    pred
):
    t = df[
        [
            "_cell_id",
            "_chemistry",
            "_group",
            "_SOH",
        ]
    ].copy()

    t["pred"] = pred

    return (
        t.groupby(
            [
                "_cell_id",
                "_chemistry",
                "_group",
            ],
            as_index=False
        )
        .agg(
            true_SOH=(
                "_SOH",
                "median"
            ),
            pred_SOH=(
                "pred",
                "mean"
            ),
            pulse_rows=(
                "pred",
                "size"
            ),
        )
    )


def conformal_rank(
    n_cal,
    alpha=ALPHA
):
    raw_rank = math.ceil(
        (n_cal + 1)
        * (1 - alpha)
    )

    used_rank = min(
        n_cal,
        raw_rank
    )

    return raw_rank, used_rank


def conformal_qhat(
    residuals,
    alpha=ALPHA
):
    r = np.sort(
        np.asarray(
            residuals,
            dtype=float
        )
    )

    r = r[
        np.isfinite(r)
    ]

    n = len(r)

    if n == 0:
        raise ValueError(
            "No calibration residuals."
        )

    _, used_rank = conformal_rank(
        n,
        alpha
    )

    return float(
        r[
            used_rank - 1
        ]
    )


def decision_from_interval(
    lower,
    upper
):
    if lower >= DIRECT_REUSE_SOH:
        return "A"

    if (
        lower >= RECYCLE_SOH
        and upper < DIRECT_REUSE_SOH
    ):
        return "B"

    if upper < RECYCLE_SOH:
        return "D"

    return "C"


data, features = load_data()

prediction_rows = []
repeat_rows = []

for target_chem in sorted(
    data["_chemistry"].unique()
):
    source_all = data[
        data["_chemistry"]
        != target_chem
    ].copy()

    target_all = data[
        data["_chemistry"]
        == target_chem
    ].copy()

    source_cells_all = np.array(
        sorted(
            source_all[
                "_cell_id"
            ].unique()
        )
    )

    target_cells_all = np.array(
        sorted(
            target_all[
                "_cell_id"
            ].unique()
        )
    )

    for rep in range(REPEATS):

        # IMPORTANT:
        # Match Day16 RNG order exactly:
        # 1) source shuffle
        # 2) target shuffle
        rng = np.random.default_rng(
            SEED + rep
        )

        source_cells = (
            source_cells_all.copy()
        )

        rng.shuffle(
            source_cells
        )

        n_source_cal = max(
            10,
            int(
                round(
                    len(source_cells)
                    * SOURCE_CAL_FRACTION
                )
            )
        )

        source_cal_ids = (
            source_cells[
                :n_source_cal
            ]
        )

        source_train_ids = (
            source_cells[
                n_source_cal:
            ]
        )

        source_train = source_all[
            source_all[
                "_cell_id"
            ].isin(
                source_train_ids
            )
        ].copy()

        target_cells = (
            target_cells_all.copy()
        )

        rng.shuffle(
            target_cells
        )

        # Fixed adaptation set = first 10 target cells.
        adapt_ids = (
            target_cells[
                :ADAPT_CELLS
            ]
        )

        adapt = target_all[
            target_all[
                "_cell_id"
            ].isin(
                adapt_ids
            )
        ].copy()

        # Fit model ONCE for this chemistry/repeat.
        # Thus calibration-size comparisons do not change the model.
        imp, model = fit_model(
            source_train,
            adapt,
            features,
            SEED + rep
        )

        for total_labeled in TOTAL_LABELED_CONFIGS:

            if total_labeled >= len(
                target_cells
            ):
                continue

            n_cal = (
                total_labeled
                - ADAPT_CELLS
            )

            cal_ids = target_cells[
                ADAPT_CELLS:
                total_labeled
            ]

            test_ids = target_cells[
                total_labeled:
            ]

            cal = target_all[
                target_all[
                    "_cell_id"
                ].isin(
                    cal_ids
                )
            ].copy()

            test = target_all[
                target_all[
                    "_cell_id"
                ].isin(
                    test_ids
                )
            ].copy()

            cal_pred = model.predict(
                imp.transform(
                    cal[features]
                )
            )

            cal_cell = predict_cell(
                cal,
                cal_pred
            )

            cal_res = np.abs(
                cal_cell[
                    "pred_SOH"
                ]
                - cal_cell[
                    "true_SOH"
                ]
            )

            qhat = conformal_qhat(
                cal_res,
                ALPHA
            )

            raw_rank, used_rank = (
                conformal_rank(
                    len(cal_cell),
                    ALPHA
                )
            )

            test_pred = model.predict(
                imp.transform(
                    test[features]
                )
            )

            cell = predict_cell(
                test,
                test_pred
            )

            cell["lower"] = (
                cell["pred_SOH"]
                - qhat
            )

            cell["upper"] = (
                cell["pred_SOH"]
                + qhat
            )

            cell["covered"] = (
                (
                    cell["true_SOH"]
                    >= cell["lower"]
                )
                &
                (
                    cell["true_SOH"]
                    <= cell["upper"]
                )
            )

            cell["decision"] = [
                decision_from_interval(
                    lo,
                    hi
                )
                for lo, hi in zip(
                    cell["lower"],
                    cell["upper"]
                )
            ]

            cell[
                "false_safe"
            ] = (
                (
                    cell["true_SOH"]
                    < RECYCLE_SOH
                )
                &
                (
                    cell["decision"]
                    .isin(
                        ["A", "B"]
                    )
                )
            )

            cell[
                "false_direct_reuse"
            ] = (
                (
                    cell["true_SOH"]
                    < DIRECT_REUSE_SOH
                )
                &
                (
                    cell["decision"]
                    == "A"
                )
            )

            cell[
                "target_chemistry"
            ] = target_chem

            cell[
                "repeat"
            ] = rep

            cell[
                "total_labeled_cells"
            ] = total_labeled

            cell[
                "adaptation_cells"
            ] = ADAPT_CELLS

            cell[
                "calibration_cells"
            ] = len(cal_cell)

            cell[
                "qhat"
            ] = qhat

            prediction_rows.append(
                cell
            )

            repeat_rows.append({
                "target_chemistry":
                    target_chem,

                "repeat":
                    rep,

                "source_train_cells":
                    len(
                        source_train_ids
                    ),

                "source_reserved_cells":
                    len(
                        source_cal_ids
                    ),

                "total_labeled_cells":
                    total_labeled,

                "adaptation_cells":
                    ADAPT_CELLS,

                "calibration_cells":
                    len(cal_cell),

                "test_cells":
                    len(cell),

                "raw_conformal_rank":
                    raw_rank,

                "used_conformal_rank":
                    used_rank,

                "uses_maximum_residual":
                    used_rank
                    == len(cal_cell),

                "qhat_pp":
                    qhat * 100,

                "MAE_pp":
                    mean_absolute_error(
                        cell["true_SOH"],
                        cell["pred_SOH"]
                    ) * 100,

                "RMSE_pp":
                    mean_squared_error(
                        cell["true_SOH"],
                        cell["pred_SOH"]
                    ) ** 0.5 * 100,

                "R2":
                    r2_score(
                        cell["true_SOH"],
                        cell["pred_SOH"]
                    )
                    if len(cell) > 1
                    else np.nan,

                "PICP":
                    cell[
                        "covered"
                    ].mean(),

                "MPIW_pp":
                    2
                    * qhat
                    * 100,

                "Class_A_rate":
                    (
                        cell[
                            "decision"
                        ]
                        == "A"
                    ).mean(),

                "Class_B_rate":
                    (
                        cell[
                            "decision"
                        ]
                        == "B"
                    ).mean(),

                "Class_C_rate":
                    (
                        cell[
                            "decision"
                        ]
                        == "C"
                    ).mean(),

                "Class_D_rate":
                    (
                        cell[
                            "decision"
                        ]
                        == "D"
                    ).mean(),

                "decisive_rate":
                    cell[
                        "decision"
                    ]
                    .isin(
                        ["A", "B", "D"]
                    )
                    .mean(),

                "reuse_assignment_rate":
                    cell[
                        "decision"
                    ]
                    .isin(
                        ["A", "B"]
                    )
                    .mean(),

                "false_safe_rate":
                    cell[
                        "false_safe"
                    ]
                    .mean(),

                "false_direct_reuse_rate":
                    cell[
                        "false_direct_reuse"
                    ]
                    .mean(),

                "false_safe_count":
                    int(
                        cell[
                            "false_safe"
                        ].sum()
                    ),

                "false_direct_reuse_count":
                    int(
                        cell[
                            "false_direct_reuse"
                        ].sum()
                    ),
            })


predictions = pd.concat(
    prediction_rows,
    ignore_index=True
)

repeat_metrics = pd.DataFrame(
    repeat_rows
)

predictions.to_csv(
    OUT
    / "01_cell_corrected_calibration_predictions.csv",
    index=False
)

repeat_metrics.to_csv(
    OUT
    / "02_corrected_calibration_repeat_metrics.csv",
    index=False
)


chem_agg = (
    repeat_metrics
    .groupby(
        [
            "target_chemistry",
            "total_labeled_cells",
            "adaptation_cells",
            "calibration_cells",
        ]
    )
    .agg(
        qhat_mean_pp=(
            "qhat_pp",
            "mean"
        ),

        qhat_std_pp=(
            "qhat_pp",
            "std"
        ),

        PICP_mean=(
            "PICP",
            "mean"
        ),

        PICP_std=(
            "PICP",
            "std"
        ),

        MPIW_mean_pp=(
            "MPIW_pp",
            "mean"
        ),

        decisive_rate_mean=(
            "decisive_rate",
            "mean"
        ),

        Class_C_rate_mean=(
            "Class_C_rate",
            "mean"
        ),

        reuse_assignment_rate_mean=(
            "reuse_assignment_rate",
            "mean"
        ),

        false_safe_rate_mean=(
            "false_safe_rate",
            "mean"
        ),

        false_direct_reuse_rate_mean=(
            "false_direct_reuse_rate",
            "mean"
        ),

        total_false_safe=(
            "false_safe_count",
            "sum"
        ),

        total_false_direct_reuse=(
            "false_direct_reuse_count",
            "sum"
        ),

        mean_test_cells=(
            "test_cells",
            "mean"
        ),

        repeats=(
            "repeat",
            "nunique"
        ),
    )
    .reset_index()
)

chem_agg.to_csv(
    OUT
    / "03_corrected_calibration_chemistry.csv",
    index=False
)


overall_by_repeat = (
    repeat_metrics
    .groupby(
        [
            "repeat",
            "total_labeled_cells",
            "adaptation_cells",
            "calibration_cells",
        ]
    )
    .agg(
        qhat_pp=(
            "qhat_pp",
            "mean"
        ),

        PICP=(
            "PICP",
            "mean"
        ),

        MPIW_pp=(
            "MPIW_pp",
            "mean"
        ),

        decisive_rate=(
            "decisive_rate",
            "mean"
        ),

        Class_C_rate=(
            "Class_C_rate",
            "mean"
        ),

        reuse_assignment_rate=(
            "reuse_assignment_rate",
            "mean"
        ),

        false_safe_rate=(
            "false_safe_rate",
            "mean"
        ),

        false_direct_reuse_rate=(
            "false_direct_reuse_rate",
            "mean"
        ),

        false_safe_count=(
            "false_safe_count",
            "sum"
        ),

        false_direct_reuse_count=(
            "false_direct_reuse_count",
            "sum"
        ),
    )
    .reset_index()
)


overall = (
    overall_by_repeat
    .groupby(
        [
            "total_labeled_cells",
            "adaptation_cells",
            "calibration_cells",
        ]
    )
    .agg(
        qhat_mean_pp=(
            "qhat_pp",
            "mean"
        ),

        qhat_std_pp=(
            "qhat_pp",
            "std"
        ),

        PICP_mean=(
            "PICP",
            "mean"
        ),

        PICP_std=(
            "PICP",
            "std"
        ),

        MPIW_mean_pp=(
            "MPIW_pp",
            "mean"
        ),

        decisive_rate_mean=(
            "decisive_rate",
            "mean"
        ),

        Class_C_rate_mean=(
            "Class_C_rate",
            "mean"
        ),

        reuse_assignment_rate_mean=(
            "reuse_assignment_rate",
            "mean"
        ),

        false_safe_rate_mean=(
            "false_safe_rate",
            "mean"
        ),

        false_direct_reuse_rate_mean=(
            "false_direct_reuse_rate",
            "mean"
        ),

        total_false_safe=(
            "false_safe_count",
            "sum"
        ),

        total_false_direct_reuse=(
            "false_direct_reuse_count",
            "sum"
        ),

        repeats=(
            "repeat",
            "nunique"
        ),
    )
    .reset_index()
)

overall.to_csv(
    OUT
    / "04_corrected_calibration_overall.csv",
    index=False
)


# ---------------------------------------------------------
# Day16 integrity reproduction gate
# ---------------------------------------------------------

integrity_rows = []

day19_k20 = repeat_metrics[
    repeat_metrics[
        "total_labeled_cells"
    ] == 20
].copy()

if (
    DAY16_ROOT
    / "02_screening_repeat_metrics.csv"
).exists():

    day16 = pd.read_csv(
        DAY16_ROOT
        / "02_screening_repeat_metrics.csv"
    )

    keys = [
        "target_chemistry",
        "repeat",
    ]

    compare_cols = [
        "MAE_pp",
        "PICP",
        "MPIW_pp",
        "false_safe_count",
        "false_direct_reuse_count",
    ]

    merged = day16[
        keys + compare_cols
    ].merge(
        day19_k20[
            keys + compare_cols
        ],
        on=keys,
        suffixes=(
            "_Day16",
            "_Day19"
        )
    )

    for c in compare_cols:
        merged[
            f"{c}_abs_diff"
        ] = np.abs(
            merged[
                f"{c}_Day16"
            ]
            - merged[
                f"{c}_Day19"
            ]
        )

    merged.to_csv(
        OUT
        / "05_day16_reproduction_comparison.csv",
        index=False
    )

    max_numeric_diff = max(
        merged[
            f"{c}_abs_diff"
        ].max()
        for c in [
            "MAE_pp",
            "PICP",
            "MPIW_pp",
        ]
    )

    exact_count_match = all(
        (
            merged[
                f"{c}_Day16"
            ]
            ==
            merged[
                f"{c}_Day19"
            ]
        ).all()
        for c in [
            "false_safe_count",
            "false_direct_reuse_count",
        ]
    )

    reproduction_pass = (
        max_numeric_diff
        < 1e-10
        and exact_count_match
    )

    integrity_rows.append({
        "day16_repeat_file_found":
            True,

        "matched_rows":
            len(merged),

        "max_numeric_abs_diff":
            max_numeric_diff,

        "exact_count_match":
            exact_count_match,

        "reproduction_pass":
            reproduction_pass,
    })

else:

    reproduction_pass = False

    integrity_rows.append({
        "day16_repeat_file_found":
            False,

        "matched_rows":
            0,

        "max_numeric_abs_diff":
            np.nan,

        "exact_count_match":
            False,

        "reproduction_pass":
            False,
    })


integrity = pd.DataFrame(
    integrity_rows
)

integrity.to_csv(
    OUT
    / "06_day16_integrity_gate.csv",
    index=False
)


# NMC repeat 3 forensic comparison.
nmc_rep3 = repeat_metrics[
    (
        repeat_metrics[
            "target_chemistry"
        ]
        == "NMC"
    )
    &
    (
        repeat_metrics[
            "repeat"
        ]
        == 3
    )
].copy()

nmc_rep3.to_csv(
    OUT
    / "07_nmc_repeat3_corrected_sensitivity.csv",
    index=False
)


false_safe_details = predictions[
    predictions[
        "false_safe"
    ]
    == True
].copy()

false_safe_details.to_csv(
    OUT
    / "08_false_safe_cell_details.csv",
    index=False
)


# ---------------------------------------------------------
# Figures
# ---------------------------------------------------------

plt.figure(
    figsize=(7.2, 5.0)
)

plt.errorbar(
    overall[
        "calibration_cells"
    ],
    overall[
        "qhat_mean_pp"
    ],
    yerr=overall[
        "qhat_std_pp"
    ],
    marker="o",
    capsize=4
)

plt.xlabel(
    "Target calibration cells"
)

plt.ylabel(
    "Mean conformal half-width qhat (pp)"
)

plt.title(
    "Corrected calibration-size effect on qhat"
)

plt.tight_layout()

plt.savefig(
    OUT
    / "Fig01_Corrected_Qhat_vs_CalibrationSize.png",
    dpi=300
)

plt.savefig(
    OUT
    / "Fig01_Corrected_Qhat_vs_CalibrationSize.pdf"
)

plt.close()


plt.figure(
    figsize=(7.2, 5.0)
)

plt.plot(
    overall[
        "calibration_cells"
    ],
    overall[
        "PICP_mean"
    ] * 100,
    marker="o"
)

plt.axhline(
    90,
    linestyle="--"
)

plt.xlabel(
    "Target calibration cells"
)

plt.ylabel(
    "Empirical coverage (%)"
)

plt.title(
    "Corrected coverage vs calibration size"
)

plt.tight_layout()

plt.savefig(
    OUT
    / "Fig02_Corrected_PICP_vs_CalibrationSize.png",
    dpi=300
)

plt.savefig(
    OUT
    / "Fig02_Corrected_PICP_vs_CalibrationSize.pdf"
)

plt.close()


plt.figure(
    figsize=(7.2, 5.0)
)

plt.plot(
    overall[
        "calibration_cells"
    ],
    overall[
        "false_safe_rate_mean"
    ] * 100,
    marker="o",
    label="False-safe"
)

plt.plot(
    overall[
        "calibration_cells"
    ],
    overall[
        "decisive_rate_mean"
    ] * 100,
    marker="o",
    label="Decisive A/B/D"
)

plt.xlabel(
    "Target calibration cells"
)

plt.ylabel(
    "Rate (%)"
)

plt.title(
    "Corrected safety–decisiveness sensitivity"
)

plt.legend()

plt.tight_layout()

plt.savefig(
    OUT
    / "Fig03_Corrected_Safety_Decisiveness.png",
    dpi=300
)

plt.savefig(
    OUT
    / "Fig03_Corrected_Safety_Decisiveness.pdf"
)

plt.close()


run_summary = {
    "day":
        "Day19",

    "representation":
        "REL_RATIO_NO_STATE",

    "nominal_coverage":
        0.90,

    "source_protocol":
        "Day16 exact source split locked: 20% source cells reserved before model fitting",

    "rng_protocol":
        "Day16 exact RNG order locked: source shuffle first, target shuffle second",

    "adaptation_cells_fixed":
        ADAPT_CELLS,

    "calibration_sizes":
        [
            x - ADAPT_CELLS
            for x in TOTAL_LABELED_CONFIGS
        ],

    "integrity_gate":
        "20-total-label configuration must reproduce Day16 repeat-level metrics exactly",

    "purpose":
        (
            "Isolate target calibration-size effects while keeping the "
            "Day16 source-training protocol, model, adaptation set, RNG "
            "sequence, feature representation, and screening thresholds fixed."
        ),

    "scope_note":
        (
            "This is a sensitivity analysis, not deployment-policy tuning. "
            "Interpret 20/30/40-label results only if the Day16 reproduction "
            "integrity gate passes."
        ),

    "output_dir":
        str(OUT),
}

(
    OUT
    / "09_run_summary.json"
).write_text(
    json.dumps(
        run_summary,
        indent=2
    ),
    encoding="utf-8"
)


print(
    "\n=== DAY 19 COMPLETE ==="
)

print(
    "\nDay16 reproduction integrity gate:"
)

print(
    integrity.to_string(
        index=False
    )
)

print(
    "\nCorrected overall calibration-size sensitivity:"
)

print(
    overall.to_string(
        index=False
    )
)

print(
    "\nCorrected NMC repeat-3 sensitivity:"
)

print(
    nmc_rep3.to_string(
        index=False
    )
)

print(
    f"\nResults saved to:\n{OUT}"
)

print(
    "\nSend me:"
)

print(
    "04_corrected_calibration_overall.csv"
)

print(
    "05_day16_reproduction_comparison.csv"
)

print(
    "06_day16_integrity_gate.csv"
)

print(
    "07_nmc_repeat3_corrected_sensitivity.csv"
)

print(
    "08_false_safe_cell_details.csv"
)

print(
    "09_run_summary.json"
)
