"""
Opportunity Scanner + Alert Engine (State Machine)
====================================================
الترتيب الصحيح حسب التصميم:
  500 سهم → Python scanner → عدد قليل من المرشحين → AI (فقط للمرشحين الجدد، وليس كل مرة)

حالات الإشارة: NOT_TRIGGERED → TRIGGERED → ACTIVE → RESET → (تتكرر)
مع Cooldown يمنع تكرار التنبيه لنفس الحدث خلال فترة محددة.
"""
from datetime import datetime, timedelta
import storage
import strategy_engine
import historical_analyzer
import fibonacci_engine
import ai_engine
import data_quality
from data_fetcher import _get_yahoo_with_retry

DEFAULT_COOLDOWN_MINUTES = 30
DEFAULT_SAUDI_SYMBOLS = ['2222','1180','1120','2010','1010','3020','2350','8280','2050','1211',
                         '4200','2220','1060','1150','2380','4230','2360','1140','3001','3002']
DEFAULT_US_SYMBOLS = ['AAPL','MSFT','GOOGL','AMZN','META','TSLA','NVDA','JPM','JNJ','V',
                      'PG','HD','MA','UNH','BAC','XOM','CVX','DIS','NFLX','AMD']


def _cooldown_ok(state_row, cooldown_minutes):
    if not state_row or not state_row.get('last_notified_at'):
        return True
    last = datetime.fromisoformat(state_row['last_notified_at'])
    return datetime.now() - last >= timedelta(minutes=cooldown_minutes)


def build_snapshot(symbol, data, analysis, ctx, score_result):
    """Snapshot يُحفظ وقت التنبيه بالضبط — لا يتغير لاحقاً حتى لو تغيرت بيانات السوق (البند 35)."""
    return {
        'symbol': symbol, 'price': data.get('current'), 'currency': data.get('currency'),
        'change_pct': data.get('change'), 'rsi': ctx['rsi'],
        'sma_20': ctx['sma_20'], 'sma_50': ctx['sma_50'], 'sma_200': ctx['sma_200'],
        'macd': ctx['macd'], 'signal': ctx['signal'], 'histogram': ctx['histogram'],
        'volume_ratio': round(ctx['volume_ratio'], 2), 'support': ctx['support'],
        'resistance': ctx['resistance'], 'fibonacci': ctx.get('fibonacci'),
        'score_100': score_result['score_100'],
        'score_label': score_result['score_label'],
        'triggered_conditions': score_result['satisfied'],
        'timestamp': datetime.now().isoformat(),
    }


