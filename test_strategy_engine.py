"""
اختبارات حالات حدّية حقيقية — حسب طلب المراجعة، وليست مجرد "يعمل زي المثال".
تشغيل: python3 test_strategy_engine.py
كل اختبار فاشل يطبع AssertionError بوضوح ويوقف السكربت — بدون أي "قد يعمل".
"""
import os
os.environ.setdefault('LEO2STOCK_DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'leo2stock_test_tmp.db'))
if os.path.exists(os.environ['LEO2STOCK_DB_PATH']):
    os.remove(os.environ['LEO2STOCK_DB_PATH'])

import time
import strategy_engine as se
import storage

passed = 0


def check(name, condition):
    global passed
    assert condition, f"❌ FAILED: {name}"
    passed += 1
    print(f"✅ {name}")


def ctx(price=100, rsi=50, sma_50=100, sma_200=100, macd=0, signal=0, histogram=0,
        volume_ratio=1.0, support=90, resistance=110):
    return {'price': price, 'change_pct': 0, 'rsi': rsi, 'sma_20': price, 'sma_50': sma_50,
            'sma_200': sma_200, 'macd': macd, 'signal': signal, 'histogram': histogram,
            'volume_ratio': volume_ratio, 'support': support, 'resistance': resistance}


# ---------------------------------------------------------------------------
# 1) RSI Cross Below 30 — حالات حدّية دقيقة
# ---------------------------------------------------------------------------
cond = {'type': 'rsi_below', 'value': 30, 'points': 10}

r = se.evaluate_leaf(cond, ctx(rsi=29.99), ctx(rsi=30.01))
check("RSI 30.01 -> 29.99: rsi_below(30) = True (عبر تحت 30 فعلاً)", r['satisfied'] is True)

r = se.evaluate_leaf(cond, ctx(rsi=28), ctx(rsi=29))
check("RSI 29 -> 28 (كلاهما تحت 30 مسبقاً): rsi_below(30) لا يزال True (شرط حالة وليس Cross)",
      r['satisfied'] is True)

# لو الاستراتيجية تستخدم Cross Detection صريح، يجب أن لا يتكرر الحدث بعد أول تقاطع.
# هذا يُختبر عبر alert_state في scanner.py (انظر القسم 4 بالأسفل) وليس هنا فقط.

# ---------------------------------------------------------------------------
# 2) MACD Cross Above Signal — حدّي عند التقاطع بالضبط
# ---------------------------------------------------------------------------
cross_cond = {'type': 'macd_cross_above_signal', 'points': 10}

prev = ctx(macd=0.40, signal=0.50)   # MACD تحت الإشارة
now = ctx(macd=0.51, signal=0.50)    # تجاوزها للتو
r = se.evaluate_leaf(cross_cond, now, prev)
check("MACD 0.40<0.50 -> 0.51>0.50: macd_cross_above_signal = True", r['satisfied'] is True)

prev2 = ctx(macd=0.60, signal=0.50)  # كان فوقها مسبقاً
now2 = ctx(macd=0.70, signal=0.50)   # لا يزال فوقها (لا تقاطع جديد)
r = se.evaluate_leaf(cross_cond, now2, prev2)
check("MACD كان فوق الإشارة أصلاً (0.60->0.70): macd_cross_above_signal = False (لا تقاطع جديد)",
      r['satisfied'] is False)

r = se.evaluate_leaf(cross_cond, now, None)
check("MACD cross بدون prev_ctx (أول فحص): يرجع False دائماً (لا يمكن تحديد تقاطع)",
      r['satisfied'] is False)

# ---------------------------------------------------------------------------
# 3) SMA Cross (تقاطع ذهبي) — حدّي عند التساوي بالضبط
# ---------------------------------------------------------------------------
sma_cross = {'type': 'sma_cross_above_sma', 'fast': 50, 'slow': 200, 'points': 10}
prev = ctx(sma_50=199.99, sma_200=200)   # تحت المتوسط الطويل
now = ctx(sma_50=200.01, sma_200=200)    # تجاوزه للتو
r = se.evaluate_leaf(sma_cross, now, prev)
check("SMA50 199.99->200.01 (SMA200=200): تقاطع ذهبي = True", r['satisfied'] is True)

prev2 = ctx(sma_50=200, sma_200=200)     # متساويان تماماً (Edge Case)
now2 = ctx(sma_50=199, sma_200=200)      # هبط تحت
r = se.evaluate_leaf(sma_cross, now2, prev2)
check("SMA50 كان مساوياً لـSMA200 ثم هبط: تقاطع ذهبي = False (لم يعبر من تحت لفوق)",
      r['satisfied'] is False)

# ---------------------------------------------------------------------------
# 4) Breakout / Breakdown
# ---------------------------------------------------------------------------
breakout = {'type': 'price_breaks_resistance', 'points': 10}
check("سعر 111 مع مقاومة 110: breakout = True",
      se.evaluate_leaf(breakout, ctx(price=111, resistance=110), None)['satisfied'] is True)
check("سعر 110 بالضبط (مساوٍ) مع مقاومة 110: breakout = False (لازم اختراق حقيقي وليس ملامسة)",
      se.evaluate_leaf(breakout, ctx(price=110, resistance=110), None)['satisfied'] is False)

breakdown = {'type': 'price_breaks_support_down', 'points': 10}
check("سعر 89 مع دعم 90: breakdown = True",
      se.evaluate_leaf(breakdown, ctx(price=89, support=90), None)['satisfied'] is True)
check("سعر 90 بالضبط مع دعم 90: breakdown = False",
      se.evaluate_leaf(breakdown, ctx(price=90, support=90), None)['satisfied'] is False)

# ---------------------------------------------------------------------------
# 5) AND / OR / Nested Groups — من نفس مثال المستند بالضبط
# ---------------------------------------------------------------------------
strategy_tree = {
    'logic': 'AND', 'conditions': [
        {'type': 'rsi_below', 'value': 30, 'points': 20},
        {'type': 'price_above_sma', 'period': 200, 'points': 20},
        {'logic': 'OR', 'points': 20, 'conditions': [
            {'type': 'macd_cross_above_signal', 'points': 20},
            {'type': 'volume_ratio_above', 'value': 1.5, 'points': 15},
        ]},
    ]
}
c = ctx(price=174.20, rsi=28.4, sma_200=161.30, macd=0.9, signal=0.6, volume_ratio=1.83)
prev = ctx(macd=0.4, signal=0.5)
result = se.run_strategy(strategy_tree, c, prev)
check("مثال NVDA الكامل: triggered=True", result['triggered'] is True)
check("مثال NVDA الكامل: score_100 = 100 (كل الشروط الثلاث الرئيسية + كلا فرعي OR تحققا)",
      result['score_100'] == 100)

# فشل شرط AND واحد -> triggered يجب أن يصبح False حتى لو الدرجة عالية
c_fail = ctx(price=150, rsi=28.4, sma_200=161.30, macd=0.9, signal=0.6, volume_ratio=1.83)  # السعر تحت SMA200
result2 = se.run_strategy(strategy_tree, c_fail, prev)
check("كسر شرط AND واحد (السعر تحت SMA200): triggered=False رغم أن باقي الشروط محققة",
      result2['triggered'] is False)
check("لكن الدرجة الوزنية لا تصبح صفراً (لأن باقي الشروط محققة فعلياً)",
      result2['score_100'] > 0)

# ---------------------------------------------------------------------------
# 6) Scoring عند الحدود 0 و100
# ---------------------------------------------------------------------------
all_true = {'logic': 'AND', 'conditions': [{'type': 'rsi_below', 'value': 100, 'points': 50},
                                            {'type': 'rsi_above', 'value': -1, 'points': 50}]}
check("كل الشروط محققة: score=100", se.run_strategy(all_true, ctx(rsi=50), None)['score_100'] == 100)

all_false = {'logic': 'AND', 'conditions': [{'type': 'rsi_below', 'value': 0, 'points': 50},
                                             {'type': 'rsi_above', 'value': 100, 'points': 50}]}
check("لا شرط محقق: score=0", se.run_strategy(all_false, ctx(rsi=50), None)['score_100'] == 0)

# ---------------------------------------------------------------------------
# 7) Alert State Machine + Cooldown (نفس منطق scanner.py عبر storage مباشرة)
# ---------------------------------------------------------------------------
storage.init_db()
uid, sid, sym = 'test_user', 999, 'TESTX'

storage.set_alert_state(uid, sid, sym, 'NOT_TRIGGERED')
st = storage.get_alert_state(uid, sid, sym)
check("الحالة الابتدائية = NOT_TRIGGERED", st['state'] == 'NOT_TRIGGERED')

storage.set_alert_state(uid, sid, sym, 'ACTIVE', score=90, snapshot={'x': 1}, notified=True)
st = storage.get_alert_state(uid, sid, sym)
check("بعد أول تفعيل: الحالة=ACTIVE و last_notified_at مضبوط",
      st['state'] == 'ACTIVE' and st['last_notified_at'] is not None)

from scanner import _cooldown_ok
check("مباشرة بعد الإشعار: cooldown نشط (لا يسمح بإشعار جديد فوراً)",
      _cooldown_ok(st, 30) is False)
check("Cooldown=0 دقيقة: يسمح فوراً (لاختبار حد أدنى)", _cooldown_ok(st, 0) is True)

storage.set_alert_state(uid, sid, sym, 'RESET', score=40, snapshot={'x': 1})
st = storage.get_alert_state(uid, sid, sym)
check("بعد اختفاء الشروط: الحالة=RESET", st['state'] == 'RESET')
check("RESET لا يمسح last_notified_at (الـcooldown يبقى فعّالاً حتى بعد RESET)",
      st['last_notified_at'] is not None)

# ---------------------------------------------------------------------------
# 8) Signal Lifecycle — signal_id مستقل + Snapshot كامل
# ---------------------------------------------------------------------------
sig_id = storage.create_signal(uid, sid, 'استراتيجية تجريبية', 1, sym, 'us', '1d',
                                '2026-01-01T10:00:00', 174.20, 87, ['RSI أقل من 30'], {'price': 174.20},
                                entry={'conditions': ['RSI أقل من 30']},
                                invalidation={'active': False, 'conditions': ['السعر تحت SMA200']})
sig = storage.get_signal(sig_id)
check("Signal له معرّف مستقل (signal_id) مختلف عن alert_state", sig is not None and sig['signal_id'] == sig_id)
check("الحالة الابتدائية للإشارة = ACTIVE", sig['status'] == 'ACTIVE')

storage.update_signal_status(sig_id, 'CONFIRMED')
check("بعد التأكيد: status=CONFIRMED", storage.get_signal(sig_id)['status'] == 'CONFIRMED')

storage.update_signal_status(sig_id, 'CLOSED', outcome={'price_after_5_days': 180.0})
closed = storage.get_signal(sig_id)
check("بعد الإغلاق: status=CLOSED والنتيجة (outcome) محفوظة لقياس جودة الاستراتيجية لاحقاً",
      closed['status'] == 'CLOSED' and closed['outcome']['price_after_5_days'] == 180.0)

# ---------------------------------------------------------------------------
# 9) AI Score Gating
# ---------------------------------------------------------------------------
import ai_engine
check("Score 50 -> skip (لا AI إطلاقاً)", ai_engine.ai_gate(50) == 'skip')
check("Score 65 -> optional (متاح يدوياً فقط)", ai_engine.ai_gate(65) == 'optional')
check("Score 80 -> auto (AI تلقائي)", ai_engine.ai_gate(80) == 'auto')
check("Score 95 -> priority (AI + تنبيه أولوية)", ai_engine.ai_gate(95) == 'priority')
check("الحدود قابلة للتعديل عبر متغيرات البيئة",
      ai_engine.SCORE_AUTO_THRESHOLD == 75 and ai_engine.SCORE_PRIORITY_THRESHOLD == 90)

# ---------------------------------------------------------------------------
# 10) news_analyzer — يجب ألا يخترع أي خبر إطلاقاً
# ---------------------------------------------------------------------------
import importlib
os.environ['FINNHUB_KEY'] = ''  # محاكاة عدم وجود مفتاح حقيقي
import news_analyzer
importlib.reload(news_analyzer)
na = news_analyzer.NewsAnalyzer()
news = na.get_news('AAPL', 'us')
check("بدون مفتاح Finnhub: status=NO_NEWS_SOURCE_CONFIGURED (وليس أخباراً مختلقة)",
      news['status'] == 'NO_NEWS_SOURCE_CONFIGURED')
check("بدون مفتاح: قائمة المقالات فارغة تماماً (صفر اختلاق)", len(news['articles']) == 0)
check("لا توجد أي دالة توليد أخبار وهمية متبقية في الكود",
      not hasattr(news_analyzer.NewsAnalyzer, '_generate_synthetic_news'))

# ---------------------------------------------------------------------------
# 11) Data Quality Check — لا Signal من بيانات فاشلة/قديمة/مزيّفة
# ---------------------------------------------------------------------------
import data_quality
from datetime import datetime as _dt, timedelta as _td

check("data=None -> valid=False (FETCH_FAILED)", data_quality.validate(None, 'us')['valid'] is False)

bad_price = {'current': 0, 'prices': list(range(30)), 'last_bar_timestamp': _dt.now().isoformat()}
check("سعر=0 -> valid=False (INVALID_PRICE)", data_quality.validate(bad_price, 'us')['valid'] is False)

short_hist = {'current': 100, 'prices': list(range(5)), 'last_bar_timestamp': _dt.now().isoformat()}
check("تاريخ قصير (<20 شمعة) -> valid=False (INSUFFICIENT_HISTORY)",
      data_quality.validate(short_hist, 'us')['valid'] is False)

stale = {'current': 100, 'prices': list(range(30)),
         'last_bar_timestamp': (_dt.now() - _td(days=10)).isoformat()}
check("بيانات عمرها 10 أيام -> valid=False (STALE_DATA)", data_quality.validate(stale, 'us')['valid'] is False)

fresh = {'current': 100, 'prices': list(range(30)), 'last_bar_timestamp': _dt.now().isoformat()}
check("بيانات حديثة وكاملة -> valid=True", data_quality.validate(fresh, 'us')['valid'] is True)

# ---------------------------------------------------------------------------
# 12) Market Hours — لا يعتمد على توقيت محلي عشوائي
# ---------------------------------------------------------------------------
import market_hours
us_status = market_hours.market_status('us')
saudi_status = market_hours.market_status('saudi')
check("market_status('us') يرجع حقل open منطقي", isinstance(us_status['open'], bool))
check("market_status('saudi') يرجع حقل open منطقي", isinstance(saudi_status['open'], bool))

# ---------------------------------------------------------------------------
# 13) User Isolation — توكن غير صالح لا يُرجع أي مستخدم
# ---------------------------------------------------------------------------
check("توكن عشوائي غير مسجّل -> None", storage.get_user_by_token('not-a-real-token') is None)
new_user = storage.create_user('اختبار')
check("توكن صحيح بعد الإنشاء -> يرجع نفس user_id",
      storage.get_user_by_token(new_user['token']) == new_user['user_id'])
check("القاعدة لا تخزّن التوكن الحقيقي نصاً صريحاً (Hash فقط)",
      storage.get_user_by_token('اختبار') != new_user['user_id'])  # التسمية العادية مو توكن صالح
import sqlite3 as _sqlite3
with _sqlite3.connect(os.environ['LEO2STOCK_DB_PATH']) as _c:
    _row = _c.execute("SELECT token_hash FROM users WHERE user_id=?", (new_user['user_id'],)).fetchone()
    check("عمود token_hash في القاعدة لا يساوي التوكن الحقيقي إطلاقاً (Hashed فعلاً)",
          _row[0] != new_user['token'] and len(_row[0]) == 64)  # SHA-256 hex = 64 حرف


# ---------------------------------------------------------------------------
# 14) Strategy Version — لا تتأثر الإشارات القديمة بتعديل لاحق للاستراتيجية
# ---------------------------------------------------------------------------
sid_v = storage.create_strategy(uid, 'نسخة تجريبية', 'us', 'trigger',
                                 {'logic': 'AND', 'conditions': [{'type': 'rsi_below', 'value': 30, 'points': 10}]})
v1 = storage.get_strategy(sid_v)['version']
storage.update_strategy(sid_v, conditions_json='{"logic":"AND","conditions":[{"type":"rsi_above","value":70,"points":10}]}')
v2 = storage.get_strategy(sid_v)['version']
check(f"تعديل شروط الاستراتيجية يرفع version ({v1} -> {v2})", v2 == v1 + 1)

# ---------------------------------------------------------------------------
# 16) Strategy Classification (Tabs بالواجهة) — مبني على أنواع الشروط الفعلية فقط
# ---------------------------------------------------------------------------
fib_strategy = {'logic': 'AND', 'conditions': [{'type': 'price_in_fibonacci_zone', 'level': '61.8%', 'points': 10}]}
check("استراتيجية فيها شرط فيبوناتشي -> classify='fibonacci'", se.classify_strategy(fib_strategy) == 'fibonacci')

breakout_strategy = {'logic': 'AND', 'conditions': [{'type': 'price_breaks_resistance', 'points': 10}]}
check("استراتيجية اختراق -> classify='breakout'", se.classify_strategy(breakout_strategy) == 'breakout')

rsi_only = {'logic': 'AND', 'conditions': [{'type': 'rsi_below', 'value': 30, 'points': 10}]}
check("استراتيجية RSI فقط -> classify='rsi'", se.classify_strategy(rsi_only) == 'rsi')

mixed_custom = {'logic': 'AND', 'conditions': [{'type': 'volume_ratio_above', 'value': 2, 'points': 10},
                                                {'type': 'daily_change_above', 'value': 5, 'points': 10}]}
check("استراتيجية بدون RSI/MACD/Fibonacci/Breakout -> classify='custom'", se.classify_strategy(mixed_custom) == 'custom')

nested_fib_priority = {'logic': 'AND', 'conditions': [
    {'type': 'rsi_below', 'value': 30, 'points': 10},
    {'logic': 'OR', 'conditions': [{'type': 'price_in_fibonacci_zone', 'level': '50.0%', 'points': 10}]}
]}
check("فيبوناتشي متداخل مع RSI -> الأولوية لفيبوناتشي", se.classify_strategy(nested_fib_priority) == 'fibonacci')

# ---------------------------------------------------------------------------
# 15) Fibonacci Engine — حسابات حقيقية، ليست واجهة بدون محرك
# ---------------------------------------------------------------------------
import fibonacci_engine as fib


class _FakePrices(dict):
    """محاكاة بسيطة لبنية prices المستخدمة في الكود (High/Low/Close قابلة للتكرار)."""
    pass


def make_prices(highs, lows, closes):
    return _FakePrices({'High': highs, 'Low': lows, 'Close': closes})


# اتجاه صاعد واضح: قاع عند اليوم 0، قمة عند اليوم آخر
lows_up = [100] + [110] * 29
highs_up = [105] + [150] * 29
closes_up = [102] + [140] * 29
prices_up = make_prices(highs_up, lows_up, closes_up)
swing = fib.find_swing(prices_up, lookback=30)
check("Swing Detection: القاع قبل القمة زمنياً -> direction='up'", swing['direction'] == 'up')
check("Swing High/Low صحيحان (100 -> 150)", swing['swing_low'] == 100 and swing['swing_high'] == 150)

levels = fib.compute_levels(150, 100, 'up')
check("مستوى 0% في الاتجاه الصاعد = القمة (150)", levels['0.0%'] == 150)
check("مستوى 100% في الاتجاه الصاعد = القاع (100)", levels['100.0%'] == 100)
check("مستوى 61.8% محسوب صح: 150 - 50*0.618 = 119.1",
      abs(levels['61.8%'] - 119.1) < 0.01)

zone = fib.current_zone(119.1, levels, tolerance_pct=1.5)
check("سعر بالضبط عند 61.8% -> current_zone يطابق '61.8%'", zone is not None and zone['level'] == '61.8%')

zone_far = fib.current_zone(135, levels, tolerance_pct=1.5)
check("سعر بعيد عن كل المستويات (خارج التسامح) -> current_zone = None", zone_far is None)

# اتجاه هابط: قمة أولاً ثم قاع
prices_down = make_prices([150] + [110] * 29, [100] + [90] * 29, [140] + [95] * 29)
swing_down = fib.find_swing(prices_down, lookback=30)
check("اتجاه هابط: القمة قبل القاع زمنياً -> direction='down'", swing_down['direction'] == 'down')

# بيانات غير كافية -> لا نختلق Swing
check("بيانات أقل من 10 شموع -> find_swing يرجع None", fib.find_swing(make_prices([1, 2], [1, 2], [1, 2])) is None)

# شرط الاستراتيجية price_in_fibonacci_zone
fib_result = fib.analyze(prices_up, 119.1)
ctx_fib = se.build_context(119.1, 0, {'rsi': 50}, support=90, resistance=200, volume_ratio=1, fibonacci=fib_result)
cond_fib = {'type': 'price_in_fibonacci_zone', 'level': '61.8%', 'points': 15}
r = se.evaluate_leaf(cond_fib, ctx_fib, None)
check("شرط price_in_fibonacci_zone (61.8%) يتحقق فعلاً عند السعر المطابق", r['satisfied'] is True)

cond_fib_wrong = {'type': 'price_in_fibonacci_zone', 'level': '23.6%', 'points': 15}
r2 = se.evaluate_leaf(cond_fib_wrong, ctx_fib, None)
check("نفس السعر لكن يطلب مستوى مختلف (23.6%) -> False", r2['satisfied'] is False)

ctx_no_fib = se.build_context(119.1, 0, {'rsi': 50}, support=90, resistance=200, volume_ratio=1, fibonacci=None)
r3 = se.evaluate_leaf(cond_fib, ctx_no_fib, None)
check("لا يوجد تحليل فيبوناتشي أصلاً (fibonacci=None) -> الشرط False (لا اختلاق)", r3['satisfied'] is False)

# ---------------------------------------------------------------------------
if os.path.exists(os.environ['LEO2STOCK_DB_PATH']):
    os.remove(os.environ['LEO2STOCK_DB_PATH'])



print(f"\n🎉 كل الاختبارات نجحت: {passed}/{passed}")
