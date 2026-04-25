"""
BTC Short-at-Resistance Backtest v4
- Vectorized NumPy price loop (20-50x faster than iterrows)
- Rolling local range TP: TP1 = range midpoint, TP2 = range bottom
- Split exit: 50% @ TP1, 50% runner @ TP2 (trail to BE after TP1 hit)
- Stop: 0.35% above resistance
- 5x leverage, 1% account risk sizing
- Max 1 trade per day
- Filters: resistance must have >= 2 touches; only enter in downtrend or range
"""

import glob, os, sys, time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── config ────────────────────────────────────────────────────────────────────
DATA_GLOB     = "data/BTCUSDT-1m-*.csv"   # path to your unzipped 1m CSV files
INITIAL_CAP   = 10_000.0
LEVERAGE      = 5
RISK_PCT      = 0.01        # risk 1% of account per trade
FEE_RATE      = 0.0005      # 0.05% taker fee each way
STOP_OFFSET   = 0.0035      # stop 0.35% above resistance
ENTRY_BAND    = 0.004       # enter when price within 0.4% below resistance

# Resistance detection (run on 1H candles)
PIVOT_WINDOW  = 10          # candles each side for pivot high
CLUSTER_PCT   = 0.003       # merge levels within 0.3%
MIN_TOUCHES   = 2

# Local range window for TP (4H candles)
RANGE_LOOKBACK = 30         # 30 × 4H = 5 days rolling range

# Trend filter on 4H: price below EMA(50) → allowed; above → skip
TREND_EMA     = 50

# ── load & concat data ────────────────────────────────────────────────────────
def load_data(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern))
    if not files:
        sys.exit(f"No files matched: {pattern}\nPut unzipped CSVs in {os.path.dirname(pattern) or '.'}/")
    print(f"Loading {len(files)} file(s)…")
    chunks = []
    for f in files:
        df = pd.read_csv(f, header=None,
                         names=["ts","open","high","low","close","vol",
                                "close_time","qvol","ntrades","tbvol","tbqvol","ignore"])
        chunks.append(df[["ts","open","high","low","close","vol"]])
    data = pd.concat(chunks, ignore_index=True)
    # Binance timestamps are in ms
    data["ts"] = pd.to_datetime(data["ts"], unit="ms", utc=True)
    data = data.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    data[["open","high","low","close","vol"]] = data[["open","high","low","close","vol"]].astype(np.float64)
    print(f"  {len(data):,} rows  {data['ts'].iloc[0]}  →  {data['ts'].iloc[-1]}")
    return data

# ── resample helpers ──────────────────────────────────────────────────────────
def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    df2 = df.set_index("ts").resample(rule).agg(
        open=("open","first"), high=("high","max"),
        low=("low","min"),   close=("close","last"), vol=("vol","sum")
    ).dropna().reset_index()
    return df2

# ── resistance detection ──────────────────────────────────────────────────────
def find_resistance_levels(h1: pd.DataFrame) -> np.ndarray:
    highs = h1["high"].to_numpy()
    n = len(highs)
    w = PIVOT_WINDOW
    # vectorized pivot high: high[i] == max in [i-w, i+w]
    pivot_idx = []
    for i in range(w, n - w):
        window = highs[i - w: i + w + 1]
        if highs[i] == window.max():
            pivot_idx.append(i)
    if not pivot_idx:
        return np.array([])
    pivot_prices = highs[pivot_idx]
    # cluster nearby pivots
    sorted_p = np.sort(pivot_prices)
    clusters = []
    group = [sorted_p[0]]
    for p in sorted_p[1:]:
        if p / group[0] - 1 <= CLUSTER_PCT:
            group.append(p)
        else:
            clusters.append(group)
            group = [p]
    clusters.append(group)
    levels = []
    for g in clusters:
        if len(g) >= MIN_TOUCHES:
            levels.append(np.mean(g))
    return np.array(levels)

