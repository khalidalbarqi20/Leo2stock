let allStrategies = [];
let activeTab = 'all';

function strategiesForTab() {
    const market = document.getElementById('marketSelect').value;
    return allStrategies.filter(s =>
        (activeTab === 'all' || s.type === activeTab) &&
        (s.market === market || s.market === 'both'));
}

function populateStrategySelect() {
    const sel = document.getElementById('strategySelect');
    const list = strategiesForTab();
    sel.innerHTML = '<option value="">— اختر استراتيجية —</option>' +
        list.map(s => `<option value="${s.id}">${s.name} (${s.type})</option>`).join('');
    document.getElementById('scanBtn').disabled = list.length === 0;
    if (!list.length) {
        document.getElementById('scanNote').textContent = 'لا توجد استراتيجيات من هذا النوع لهذا السوق بعد.';
    } else {
        document.getElementById('scanNote').textContent = '';
    }
}

async function loadStrategies() {
    try {
        const r = await fetch('/api/strategies', { headers: authHeaders() });
        if (r.status === 401) { clearToken(); location.reload(); return; }
        allStrategies = await r.json();
        populateStrategySelect();
    } catch (e) {
        showToast('تعذّر تحميل الاستراتيجيات');
        console.error(e);
    }
}

// ---------------- تبويبات النوع ----------------
document.querySelectorAll('#typeTabs .tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('#typeTabs .tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        activeTab = tab.dataset.type;
        populateStrategySelect();
        loadAllSignals();
    });
});

document.getElementById('marketSelect').addEventListener('change', () => {
    populateStrategySelect();
    loadAllSignals();
});

// ---------------- فحص حي (عبر الباك إند فقط — لا يوجد اتصال مباشر بـYahoo من المتصفح) ----------------
document.getElementById('scanBtn').addEventListener('click', async () => {
    const sid = document.getElementById('strategySelect').value;
    if (!sid) return;
    const minScore = parseInt(document.getElementById('minScoreInput').value || '0', 10);
    const btn = document.getElementById('scanBtn');
    const note = document.getElementById('scanNote');
    btn.disabled = true;
    note.textContent = 'جارٍ الفحص عبر الباك إند... قد يأخذ لحظات';

    try {
        const r = await fetch(`/api/scan/${sid}`, { headers: authHeaders() });
        if (r.status === 401) { clearToken(); location.reload(); return; }
        const data = await r.json();
        if (data.error) {
            note.textContent = 'خطأ: ' + data.error;
            document.getElementById('scanResults').innerHTML = '';
            return;
        }
        const candidates = (data.candidates || []).filter(c => (c.score_100 ?? 0) >= minScore);
        note.textContent = `تم فحص ${data.scanned_count} سهم — وُجد ${candidates.length} فرصة` +
            (data.unavailable && data.unavailable.length ? ` (تعذّر جلب بيانات ${data.unavailable.length} سهم)` : '');

        const items = candidates.map(c => ({
            symbol: c.symbol, strategy_name: data.strategy_name, score: c.score_100,
            display_status: 'ENTRY SETUP', // إشارة جديدة تواً — بدون بيانات تأكيد إضافية بهذه المرحلة
            conditions: c.satisfied, price_text: `السعر الحالي: ${c.price ?? '—'} ${c.currency || ''}`,
        }));
        renderOppCards(document.getElementById('scanResults'), items,
            'ما فيه أسهم مطابقة للشروط حالياً.', 'scan-');
    } catch (e) {
        note.textContent = 'تعذّر إتمام الفحص — حاول مرة ثانية';
        console.error(e);
    } finally {
        btn.disabled = false;
    }
});

// ---------------- تصفح الإشارات المحفوظة ----------------
async function loadAllSignals() {
    const market = document.getElementById('marketSelect').value;
    const status = document.getElementById('statusFilter').value;
    const params = new URLSearchParams({ market, limit: '30' });
    if (status) params.set('status', status);

    try {
        const r = await fetch('/api/signals?' + params.toString(), { headers: authHeaders() });
        if (r.status === 401) { clearToken(); location.reload(); return; }
        let signals = await r.json();

        if (activeTab !== 'all') {
            const idsOfType = new Set(allStrategies.filter(s => s.type === activeTab).map(s => s.id));
            signals = signals.filter(s => idsOfType.has(s.strategy_id));
        }

        const items = signals.map(s => ({
            symbol: s.symbol, strategy_name: s.strategy_name, score: s.score,
            display_status: s.display_status, conditions: s.conditions,
            price_text: `السعر وقت الإشارة: ${s.trigger_price ?? '—'}`,
        }));
        renderOppCards(document.getElementById('allSignals'), items, 'لا توجد إشارات محفوظة بهذا الفلتر.', 'all-');
    } catch (e) {
        showToast('تعذّر تحميل الإشارات');
        console.error(e);
    }
}

document.getElementById('statusFilter').addEventListener('change', loadAllSignals);

async function startScanner() {
    await loadStrategies();
    await loadAllSignals();
}

initAuthGate(startScanner);
