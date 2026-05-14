from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os, threading, random
from datetime import datetime, timedelta

from data_fetcher import StockDataFetcher
from technical_analysis import TechnicalAnalyzer
from report_generator import ReportGenerator

app = Flask(__name__, template_folder='templates')
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

# AI PREDICTION
def ai_predict(prices, indicators, trend):
    closes = list(prices['Close']) if hasattr(prices['Close'], '__iter__') else prices['Close']
    if not isinstance(closes, list):
        closes = list(closes)
    if len(closes) < 20:
        return {'prediction': 'غير كافٍ', 'confidence': 0, 'direction': 'neutral'}
    recent = closes[-10:]
    momentum = (recent[-1] - recent[0]) / recent[0] * 100 if recent[0] else 0
    rsi = indicators.get('rsi', 50)
    macd = indicators.get('macd', {})
    bb = indicators.get('bollinger', {})
    score = 0
    reasons = []
    if rsi < 30:
        score += 2
        reasons.append('RSI في منطقة تشبع بيعي - احتمال ارتداد صعودي')
    elif rsi > 70:
        score -= 2
        reasons.append('RSI في منطقة تشبع شرائي - احتمال تصحيح')
    if macd.get('histogram', 0) > 0:
        score += 1.5
        reasons.append('MACD إيجابي - الزخم صاعد')
    else:
        score -= 1.5
        reasons.append('MACD سلبي - الزخم هابط')
    current = closes[-1]
    if bb.get('lower') and current <= bb['lower']:
        score += 1.5
        reasons.append('السعر عند حد بولينجر السفلي - منطقة شراء')
    elif bb.get('upper') and current >= bb['upper']:
        score -= 1.5
        reasons.append('السعر عند حد بولينجر العلوي - منطقة بيع')
    if 'bullish' in trend:
        score += 1
        reasons.append('الاتجاه العام صعودي')
    elif 'bearish' in trend:
        score -= 1
        reasons.append('الاتجاه العام هبوطي')
    if momentum > 5:
        score += 0.5
        reasons.append(f'زخم صعودي قوي +{momentum:.1f}%')
    elif momentum < -5:
        score -= 0.5
        reasons.append(f'زخم هبوطي قوي {momentum:.1f}%')
    confidence = min(abs(score) / 6 * 100, 95)
    if score >= 3:
        return {'prediction': 'ارتفاع متوقع', 'confidence': round(confidence, 1), 'direction': 'up',
                'target_price': round(current * 1.05, 2), 'reasons': reasons, 'timeframe': '5-10 أيام'}
    elif score <= -3:
        return {'prediction': 'هبوط متوقع', 'confidence': round(confidence, 1), 'direction': 'down',
                'target_price': round(current * 0.95, 2), 'reasons': reasons, 'timeframe': '5-10 أيام'}
    else:
        return {'prediction': 'تذبذب/محايد', 'confidence': round(confidence, 1), 'direction': 'neutral',
                'target_price': round(current, 2), 'reasons': reasons, 'timeframe': '3-7 أيام'}

# EARNINGS CALENDAR
EARNINGS_DATA = {
    'AAPL': {'date': '2026-07-28', 'eps_estimate': 1.35, 'revenue_estimate': '89.5B'},
    'MSFT': {'date': '2026-07-22', 'eps_estimate': 3.12, 'revenue_estimate': '64.2B'},
    'GOOGL': {'date': '2026-07-23', 'eps_estimate': 1.85, 'revenue_estimate': '84.1B'},
    'AMZN': {'date': '2026-07-30', 'eps_estimate': 1.25, 'revenue_estimate': '148.5B'},
    'TSLA': {'date': '2026-07-19', 'eps_estimate': 0.72, 'revenue_estimate': '25.8B'},
    'NVDA': {'date': '2026-08-20', 'eps_estimate': 0.65, 'revenue_estimate': '28.7B'},
    'META': {'date': '2026-07-24', 'eps_estimate': 5.25, 'revenue_estimate': '39.8B'},
    '2222': {'date': '2026-08-05', 'eps_estimate': None, 'revenue_estimate': '402B SAR'},
    '1120': {'date': '2026-07-15', 'eps_estimate': None, 'revenue_estimate': '8.2B SAR'},
    '2010': {'date': '2026-07-20', 'eps_estimate': None, 'revenue_estimate': '38.5B SAR'},
}