# ── local range (rolling 4H window) ──────────────────────────────────────────
def build_range_arrays(h4: pd.DataFrame, m1_ts: np.ndarray) -> tuple:
    """
    For each 1m bar return the rolling range high/low from the last
    RANGE_LOOKBACK 4H candles that closed before that bar.
    Returns (range_high, range_low) as float64 arrays aligned to m1_ts.
    """
    h4_ts  = h4["ts"].to_numpy(dtype="datetime64[ns]")
    h4_hi  = h4["high"].to_numpy()
    h4_lo  = h4["low"].to_numpy()
    n1     = len(m1_ts)
    rng_hi = np.full(n1, np.nan)
    rng_lo = np.full(n1, np.nan)

    j = 0  # pointer into h4
    for i in range(n1):
        t = m1_ts[i]
        # advance j so h4[j] is the last closed 4H bar before t
        while j < len(h4_ts) and h4_ts[j] <= t:
            j += 1
        end = j        # h4[:end] are all bars that closed ≤ t
        start = max(0, end - RANGE_LOOKBACK)
        if end - start >= 5:   # need at least 5 bars
            rng_hi[i] = h4_hi[start:end].max()
            rng_lo[i] = h4_lo[start:end].min()
    return rng_hi, rng_lo

# ── 4H trend filter ───────────────────────────────────────────────────────────
def build_trend_array(h4: pd.DataFrame, m1_ts: np.ndarray) -> np.ndarray:
    """
    Returns bool array: True = downtrend/range (allowed to short).
    Condition: 4H close < EMA(TREND_EMA) on the last closed 4H bar.
    """
    ema = h4["close"].ewm(span=TREND_EMA, adjust=False).mean().to_numpy()
    h4_ts    = h4["ts"].to_numpy(dtype="datetime64[ns]")
    h4_close = h4["close"].to_numpy()
    n1 = len(m1_ts)
    trend_ok = np.zeros(n1, dtype=bool)
    j = 0
    for i in range(n1):
        t = m1_ts[i]
        while j < len(h4_ts) and h4_ts[j] <= t:
            j += 1
        last = j - 1
        if last >= TREND_EMA:
            trend_ok[i] = h4_close[last] < ema[last]
    return trend_ok

