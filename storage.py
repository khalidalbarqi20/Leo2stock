"""
طبقة التخزين — SQLite خفيف (بدون سيرفر قاعدة بيانات منفصل، يناسب Render/Termux).
كل الجداول المطلوبة من التصميم: strategies, watchlist, alert_state (Alert State Machine),
alert_history (Snapshot عند وقت التنبيه), ai_cache (Caching + Deduplication).

ملاحظة تصميم مهمة (تحتاج قرارك لاحقاً):
لا يوجد نظام مستخدمين/تسجيل دخول في المشروع حالياً. كل الدوال هنا تأخذ user_id كسلسلة نصية
حرة (افتراضياً 'default') حتى نبني نظام مستخدمين حقيقي — بهذا الشكل الكود جاهز لإضافة auth
لاحقاً بدون إعادة هيكلة الجداول.
"""
import sqlite3
import json
import os
import threading
from datetime import datetime

DB_PATH = os.environ.get('LEO2STOCK_DB_PATH', os.path.join(os.path.dirname(__file__), 'leo2stock.db'))
_lock = threading.Lock()


def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            name TEXT NOT NULL,
            market TEXT NOT NULL DEFAULT 'both',
            mode TEXT NOT NULL DEFAULT 'trigger',   -- 'trigger' (AND/OR صارم) أو 'score' (ترتيب بالنقاط)
            conditions_json TEXT NOT NULL,
            reset_conditions_json TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            symbol TEXT NOT NULL,
            market TEXT NOT NULL,
            added_at TEXT NOT NULL,
            UNIQUE(user_id, symbol, market)
        );

        CREATE TABLE IF NOT EXISTS alert_state (
            user_id TEXT NOT NULL DEFAULT 'default',
            strategy_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'NOT_TRIGGERED',
            last_score INTEGER,
            last_snapshot_json TEXT,
            last_notified_at TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, strategy_id, symbol)
        );

        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            strategy_id INTEGER,
            strategy_name TEXT,
            symbol TEXT NOT NULL,
            market TEXT NOT NULL,
            alert_kind TEXT NOT NULL DEFAULT 'entry',  -- entry/exit/breakout/breakdown/volume/weakening/cancelled
            score INTEGER,
            triggered_conditions_json TEXT,
            snapshot_json TEXT,
            ai_explanation_json TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_cache (
            cache_key TEXT PRIMARY KEY,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS signals (
            signal_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            strategy_id INTEGER NOT NULL,
            strategy_name TEXT,
            strategy_version INTEGER NOT NULL DEFAULT 1,
            symbol TEXT NOT NULL,
            market TEXT NOT NULL,
            timeframe TEXT NOT NULL DEFAULT '1d',
            trigger_timestamp TEXT NOT NULL,
            market_data_timestamp TEXT,
            trigger_price REAL,
            score INTEGER,
            conditions_json TEXT,
            snapshot_json TEXT,
            indicators_json TEXT,
            entry_json TEXT,
            confirmation_json TEXT,
            invalidation_json TEXT,
            exit_json TEXT,
            news_snapshot_json TEXT,
            ai_explanation_json TEXT,
            ai_status TEXT DEFAULT 'skip',
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            outcome_json TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            token_hash TEXT UNIQUE NOT NULL,
            label TEXT,
            created_at TEXT NOT NULL
        );
        """)
        # ترقية آمنة: قواعد بيانات قديمة قد تحتوي عمود token (نص صريح) بدل token_hash
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if 'token' in cols and 'token_hash' not in cols:
                conn.execute("ALTER TABLE users RENAME COLUMN token TO token_hash")
                print("⚠️  تمت ترقية جدول users: عمود token القديم كان يخزّن نصاً صريحاً — "
                      "التوكنات القديمة (إن وجدت) لم تعد صالحة، أصدر توكنات جديدة عبر /api/auth/create-user")
        except sqlite3.OperationalError:
            pass
        # ترقية آمنة لقواعد بيانات قديمة قد لا تحتوي هذه الأعمدة بعد (idempotent)
        for stmt in [
            "ALTER TABLE strategies ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE signals ADD COLUMN strategy_version INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE signals ADD COLUMN market_data_timestamp TEXT",
            "ALTER TABLE signals ADD COLUMN indicators_json TEXT",
            "ALTER TABLE signals ADD COLUMN news_snapshot_json TEXT",
            "ALTER TABLE signals ADD COLUMN ai_status TEXT DEFAULT 'skip'",
        ]:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass  # العمود موجود مسبقاً


# ---------- Strategies ----------
def create_strategy(user_id, name, market, mode, conditions, reset_conditions=None):
    with _lock, _conn() as conn:
        cur = conn.execute(
            "INSERT INTO strategies (user_id, name, market, mode, conditions_json, reset_conditions_json, active, created_at) "
            "VALUES (?,?,?,?,?,?,1,?)",
            (user_id, name, market, mode, json.dumps(conditions, ensure_ascii=False),
             json.dumps(reset_conditions, ensure_ascii=False) if reset_conditions else None,
             datetime.now().isoformat()))
        return cur.lastrowid


def list_strategies(user_id='default', active_only=False):
    with _lock, _conn() as conn:
        q = "SELECT * FROM strategies WHERE user_id=?"
        params = [user_id]
        if active_only:
            q += " AND active=1"
        rows = conn.execute(q, params).fetchall()
        return [_strategy_row_to_dict(r) for r in rows]


def get_strategy(strategy_id):
    with _lock, _conn() as conn:
        row = conn.execute("SELECT * FROM strategies WHERE id=?", (strategy_id,)).fetchone()
        return _strategy_row_to_dict(row) if row else None


def update_strategy(strategy_id, **fields):
    allowed = {'name', 'market', 'mode', 'conditions_json', 'reset_conditions_json', 'active'}
    version_bump_triggers = {'mode', 'conditions_json', 'reset_conditions_json'}
    sets, params = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?")
            params.append(v)
    if not sets:
        return False
    if any(k in version_bump_triggers for k in fields):
        # تغيير جوهري بالاستراتيجية -> ترقيم إصدار جديد؛ الإشارات القديمة تبقى محفوظة بإصدارها الأصلي
        sets.append("version = version + 1")
    params.append(strategy_id)
    with _lock, _conn() as conn:
        conn.execute(f"UPDATE strategies SET {', '.join(sets)} WHERE id=?", params)
    return True


def delete_strategy(strategy_id):
    with _lock, _conn() as conn:
        conn.execute("DELETE FROM strategies WHERE id=?", (strategy_id,))
        conn.execute("DELETE FROM alert_state WHERE strategy_id=?", (strategy_id,))


def _strategy_row_to_dict(row):
    import strategy_engine
    conditions = json.loads(row['conditions_json'])
    return {
        'id': row['id'], 'user_id': row['user_id'], 'name': row['name'],
        'market': row['market'], 'mode': row['mode'],
        'conditions': conditions,
        'type': strategy_engine.classify_strategy(conditions),
        'reset_conditions': json.loads(row['reset_conditions_json']) if row['reset_conditions_json'] else None,
        'active': bool(row['active']), 'version': row['version'], 'created_at': row['created_at'],
    }


def _hash_token(token):
    """HMAC-SHA256 مع Pepper من متغير بيئة — التوكن الحقيقي لا يُخزَّن أبداً، فقط هذا الـHash."""
    import hmac, hashlib
    pepper = os.environ.get('TOKEN_PEPPER')
    if not pepper:
        pepper = 'dev-only-insecure-pepper-set-TOKEN_PEPPER-env-var'
        print("⚠️  TOKEN_PEPPER غير مضبوط في متغيرات البيئة — يُستخدم Pepper تطويري غير آمن. "
              "اضبط TOKEN_PEPPER قبل أي استخدام حقيقي.")
    return hmac.new(pepper.encode('utf-8'), token.encode('utf-8'), hashlib.sha256).hexdigest()


def get_user_by_token(token):
    """يقارن Hash التوكن المُرسل مع المخزّن — التوكن نفسه لا يُقرأ من القاعدة أبداً."""
    token_hash = _hash_token(token)
    with _lock, _conn() as conn:
        row = conn.execute("SELECT user_id FROM users WHERE token_hash=?", (token_hash,)).fetchone()
        return row['user_id'] if row else None


def create_user(label=None):
    """
    يرجع التوكن الحقيقي مرة واحدة فقط هنا (وقت الإنشاء) — بعدها لا يمكن استرجاعه،
    فقط Hash موجود بقاعدة البيانات. المستخدم يجب يحفظه فوراً.
    """
    import uuid, secrets
    user_id, token = str(uuid.uuid4()), secrets.token_urlsafe(32)
    with _lock, _conn() as conn:
        conn.execute("INSERT INTO users (user_id, token_hash, label, created_at) VALUES (?,?,?,?)",
                     (user_id, _hash_token(token), label, datetime.now().isoformat()))
    return {'user_id': user_id, 'token': token, 'label': label}  # آخر مرة يظهر فيها التوكن الحقيقي


def list_users():
    with _lock, _conn() as conn:
        rows = conn.execute("SELECT user_id, label, created_at FROM users ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]  # لا يوجد عمود token هنا إطلاقاً — Hash فقط بالقاعدة


# ---------- Watchlist ----------
def add_to_watchlist(user_id, symbol, market):
    with _lock, _conn() as conn:
        try:
            conn.execute("INSERT INTO watchlist (user_id, symbol, market, added_at) VALUES (?,?,?,?)",
                         (user_id, symbol, market, datetime.now().isoformat()))
        except sqlite3.IntegrityError:
            pass  # موجود مسبقاً


def remove_from_watchlist(user_id, symbol, market):
    with _lock, _conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE user_id=? AND symbol=? AND market=?", (user_id, symbol, market))


def get_watchlist(user_id='default'):
    with _lock, _conn() as conn:
        rows = conn.execute("SELECT symbol, market, added_at FROM watchlist WHERE user_id=?", (user_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------- Alert state machine ----------
def get_alert_state(user_id, strategy_id, symbol):
    with _lock, _conn() as conn:
        row = conn.execute(
            "SELECT * FROM alert_state WHERE user_id=? AND strategy_id=? AND symbol=?",
            (user_id, strategy_id, symbol)).fetchone()
        if not row:
            return None
        d = dict(row)
        d['last_snapshot'] = json.loads(d['last_snapshot_json']) if d['last_snapshot_json'] else None
        return d


def set_alert_state(user_id, strategy_id, symbol, state, score=None, snapshot=None, notified=False):
    now = datetime.now().isoformat()
    with _lock, _conn() as conn:
        existing = conn.execute(
            "SELECT last_notified_at FROM alert_state WHERE user_id=? AND strategy_id=? AND symbol=?",
            (user_id, strategy_id, symbol)).fetchone()
        last_notified_at = existing['last_notified_at'] if existing else None
        if notified:
            last_notified_at = now
        conn.execute("""
            INSERT INTO alert_state (user_id, strategy_id, symbol, state, last_score, last_snapshot_json, last_notified_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id, strategy_id, symbol) DO UPDATE SET
                state=excluded.state, last_score=excluded.last_score,
                last_snapshot_json=excluded.last_snapshot_json,
                last_notified_at=excluded.last_notified_at, updated_at=excluded.updated_at
        """, (user_id, strategy_id, symbol, state, score,
              json.dumps(snapshot, ensure_ascii=False) if snapshot else None, last_notified_at, now))


# ---------- Alert history ----------
def add_alert_history(user_id, strategy_id, strategy_name, symbol, market, alert_kind,
                       score, triggered_conditions, snapshot, ai_explanation=None):
    with _lock, _conn() as conn:
        cur = conn.execute("""
            INSERT INTO alert_history (user_id, strategy_id, strategy_name, symbol, market, alert_kind,
                score, triggered_conditions_json, snapshot_json, ai_explanation_json, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (user_id, strategy_id, strategy_name, symbol, market, alert_kind, score,
              json.dumps(triggered_conditions, ensure_ascii=False),
              json.dumps(snapshot, ensure_ascii=False),
              json.dumps(ai_explanation, ensure_ascii=False) if ai_explanation else None,
              datetime.now().isoformat()))
        return cur.lastrowid


def get_alert_history(user_id='default', symbol=None, limit=50):
    with _lock, _conn() as conn:
        q = "SELECT * FROM alert_history WHERE user_id=?"
        params = [user_id]
        if symbol:
            q += " AND symbol=?"
            params.append(symbol)
        q += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d['triggered_conditions'] = json.loads(d['triggered_conditions_json']) if d['triggered_conditions_json'] else []
            d['snapshot'] = json.loads(d['snapshot_json']) if d['snapshot_json'] else {}
            d['ai_explanation'] = json.loads(d['ai_explanation_json']) if d['ai_explanation_json'] else None
            out.append(d)
        return out


# ---------- AI cache (caching + dedup, TTL بالدقائق) ----------
def ai_cache_get(cache_key):
    with _lock, _conn() as conn:
        row = conn.execute("SELECT response_json, expires_at FROM ai_cache WHERE cache_key=?", (cache_key,)).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row['expires_at']) < datetime.now():
            conn.execute("DELETE FROM ai_cache WHERE cache_key=?", (cache_key,))
            return None
        return json.loads(row['response_json'])


