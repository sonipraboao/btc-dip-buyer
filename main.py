"""Dip-buying mean-reversion bot for cbBTC (bars-replay/v1).

Strategy: keep a 120-bar EMA of the CBBTC close. When the latest close
falls more than 0.4% below that EMA, buy with 95% of the cash: a dip of
that size is treated as a temporary dislocation, not a trend. Sell the
whole position when it is 1.4% above its average entry cost (the
take-profit) or 1.5% below it (the stop-loss). If no dip has triggered
by bar 720 and the price sits above the EMA (an uptrend that never
dipped), buy a half position so the bot still takes part. A full-size
round trip costs roughly 20-40 bps in fees, slippage and price impact,
so entries and exits are kept rare on purpose.

The bot is a pure function of the bars it has seen: no clock, no
randomness, no files, no network, so two runs on the same data give
byte-identical orders.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
EMA_N = 120          # bars in the trend average (2 hours of 1-minute bars)
DIP = 0.004          # buy when the close is this far below the EMA
TAKE = 0.014         # sell this far above the average entry cost
STOP = 0.015         # sell this far below the average entry cost
SIZE = 0.95          # share of cash spent on a dip entry
FALLBACK_BAR = 720   # halfway through a 24h window
FALLBACK_SIZE = 0.5  # share of cash spent on the trend fallback entry
MAX_SLIPPAGE_BPS = 300

_closes = []         # every CBBTC close seen, oldest first (price-scale ints)
_ema = None          # running EMA of the closes (float, price-scale units)


def _on_batch(state, batch):
    global _ema
    bar = None
    for b in batch.get("bars", []):
        if b.get("symbol") == SYMBOL:
            bar = b
    if bar is None:
        return None
    close = int(bar["c"])
    _closes.append(close)
    if _ema is None:
        _ema = float(close)
    else:
        k = 2.0 / (EMA_N + 1)
        _ema = _ema + k * (close - _ema)
    if state.warming_up:
        return None

    held = state.positions.get(SYMBOL)
    qty = held.qty if held else 0

    if qty > 0:
        # Average entry price in the same scaled units as the close:
        # cost is in quote units (1e6 per USDC) for qty units at the
        # symbol's qty scale (1e8 per BTC), so the USDC price of one
        # BTC is cost * 100 / qty; times the price scale (1e5) below.
        entry = held.cost * 10_000_000 / qty
        r = close / entry - 1.0
        if r >= TAKE or r <= -STOP:
            return [{"side": "sell", "symbol": SYMBOL, "qty": qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return None

    if len(_closes) <= EMA_N:
        return None
    dev = close / _ema - 1.0
    if dev <= -DIP:
        spend = int(state.cash * SIZE)
    elif len(_closes) >= FALLBACK_BAR and close > _ema:
        spend = int(state.cash * FALLBACK_SIZE)
    else:
        return None
    if spend < 1_000_000:  # below the 1 USDC minimum notional
        return None
    return [{"side": "buy", "symbol": SYMBOL, "notional_quote_units": spend,
             "max_slippage_bps": MAX_SLIPPAGE_BPS}]


makefun_bars.run(_on_batch)
