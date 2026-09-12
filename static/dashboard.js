const REFRESH_MS = 45000; // 45 ثانية — ضمن نطاق 30-60 المطلوب


// ---------------- Rendering helpers ----------------
function renderMarketStatus(ms) {
    const setPill = (pillId, stateId, info) => {
        document.getElementById(pillId).className = 'market-pill ' + (info.open ? 'open' : 'closed');
        document.getElementById(stateId).textContent = info.open ? 'مفتوح' : 'مغلق';
    };
    setPill('pillSaudi', 'saudiState', ms.saudi);
    setPill('pillUs', 'usState', ms.us);
}

function renderCounts(c) {
    document.getElementById('statToday').textContent = c.today_signals;
    document.getElementById('statHigh').textContent = c.high_score;
    document.getElementById('statActive').textContent = c.active_total;
    document.getElementById('statConfirmed').textContent = c.confirmed;
    document.getElementById('statInvalidated').textContent = c.invalidated_today;
}

function renderOpportunities(list) {
    const items = list.map(s => ({
        symbol: s.symbol, strategy_name: s.strategy_name, score: s.score,
        display_status: s.display_status, conditions: s.satisfied_conditions,
        price_text: `السعر وقت الإشارة: ${s.trigger_price ?? '—'}`,
    }));
    renderOppCards(document.getElementById('topOpportunities'), items,
        'لا توجد فرص نشطة حالياً — سيظهر هنا أي سهم تحقق فيه شروط استراتيجياتك.', 'dash-');
}

function renderStrategies(list) {
    const el = document.getElementById('strategiesList');
    if (!list.length) { el.innerHTML = emptyRow('لا توجد استراتيجيات لها إشارات بعد.'); return; }
    el.innerHTML = list.map(s => `
        <div class="strategy-row">
            <span class="name">${s.strategy_name || ('استراتيجية #' + s.strategy_id)}</span>
            <span class="count">${s.signal_count} إشارة</span>
        </div>`).join('');
}

function renderWatchlist(list) {
    const el = document.getElementById('watchlist');
    if (!list.length) { el.innerHTML = emptyRow('قائمة المراقبة فاضية — أضف أسهماً عبر API الـWatchlist.'); return; }
    el.innerHTML = list.map(w => `
        <div class="watch-row">
            <div class="w-left">
                <span class="w-symbol">${w.symbol}</span>
                <span class="w-time">${w.data_timestamp ? new Date(w.data_timestamp).toLocaleString('ar-SA') : 'لا توجد بيانات'}</span>
            </div>
            <div class="w-right">
                <div class="w-price">${w.price != null ? w.price : 'N/A'}</div>
                <div class="w-signal">${w.active_signal_score != null ? (w.active_strategy + ' · ' + w.active_signal_score + '/100') : 'لا توجد إشارة نشطة'}</div>
            </div>
        </div>`).join('');
}

function renderAlerts(list) {
    const el = document.getElementById('latestAlerts');
    if (!list.length) { el.innerHTML = emptyRow('لا توجد تنبيهات بعد.'); return; }
    el.innerHTML = list.map(a => {
        const time = new Date(a.created_at);
        const hh = String(time.getHours()).padStart(2, '0');
        const mm = String(time.getMinutes()).padStart(2, '0');
        return `
        <div class="alert-row">
            <span class="a-time">${hh}:${mm}</span>
            <div class="a-mid">
                <div class="a-symbol">${a.symbol}</div>
                <div class="a-strategy">${a.strategy_name || '—'}</div>
            </div>
            <span class="a-score">${a.score ?? '—'}/100</span>
        </div>`;
    }).join('');
}

// ---------------- Main loop ----------------
let refreshTimer = null;

async function loadDashboard() {
    try {
        const r = await fetch('/api/dashboard-summary', { headers: authHeaders() });
        if (r.status === 401) {
            clearToken();
            location.reload();
            return;
        }
        const data = await r.json();
        renderMarketStatus(data.market_status);
        renderCounts(data.counts);
        renderOpportunities(data.top_opportunities);
        renderStrategies(data.active_strategies);
        renderWatchlist(data.watchlist);
        renderAlerts(data.latest_alerts);
        document.getElementById('lastRefresh').textContent =
            'آخر تحديث: ' + new Date().toLocaleTimeString('ar-SA');
    } catch (e) {
        showToast('تعذّر تحديث البيانات — سيُعاد المحاولة تلقائياً');
        console.error(e);
    }
}

function startDashboard() {
    loadDashboard();
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(loadDashboard, REFRESH_MS);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) loadDashboard();
    });
}

initAuthGate(startDashboard);
