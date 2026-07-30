# ml_vol_estimator

Python package for ML realized volatility forecasting — signal discovery.

## Installation

```bash
pip install -e .
```

## Usage

```python
from ml_vol_estimator.features import har
from ml_vol_estimator.models import baselines
from ml_vol_estimator.evaluation import metrics
```

## Package Structure

- `data/` — Data access: Chunk Store tick data, TSDB daily, Marquee IV surface
- `features/` — Feature layers 0–6: HAR, asymmetry, options, microstructure, cross-asset, calendar
- `models/` — HAR baselines, LightGBM, LSTM/TCN, ensemble
- `evaluation/` — QLIKE metrics, statistical tests (DM, MCS), economic value
- `pipeline/` — Orchestration (feature build, train, evaluate per model)
- `utils/` — Purged k-fold CV, walk-forward splits, expanding window utilities