def evaluate_symbol(strategy, symbol, market, fetcher, analyzer, user_id='default',
                     with_ai=True, force_ai=False):
    """
    يفحص سهماً واحداً ضد استراتيجية واحدة، يدير حالة التنبيه، ويرجع نتيجة كاملة
    (أو None إذا تعذر جلب البيانات — Data Unavailable وليس 'لا توجد فرصة'، البند 44).
    """
    # -------- Data Quality Check: Fetch -> Validate -> Normalize -> Strategy --------
    data = fetcher.get_stock_data(symbol, market)
    quality = data_quality.validate(data, market)
    if not quality['valid']:
        # لا يُنشأ Signal أبداً من بيانات فاشلة/قديمة — هذا مقصود وليس خطأً
        return {'symbol': symbol, 'error': 'data_unavailable', 'reason': quality['reason']}

    analysis = analyzer.full_analysis(data['prices'])
    indicators = analysis['indicators']
    volume_ratio = (data.get('volume', 0) / data.get('avg_volume', 1)) if data.get('avg_volume') else 1.0
    fib = fibonacci_engine.analyze(data['prices'], data.get('current', analysis['current_price']))

    ctx = strategy_engine.build_context(
        current_price=data.get('current', analysis['current_price']),
        change_pct=data.get('change', 0),
        indicators=indicators, support=analysis['support'],
        resistance=analysis['resistance'], volume_ratio=volume_ratio, fibonacci=fib)

    prev_state = storage.get_alert_state(user_id, strategy['id'], symbol)
    prev_ctx = prev_state['last_snapshot'] if prev_state else None

    result = strategy_engine.run_strategy(strategy['conditions'], ctx, prev_ctx)
    current_state = prev_state['state'] if prev_state else 'NOT_TRIGGERED'

    new_state, alert_created, ai_explanation, ai_status, signal_id = current_state, None, None, 'skip', None
    cooldown_ok = _cooldown_ok(prev_state, DEFAULT_COOLDOWN_MINUTES)

    if result['triggered'] and current_state in ('NOT_TRIGGERED', 'RESET') and cooldown_ok:
        # حدث جديد -> ننشئ الإشارة والتنبيه دائماً (بغض النظر عن نجاح AI)، ونستدعي AI حسب فلتر الدرجة فقط
        snapshot = build_snapshot(symbol, data, analysis, ctx, result)
        new_state = 'ACTIVE'
        entry, confirmation, invalidation, exit_ = strategy_engine.derive_lifecycle_conditions(
            strategy, ctx, prev_ctx, result)

        gate = ai_engine.ai_gate(result['score_100'])
        ai_status = gate
        if with_ai and gate in ('auto', 'priority'):
            try:
                technical_payload = {
                    'symbol': symbol, 'price': snapshot['price'], 'rsi': snapshot['rsi'],
                    'sma_50': snapshot['sma_50'], 'sma_200': snapshot['sma_200'],
                    'macd_histogram': snapshot['histogram'], 'volume_ratio': snapshot['volume_ratio'],
                    'score_100': snapshot['score_100'], 'triggered_conditions': snapshot['triggered_conditions'],
                    'entry': entry, 'confirmation': confirmation,
                    'invalidation': invalidation, 'exit': exit_,
                }
                hist_payload = None
                try:
                    yahoo_sym = f'{symbol}.SR' if market == 'saudi' else symbol
                    res5y = _get_yahoo_with_retry(yahoo_sym, range_period='5y', interval='1d')
                    if res5y:
                        prices5y = fetcher._build_df_yahoo(res5y)
                        if prices5y:
                            hist_payload = historical_analyzer.analyze(prices5y)
                except Exception as e:
                    print(f"historical fetch error: {e}")

                ai_explanation = ai_engine.explain_full(
                    symbol, technical_payload, news_payload=None,
                    historical_payload=hist_payload, force_refresh=force_ai)
                ai_status = ai_explanation.get('overall_status', 'ok')
            except Exception as e:
                # فشل AI لا يمنع إطلاقاً إنشاء الإشارة/التنبيه الأساسي
                print(f"AI explanation failed for {symbol}: {e}")
                ai_explanation = None
                ai_status = 'failed'

        alert_id = storage.add_alert_history(
            user_id, strategy['id'], strategy['name'], symbol, market, 'entry',
            result['score_100'], result['satisfied'], snapshot, ai_explanation)
        alert_created = alert_id

        signal_id = storage.create_signal(
            user_id, strategy['id'], strategy['name'], strategy.get('version', 1), symbol, market, '1d',
            data.get('last_bar_timestamp'), snapshot['price'], result['score_100'],
            result['satisfied'], snapshot, indicators=ctx,
            entry=entry, confirmation=confirmation, invalidation=invalidation,
            exit_=exit_, ai_explanation=ai_explanation, ai_status=ai_status)

        storage.set_alert_state(user_id, strategy['id'], symbol, new_state,
                                 result['score_100'], ctx, notified=True)

    elif not result['triggered'] and current_state == 'ACTIVE':
        new_state = 'RESET'
        storage.set_alert_state(user_id, strategy['id'], symbol, new_state, result['score_100'], ctx)
    else:
        storage.set_alert_state(user_id, strategy['id'], symbol, current_state, result['score_100'], ctx)

    return {
        'symbol': symbol, 'market': market, 'price': data.get('current'),
        'currency': data.get('currency'), 'change_pct': data.get('change'),
        'triggered': result['triggered'], 'score_100': result['score_100'],
        'score_label': result['score_label'], 'satisfied': result['satisfied'],
        'unsatisfied': result['unsatisfied'], 'state': new_state,
        'alert_created': alert_created, 'signal_id': signal_id,
        'ai_status': ai_status, 'ai_explanation': ai_explanation,
    }


def run_scan(strategy, fetcher, analyzer, symbols=None, user_id='default', with_ai=True):
    """يفحص قائمة أسهم كاملة ضد استراتيجية، ويرجع فقط المرشحين (Candidates) + إحصائية عامة."""
    if symbols is None:
        symbols = DEFAULT_SAUDI_SYMBOLS if strategy['market'] == 'saudi' else DEFAULT_US_SYMBOLS

    candidates, unavailable, scanned = [], [], 0
    for sym in symbols:
        try:
            r = evaluate_symbol(strategy, sym, strategy['market'], fetcher, analyzer, user_id, with_ai)
            if r.get('error') == 'data_unavailable':
                unavailable.append(sym)
                continue
            scanned += 1
            if r['triggered']:
                candidates.append(r)
        except Exception as e:
            print(f"scan error {sym}: {e}")
            unavailable.append(sym)

    candidates.sort(key=lambda c: c['score_100'], reverse=True)
    return {
        'strategy_id': strategy['id'], 'strategy_name': strategy['name'],
        'scanned_count': scanned, 'candidates': candidates,
        'unavailable': unavailable, 'scanned_at': datetime.now().isoformat(),
    }
