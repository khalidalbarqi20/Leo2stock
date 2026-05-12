import yfinance as yf
import requests
from datetime import datetime

class StockDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def get_stock_data(self, symbol, market='us'):
        try:
            if market == 'saudi':
                yahoo_symbol = f"{symbol}.SR" if not symbol.endswith('.SR') else symbol
            else:
                yahoo_symbol = symbol.upper()

            ticker = yf.Ticker(yahoo_symbol, session=self.session)
            
            hist = ticker.history(period="6mo", interval="1d", auto_adjust=True)

            if hist.empty:
                # جرب بدون session
                ticker2 = yf.Ticker(yahoo_symbol)
                hist = ticker2.history(period="3mo", interval="1d")
                if hist.empty:
                    return None

            try:
                info = ticker.fast_info
                name = yahoo_symbol
                market_cap = 0
                pe_ratio = None
                currency = 'USD'
                sector = 'Unknown'
            except:
                name = yahoo_symbol
                market_cap = 0
                pe_ratio = None
                currency = 'USD'
                sector = 'Unknown'

            current = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            change = ((current - prev) / prev) * 100

            return {
                'symbol': yahoo_symbol,
                'name': name,
                'market': market,
                'current': round(current, 2),
                'change': round(change, 2),
                'open': round(float(hist['Open'].iloc[-1]), 2),
                'high': round(float(hist['High'].iloc[-1]), 2),
                'low': round(float(hist['Low'].iloc[-1]), 2),
                'previous_close': round(prev, 2),
                'volume': int(hist['Volume'].iloc[-1]),
                'avg_volume': int(hist['Volume'].mean()),
                'high_52w': round(float(hist['High'].max()), 2),
                'low_52w': round(float(hist['Low'].min()), 2),
                'market_cap': market_cap,
                'pe_ratio': pe_ratio,
                'prices': hist,
                'currency': currency,
                'sector': sector,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"خطأ في جلب {symbol}: {e}")
            return None
