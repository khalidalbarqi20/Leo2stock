"""
Historical Price Analyzer
==========================
محرك منفصل يحسب إحصائيات تاريخية بحتة (Return, Volatility, Max Drawdown, أعلى/أدنى سعر)
لفترات 1/2/5 سنوات. لا علاقة له بالـAI — فقط أرقام، ثم تُرسل لاحقاً لشخصية 'historical' في ai_engine.
"""
import numpy as np

TRADING_DAYS = {'1y': 252, '2y': 504, '5y': 1260}


def _closes(prices):
    col = prices['Close']
    return list(col._d) if hasattr(col, '_d') else list(col)


def _period_stats(closes):
    if len(closes) < 2:
        return None
    closes = np.array(closes, dtype=float)
    start, end = closes[0], closes[-1]
    ret_pct = round((end - start) / start * 100, 2) if start else 0.0

    daily_returns = np.diff(closes) / closes[:-1]
    volatility_annual_pct = round(float(np.std(daily_returns)) * (252 ** 0.5) * 100, 2) if len(daily_returns) else 0.0

    running_max = np.maximum.accumulate(closes)
    drawdowns = (closes - running_max) / running_max
    max_drawdown_pct = round(float(drawdowns.min()) * 100, 2)

    return {
        'return_pct': ret_pct,
        'volatility_annual_pct': volatility_annual_pct,
        'max_drawdown_pct': max_drawdown_pct,
        'highest_price': round(float(closes.max()), 2),
        'lowest_price': round(float(closes.min()), 2),
    }


def analyze(prices_5y):
    """
    prices_5y: أطول سلسلة أسعار متاحة (يفضل 5 سنوات). يحسب لكل فترة متاحة فقط
    (إذا لم تتوفر 5 سنوات فعلياً، تُحذف تلك الفترة من النتيجة بدل اختراع رقم).
    """
    closes = _closes(prices_5y)
    result = {}
    for label, days in TRADING_DAYS.items():
        if len(closes) >= days:
            result[label] = _period_stats(closes[-days:])
        elif label == '1y' and closes:
            # إذا كانت البيانات المتاحة أقل من سنة، نحسب على المتاح فقط ونوضح ذلك
            result[label] = _period_stats(closes)
            result[label]['note'] = f'بيانات متاحة فعلياً: {len(closes)} يوم تداول فقط'
    return result