# ── main backtest loop (NumPy arrays, no iterrows) ────────────────────────────
def run_backtest(m1: pd.DataFrame, levels: np.ndarray,
                 rng_hi: np.ndarray, rng_lo: np.ndarray,
                 trend_ok: np.ndarray) -> pd.DataFrame:
    if len(levels) == 0:
        print("No resistance levels found — check data or parameters.")
        return pd.DataFrame()

    close = m1["close"].to_numpy()
    high  = m1["high"].to_numpy()
    low   = m1["low"].to_numpy()
    ts    = m1["ts"].to_numpy(dtype="datetime64[ns]")
    n     = len(close)

    capital = INITIAL_CAP
    trades  = []
    last_trade_day = None
    in_trade = False
    entry_price = stop = tp1 = tp2 = 0.0
    tp1_hit = be_stop = False
    half_pnl = 0.0
    entry_idx = 0
    entry_ts  = None

    equity_curve = np.full(n, np.nan)
    equity_curve[0] = capital

    for i in range(1, n):
        day = ts[i].astype("datetime64[D]")
        equity_curve[i] = capital

        if in_trade:
            # check stop first (uses bar high for long stops / low for short stops)
            bar_high = high[i]
            bar_low  = low[i]

            if tp1_hit:
                # trailing stop is BE level
                current_stop = be_stop
            else:
                current_stop = stop

            # stopped out
            if bar_high >= current_stop:
                if tp1_hit:
                    # runner stopped at BE → net = half_pnl (first half profit)
                    pnl = half_pnl
                    exit_reason = "runner_BE"
                else:
                    # full stop both halves
                    notional = (capital * RISK_PCT / (stop / entry_price - 1)) * LEVERAGE
                    gross_loss = -notional * (stop / entry_price - 1)
                    fees = notional * FEE_RATE * 2
                    pnl = gross_loss - fees
                    exit_reason = "full_stop"
                capital = max(capital + pnl, 0.01)
                trades.append(dict(entry_ts=entry_ts, exit_ts=ts[i],
                                   entry=entry_price, stop=stop, tp1=tp1, tp2=tp2,
                                   exit_price=current_stop, pnl=pnl,
                                   exit_reason=exit_reason, capital=capital))
                in_trade = False
                continue

            # TP1 hit
            if not tp1_hit and bar_low <= tp1:
                notional = (capital * RISK_PCT / (stop / entry_price - 1)) * LEVERAGE
                half_notional = notional / 2
                gross_profit = half_notional * (entry_price / tp1 - 1)
                fees_half = half_notional * FEE_RATE * 2
                half_pnl = gross_profit - fees_half
                tp1_hit = True
                be_stop = entry_price * 1.0001  # trail to just above entry

            # TP2 hit (runner)
            if tp1_hit and bar_low <= tp2:
                notional = (capital * RISK_PCT / (stop / entry_price - 1)) * LEVERAGE
                half_notional = notional / 2
                gross_profit2 = half_notional * (entry_price / tp2 - 1)
                fees_half2 = half_notional * FEE_RATE * 2
                runner_pnl = gross_profit2 - fees_half2
                total_pnl = half_pnl + runner_pnl
                capital = max(capital + total_pnl, 0.01)
                trades.append(dict(entry_ts=entry_ts, exit_ts=ts[i],
                                   entry=entry_price, stop=stop, tp1=tp1, tp2=tp2,
                                   exit_price=tp2, pnl=total_pnl,
                                   exit_reason="full_tp", capital=capital))
                in_trade = False
                continue

        else:
            # look for entry signal
            if last_trade_day == day:
                continue  # 1 trade per day
            if np.isnan(rng_hi[i]) or np.isnan(rng_lo[i]):
                continue
            if not trend_ok[i]:
                continue

            price = close[i]
            rh = rng_hi[i]
            rl = rng_lo[i]
            range_width = rh - rl
            if range_width / price < 0.005:   # ignore micro ranges < 0.5%
                continue

            mid = (rh + rl) / 2.0   # TP1 = range midpoint
            bot = rl                  # TP2 = range bottom

            # check against all resistance levels
            for lvl in levels:
                if lvl < price * 0.98 or lvl > price * 1.02:
                    continue  # level must be within 2% of current price
                near = lvl * (1 - ENTRY_BAND)
                if price <= lvl and price >= near:
                    # valid entry
                    ep  = price
                    sl  = lvl * (1 + STOP_OFFSET)
                    tp1_target = mid
                    tp2_target = bot
                    # TP1 must be at least 0.5R below entry
                    r = sl / ep - 1
                    if (ep - tp1_target) / ep < r * 0.5:
                        continue  # range too tight for sensible TP1
                    if tp2_target >= tp1_target:
                        continue  # range bottom must be below midpoint

                    in_trade   = True
                    entry_price = ep
                    stop        = sl
                    tp1         = tp1_target
                    tp2         = tp2_target
                    tp1_hit     = False
                    half_pnl    = 0.0
                    entry_idx   = i
                    entry_ts    = ts[i]
                    last_trade_day = day
                    break

    # close any open trade at end of data
    if in_trade:
        pnl = -capital * RISK_PCT  # assume stopped out
        capital += pnl
        trades.append(dict(entry_ts=entry_ts, exit_ts=ts[-1],
                           entry=entry_price, stop=stop, tp1=tp1, tp2=tp2,
                           exit_price=close[-1], pnl=pnl,
                           exit_reason="eod_close", capital=capital))

    return pd.DataFrame(trades), equity_curve

