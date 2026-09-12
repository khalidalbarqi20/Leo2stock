from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os, threading
from datetime import datetime, timedelta

from data_fetcher import StockDataFetcher, _get_yahoo_with_retry
from technical_analysis import TechnicalAnalyzer
from report_generator import ReportGenerator
import storage
import scanner as scanner_module
import auth
import signal_view

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

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/scanner')
def scanner_page():
    return render_template('scanner.html')

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

# ==========================================================================
# مراقب الفرص — Custom Strategies / Scanner / Alerts / Watchlist / AI / Auth
# ==========================================================================

@app.route('/api/auth/create-user', methods=['POST'])
@auth.require_admin
def create_user():
    """يصدر Token جديد لمستخدم — محمي بمفتاح ADMIN_KEY فقط (خالد يستخدمه يدوياً)."""
    body = request.get_json(silent=True) or {}
    user = storage.create_user(body.get('label'))
    return jsonify(user)  # التوكن يظهر مرة واحدة هنا فقط — يُحفظ من طرف العميل


@app.route('/api/market-status')
def api_market_status():
    import market_hours
    return jsonify({'saudi': market_hours.market_status('saudi'), 'us': market_hours.market_status('us')})


@app.route('/api/strategies', methods=['GET', 'POST'])
@auth.require_auth
def strategies_collection(uid):
    if request.method == 'GET':
        return jsonify(storage.list_strategies(uid))
    body = request.get_json(force=True)
    required = ['name', 'market', 'conditions']
    if not all(k in body for k in required):
        return jsonify({'error': 'الحقول المطلوبة: name, market, conditions'}), 400
    sid = storage.create_strategy(uid, body['name'], body['market'], body.get('mode', 'trigger'),
                                   body['conditions'], body.get('reset_conditions'))
    return jsonify(storage.get_strategy(sid))


def _owns_strategy_or_404(sid, uid):
    s = storage.get_strategy(sid)
    if not s:
        return None, (jsonify({'error': 'غير موجودة'}), 404)
    if s['user_id'] != uid:
        # لا نكشف حتى بوجودها لمستخدم آخر — نفس رسالة "غير موجودة"
        return None, (jsonify({'error': 'غير موجودة'}), 404)
    return s, None


@app.route('/api/strategies/<int:sid>', methods=['GET', 'PATCH', 'DELETE'])
@auth.require_auth
def strategy_item(sid, uid):
    s, err = _owns_strategy_or_404(sid, uid)
    if err:
        return err
    if request.method == 'GET':
        return jsonify(s)
    if request.method == 'DELETE':
        storage.delete_strategy(sid)
        return jsonify({'deleted': sid})
    body = request.get_json(force=True)
    fields = {}
    if 'name' in body: fields['name'] = body['name']
    if 'market' in body: fields['market'] = body['market']
    if 'mode' in body: fields['mode'] = body['mode']
    if 'active' in body: fields['active'] = int(bool(body['active']))
    if 'conditions' in body:
        import json as _json
        fields['conditions_json'] = _json.dumps(body['conditions'], ensure_ascii=False)
    if 'reset_conditions' in body:
        import json as _json
        fields['reset_conditions_json'] = _json.dumps(body['reset_conditions'], ensure_ascii=False)
    storage.update_strategy(sid, **fields)
    return jsonify(storage.get_strategy(sid))


@app.route('/api/scan/<int:sid>')
@auth.require_auth
def run_scan(sid, uid):
    strategy, err = _owns_strategy_or_404(sid, uid)
    if err:
        return err
    if not strategy['active']:
        return jsonify({'error': 'الاستراتيجية معطّلة'}), 400
    with_ai = request.args.get('ai', '1') != '0'
    symbols_param = request.args.get('symbols')
    symbols = symbols_param.split(',') if symbols_param else None
    result = scanner_module.run_scan(strategy, fetcher, analyzer, symbols=symbols,
                                      user_id=uid, with_ai=with_ai)
    return jsonify(result)


@app.route('/api/watchlist', methods=['GET', 'POST', 'DELETE'])
@auth.require_auth
def watchlist_endpoint(uid):
    if request.method == 'GET':
        return jsonify(storage.get_watchlist(uid))
    body = request.get_json(force=True)
    sym = body.get('symbol', '').upper().replace('.SR', '')
    if not sym:
        return jsonify({'error': 'أدخل رمز السهم'}), 400
    mkt = body.get('market') or ('saudi' if sym.isdigit() else 'us')
    if request.method == 'POST':
        storage.add_to_watchlist(uid, sym, mkt)
    else:
        storage.remove_from_watchlist(uid, sym, mkt)
    return jsonify(storage.get_watchlist(uid))


@app.route('/api/alerts/history')
@auth.require_auth
def alerts_history(uid):
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 50))
    return jsonify(storage.get_alert_history(uid, symbol, limit))


@app.route('/api/signals')
@auth.require_auth
def list_signals(uid):
    signals = storage.list_signals(
        uid, strategy_id=request.args.get('strategy_id', type=int),
        symbol=request.args.get('symbol'), status=request.args.get('status'),
        market=request.args.get('market'), min_score=request.args.get('min_score', type=int),
        limit=int(request.args.get('limit', 50)))
    for s in signals:
        s['display_status'] = signal_view.display_status(s)
    return jsonify(signals)


@app.route('/api/signals/<signal_id>')
@auth.require_auth
def signal_detail(signal_id, uid):
    sig = storage.get_signal(signal_id)
    if not sig or sig['user_id'] != uid:
        return jsonify({'error': 'غير موجودة'}), 404
    return jsonify(sig)


