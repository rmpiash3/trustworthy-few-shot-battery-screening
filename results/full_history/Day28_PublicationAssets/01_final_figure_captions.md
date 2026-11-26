# Final Main-Figure Captions

## Figure 1
**Trustworthy few-shot pulse-diagnostic framework for heterogeneous second-life
lithium-ion batteries.** Short-pulse turning-point voltages U1–U21 are converted
to the frozen state-free relative pulse representation. A small labeled
target-domain set supports few-shot model adaptation and target-aware conformal
calibration. An applicability-domain/OOD layer is evaluated separately from SOH
regression. The final interval-aware A/B/C/D screening layer assigns decisive
reuse/recycle classes only when uncertainty is sufficiently bounded; Class C
denotes abstention or additional diagnostics.

## Figure 2
**Few-shot adaptation under internal chemistry shift and overlap-excluded
cross-dataset transfer.** Mean SOH MAE is shown versus labeled target-cell
budget K using the frozen REL_RATIO_NO_STATE representation. The figure
summarizes both internal chemistry-shift evaluation and overlap-excluded
cross-dataset transfer, illustrating the reduction in target-domain error as
limited labeled target information is introduced.

## Figure 3
**Target-aware split-conformal coverage versus labeled target-cell budget.**
Empirical prediction-interval coverage is shown relative to the nominal 90%
target. The result demonstrates that target-aware calibration approaches
nominal empirical coverage as target-domain calibration evidence increases.
Coverage is reported for the tested calibration protocol and is not a universal
distribution-shift guarantee.

## Figure 4
**Safety–decisiveness sensitivity to target calibration-set size.** Observed
false-safe rate and decisive A/B/D assignment rate are shown for the
protocol-locked calibration-size sensitivity analysis. The results illustrate a
non-monotonic safety–coverage–decisiveness trade-off. Zero observed false-safe
events in selected calibration configurations must not be interpreted as zero
deployment risk.