# ── plot ──────────────────────────────────────────────────────────────────────
def plot_results(m1: pd.DataFrame, trades_df: pd.DataFrame,
                 equity: np.ndarray, levels: np.ndarray):
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    fig.suptitle("BTC Short-at-Resistance v4  |  Rolling Range TP  |  Real 1m Data", fontsize=13)

    # price + resistance
    ax = axes[0]
    ts = m1["ts"]
    ax.plot(ts, m1["close"], color="#1a1a2e", lw=0.4, label="BTC Close")
    for lvl in levels:
        ax.axhline(lvl, color="red", lw=0.6, alpha=0.6, ls="--")
    if len(trades_df):
        wins  = trades_df[trades_df["pnl"] > 0]
        loss  = trades_df[trades_df["pnl"] <= 0]
        ax.scatter(wins["entry_ts"], wins["entry"], marker="v", color="green", s=40, zorder=5, label="Win entry")
        ax.scatter(loss["entry_ts"], loss["entry"], marker="v", color="red",   s=40, zorder=5, label="Loss entry")
    ax.set_ylabel("BTC Price (USDT)")
    ax.legend(fontsize=8)

    # equity curve
    ax2 = axes[1]
    ax2.plot(ts, equity, color="darkorange", lw=1)
    ax2.set_ylabel("Account ($)")
    ax2.set_title("Equity Curve")

    # per-trade PnL
    ax3 = axes[2]
    if len(trades_df):
        colors = ["green" if p > 0 else "red" for p in trades_df["pnl"]]
        ax3.bar(range(len(trades_df)), trades_df["pnl"], color=colors, width=0.8)
        ax3.axhline(0, color="black", lw=0.8)
    ax3.set_xlabel("Trade #")
    ax3.set_ylabel("PnL ($)")
    ax3.set_title("Per-Trade PnL")

    plt.tight_layout()
    out = "results/backtest_v4.png"
    os.makedirs("results", exist_ok=True)
    plt.savefig(out, dpi=150)
    print(f"Chart saved → {out}")

# ── entry point ───────────────────────────────────────────────────────────────
def main():
    t0 = time.time()

    m1 = load_data(DATA_GLOB)

    print("Resampling to 1H and 4H…")
    h1 = resample(m1, "1h")
    h4 = resample(m1, "4h")

    print(f"Detecting resistance on {len(h1)} 1H bars…")
    levels = find_resistance_levels(h1)
    print(f"  Found {len(levels)} resistance levels: {np.round(levels, 0)}")

    print(f"Building rolling range arrays from {len(h4)} 4H bars…")
    m1_ts  = m1["ts"].to_numpy(dtype="datetime64[ns]")
    rng_hi, rng_lo = build_range_arrays(h4, m1_ts)
    trend_ok       = build_trend_array(h4, m1_ts)

    print(f"  Trend filter passes {trend_ok.sum():,} / {len(trend_ok):,} bars ({100*trend_ok.mean():.1f}%)")

    print("Running backtest…")
    trades_df, equity = run_backtest(m1, levels, rng_hi, rng_lo, trend_ok)

    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.1f}s")

    if len(trades_df) == 0:
        print("No trades generated — try relaxing ENTRY_BAND or MIN_TOUCHES.")
        return

    final_cap = trades_df["capital"].iloc[-1]
    ret       = (final_cap / INITIAL_CAP - 1) * 100
    wins      = trades_df["pnl"] > 0
    win_rate  = wins.mean() * 100
    avg_win   = trades_df.loc[wins, "pnl"].mean() if wins.any() else 0
    avg_loss  = trades_df.loc[~wins, "pnl"].mean() if (~wins).any() else 0

    by_exit = trades_df.groupby("exit_reason")["pnl"].agg(["count","mean","sum"])

    # max drawdown
    running_max = np.maximum.accumulate(equity[~np.isnan(equity)])
    dd = (equity[~np.isnan(equity)] - running_max) / running_max
    max_dd = dd.min() * 100

    print(f"""
══════════════════════════════════════════════
 BTC Short-at-Resistance  v4  Results
══════════════════════════════════════════════
 Period        : {m1['ts'].iloc[0].date()} → {m1['ts'].iloc[-1].date()}
 Start capital : ${INITIAL_CAP:,.0f}
 End capital   : ${final_cap:,.0f}
 Return        : {ret:+.1f}%
 Total trades  : {len(trades_df)}
 Win rate      : {win_rate:.1f}%
 Avg win       : ${avg_win:,.0f}
 Avg loss      : ${avg_loss:,.0f}
 Max drawdown  : {max_dd:.1f}%
──────────────────────────────────────────────
 Exit breakdown:
{by_exit.to_string()}
══════════════════════════════════════════════""")

    os.makedirs("results", exist_ok=True)
    trades_df.to_csv("results/trades_v4.csv", index=False)
    print("Trades saved → results/trades_v4.csv")

    plot_results(m1, trades_df, equity, levels)

if __name__ == "__main__":
    main()