def ai_cache_set(cache_key, response, ttl_minutes=45):
    from datetime import timedelta
    now = datetime.now()
    with _lock, _conn() as conn:
        conn.execute("""
            INSERT INTO ai_cache (cache_key, response_json, created_at, expires_at) VALUES (?,?,?,?)
            ON CONFLICT(cache_key) DO UPDATE SET response_json=excluded.response_json,
                created_at=excluded.created_at, expires_at=excluded.expires_at
        """, (cache_key, json.dumps(response, ensure_ascii=False), now.isoformat(),
              (now + timedelta(minutes=ttl_minutes)).isoformat()))


init_db()


# ---------- Signal Lifecycle (هوية مستقلة لكل إشارة، منفصلة عن alert_state البسيطة) ----------
def create_signal(user_id, strategy_id, strategy_name, strategy_version, symbol, market, timeframe,
                   market_data_timestamp, trigger_price, score, conditions, snapshot, indicators=None,
                   entry=None, confirmation=None, invalidation=None, exit_=None, news_snapshot=None,
                   ai_explanation=None, ai_status='skip'):
    import uuid
    signal_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    with _lock, _conn() as conn:
        conn.execute("""
            INSERT INTO signals (signal_id, user_id, strategy_id, strategy_name, strategy_version,
                symbol, market, timeframe, trigger_timestamp, market_data_timestamp, trigger_price,
                score, conditions_json, snapshot_json, indicators_json,
                entry_json, confirmation_json, invalidation_json, exit_json, news_snapshot_json,
                ai_explanation_json, ai_status, status, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ACTIVE',?)
        """, (signal_id, user_id, strategy_id, strategy_name, strategy_version, symbol, market,
              timeframe, now, market_data_timestamp, trigger_price, score,
              json.dumps(conditions, ensure_ascii=False), json.dumps(snapshot, ensure_ascii=False),
              json.dumps(indicators, ensure_ascii=False) if indicators else None,
              json.dumps(entry, ensure_ascii=False) if entry else None,
              json.dumps(confirmation, ensure_ascii=False) if confirmation else None,
              json.dumps(invalidation, ensure_ascii=False) if invalidation else None,
              json.dumps(exit_, ensure_ascii=False) if exit_ else None,
              json.dumps(news_snapshot, ensure_ascii=False) if news_snapshot else None,
              json.dumps(ai_explanation, ensure_ascii=False) if ai_explanation else None,
              ai_status, now))
        return signal_id


