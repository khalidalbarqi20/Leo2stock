"""
User Isolation (نسخة أولية بسيطة — ليست نظام حسابات كامل)
=============================================================
المشكلة اللي نحلها: قبل هذا الملف كان user_id يُقرأ مباشرة من طلب العميل (?user_id=xxx)،
أي شخص يقدر يغيّره ويشوف بيانات مستخدم ثاني. الآن:

- كل مستخدم له Token عشوائي (secrets.token_urlsafe) يُصدره الأدمن (خالد) عبر
  /api/auth/create-user (محمي بمفتاح ADMIN_KEY في متغيرات البيئة).
- التوكن الحقيقي يظهر للمستخدم مرة واحدة فقط عند الإنشاء؛ القاعدة تخزّن HMAC-SHA256
  للتوكن فقط (راجع storage._hash_token) — لا نص صريح، ولا رجوع للتوكن لاحقاً حتى من الأدمن.
- كل طلب لأي endpoint محمي يجب أن يرسل:
      Authorization: Bearer <token>
  ولو التوكن غير صالح أو غير موجود -> 401، ولا يُقرأ user_id من العميل إطلاقاً.

⚠️ حدود صريحة (يحتاج تحسين لاحقاً قبل إطلاق عام واسع):
- لازم تضبط TOKEN_PEPPER في متغيرات البيئة (قيمة سرية طويلة) — بدونها يُستخدم Pepper
  تطويري غير آمن مع تحذير في اللوق.
- لا يوجد تسجيل دخول ذاتي (Self-signup) ولا صفحة واجهة لإدارة المستخدمين بعد — الإصدار
  حالياً فقط عبر API بمفتاح الأدمن.
- لا يوجد تدوير (rotation) أو انتهاء صلاحية للتوكنات بعد.
"""
import os
from functools import wraps
from flask import request, jsonify
import storage

ADMIN_KEY = os.environ.get('ADMIN_KEY', '')


def resolve_user_id():
    """يرجع user_id إذا كان التوكن صالحاً، وإلا None. لا يقرأ user_id من العميل إطلاقاً."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[len('Bearer '):].strip()
    if not token:
        return None
    return storage.get_user_by_token(token)


def require_auth(view_func):
    """Decorator: يرفض الطلب بـ401 إذا التوكن غير صالح، ويمرر uid كـkwarg."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        uid = resolve_user_id()
        if not uid:
            return jsonify({'error': 'غير مصرح — أرسل Authorization: Bearer <token> صالح'}), 401
        return view_func(*args, uid=uid, **kwargs)
    return wrapper


def require_admin(view_func):
    """Decorator لعمليات الأدمن فقط (مثل إصدار توكنات جديدة)."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not ADMIN_KEY:
            return jsonify({'error': 'ADMIN_KEY غير مضبوط في متغيرات البيئة — لا يمكن إصدار مستخدمين'}), 503
        key = request.headers.get('X-Admin-Key', '')
        if key != ADMIN_KEY:
            return jsonify({'error': 'مفتاح الأدمن غير صحيح'}), 403
        return view_func(*args, **kwargs)
    return wrapper
