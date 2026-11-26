# Final Main Equation Plan — APPROVED

Use only equations that define the implemented method.

## Equation 1 — SOH target

Use fractional SOH internally:

\[
y \equiv SOH =
\frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}}
\]

and report percentage SOH, when needed, as:

\[
SOH(\%) = 100y
\]

This avoids mixing a fraction-valued target with percentage-point error metrics.


## Equation 2 — State-free relative pulse representation

\[
r_i =
\frac{U_i-U_1}{|U_1|},
\qquad i=2,\ldots,21
\]

with input vector

\[
\mathbf{x}
=
[r_2,r_3,\ldots,r_{21}]^{\mathsf T}
\]


## Equation 3 — Weighted few-shot target adaptation

\[
\theta^\ast
=
\arg\min_{\theta}
\left[
\sum_{j\in\mathcal{S}}
\ell(f_\theta(\mathbf{x}_j),y_j)
+
\lambda_T
\sum_{k\in\mathcal{T}_K}
\ell(f_\theta(\mathbf{x}_k),y_k)
\right]
\]

where the frozen implementation uses

\[
\lambda_T = 8
\]

This notation represents the implemented sample weighting:
source weight = 1, target-adaptation weight = 8.


## Equation 4 — Finite-sample conformal calibration

Calibration residual:

\[
s_i = |y_i-\hat y_i|
\]

For \(n_{\mathrm{cal}}\) calibration samples and miscoverage \(\alpha\),

\[
k =
\min\left\{
n_{\mathrm{cal}},
\left\lceil
(n_{\mathrm{cal}}+1)(1-\alpha)
\right\rceil
\right\}
\]

and

\[
\hat q_{1-\alpha}=s_{(k)}
\]

where \(s_{(k)}\) denotes the k-th ordered residual.


## Equation 5 — Conformal prediction interval

\[
[L,U]
=
\left[
\hat y(\mathbf{x})-\hat q_{1-\alpha},
\;
\hat y(\mathbf{x})+\hat q_{1-\alpha}
\right]
\]


## Equation 6 — Conservative screening / abstention rule

Using

\[
\tau_A=0.80,
\qquad
\tau_D=0.70,
\]

the interval-based decision rule is

\[
g(L,U)=
\begin{cases}
A, & L\ge\tau_A,\\
B, & L\ge\tau_D \;\text{and}\; U<\tau_A,\\
D, & U<\tau_D,\\
C, & \text{otherwise}.
\end{cases}
\]

Interpretation:

- A: interval entirely in the direct-reuse region;
- B: interval entirely in the restricted-reuse region;
- D: interval entirely below the recycle threshold;
- C: threshold-crossing uncertainty, OOD condition, or otherwise insufficient
  evidence for a decisive reuse/recycle assignment.

Important:
The screening thresholds are study-specific engineering assumptions for
sensitivity analysis, not universal regulatory standards.


# Excluded from the validated main framework

Do not use 1RC/2RC state equations as validated study equations.
The current evidence does not support identified electrical parameters
\(R_0,R_1,C_1,R_2,C_2\).

Mahalanobis and KNN formulas can remain in Supplementary Methods if desired.
