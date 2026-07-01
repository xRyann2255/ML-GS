"""Diagnose LSTM 5-min training: inspect per-epoch loss curves and feature stats.

Usage: ./vol shell ../workspace/scripts/diagnose_lstm_5min.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from volforecast.data.sequence_cache import SequenceSpec, build_sequence_tensor, fit_seq_normaliser, apply_normaliser
from volforecast.models.lstm import LSTMVolModel
from volforecast.utils.paths import data_path

# --- Load 5-min sequences for SPY ---
features = (
    "log_ret", "abs_ret", "vol_share", "buy_ratio",
    "order_flow_imbalance", "rolling_vpin", "cum_rv", "session_frac",
    "price_accel", "log_n_trades", "intrabar_rv", "volume_surprise",
)
spec = SequenceSpec(features=features, max_bars=78, bar_interval=300)
print(f"Loading SPY 5-min sequences (spec hash: {spec.hash})...")
seq = build_sequence_tensor("SPY", spec)
print(f"  Shape: {seq.tensor.shape} ({seq.tensor.shape[0]} dates, {seq.tensor.shape[1]} bars, {seq.tensor.shape[2]} features)")
print(f"  Date range: {seq.dates[0]} to {seq.dates[-1]}")
print(f"  Mean length: {seq.lengths.float().mean():.1f} bars")

# --- Feature statistics (pre-normalisation) ---
print("\n--- RAW Feature Statistics (non-padded values only) ---")
T = seq.tensor.numpy()
L = seq.lengths.numpy()
for i, f in enumerate(features):
    vals = []
    for d in range(T.shape[0]):
        vals.append(T[d, :L[d], i])
    vals = np.concatenate(vals)
    print(f"  {f:25s}: mean={vals.mean():10.4f}  std={vals.std():10.4f}  min={vals.min():10.4f}  max={vals.max():10.4f}")

# --- Load target (log RV) ---
rv_path = data_path("raw/ticks/SPY.parquet")
if not rv_path.exists():
    print(f"\nERROR: {rv_path} not found")
    sys.exit(1)

rv_df = pd.read_parquet(rv_path)
rv_df.index = pd.to_datetime(rv_df.index)
# Target = forward log RV (h=1)
if "log_rv" in rv_df.columns:
    target_col = "log_rv"
elif "rv" in rv_df.columns:
    target_col = "rv"
    rv_df["log_rv"] = np.log(rv_df["rv"])
    target_col = "log_rv"
else:
    print(f"Available columns: {list(rv_df.columns)[:20]}")
    sys.exit(1)

# Align dates
common_dates = seq.dates.intersection(rv_df.index)
print(f"\nCommon dates with target: {len(common_dates)}")

# Forward target: y[t] = log_rv[t+1]
target_series = rv_df[target_col].shift(-1)
aligned_target = target_series.reindex(common_dates).dropna()
aligned_dates = aligned_target.index

# Subset sequence tensor
seq_aligned = seq.subset_by_dates(pd.DatetimeIndex(aligned_dates))
y = aligned_target.values.astype(np.float32)
print(f"Training samples: {len(y)}")
print(f"Target stats: mean={y.mean():.4f}, std={y.std():.4f}, min={y.min():.4f}, max={y.max():.4f}")

# --- Train with verbose logging (no normalisation first) ---
print("\n\n=== EXPERIMENT 1: NO NORMALISATION ===")
model_raw = LSTMVolModel(
    input_dim=12, hidden_dim=64, n_layers=2,
    loss="qlike", pool_mode="attention", head_mode="mlp",
    max_epochs=15, batch_size=64, learning_rate=1e-3,
    val_fraction=0.15, early_stopping_rounds=0,  # no early stopping
    dropout=0.1, weight_decay=1e-4,
)
model_raw.fit(seq_aligned, y)
print("\nEpoch | Train Loss | Val Loss")
print("-" * 40)
for entry in model_raw.history_:
    vl = entry.get("val_loss", float("nan"))
    print(f"  {entry['epoch']:3d}  | {entry['train_loss']:10.4f} | {vl:10.4f}")

# --- Train with normalisation ---
print("\n\n=== EXPERIMENT 2: WITH NORMALISATION ===")
# Compute normaliser on train portion (first 85%)
n_train = int(len(y) * 0.85)
train_dates = pd.DatetimeIndex(aligned_dates[:n_train])
mean_stats, std_stats = fit_seq_normaliser(seq_aligned, train_dates)
seq_normed = apply_normaliser(seq_aligned, mean_stats, std_stats)

# Check normalised stats
T_n = seq_normed.tensor.numpy()
L_n = seq_normed.lengths.numpy()
print("\n--- NORMALISED Feature Statistics ---")
for i, f in enumerate(features):
    vals = []
    for d in range(T_n.shape[0]):
        vals.append(T_n[d, :L_n[d], i])
    vals = np.concatenate(vals)
    print(f"  {f:25s}: mean={vals.mean():8.4f}  std={vals.std():8.4f}")

model_norm = LSTMVolModel(
    input_dim=12, hidden_dim=64, n_layers=2,
    loss="qlike", pool_mode="attention", head_mode="mlp",
    max_epochs=15, batch_size=64, learning_rate=1e-3,
    val_fraction=0.15, early_stopping_rounds=0,
    dropout=0.1, weight_decay=1e-4,
)
model_norm.fit(seq_normed, y)
print("\nEpoch | Train Loss | Val Loss")
print("-" * 40)
for entry in model_norm.history_:
    vl = entry.get("val_loss", float("nan"))
    print(f"  {entry['epoch']:3d}  | {entry['train_loss']:10.4f} | {vl:10.4f}")

# Final predictions QLIKE
from volforecast.evaluation.metrics import qlike
preds_raw = model_raw.predict(seq_aligned)
preds_norm = model_norm.predict(seq_normed)
print(f"\n\n=== RESULTS ===")
print(f"Raw QLIKE:        {qlike(y, preds_raw):.4f}")
print(f"Normalised QLIKE: {qlike(y, preds_norm):.4f}")
print(f"Naive (mean):     {qlike(y, np.full_like(y, y.mean())):.4f}")
