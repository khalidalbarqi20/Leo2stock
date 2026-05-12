import yfinance as yf
import pandas as pd
import time
import random
from datetime import datetime
import requests

# نظام ذاكرة مؤقتة لتقليل الطلبات تماماً
_cache = {}
CACHE_EXPIRY = 600 

class StockDataFetcher:
    def __init__(self):
        # إنشاء جلسة متطورة لتجاوز حظر ياهو
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def get_stock_data(self, symbol, market='us', period='6mo'):
        # تحويل الرمز تلقائياً (رقمي -> سعودي)
        s_str = str(symbol).strip()
        yahoo_symbol = f"{s_str}.SR" if s_str.isdigit() else s_str.upper()
        if not s_str.isdigit() and not s_str.upper().endswith('.SR') and market == 'saudi':
             yahoo_symbol = f"{s_str.upper()}.SR"

        # فحص الكاش للاستجابة الفورية
        now = time.time()
        if yahoo_symbol in _cache:
            data, timestamp = _cache[yahoo_symbol]
            if now - timestamp < CACHE_EXPIRY:
                return data

        try:
            # استخدام الجلسة المخصصة مع yfinance لتجنب خطأ 429
            ticker = yf.Ticker(yahoo_symbol, session=self.session)
            
            # جلب البيانات التاريخية (الأساس للرسم البياني والمؤشرات)
            hist = ticker.history(period=period, interval="1d")
            
            if hist.empty:
                # محاولة أخيرة بمدة أقل لتجنب الحظر
                hist = ticker.history(period="1mo", interval="1d")
                if hist.empty: return None

            # جلب المعلومات الأساسية مع معالجة فشل التجاوب
            try:
                info = ticker.info
            except:
                info = {}

            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            
            data_res = {
                'symbol': yahoo_symbol,
                'name': info.get('longName') or info.get('shortName') or yahoo_symbol,
                'current': round(current, 2),
                'change': round(((current - prev) / prev) * 100, 2),
                'open': round(hist['Open'].iloc[-1], 2),
                'high': round(hist['High'].iloc[-1], 2),
                'low': round(hist['Low'].iloc[-1], 2),
                'previous_close': round(prev, 2),
                'volume': int(hist['Volume'].iloc[-1]),
                'avg_volume': int(hist['Volume'].mean()),
                'high_52w': round(hist['High'].max(), 2),
                'low_52w': round(hist['Low'].min(), 2),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE'),
                'prices': hist,
                'currency': info.get('currency', 'SAR' if '.SR' in yahoo_symbol else 'USD'),
                'timestamp': datetime.now().isoformat()
            }

            _cache[yahoo_symbol] = (data_res, now)
            return data_res

        except Exception as e:
            print(f"❌ Error fetching {yahoo_symbol}: {e}")
            return None

    def prepare_json(self, data):
        if not data: return None
        return {k: v for k, v in data.items() if k != 'prices'}

    def get_chart_series(self, prices_df):
        # حساب المؤشرات الفنية (RSI, MACD) بسرعة باستخدام Pandas
        closes = prices_df['Close']
        
        # SMA
        sma20 = closes.rolling(window=20).mean()
        sma50 = closes.rolling(window=50).mean()

        # RSI
        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))

        # MACD
        exp12 = closes.ewm(span=12, adjust=False).mean()
        exp26 = closes.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()

        return {
            'dates_list': [d.strftime('%m/%d') for d in prices_df.index],
            'prices_list': [round(c, 2) for c in closes],
            'sma20_list': [round(v, 2) if pd.notnull(v) else None for v in sma20],
            'sma50_list': [round(v, 2) if pd.notnull(v) else None for v in sma50],
            'rsi_list': [round(v, 2) if pd.notnull(v) else None for v in rsi],
            'macd_list': [round(v, 4) if pd.notnull(v) else None for v in macd],
            'signal_list': [round(v, 4) if pd.notnull(v) else None for v in signal],
            'histogram_list': [round(v, 4) if pd.notnull(v) else None for v in (macd - signal)],
        }
