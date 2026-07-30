"""Sequence tensor cache for LSTM/TCN models.

Pre-stacks the per-symbol 10s bar parquets under ``data/raw/micro/sequences/``
into a single padded tensor of shape ``(n_dates, max_bars, n_features)`` so
the training loop is pure GPU tensor ops with no pandas / parquet overhead.

Cached tensors live under ``data/processed/sequences/{SYMBOL}_{hash}.pt`` and
are keyed on the ``SequenceSpec`` (features tuple + max_bars). Changing either
field invalidates the cache automatically.

Public API:
    SequenceSpec          — frozen dataclass describing tensor layout
    SequenceTensor        — built tensor + lengths + dates + feature names
    build_sequence_tensor — read parquet → padded tensor (no caching)
    load_sequence_tensor  — cached build (read or write .pt)
    fit_seq_normaliser    — per-feature mean/std on training dates only
    apply_normaliser      — z-score in-place, then re-zero pad positions
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from volforecast.utils.paths import micro_sequences_dir, processed_dir

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Spec + tensor container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SequenceSpec:
    """Cache key describing the desired tensor layout.

    Two specs with identical fields produce the same cache hash and therefore
    share the same on-disk ``.pt`` file. Any change (features tuple, ordering,
    max_bars) yields a new cache entry — no manual invalidation needed.

    Parameters
    ----------
    features : tuple[str, ...]
        Column names from the source parquet to include, in order. Order is
        significant: it becomes the last-axis order of the produced tensor.
    max_bars : int
        Padding / truncation target. Days with fewer bars are zero-padded;
        days with more are truncated to the first ``max_bars`` rows
        (sorted by ``bar_idx``).
    """

    features: tuple[str, ...]
    max_bars: int
    bar_interval: int = 10

    def __post_init__(self) -> None:
        if not isinstance(self.features, tuple):
            # frozen dataclass: bypass setattr
            object.__setattr__(self, "features", tuple(self.features))
        if not self.features:
            raise ValueError("features must be non-empty")
        if self.max_bars <= 0:
            raise ValueError(f"max_bars must be positive, got {self.max_bars}")

    @property
    def hash(self) -> str:
        payload = ";" .join(self.features) + f"|max_bars={self.max_bars}|bar_interval={self.bar_interval}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]


@dataclass
class SequenceTensor:
    """Per-symbol padded sequence tensor with valid-length info.

    Attributes
    ----------
    symbol : str
    tensor : torch.Tensor
        Shape ``(n_dates, max_bars, n_features)``, dtype ``float32``.
        Padded positions (beyond ``lengths[i]``) are zero.
    lengths : torch.Tensor
        Shape ``(n_dates,)``, dtype ``int64``. Number of valid bars per day.
    dates : pd.DatetimeIndex
        Length ``n_dates``. One date per outer-axis row.
    feature_names : tuple[str, ...]
        Names of the last axis, in order.
    """

    symbol: str
    tensor: torch.Tensor
    lengths: torch.Tensor
    dates: pd.DatetimeIndex
    feature_names: tuple[str, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        return int(self.tensor.shape[0])

    @property
    def n_features(self) -> int:
        return int(self.tensor.shape[2])

    @property
    def max_bars(self) -> int:
        return int(self.tensor.shape[1])

    def subset_by_dates(self, dates: pd.DatetimeIndex) -> SequenceTensor:
        """Return a new SequenceTensor containing only ``dates`` in order.

        Raises ``KeyError`` if any requested date is absent from the cached
        index — the caller is expected to align beforehand.
        """
        date_to_pos: dict[pd.Timestamp, int] = {d: i for i, d in enumerate(self.dates)}
        try:
            positions = [date_to_pos[d] for d in dates]
        except KeyError as exc:
            missing = [d for d in dates if d not in date_to_pos]
            raise KeyError(
                f"{self.symbol}: {len(missing)} requested date(s) missing from cache, "
                f"first={missing[0]}"
            ) from exc
        idx = torch.tensor(positions, dtype=torch.long)
        return SequenceTensor(
            symbol=self.symbol,
            tensor=self.tensor.index_select(0, idx),
            lengths=self.lengths.index_select(0, idx),
            dates=pd.DatetimeIndex(dates),
            feature_names=self.feature_names,
        )


# ---------------------------------------------------------------------------
# Daily lookback builder (panel → tensor)
# ---------------------------------------------------------------------------


def build_daily_lookback_tensor(
    symbol: str,
    daily_data: pd.DataFrame,
    features: tuple[str, ...],
    lookback: int,
) -> SequenceTensor:
    """Build a SequenceTensor from daily panel data using rolling lookback windows.

    Each row of the output corresponds to one target date. Its tensor row
    contains the previous ``lookback`` days of the specified feature columns.
    Earlier dates with insufficient history have shorter valid lengths.

    Parameters
    ----------
    symbol : str
        Symbol name for the tensor metadata.
    daily_data : pd.DataFrame
        Daily panel with DatetimeIndex and at least ``features`` columns.
    features : tuple[str, ...]
        Column names to include in the sequence (e.g. ("log_rv_d", "log_ret")).
    lookback : int
        Number of past days per sequence (e.g. 22 for Rosenbaum-style).

    Returns
    -------
    SequenceTensor
        Shape ``(n_dates, lookback, n_features)``.
    """
    df = daily_data[list(features)].copy()
    df = df.sort_index()
    # Drop rows where any feature is NaN (can't form valid input)
    all_valid = df.notna().all(axis=1)
    values = df.values.astype(np.float32)  # (T, F)
    dates = df.index
    n_dates = len(dates)
    n_features = len(features)

    # Pre-allocate output tensors
    tensor = torch.zeros(n_dates, lookback, n_features, dtype=torch.float32)
    lengths = torch.zeros(n_dates, dtype=torch.int64)

    for i in range(n_dates):
        # For date i, look back up to `lookback` days ending at i (inclusive).
        # This means the sequence includes day i's features because at the
        # prediction point (close of day i), today's RV and return are known.
        # Target = forward_log_rv at date i = log(rv[i+1]), so including day i
        # gives the model the same information set as HAR (which uses log_rv_d[i]).
        start = max(0, i + 1 - lookback)
        window = values[start:i + 1]  # up to lookback rows, ending at day i
        # Only include rows where all features were valid
        valid_rows = all_valid.values[start:i + 1]
        window = window[valid_rows]
        n_valid = len(window)
        if n_valid > 0:
            # Left-align: data at positions 0..n_valid-1 (oldest to newest).
            # pack_padded_sequence expects valid data starting at position 0.
            tensor[i, :n_valid, :] = torch.from_numpy(window)
            lengths[i] = n_valid

    # Remove rows with zero length (no history at all — first date)
    keep = lengths > 0
    tensor = tensor[keep]
    lengths = lengths[keep]
    kept_dates = pd.DatetimeIndex(dates[keep.numpy()])

    return SequenceTensor(
        symbol=symbol,
        tensor=tensor,
        lengths=lengths,
        dates=kept_dates,
        feature_names=features,
    )


# ---------------------------------------------------------------------------
# Build (parquet → tensor)
# ---------------------------------------------------------------------------


def build_sequence_tensor(
    symbol: str,
    spec: SequenceSpec,
    *,
    sequences_dir: Path | None = None,
) -> SequenceTensor:
    """Build a ``SequenceTensor`` for ``symbol`` from its source parquet.

    No caching — always reads from disk and computes the tensor. Use
    :func:`load_sequence_tensor` for the cached variant.

    Parameters
    ----------
    symbol : str
        Per-symbol parquet name (without extension) under ``sequences_dir``.
    spec : SequenceSpec
        Features + max_bars layout to materialise.
    sequences_dir : Path, optional
        Defaults to ``data/raw/micro/sequences/`` resolved via paths utility.

    Returns
    -------
    SequenceTensor

    Raises
    ------
    FileNotFoundError
        If the source parquet does not exist.
    KeyError
        If a requested feature column is missing from the source parquet.
    """
    if sequences_dir is None:
        sequences_dir = micro_sequences_dir().parent / "sequences_5min" if spec.bar_interval != 10 else micro_sequences_dir()
    src = Path(sequences_dir) / f"{symbol}.parquet"
    if not src.exists():
        raise FileNotFoundError(
            f"sequences parquet for {symbol!r} not found at {src}. "
            "Run `vol ingest-micro` to populate."
        )

    cols_needed = ["date", "bar_idx", *spec.features]
    df = pd.read_parquet(src, columns=cols_needed)

    missing = [c for c in spec.features if c not in df.columns]
    if missing:
        raise KeyError(f"{symbol}: requested feature columns {missing!r} not present in {src}")

    # Date normalisation: parquet stores ISO strings or pandas Timestamps.
    df["date"] = pd.to_datetime(df["date"])

    # Stable sort: date primary, bar_idx secondary. We need the bar order
    # within each day to be preserved for the LSTM input.
    df = df.sort_values(["date", "bar_idx"], kind="mergesort").reset_index(drop=True)

    # Unique dates in chronological order.
    unique_dates = pd.DatetimeIndex(df["date"].drop_duplicates().sort_values().values)
    n_dates = len(unique_dates)
    n_features = len(spec.features)
    max_bars = spec.max_bars

    tensor = torch.zeros((n_dates, max_bars, n_features), dtype=torch.float32)
    lengths = torch.zeros(n_dates, dtype=torch.int64)
    date_to_row = {d: i for i, d in enumerate(unique_dates)}

    # Vectorised by-day fill via groupby. Each group's bars are already
    # ordered correctly thanks to the sort above.
    feat_arr_all = df[list(spec.features)].to_numpy(dtype=np.float32, copy=False)
    date_series = df["date"].values

    # Compute group boundaries without a Python-level loop over rows.
    # pandas groupby preserves sort order in the indices array.
    grouped = df.groupby("date", sort=False).indices  # dict[date, np.ndarray[int]]
    for d, idx_arr in grouped.items():
        row = date_to_row[d]
        n_valid = min(len(idx_arr), max_bars)
        if n_valid < len(idx_arr):
            # Truncation: keep the first max_bars bars (already bar_idx-sorted).
            idx_arr = idx_arr[:max_bars]
        tensor[row, :n_valid, :] = torch.from_numpy(feat_arr_all[idx_arr])
        lengths[row] = n_valid

    # Mark `date_series` used so flake8/ruff sees it deliberate. (Reserved for
    # future per-row metadata if needed.)
    del date_series

    return SequenceTensor(
        symbol=symbol,
        tensor=tensor,
        lengths=lengths,
        dates=unique_dates,
        feature_names=spec.features,
    )


def build_5min_sequence_tensor(
    symbol: str,
    spec: SequenceSpec,
    *,
    sequences_dir: Path | None = None,
    bar_interval_s: int = 10,
    target_interval_s: int = 300,
) -> SequenceTensor:
    """Build a ``SequenceTensor`` from 10s bar parquets aggregated to 5-min bars.

    Reads the raw 10s parquet, aggregates to 5-min bars via
    :func:`volforecast.data.resample.aggregate_to_5min`, then pads/truncates
    to ``spec.max_bars`` (typically 78 for a full trading day of 5-min bars).

    Parameters
    ----------
    symbol : str
        Per-symbol parquet name under ``sequences_dir``.
    spec : SequenceSpec
        Features + max_bars layout. ``spec.features`` must be a subset of
        the 5-min output columns (``log_ret``, ``abs_ret``, ``rv_5min``).
    sequences_dir : Path, optional
        Defaults to ``data/raw/micro/sequences/``.
    bar_interval_s : int
        Source bar interval in seconds (default 10).
    target_interval_s : int
        Target bar interval in seconds (default 300 = 5 min).
    """
    from volforecast.data.resample import aggregate_to_5min

    if sequences_dir is None:
        sequences_dir = micro_sequences_dir()
    src = Path(sequences_dir) / f"{symbol}.parquet"
    if not src.exists():
        raise FileNotFoundError(
            f"sequences parquet for {symbol!r} not found at {src}. "
            "Run `vol ingest-micro` to populate."
        )

    # Read only columns needed for aggregation + requested features.
    agg_input_cols = {"date", "bar_idx", "log_ret", "abs_ret"}
    df = pd.read_parquet(src, columns=list(agg_input_cols))

    # Date normalisation: parquet stores ISO strings or datetime.date objects.
    df["date"] = pd.to_datetime(df["date"])

    # Aggregate 10s → 5-min bars.
    df_5min = aggregate_to_5min(df, bar_interval_s=bar_interval_s, target_interval_s=target_interval_s)

    if df_5min.empty:
        return SequenceTensor(
            symbol=symbol,
            tensor=torch.zeros((0, spec.max_bars, len(spec.features)), dtype=torch.float32),
            lengths=torch.zeros(0, dtype=torch.int64),
            dates=pd.DatetimeIndex([]),
            feature_names=spec.features,
        )

    missing = [c for c in spec.features if c not in df_5min.columns]
    if missing:
        raise KeyError(
            f"{symbol}: requested feature columns {missing!r} not available "
            f"in 5-min aggregated output. Available: {list(df_5min.columns)}"
        )

    df_5min = df_5min.sort_values(["date", "bar_idx"], kind="mergesort").reset_index(drop=True)
    unique_dates = pd.DatetimeIndex(df_5min["date"].drop_duplicates().sort_values().values)
    n_dates = len(unique_dates)
    n_features = len(spec.features)
    max_bars = spec.max_bars

    tensor = torch.zeros((n_dates, max_bars, n_features), dtype=torch.float32)
    lengths = torch.zeros(n_dates, dtype=torch.int64)
    date_to_row = {d: i for i, d in enumerate(unique_dates)}

    feat_arr_all = df_5min[list(spec.features)].to_numpy(dtype=np.float32, copy=False)
    grouped = df_5min.groupby("date", sort=False).indices
    for d, idx_arr in grouped.items():
        row = date_to_row[d]
        n_valid = min(len(idx_arr), max_bars)
        if n_valid < len(idx_arr):
            idx_arr = idx_arr[:max_bars]
        tensor[row, :n_valid, :] = torch.from_numpy(feat_arr_all[idx_arr])
        lengths[row] = n_valid

    return SequenceTensor(
        symbol=symbol,
        tensor=tensor,
        lengths=lengths,
        dates=unique_dates,
        feature_names=spec.features,
    )


def build_multiday_5min_sequence_tensor(
    symbol: str,
    spec: SequenceSpec,
    *,
    lookback_days: int = 20,
    sequences_dir: Path | None = None,
    bar_interval_s: int = 10,
    target_interval_s: int = 300,
) -> SequenceTensor:
    """Build multi-day 5-min bar sequences for TCN/LSTM models.

    Aggregates 10s bars to 5-min bars, then concatenates ``lookback_days``
    consecutive trading days into a single sequence per prediction date.

    For the DeepVol paper architecture: lookback_days=20 → 20×78=1,560
    timesteps per sequence.  Each sequence is ordered oldest→newest
    (chronological) so causal convolutions see the correct time flow.

    Dates with fewer than ``lookback_days`` of history are included with
    shorter sequences (``lengths[i] < lookback_days * bars_per_day``).

    Parameters
    ----------
    symbol : str
        Per-symbol parquet name under ``sequences_dir``.
    spec : SequenceSpec
        Features + max_bars layout. ``spec.max_bars`` should be
        ``lookback_days * bars_per_day`` (e.g. 20 * 78 = 1560).
    lookback_days : int
        Number of trading days to concatenate per sequence (default 20).
    sequences_dir : Path, optional
        Defaults to ``data/raw/micro/sequences/``.
    bar_interval_s : int
        Source bar interval in seconds (default 10).
    target_interval_s : int
        Target bar interval in seconds (default 300 = 5 min).

    Returns
    -------
    SequenceTensor
        Shape ``(n_dates, max_bars, n_features)`` with valid lengths.
    """
    from volforecast.data.resample import aggregate_to_5min

    if sequences_dir is None:
        sequences_dir = micro_sequences_dir()
    src = Path(sequences_dir) / f"{symbol}.parquet"
    if not src.exists():
        raise FileNotFoundError(
            f"sequences parquet for {symbol!r} not found at {src}. "
            "Run `vol ingest-micro` to populate."
        )

    # Read columns needed for aggregation.
    agg_input_cols = {"date", "bar_idx", "log_ret", "abs_ret"}
    df = pd.read_parquet(src, columns=list(agg_input_cols))
    df["date"] = pd.to_datetime(df["date"])

    # Aggregate 10s → 5-min bars.
    df_5min = aggregate_to_5min(df, bar_interval_s=bar_interval_s, target_interval_s=target_interval_s)

    if df_5min.empty:
        return SequenceTensor(
            symbol=symbol,
            tensor=torch.zeros((0, spec.max_bars, len(spec.features)), dtype=torch.float32),
            lengths=torch.zeros(0, dtype=torch.int64),
            dates=pd.DatetimeIndex([]),
            feature_names=spec.features,
        )

    missing = [c for c in spec.features if c not in df_5min.columns]
    if missing:
        raise KeyError(
            f"{symbol}: requested feature columns {missing!r} not available "
            f"in 5-min aggregated output. Available: {list(df_5min.columns)}"
        )

    df_5min = df_5min.sort_values(["date", "bar_idx"], kind="mergesort").reset_index(drop=True)
    unique_dates = df_5min["date"].drop_duplicates().sort_values().values
    unique_dates = pd.DatetimeIndex(unique_dates)
    n_dates = len(unique_dates)
    n_features = len(spec.features)
    max_bars = spec.max_bars

    # Pre-extract per-day feature arrays for fast concatenation.
    feat_arr_all = df_5min[list(spec.features)].to_numpy(dtype=np.float32, copy=False)
    grouped = df_5min.groupby("date", sort=False).indices
    # Build ordered list of per-day arrays.
    day_arrays: list[np.ndarray] = []
    for d in unique_dates:
        idx_arr = grouped[d]
        day_arrays.append(feat_arr_all[idx_arr])

    # Build multi-day sequences: for each date i, concatenate days
    # max(0, i+1-lookback_days) .. i (oldest to newest).
    tensor = torch.zeros((n_dates, max_bars, n_features), dtype=torch.float32)
    lengths = torch.zeros(n_dates, dtype=torch.int64)

    for i in range(n_dates):
        start = max(0, i + 1 - lookback_days)
        window_arrays = day_arrays[start : i + 1]
        concat = np.concatenate(window_arrays, axis=0)  # (total_bars, n_features)
        n_valid = min(len(concat), max_bars)
        tensor[i, :n_valid, :] = torch.from_numpy(concat[:n_valid])
        lengths[i] = n_valid

    return SequenceTensor(
        symbol=symbol,
        tensor=tensor,
        lengths=lengths,
        dates=unique_dates,
        feature_names=spec.features,
    )


# ---------------------------------------------------------------------------
# Cache (atomic write/read)
# ---------------------------------------------------------------------------


def _cache_path(symbol: str, spec: SequenceSpec, cache_dir: Path) -> Path:
    return cache_dir / f"{symbol}_{spec.hash}.pt"


def _atomic_torch_save(obj: dict, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=".pt", dir=str(target.parent))
    try:
        os.close(fd)
        torch.save(obj, tmp_path)
        os.replace(tmp_path, target)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _save_sequence_tensor(seq: SequenceTensor, path: Path) -> None:
    # Persist dates as ISO strings so we are immune to pandas' DatetimeIndex
    # precision (ns/us/ms/s — varies across pandas versions and constructors).
    payload = {
        "symbol": seq.symbol,
        "tensor": seq.tensor,
        "lengths": seq.lengths,
        "dates_iso": [d.isoformat() for d in seq.dates],
        "feature_names": list(seq.feature_names),
        "schema_version": 2,
    }
    _atomic_torch_save(payload, path)


def _load_sequence_tensor_from_disk(path: Path) -> SequenceTensor:
    # weights_only=False because we deserialise a small Python dict; the cache
    # is owned by the workspace so this is not a trust boundary.
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if "dates_iso" in payload:
        dates = pd.DatetimeIndex(pd.to_datetime(payload["dates_iso"]))
    else:  # schema_version == 1 (legacy: ns ints, precision-dependent)
        dates_ns = payload["dates_ns"].numpy()
        dates = pd.DatetimeIndex(pd.to_datetime(dates_ns, unit="ns"))
    return SequenceTensor(
        symbol=payload["symbol"],
        tensor=payload["tensor"],
        lengths=payload["lengths"],
        dates=dates,
        feature_names=tuple(payload["feature_names"]),
    )


def load_sequence_tensor(
    symbol: str,
    spec: SequenceSpec,
    *,
    sequences_dir: Path | None = None,
    cache_dir: Path | None = None,
    force_rebuild: bool = False,
) -> SequenceTensor:
    """Return a SequenceTensor, building from parquet only if cache miss.

    Cache key = ``{symbol}_{spec.hash}.pt`` under ``cache_dir`` (defaults to
    ``data/processed/sequences/``). Atomic write guarantees readers never see
    a partial file.

    Parameters
    ----------
    symbol, spec : as for :func:`build_sequence_tensor`.
    sequences_dir : Path, optional
        Source-parquet directory. Defaults to canonical micro/sequences path.
    cache_dir : Path, optional
        Where to read/write the ``.pt`` files. Defaults to
        ``data/processed/sequences``.
    force_rebuild : bool
        If True, rebuild from parquet even if the cache is present.
    """
    if cache_dir is None:
        cache_dir = processed_dir() / "sequences"
    cache_dir = Path(cache_dir)
    path = _cache_path(symbol, spec, cache_dir)

    if path.exists() and not force_rebuild:
        try:
            seq = _load_sequence_tensor_from_disk(path)
        except Exception as exc:  # noqa: BLE001 — cache corruption is recoverable
            logger.warning("sequence cache %s unreadable (%s); rebuilding", path, exc)
        else:
            if (
                seq.feature_names == spec.features
                and seq.tensor.shape[1] == spec.max_bars
                and seq.tensor.shape[2] == len(spec.features)
            ):
                return seq
            logger.warning(
                "sequence cache %s spec mismatch; rebuilding "
                "(cached features=%s, max_bars=%d; requested features=%s, max_bars=%d)",
                path,
                seq.feature_names,
                seq.tensor.shape[1],
                spec.features,
                spec.max_bars,
            )

    seq = build_sequence_tensor(symbol, spec, sequences_dir=sequences_dir)
    _save_sequence_tensor(seq, path)
    return seq


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def fit_seq_normaliser(
    seq: SequenceTensor,
    train_dates: pd.DatetimeIndex,
    *,
    eps: float = 1e-6,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute per-feature mean/std using ONLY ``train_dates`` valid bars.

    Pad rows (beyond ``lengths[i]``) and non-training dates are excluded so
    there is zero leakage from validation / test folds into the normaliser.

    Returns
    -------
    (mean, std) : tuple[torch.Tensor, torch.Tensor]
        Both shape ``(n_features,)``, dtype float32. ``std`` is clamped at
        ``eps`` to avoid div-by-zero on degenerate (all-equal) columns.
    """
    if len(train_dates) == 0:
        raise ValueError("train_dates is empty; cannot fit normaliser")
    train_set = set(pd.DatetimeIndex(train_dates))
    train_mask_np = np.array([d in train_set for d in seq.dates], dtype=bool)
    if not train_mask_np.any():
        raise ValueError(f"{seq.symbol}: none of the requested train_dates are present in cache")
    train_idx = torch.from_numpy(np.where(train_mask_np)[0]).to(torch.long)
    subset = seq.tensor.index_select(0, train_idx)  # (n_train, B, F)
    sub_lens = seq.lengths.index_select(0, train_idx)  # (n_train,)

    B = subset.shape[1]
    # Build a (n_train, B) bool mask of valid positions, expand to features.
    arange = torch.arange(B).unsqueeze(0)  # (1, B)
    valid_2d = arange < sub_lens.unsqueeze(1)  # (n_train, B)
    valid_3d = valid_2d.unsqueeze(-1).expand_as(subset)  # (n_train, B, F)

    # Flatten valid entries per feature: count via mask sum, then mean/std
    # via masked aggregation. Use float64 accumulators for numerical safety
    # over millions of bars.
    counts = valid_2d.sum().to(torch.float64).item()
    if counts <= 1:
        raise ValueError(f"{seq.symbol}: only {counts} valid bars in train set")

    x = subset.to(torch.float64)
    masked = torch.where(valid_3d, x, torch.zeros_like(x))
    sums = masked.sum(dim=(0, 1))  # (F,)
    mean = sums / counts

    sq = torch.where(valid_3d, (x - mean) ** 2, torch.zeros_like(x))
    var = sq.sum(dim=(0, 1)) / counts  # population variance
    std = var.sqrt().to(torch.float32).clamp_min(eps)
    mean = mean.to(torch.float32)
    return mean, std


