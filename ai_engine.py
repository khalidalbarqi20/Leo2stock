"""
AI Explanation Engine
======================
القاعدة الذهبية: AI يفسر فقط، لا يحسب أرقاماً ولا يخترعها ولا يصدر أمر شراء/بيع.
التسلسل الصحيح (لا العكس):
  Market Data -> Strategy Engine -> Signal Created -> Notification -> AI Explanation
AI ليس شرطاً لإنشاء أي إشارة أو تنبيه — فشله لا يوقف شيئاً، فقط يُسجَّل ai_status.

هذا الملف لا يُستدعى لكل سهم — فقط للمرشحين بعد فلترة الدرجة (ai_gate)،
ومع تخزين مؤقت (cache) لمنع استهلاك حدود NVIDIA المجانية.

الإخراج المطلوب من النموذج: JSON صارم فقط (لا نص حر) -> يُتحقق من صحته Schema،
وإذا فشل التحقق نستخدم شرحاً حتمياً (Deterministic) مبنياً على القواعد فقط — بدون AI إطلاقاً.

ai_status الممكنة: skip / optional / ok / cached / timeout / api_error / invalid_json_fallback / failed
"""
import os
import json
import hashlib
import requests
import storage

AI_PROVIDER = os.environ.get('AI_PROVIDER', 'nvidia')
NVIDIA_API_KEY = os.environ.get('NVIDIA_API_KEY', '')
NVIDIA_MODEL = os.environ.get('NVIDIA_MODEL', 'meta/llama-3.3-70b-instruct')
NVIDIA_BASE_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
NVIDIA_TIMEOUT_SECONDS = 30

CACHE_TTL_MINUTES = 45

SCORE_OPTIONAL_THRESHOLD = int(os.environ.get('AI_SCORE_OPTIONAL_THRESHOLD', 60))
SCORE_AUTO_THRESHOLD = int(os.environ.get('AI_SCORE_AUTO_THRESHOLD', 75))
SCORE_PRIORITY_THRESHOLD = int(os.environ.get('AI_SCORE_PRIORITY_THRESHOLD', 90))


def ai_gate(score_100):
    """يرجع: 'skip' / 'optional' / 'auto' / 'priority' — القيم قابلة للتعديل عبر متغيرات بيئة."""
    if score_100 >= SCORE_PRIORITY_THRESHOLD:
        return 'priority'
    if score_100 >= SCORE_AUTO_THRESHOLD:
        return 'auto'
    if score_100 >= SCORE_OPTIONAL_THRESHOLD:
        return 'optional'
    return 'skip'


class AIProvider:
    """Interface — أي مزود جديد (OpenAI, Gemini...) يطبّق نفس الدالة."""
    def chat(self, system_prompt, user_content):
        """يرجع (text, status) حيث status في: 'ok' / 'timeout' / 'api_error' / 'no_key'"""
        raise NotImplementedError


class NvidiaProvider(AIProvider):
    def chat(self, system_prompt, user_content):
        if not NVIDIA_API_KEY:
            return None, 'no_key'
        headers = {'Authorization': f'Bearer {NVIDIA_API_KEY}', 'Content-Type': 'application/json'}
        payload = {
            'model': NVIDIA_MODEL,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content},
            ],
            'temperature': 0.2,
            'max_tokens': 500,
        }
        try:
            r = requests.post(NVIDIA_BASE_URL, headers=headers, json=payload, timeout=NVIDIA_TIMEOUT_SECONDS)
            if r.status_code == 200:
                data = r.json()
                return data['choices'][0]['message']['content'].strip(), 'ok'
            print(f"NVIDIA API error {r.status_code}: {r.text[:300]}")
            return None, 'api_error'
        except requests.Timeout:
            print("NVIDIA API timeout")
            return None, 'timeout'
        except Exception as e:
            print(f"NVIDIA API exception: {e}")
            return None, 'api_error'


def get_provider():
    if AI_PROVIDER == 'nvidia':
        return NvidiaProvider()
    raise ValueError(f"مزود AI غير مدعوم: {AI_PROVIDER}")


