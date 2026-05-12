import yfinance as yf
import requests
from datetime import datetime

class StockDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_stock_data(self, symbol, market='us'):
        try:
            if market == 'saudi':
                yahoo_symbol = f"{symbol}.SR" if not symbol.endswith('.SR') else symbol
            else:
                yahoo_symbol = symbol.upper()

            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            hist = ticker.history(period="6mo", interval="1d")

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
                'prices': hist,
                'currency': info.get('currency', 'USD'),
                'sector': info.get('sector', 'Unknown'),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"خطأ في جلب {symbol}: {e}")
            return None
