from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os, threading
from datetime import datetime, timedelta

from data_fetcher import StockDataFetcher, _get_yahoo_with_retry
from technical_analysis import TechnicalAnalyzer
from report_generator import ReportGenerator

app = Flask(__name__)
CORS(app)

fetcher = StockDataFetcher()
analyzer = TechnicalAnalyzer()
reporter = ReportGenerator()

_cache = {}
_lock = threading.Lock()

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
    return {k: v for k, v in data.items() if k != 'prices'}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze/<symbol>')
def analyze_stock(symbol):
    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'
    key = f"analyze_{sym}_{mkt}"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    data = fetcher.get_stock_data(sym, mkt)
    if not data:
        return jsonify({'error': 'تعذّر جلب البيانات، حاول بعد دقيقة'})

    try:
        analysis = analyzer.full_analysis(data['prices'])
        rec = analyzer.get_recommendation(analysis)
        chart_data = analyzer.get_chart_data(data['prices'])
        prices_arr = fetcher.prices_to_array(data['prices'])
        dates_list = [p['date'] for p in prices_arr]
        fibonacci = analyzer.calculate_fibonacci(data['prices'])

        result = {
            **safe_data(data),
            'analysis': analysis,
            'recommendation': rec,
            'prices_arr': prices_arr,
            'dates_list': dates_list,
            'fibonacci': fibonacci,
            **chart_data,
        }
        cache_set(key, result, minutes=10)
        return jsonify(result)
    except Exception as e:
        import traceback
        print(f"Error analyze {symbol}: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'خطأ في التحليل: {str(e)}'})

@app.route('/api/chart-data/<symbol>')
def chart_data(symbol):
    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'
    period   = request.args.get('period', '6mo')
    interval = request.args.get('interval', '1d')

    # map interval → yahoo interval + period
    interval_map = {
        '1m': '1m',  '5m': '5m',  '15m': '15m',
        '1h': '1h',  '4h': '1h',  '1d': '1d',  '1wk': '1wk'
    }
    period_map = {
        '1m': '1d',  '5m': '5d',  '15m': '1mo',
        '1h': '3mo', '4h': '6mo', '1d': period, '1wk': '1y'
    }
    yahoo_interval = interval_map.get(interval, '1d')
    final_period   = period_map.get(interval, period)

    yahoo_sym = f'{sym}.SR' if mkt == 'saudi' else sym
    cache_key = f"chart_{sym}_{mkt}_{final_period}_{yahoo_interval}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)

    # محاولة جلب البيانات بالـ interval المطلوب
    result_yahoo = _get_yahoo_with_retry(yahoo_sym, range_period=final_period, interval=yahoo_interval)

    if result_yahoo:
        hist = fetcher._build_df_yahoo(result_yahoo)
        if hist and len(hist) >= 5:
            try:
                chart_result = analyzer.get_chart_data(hist)
                prices_arr = fetcher.prices_to_array(hist)
                dates_list = [p['date'] for p in prices_arr]
                chart_result['dates_list'] = dates_list
                chart_result['prices_arr'] = prices_arr
                cache_set(cache_key, chart_result, minutes=5)
                return jsonify(chart_result)
            except Exception as e:
                print(f"Chart data error: {e}")

    # fallback: بيانات يومية
    data = fetcher.get_stock_data(sym, mkt)
    if not data:
        return jsonify({'error': 'تعذّر جلب البيانات'})

    try:
        chart_result = analyzer.get_chart_data(data['prices'])
        prices_arr = fetcher.prices_to_array(data['prices'])
        dates_list = [p['date'] for p in prices_arr]

        days_map = {'1mo': 30, '3mo': 90, '6mo': 180, '1y': 365}
        days = days_map.get(final_period, 180)

        if len(dates_list) > days:
            start = len(dates_list) - days
            dates_list = dates_list[start:]
            for k in ['prices_list', 'opens_list', 'highs_list', 'lows_list', 'volumes_list',
                      'sma20_list', 'sma50_list', 'sma200_list', 'rsi_list',
                      'macd_list', 'signal_list', 'histogram_list']:
                if k in chart_result and chart_result[k]:
                    chart_result[k] = chart_result[k][start:]

        chart_result['dates_list'] = dates_list
        chart_result['prices_arr'] = prices_arr
        cache_set(cache_key, chart_result, minutes=5)
        return jsonify(chart_result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/report/<symbol>')
def generate_report(symbol):
    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'
    data = fetcher.get_stock_data(sym, mkt)
    if not data:
        return jsonify({'error': 'تعذّر جلب البيانات'})
    try:
        analysis = analyzer.full_analysis(data['prices'])
        rec = analyzer.get_recommendation(analysis)
        analysis['recommendation'] = rec
        pdf = reporter.generate_pdf(symbol, data, analysis)
        return send_file(pdf, as_attachment=True,
                         download_name=f'{symbol}_تحليل_{datetime.now().strftime("%Y%m%d")}.pdf')
    except Exception as e:
        return jsonify({'error': f'خطأ التقرير: {str(e)}'})

@app.route('/api/main-indices')
def main_indices():
    indices = [
        {'symbol': '^TASI', 'name': 'تاسي', 'flag': '🇸🇦', 'currency': 'SAR'},
        {'symbol': '^GSPC', 'name': 'S&P 500', 'flag': '🇺🇸', 'currency': 'USD'},
        {'symbol': 'GC=F', 'name': 'الذهب', 'flag': '🥇', 'currency': 'USD'},
    ]
    result = []
    for idx in indices:
        key = f"idx_{idx['symbol']}"
        cached = cache_get(key)
        if cached:
            result.append(cached)
            continue
        data = fetcher.get_index_data(idx['symbol'])
        if data:
            row = {**idx, **data}
            cache_set(key, row, minutes=30)
            result.append(row)
    return jsonify(result)

@app.route('/api/rsi-scan')
def rsi_scan():
    market = request.args.get('market', 'saudi')
    rsi_max = float(request.args.get('rsi_max', 30))
    key = f"rsi_scan_{market}_{rsi_max}"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    if market == 'saudi':
        symbols = ['2222','1180','1120','2010','1010','3020','2350','8280','2050','1211',
                   '4200','2220','1060','1150','2380','4230','2360','1140','3001','3002']
    else:
        symbols = ['AAPL','MSFT','GOOGL','AMZN','META','TSLA','NVDA','JPM','JNJ','V',
                   'PG','HD','MA','UNH','BAC','XOM','CVX','DIS','NFLX','AMD']

    results = []
    for sym in symbols:
        try:
            sk = f"analyze_{sym}_{market}"
            cd = cache_get(sk)
            if cd:
                rsi = cd.get('analysis', {}).get('indicators', {}).get('rsi', 100)
                if rsi <= rsi_max:
                    results.append({
                        'symbol': cd.get('symbol'), 'name': cd.get('name'),
                        'price': cd.get('current'), 'change': cd.get('change'),
                        'currency': cd.get('currency'), 'rsi': rsi,
                        'recommendation': cd.get('recommendation', {}),
                    })
                continue
            data = fetcher.get_stock_data(sym, market)
            if not data:
                continue
            inds = analyzer.calculate_all(data['prices'])
            rsi = inds.get('rsi', 100)
            if rsi <= rsi_max:
                rec = analyzer.get_recommendation(analyzer.full_analysis(data['prices']))
                results.append({**safe_data(data), 'rsi': rsi, 'recommendation': rec})
        except:
            continue

    results.sort(key=lambda x: x.get('rsi', 100))
    cache_set(key, results, minutes=30)
    return jsonify(results)

@app.route('/api/search')
def search():
    q = request.args.get('q', '').upper().replace('.SR', '')
    if not q:
        return jsonify({'error': 'أدخل رمز السهم'})
    mkt = 'saudi' if q.isdigit() else 'us'
    data = fetcher.get_stock_data(q, mkt)
    if not data:
        return jsonify({'error': 'لم يتم العثور على السهم'})
    return jsonify(safe_data(data))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
