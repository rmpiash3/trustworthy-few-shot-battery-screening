# Main Table Plan — FROZEN

## Table 1 — Dataset and validation design

Recommended columns:
- Dataset / cohort
- Chemistry
- Rated capacity
- Number of cells / groups
- Available signal representation
- Role in study
- Leakage / overlap handling

Rows:
- PulseBat NMC 2.1 Ah
- PulseBat LMO 10 Ah
- PulseBat NMC 21 Ah
- PulseBat LFP 35 Ah
- LFP23
- Bipolar709 overlap-excluded cohort

Purpose:
Make dataset heterogeneity and validation scope immediately clear.


## Table 2 — Core predictive and uncertainty performance

Use the frozen Day25 publication-table values:
- Internal K=0
- Internal K=20
- Internal K0→K20 reduction + p value
- K20 conformal PICP / MPIW
- External K=0
- External K=20
- External K0→K20 reduction + p value

Purpose:
Compactly report the headline numerical evidence.


## Table 3 — Screening sensitivity

Recommended if the journal allows three main tables.

Rows:
- 10 calibration cells
- 20 calibration cells
- 30 calibration cells

Columns:
- PICP
- MPIW
- decisive rate
- Class-C rate
- false-safe rate
- false-direct-reuse rate
- event counts

If the journal strongly limits tables:
Move Table 3 to Supplementary Material and retain Figure 4 in the main text.
