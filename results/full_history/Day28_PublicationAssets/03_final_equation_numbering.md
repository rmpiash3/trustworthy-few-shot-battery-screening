# Final Equation Numbering and Placement

## Eq. (1) — SOH target
Place in Methods, immediately after defining ground-truth capacity.

\[
y \equiv SOH = \frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}},
\qquad
SOH(\%)=100y
\]

## Eq. (2) — State-free pulse representation
Place in the primary representation subsection.

\[
r_i=\frac{U_i-U_1}{|U_1|},
\qquad i=2,\ldots,21
\]

with

\[
\mathbf{x}=[r_2,r_3,\ldots,r_{21}]^{\mathsf T}
\]

## Eq. (3) — Weighted few-shot adaptation
Place in the few-shot adaptation subsection.

\[
\theta^\ast=
\arg\min_\theta
\left[
\sum_{j\in\mathcal{S}}\ell(f_\theta(\mathbf{x}_j),y_j)
+
\lambda_T
\sum_{k\in\mathcal{T}_K}\ell(f_\theta(\mathbf{x}_k),y_k)
\right]
\]

with \(\lambda_T=8\).

## Eq. (4) — Finite-sample conformal quantile
Place in the conformal-calibration subsection.

\[
s_i=|y_i-\hat y_i|
\]

\[
k=
\min\left\{
n_{\mathrm{cal}},
\left\lceil(n_{\mathrm{cal}}+1)(1-\alpha)\right\rceil
\right\},
\qquad
\hat q_{1-\alpha}=s_{(k)}
\]

## Eq. (5) — Conformal interval
Place immediately after Eq. (4).

\[
[L,U]=
[\hat y(\mathbf{x})-\hat q_{1-\alpha},
\hat y(\mathbf{x})+\hat q_{1-\alpha}]
\]

## Eq. (6) — Screening / abstention rule
Place in the screening subsection.

\[
g(L,U)=
\begin{cases}
A, & L\ge0.80,\\
B, & L\ge0.70 \;\text{and}\; U<0.80,\\
D, & U<0.70,\\
C, & \text{otherwise}.
\end{cases}
\]

Class C denotes abstention/additional diagnostics and also applies when the OOD
gate rejects the target as outside the tested applicability domain.

Important:
The 0.80 and 0.70 thresholds are study-specific engineering assumptions for
sensitivity analysis, not universal regulatory standards.
