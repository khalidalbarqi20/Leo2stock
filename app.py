from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os, threading
from datetime import datetime, timedelta

from data_fetcher import StockDataFetcher
from technical_analysis import TechnicalAnalyzer
from report_generator import ReportGenerator
from backtesting import BacktestingEngine
from risk_manager import RiskManager
from news_analyzer import NewsAnalyzer
from multi_timeframe import MultiTimeframeAnalyzer
from alert_system import AlertSystem

app = Flask(__name__)
CORS(app)

fetcher = StockDataFetcher()
analyzer = TechnicalAnalyzer()
reporter = ReportGenerator()
backtester = BacktestingEngine(analyzer)
risk_manager = RiskManager()
news_analyzer = NewsAnalyzer()
mtf_analyzer = MultiTimeframeAnalyzer(fetcher)
alert_system = AlertSystem(fetcher, analyzer, news_analyzer)

# ── كاش قوي ──
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
    """إزالة DataFrame قبل الإرسال"""
    return {k: v for k, v in data.items() if k != 'prices'}

# ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ── تحليل سهم ────────────────────────────────────────────
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

        # بيانات الرسوم البيانية
        chart_data = analyzer.get_chart_data(data['prices'])
        prices_arr = fetcher.prices_to_array(data['prices'])

        # استخراج التواريخ
        dates_list = []
        for p in prices_arr:
            dates_list.append(p['date'])

        # Calculate Fibonacci levels
        fibonacci = analyzer.calculate_fibonacci(data['prices'])

        # Risk Analysis
        risk_analysis = risk_manager.calculate_risk_reward(
            data['current'],
            analysis['targets']['target_1'],
            analysis['targets']['stop_loss']
        )

        # News Analysis
        news_data = news_analyzer.get_news(sym, mkt, limit=5)

        # Multi-timeframe Analysis
        mtf_data = mtf_analyzer.analyze_all_timeframes(sym, mkt)

        result = {
            **safe_data(data),
            'analysis': analysis,
            'recommendation': rec,
            'prices_arr': prices_arr,
            'dates_list': dates_list,
            'fibonacci': fibonacci,
            'risk_analysis': risk_analysis,
            'news': news_data,
            'multi_timeframe': mtf_data,
            **chart_data,
        }
        cache_set(key, result, minutes=10)
        return jsonify(result)
    except Exception as e:
        import traceback
        print(f"Error analyze {symbol}: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'خطأ في التحليل: {str(e)}'})

# ── بيانات الرسم البياني لفترة محددة ─────────────────────
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

        # تصفية حسب الفترة
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

# ── تقرير PDF ─────────────────────────────────────────────
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

# ── مؤشرات رئيسية ─────────────────────────────────────────
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

# ── مسح RSI ──────────────────────────────────────────
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
                        'symbol': cd.get('symbol'),
                        'name': cd.get('name'),
                        'price': cd.get('current'),
                        'change': cd.get('change'),
                        'currency': cd.get('currency'),
                        'rsi': rsi,
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
                results.append({
                    **safe_data(data),
                    'rsi': rsi,
                    'recommendation': rec,
                })
        except:
            continue

    results.sort(key=lambda x: x.get('rsi', 100))
    cache_set(key, results, minutes=30)
    return jsonify(results)

# ── فرص الدخول ────────────────────────────────────────────
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
            return {**safe_data(data), 'analysis': an,
                    'recommendation': rec, 'score': rec.get('score', 0)}
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

# ── نظرة السوق ────────────────────────────────────────────
@app.route('/api/market-overview')
def market_overview():
    key = "market_overview"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    symbols = {'saudi': ['2222', '1180', '8280', '2350'], 'us': ['AAPL', 'TSLA', 'NVDA', 'MSFT']}
    overview = {}
    for mkt, syms in symbols.items():
        overview[mkt] = []
        for sym in syms:
            try:
                data = fetcher.get_stock_data(sym, mkt)
                if data:
                    overview[mkt].append({
                        'symbol': data['symbol'],
                        'price': data['current'],
                        'change': data['change'],
                        'name': data['name'],
                        'currency': data['currency']
                    })
            except:
                continue

    cache_set(key, overview, minutes=15)
    return jsonify(overview)

# ── بحث سريع ──────────────────────────────────────────────
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

# ═══════════════════════════════════════════════════════════
# ═══ المرحلة الثانية: Backtesting API ═══════════════════
# ═══════════════════════════════════════════════════════════

@app.route('/api/backtest/<symbol>')
def backtest_stock(symbol):
    """تشغيل Backtest على سهم"""
    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'

    strategy = request.args.get('strategy', 'sma_cross')
    initial_capital = float(request.args.get('capital', 10000))
    stop_loss = float(request.args.get('stop_loss', 0.05))
    take_profit = float(request.args.get('take_profit', 0.10))

    key = f"backtest_{sym}_{mkt}_{strategy}_{initial_capital}_{stop_loss}_{take_profit}"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    data = fetcher.get_stock_data(sym, mkt)
    if not data:
        return jsonify({'error': 'تعذّر جلب البيانات'})

    try:
        result = backtester.run_backtest(
            data['prices'],
            strategy=strategy,
            initial_capital=initial_capital,
            stop_loss_pct=stop_loss,
            take_profit_pct=take_profit
        )

        if 'error' in result:
            return jsonify(result)

        # Add metadata
        result['symbol'] = sym
        result['market'] = mkt
        result['strategy_name'] = backtester.STRATEGIES.get(strategy, strategy)
        result['strategy_key'] = strategy

        cache_set(key, result, minutes=30)
        return jsonify(result)
    except Exception as e:
        import traceback
        print(f"Backtest error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'خطأ في الـ Backtest: {str(e)}'})

@app.route('/api/backtest-compare/<symbol>')
def backtest_compare(symbol):
    """مقارنة جميع الاستراتيجيات"""
    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'

    key = f"backtest_compare_{sym}_{mkt}"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    data = fetcher.get_stock_data(sym, mkt)
    if not data:
        return jsonify({'error': 'تعذّر جلب البيانات'})

    try:
        results = backtester.compare_strategies(data['prices'])

        comparison = {
            'symbol': sym,
            'market': mkt,
            'strategies': results,
            'best_strategy': None,
            'best_return': -float('inf')
        }

        for key, result in results.items():
            if result.get('total_return_pct', -999) > comparison['best_return']:
                comparison['best_return'] = result['total_return_pct']
                comparison['best_strategy'] = key

        cache_set(f"backtest_compare_{sym}_{mkt}", comparison, minutes=30)
        return jsonify(comparison)
    except Exception as e:
        return jsonify({'error': f'خطأ في المقارنة: {str(e)}'})

@app.route('/api/backtest-strategies')
def backtest_strategies():
    """قائمة الاستراتيجيات المتاحة"""
    return jsonify({
        'strategies': [
            {'key': k, 'name': v} for k, v in backtester.STRATEGIES.items()
        ]
    })

# ═══════════════════════════════════════════════════════════
# ═══ المرحلة الثانية: Risk Management API ═════════════════
# ═══════════════════════════════════════════════════════════

@app.route('/api/risk/position-size', methods=['POST'])
def calculate_position_size():
    """حساب حجم المركز المثالي"""
    data = request.get_json() or {}

    account_balance = float(data.get('account_balance', 10000))
    entry_price = float(data.get('entry_price', 100))
    stop_loss = float(data.get('stop_loss', 95))
    risk_per_trade = float(data.get('risk_per_trade', 0.02))
    max_position_pct = float(data.get('max_position_pct', 0.25))

    result = risk_manager.calculate_position_size(
        account_balance, entry_price, stop_loss,
        risk_per_trade, max_position_pct
    )
    return jsonify(result)

@app.route('/api/risk/kelly', methods=['POST'])
def calculate_kelly():
    """حساب Kelly Criterion"""
    data = request.get_json() or {}

    win_rate = float(data.get('win_rate', 0.5))
    avg_win_pct = float(data.get('avg_win_pct', 5))
    avg_loss_pct = float(data.get('avg_loss_pct', 3))

    result = risk_manager.calculate_kelly_criterion(win_rate, avg_win_pct, avg_loss_pct)
    return jsonify(result)

@app.route('/api/risk/risk-reward', methods=['POST'])
def calculate_risk_reward():
    """حساب Risk/Reward Ratio"""
    data = request.get_json() or {}

    entry_price = float(data.get('entry_price', 100))
    target_price = float(data.get('target_price', 110))
    stop_loss_price = float(data.get('stop_loss_price', 95))

    result = risk_manager.calculate_risk_reward(entry_price, target_price, stop_loss_price)
    return jsonify(result)

@app.route('/api/risk/stop-loss', methods=['POST'])
def calculate_stop_loss():
    """حساب وقف الخسارة"""
    data = request.get_json() or {}

    entry_price = float(data.get('entry_price', 100))
    atr = float(data.get('atr', 2))
    method = data.get('method', 'atr')
    multiplier = float(data.get('multiplier', 2.0))
    support_level = data.get('support_level')
    recent_low = data.get('recent_low')

    result = risk_manager.calculate_stop_loss(
        entry_price, atr, method, multiplier,
        support_level, recent_low
    )
    return jsonify(result)

@app.route('/api/risk/trailing-stop', methods=['POST'])
def calculate_trailing_stop():
    """حساب Trailing Stop"""
    data = request.get_json() or {}

    current_price = float(data.get('current_price', 100))
    highest_price = float(data.get('highest_price', 110))
    trailing_pct = float(data.get('trailing_pct', 0.10))
    atr = data.get('atr')
    atr_multiplier = float(data.get('atr_multiplier', 3.0))

    result = risk_manager.calculate_trailing_stop(
        current_price, highest_price, trailing_pct,
        atr, atr_multiplier
    )
    return jsonify(result)

@app.route('/api/risk/portfolio', methods=['POST'])
def portfolio_risk_analysis():
    """تحليل مخاطر المحفظة"""
    data = request.get_json() or {}

    positions = data.get('positions', [])
    account_balance = float(data.get('account_balance', 10000))

    result = risk_manager.portfolio_risk_analysis(positions, account_balance)
    return jsonify(result)

@app.route('/api/risk/monte-carlo', methods=['POST'])
def monte_carlo_simulation():
    """محاكاة Monte Carlo"""
    data = request.get_json() or {}

    historical_returns = data.get('historical_returns', [])
    initial_capital = float(data.get('initial_capital', 10000))
    num_simulations = int(data.get('num_simulations', 1000))
    num_days = int(data.get('num_days', 252))

    result = risk_manager.monte_carlo_simulation(
        historical_returns, initial_capital, num_simulations, num_days
    )
    return jsonify(result)

# ═══════════════════════════════════════════════════════════
# ═══ المرحلة الثانية: News & Sentiment API ════════════════
# ═══════════════════════════════════════════════════════════

@app.route('/api/news/<symbol>')
def get_stock_news(symbol):
    """جلب أخبار السهم"""
    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'
    limit = int(request.args.get('limit', 10))

    key = f"news_{sym}_{mkt}_{limit}"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    try:
        result = news_analyzer.get_news(sym, mkt, limit)
        cache_set(key, result, minutes=15)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/news/market-sentiment')
def get_market_sentiment():
    """جلب المشاعر العامة للسوق"""
    key = "market_sentiment"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    try:
        result = news_analyzer.get_market_sentiment()
        cache_set(key, result, minutes=30)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/news/sector/<sector>')
def get_sector_news(sector):
    """جلب أخبار القطاع"""
    limit = int(request.args.get('limit', 5))

    try:
        result = news_analyzer.get_sector_news(sector, limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/news/earnings/<symbol>')
def get_earnings_calendar(symbol):
    """جلب تقويم الأرباح"""
    sym = symbol.upper().replace('.SR', '')

    try:
        result = news_analyzer.get_earnings_calendar(sym)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/news/insider/<symbol>')
def get_insider_sentiment(symbol):
    """جلب مشاعر التداول الداخلي"""
    sym = symbol.upper().replace('.SR', '')

    try:
        result = news_analyzer.get_insider_sentiment(sym)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

# ═══════════════════════════════════════════════════════════
# ═══ المرحلة الثانية: Multi-Timeframe API ═════════════════
# ═══════════════════════════════════════════════════════════

@app.route('/api/multi-timeframe/<symbol>')
def get_multi_timeframe(symbol):
    """تحليل متعدد الفريمات الزمنية"""
    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'

    key = f"mtf_{sym}_{mkt}"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    try:
        result = mtf_analyzer.analyze_all_timeframes(sym, mkt)
        cache_set(key, result, minutes=20)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

# ═══════════════════════════════════════════════════════════
# ═══ المرحلة الثانية: Alerts API ══════════════════════════
# ═══════════════════════════════════════════════════════════

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """جلب قائمة التنبيهات"""
    symbol = request.args.get('symbol')
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    return jsonify(alert_system.get_alerts(symbol, active_only))

@app.route('/api/alerts', methods=['POST'])
def create_alert():
    """إنشاء تنبيه جديد"""
    data = request.get_json() or {}

    alert = alert_system.add_alert(
        symbol=data.get('symbol', ''),
        alert_type=data.get('alert_type', 'price_above'),
        threshold=float(data.get('threshold', 0)),
        market=data.get('market', 'us'),
        message=data.get('message'),
        enabled=data.get('enabled', True),
        one_time=data.get('one_time', True)
    )
    return jsonify(alert)

@app.route('/api/alerts/<alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """حذف تنبيه"""
    alert_system.remove_alert(alert_id)
    return jsonify({'success': True})

@app.route('/api/alerts/<alert_id>/toggle', methods=['POST'])
def toggle_alert(alert_id):
    """تفعيل/تعطيل تنبيه"""
    alert = alert_system.toggle_alert(alert_id)
    if alert:
        return jsonify(alert)
    return jsonify({'error': 'التنبيه غير موجود'})

@app.route('/api/alerts/smart', methods=['POST'])
def create_smart_alerts():
    """إنشاء تنبيهات ذكية"""
    data = request.get_json() or {}
    symbol = data.get('symbol', '')
    market = data.get('market', 'us')

    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'

    stock_data = fetcher.get_stock_data(sym, mkt)
    if not stock_data:
        return jsonify({'error': 'تعذّر جلب البيانات'})

    analysis = analyzer.full_analysis(stock_data['prices'])

    alerts = alert_system.create_smart_alerts(sym, mkt, stock_data, analysis)
    return jsonify({'alerts_created': alerts, 'count': len(alerts)})

@app.route('/api/alerts/stats')
def get_alert_stats():
    """إحصائيات التنبيهات"""
    return jsonify(alert_system.get_alert_stats())

@app.route('/api/alerts/history')
def get_alert_history():
    """سجل التنبيهات"""
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 50))
    return jsonify(alert_system.get_alert_history(symbol, limit))

# ═══════════════════════════════════════════════════════════
# ═══ المرحلة الثانية: Combined Analysis API ═══════════════
# ═══════════════════════════════════════════════════════════

@app.route('/api/full-analysis/<symbol>')
def full_analysis(symbol):
    """تحليل شامل يجمع كل الميزات"""
    sym = symbol.upper().replace('.SR', '')
    mkt = 'saudi' if sym.isdigit() else 'us'

    key = f"full_analysis_{sym}_{mkt}"
    cached = cache_get(key)
    if cached:
        return jsonify(cached)

    data = fetcher.get_stock_data(sym, mkt)
    if not data:
        return jsonify({'error': 'تعذّر جلب البيانات'})

    try:
        # Technical Analysis
        analysis = analyzer.full_analysis(data['prices'])
        rec = analyzer.get_recommendation(analysis)

        # Risk Analysis
        risk = risk_manager.calculate_risk_reward(
            data['current'],
            analysis['targets']['target_1'],
            analysis['targets']['stop_loss']
        )

        # Position Size Recommendation
        position_size = risk_manager.calculate_position_size(
            10000, data['current'], analysis['targets']['stop_loss']
        )

        # News
        news = news_analyzer.get_news(sym, mkt, limit=5)

        # Multi-timeframe
        mtf = mtf_analyzer.analyze_all_timeframes(sym, mkt)

        # Backtest (quick SMA cross)
        backtest = backtester.run_backtest(data['prices'], strategy='sma_cross', 
                                           initial_capital=10000)

        # Market Sentiment
        market_sentiment = news_analyzer.get_market_sentiment()

        result = {
            'symbol': sym,
            'market': mkt,
            'price_data': safe_data(data),
            'technical_analysis': {
                'indicators': analysis['indicators'],
                'trend': analysis['trend'],
                'support': analysis['support'],
                'resistance': analysis['resistance'],
                'signals': analysis['signals'],
                'targets': analysis['targets'],
            },
            'recommendation': rec,
            'risk_analysis': {
                'risk_reward': risk,
                'position_size': position_size,
            },
            'news_sentiment': news,
            'market_sentiment': market_sentiment,
            'multi_timeframe': mtf,
            'backtest_summary': {
                'strategy': 'SMA Cross',
                'total_return_pct': backtest.get('total_return_pct', 0),
                'win_rate': backtest.get('win_rate', 0),
                'total_trades': backtest.get('total_trades', 0),
                'sharpe_ratio': backtest.get('sharpe_ratio', 0),
            } if 'error' not in backtest else {'error': backtest['error']},
            'generated_at': datetime.now().isoformat(),
        }

        cache_set(key, result, minutes=10)
        return jsonify(result)
    except Exception as e:
        import traceback
        print(f"Full analysis error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'خطأ في التحليل الشامل: {str(e)}'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
