from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os, threading
from datetime import datetime, timedelta

from data_fetcher import StockDataFetcher
from technical_analysis import TechnicalAnalyzer
from report_generator import ReportGenerator

app = Flask(__name__)
CORS(app)

fetcher  = StockDataFetcher()
analyzer = TechnicalAnalyzer()
reporter = ReportGenerator()

# ── كاش قوي: 10 دقائق للبيانات العادية، ساعة للمؤشرات ──
_cache = {}
_lock  = threading.Lock()

def cache_get(key):
    with _lock:
        if key in _cache:
            val, exp = _cache[key]
            if datetime.now() < exp:
                return val
            del _cache[key]
    return None

def cache_set(key, val, minutes=10):
    with _lock:
        _cache[key] = (val, datetime.now() + timedelta(minutes=minutes))

def safe_data(data):
    """إزالة DataFrame قبل الإرسال"""
    return {k: v for k, v in data.items() if k != 'prices'}

# ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ── تحليل سهم ────────────────────────────────────────────
@app.route('/api/analyze/<symbol>')
def analyze_stock(symbol):
    sym  = symbol.upper().replace('.SR','')
    mkt  = 'saudi' if sym.isdigit() else 'us'
    key  = f"analyze_{sym}_{mkt}"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    data = fetcher.get_stock_data(sym, mkt)
    if not data:
        return jsonify({'error': 'تعذّر جلب البيانات، حاول بعد دقيقة'})

    try:
        analysis = analyzer.full_analysis(data['prices'])
        rec      = analyzer.get_recommendation(analysis)
        prices_arr = fetcher.prices_to_array(data['prices'])
        result = {**safe_data(data), 'analysis': analysis,
                  'recommendation': rec, 'prices_arr': prices_arr}
        cache_set(key, result, minutes=10)
        return jsonify(result)
    except Exception as e:
        print(f"Error analyze {symbol}: {e}")
        return jsonify({'error': f'خطأ في التحليل: {str(e)}'})

# ── تقرير PDF ─────────────────────────────────────────────
@app.route('/api/report/<symbol>')
def generate_report(symbol):
    sym = symbol.upper().replace('.SR','')
    mkt = 'saudi' if sym.isdigit() else 'us'
    data = fetcher.get_stock_data(sym, mkt)
    if not data:
        return jsonify({'error': 'تعذّر جلب البيانات'})
    try:
        analysis = analyzer.full_analysis(data['prices'])
        rec      = analyzer.get_recommendation(analysis)
        analysis['recommendation'] = rec
        pdf = reporter.generate_pdf(symbol, data, analysis)
        return send_file(pdf, as_attachment=True,
                         download_name=f'{symbol}_تحليل_{datetime.now().strftime("%Y%m%d")}.pdf')
    except Exception as e:
        return jsonify({'error': f'خطأ التقرير: {str(e)}'})

# ── مؤشرات رئيسية ─────────────────────────────────────────
@app.route('/api/main-indices')
def main_indices():
    indices = [
        {'symbol':'^TASI', 'name':'تاسي',   'flag':'🇸🇦','currency':'SAR'},
        {'symbol':'^GSPC', 'name':'S&P 500', 'flag':'🇺🇸','currency':'USD'},
        {'symbol':'GC=F',  'name':'الذهب',   'flag':'🥇', 'currency':'USD'},
    ]
    result = []
    for idx in indices:
        key    = f"idx_{idx['symbol']}"
        cached = cache_get(key)
        if cached:
            result.append(cached); continue
        data = fetcher.get_index_data(idx['symbol'])
        if data:
            row = {**idx, **data}
            cache_set(key, row, minutes=30)
            result.append(row)
    return jsonify(result)

# ── مسح RSI < 30 ──────────────────────────────────────────
@app.route('/api/rsi-scan')
def rsi_scan():
    market = request.args.get('market', 'saudi')
    key    = f"rsi_scan_{market}"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    if market == 'saudi':
        symbols = ['2222','1180','1120','2010','1010','3020','2350','8280','2050','1211','4200','2220','1060','1150','2380']
    else:
        symbols = ['AAPL','MSFT','GOOGL','AMZN','META','TSLA','NVDA','JPM','JNJ','V','PG','HD','MA','UNH','BAC']

    results = []
    for sym in symbols:
        try:
            sk = f"analyze_{sym}_{market}"
            cd = cache_get(sk)
            if cd:
                rsi = cd.get('analysis',{}).get('indicators',{}).get('rsi', 100)
                if rsi < 30:
                    results.append({**cd, 'rsi': rsi})
                continue
            data = fetcher.get_stock_data(sym, market)
            if not data: continue
            inds = analyzer.calculate_all(data['prices'])
            rsi  = inds.get('rsi', 100)
            if rsi < 30:
                results.append({**safe_data(data), 'rsi': rsi})
        except: continue

    results.sort(key=lambda x: x.get('rsi', 100))
    cache_set(key, results, minutes=30)
    return jsonify(results)

# ── فرص الدخول ────────────────────────────────────────────
@app.route('/api/opportunities')
def opportunities():
    key    = "opportunities"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    saudi = ['2222','1180','1120','2010','1010','3020','2350','8280','2050','1211']
    us    = ['AAPL','MSFT','GOOGL','AMZN','META','TSLA','NVDA','JPM','JNJ','V']

    def score(sym, mkt):
        try:
            data = fetcher.get_stock_data(sym, mkt)
            if not data: return None
            an  = analyzer.full_analysis(data['prices'])
            rec = analyzer.get_recommendation(an)
            return {**safe_data(data), 'analysis': an,
                    'recommendation': rec, 'score': rec.get('score', 0)}
        except: return None

    sr, ur = [], []
    for s in saudi:
        r = score(s, 'saudi')
        if r and r['score'] >= 1: sr.append(r)
    for s in us:
        r = score(s, 'us')
        if r and r['score'] >= 1: ur.append(r)

    sr.sort(key=lambda x: x['score'], reverse=True)
    ur.sort(key=lambda x: x['score'], reverse=True)
    result = {'saudi': sr[:5], 'us': ur[:5]}
    cache_set(key, result, minutes=60)
    return jsonify(result)

# ── نظرة السوق ────────────────────────────────────────────
@app.route('/api/market-overview')
def market_overview():
    key    = "market_overview"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    symbols = {'saudi':['2222','1180','8280','2350'], 'us':['AAPL','TSLA','NVDA','MSFT']}
    overview = {}
    for mkt, syms in symbols.items():
        overview[mkt] = []
        for sym in syms:
            try:
                data = fetcher.get_stock_data(sym, mkt)
                if data:
                    overview[mkt].append({
                        'symbol': data['symbol'], 'price': data['current'],
                        'change': data['change'], 'name':  data['name'],
                        'currency': data['currency']
                    })
            except: continue

    cache_set(key, overview, minutes=15)
    return jsonify(overview)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
