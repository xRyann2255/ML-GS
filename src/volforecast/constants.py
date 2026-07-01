"""Pure-data constants for the volforecast package.

Universe definitions, timezone, field lists, regime boundaries, and default paths.
No logic — only data declarations.
"""

from __future__ import annotations

from pathlib import Path

import pytz

# ---------------------------------------------------------------------------
# Time zone
# ---------------------------------------------------------------------------

TZ = pytz.timezone("America/New_York")

# ---------------------------------------------------------------------------
# Chunk Store / Tick data
# ---------------------------------------------------------------------------

CHUNKDB = "Eq"

L1_FIELDS = ["TRDPRC_1", "TRDVOL_1", "ASK", "BID", "ASKSIZE", "BIDSIZE"]

L2_FIELDS = [
    "ASK1",
    "ASK2",
    "ASK3",
    "ASK4",
    "ASK5",
    "BID1",
    "BID2",
    "BID3",
    "BID4",
    "BID5",
    "ASKSIZE1",
    "ASKSIZE2",
    "ASKSIZE3",
    "ASKSIZE4",
    "ASKSIZE5",
    "BIDSIZE1",
    "BIDSIZE2",
    "BIDSIZE3",
    "BIDSIZE4",
    "BIDSIZE5",
]

# ---------------------------------------------------------------------------
# Symbol universe (34 symbols)
# ---------------------------------------------------------------------------

EQUITY_SYMBOLS = frozenset(
    {
        "AAPL",
        "MSFT",
        "AMZN",
        "GOOGL",
        "META",
        "NVDA",
        "TSLA",
        "BRK.B",
        "JPM",
        "JNJ",
        "V",
        "PG",
        "UNH",
        "HD",
        "MA",
        "DIS",
        "PYPL",
        "BAC",
        "CMCSA",
        "XOM",
        "NFLX",
        "ADBE",
        "CRM",
        "PFE",
        "TMO",
        "CSCO",
        "ABT",
        "AVGO",
        "ACN",
        "NKE",
    }
)

ETF_SYMBOLS = frozenset({"SPY", "QQQ", "IWM", "DIA"})

FUTURES_SYMBOLS = frozenset({"ES"})

INDEX_SYMBOLS = frozenset({"SPX"})

SYMBOL_UNIVERSE = EQUITY_SYMBOLS | ETF_SYMBOLS | FUTURES_SYMBOLS | INDEX_SYMBOLS

# ---------------------------------------------------------------------------
# Chunk Store RIC mapping
# ---------------------------------------------------------------------------
# Chunk Store requires exchange-suffixed RICs for NASDAQ symbols.
# NYSE/Arca work bare, but explicit RICs are more reliable for large queries.
# Source: data audit (workspace/docs/data-audit.md Section 2.5)

TICKER_TO_RIC: dict[str, str] = {
    # NASDAQ (.OQ)
    "AAPL": "AAPL.OQ",
    "MSFT": "MSFT.OQ",
    "AMZN": "AMZN.OQ",
    "GOOGL": "GOOGL.OQ",
    "META": "META.OQ",
    "NVDA": "NVDA.OQ",
    "TSLA": "TSLA.OQ",
    "NFLX": "NFLX.OQ",
    "ADBE": "ADBE.OQ",
    "AVGO": "AVGO.OQ",
    "COST": "COST.OQ",
    "CSCO": "CSCO.OQ",
    "PYPL": "PYPL.OQ",
    "CMCSA": "CMCSA.OQ",
    "AMD": "AMD.OQ",
    # NYSE (.N)
    "BRK.B": "BRKb.N",
    "JPM": "JPM.N",
    "JNJ": "JNJ.N",
    "V": "V.N",
    "PG": "PG.N",
    "UNH": "UNH.N",
    "HD": "HD.N",
    "MA": "MA.N",
    "DIS": "DIS.N",
    "BAC": "BAC.N",
    "XOM": "XOM.N",
    "PFE": "PFE.N",
    "NKE": "NKE.N",
    "CRM": "CRM.N",
    "ACN": "ACN.N",
    "TMO": "TMO.N",
    "ABT": "ABT.N",
    # NYSE Arca (.P)
    "SPY": "SPY.P",
    "QQQ": "QQQ.P",
    "IWM": "IWM.P",
    "DIA": "DIA.P",
    # Futures: resolved dynamically (ES -> ESM26 etc.), no static entry needed
    # Index
    "SPX": ".SPX",
}

# 8-symbol subset for fast iteration (~75% less compute vs full 34)
# SPY/IWM: ETFs, AAPL/MSFT/NVDA: tech, XOM: energy, JPM: financials, ES: futures
DEV_UNIVERSE = frozenset({"SPY", "AAPL", "MSFT", "NVDA", "XOM", "JPM", "IWM", "ES"})

