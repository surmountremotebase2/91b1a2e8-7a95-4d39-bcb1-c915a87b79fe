#Type code hereimport pandas as pd
import numpy as np

# === USER CONFIGURATION ===
USE_MACD = True
USE_SUPERTREND = True

# MACD Parameters
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
MACD_SIGNAL_STRENGTH_PERIOD = 5  # Period for signal strength SMA
BUY_SIGNAL_STRENGTH_THRESHOLD = 0.4  # % of price
SELL_SIGNAL_STRENGTH_THRESHOLD = 0.3  # % of price

# Volatility filter
VOLATILITY_LOOKBACK = 14
MIN_VOLATILITY = 0.005
MAX_VOLATILITY = 0.05

# Supertrend Parameters
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0

# ATR-based stop loss/trailing stop
USE_ATR_STOP = True
ATR_PERIOD = 14
ATR_MULTIPLIER_SL = 2.0    # Stop loss = entry − ATR*multiplier
ATR_MULTIPLIER_TSL = 1.5   # Trailing stop = peak − ATR*multiplier

# Fallback fixed stops
STOP_LOSS_PCT = 0.03
TRAILING_STOP_PCT = 0.02

# Risk management
CAPITAL = 5500          # USD
MAX_LOSS_PER_DAY = 500  # USD
RISK_PER_TRADE = 200    # USD

print("\n=== INDICATOR STATUS ===")
print(f"MACD: {'ENABLED' if USE_MACD else 'DISABLED'}")
print(f"Supertrend: {'ENABLED' if USE_SUPERTREND else 'DISABLED'}")
print("=======================\n")


def compute_macd(df):
    df['ema_fast'] = df['Close'].ewm(span=MACD_FAST, adjust=False).mean()
    df['ema_slow'] = df['Close'].ewm(span=MACD_SLOW, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['macd_signal'] = df['macd'].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    df['macd_strength'] = df['macd_hist'].abs().rolling(MACD_SIGNAL_STRENGTH_PERIOD).mean()
    return df


def compute_volatility(df):
    df['volatility'] = df['Close'].pct_change().rolling(VOLATILITY_LOOKBACK).std()
    return df


def compute_supertrend(df):
    hl2 = (df['High'] + df['Low']) / 2
    tr = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift()).abs(),
        (df['Low'] - df['Close'].shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(SUPERTREND_PERIOD).mean()
    upperband = hl2 + SUPERTREND_MULTIPLIER * atr
    lowerband = hl2 - SUPERTREND_MULTIPLIER * atr

    direction = np.ones(len(df), dtype=bool)
    for i in range(1, len(df)):
        if df['Close'].iat[i] > upperband.iat[i-1]:
            direction[i] = True
        elif df['Close'].iat[i] < lowerband.iat[i-1]:
            direction[i] = False
        else:
            direction[i] = direction[i-1]
            upperband.iat[i] = min(upperband.iat[i], upperband.iat[i-1]) if direction[i] else upperband.iat[i]
            lowerband.iat[i] = max(lowerband.iat[i], lowerband.iat[i-1]) if not direction[i] else lowerband.iat[i]

    df['supertrend'] = direction
    return df


def compute_atr(df):
    tr = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift()).abs(),
        (df['Low'] - df['Close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(ATR_PERIOD).mean()
    return df


def backtest(df):
    cash = CAPITAL
    position = 0.0
    entry_price = 0.0
    peak_price = 0.0
    daily_loss = 0.0
    current_day = df.index[0].date()
    trades = []

    for ts, row in df.iterrows():
        # reset daily loss on new day
        if ts.date() != current_day:
            daily_loss = 0.0
            current_day = ts.date()

        # entry
        if position == 0 and USE_MACD and USE_SUPERTREND:
            cond_buy = (
                row['macd_hist'] > 0 and
                row['macd_strength'] > BUY_SIGNAL_STRENGTH_THRESHOLD * row['Close'] and
                MIN_VOLATILITY < row['volatility'] < MAX_VOLATILITY and
                row['supertrend']
            )
            if cond_buy:
                risk = min(RISK_PER_TRADE, MAX_LOSS_PER_DAY - daily_loss)
                shares = risk / row['Close']
                position = shares
                entry_price = row['Close']
                peak_price = entry_price
                cash -= shares * entry_price
                trades.append(('BUY', ts, shares, entry_price))

        # exit / stops
        elif position > 0:
            peak_price = max(peak_price, row['Close'])
            if USE_ATR_STOP:
                sl = entry_price - ATR_MULTIPLIER_SL * row['ATR']
                tsl = peak_price - ATR_MULTIPLIER_TSL * row['ATR']
            else:
                sl = entry_price * (1 - STOP_LOSS_PCT)
                tsl = peak_price * (1 - TRAILING_STOP_PCT)

            cond_sell = (
                row['macd_hist'] < 0 and
                row['macd_strength'] > SELL_SIGNAL_STRENGTH_THRESHOLD * row['Close']
            )
            if cond_sell or row['Close'] < sl or row['Close'] < tsl:
                cash += position * row['Close']
                pnl = (row['Close'] - entry_price) * position
                daily_loss += max(0, -pnl)
                trades.append(('SELL', ts, position, row['Close'], pnl))
                position = 0.0

    # close any open position at end
    if position > 0:
        final_price = df['Close'].iloc[-1]
        cash += position * final_price
        pnl = (final_price - entry_price) * position
        trades.append(('SELL', df.index[-1], position, final_price, pnl))

    total_pnl = cash - CAPITAL
    return trades, total_pnl


def main():
    # === LOAD YOUR DATA HERE ===
    # df should be a DataFrame with a DateTimeIndex and columns: Open, High, Low, Close.
    # For example:
    # df = pd.read_csv('your_1min_data.csv', parse_dates=['Datetime'], index_col='Datetime')

    # Placeholder:
    df = pd.DataFrame()  # ← replace with your data load

    # Compute indicators
    if USE_MACD:
        df = compute_macd(df)
        df = compute_volatility(df)
    if USE_SUPERTREND:
        df = compute_supertrend(df)
    if USE_ATR_STOP:
        df = compute_atr(df)

    # Run backtest
    trades, pnl = backtest(df)

    print(f"Total P&L: ${pnl:.2f}")
    print("Trade log:")
    for t in trades:
        print(t)


if __name__ == '__main__':
    main()