_JSON_INSTRUCTIONS = """
أجب حصراً بصيغة JSON صالحة (بدون أي نص قبلها أو بعدها، بدون Markdown)، بالشكل التالي بالضبط:
{"explanation": "شرح عربي من 3-5 جمل", "key_points": ["نقطة قصيرة 1", "نقطة قصيرة 2", "نقطة قصيرة 3"]}
"""

_BASE_RULES = """أنت محلل يشرح بيانات جاهزة فقط — لا تحسب ولا تخترع أي رقم غير موجود في البيانات المرسلة إليك.
ممنوع عليك منعاً باتاً:
- اختلاق أي رقم أو خبر أو مستوى دعم/مقاومة غير مذكور في البيانات.
- اختراع أي مستوى دخول أو وقف خسارة أو هدف سعري من عندك — إذا لم يُرسل لك مستوى رقمي محدد ضمن
  entry/confirmation/invalidation/exit، فاشرح الشروط النصية فقط ولا تضف رقماً.
- الادعاء بمعرفة المستقبل أو إعطاء نسبة نجاح غير محسوبة إحصائياً.
- اعتبار "درجة التوافق" احتمال ربح أو صعود.
- إصدار أمر قطعي "اشترِ" أو "بع".
إذا كانت بيانات معينة غير متوفرة أو حالتها NO_NEWS_AVAILABLE، قل صراحة "لا توجد بيانات كافية" بدل
اختراع أي محتوى إخباري أو تحويل التحليل الفني إلى "خبر".
استخدم لغة مثل "توجد إشارة متوافقة مع الشروط" أو "قد تستحق المراجعة"، وتجنب لغة اليقين.""" + _JSON_INSTRUCTIONS

PERSONAS = {
    'technical': _BASE_RULES + "\nمهمتك: شرح المؤشرات الفنية المرسلة (RSI, MACD, SMA, الحجم) وسبب ظهور الإشارة بلغة مبسطة.",
    'fundamental_news': _BASE_RULES + "\nمهمتك: تلخيص الأخبار والبيانات الأساسية المرسلة فقط (لا تضف أخباراً من عندك)، ووضح تاريخ كل خبر إن وجد، وهل تأثيره إيجابي/سلبي/محايد محتمل.",
    'historical': _BASE_RULES + "\nمهمتك: شرح نمط السهم التاريخي (العائد، أعلى هبوط، التذبذب) خلال الفترات المرسلة، وربط ذلك بمستوى المخاطرة العام دون التنبؤ بالمستقبل.",
}


def _cache_key(persona, payload):
    raw = persona + json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _validate_schema(parsed):
    if not isinstance(parsed, dict):
        return False
    if not isinstance(parsed.get('explanation'), str) or not parsed['explanation'].strip():
        return False
    if 'key_points' in parsed and not isinstance(parsed['key_points'], list):
        return False
    return True


def _deterministic_explanation(persona, payload):
    """Fallback حتمي 100% بدون AI — عند فشل AI أو JSON غير صالح."""
    payload = payload or {}
    if persona == 'technical':
        rsi = payload.get('rsi')
        score = payload.get('score_100')
        conds = payload.get('triggered_conditions') or []
        parts = []
        if rsi is not None:
            parts.append(f"RSI الحالي {rsi}")
        if score is not None:
            parts.append(f"درجة التوافق مع الاستراتيجية {score}/100")
        if conds:
            parts.append("الشروط المتحققة: " + '، '.join(conds))
        text = '. '.join(parts) if parts else "لا توجد بيانات كافية لعرض شرح فني."
        return {'explanation': text, 'key_points': conds[:5]}

    if persona == 'fundamental_news':
        return {'explanation': 'لا توجد بيانات كافية (NO_NEWS_AVAILABLE أو تعذّر توليد الشرح).', 'key_points': []}

    if persona == 'historical':
        y1 = payload.get('1y') or {}
        if y1:
            text = (f"خلال آخر سنة: العائد {y1.get('return_pct')}%، "
                    f"أقصى هبوط {y1.get('max_drawdown_pct')}%، تذبذب سنوي {y1.get('volatility_annual_pct')}%.")
        else:
            text = "لا توجد بيانات تاريخية كافية."
        return {'explanation': text, 'key_points': []}

    return {'explanation': 'لا توجد بيانات كافية.', 'key_points': []}


