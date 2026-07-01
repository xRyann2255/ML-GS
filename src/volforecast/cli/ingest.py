"""CLI entry point for data ingestion.

Fetches tick data from Chunk Store and builds daily RV panels for all
symbols in the experiment config. Saves parquet files to data/raw/.

Usage:
    vol run --config workspace/configs/ingest_full_universe.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path

from volforecast.config import ExperimentConfig
from volforecast.utils.manifest import record_ingestion, record_ingestion_yaml
from volforecast.utils.paths import rv_cache_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for data ingestion."""
    parser = argparse.ArgumentParser(
        prog="volforecast ingest",
        description="Fetch tick data and build daily RV panels",
    )
    parser.add_argument("--config", type=Path, required=True, help="Path to experiment YAML config")
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbol subset (overrides config universe)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel threads for batch fetching (overrides config)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Max trading days per single API call (overrides config)",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=None,
        help="Save cache every N processed days (overrides config)",
    )
    parser.add_argument(
        "--compute-workers",
        type=int,
        default=None,
        help="Threads for parallel RV computation (overrides config)",
    )
    parser.add_argument(
        "--symbol-workers",
        type=int,
        default=None,
        help="Number of symbols to ingest concurrently (overrides config)",
    )
    return parser.parse_args(argv)


def run(
    config: ExperimentConfig,
    symbols: list[str] | None = None,
    progress=None,
    max_workers: int | None = None,
    batch_size: int | None = None,
    checkpoint_interval: int | None = None,
    compute_workers: int | None = None,
    symbol_workers: int | None = None,
) -> dict[str, int]:
    """Execute data ingestion for all symbols in config.

    Parameters
    ----------
    config : ExperimentConfig
        Experiment configuration with universe and date_range.
    symbols : list[str] | None
        Optional symbol subset override.
    progress : ExperimentProgress | StageProgress | None
        Progress display handle. If None, creates a standalone StageProgress.
    max_workers : int | None
        Override for parallel fetch threads (default: from config.ingest).
    batch_size : int | None
        Override for max days per API call (default: from config.ingest).
    checkpoint_interval : int | None
        Override for checkpoint cadence (default: from config.ingest).
    compute_workers : int | None
        Override for parallel compute threads (default: from config.ingest).
    symbol_workers : int | None
        Override for cross-symbol concurrency (default: from config.ingest).

    Returns
    -------
    dict[str, int]
        Mapping of symbol → number of rows in the RV panel.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from volforecast.cli.progress import ExperimentProgress, StageProgress, _format_elapsed
    from volforecast.data import rv_panel as _rv_panel

    # Resolve ingest parameters: CLI overrides > config > defaults
    _workers = max_workers if max_workers is not None else config.ingest.workers
    _batch_size = batch_size if batch_size is not None else config.ingest.batch_size
    _checkpoint = (
        checkpoint_interval
        if checkpoint_interval is not None
        else config.ingest.checkpoint_interval
    )
    _compute_workers = (
        compute_workers if compute_workers is not None else config.ingest.compute_workers
    )
    _symbol_workers = symbol_workers if symbol_workers is not None else config.ingest.symbol_workers

    universe = symbols or config.universe
    start = date.fromisoformat(config.date_range[0])
    end = date.fromisoformat(config.date_range[1])
    cache = rv_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)

    standalone = progress is None
    if standalone:
        progress = StageProgress("ingest", config.name, universe)
        progress.__enter__()

    # Add outer symbol task (skip for single-symbol runs — the subtask shows progress)
    is_pipeline = isinstance(progress, ExperimentProgress)
    task_key: str | None = None
    if len(universe) > 1:
        if is_pipeline:
            task_key = progress.add_task("INGEST", total=len(universe), description="symbols")
        else:
            task_key = progress.add_task(total=len(universe), description="symbols")

    def _ingest_one_symbol(sym: str) -> tuple[str, int]:
        """Ingest a single symbol and return (symbol, n_rows)."""
        sym_start = time.time()

        panel = _rv_panel.build_rv_panel(
            sym,
            start,
            end,
            cache_dir=cache,
            progress=progress if _symbol_workers <= 1 else None,
            max_workers=_workers,
            batch_size=_batch_size,
            checkpoint_interval=_checkpoint,
            compute_workers=_compute_workers,
        )

        panel = _rv_panel.enrich_panel_with_ohlcv(panel, sym, start, end)
        if not panel.empty and "open" in panel.columns:
            # Merge OHLCV into the full cache (which may span a wider date range
            # than the returned panel) to avoid narrowing previously cached data.
            full_cache = _rv_panel.load_rv_cache(sym, cache)
            if full_cache is not None and len(full_cache) > len(panel):
                import pandas as _pd

                full_cache["open"] = (
                    panel["open"]
                    .reindex(full_cache.index)
                    .combine_first(full_cache.get("open", _pd.Series(dtype=float)))
                )
                full_cache["close"] = (
                    panel["close"]
                    .reindex(full_cache.index)
                    .combine_first(full_cache.get("close", _pd.Series(dtype=float)))
                )
                _rv_panel.save_rv_cache(full_cache, sym, cache)
            else:
                _rv_panel.save_rv_cache(panel, sym, cache)

        n_rows = len(panel)

        if n_rows > 0:
            skipped = panel.attrs.get("skipped_dates", [])
            record_ingestion("rv", sym, start, end, n_rows, skipped_dates=skipped)
            record_ingestion_yaml("rv", sym, start, end, n_rows)

        elapsed = _format_elapsed(time.time() - sym_start)

        msg = f"{sym}: {n_rows:,} days [{elapsed}]"
        if is_pipeline:
            progress.log("INGEST", msg)
        else:
            progress.log(msg)

        if task_key is not None:
            progress.advance(task_key)
        return sym, n_rows

    results: dict[str, int] = {}

    if _symbol_workers <= 1:
        # Serial symbol processing (existing behavior)
        for symbol in universe:
            sym, n_rows = _ingest_one_symbol(symbol)
            results[sym] = n_rows
    else:
        # Parallel symbol processing
        if is_pipeline:
            progress.log("INGEST", f"Parallel mode: {_symbol_workers} symbol-workers")
        else:
            progress.log(f"Parallel mode: {_symbol_workers} symbol-workers")
        with ThreadPoolExecutor(max_workers=_symbol_workers) as pool:
            futures = {pool.submit(_ingest_one_symbol, sym): sym for sym in universe}
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    sym, n_rows = future.result()
                    results[sym] = n_rows
                except Exception as exc:  # noqa: BLE001
                    logging.getLogger(__name__).error(
                        "%s: ingest failed: %s",
                        sym,
                        exc,
                        exc_info=True,
                    )
                    results[sym] = 0

    if standalone:
        total = sum(results.values())
        progress.finish(f"{len(results)} symbols, {total:,} total days")
        progress.__exit__(None, None, None)

    return results


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ingest CLI."""
    from volforecast.cli.console import setup_logging

    setup_logging()
    args = parse_args(argv)
    config = ExperimentConfig.from_yaml(args.config)
    symbols = args.symbols.split(",") if args.symbols else None

    try:
        run(
            config,
            symbols,
            max_workers=args.workers,
            batch_size=args.batch_size,
            checkpoint_interval=args.checkpoint_interval,
            compute_workers=args.compute_workers,
            symbol_workers=args.symbol_workers,
        )
    except ConnectionError as e:
        print(f"[ingest] ERROR: Cannot connect to data source: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
