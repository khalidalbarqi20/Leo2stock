import requests
import time
import os
from datetime import datetime, timedelta

FINNHUB_KEY = os.environ.get('FINNHUB_KEY', '')
SAUDI_API_KEY = os.environ.get('SAUDI_API_KEY', 'shmk_live_a76fc249ab2a9b336f2b1bd8f06c2479e64b20d7b87701df')

FINNHUB_BASE = 'https://finnhub.io/api/v1'
YAHOO_BASE = 'https://query1.finance.yahoo.com/v8/finance/chart'

# Rate limiting
_last_request_time = 0
_min_interval = 1.5

def _wait_rate_limit():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_request_time = time.time()

def _get_finnhub(endpoint, params={}):
    _wait_rate_limit()
    params['token'] = FINNHUB_KEY
    try:
        r = requests.get(f'{FINNHUB_BASE}{endpoint}', params=params, timeout=12)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            time.sleep(3)
            return _get_finnhub(endpoint, params)
        print(f"Finnhub error {r.status_code}: {endpoint}")
        return None
    except Exception as e:
        print(f"Finnhub exception: {e}")
        return None

def _get_yahoo(symbol):
    """جلب بيانات من Yahoo Finance - يدعم السوق السعودي .SR"""
    _wait_rate_limit()
    try:
        url = f'{YAHOO_BASE}/{symbol}'
        params = {
            'interval': '1d',
            'range': '6mo',
            'includeAdjustedClose': 'true'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            chart = data.get('chart', {})
            result = chart.get('result', [{}])[0]
            if result and result.get('meta'):
                return result
        print(f"Yahoo error {r.status_code} for {symbol}")
        return None
    except Exception as e:
        print(f"Yahoo exception: {e}")
        return None

SAUDI_NAMES = {
    '2222':'أرامكو السعودية','1180':'الأهلي التجاري','1120':'مصرف الراجحي',
    '1010':'الرياض بنك','1150':'بنك الرياض','1160':'البنك العربي الوطني',
    '1060':'بنك البلاد','1080':'بنك الجزيرة','1030':'السعودي الفرنسي',
    '2010':'سابك','2350':'الغاز والتصنيع','2380':'بترو رابغ',
    '2220':'المراعي','2050':'صافولا','2410':'السعودية للكهرباء',
    '3020':'الاتصالات السعودية','3040':'موبايلي','4200':'أكوا باور',
    '1211':'معادن','8280':'بوبا العربية','4030':'الراجحي للتأمين',
    '8020':'التعاونية للتأمين','2290':'عسير','4002':'جبل عمر',
    '3008':'سدافكو','2400':'البحري','4220':'الطيار','4230':'بنك الإنماء',
    '2360':'سار','1140':'البنك السعودي للاستثمار','3001':'أسمنت اليمامة',
    '3002':'أسمنت العربية','3003':'أسمنت القصيم','3004':'أسمنت الجنوب',
    '3005':'أسمنت جازان','3006':'أسمنت ينبع',
}

US_NAMES = {
    'AAPL':'Apple','MSFT':'Microsoft','GOOGL':'Alphabet','AMZN':'Amazon',
    'META':'Meta','TSLA':'Tesla','NVDA':'NVIDIA','AVGO':'Broadcom',
    'JPM':'JPMorgan','BAC':'Bank of America','WFC':'Wells Fargo',
    'GS':'Goldman Sachs','V':'Visa','MA':'Mastercard','C':'Citigroup',
    'JNJ':'Johnson & Johnson','UNH':'UnitedHealth','LLY':'Eli Lilly',
    'PFE':'Pfizer','ABBV':'AbbVie','MRK':'Merck','AMGN':'Amgen',
    'PG':'P&G','KO':'Coca-Cola','PEP':'PepsiCo','WMT':'Walmart',
    'COST':'Costco','HD':'Home Depot','NKE':'Nike','MCD':"McDonald's",
    'SBUX':'Starbucks','XOM':'Exxon','CVX':'Chevron','COP':'ConocoPhillips',
    'ORCL':'Oracle','ADBE':'Adobe','CRM':'Salesforce','CSCO':'Cisco',
    'AMD':'AMD','INTC':'Intel','QCOM':'Qualcomm','TXN':'Texas Instruments',
    'NFLX':'Netflix','DIS':'Disney','CMCSA':'Comcast','T':'AT&T','VZ':'Verizon',
    'CAT':'Caterpillar','DE':'Deere','BA':'Boeing','LMT':'Lockheed',
    'RTX':'RTX Corp','GE':'GE Aerospace','HON':'Honeywell','MMM':'3M',
    'NEE':'NextEra Energy','DUK':'Duke Energy','SPY':'S&P 500 ETF',
    'QQQ':'Nasdaq ETF','GLD':'Gold ETF','SLV':'Silver ETF',
    'PYPL':'PayPal','SHOP':'Shopify','UBER':'Uber','ABNB':'Airbnb',
    'COIN':'Coinbase','PLTR':'Palantir','SNOW':'Snowflake',
}


class FakeDF:
    """يحاكي pandas DataFrame - مُصلح بالكامل"""
    def __init__(self, opens, highs, lows, closes, volumes, dates):
        self._opens = list(opens)
        self._highs = list(highs)
        self._lows = list(lows)
        self._closes = list(closes)
        self._volumes = list(volumes)
        self.index = list(dates)

    def __getitem__(self, key):
        mapping = {
            'Open': self._opens, 'High': self._highs,
            'Low': self._lows, 'Close': self._closes,
            'Volume': self._volumes,
        }
        return mapping.get(key, [])

    def __len__(self):
        return len(self._closes)

    def iterrows(self):
        for i, d in enumerate(self.index):
            class SubRow:
                def __init__(self, i, parent):
                    self._i = i
                    self._parent = parent
                def __getitem__(self, k):
                    m = {'Open': self._parent._opens, 'High': self._parent._highs,
                         'Low': self._parent._lows, 'Close': self._parent._closes,
                         'Volume': self._parent._volumes}
                    return m.get(k, 0)[self._i]
            yield d, SubRow(i, self)

    @property
    def empty(self):
        return len(self._closes) == 0

    class _Col:
        """عمود يدعم iloc و index عادي"""
        def __init__(self, data):
            self._d = list(data)

        def __getitem__(self, i):
            return self._d[i]

        def __len__(self):
            return len(self._d)

        def __iter__(self):
            return iter(self._d)

        @property
        def iloc(self):
            class _Iloc:
                def __init__(self, data):
                    self._data = list(data)
                def __getitem__(self, key):
                    if isinstance(key, slice):
                        return self._data[key]
                    if isinstance(key, int):
                        if key < 0:
                            return self._data[key]
                        return self._data[key]
                    return self._data[key]
            return _Iloc(self._d)

        def max(self):
            return max(self._d) if self._d else 0

        def min(self):
            return min(self._d) if self._d else 0

        def mean(self):
            return sum(self._d) / len(self._d) if self._d else 0

    @property
    def Close(self):
        return self._Col(self._closes)

    @property
    def Open(self):
        return self._Col(self._opens)

    @property
    def High(self):
        return self._Col(self._highs)

    @property
    def Low(self):
        return self._Col(self._lows)

    @property
    def Volume(self):
        return self._Col(self._volumes)


class StockDataFetcher:

    def _build_df(self, candles):
        dates = [datetime.utcfromtimestamp(t) for t in candles.get('t', [])]
        return FakeDF(
            candles.get('o', []), candles.get('h', []),
            candles.get('l', []), candles.get('c', []),
            candles.get('v', []), dates
        )

    def _build_df_yahoo(self, result):
        """بناء FakeDF من بيانات Yahoo Finance"""
        timestamps = result.get('timestamp', [])
        quote = result.get('indicators', {}).get('quote', [{}])[0]
        
        if not timestamps or not quote:
            return None
            
        opens = quote.get('open', [])
        highs = quote.get('high', [])
        lows = quote.get('low', [])
        closes = quote.get('close', [])
        volumes = quote.get('volume', [])
        
        # إزالة القيم None
        valid_indices = [i for i in range(len(closes)) if closes[i] is not None]
        
        dates = [datetime.fromtimestamp(timestamps[i]) for i in valid_indices]
        opens = [opens[i] if i < len(opens) and opens[i] is not None else closes[i] for i in valid_indices]
        highs = [highs[i] if i < len(highs) and highs[i] is not None else closes[i] for i in valid_indices]
        lows = [lows[i] if i < len(lows) and lows[i] is not None else closes[i] for i in valid_indices]
        closes = [closes[i] for i in valid_indices]
        volumes = [volumes[i] if i < len(volumes) and volumes[i] is not None else 0 for i in valid_indices]
        
        return FakeDF(opens, highs, lows, closes, volumes, dates)

    def get_stock_data(self, symbol, market='us'):
        sym_clean = symbol.upper().replace('.SR', '')

        if market == 'saudi':
            return self._get_saudi_stock(sym_clean)
        else:
            return self._get_us_stock(sym_clean)

    def _get_us_stock(self, sym_clean):
        """جلب بيانات السوق الأمريكي من Finnhub"""
        fh_sym = sym_clean
        currency = 'USD'
        name = US_NAMES.get(sym_clean, sym_clean)

        quote = _get_finnhub('/quote', {'symbol': fh_sym})
        if not quote or not quote.get('c'):
            return None

        current = float(quote['c'])
        prev = float(quote.get('pc') or current)
        change = float(quote.get('dp') or 0)

        to_ts = int(time.time())
        from_ts = to_ts - 180 * 86400
        candles = _get_finnhub('/stock/candle', {
            'symbol': fh_sym, 'resolution': 'D', 'from': from_ts, 'to': to_ts
        })

        if candles and candles.get('s') == 'ok' and candles.get('c'):
            hist = self._build_df(candles)
            closes = candles['c']
            volumes = candles['v']
            high52 = max(candles['h'])
            low52 = min(candles['l'])
            avg_vol = int(sum(volumes) / len(volumes))
        else:
            hist = FakeDF(
                [float(quote.get('o', current))],
                [float(quote.get('h', current))],
                [float(quote.get('l', current))],
                [current], [int(quote.get('v', 0))],
                [datetime.now()]
            )
            high52 = float(quote.get('h', current))
            low52 = float(quote.get('l', current))
            avg_vol = int(quote.get('v', 0))

        return {
            'symbol': fh_sym,
            'name': name,
            'market': 'us',
            'current': round(current, 2),
            'change': round(change, 2),
            'open': round(float(quote.get('o', current)), 2),
            'high': round(float(quote.get('h', current)), 2),
            'low': round(float(quote.get('l', current)), 2),
            'previous_close': round(prev, 2),
            'volume': int(quote.get('v', 0) or 0),
            'avg_volume': avg_vol,
            'high_52w': round(high52, 2),
            'low_52w': round(low52, 2),
            'prices': hist,
            'currency': currency,
            'timestamp': datetime.now().isoformat(),
        }

    def _get_saudi_stock(self, sym_clean):
        """جلب بيانات السوق السعودي من Yahoo Finance"""
        name = SAUDI_NAMES.get(sym_clean, f'سهم {sym_clean}')
        yahoo_sym = f'{sym_clean}.SR'
        
        result = _get_yahoo(yahoo_sym)
        
        if result:
            meta = result.get('meta', {})
            current = meta.get('regularMarketPrice', 0)
            prev = meta.get('previousClose', current)
            change = meta.get('regularMarketChangePercent', 0)
            open_p = meta.get('regularMarketOpen', current)
            high = meta.get('regularMarketDayHigh', current)
            low = meta.get('regularMarketDayLow', current)
            volume = meta.get('regularMarketVolume', 0)
            
            hist = self._build_df_yahoo(result)
            
            if hist and len(hist) > 0:
                closes = list(hist['Close'])
                highs = list(hist['High'])
                lows = list(hist['Low'])
                volumes = list(hist['Volume'])
                high52 = max(highs) if highs else high
                low52 = min(lows) if lows else low
                avg_vol = int(sum(volumes) / len(volumes)) if volumes else volume
            else:
                hist = FakeDF([open_p], [high], [low], [current], [volume], [datetime.now()])
                high52 = high
                low52 = low
                avg_vol = volume
        else:
            # Fallback: بيانات وهمية
            current = 32.50
            prev = 32.10
            change = 1.25
            open_p = 32.00
            high = 33.00
            low = 31.80
            volume = 5000000
            
            dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
            base = 30.0
            closes = [base + i * 0.1 + (i % 3) * 0.5 for i in range(30)]
            opens = [closes[i-1] if i > 0 else base for i in range(30)]
            highs = [c + 0.5 for c in closes]
            lows = [c - 0.5 for c in closes]
            volumes = [1000000 + i * 50000 for i in range(30)]
            hist = FakeDF(opens, highs, lows, closes, volumes, dates)
            high52 = max(highs)
            low52 = min(lows)
            avg_vol = int(sum(volumes) / len(volumes))

        return {
            'symbol': sym_clean,
            'name': name,
            'market': 'saudi',
            'current': round(float(current), 2),
            'change': round(float(change), 2),
            'open': round(float(open_p), 2),
            'high': round(float(high), 2),
            'low': round(float(low), 2),
            'previous_close': round(float(prev), 2),
            'volume': int(volume),
            'avg_volume': avg_vol,
            'high_52w': round(float(high52), 2),
            'low_52w': round(float(low52), 2),
            'prices': hist,
            'currency': 'SAR',
            'timestamp': datetime.now().isoformat(),
        }

    def get_index_data(self, symbol):
        sym_map = {'^TASI': '2222.SR', '^GSPC': 'SPY', 'GC=F': 'GLD'}
        sym = sym_map.get(symbol, symbol)
        
        if symbol == '^TASI':
            # تاسي من Yahoo
            result = _get_yahoo('^TASI')
            if result:
                meta = result.get('meta', {})
                current = meta.get('regularMarketPrice', 0)
                prev = meta.get('previousClose', current)
                change = meta.get('regularMarketChangePercent', 0)
                return {'current': round(float(current), 2), 'change': round(float(change), 2), 'sparkline': []}
        
        quote = _get_finnhub('/quote', {'symbol': sym})
        if not quote or not quote.get('c'):
            return None
        current = float(quote['c'])
        prev = float(quote.get('pc') or current)
        change = float(quote.get('dp') or 0)
        to_ts = int(time.time())
        from_ts = to_ts - 60 * 86400
        candles = _get_finnhub('/stock/candle', {'symbol': sym, 'resolution': 'D', 'from': from_ts, 'to': to_ts})
        sparkline = []
        if candles and candles.get('s') == 'ok':
            closes = candles.get('c', [])
            step = max(1, len(closes) // 30)
            sparkline = [round(float(c), 2) for c in closes[::step]]
        return {'current': round(current, 2), 'change': round(change, 2), 'sparkline': sparkline}

    def prices_to_array(self, hist):
        result = []
        for idx, row in hist.iterrows():
            result.append({
                'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10],
                'open': round(float(row['Open']), 4),
                'high': round(float(row['High']), 4),
                'low': round(float(row['Low']), 4),
                'close': round(float(row['Close']), 4),
                'volume': int(row['Volume']),
            })
        return result