def explain(persona, payload, force_refresh=False):
    """
    يرجع دائماً dict: {'explanation': str, 'key_points': list, 'status': str, 'cached': bool}
    لا يرمي استثناءً، ولا يرجع None أبداً — عند أي فشل يُستخدم fallback حتمي مع status مناسب.
    """
    if persona not in PERSONAS:
        raise ValueError(f"شخصية غير معروفة: {persona}")

    key = _cache_key(persona, payload)
    if not force_refresh:
        cached = storage.ai_cache_get(key)
        if cached:
            return {**cached, 'cached': True}

    provider = get_provider()
    user_content = "البيانات (لا تخترع أي رقم خارجها):\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    raw_text, status = provider.chat(PERSONAS[persona], user_content)

    if status != 'ok' or raw_text is None:
        fallback = _deterministic_explanation(persona, payload)
        return {**fallback, 'status': status if status != 'ok' else 'failed', 'cached': False}

    try:
        cleaned = raw_text.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.strip('`').replace('json', '', 1).strip()
        parsed = json.loads(cleaned)
        if not _validate_schema(parsed):
            raise ValueError("schema invalid")
        result = {'explanation': parsed['explanation'], 'key_points': parsed.get('key_points', []),
                  'status': 'ok', 'cached': False}
        storage.ai_cache_set(key, {'explanation': result['explanation'], 'key_points': result['key_points'],
                                    'status': 'ok'}, ttl_minutes=CACHE_TTL_MINUTES)
        return result
    except Exception as e:
        print(f"ai_engine: invalid JSON from model for persona={persona}: {e}")
        fallback = _deterministic_explanation(persona, payload)
        return {**fallback, 'status': 'invalid_json_fallback', 'cached': False}


def explain_full(symbol, technical_payload, news_payload=None, historical_payload=None, force_refresh=False):
    """
    يجمع الشخصيات الثلاث. لا يرمي استثناءً أبداً — فشل AI لا يمنع إنشاء الإشارة/التنبيه
    الأساسي في scanner.py (الإشارة تُنشأ من المحرك، لا من AI).
    """
    out = {'symbol': symbol}
    statuses = []

    try:
        out['technical'] = explain('technical', technical_payload, force_refresh)
        statuses.append(out['technical']['status'])
    except Exception as e:
        print(f"ai_engine technical error: {e}")
        out['technical'] = {**_deterministic_explanation('technical', technical_payload), 'status': 'failed', 'cached': False}
        statuses.append('failed')

    if news_payload is not None and news_payload.get('status') == 'NEWS_FOUND':
        try:
            out['fundamental_news'] = explain('fundamental_news', news_payload, force_refresh)
            statuses.append(out['fundamental_news']['status'])
        except Exception as e:
            print(f"ai_engine news error: {e}")
            out['fundamental_news'] = {**_deterministic_explanation('fundamental_news', {}), 'status': 'failed', 'cached': False}
            statuses.append('failed')
    else:
        out['fundamental_news'] = {'explanation': 'لا توجد بيانات كافية (NO_NEWS_AVAILABLE)',
                                    'key_points': [], 'status': 'skip', 'cached': False}

    if historical_payload is not None:
        try:
            out['historical'] = explain('historical', historical_payload, force_refresh)
            statuses.append(out['historical']['status'])
        except Exception as e:
            print(f"ai_engine historical error: {e}")
            out['historical'] = {**_deterministic_explanation('historical', historical_payload), 'status': 'failed', 'cached': False}
            statuses.append('failed')
    else:
        out['historical'] = {'explanation': 'لا توجد بيانات كافية', 'key_points': [], 'status': 'skip', 'cached': False}

    real_statuses = [s for s in statuses if s != 'skip']
    if not real_statuses:
        out['overall_status'] = 'skip'
    elif all(s in ('ok', 'cached') for s in real_statuses):
        out['overall_status'] = 'ok'
    elif any(s in ('ok', 'cached') for s in real_statuses):
        out['overall_status'] = 'degraded'
    else:
        out['overall_status'] = 'failed'

    return out