@app.route('/api/cron/scan-all', methods=['POST'])
def cron_scan_all():
    """
    نقطة دخول للفحص المستمر — يستدعيها Scheduler خارجي (انظر scheduler.py) عبر:
    Authorization: Bearer <CRON_SECRET>. لا تُشغّل شيئاً بدون هذا المفتاح.
    """
    secret = os.environ.get('CRON_SECRET', '')
    if not secret or request.headers.get('Authorization') != f'Bearer {secret}':
        return jsonify({'error': 'غير مصرح'}), 401
    import scheduler as scheduler_module
    result = scheduler_module.run_all_active_strategies(fetcher, analyzer)
    return jsonify(result)


@app.route('/api/ai-explain/<symbol>')
def ai_explain(symbol):
    """تفسير AI عند الطلب لسهم واحد (بيانات سوق عامة، لا علاقة لها بعزل المستخدمين)."""
    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'
    import data_quality
    data = fetcher.get_stock_data(sym, mkt)
    quality = data_quality.validate(data, mkt)
    if not quality['valid']:
        return jsonify({'error': 'data_unavailable', 'reason': quality['reason']})

    analysis = analyzer.full_analysis(data['prices'])
    indicators = analysis['indicators']
    volume_ratio = (data.get('volume', 0) / data.get('avg_volume', 1)) if data.get('avg_volume') else 1.0
    rec = analyzer.get_recommendation(analysis)

    technical_payload = {
        'symbol': sym, 'price': data.get('current'), 'rsi': indicators.get('rsi'),
        'sma_50': indicators.get('sma_50'), 'sma_200': indicators.get('sma_200'),
        'macd_histogram': indicators.get('macd', {}).get('histogram'),
        'volume_ratio': round(volume_ratio, 2), 'score_100': rec.get('score_100'),
    }
    hist_payload = None
    try:
        yahoo_sym = f'{sym}.SR' if mkt == 'saudi' else sym
        res5y = _get_yahoo_with_retry(yahoo_sym, range_period='5y', interval='1d')
        if res5y:
            prices5y = fetcher._build_df_yahoo(res5y)
            if prices5y:
                import historical_analyzer
                hist_payload = historical_analyzer.analyze(prices5y)
    except Exception as e:
        print(f"historical fetch error: {e}")

    force = request.args.get('refresh') == '1'
    import ai_engine as _ai
    result = _ai.explain_full(sym, technical_payload, news_payload=None,
                               historical_payload=hist_payload, force_refresh=force)
    return jsonify(result)


@app.route('/api/capabilities')
def api_capabilities():
    """صدق البيانات: لا نوهم الواجهة بدعم Timeframes غير موجودة فعلياً."""
    return jsonify({
        'data_source': 'Yahoo Finance (unofficial public endpoint) — لا SLA رسمي، عرضة للانقطاع',
        'delayed': True,
        'supported_timeframes': ['1D'],
        'unsupported_timeframes_note': '5m/15m/1h/4h غير مدعومة حالياً — تحتاج Data Provider مختص بالبيانات اللحظية',
        'markets': ['saudi', 'us'],
    })


@app.route('/api/dashboard-summary')
@auth.require_auth
def dashboard_summary(uid):
    """
    كل رقم هنا محسوب في الـBackend من بيانات حقيقية فقط — لا Mock Data.
    لو ما فيه بيانات لجزء معيّن (مثلاً Watchlist فاضية)، نرجع قائمة فاضية والواجهة تعرض
    'No data available' بدل اختلاق أرقام.
    """
    import market_hours
    counts = storage.dashboard_counts(uid)

    top_signals_raw = storage.list_signals(uid, status='ACTIVE', limit=20)
    top_signals_raw.sort(key=lambda s: s['score'] or 0, reverse=True)
    top_opportunities = [{
        'signal_id': s['signal_id'], 'symbol': s['symbol'], 'market': s['market'],
        'score': s['score'], 'display_status': signal_view.display_status(s),
        'trigger_price': s['trigger_price'], 'strategy_name': s['strategy_name'],
        'satisfied_conditions': s.get('conditions') or [],
    } for s in top_signals_raw[:10]]

    latest_alerts = [{
        'created_at': a['created_at'], 'symbol': a['symbol'], 'strategy_name': a['strategy_name'],
        'score': a['score'],
    } for a in storage.get_alert_history(uid, limit=10)]

    watchlist_raw = storage.get_watchlist(uid)
    watchlist = []
    for w in watchlist_raw:
        data = fetcher.get_stock_data(w['symbol'], w['market'])
        active_signal = next((s for s in top_signals_raw if s['symbol'] == w['symbol']), None)
        watchlist.append({
            'symbol': w['symbol'], 'market': w['market'],
            'price': data.get('current') if data else None,
            'data_timestamp': data.get('last_bar_timestamp') if data else None,
            'active_signal_score': active_signal['score'] if active_signal else None,
            'active_strategy': active_signal['strategy_name'] if active_signal else None,
        })

    return jsonify({
        'market_status': {'saudi': market_hours.market_status('saudi'), 'us': market_hours.market_status('us')},
        'counts': counts,
        'top_opportunities': top_opportunities,
        'latest_alerts': latest_alerts,
        'watchlist': watchlist,
        'active_strategies': storage.signals_per_strategy(uid),
        'data_capabilities': {'supported_timeframes': ['1D'], 'delayed': True,
                               'data_source': 'Yahoo Finance (unofficial)'},
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
