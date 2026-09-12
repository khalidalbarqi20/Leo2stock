// مشترك بين كل صفحات التطبيق — إدارة التوكن، الـauth gate، والتنقل السفلي
const TOKEN_KEY = 'leo2stock_token';

function getToken() { return localStorage.getItem(TOKEN_KEY); }
function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
function clearToken() { localStorage.removeItem(TOKEN_KEY); }

function authHeaders() {
    return { 'Authorization': 'Bearer ' + getToken() };
}

function showToast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 1800);
}

async function testToken() {
    try {
        const r = await fetch('/api/strategies', { headers: authHeaders() });
        return r.status !== 401;
    } catch (e) { return false; }
}

// onSuccess: دالة تُستدعى بعد التحقق من التوكن (كل صفحة تمرر دالة التحميل الخاصة فيها)
function initAuthGate(onSuccess) {
    const gate = document.getElementById('authGate');
    const app = document.getElementById('app');
    const existing = getToken();
    if (existing) {
        gate.style.display = 'none';
        app.style.display = 'block';
        onSuccess();
        return;
    }
    document.getElementById('tokenSubmit').addEventListener('click', async () => {
        const val = document.getElementById('tokenInput').value.trim();
        const errEl = document.getElementById('authError');
        errEl.textContent = '';
        if (!val) { errEl.textContent = 'أدخل التوكن أولاً'; return; }
        setToken(val);
        const ok = await testToken();
        if (!ok) {
            clearToken();
            errEl.textContent = 'التوكن غير صحيح — تأكد منه مع الأدمن';
            return;
        }
        gate.style.display = 'none';
        app.style.display = 'block';
        onSuccess();
    });
}

document.querySelectorAll('.nav-item.soon').forEach(el => {
    el.addEventListener('click', (e) => {
        e.preventDefault();
        if (el.id === 'settingsNav') {
            if (confirm('تسجيل الخروج ومسح التوكن المحفوظ؟')) {
                clearToken();
                location.reload();
            }
            return;
        }
        showToast(`صفحة "${el.dataset.name}" قريباً`);
    });
});

// ---------------- Opportunity Card Rendering (مشترك بين Dashboard والفاحص) ----------------
function emptyRow(text) {
    return `<div class="empty-state">${text}</div>`;
}

function statusClass(status) {
    switch (status) {
        case 'ENTRY SETUP': return 'entry';
        case 'CONFIRMATION REQUIRED': return 'confirm';
        case 'CONFIRMED': return 'confirmed';
        case 'INVALIDATED': return 'invalidated';
        case 'CLOSED': return 'closed';
        default: return 'entry';
    }
}

// items: [{symbol, strategy_name, score, display_status, price_text, conditions: []}]
function renderOppCards(container, items, emptyText, idPrefix) {
    if (!items.length) { container.innerHTML = emptyRow(emptyText); return; }
    container.innerHTML = items.map((s, i) => {
        const cls = statusClass(s.display_status);
        const conditionsHtml = (s.conditions && s.conditions.length)
            ? `<ul>${s.conditions.map(c => `<li>${c}</li>`).join('')}</ul>`
            : `<p>لا توجد تفاصيل شروط محفوظة لهذه الإشارة.</p>`;
        return `
        <div class="opp-card">
            <div class="opp-top">
                <div>
                    <div class="opp-symbol">${s.symbol}</div>
                    <div class="opp-strategy">${s.strategy_name || '—'}</div>
                </div>
                <div class="opp-score">
                    <div class="num">${s.score ?? '—'}</div>
                    <div class="lbl">/100</div>
                </div>
            </div>
            <span class="opp-status ${cls}">${s.display_status}</span>
            <div class="opp-price">${s.price_text || ''}</div>
            <button class="opp-why-toggle" data-idx="${idPrefix}${i}">لماذا ظهرت؟ ⌄</button>
            <div class="opp-why" id="why-${idPrefix}${i}">${conditionsHtml}</div>
        </div>`;
    }).join('');

    container.querySelectorAll('.opp-why-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('why-' + btn.dataset.idx).classList.toggle('show');
        });
    });
}