def apply_normaliser(
    seq: SequenceTensor,
    mean: torch.Tensor,
    std: torch.Tensor,
) -> SequenceTensor:
    """Return a new SequenceTensor with z-score normalised features.

    Padded positions (beyond ``lengths[i]``) are re-zeroed after normalisation
    so downstream masking still sees zeros and the LSTM's packed sequence
    stays well-defined.
    """
    if mean.shape != (seq.n_features,):
        raise ValueError(f"mean shape {tuple(mean.shape)} != ({seq.n_features},)")
    if std.shape != (seq.n_features,):
        raise ValueError(f"std shape {tuple(std.shape)} != ({seq.n_features},)")
    normed = (seq.tensor - mean) / std

    # Re-zero pad positions (post-norm they would be -mean/std otherwise).
    B = seq.tensor.shape[1]
    arange = torch.arange(B).unsqueeze(0)  # (1, B)
    valid_2d = arange < seq.lengths.unsqueeze(1)  # (n_dates, B)
    pad_mask_3d = (~valid_2d).unsqueeze(-1).expand_as(normed)
    normed = normed.masked_fill(pad_mask_3d, 0.0)

    return SequenceTensor(
        symbol=seq.symbol,
        tensor=normed.to(torch.float32),
        lengths=seq.lengths,
        dates=seq.dates,
        feature_names=seq.feature_names,
    )
