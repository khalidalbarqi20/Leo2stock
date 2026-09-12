"""
Strategy / Rules Engine + Scoring Engine
=========================================
هذا الملف لا يستدعي أي AI إطلاقاً — فقط حسابات رقمية صريحة، حسب القاعدة:
"المحرك يحسب — الذكاء الاصطناعي يفسر".

بنية الاستراتيجية (Condition Tree) — تدعم AND / OR / Nested Groups:
{
  "logic": "AND",
  "conditions": [
      {"type": "rsi_below", "value": 30, "points": 20},
      {"type": "price_above_sma", "period": 200, "points": 20},
      {"logic": "OR", "points": 20, "conditions": [
          {"type": "macd_cross_above_signal", "points": 20},
          {"type": "volume_ratio_above", "value": 2, "points": 15}
      ]}
  ]
}

كل شرط ورقي (leaf) يُعاد له: satisfied (True/False) + reason (نص عربي واضح) + points.
"""

CONDITION_LABELS = {
    'rsi_below': 'RSI أقل من {value}',
    'rsi_above': 'RSI أعلى من {value}',
    'price_above_sma': 'السعر فوق SMA{period}',
    'price_below_sma': 'السعر تحت SMA{period}',
    'price_cross_above_sma': 'السعر اخترق SMA{period} صعوداً',
    'price_cross_below_sma': 'السعر كسر SMA{period} هبوطاً',
    'sma_above_sma': 'SMA{fast} فوق SMA{slow}',
    'sma_cross_above_sma': 'تقاطع ذهبي: SMA{fast} اخترق SMA{slow} صعوداً',
    'macd_above_signal': 'MACD فوق خط الإشارة',
    'macd_cross_above_signal': 'تقاطع MACD صعودي',
    'macd_cross_below_signal': 'تقاطع MACD هبوطي',
    'histogram_above_zero': 'هيستوجرام MACD موجب',
    'histogram_cross_above_zero': 'هيستوجرام MACD تجاوز الصفر صعوداً',
    'volume_ratio_above': 'حجم التداول أعلى من {value}× المتوسط',
    'price_near_support': 'السعر قريب من الدعم (ضمن {value}%)',
    'price_breaks_resistance': 'السعر اخترق المقاومة',
    'price_breaks_support_down': 'السعر كسر الدعم هبوطاً',
    'price_in_fibonacci_zone': 'السعر داخل منطقة فيبوناتشي {level}',
    'daily_change_above': 'التغير اليومي أعلى من {value}%',
    'daily_change_below': 'التغير اليومي أقل من {value}%',
}


def _get(ctx, path, default=0):
    cur = ctx
    for p in path.split('.'):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


class _SafeDict(dict):
    def __missing__(self, key):
        return f'؟{key}'


def _label(cond):
    try:
        return CONDITION_LABELS.get(cond['type'], cond['type']).format_map(_SafeDict(cond))
    except Exception:
        return cond.get('type', 'شرط')


