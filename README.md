# Trustworthy Few-Shot Pulse Diagnostics for Heterogeneous Second-Life Batteries

Reproducibility repository for:

**Trustworthy Few-Shot Pulse Diagnostics with Calibrated Uncertainty and OOD-Aware Screening for Heterogeneous Second-Life Lithium-Ion Batteries**

## Core method

State-free pulse representation:

`r_i = (U_i - U_1) / |U_1|`, i=2,...,21

combined with:
- few-shot target adaptation
- target-aware split-conformal uncertainty
- OOD applicability-domain checking
- A/B/C/D screening with abstention

## Frozen headline evidence

Internal chemistry shift:
8.268 pp at K=0 -> 3.006 pp at K=20
(63.65% MAE reduction; p=0.000977)

Overlap-excluded cross-dataset:
8.720 pp at K=0 -> 3.468 pp at K=20
(60.24% reduction; p=0.000977)

Primary trustworthy screening:
10 adaptation + 10 calibration = 20 total target labels
PICP=90.93%, MPIW=19.90 pp

## Structure

- `src/`
- `data/`
- `results/`
- `figures/`
- `tables/`
- `supplementary/`
- `docs/`
- `environment/`
- `manuscript_support/`
- `audit/`

See `REPRODUCE.md`.

## Data
Third-party raw datasets are not redistributed by default.
See `data/README_DATA_ACCESS.md`.

## Repository
https://github.com/rmpiash/trustworthy-few-shot-battery-screening

## Zenodo DOI
TO BE ADDED AFTER v1.0.0 ARCHIVE
