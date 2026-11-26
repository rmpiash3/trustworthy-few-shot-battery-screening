# Publication Tables

## Table 1. Core predictive and uncertainty results

| Evidence block | Condition | MAE_pp | Primary result |
| --- | --- | --- | --- |
| Internal few-shot | K=0 | 8.26829 | Zero-shot chemistry transfer |
| Internal few-shot | K=20 | 3.00565 | Few-shot chemistry transfer |
| Internal statistics | K0 vs K20 |  | 63.65% reduction; p=0.000977 |
| Conformal UQ | K=20 | 3.63382 | PICP=90.93%; MPIW=19.90 pp |
| External cross-dataset | K=0 | 8.7201 | Overlap-excluded zero-shot transfer |
| External cross-dataset | K=20 | 3.46776 | Overlap-excluded few-shot transfer |
| External statistics | K0 vs K20 |  | 60.24% reduction; p=0.000977 |

## Table 2. Protocol-locked screening sensitivity

| total_labeled_cells | adaptation_cells | calibration_cells | PICP_mean | MPIW_mean_pp | decisive_rate_mean | Class_C_rate_mean | false_safe_rate_mean | false_direct_reuse_rate_mean | total_false_safe | total_false_direct_reuse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 10 | 10 | 0.909273 | 19.9028 | 0.260303 | 0.739697 | 0.0023569 | 0.00942761 | 7 | 28 |
| 30 | 10 | 20 | 0.912734 | 19.3498 | 0.223313 | 0.776687 | 0 | 0.000749064 | 0 | 2 |
| 40 | 10 | 30 | 0.890166 | 17.0735 | 0.291628 | 0.708372 | 0 | 0.00126582 | 0 | 3 |
