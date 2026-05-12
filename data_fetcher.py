import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import requests

# نظام ذاكرة مؤقتة
_cache = {}
CACHE_EXPIRY = 900  # 15 دقيقة

# قاموس أسماء الأسهم السعودية (اختياري)
SAUDI_NAMES = {
    '2220.SR': 'الراجحي',
    '1180.SR': 'الأهلي السعودي',
    '2350.SR': 'كيان السعودية',
    '1320.SR': 'السعودية للكهرباء',
    '2010.SR': 'سابك',
    '2222.SR': 'أرامكو',
    '1120.SR': 'الراجحي',
    '1211.SR': 'معادن',
    '8280.SR': 'علم',
}

class StockDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://finance.yahoo.com/'
        })

    def get_stock_data(self, symbol, market='us', period='6mo'):
        # معالجة الرمز
        s_str = str(symbol).strip()
        if s_str.isdigit():
            yahoo_symbol = f"{s_str}.SR"
            market = 'saudi'
        elif s_str.upper().endswith('.SR'):
            yahoo_symbol = s_str.upper()
            market = 'saudi'
        else:
            yahoo_symbol = s_str.upper()
            market = 'us'

        # فحص الكاش
        now = time.time()
        if yahoo_symbol in _cache:
            data, timestamp = _cache[yahoo_symbol]
            if now - timestamp < CACHE_EXPIRY:
                print(f"✅ كاش: {yahoo_symbol}")
                return data

        # ⭐ تأخير قبل كل طلب لتجنب 429
        print(f"⏳ جلب بيانات: {yahoo_symbol}...")
        time.sleep(1.5)

        try:
            ticker = yf.Ticker(yahoo_symbol, session=self.session)
            
            # جلب التاريخ فقط (طلب واحد)
            hist = ticker.history(period=period, interval="1d")
            
            if hist.empty or len(hist) < 2:
                print(f"⚠️ لا توجد بيانات لـ {yahoo_symbol}")
                return None

            # ⭐ تجنب ticker.info تماماً!
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            
            # اسم الشركة من القاموس أو استخدم الرمز
            company_name = SAUDI_NAMES.get(yahoo_symbol, yahoo_symbol)
            
            stock_results = {
                'symbol': yahoo_symbol,
                'name': company_name,
                'current': round(current, 2),
                'change': round(((current - prev) / prev) * 100, 2),
                'open': round(hist['Open'].iloc[-1], 2),
                'high': round(hist['High'].iloc[-1], 2),
                'low': round(hist['Low'].iloc[-1], 2),
                'previous_close': round(prev, 2),
                'volume': int(hist['Volume'].iloc[-1]),
                'prices': hist,
                'currency': 'SAR' if market == 'saudi' else 'USD',
                'timestamp': datetime.now().isoformat()
            }

            _cache[yahoo_symbol] = (stock_results, now)
            print(f"✅ تم جلب {yahoo_symbol} بنجاح")
            return stock_results

        except Exception as e:
            print(f"❌ خطأ في جلب {yahoo_symbol}: {e}")
            return None

    def prepare_json(self, data):
        if not data: 
            return None
        return {k: v for k, v in data.items() if k != 'prices'}

    def get_chart_series(self, prices_df):
        closes = prices_df['Close']
        sma20 = closes.rolling(window=20).mean()
        
        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))

        exp12 = closes.ewm(span=12, adjust=False).mean()
        exp26 = closes.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()

        return {
            'dates_list': [d.strftime('%m/%d') for d in prices_df.index],
            'prices_list': [round(c, 2) for c in closes],
            'sma20_list': [round(v, 2) if pd.notnull(v) else None for v in sma20],
            'rsi_list': [round(v, 2) if pd.notnull(v) else None for v in rsi],
            'macd_list': [round(v, 4) if pd.notnull(v) else None for v in macd],
            'signal_list': [round(v, 4) if pd.notnull(v) else None for v in signal],
            'histogram_list': [round(v, 4) if pd.notnull(v) else None for v in (macd - signal)],
        }
