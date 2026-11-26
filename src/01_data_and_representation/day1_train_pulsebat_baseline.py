from pathlib import Path
import json, re, warnings, joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

SEED = 42
ROOT = Path.cwd()
DATA_DIR = ROOT / "Pulse-Voltage-Response-Generation" / "ProcessedData_adjustable"
OUT = ROOT / "Day1_PulseBat_Baseline_Results"
OUT.mkdir(parents=True, exist_ok=True)

def pick_col(columns, candidates):
    low = {str(c).strip().lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in low:
            return low[cand.lower()]
    for c in columns:
        lc = str(c).strip().lower()
        for cand in candidates:
            if cand.lower() in lc:
                return c
    return None

files = sorted(DATA_DIR.rglob("*.xlsx"))
if not files:
    raise FileNotFoundError("No xlsx files found. Clone Pulse-Voltage-Response-Generation first.")

frames, audit = [], []
for f in files:
    try:
        xl = pd.ExcelFile(f)
        sheet = "SOC ALL" if "SOC ALL" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(f, sheet_name=sheet).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]
        rel = f.relative_to(DATA_DIR)
        df["_source_file"] = str(rel)
        df["_chemistry_group"] = rel.parts[0] if rel.parts else f.parent.name
        frames.append(df)
        audit.append({"file": str(rel), "sheet": sheet, "rows": len(df),
                      "columns": len(df.columns), "column_names": " | ".join(df.columns)})
    except Exception as e:
        audit.append({"file": str(f), "sheet": "ERROR", "rows": 0, "columns": 0,
                      "column_names": repr(e)})

pd.DataFrame(audit).to_csv(OUT / "dataset_audit.csv", index=False)
df = pd.concat(frames, ignore_index=True, sort=False)

target = pick_col(df.columns, ["SOH"])
if target is None:
    raise ValueError("SOH column not found. Check dataset_audit.csv")
df[target] = pd.to_numeric(df[target], errors="coerce")
df = df[df[target].notna()].copy()

u_cols = []
for c in df.columns:
    m = re.fullmatch(r"U(\d+)", str(c).strip(), flags=re.I)
    if m and 1 <= int(m.group(1)) <= 41:
        u_cols.append(c)
u_cols = sorted(u_cols, key=lambda x: int(re.findall(r"\d+", str(x))[0]))
if len(u_cols) < 5:
    raise ValueError("Too few U features found. Check dataset_audit.csv")

soc_col = pick_col(df.columns, ["SOCR", "SOC"])
numeric_features = list(u_cols)
if soc_col is not None and soc_col != target:
    df[soc_col] = pd.to_numeric(df[soc_col], errors="coerce")
    numeric_features.append(soc_col)

categorical_features = ["_chemistry_group"]
id_col = pick_col(df.columns, ["ID", "BatteryID", "Battery_ID", "No.", "No", "cell_id"])
if id_col is not None:
    df["_group_id"] = df["_chemistry_group"].astype(str) + "::" + df[id_col].astype(str)
else:
    df["_group_id"] = df["_source_file"].astype(str)
    warnings.warn("No explicit battery ID found; verify grouping before publication.")

for c in numeric_features:
    df[c] = pd.to_numeric(df[c], errors="coerce")

keep = numeric_features + categorical_features + [target, "_group_id", "_source_file"]
model_df = df[keep].copy()
model_df = model_df[model_df[u_cols].notna().any(axis=1)].reset_index(drop=True)

groups = model_df["_group_id"]
if groups.nunique() >= 5:
    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
    tr_idx, te_idx = next(gss.split(model_df, groups=groups))
else:
    tr_idx, te_idx = train_test_split(np.arange(len(model_df)), test_size=0.20, random_state=SEED)

train = model_df.iloc[tr_idx].copy()
test = model_df.iloc[te_idx].copy()
X_train = train[numeric_features + categorical_features]
X_test = test[numeric_features + categorical_features]
y_train = train[target].astype(float)
y_test = test[target].astype(float)

if y_train.median() > 2:
    y_train = y_train / 100.0
    y_test = y_test / 100.0

pre = ColumnTransformer([
    ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric_features),
    ("cat", Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ]), categorical_features),
])

models = {
    "ExtraTrees": ExtraTreesRegressor(n_estimators=700, random_state=SEED, n_jobs=-1,
                                     min_samples_leaf=2, max_features=0.8),
    "RandomForest": RandomForestRegressor(n_estimators=500, random_state=SEED, n_jobs=-1,
                                         min_samples_leaf=2, max_features=0.8),
    "HistGradientBoosting": HistGradientBoostingRegressor(learning_rate=0.05, max_iter=500,
                                                         l2_regularization=1e-3,
                                                         random_state=SEED),
}

metrics, preds = [], []
for name, est in models.items():
    pipe = Pipeline([("pre", pre), ("model", est)])
    pipe.fit(X_train, y_train)
    p = pipe.predict(X_test)
    mae = mean_absolute_error(y_test, p)
    rmse = mean_squared_error(y_test, p) ** 0.5
    r2 = r2_score(y_test, p)
    metrics.append({"model": name, "MAE_pp": mae*100, "RMSE_pp": rmse*100, "R2": r2,
                    "n_train": len(train), "n_test": len(test),
                    "train_groups": train["_group_id"].nunique(),
                    "test_groups": test["_group_id"].nunique()})
    q = test[["_group_id", "_source_file", target]].copy()
    q["model"] = name
    q["true_soh_fraction"] = y_test.to_numpy()
    q["pred_soh_fraction"] = p
    q["error_pp"] = (p-y_test.to_numpy())*100
    preds.append(q)
    joblib.dump(pipe, OUT / f"{name}_model.joblib")

metrics_df = pd.DataFrame(metrics).sort_values("MAE_pp")
metrics_df.to_csv(OUT/"baseline_metrics.csv", index=False)
preds_df = pd.concat(preds, ignore_index=True)
preds_df.to_csv(OUT/"test_predictions.csv", index=False)

best = metrics_df.iloc[0]["model"]
p = preds_df[preds_df["model"] == best]
plt.figure(figsize=(6,6))
plt.scatter(p["true_soh_fraction"]*100, p["pred_soh_fraction"]*100, alpha=0.7)
lo = min((p["true_soh_fraction"]*100).min(), (p["pred_soh_fraction"]*100).min())
hi = max((p["true_soh_fraction"]*100).max(), (p["pred_soh_fraction"]*100).max())
plt.plot([lo,hi],[lo,hi],"--")
plt.xlabel("True SOH (%)"); plt.ylabel("Predicted SOH (%)")
plt.title(f"PulseBat baseline — {best}")
plt.tight_layout()
plt.savefig(OUT/"true_vs_predicted_soh.png", dpi=300)
plt.savefig(OUT/"true_vs_predicted_soh.pdf")
plt.close()

summary = {
    "rows": len(model_df),
    "target": str(target),
    "soc_col": None if soc_col is None else str(soc_col),
    "id_col": None if id_col is None else str(id_col),
    "u_feature_count": len(u_cols),
    "best_model": str(best),
    "note": "Day-1 baseline only. Final paper still needs DT/physics features, few-shot, UQ, OOD and external validation."
}
(OUT/"run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("\n=== TRAINING COMPLETE ===")
print(metrics_df.to_string(index=False))
print("\nResults:", OUT.resolve())
