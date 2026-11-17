# BTC Dip Buyer — a cbBTC trading bot for make.fun's 24-hour BTC race

A Python 3.13 bot for the `agent-fun/bars-replay/v1` protocol. It trades
one asset, CBBTC (Coinbase Wrapped BTC on Solana, against USDC), on
1-minute bars with $1,000 of paper money.

## Strategy

Mean reversion against a 2-hour trend average:

- Keep a 120-bar EMA of the close.
- **Buy** with 95% of the cash when the close falls more than 0.4% below
  the EMA — a dip that size is treated as a temporary dislocation.
- **Sell** everything 1.4% above the average entry cost (take-profit) or
  1.5% below it (stop-loss).
- If no dip has triggered by bar 720 and the price is above the EMA,
  buy a half position so an uptrend that never dips is not missed.

A full-size round trip costs roughly 20–40 bps in fees, slippage and
price impact, so the bot trades rarely on purpose: on the published
24-hour dev window it makes a handful of trades and a small drawdown.

The bot is deterministic: a pure function of the bars it has seen, with
no clock, no randomness, no files and no network, so two runs on the
same data produce byte-identical orders.

## Layout

- `main.py` — the bot (the entrypoint the grader runs)
- `vendor/makefun_bars.py` — the kit's Python SDK shim, copied unchanged
- `LICENSE` — MIT

## Running it

The grader runs `python3 -P -s main.py` and speaks newline-delimited
JSON on stdin/stdout: one `hello`, one `batch` per minute, then `done`.
The bot answers every batch with exactly one reply.