def get_earnings_data(symbol):
    return EARNINGS_DATA.get(symbol, None)

# ROUTES
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
        ai_result = ai_predict(data['prices'], analysis['indicators'], analysis['trend'])
        earnings = get_earnings_data(sym)
        fib_levels = analyzer.calculate_fibonacci(data['prices'])
        vol_profile = analyzer.calculate_volume_profile(data['prices'])
        chart_data = analyzer.get_chart_data(data['prices'])
        prices_arr = fetcher.prices_to_array(data['prices'])
        dates_list = [p['date'] for p in prices_arr]
        result = {
            **safe_data(data),
            'analysis': analysis,
            'recommendation': rec,
            'ai_prediction': ai_result,
            'earnings': earnings,
            'fibonacci': fib_levels,
            'volume_profile': vol_profile,
            'prices_arr': prices_arr,
            'dates_list': dates_list,
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
    period = request.args.get('period', '6mo')
    data = fetcher.get_stock_data(sym, mkt)
    if not data:
        return jsonify({'error': 'تعذّر جلب البيانات'})
    try:
        chart_data = analyzer.get_chart_data(data['prices'])
        prices_arr = fetcher.prices_to_array(data['prices'])
        dates_list = [p['date'] for p in prices_arr]
        days_map = {'1mo': 30, '3mo': 90, '6mo': 180, '1y': 365}
        days = days_map.get(period, 180)
        if len(dates_list) > days:
            start = len(dates_list) - days
            dates_list = dates_list[start:]
            for k in ['prices_list', 'opens_list', 'highs_list', 'lows_list', 'volumes_list',
                      'sma20_list', 'sma50_list', 'sma200_list', 'rsi_list', 
                      'macd_list', 'signal_list', 'histogram_list']:
                if k in chart_data and chart_data[k]:
                    chart_data[k] = chart_data[k][start:]
        chart_data['dates_list'] = dates_list
        return jsonify(chart_data)
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
        symbols = ['2222', '1180', '1120', '2010', '1010', '3020', '2350', '8280', '2050', '1211', 
                   '4200', '2220', '1060', '1150', '2380', '4230', '2360', '1140', '3001', '3002']
    else:
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V', 
                   'PG', 'HD', 'MA', 'UNH', 'BAC', 'XOM', 'CVX', 'DIS', 'NFLX', 'AMD']
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

@app.route('/api/opportunities')
def opportunities():
    key = "opportunities"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)
    saudi = ['2222', '1180', '1120', '2010', '1010', '3020', '2350', '8280', '2050', '1211']
    us = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V']
    def score(sym, mkt):
        try:
            data = fetcher.get_stock_data(sym, mkt)
            if not data:
                return None
            an = analyzer.full_analysis(data['prices'])
            rec = analyzer.get_recommendation(an)
            return {**safe_data(data), 'analysis': an, 'recommendation': rec, 'score': rec.get('score', 0)}
        except:
            return None
    sr, ur = [], []
    for s in saudi:
        r = score(s, 'saudi')
        if r and r['score'] >= 1:
            sr.append(r)
    for s in us:
        r = score(s, 'us')
        if r and r['score'] >= 1:
            ur.append(r)
    sr.sort(key=lambda x: x['score'], reverse=True)
    ur.sort(key=lambda x: x['score'], reverse=True)
    result = {'saudi': sr[:5], 'us': ur[:5]}
    cache_set(key, result, minutes=60)
    return jsonify(result)

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