def evaluate_leaf(cond, ctx, prev_ctx):
    """
    ctx: القيم الحالية {price, change_pct, rsi, sma_20, sma_50, sma_200, macd, signal, histogram,
                          volume_ratio, support, resistance}
    prev_ctx: نفس البنية لكن من آخر فحص (للـ Cross Detection) — قد تكون None
    """
    t = cond['type']
    label = _label(cond)
    points = cond.get('points', 10)

    def leaf(satisfied):
        return {'type': t, 'label': label, 'satisfied': bool(satisfied), 'points': points,
                'value_now': None}

    if t == 'rsi_below':
        return leaf(_get(ctx, 'rsi', 50) < cond['value'])
    if t == 'rsi_above':
        return leaf(_get(ctx, 'rsi', 50) > cond['value'])

    if t == 'price_above_sma':
        return leaf(_get(ctx, 'price') > _get(ctx, f"sma_{cond['period']}"))
    if t == 'price_below_sma':
        return leaf(_get(ctx, 'price') < _get(ctx, f"sma_{cond['period']}"))

    if t == 'price_cross_above_sma':
        if not prev_ctx:
            return leaf(False)
        key = f"sma_{cond['period']}"
        return leaf(_get(prev_ctx, 'price') <= _get(prev_ctx, key) and _get(ctx, 'price') > _get(ctx, key))
    if t == 'price_cross_below_sma':
        if not prev_ctx:
            return leaf(False)
        key = f"sma_{cond['period']}"
        return leaf(_get(prev_ctx, 'price') >= _get(prev_ctx, key) and _get(ctx, 'price') < _get(ctx, key))

    if t == 'sma_above_sma':
        return leaf(_get(ctx, f"sma_{cond['fast']}") > _get(ctx, f"sma_{cond['slow']}"))
    if t == 'sma_cross_above_sma':
        if not prev_ctx:
            return leaf(False)
        fk, sk = f"sma_{cond['fast']}", f"sma_{cond['slow']}"
        return leaf(_get(prev_ctx, fk) <= _get(prev_ctx, sk) and _get(ctx, fk) > _get(ctx, sk))

    if t == 'macd_above_signal':
        return leaf(_get(ctx, 'macd') > _get(ctx, 'signal'))
    if t == 'macd_cross_above_signal':
        if not prev_ctx:
            return leaf(False)
        return leaf(_get(prev_ctx, 'macd') <= _get(prev_ctx, 'signal') and _get(ctx, 'macd') > _get(ctx, 'signal'))
    if t == 'macd_cross_below_signal':
        if not prev_ctx:
            return leaf(False)
        return leaf(_get(prev_ctx, 'macd') >= _get(prev_ctx, 'signal') and _get(ctx, 'macd') < _get(ctx, 'signal'))

    if t == 'histogram_above_zero':
        return leaf(_get(ctx, 'histogram') > 0)
    if t == 'histogram_cross_above_zero':
        if not prev_ctx:
            return leaf(False)
        return leaf(_get(prev_ctx, 'histogram') <= 0 and _get(ctx, 'histogram') > 0)

    if t == 'volume_ratio_above':
        return leaf(_get(ctx, 'volume_ratio', 1) > cond['value'])

    if t == 'price_near_support':
        pct = cond.get('value', 2)
        support = _get(ctx, 'support')
        price = _get(ctx, 'price')
        if not support:
            return leaf(False)
        return leaf(abs(price - support) / support * 100 <= pct)

    if t == 'price_breaks_resistance':
        return leaf(_get(ctx, 'price') > _get(ctx, 'resistance', float('inf')))
    if t == 'price_breaks_support_down':
        return leaf(_get(ctx, 'price') < _get(ctx, 'support', float('-inf')))

    if t == 'price_in_fibonacci_zone':
        fib = ctx.get('fibonacci')
        if not fib or not fib.get('current_zone'):
            return leaf(False)
        target_level = cond.get('level')  # مثلاً "61.8%" — إن لم يُحدد، أي منطقة تكفي
        if target_level and fib['current_zone']['level'] != target_level:
            return leaf(False)
        return leaf(True)

    if t == 'daily_change_above':
        return leaf(_get(ctx, 'change_pct') > cond['value'])
    if t == 'daily_change_below':
        return leaf(_get(ctx, 'change_pct') < cond['value'])

    return leaf(False)


def evaluate_tree(node, ctx, prev_ctx, leaves_out):
    """يرجع True/False حسب AND/OR، ويجمع كل الأوراق (leaves) في leaves_out للتسجيل والتفسير."""
    if 'type' in node:  # ورقة
        result = evaluate_leaf(node, ctx, prev_ctx)
        leaves_out.append(result)
        return result['satisfied']

    logic = node.get('logic', 'AND').upper()
    children = node.get('conditions', [])
    results = [evaluate_tree(c, ctx, prev_ctx, leaves_out) for c in children]
    if logic == 'OR':
        return any(results) if results else False
    return all(results) if results else False


def _collect_leaf_types(node, out):
    if 'type' in node:
        out.add(node['type'])
        return
    for c in node.get('conditions', []):
        _collect_leaf_types(c, out)


def classify_strategy(conditions):
    """
    تصنيف عرضي بسيط للواجهة فقط (Tabs)، مبني فعلياً على أنواع الشروط الموجودة —
    وليس تصنيفاً مختلقاً. الأولوية: fibonacci > breakout > macd > rsi > custom.
    """
    types = set()
    _collect_leaf_types(conditions, types)
    if 'price_in_fibonacci_zone' in types:
        return 'fibonacci'
    if 'price_breaks_resistance' in types or 'price_breaks_support_down' in types:
        return 'breakout'
    if any(t.startswith('macd') or t.startswith('histogram') for t in types):
        return 'macd'
    if any(t.startswith('rsi') for t in types):
        return 'rsi'
    return 'custom'


