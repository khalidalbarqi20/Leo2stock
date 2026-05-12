import yfinance as yf
import pandas as pd
import time
import random
from datetime import datetime

# نظام تخزين مؤقت لمنع الحظر (يحتفظ بالبيانات لمدة 5 دقائق)
_cache = {}
CACHE_EXPIRY = 300 

class StockDataFetcher:
    def __init__(self):
        # تم تحديث الرأس لمحاكاة متصفح حقيقي بشكل أفضل
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def get_stock_data(self, symbol, market='us', period='6mo'):
        # 1. التحقق من التخزين المؤقت أولاً لتجنب طلب البيانات المتكرر
        cache_key = f"{symbol}_{market}_{period}"
        now = time.time()
        if cache_key in _cache:
            cached_data, timestamp = _cache[cache_key]
            if now - timestamp < CACHE_EXPIRY:
                print(f"✅ جلب من التخزين المؤقت: {symbol}")
                return cached_data

        # 2. إضافة تأخير عشوائي ذكي لمنع نظام الحماية في ياهو من رصدك
        time.sleep(random.uniform(1.5, 3.5))

        try:
            if market == 'saudi':
                yahoo_symbol = f"{symbol}.SR" if not str(symbol).endswith('.SR') else symbol
            else:
                yahoo_symbol = str(symbol).upper()

            ticker = yf.Ticker(yahoo_symbol)
            
            # جلب البيانات التاريخية
            hist = ticker.history(period=period, interval="1d")
            if hist.empty:
                print(f"⚠️ لا توجد بيانات للرمز: {yahoo_symbol}")
                return None

            # جلب معلومات السهم (Info) مع معالجة احتمالية فشلها
            try:
                info = ticker.info
            except:
                info = {}

            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change = ((current - prev) / prev) * 100

            data = {
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

            # 3. حفظ النتيجة في التخزين المؤقت
            _cache[cache_key] = (data, now)
            return data

        except Exception as e:
            print(f"❌ خطأ في جلب {symbol}: {e}")
            # إذا ظهر خطأ الحظر الشهير 429، انتظر دقيقتين
            if "429" in str(e):
                print("⚠️ تم اكتشاف حظر مؤقت.. جاري الانتظار 120 ثانية...")
                time.sleep(120)
            return None

    def prepare_json(self, data):
        """تحويل البيانات لصيغة JSON آمنة."""
        if not data: return None
        return {k: v for k, v in data.items() if k != 'prices'}

    def get_chart_series(self, prices_df):
        """حساب المؤشرات الفنية (SMA, RSI, MACD) للرسوم البيانية."""
        closes = list(prices_df['Close'])
        dates = [d.strftime('%m/%d') for d in prices_df.index]

        # حساب المتوسطات المتحركة SMA
        sma20 = [round(prices_df['Close'].rolling(window=20).mean().iloc[i], 2) if i >= 19 else None for i in range(len(closes))]
        sma50 = [round(prices_df['Close'].rolling(window=50).mean().iloc[i], 2) if i >= 49 else None for i in range(len(closes))]

        # حساب مؤشر القوة النسبية RSI (بشكل مبسط واحترافي)
        delta = prices_df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_list = [round(100 - (100 / (1 + r)), 2) if not pd.isna(r) else None for r in rs]

        # حساب مؤشر MACD
        exp1 = prices_df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = prices_df['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal

        return {
            'dates_list': dates,
            'prices_list': [round(c, 2) for c in closes],
            'sma20_list': sma20,
            'sma50_list': sma50,
            'rsi_list': rsi_list,
            'macd_list': [round(m, 4) if not pd.isna(m) else None for m in macd],
            'signal_list': [round(s, 4) if not pd.isna(s) else None for s in signal],
            'histogram_list': [round(h, 4) if not pd.isna(h) else None for h in hist],
        }
