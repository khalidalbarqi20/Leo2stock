"""
Data Quality Check
====================
يقف بين Data Fetcher وStrategy Engine بالضبط كما طُلب:
"Fetch → Validate → Normalize → Strategy"

لا يُسمح بتمرير بيانات لمحرك الاستراتيجيات إلا بعد المرور من هنا بنجاح.
"""
from datetime import datetime, timedelta
import market_hours

MIN_BARS_REQUIRED = 20          # أقل عدد شموع لحساب المؤشرات (SMA200 يحتاج فعلياً 200، يُتحقق بشكل منفصل)
MAX_STALENESS_OPEN_MINUTES = 45     # أقصى قِدَم مسموح للبيانات والسوق مفتوح
MAX_STALENESS_CLOSED_HOURS = 96     # أقصى قِدَم مسموح والسوق مغلق (يغطي عطلة نهاية أسبوع + هامش)


def validate(data, market):
    """
    data: مخرجات data_fetcher.get_stock_data() أو None.
    يرجع: {'valid': bool, 'reason': str, 'staleness': ..., 'market_open': bool}
    لا يُنشئ Signal أبداً إذا valid=False — القرار في scanner.py.
    """
    status = market_hours.market_status(market)

    if data is None:
        return {'valid': False, 'reason': 'FETCH_FAILED', 'market_open': status['open']}

    if not data.get('current') or data['current'] <= 0:
        return {'valid': False, 'reason': 'INVALID_PRICE', 'market_open': status['open']}

    prices = data.get('prices')
    bars = len(prices) if prices else 0
    if bars < MIN_BARS_REQUIRED:
        return {'valid': False, 'reason': f'INSUFFICIENT_HISTORY ({bars} < {MIN_BARS_REQUIRED})',
                'market_open': status['open']}

    last_bar_ts = data.get('last_bar_timestamp')
    if not last_bar_ts:
        return {'valid': False, 'reason': 'MISSING_TIMESTAMP', 'market_open': status['open']}

    try:
        last_dt = datetime.fromisoformat(last_bar_ts)
    except Exception:
        return {'valid': False, 'reason': 'BAD_TIMESTAMP_FORMAT', 'market_open': status['open']}

    age = datetime.now() - last_dt.replace(tzinfo=None)
    if status['open'] and age > timedelta(minutes=MAX_STALENESS_OPEN_MINUTES):
        return {'valid': False, 'reason': f'STALE_DATA (عمرها {age}, والسوق مفتوح)',
                'market_open': True, 'staleness_minutes': age.total_seconds() / 60}
    if not status['open'] and age > timedelta(hours=MAX_STALENESS_CLOSED_HOURS):
        return {'valid': False, 'reason': f'STALE_DATA (عمرها {age}, أطول من {MAX_STALENESS_CLOSED_HOURS} ساعة)',
                'market_open': False, 'staleness_minutes': age.total_seconds() / 60}

    return {'valid': True, 'reason': 'OK', 'market_open': status['open'],
            'staleness_minutes': round(age.total_seconds() / 60, 1),
            'last_bar_timestamp': last_bar_ts, 'source': data.get('source', 'unknown')}
