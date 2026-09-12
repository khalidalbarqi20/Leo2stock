"""
Signal Display Status
=======================
يحوّل status الخام في قاعدة البيانات (ACTIVE/CONFIRMED/INVALIDATED/CLOSED) إلى تسمية
عرض أدق للمستخدم، بالاعتماد فقط على بيانات confirmation المخزّنة فعلياً وقت الإشارة.

⚠️ حد صريح: WATCHING / APPROACHING (أسهم تقترب من الشروط لكن لم تُطلق إشارة بعد) غير
مدعومة حالياً — تحتاج تتبع درجة جزئية لكل الأسهم المراقبة باستمرار (وليس فقط عند التفعيل
الكامل)، وهذا لم يُبنَ بعد. لا نعرضها في الواجهة حتى تُبنى فعلياً.
"""

DISPLAY_LABELS = {
    'CONFIRMED': 'CONFIRMED',
    'INVALIDATED': 'INVALIDATED',
    'CLOSED': 'CLOSED',
}


def display_status(signal):
    raw = signal.get('status')
    if raw in DISPLAY_LABELS:
        return DISPLAY_LABELS[raw]
    if raw == 'ACTIVE':
        confirmation = signal.get('confirmation')
        if confirmation and confirmation.get('met') is False:
            return 'CONFIRMATION REQUIRED'
        return 'ENTRY SETUP'
    return raw or 'UNKNOWN'
