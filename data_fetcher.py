import yfinance as yf
import requests
import time
import random
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
        # حاول 3 مرات مع تأخير
        for attempt in range(3):
            try:
                if attempt > 0:
                    wait = random.uniform(3, 7)
                    print(f"انتظار {wait:.1f} ثانية قبل المحاولة {attempt + 1}")
                    time.sleep(wait)

                if market == 'saudi':
                    yahoo_symbol = f"{symbol}.SR" if not symbol.endswith('.SR') else symbol
                else:
                    yahoo_symbol = symbol.upper()

                print(f"جلب بيانات: {yahoo_symbol} (محاولة {attempt + 1})")

                ticker = yf.Ticker(yahoo_symbol)
                hist = ticker.history(period="6mo", interval="1d", auto_adjust=True)

                if hist.empty:
                    print(f"لا توجد بيانات للرمز: {yahoo_symbol}")
                    if attempt < 2:
                        continue
                    return None

                # جلب المعلومات بشكل آمن
                name = yahoo_symbol
                market_cap = 0
                pe_ratio = None
                currency = 'SAR' if market == 'saudi' else 'USD'
                sector = 'Unknown'

                try:
                    info = ticker.fast_info
                    if hasattr(info, 'market_cap'):
                        market_cap = info.market_cap or 0
                    if hasattr(info, 'currency'):
                        currency = info.currency or currency
                except:
                    pass

                try:
                    slow_info = ticker.info
                    name = slow_info.get('longName', yahoo_symbol)
                    pe_ratio = slow_info.get('trailingPE', None)
                    sector = slow_info.get('sector', 'Unknown')
                except:
                    pass

                current = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                change = ((current - prev) / prev) * 100

                print(f"نجح جلب: {yahoo_symbol} السعر: {current}")

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
                error_msg = str(e)
                print(f"خطأ في جلب {symbol} (محاولة {attempt + 1}): {error_msg}")

                if 'Too Many Requests' in error_msg or 'rate limit' in error_msg.lower():
                    wait = (attempt + 1) * 10
                    print(f"Rate limit - انتظار {wait} ثانية")
                    time.sleep(wait)
                elif attempt < 2:
                    time.sleep(3)
                else:
                    return None

        return None
