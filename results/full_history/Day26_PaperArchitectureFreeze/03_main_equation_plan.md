# Main Equation Plan — FROZEN

Use equations only where they define the method.
Do not add equations merely for appearance.

## Equation 1 — Capacity-based SOH definition

\[
SOH = \frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}}
\]

If reported as percent:

\[
SOH(\%) =
100\frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}}
\]

Purpose:
Define the prediction target.


## Equation 2 — Frozen state-free relative pulse representation

\[
r_i =
\frac{U_i-U_1}{|U_1|},
\qquad i=2,\ldots,21
\]

The model input vector is:

\[
\mathbf{x}
=
[r_2,r_3,\ldots,r_{21}]^{\mathsf T}
\]

Purpose:
This is the most important method equation in the paper.


## Equation 3 — Weighted few-shot adaptation objective

For model \(f_\theta\):

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

where:
- \(\mathcal{S}\) = source training cells
- \(\mathcal{T}_K\) = K labeled target adaptation cells
- \(\lambda_T\) = target weighting factor

For the frozen implementation:
\[
\lambda_T = 8
\]

Purpose:
Mathematically explain weighted target adaptation.


## Equation 4 — Finite-sample conformal residual quantile

Calibration residual:

\[
s_i = |y_i-\hat y_i|
\]

For calibration size \(n_{\mathrm{cal}}\) and miscoverage \(\alpha\):

\[
k =
\min
\left[
n_{\mathrm{cal}},
\left\lceil
(n_{\mathrm{cal}}+1)(1-\alpha)
\right\rceil
\right]
\]

and

\[
\hat q_{1-\alpha}
=
s_{(k)}
\]

where \(s_{(k)}\) is the k-th ordered calibration residual.

Purpose:
This equation is essential because Day17 showed the finite-sample rank-resolution
effect when \(n_{\mathrm{cal}}=10\).


## Equation 5 — Conformal prediction interval

\[
\mathcal{C}_{1-\alpha}(\mathbf{x})
=
\left[
\hat y(\mathbf{x})-\hat q_{1-\alpha},
\;
\hat y(\mathbf{x})+\hat q_{1-\alpha}
\right]
\]

Purpose:
Defines the uncertainty interval used by screening.


## Equation 6 — Conservative screening / abstention rule

Let the interval be:

\[
[L,U] = \mathcal{C}_{1-\alpha}(\mathbf{x})
\]

Using the study's configurable SOH thresholds:

\[
\tau_A = 0.80,
\qquad
\tau_D = 0.70
\]

A compact decision rule is:

\[
g(L,U)=
\begin{cases}
A, & L\ge\tau_A,\\
B, & \tau_D\le L \;\text{and}\; U<\tau_A,\\
D, & U<\tau_D,\\
C, & \text{otherwise}.
\end{cases}
\]

Class C means additional diagnostics / abstention.

Important:
These thresholds are engineering assumptions for sensitivity analysis, not
universal regulatory thresholds.


# Equations NOT recommended in the main paper

## 1RC/2RC electrical equations
Do not present them as part of the validated main framework because the current
study did not obtain defensible identified \(R_0,R_1,C_1,R_2,C_2\) parameters.

If discussed, keep them in background / Supplementary Material and explicitly
state that they motivated surrogate physics auditing rather than a validated
Digital Twin.

## OOD formulas
Mahalanobis/KNN definitions are standard and do not need to occupy main-text
equation space unless the target journal asks for a highly formal Methods section.
They can be described in prose or Supplementary Material.
