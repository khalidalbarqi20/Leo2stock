import requests
import time
import os
from datetime import datetime

FINNHUB_KEY = os.environ.get('FINNHUB_KEY', '')
BASE = 'https://finnhub.io/api/v1'

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
    '2360':'سار','1140':'البنك السعودي للاستثمار','1120':'مصرف الراجحي',
    '3001':'أسمنت اليمامة','3002':'أسمنت العربية','3003':'أسمنت القصيم',
    '3004':'أسمنت الجنوب','3005':'أسمنت جازان','3006':'أسمنت ينبع',
}

US_NAMES = {
    'AAPL':'Apple','MSFT':'Microsoft','GOOGL':'Alphabet','AMZN':'Amazon',
    'META':'Meta','TSLA':'Tesla','NVDA':'NVIDIA','AVGO':'Broadcom',
    'JPM':'JPMorgan','BAC':'Bank of America','WFC':'Wells Fargo',
    'GS':'Goldman Sachs','V':'Visa','MA':'Mastercard','C':'Citigroup',
    'JNJ':'Johnson & Johnson','UNH':'UnitedHealth','LLY':'Eli Lilly',
    'PFE':'Pfizer','ABBV':'AbbVie','MRK':'Merck','AMGN':'Amgen',
    'PG':'P&G','KO':'Coca-Cola','PEP':'PepsiCo','WMT':'Walmart',
    'COST':'Costco','HD':'Home Depot','NKE':'Nike','MCD':'McDonald\'s',
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

def _get(endpoint, params={}):
    params['token'] = FINNHUB_KEY
    try:
        r = requests.get(f'{BASE}{endpoint}', params=params, timeout=8)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None

class FakeDF:
    """يحاكي pandas DataFrame لتوافق technical_analysis.py"""
    def __init__(self, opens, highs, lows, closes, volumes, dates):
        self._opens   = opens
        self._highs   = highs
        self._lows    = lows
        self._closes  = closes
        self._volumes = volumes
        self.index    = dates

    def __getitem__(self, key):
        return {
            'Open': self._opens, 'High': self._highs,
            'Low':  self._lows,  'Close': self._closes,
            'Volume': self._volumes,
        }[key]

    def iterrows(self):
        for i, d in enumerate(self.index):
            yield d, type('R',(),{
                '__getitem__': lambda s,k,i=i: {
                    'Open':self._opens[i],'High':self._highs[i],
                    'Low':self._lows[i],'Close':self._closes[i],
                    'Volume':self._volumes[i]
                }[k]
            })()

    @property
    def empty(self): return len(self._closes)==0

    # واجهة مشابهة لـ pandas Series
    class _Col:
        def __init__(self, data):
            self._d = data
        def iloc(self): pass
        def __getitem__(self, i): return self._d[i]
        def max(self): return max(self._d) if self._d else 0
        def min(self): return min(self._d) if self._d else 0
        def mean(self): return sum(self._d)/len(self._d) if self._d else 0

    @property
    def Close(self): return self._Col(self._closes)
    @property
    def Open(self):  return self._Col(self._opens)
    @property
    def High(self):  return self._Col(self._highs)
    @property
    def Low(self):   return self._Col(self._lows)
    @property
    def Volume(self):return self._Col(self._volumes)


class StockDataFetcher:

    def _build_df(self, candles):
        dates   = [datetime.utcfromtimestamp(t) for t in candles['t']]
        return FakeDF(candles['o'], candles['h'], candles['l'],
                      candles['c'], candles['v'], dates)

    def get_stock_data(self, symbol, market='us'):
        sym_clean = symbol.upper().replace('.SR','')
        if market == 'saudi':
            fh_sym   = f'{sym_clean}.SR'
            currency = 'SAR'
            name     = SAUDI_NAMES.get(sym_clean, f'سهم {sym_clean}')
        else:
            fh_sym   = sym_clean
            currency = 'USD'
            name     = US_NAMES.get(sym_clean, sym_clean)

        # 1) السعر الحالي
        quote = _get('/quote', {'symbol': fh_sym})
        if not quote or not quote.get('c'):
            return None
        current = float(quote['c'])
        prev    = float(quote.get('pc') or current)
        change  = float(quote.get('dp') or 0)

        # 2) التاريخ — آخر 6 أشهر
        to_ts   = int(time.time())
        from_ts = to_ts - 180*86400
        candles = _get('/stock/candle', {
            'symbol':fh_sym,'resolution':'D','from':from_ts,'to':to_ts
        })

        if candles and candles.get('s')=='ok' and candles.get('c'):
            hist = self._build_df(candles)
            closes  = candles['c']
            volumes = candles['v']
            high52  = max(candles['h'])
            low52   = min(candles['l'])
            avg_vol = int(sum(volumes)/len(volumes))
        else:
            # fallback بيانات اليوم فقط
            hist = FakeDF(
                [float(quote.get('o',current))],
                [float(quote.get('h',current))],
                [float(quote.get('l',current))],
                [current],[int(quote.get('v',0))],
                [datetime.now()]
            )
            high52  = float(quote.get('h',current))
            low52   = float(quote.get('l',current))
            avg_vol = int(quote.get('v',0))

        return {
            'symbol':         fh_sym,
            'name':           name,
            'market':         market,
            'current':        round(current,2),
            'change':         round(change,2),
            'open':           round(float(quote.get('o',current)),2),
            'high':           round(float(quote.get('h',current)),2),
            'low':            round(float(quote.get('l',current)),2),
            'previous_close': round(prev,2),
            'volume':         int(quote.get('v',0) or 0),
            'avg_volume':     avg_vol,
            'high_52w':       round(high52,2),
            'low_52w':        round(low52,2),
            'prices':         hist,
            'currency':       currency,
            'timestamp':      datetime.now().isoformat(),
        }

    def get_index_data(self, symbol):
        sym_map = {'^TASI':'2222.SR','^GSPC':'SPY','GC=F':'GLD'}
        sym = sym_map.get(symbol, symbol)
        quote = _get('/quote',{'symbol':sym})
        if not quote or not quote.get('c'):
            return None
        current = float(quote['c'])
        prev    = float(quote.get('pc') or current)
        change  = float(quote.get('dp') or 0)
        to_ts   = int(time.time())
        from_ts = to_ts - 60*86400
        candles = _get('/stock/candle',{'symbol':sym,'resolution':'D','from':from_ts,'to':to_ts})
        sparkline = []
        if candles and candles.get('s')=='ok':
            closes = candles.get('c',[])
            step   = max(1,len(closes)//30)
            sparkline = [round(float(c),2) for c in closes[::step]]
        return {'current':round(current,2),'change':round(change,2),'sparkline':sparkline}

    def prices_to_array(self, hist):
        result = []
        for idx, row in hist.iterrows():
            result.append({
                'date':   idx.strftime('%Y-%m-%d') if hasattr(idx,'strftime') else str(idx)[:10],
                'open':   round(float(row['Open']),4),
                'high':   round(float(row['High']),4),
                'low':    round(float(row['Low']),4),
                'close':  round(float(row['Close']),4),
                'volume': int(row['Volume']),
            })
        return result
