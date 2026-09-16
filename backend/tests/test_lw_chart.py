"""Tests for the Lightweight Charts config builder (engine/lw_chart.py).

The builder only reshapes pre-computed data into the render config the
frontend turns into a lightweight-charts v5 chart. It computes nothing new,
so these tests feed a fixed fixture DataFrame and assert the output shape.
"""
import pandas as pd
import pytest

from app.engine.lw_chart import build_chart_config


def _df():
    return pd.DataFrame({
        'time': [1700000000 + i * 3600 for i in range(5)],
        'open': [100.0, 101.0, 102.0, 101.0, 103.0],
        'high': [102.0, 103.0, 104.0, 103.0, 105.0],
        'low':  [99.0,  100.0, 101.0, 100.0, 102.0],
        'close':[101.0, 102.0, 101.0, 103.0, 104.0],
        'volume':[1000.0, 1200.0, 900.0, 1100.0, 1300.0],
    })


def test_default_config_has_candlestick_ema_and_volume_series():
    df = _df()
    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
    ema_series = {
        '20': [{'time': int(t), 'value': v} for t, v in
               zip(df['time'], [100.5, 101.5, 101.8, 102.2, 103.0])],
    }
    config = build_chart_config(
        df, {}, patterns=[], chart_type='candlestick',
        show_emas=True, show_volume=True, height=500,
        ema_series=ema_series,
    )

    assert len(config) == 1
    chart, series = config[0]['chart'], config[0]['series']
    assert chart['height'] == 500

    types = [s['type'] for s in series]
    assert 'Candlestick' in types
    assert 'Line' in types       # the EMA overlay
    assert 'Histogram' in types  # volume
    assert len(series[0]['data']) == 5
    # Candles carry open/high/low/close, not value.
    candle = series[0]['data'][0]
    assert set(candle) == {'time', 'open', 'high', 'low', 'close'}


def test_dark_theme_uses_dark_background_and_light_text():
    df = _df()
    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
    config = build_chart_config(df, {}, theme='dark')
    layout = config[0]['chart']['layout']
    assert layout['background']['color'] == '#0b0e13'
    assert layout['textColor'] == '#d5d9e2'


def test_light_theme_uses_white_background_and_dark_text():
    df = _df()
    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
    config = build_chart_config(df, {}, theme='light')
    layout = config[0]['chart']['layout']
    assert layout['background']['color'] == '#ffffff'
    assert layout['textColor'] == '#475569'


def test_line_chart_type_overrides_candlestick():
    df = _df()
    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
    config = build_chart_config(df, {}, chart_type='line', show_emas=False, show_volume=False)
    series = config[0]['series']
    assert len(series) == 1
    assert series[0]['type'] == 'Line'
    assert 'value' in series[0]['data'][0]


def test_pattern_markers_pair_with_points():
    df = _df()
    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
    patterns = [{
        'name': 'fake_double_top', 'direction': 'bearish', 'display': 'Double Top',
        'points': [{'idx': 1}, {'idx': 3}],
    }]
    config = build_chart_config(df, {}, patterns=patterns, show_emas=False, show_volume=False)
    markers = config[0]['series'][0].get('markers', [])
    assert len(markers) == 1
    assert markers[0]['position'] == 'aboveBar'  # bearish markers sit above the bar
    assert markers[0]['shape'] == 'arrowDown'