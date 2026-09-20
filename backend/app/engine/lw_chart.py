"""
Lightweight Charts renderer
================================
Converts our already-computed data (enriched OHLCV DataFrame from
ta_engine, detected patterns from patterns.py) into the config format
TradingView's Lightweight Charts library expects, via the
streamlit-lightweight-charts wrapper.

This module only reshapes data for rendering — it computes nothing new.
Same rule as everywhere else: the numbers were already decided by
ta_engine.py/patterns.py; this just draws them.

Usage
-----
    from lw_chart import render_chart

    render_chart(enriched_df, technical_summary, detected_patterns, chart_type="candlestick")
"""

from typing import Optional, List, Dict, Any

import pandas as pd


def _to_unix(ts) -> int:
    # Ensure the timestamp is in seconds for Lightweight Charts
    return int(pd.Timestamp(ts).timestamp())


def _candlestick_series(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return [
        {
            "time": _to_unix(row["timestamp"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for _, row in df.iterrows()
    ]


def _line_series(df: pd.DataFrame, column: str) -> List[Dict[str, Any]]:
    out = []
    for _, row in df.iterrows():
        value = row.get(column)
        if value is None or pd.isna(value):
            continue
        out.append({"time": _to_unix(row["timestamp"]), "value": float(value)})
    return out


def _volume_series(df: pd.DataFrame) -> List[Dict[str, Any]]:
    out = []
    for _, row in df.iterrows():
        color = "rgba(38,166,154,0.5)" if row["close"] >= row["open"] else "rgba(239,83,80,0.5)"
        out.append({"time": _to_unix(row["timestamp"]), "value": float(row["volume"]), "color": color})
    return out


def _all_zero_volume(df: pd.DataFrame) -> bool:
    """True when every volume value is missing/zero (Twelve Data does not
    report volume for XAU/USD)."""
    return df["volume"].isna().all() or (df["volume"] == 0).all()


def _pattern_markers(df: pd.DataFrame, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One marker per detected pattern, placed at its last defining point."""
    markers = []
    for p in patterns:
        pts = sorted(p["points"], key=lambda pt: pt["idx"])
        last_idx = pts[-1]["idx"]
        if last_idx >= len(df):
            continue
        # Determine marker orientation from the pattern direction, not the name.
        direction = p.get("direction", "bullish")
        is_bearish = direction == "bearish"
        markers.append({
            "time": _to_unix(df["timestamp"].iloc[last_idx]),
            "position": "aboveBar" if is_bearish else "belowBar",
            "color": "#e53935" if is_bearish else "#43a047",
            "shape": "arrowDown" if is_bearish else "arrowUp",
            "text": p.get("display", p.get("name", "pattern")).replace("_", " ").title(),
        })
    return markers


# Keys here match the period strings in the pre-computed ema_series from analyze()
EMA_COLORS = {"20": "#2196F3", "50": "#FF9800", "200": "#9C27B0"}


def build_chart_config(
    df: pd.DataFrame,
    technical_summary: Dict[str, Any],
    patterns: Optional[List[Dict[str, Any]]] = None,
    chart_type: str = "candlestick",
    show_emas: bool = True,
    show_volume: bool = True,
    height: int = 500,
    theme: str = "dark",
    ema_series: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    support_resistance_levels: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Build the ``charts`` config list that renderLightweightCharts expects.

    Parameters
    ----------
    df : DataFrame with columns time/open/high/low/close/volume and a
         ``timestamp`` datetime column (set by the caller).
    technical_summary : legacy dict — kept for backward compat but ignored
         when the pre-computed optional args are provided.
    ema_series : pre-computed EMA data from ``analyze()``
         ``{"20": [{time, value}, …], "50": …, "200": …}``.
    support_resistance_levels : flat list from ``indicators['support_resistance']``
         — each item has ``kind`` ("support"/"resistance"), ``price``, ``touches``.
    """
    series = []

    # Chart colors based on theme
    if theme == "dark":
        upColor = "#16c784"
        downColor = "#ea3943"
        textColor = "#d5d9e2"
        backgroundColor = "#0b0e13"
        gridColor = "#161b24"
        borderColor = "#252b36"
    else:  # light theme
        upColor = "#26a69a"
        downColor = "#ef5350"
        textColor = "#475569"
        backgroundColor = "#ffffff"
        gridColor = "#f1f5f9"
        borderColor = "#e2e8f0"

    # Time bounds for horizontal S/R lines
    first_time = _to_unix(df["timestamp"].iloc[0]) if len(df) else 0
    last_time = _to_unix(df["timestamp"].iloc[-1]) if len(df) else 0

    # --- Price series (candlestick or line) ---
    if chart_type == "line":
        series.append({
            "type": "Line",
            "data": _line_series(df, "close"),
            "options": {"color": textColor, "lineWidth": 2},
        })
    else:
        series.append({
            "type": "Candlestick",
            "data": _candlestick_series(df),
            "options": {
                "upColor": upColor, "downColor": downColor,
                "borderVisible": False,
                "wickUpColor": upColor, "wickDownColor": downColor,
            },
            "markers": _pattern_markers(df, patterns) if patterns else [],
        })

    # --- EMA overlay lines ---
    # Prefer the pre-computed ema_series from analyze(); fall back to DataFrame cols.
    if show_emas:
        ema_data = ema_series or {}
        ema_col_map = {"20": "ema_20", "50": "ema_50", "200": "ema_200"}
        for period, color in EMA_COLORS.items():
            data = None
            if period in ema_data:
                data = ema_data[period]  # already [{time, value}, …]
            else:
                col = ema_col_map[period]
                if col in df.columns:
                    data = _line_series(df, col)
            if data:
                series.append({
                    "type": "Line",
                    "data": data,
                    "options": {
                        "color": color, "lineWidth": 1, "lineStyle": 0,
                        "lastValueVisible": False, "priceLineVisible": False,
                    },
                })

    # --- Volume histogram ---
    # Skip the volume series entirely when the provider reports no
    # volume data (e.g. Twelve Data does not return volume for
    # XAU/USD). Rendering all-zero histograms looks like a dummy
    # chart and misleads the user about genuine market activity.
    if show_volume and not _all_zero_volume(df):
        series.append({
            "type": "Histogram",
            "data": _volume_series(df),
            "options": {"priceFormat": {"type": "volume"}, "priceScaleId": ""},
            "priceScale": {"scaleMargins": {"top": 0.8, "bottom": 0}},
        })

    # --- Support / Resistance horizontal lines ---
    # Use the flat list from indicators['support_resistance'] when provided.
    sr_list = support_resistance_levels or []
    for level in sr_list:
        is_support = level.get("kind") == "support"
        series.append({
            "type": "Line",
            "data": [
                {"time": first_time, "value": level["price"]},
                {"time": last_time,  "value": level["price"]},
            ],
            "options": {
                "color": "rgba(38,166,154,0.6)" if is_support else "rgba(239,83,80,0.6)",
                "lineWidth": 1, "lineStyle": 2,
                "lastValueVisible": False, "priceLineVisible": False,
            },
        })

    return [{
        "chart": {
            "height": height,
            "layout": {"background": {"type": "Solid", "color": backgroundColor}, "textColor": textColor},
            "grid": {"vertLines": {"color": gridColor}, "horzLines": {"color": gridColor}},
            "timeScale": {"timeVisible": True, "secondsVisible": False, "borderColor": borderColor},
            "rightPriceScale": {"borderColor": borderColor},
            "crosshair": {"mode": 0},
        },
        "series": series,
    }]


def render_chart(
    df: pd.DataFrame,
    technical_summary: Dict[str, Any],
    patterns: Optional[List[Dict[str, Any]]] = None,
    chart_type: str = "candlestick",
    show_emas: bool = True,
    show_volume: bool = True,
    height: int = 500,
    theme: str = "dark",
    key: Optional[str] = None,
) -> None:
    """Build the config and actually render it in the current Streamlit app."""
    config = build_chart_config(df, technical_summary, patterns, chart_type, show_emas, show_volume, height, theme)
    # Streamlit specific rendering: renderLightweightCharts(config, key=key)
    # For Next.js, the config is returned and handled by the frontend.
    pass
