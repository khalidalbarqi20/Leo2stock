"""
Market Scheduler — معرفة هل السوق مفتوح أم مغلق، لمنع فحص/تنبيهات وهمية وقت الإغلاق.

⚠️ حدود صريحة (مهم تعرفها):
- ساعات Tadawul هنا تقريبية (الجلسة المستمرة المعتادة تقريباً 10:00–15:00 بتوقيت الرياض،
  الأحد–الخميس) ولا تشمل التعديلات الموسمية أو تغييرات ساعات السوق الرسمية — يفضل
  التأكد من مصدر Tadawul الرسمي دورياً.
- لا يوجد تقويم عطلات حقيقي (لا للسعودية ولا لأمريكا) — يوم عطلة رسمية سيُعامل حالياً
  كأنه يوم تداول عادي. هذا يحتاج قائمة عطلات فعلية لاحقاً (تحسين مستقبلي).
- التوقيت الأمريكي يُحسب صح تلقائياً مع التوقيت الصيفي/الشتوي عبر zoneinfo.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

SAUDI_TZ = ZoneInfo('Asia/Riyadh')
US_TZ = ZoneInfo('America/New_York')

# الأحد=6, الاثنين=0 ... حسب weekday() بايثون: الاثنين=0 ... الأحد=6
SAUDI_TRADING_DAYS = {6, 0, 1, 2, 3}   # الأحد، الاثنين، الثلاثاء، الأربعاء، الخميس
US_TRADING_DAYS = {0, 1, 2, 3, 4}       # الاثنين-الجمعة


def market_status(market):
    """يرجع dict: {open: bool, reason: str, local_time: str, session: 'saudi'/'us'}"""
    if market == 'saudi':
        now = datetime.now(SAUDI_TZ)
        is_trading_day = now.weekday() in SAUDI_TRADING_DAYS
        open_time, close_time = now.replace(hour=10, minute=0, second=0, microsecond=0), \
                                 now.replace(hour=15, minute=0, second=0, microsecond=0)
    elif market == 'us':
        now = datetime.now(US_TZ)
        is_trading_day = now.weekday() in US_TRADING_DAYS
        open_time, close_time = now.replace(hour=9, minute=30, second=0, microsecond=0), \
                                 now.replace(hour=16, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"سوق غير معروف: {market}")

    is_open = is_trading_day and open_time <= now <= close_time
    return {
        'market': market, 'open': is_open, 'local_time': now.isoformat(),
        'is_trading_day': is_trading_day,
        'reason': 'مفتوح' if is_open else ('يوم عطلة أسبوعية' if not is_trading_day else 'خارج ساعات التداول'),
        'note': 'ساعات تقريبية بدون تقويم عطلات رسمية — راجع docstring الملف',
    }


def is_market_open(market):
    return market_status(market)['open']
