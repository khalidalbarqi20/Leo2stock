import yfinance as yf
import requests
from datetime import datetime

class StockDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_stock_data(self, symbol, market='us', period='6mo'):
        try:
            if market == 'saudi':
                yahoo_symbol = f"{symbol}.SR" if not symbol.endswith('.SR') else symbol
            else:
                yahoo_symbol = symbol.upper()

            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            hist = ticker.history(period=period, interval="1d")

            if hist.empty:
                return None

            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change = ((current - prev) / prev) * 100

            return {
                'symbol': yahoo_symbol,
                'name': info.get('longName', symbol),
                'market': market,
                'current': round(current, 2),
                'change': round(change, 2),
                'open': round(hist['Open'].iloc[-1], 2),
                'high': round(hist['High'].iloc[-1], 2),
                'low': round(hist['Low'].iloc[-1], 2),
                'previous_close': round(prev, 2),
                'volume': int(hist['Volume'].iloc[-1]),
                'avg_volume': int(hist['Volume'].mean()),
                'high_52w': round(hist['High'].max(), 2),
                'low_52w': round(hist['Low'].min(), 2),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', None),
                'eps': info.get('trailingEps', None),
                'revenue': info.get('totalRevenue', None),
                'prices': hist,
                'currency': info.get('currency', 'USD'),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', ''),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"خطأ في جلب {symbol}: {e}")
            return None

    def prepare_json(self, data):
        """Convert data dict to JSON-safe format (remove DataFrame)."""
        result = {k: v for k, v in data.items() if k != 'prices'}
        return result

    def get_chart_series(self, prices_df):
        """Returns chart-ready lists for price, SMA20, SMA50, RSI, MACD."""
        closes = list(prices_df['Close'])
        dates = [d.strftime('%m/%d') for d in prices_df.index]

        # SMA 20
        sma20 = []
        for i in range(len(closes)):
            if i >= 19:
                sma20.append(round(sum(closes[i-19:i+1]) / 20, 2))
            else:
                sma20.append(None)

        # SMA 50
        sma50 = []
        for i in range(len(closes)):
            if i >= 49:
                sma50.append(round(sum(closes[i-49:i+1]) / 50, 2))
            else:
                sma50.append(None)

        # RSI series (rolling)
        rsi_list = []
        period = 14
        for i in range(len(closes)):
            if i < period:
                rsi_list.append(None)
                continue
            subset = closes[max(0, i-period):i+1]
            gains, losses = [], []
            for j in range(1, len(subset)):
                diff = subset[j] - subset[j-1]
                (gains if diff > 0 else losses).append(abs(diff))
            avg_gain = sum(gains) / period if gains else 0.001
            avg_loss = sum(losses) / period if losses else 0.001
            rs = avg_gain / avg_loss
            rsi_list.append(round(100 - (100 / (1 + rs)), 2))

        # MACD series
        def ema_list(data, p):
            if len(data) < p:
                return [None] * len(data)
            mult = 2 / (p + 1)
            ema = [None] * (p - 1)
            ema.append(sum(data[:p]) / p)
            for price in data[p:]:
                ema.append((price - ema[-1]) * mult + ema[-1])
            return ema

        ema12 = ema_list(closes, 12)
        ema26 = ema_list(closes, 26)
        macd_line = [
            round(e12 - e26, 4) if (e12 is not None and e26 is not None) else None
            for e12, e26 in zip(ema12, ema26)
        ]
        valid_macd = [m for m in macd_line if m is not None]
        signal_raw = ema_list(valid_macd, 9)
        # Pad signal to same length
        pad = len(macd_line) - len(valid_macd)
        signal_line = [None] * pad + [None] * (len(valid_macd) - len(signal_raw)) + signal_raw

        histogram_list = [
            round(m - s, 4) if (m is not None and s is not None) else None
            for m, s in zip(macd_line, signal_line)
        ]

        return {
            'dates_list': dates,
            'prices_list': [round(c, 2) for c in closes],
            'sma20_list': sma20,
            'sma50_list': sma50,
            'rsi_list': rsi_list,
            'macd_list': macd_line,
            'signal_list': signal_line,
            'histogram_list': histogram_list,
        }
