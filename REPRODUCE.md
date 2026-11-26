# Reproduction Guide

## Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r environment/requirements-lock.txt
```

If exact lock installation is platform-specific:
```powershell
pip install -r environment/requirements-core.txt
```

## Data
See `data/README_DATA_ACCESS.md`.

## Code
Complete discovered source history: `src/full_history/`.

## Evidence
Frozen/archived outputs:
- `results/frozen_core/`
- `results/full_history/`

Publication assets:
- `figures/main/`
- `figures/supplementary/`
- `tables/`

Audit:
- `audit/repository_manifest.csv`
- `audit/checksums_sha256.csv`
- `audit/missing_expected_assets.txt`

Missing assets are never fabricated.