SCORE_LABELS = [
    (90, 'مرتفع جداً'), (75, 'مرتفع'), (60, 'متوسط'), (40, 'منخفض'), (0, 'ضعيف'),
]


def score_label(score_100):
    for threshold, label in SCORE_LABELS:
        if score_100 >= threshold:
            return label
    return 'ضعيف'


def run_strategy(strategy_conditions, ctx, prev_ctx=None):
    """
    يرجع:
      triggered: bool (نتيجة منطق AND/OR الصارم)
      score_100: 0-100 (درجة توافق وزنية — مو احتمال صعود)
      score_label: نص وصفي للدرجة
      satisfied: قائمة الشروط المتحققة (labels)
      unsatisfied: قائمة الشروط غير المتحققة (labels)
    """
    leaves = []
    triggered = evaluate_tree(strategy_conditions, ctx, prev_ctx, leaves)

    total_points = sum(l['points'] for l in leaves) or 1
    earned_points = sum(l['points'] for l in leaves if l['satisfied'])
    score_100 = max(0, min(100, round(earned_points / total_points * 100)))

    satisfied = [l['label'] for l in leaves if l['satisfied']]
    unsatisfied = [l['label'] for l in leaves if not l['satisfied']]

    return {
        'triggered': triggered,
        'score_100': score_100,
        'score_label': score_label(score_100),
        'satisfied': satisfied,
        'unsatisfied': unsatisfied,
    }


def build_context(current_price, change_pct, indicators, support, resistance, volume_ratio, fibonacci=None):
    """يبني ctx موحّد من مخرجات technical_analysis.py الحالية — بدون أي تعديل على تلك الحسابات."""
    macd = indicators.get('macd', {})
    return {
        'price': current_price,
        'change_pct': change_pct,
        'rsi': indicators.get('rsi', 50),
        'sma_20': indicators.get('sma_20', current_price),
        'sma_50': indicators.get('sma_50', current_price),
        'sma_200': indicators.get('sma_200', current_price),
        'macd': macd.get('macd', 0),
        'signal': macd.get('signal', 0),
        'histogram': macd.get('histogram', 0),
        'volume_ratio': volume_ratio,
        'support': support,
        'resistance': resistance,
        'fibonacci': fibonacci,  # dict من fibonacci_engine.analyze() أو None
    }


def derive_lifecycle_conditions(strategy, ctx, prev_ctx, run_result):
    """
    يبني Entry/Confirmation/Invalidation/Exit من قواعد صريحة فقط — لا AI هنا إطلاقاً.
    - entry: الشروط الأساسية التي حققت التفعيل (من run_result مباشرة).
    - confirmation: شجرة "confirmation_conditions" في تعريف الاستراتيجية إن وُجدت (اختيارية).
    - invalidation: شجرة "reset_conditions" في الاستراتيجية (الافتراضي: عكس الشرط الرئيسي).
    - exit: شجرة "exit_conditions" إن وُجدت.
    كل قيمة نصية هنا مبنية على تعريف المستخدم للاستراتيجية، وليست أرقاماً يخترعها AI لاحقاً.
    """
    entry = {'conditions': run_result['satisfied']}

    confirmation = None
    if strategy.get('confirmation_conditions'):
        leaves = []
        met = evaluate_tree(strategy['confirmation_conditions'], ctx, prev_ctx, leaves)
        confirmation = {'met': met, 'conditions': [l['label'] for l in leaves]}

    invalidation_tree = strategy.get('reset_conditions')
    if invalidation_tree:
        leaves = []
        active = evaluate_tree(invalidation_tree, ctx, prev_ctx, leaves)
        invalidation = {'active': active, 'conditions': [l['label'] for l in leaves]}
    else:
        # افتراضي: الفكرة تصبح غير صالحة إذا لم تعد الشروط الأساسية متحققة
        invalidation = {'active': not run_result['triggered'],
                         'conditions': ['عدم استمرار تحقق شروط الاستراتيجية الأساسية']}

    exit_ = None
    if strategy.get('exit_conditions'):
        leaves = []
        met = evaluate_tree(strategy['exit_conditions'], ctx, prev_ctx, leaves)
        exit_ = {'met': met, 'conditions': [l['label'] for l in leaves]}

    return entry, confirmation, invalidation, exit_