def update_signal_ai(signal_id, ai_explanation, ai_status):
    """لتحديث نتيجة AI لاحقاً (إعادة طلب تحليل يدوياً) بدون التأثير على بيانات الإشارة الأصلية."""
    with _lock, _conn() as conn:
        conn.execute("UPDATE signals SET ai_explanation_json=?, ai_status=?, updated_at=? WHERE signal_id=?",
                     (json.dumps(ai_explanation, ensure_ascii=False) if ai_explanation else None,
                      ai_status, datetime.now().isoformat(), signal_id))


def update_signal_status(signal_id, status, outcome=None):
    """status: ACTIVE / CONFIRMED / INVALIDATED / CLOSED"""
    with _lock, _conn() as conn:
        if outcome is not None:
            conn.execute("UPDATE signals SET status=?, outcome_json=?, updated_at=? WHERE signal_id=?",
                         (status, json.dumps(outcome, ensure_ascii=False), datetime.now().isoformat(), signal_id))
        else:
            conn.execute("UPDATE signals SET status=?, updated_at=? WHERE signal_id=?",
                         (status, datetime.now().isoformat(), signal_id))


def _signal_row_to_dict(row):
    d = dict(row)
    for f in ('conditions_json', 'snapshot_json', 'indicators_json', 'entry_json', 'confirmation_json',
              'invalidation_json', 'exit_json', 'news_snapshot_json', 'ai_explanation_json', 'outcome_json'):
        key = f.replace('_json', '')
        d[key] = json.loads(d[f]) if d[f] else None
    return d


