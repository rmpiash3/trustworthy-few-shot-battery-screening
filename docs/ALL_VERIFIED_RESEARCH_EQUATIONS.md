# COMPLETE VERIFIED EQUATION INVENTORY

## Primary target
\[
y \equiv SOH=\frac{Q_{\mathrm{actual}}}{Q_{\mathrm{rated}}}
\]

\[
SOH(\%)=100y
\]

## State-free relative pulse representation
\[
r_i=\frac{U_i-U_1}{|U_1|},\qquad i=2,\ldots,21
\]

\[
\mathbf{x}=[r_2,r_3,\ldots,r_{21}]^{\mathsf T}
\]

## Weighted few-shot target adaptation
\[
\theta^\ast=
\arg\min_\theta
\left[
\sum_{j\in\mathcal S}\ell(f_\theta(\mathbf x_j),y_j)
+\lambda_T
\sum_{k\in\mathcal T_K}\ell(f_\theta(\mathbf x_k),y_k)
\right]
\]

\[
\lambda_T=8
\]

## Conformal residual
\[
s_i=|y_i-\hat y_i|
\]

## Finite-sample conformal rank
\[
k=
\min\left\{
n_{\mathrm{cal}},
\left\lceil(n_{\mathrm{cal}}+1)(1-\alpha)\right\rceil
\right\}
\]

\[
\hat q_{1-\alpha}=s_{(k)}
\]

## Conformal interval
\[
[L,U]=
[\hat y(\mathbf x)-\hat q_{1-\alpha},
\hat y(\mathbf x)+\hat q_{1-\alpha}]
\]

## Screening rule
\[
g(L,U)=
\begin{cases}
A,&L\ge0.80,\\
B,&L\ge0.70\ \mathrm{and}\ U<0.80,\\
D,&U<0.70,\\
C,&\mathrm{otherwise}.
\end{cases}
\]

## Mean absolute error
\[
MAE=\frac1N\sum_{i=1}^N|y_i-\hat y_i|
\]

## Root mean squared error
\[
RMSE=\sqrt{\frac1N\sum_{i=1}^N(y_i-\hat y_i)^2}
\]

## Coefficient of determination
\[
R^2=1-\frac{\sum_i(y_i-\hat y_i)^2}{\sum_i(y_i-\bar y)^2}
\]

## Relative MAE reduction
\[
\mathrm{Reduction}(\%)=
100\frac{MAE_{K=0}-MAE_{K}}{MAE_{K=0}}
\]

## Prediction interval coverage probability
\[
PICP=\frac1N\sum_{i=1}^N\mathbf 1(y_i\in[L_i,U_i])
\]

## Mean prediction interval width
\[
MPIW=\frac1N\sum_{i=1}^N(U_i-L_i)
\]

## False-safe rate
\[
FSR=
\frac{N(\mathrm{true\ SOH}<\tau_D\ \mathrm{and\ decision}\in\{A,B\})}
{N(\mathrm{evaluated})}
\]

## Pearson correlation used in the optional degradation-representation audit
\[
\rho_{XY}=
\frac{\mathrm{cov}(X,Y)}{\sigma_X\sigma_Y}
\]

## Mahalanobis distance used in OOD auditing
\[
D_M(\mathbf x)=
\sqrt{(\mathbf x-\boldsymbol\mu)^{\mathsf T}
\mathbf\Sigma^{-1}
(\mathbf x-\boldsymbol\mu)}
\]

No validated 1RC/2RC electrical Digital-Twin state equations are part of the supported main framework.