# ---------------------------------------------------------------------------
# EDRVOL (per-symbol implied vol from TSDB edrvol_ namespace)
# ---------------------------------------------------------------------------
# Lowercase RICs for the 32 equity/ETF symbols with EDRVOL coverage.
# Pattern: edrvol_{ric}@{field}

TICKER_TO_EDRVOL_RIC: dict[str, str] = {
    # NASDAQ (.oq)
    "AAPL": "aapl.oq",
    "ADBE": "adbe.oq",
    "AMZN": "amzn.oq",
    "AVGO": "avgo.oq",
    "COST": "cost.oq",
    "GOOGL": "googl.oq",
    "META": "meta.oq",
    "MSFT": "msft.oq",
    "NFLX": "nflx.oq",
    "NVDA": "nvda.oq",
    "TSLA": "tsla.oq",
    "QQQ": "qqq.oq",
    # NYSE (.n)
    "ABBV": "abbv.n",
    "ABT": "abt.n",
    "ACN": "acn.n",
    "BAC": "bac.n",
    "CRM": "crm.n",
    "HD": "hd.n",
    "JNJ": "jnj.n",
    "JPM": "jpm.n",
    "LLY": "lly.n",
    "MA": "ma.n",
    "PG": "pg.n",
    "TMO": "tmo.n",
    "UNH": "unh.n",
    "UNP": "unp.n",
    "V": "v.n",
    "WMT": "wmt.n",
    "XOM": "xom.n",
    # NYSE Arca (.p)
    "DIA": "dia.p",
    "IWM": "iwm.p",
    "SPY": "spy.p",
    # Cross-asset ETFs (.p)
    "HYG": "hyg.p",
    "GLD": "gld.p",
    "EEM": "eem.p",
    "XLF": "xlf.p",
    "TLT": "tlt.p",
    "USO": "uso.p",
    # Index (no suffix)
    "SPX": "spx",
    # Futures (ES uses SPX vol surface)
    "ES": "spx",
}

# ---------------------------------------------------------------------------
# Marquee Dataset RICs (uppercase, for EDRVOL_PERCENT_EXPIRY etc.)
# ---------------------------------------------------------------------------
# Derived from TICKER_TO_EDRVOL_RIC but uppercase with proper exchange suffixes.
# SPX uses ".SPX" (dot-prefixed index convention in Marquee).

TICKER_TO_MARQUEE_RIC: dict[str, str] = {
    # NASDAQ (.OQ)
    "AAPL": "AAPL.OQ",
    "ADBE": "ADBE.OQ",
    "AMZN": "AMZN.OQ",
    "AVGO": "AVGO.OQ",
    "COST": "COST.OQ",
    "GOOGL": "GOOGL.OQ",
    "META": "META.OQ",
    "MSFT": "MSFT.OQ",
    "NFLX": "NFLX.OQ",
    "NVDA": "NVDA.OQ",
    "TSLA": "TSLA.OQ",
    "QQQ": "QQQ.OQ",
    # NYSE (.N)
    "ABBV": "ABBV.N",
    "ABT": "ABT.N",
    "ACN": "ACN.N",
    "BAC": "BAC.N",
    "CRM": "CRM.N",
    "HD": "HD.N",
    "JNJ": "JNJ.N",
    "JPM": "JPM.N",
    "LLY": "LLY.N",
    "MA": "MA.N",
    "PG": "PG.N",
    "TMO": "TMO.N",
    "UNH": "UNH.N",
    "UNP": "UNP.N",
    "V": "V.N",
    "WMT": "WMT.N",
    "XOM": "XOM.N",
    # NYSE Arca (.P)
    "DIA": "DIA.P",
    "IWM": "IWM.P",
    "SPY": "SPY.P",
    # Cross-asset ETFs (.P)
    "HYG": "HYG.P",
    "GLD": "GLD.P",
    "EEM": "EEM.P",
    "XLF": "XLF.P",
    "TLT": "TLT.P",
    "USO": "USO.P",
    # Index
    "SPX": ".SPX",
    # Futures (ES uses SPX vol surface)
    "ES": ".SPX",
}

# ---------------------------------------------------------------------------
# TSDB fields
# ---------------------------------------------------------------------------

OHLCV_FIELDS = ["open", "high", "low", "close", "volume"]

TREASURY_SYMBOLS = {"2y": "US2Y", "5y": "US5Y", "10y": "US10Y", "30y": "US30Y"}

FX_SYMBOLS = {"USD/JPY": "USDJPY", "EUR/USD": "EURUSD"}