def get_signal(signal_id):
    with _lock, _conn() as conn:
        row = conn.execute("SELECT * FROM signals WHERE signal_id=?", (signal_id,)).fetchone()
        return _signal_row_to_dict(row) if row else None


def list_signals(user_id='default', strategy_id=None, symbol=None, status=None, market=None,
                  min_score=None, limit=50):
    with _lock, _conn() as conn:
        q = "SELECT * FROM signals WHERE user_id=?"
        params = [user_id]
        if strategy_id:
            q += " AND strategy_id=?"; params.append(strategy_id)
        if symbol:
            q += " AND symbol=?"; params.append(symbol)
        if status:
            q += " AND status=?"; params.append(status)
        if market:
            q += " AND market=?"; params.append(market)
        if min_score is not None:
            q += " AND score>=?"; params.append(min_score)
        q += " ORDER BY trigger_timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()
        return [_signal_row_to_dict(r) for r in rows]


def signals_per_strategy(user_id='default'):
    """لعرض 'Active Strategies' Live بعدد إشاراتها الفعلي — بدون Win Rate (Backtesting لم يُبنَ بعد)."""
    with _lock, _conn() as conn:
        rows = conn.execute("""
            SELECT strategy_id, strategy_name, COUNT(*) as signal_count
            FROM signals WHERE user_id=? GROUP BY strategy_id
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def dashboard_counts(user_id='default'):
    """أرقام بطاقات Opportunity Summary — محسوبة بالكامل هنا (Backend)، الواجهة تعرضها فقط."""
    today = datetime.now().strftime('%Y-%m-%d')
    with _lock, _conn() as conn:
        today_signals = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE user_id=? AND trigger_timestamp LIKE ?",
            (user_id, f'{today}%')).fetchone()[0]
        high_score = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE user_id=? AND score>=75 AND status='ACTIVE'",
            (user_id,)).fetchone()[0]
        active_total = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE user_id=? AND status='ACTIVE'", (user_id,)).fetchone()[0]
        confirmed = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE user_id=? AND status='CONFIRMED'", (user_id,)).fetchone()[0]
        invalidated_today = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE user_id=? AND status='INVALIDATED' AND updated_at LIKE ?",
            (user_id, f'{today}%')).fetchone()[0]
    return {'today_signals': today_signals, 'high_score': high_score, 'active_total': active_total,
            'confirmed': confirmed, 'invalidated_today': invalidated_today}
