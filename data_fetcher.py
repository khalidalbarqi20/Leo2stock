import yfinance as yf
import pandas as pd
import time
from datetime import datetime

# ============================================================
# ذاكرة مؤقتة مشتركة (مستوى الموديول) — 15 دقيقة
# ============================================================
_cache = {}
CACHE_EXPIRY = 900  # ثانية

# ============================================================
# قاموس أسماء الأسهم السعودية — يُستخدم بدلاً من ticker.info
# لتجنب طلبات إضافية تسبب 429
# ============================================================
SAUDI_NAMES = {
    '2222.SR': 'أرامكو السعودية',
    '1180.SR': 'مصرف الراجحي',
    '1120.SR': 'مصرف الراجحي',
    '8280.SR': 'شركة علم',
    '2350.SR': 'كيان السعودية',
    '2010.SR': 'سابك',
    '1211.SR': 'معادن',
    '2380.SR': 'بترو رابغ',
    '4030.SR': 'المراعي',
    '7010.SR': 'STC',
    '1010.SR': 'الراجحي',
    '2050.SR': 'سافكو',
}

US_NAMES = {
    'AAPL': 'Apple Inc.',
    'TSLA': 'Tesla Inc.',
    'NVDA': 'NVIDIA Corp.',
    'MSFT': 'Microsoft Corp.',
    'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com',
    'META': 'Meta Platforms',
}


class StockDataFetcher:
    def __init__(self):
        # ⭐ استخدام curl_cffi لتجاوز حجب Yahoo Finance
        try:
            from curl_cffi import requests as curl_requests
            self._session = curl_requests.Session(impersonate="chrome")
            self._use_curl = True
            print("✅ curl_cffi session نشطة")
        except ImportError:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/124.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            })
            self._use_curl = False
            print("⚠️ curl_cffi غير متوفر، استخدام requests العادي")

    # ----------------------------------------------------------
    # الدالة الرئيسية لجلب البيانات
    # ----------------------------------------------------------
    def get_stock_data(self, symbol: str, market: str = 'us', period: str = '6mo'):
        symbol = str(symbol).strip()

        # تحديد الرمز الصحيح لـ Yahoo Finance
        if symbol.isdigit():
            yahoo_symbol = f"{symbol}.SR"
            market = 'saudi'
        elif symbol.upper().endswith('.SR'):
            yahoo_symbol = symbol.upper()
            market = 'saudi'
        else:
            yahoo_symbol = symbol.upper()
            market = 'us'

        # ── فحص الكاش ────────────────────────────────────────
        cache_key = f"{yahoo_symbol}_{period}"
        now = time.time()
        if cache_key in _cache:
            data, ts = _cache[cache_key]
            if now - ts < CACHE_EXPIRY:
                print(f"✅ كاش: {yahoo_symbol}")
                return data

        # ── جلب البيانات ──────────────────────────────────────
        print(f"⏳ جلب: {yahoo_symbol} ...")

        try:
            ticker = yf.Ticker(yahoo_symbol, session=self._session)
            hist = ticker.history(period=period, interval="1d", auto_adjust=True)

            if hist is None or hist.empty or len(hist) < 5:
                print(f"⚠️ لا بيانات لـ {yahoo_symbol} (period={period})")
                return None

            current = float(hist['Close'].iloc[-1])
            prev    = float(hist['Close'].iloc[-2])
            change  = round(((current - prev) / prev) * 100, 2)

            # اسم الشركة من القاموس أولاً (يتجنب ticker.info)
            if market == 'saudi':
                name = SAUDI_NAMES.get(yahoo_symbol, yahoo_symbol.replace('.SR', ''))
                currency = 'SAR'
                sector = 'سعودي'
            else:
                name = US_NAMES.get(yahoo_symbol, yahoo_symbol)
                currency = 'USD'
                sector = 'أمريكي'

            result = {
                'symbol':         yahoo_symbol,
                'name':           name,
                'market':         market,
                'currency':       currency,
                'sector':         sector,
                'current':        round(current, 2),
                'change':         change,
                'open':           round(float(hist['Open'].iloc[-1]), 2),
                'high':           round(float(hist['High'].iloc[-1]), 2),
                'low':            round(float(hist['Low'].iloc[-1]), 2),
                'previous_close': round(prev, 2),
                'volume':         int(hist['Volume'].iloc[-1]),
                'high_52w':       round(float(hist['High'].max()), 2),
                'low_52w':        round(float(hist['Low'].min()), 2),
                'market_cap':     0,
                'pe_ratio':       None,
                'prices':         hist,
                'timestamp':      datetime.now().isoformat(),
            }

            _cache[cache_key] = (result, now)
            print(f"✅ نجح: {yahoo_symbol}  السعر={current}")
            return result

        except Exception as e:
            print(f"❌ خطأ في {yahoo_symbol}: {e}")
            return None

    # ----------------------------------------------------------
    # تحويل البيانات لـ JSON (بدون DataFrame)
    # ----------------------------------------------------------
    def prepare_json(self, data: dict) -> dict:
        if not data:
            return {}
        return {k: v for k, v in data.items() if k != 'prices'}

    # ----------------------------------------------------------
    # بيانات الرسوم البيانية
    # ----------------------------------------------------------
    def get_chart_series(self, prices_df: pd.DataFrame) -> dict:
        closes = prices_df['Close']

        sma20 = closes.rolling(window=20).mean()
        sma50 = closes.rolling(window=50).mean()

        # RSI
        delta = closes.diff()
        gain  = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss  = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rsi   = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))

        # MACD
        ema12  = closes.ewm(span=12, adjust=False).mean()
        ema26  = closes.ewm(span=26, adjust=False).mean()
        macd   = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist_  = macd - signal

        def to_list(series):
            return [round(v, 4) if pd.notnull(v) else None for v in series]

        return {
            'dates_list':     [d.strftime('%m/%d') for d in prices_df.index],
            'prices_list':    to_list(closes.round(2)),
            'sma20_list':     to_list(sma20.round(2)),
            'sma50_list':     to_list(sma50.round(2)),
            'rsi_list':       to_list(rsi.round(2)),
            'macd_list':      to_list(macd.round(4)),
            'signal_list':    to_list(signal.round(4)),
            'histogram_list': to_list(hist_.round(4)),
        }