COMMODITY_SYMBOLS = {"CL": "CL1", "GC": "GC1"}

# ---------------------------------------------------------------------------
# Cross-asset ingestion (Layer 4)
# ---------------------------------------------------------------------------

# ETF implied vol via TSDB edrvol_ namespace (ticker → edrvol RIC suffix)
XASSET_ETF_IV: dict[str, str] = {
    "HYG": "hyg.p",
    "GLD": "gld.p",
    "EEM": "eem.p",
    "XLF": "xlf.p",
}

# ETF prices for realized vol computation (ticker → TSDB RIC)
XASSET_ETF_PRICE: dict[str, str] = {
    "HYG": "HYG.P",
    "GLD": "GLD.P",
    "USO": "USO.P",
    "EEM": "EEM.P",
    "TLT": "TLT.P",
}

# TSDB symbols for indices
DXY_TSDB_SYMBOL = "eqsp_s_.dxy@close"
GVZ_TSDB_SYMBOL = "eqpad_.GVZ@close"

# Marquee Dataset query params (confirmed working via probe 2026-06-01)
MARQUEE_FX_VOL = {
    "dataset_id": "FXIMPLIEDVOL_PREMIUM",
    "pairs": {
        "USDJPY": {"bbid": "USDJPY", "tenor": "1m", "deltaStrike": "DN"},
        "EURUSD": {"bbid": "EURUSD", "tenor": "1m", "deltaStrike": "DN"},
    },
    "value_col": "impliedVolatility",
}

MARQUEE_COMMODITY_VOL = {
    "dataset_id": "COMMODVOL_STANDARD",
    "query": {"bbid": "CL1 Comdty", "deltaStrike": "ATM"},
    "value_col": "impliedVolatility",
}

MARQUEE_RATE_VOL = {
    "dataset_id": "IR_SWAPTION_VOLS_STANDARD",
    "query": {"pricingLocation": "NYC", "expirationTenor": "1y", "terminationTenor": "10y"},
    "value_col": "impliedNormalVolatility",
}

MARQUEE_CREDIT_VOL = {
    "dataset_id": "CDSIVOL",
    "query": {},  # Fetch all, filter deltaStrike='ATMF' post-hoc
    "value_col": "impliedVolatility",
    "post_filter": {"deltaStrike": "ATMF"},
}

# Cross-asset output files
XASSET_OUTPUT_FILES = ("rates.parquet", "fx_vol.parquet", "credit.parquet", "commodity.parquet")

# ---------------------------------------------------------------------------
# Correlation ingestion (Layer 7 — SPX implied/realized correlation)
# ---------------------------------------------------------------------------

MARQUEE_IMPLIED_CORR = {
    "dataset_id": "EDR_INDEX_IMPLIEDCORR",
    "query": {"bbid": "SPX", "tenor": "1m", "strikeReference": "forward", "relativeStrike": 1.0},
    "value_col": "correlation",
}

MARQUEE_REALIZED_CORR = {
    "dataset_id": "EDR_INDEX_REALIZEDCORR",
    "query": {"bbid": "SPX", "tenor": "1m"},
    "value_col": "correlation",
}

MARQUEE_AVG_IMPLIED_VOL = {
    "dataset_id": "EDR_INDEX_AVERAGE_IMPLIED_VOL",
    "query": {"bbid": "SPX", "tenor": "1m", "strikeReference": "forward", "relativeStrike": 1.0},
    "value_col": "volatility",
}

CORR_ZSCORE_WINDOW = 60  # 60 trading days (~3 months) for regime z-score

# ---------------------------------------------------------------------------
# Microstructure ingestion (Layer 3 — LeeReady signed volume)
# ---------------------------------------------------------------------------

MICRO_FIELDS = ["TRDPRC_1", "TRDVOL_1"]
MICRO_BAR_INTERVAL = 10.0  # seconds (2,340 bars per RTH session)
MICRO_DAILY_COLUMNS = [
    "signed_volume_ratio",
    "vpin",
    "order_flow_imbalance",
    "buy_volume",
    "sell_volume",
    "total_volume",
]
VPIN_N_BUCKETS = 50

# ---------------------------------------------------------------------------
# Regime boundaries
# ---------------------------------------------------------------------------

COVID_START = "2020-02-20"
COVID_END = "2020-06-30"

# ---------------------------------------------------------------------------
# Default paths (relative to workspace root)
# ---------------------------------------------------------------------------

DEFAULT_TMP_DIR = Path("workspace/tmp")
DEFAULT_NOTEBOOKS_DIR = Path("workspace/notebooks")
DEFAULT_MODELS_DIR = Path("data/models")
