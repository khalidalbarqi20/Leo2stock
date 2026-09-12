"""
Fibonacci Engine
=================
حسابات فيبوناتشي بحتة — بدون أي AI. يحدد Swing High/Low من بيانات تاريخية حقيقية،
يحسب مستويات الارتداد القياسية، ويحدد أي منطقة يقع فيها السعر الحالي.

هذا محرك رياضي فقط يُغذّي strategy_engine.py بشرط جديد (price_in_fibonacci_zone) —
تماماً مثل RSI/MACD/SMA، وليس ميزة واجهة منفصلة بدون منطق خلفها.
"""
LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
DEFAULT_LOOKBACK = 60          # عدد الشموع اليومية للبحث عن آخر Swing High/Low
DEFAULT_ZONE_TOLERANCE_PCT = 1.5  # نطاق التسامح حول كل مستوى (بالنسبة المئوية من السعر)


def _closes_highs_lows(prices):
    highs = list(prices['High']._d) if hasattr(prices['High'], '_d') else list(prices['High'])
    lows = list(prices['Low']._d) if hasattr(prices['Low'], '_d') else list(prices['Low'])
    closes = list(prices['Close']._d) if hasattr(prices['Close'], '_d') else list(prices['Close'])
    return highs, lows, closes


def find_swing(prices, lookback=DEFAULT_LOOKBACK):
    """
    يحدد آخر Swing High وSwing Low ضمن نافذة lookback شمعة، ويحدد الاتجاه (صاعد/هابط)
    حسب أيهما حدث لاحقاً زمنياً (منطق مبسّط وصريح، وليس تخميناً).
    """
    highs, lows, closes = _closes_highs_lows(prices)
    if len(highs) < 10:
        return None

    window_highs = highs[-lookback:]
    window_lows = lows[-lookback:]
    swing_high = max(window_highs)
    swing_low = min(window_lows)
    idx_high = len(window_highs) - 1 - window_highs[::-1].index(swing_high)
    idx_low = len(window_lows) - 1 - window_lows[::-1].index(swing_low)

    if swing_high == swing_low:
        return None

    direction = 'up' if idx_low < idx_high else 'down'  # القاع قبل القمة = اتجاه صاعد، والعكس
    return {'swing_high': round(swing_high, 4), 'swing_low': round(swing_low, 4), 'direction': direction}


def compute_levels(swing_high, swing_low, direction):
    """
    مستويات الارتداد القياسية. في الاتجاه الصاعد تُقاس من القمة نزولاً (ارتداد محتمل قبل استكمال الصعود)،
    وفي الهابط من القاع صعوداً — هذا التعريف القياسي لأداة Fibonacci Retracement.
    """
    span = swing_high - swing_low
    levels = {}
    for lvl in LEVELS:
        if direction == 'up':
            price = swing_high - span * lvl
        else:
            price = swing_low + span * lvl
        levels[f"{lvl*100:.1f}%"] = round(price, 4)
    return levels


def current_zone(current_price, levels, tolerance_pct=DEFAULT_ZONE_TOLERANCE_PCT):
    """يرجع أقرب مستوى فيبوناتشي للسعر الحالي إذا كان ضمن نطاق التسامح، وإلا None."""
    closest, closest_dist = None, None
    for label, price in levels.items():
        if price <= 0:
            continue
        dist_pct = abs(current_price - price) / price * 100
        if closest_dist is None or dist_pct < closest_dist:
            closest, closest_dist = label, dist_pct
    if closest is not None and closest_dist <= tolerance_pct:
        return {'level': closest, 'distance_pct': round(closest_dist, 2)}
    return None


def analyze(prices, current_price, lookback=DEFAULT_LOOKBACK, tolerance_pct=DEFAULT_ZONE_TOLERANCE_PCT):
    """
    الدالة الرئيسية: تُرجع None إذا تعذّر تحديد Swing واضح (لا نختلق مستويات من بيانات غير كافية).
    """
    swing = find_swing(prices, lookback)
    if not swing:
        return None
    levels = compute_levels(swing['swing_high'], swing['swing_low'], swing['direction'])
    zone = current_zone(current_price, levels, tolerance_pct)
    return {
        'swing_high': swing['swing_high'], 'swing_low': swing['swing_low'],
        'direction': swing['direction'], 'levels': levels,
        'current_zone': zone,  # None إذا السعر بعيد عن كل المستويات
    }
