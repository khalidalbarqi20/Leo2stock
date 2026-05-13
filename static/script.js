/* ============================================
   Leo2Stock — Main JavaScript (Fixed)
   ============================================ */

// ======= State =======
let currentMarket = 'all';
let currentSymbol = null;
let currentData = null;
let priceChart = null;
let rsiChart = null;
let macdChart = null;
let alertInterval = null;

// ======= Init =======
document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    loadMarketOverview();
    renderWatchlistBadge();
    renderAlertsBadge();
    startAlertChecker();

    document.getElementById('symbolInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchStock();
    });

    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
});

// ======= Theme =======
function loadTheme() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.body.className = saved;
    document.getElementById('themeIcon').textContent = saved === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
    const isDark = document.body.classList.contains('dark');
    document.body.className = isDark ? 'light' : 'dark';
    localStorage.setItem('theme', isDark ? 'light' : 'dark');
    document.getElementById('themeIcon').textContent = isDark ? '🌙' : '☀️';
    if (currentData) redrawCharts(currentData);
}

function getChartColors() {
    const isDark = document.body.classList.contains('dark');
    return {
        grid: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
        text: isDark ? '#8892a4' : '#5a6478',
        accent: '#00e5ff',
        positive: '#00e676',
        negative: '#ff1744',
        warning: '#ffab40',
    };
}

// ======= Market Switcher =======
function switchMarket(market, el) {
    currentMarket = market;
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    loadMarketOverview();
}

// ======= Search =======
async function searchStock() {
    const symbol = document.getElementById('symbolInput').value.trim().toUpperCase();
    if (!symbol) return;

    showLoading(true);

    try {
        const res = await fetch(`./api/analyze/${symbol}`);
        const data = await res.json();

        if (data.error) {
            showError(data.error);
            showLoading(false);
            return;
        }

        currentSymbol = symbol;
        currentData = data;
        displayResult(data);
    } catch (err) {
        showError('حدث خطأ في الاتصال بالخادم');
        console.error(err);
    }

    showLoading(false);
}

// ======= Display Result =======
function displayResult(data) {
    const analysis = data.analysis || {};
    const indicators = analysis.indicators || {};
    const rec = data.recommendation || {};
    const bb = indicators.bollinger || {};
    const macd = indicators.macd || {};
    const stoch = indicators.stochastic || {};
    const fund_reason = analysis.fundamental_reason || {};

    const isPositive = data.change >= 0;

    // Header
    document.getElementById('res-symbol').textContent = data.symbol;
    document.getElementById('res-name').textContent = data.name || data.symbol;
    document.getElementById('res-sector').textContent = data.sector || 'غير محدد';
    document.getElementById('res-market').textContent = data.market === 'saudi' ? '🇸🇦 سعودي' : '🇺🇸 أمريكي';
    document.getElementById('res-price').textContent = formatPrice(data.current, data.currency);
    const changeEl = document.getElementById('res-change');
    changeEl.textContent = `${isPositive ? '+' : ''}${data.change}%`;
    changeEl.className = `price-delta ${isPositive ? 'positive' : 'negative'}`;
    document.getElementById('res-currency').textContent = data.currency || 'USD';

    // Stats
    document.getElementById('res-open').textContent = formatPrice(data.open, data.currency);
    document.getElementById('res-high').textContent = formatPrice(data.high, data.currency);
    document.getElementById('res-low').textContent = formatPrice(data.low, data.currency);
    document.getElementById('res-volume').textContent = formatVolume(data.volume);
    document.getElementById('res-high52').textContent = formatPrice(data.high_52w, data.currency);
    document.getElementById('res-low52').textContent = formatPrice(data.low_52w, data.currency);

    // Indicators
    const rsi = indicators.rsi || 50;
    document.getElementById('ind-rsi').textContent = rsi;
    const rsiBar = document.getElementById('rsi-bar');
    rsiBar.style.width = `${Math.min(rsi, 100)}%`;
    rsiBar.style.background = rsi < 30 ? '#00e676' : rsi > 70 ? '#ff1744' : '#00e5ff';
    document.getElementById('sig-rsi').textContent = rsi < 30 ? '🟢 تشبع بيعي' : rsi > 70 ? '🔴 تشبع شرائي' : '⚪ محايد';
    styleSignal('sig-rsi', rsi < 30 ? 'buy' : rsi > 70 ? 'sell' : 'neutral');

    const price = data.current;
    const sma20 = indicators.sma_20;
    const sma50 = indicators.sma_50;
    const sma200 = indicators.sma_200;

    document.getElementById('ind-sma20').textContent = formatPrice(sma20, data.currency);
    setSignal('sig-sma20', price > sma20 ? 'buy' : 'sell', price > sma20 ? '📈 فوق' : '📉 تحت');

    document.getElementById('ind-sma50').textContent = formatPrice(sma50, data.currency);
    setSignal('sig-sma50', price > sma50 ? 'buy' : 'sell', price > sma50 ? '📈 فوق' : '📉 تحت');

    document.getElementById('ind-sma200').textContent = formatPrice(sma200, data.currency);
    setSignal('sig-sma200', price > sma200 ? 'buy' : 'sell', price > sma200 ? '📈 فوق' : '📉 تحت');

    document.getElementById('ind-macd').textContent = macd.macd || '—';
    setSignal('sig-macd', macd.histogram > 0 ? 'buy' : 'sell', macd.histogram > 0 ? '📈 صاعد' : '📉 هابط');

    document.getElementById('ind-bb-upper').textContent = formatPrice(bb.upper, data.currency);
    document.getElementById('ind-bb-lower').textContent = formatPrice(bb.lower, data.currency);
    const bbSig = price >= bb.upper ? 'sell' : price <= bb.lower ? 'buy' : 'neutral';
    setSignal('sig-bb', bbSig, price >= bb.upper ? '⚠️ حد علوي' : price <= bb.lower ? '⚠️ حد سفلي' : '✅ وسط');

    document.getElementById('ind-atr').textContent = formatPrice(indicators.atr, data.currency);
    document.getElementById('ind-stoch-k').textContent = stoch.k || '—';
    setSignal('sig-stoch', stoch.k < 20 ? 'buy' : stoch.k > 80 ? 'sell' : 'neutral',
              stoch.k < 20 ? '🟢 تشبع بيعي' : stoch.k > 80 ? '🔴 تشبع شرائي' : '⚪ محايد');

    // Fundamental
    document.getElementById('fund-cap').textContent = formatMarketCap(data.market_cap);
    const pe = data.pe_ratio;
    document.getElementById('fund-pe').textContent = pe ? pe.toFixed(1) : 'N/A';
    if (pe) {
        document.getElementById('fund-pe-note').textContent = pe < 15 ? 'منخفض ← جيد' : pe > 30 ? 'مرتفع ← تقييم عالٍ' : 'معتدل';
    }
    document.getElementById('fund-sector').textContent = data.sector || 'غير محدد';
    document.getElementById('fund-support').textContent = formatPrice(analysis.support, data.currency);
    document.getElementById('fund-resistance').textContent = formatPrice(analysis.resistance, data.currency);

    const trendMap = {
        strong_bullish: '🚀 صاعد قوي',
        bullish: '📈 صاعد',
        neutral: '↔️ محايد',
        bearish: '📉 هابط',
        strong_bearish: '🔻 هابط قوي'
    };
    document.getElementById('fund-trend').textContent = trendMap[analysis.trend] || '—';

    // Fundamental Reason - سبب الهبوط/الارتفاع
    const fundReasonEl = document.getElementById('fund-reason');
    if (fundReasonEl) {
        fundReasonEl.innerHTML = `
            <div class="fund-reason-box ${fund_reason.direction || 'neutral'}">
                <h4>${fund_reason.title || 'الوضع الحالي'}</h4>
                <p class="fund-summary">${fund_reason.summary || ''}</p>
                ${fund_reason.reasons ? '<ul>' + fund_reason.reasons.map(r => `<li>${r}</li>`).join('') + '</ul>' : ''}
            </div>
        `;
    }

    // Recommendation
    const recCard = document.getElementById('rec-card');
    const action = rec.action || 'محايد';
    document.getElementById('rec-action').textContent = action;
    document.getElementById('rec-score').textContent = `نقاط: ${rec.score >= 0 ? '+' : ''}${rec.score}`;
    recCard.className = 'card rec-card';
    if (action.includes('شراء قوي')) recCard.classList.add('rec-strong-buy');
    else if (action.includes('شراء')) recCard.classList.add('rec-buy');
    else if (action.includes('بيع قوي')) recCard.classList.add('rec-strong-sell');
    else if (action.includes('بيع')) recCard.classList.add('rec-sell');
    else recCard.classList.add('rec-neutral');

    // Signals
    const signalsList = document.getElementById('signals-list');
    if (analysis.signals && analysis.signals.length) {
        signalsList.innerHTML = analysis.signals.map(s => `<li>${s}</li>`).join('');
    } else {
        signalsList.innerHTML = '<li class="no-signals">لا توجد إشارات واضحة حالياً</li>';
    }

    // Draw Charts
    drawPriceChart(data);
    drawRsiChart(data);
    drawMacdChart(data);

    // Show result
    document.getElementById('result').classList.remove('hidden');
    document.getElementById('result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ======= Charts =======
function drawPriceChart(data) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    const c = getChartColors();

    // استخدم البيانات من الـ API
    const prices = data.prices_list || [];
    const dates = data.dates_list || [];
    const sma20 = data.sma20_list || [];
    const sma50 = data.sma50_list || [];

    if (!prices.length) {
        console.warn('No price data for chart');
        return;
    }

    if (priceChart) priceChart.destroy();

    // إنشاء datasets
    const datasets = [{
        label: 'السعر',
        data: prices,
        borderColor: c.accent,
        backgroundColor: 'rgba(0,229,255,0.05)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
    }];

    // SMA 20
    if (sma20.some(v => v !== null)) {
        datasets.push({
            label: 'SMA 20',
            data: sma20,
            borderColor: c.warning,
            borderWidth: 1.5,
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            borderDash: [4, 2],
        });
    }

    // SMA 50
    if (sma50.some(v => v !== null)) {
        datasets.push({
            label: 'SMA 50',
            data: sma50,
            borderColor: c.negative,
            borderWidth: 1.5,
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            borderDash: [6, 3],
        });
    }

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: {
                    labels: { color: c.text, font: { family: 'Cairo', size: 11 }, boxWidth: 16 }
                },
                tooltip: {
                    backgroundColor: 'rgba(20,29,46,0.95)',
                    titleColor: c.text,
                    bodyColor: c.text,
                    borderColor: c.accent,
                    borderWidth: 1,
                    padding: 10,
                    rtl: true,
                }
            },
            scales: {
                x: {
                    grid: { color: c.grid },
                    ticks: { color: c.text, font: { size: 10 }, maxTicksLimit: 8 }
                },
                y: {
                    grid: { color: c.grid },
                    ticks: { color: c.text, font: { size: 10 } },
                }
            }
        }
    });
}

function drawRsiChart(data) {
    const ctx = document.getElementById('rsiChart').getContext('2d');
    const c = getChartColors();
    const rsiList = data.rsi_list || [];
    const dates = data.dates_list || [];

    if (!rsiList.length) {
        console.warn('No RSI data for chart');
        return;
    }

    if (rsiChart) rsiChart.destroy();

    rsiChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'RSI',
                data: rsiList,
                borderColor: '#7c4dff',
                backgroundColor: 'rgba(124,77,255,0.08)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                pointHoverRadius: 4,
            }]
        },
        options: {
            responsive: true,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(20,29,46,0.95)',
                    titleColor: c.text,
                    bodyColor: c.text,
                    borderColor: '#7c4dff',
                    borderWidth: 1,
                    padding: 10,
                    rtl: true,
                }
            },
            scales: {
                x: {
                    display: false,
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: c.grid },
                    ticks: { color: c.text, font: { size: 10 } },
                }
            }
        }
    });
}

function drawMacdChart(data) {
    const ctx = document.getElementById('macdChart').getContext('2d');
    const c = getChartColors();
    const macdList = data.macd_list || [];
    const signalList = data.signal_list || [];
    const histList = data.histogram_list || [];
    const dates = data.dates_list || [];

    if (!macdList.length) {
        console.warn('No MACD data for chart');
        return;
    }

    if (macdChart) macdChart.destroy();

    // Histogram colors
    const histColors = histList.map(v => v >= 0 ? 'rgba(0,230,118,0.6)' : 'rgba(255,23,68,0.6)');

    macdChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Histogram',
                    data: histList,
                    backgroundColor: histColors,
                    type: 'bar',
                    order: 2,
                },
                {
                    label: 'MACD',
                    data: macdList,
                    borderColor: c.accent,
                    borderWidth: 1.5,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 0,
                    type: 'line',
                    order: 1,
                },
                {
                    label: 'Signal',
                    data: signalList,
                    borderColor: c.warning,
                    borderWidth: 1.5,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 0,
                    type: 'line',
                    order: 0,
                }
            ]
        },
        options: {
            responsive: true,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: {
                    labels: { color: c.text, font: { family: 'Cairo', size: 11 }, boxWidth: 16 }
                },
                tooltip: {
                    backgroundColor: 'rgba(20,29,46,0.95)',
                    titleColor: c.text,
                    bodyColor: c.text,
                    borderColor: c.accent,
                    borderWidth: 1,
                    padding: 10,
                    rtl: true,
                }
            },
            scales: {
                x: {
                    display: false,
                },
                y: {
                    grid: { color: c.grid },
                    ticks: { color: c.text, font: { size: 10 } },
                }
            }
        }
    });
}

function redrawCharts(data) {
    if (!data) return;
    drawPriceChart(data);
    drawRsiChart(data);
    drawMacdChart(data);
}

function updateChartPeriod(period, btn) {
    document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (!currentSymbol) return;

    fetch(`./api/chart-data/${currentSymbol}?period=${period}`)
        .then(r => r.json())
        .then(d => {
            if (d && !d.error) {
                currentData = { ...currentData, ...d };
                drawPriceChart(currentData);
                drawRsiChart(currentData);
                drawMacdChart(currentData);
            }
        })
        .catch(err => console.error('Chart data error:', err));
}

// ======= Market Overview =======
async function loadMarketOverview() {
    try {
        const res = await fetch('./api/market-overview');
        const data = await res.json();

        const grid = document.getElementById('marketsGrid');
        grid.innerHTML = '';

        const show = (market, d) => {
            if (!d || !d.length) return;
            const block = document.createElement('div');
            block.className = 'market-block';
            block.innerHTML = `
                <div class="market-title">${market === 'saudi' ? '🇸🇦 السوق السعودي' : '🇺🇸 السوق الأمريكي'}</div>
                ${d.map(s => `
                    <div class="stock-row" onclick="loadStock('${s.symbol}')">
                        <div>
                            <div class="stock-row-sym">${s.symbol.replace('.SR', '')}</div>
                            <div class="stock-row-name">${s.name || s.symbol}</div>
                        </div>
                        <div>
                            <div class="stock-row-price">${formatPrice(s.price, s.currency)}</div>
                            <div class="stock-row-change ${s.change >= 0 ? 'positive' : 'negative'}">${s.change >= 0 ? '+' : ''}${s.change}%</div>
                        </div>
                    </div>
                `).join('')}
            `;
            grid.appendChild(block);
        };

        if (data.saudi && (currentMarket === 'all' || currentMarket === 'saudi')) show('saudi', data.saudi);
        if (data.us && (currentMarket === 'all' || currentMarket === 'us')) show('us', data.us);

    } catch (e) {
        console.error('Market overview error:', e);
    }
}

function loadStock(symbol) {
    document.getElementById('symbolInput').value = symbol.replace('.SR', '');
    searchStock();
}

// ======= Watchlist =======
function getWatchlist() { return JSON.parse(localStorage.getItem('watchlist') || '[]'); }
function saveWatchlist(list) { localStorage.setItem('watchlist', JSON.stringify(list)); }

function addToWatchlist() {
    if (!currentSymbol) return;
    let list = getWatchlist();
    if (list.includes(currentSymbol)) {
        showToast('السهم موجود في المفضلة بالفعل');
        return;
    }
    list.push(currentSymbol);
    saveWatchlist(list);
    renderWatchlistBadge();
    renderWatchlistPanel();
    showToast(`تمت إضافة ${currentSymbol} للمفضلة ⭐`);
}

function removeFromWatchlist(sym) {
    let list = getWatchlist().filter(s => s !== sym);
    saveWatchlist(list);
    renderWatchlistBadge();
    renderWatchlistPanel();
}

function renderWatchlistBadge() {
    document.getElementById('watchlistBadge').textContent = getWatchlist().length;
}

function renderWatchlistPanel() {
    const container = document.getElementById('watchlist-items');
    const list = getWatchlist();
    if (!list.length) {
        container.innerHTML = '<p class="empty-msg">لا توجد أسهم في المفضلة</p>';
        return;
    }
    container.innerHTML = list.map(sym => `
        <div class="wl-item" onclick="loadStock('${sym}')">
            <span class="wl-sym">${sym}</span>
            <button class="wl-del" onclick="event.stopPropagation(); removeFromWatchlist('${sym}')">🗑</button>
        </div>
    `).join('');
}

// ======= Alerts =======
function getAlerts() { return JSON.parse(localStorage.getItem('priceAlerts') || '[]'); }
function saveAlerts(list) { localStorage.setItem('priceAlerts', JSON.stringify(list)); }

function openAlertModal() {
    if (!currentSymbol) return;
    document.getElementById('alertSymbolLabel').textContent = `السهم: ${currentSymbol}`;
    document.getElementById('alertPrice').value = currentData ? currentData.current : '';
    document.getElementById('alertModal').classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
}

function closeAlertModal() {
    document.getElementById('alertModal').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
}

function saveAlert() {
    const type = document.getElementById('alertType').value;
    const price = parseFloat(document.getElementById('alertPrice').value);
    if (!price || isNaN(price)) { showToast('أدخل سعراً صحيحاً'); return; }

    const alerts = getAlerts();
    alerts.push({ symbol: currentSymbol, type, price, created: Date.now() });
    saveAlerts(alerts);
    renderAlertsBadge();
    renderAlertsPanel();
    closeAlertModal();
    showToast(`✅ تم حفظ التنبيه: ${currentSymbol} ${type === 'above' ? 'يتجاوز' : 'ينزل عن'} ${price}`);
}

function removeAlert(idx) {
    const alerts = getAlerts();
    alerts.splice(idx, 1);
    saveAlerts(alerts);
    renderAlertsBadge();
    renderAlertsPanel();
}

function renderAlertsBadge() {
    document.getElementById('alertsBadge').textContent = getAlerts().length;
}

function renderAlertsPanel() {
    const container = document.getElementById('alerts-items');
    const alerts = getAlerts();
    if (!alerts.length) {
        container.innerHTML = '<p class="empty-msg">لا توجد تنبيهات مضافة</p>';
        return;
    }
    container.innerHTML = alerts.map((a, i) => `
        <div class="alert-item">
            <div>
                <strong>${a.symbol}</strong> — ${a.type === 'above' ? 'يتجاوز' : 'ينزل عن'} <strong>${a.price}</strong>
            </div>
            <button class="alert-del" onclick="removeAlert(${i})">🗑</button>
        </div>
    `).join('');
}

function startAlertChecker() {
    if (alertInterval) clearInterval(alertInterval);
    alertInterval = setInterval(checkAlerts, 60000);
}

async function checkAlerts() {
    const alerts = getAlerts();
    if (!alerts.length) return;

    const symbols = [...new Set(alerts.map(a => a.symbol))];
    for (const sym of symbols) {
        try {
            const res = await fetch(`./api/search?q=${sym}`);
            const data = await res.json();
            if (data.error || !data.current) continue;

            const price = data.current;
            alerts.forEach((a, i) => {
                if (a.symbol !== sym) return;
                const triggered = (a.type === 'above' && price >= a.price) || (a.type === 'below' && price <= a.price);
                if (triggered) {
                    sendNotification(sym, a.type, a.price, price);
                    removeAlert(i);
                }
            });
        } catch (e) { /* skip */ }
    }
}

function sendNotification(sym, type, target, current) {
    const msg = `${sym}: السعر ${type === 'above' ? 'تجاوز' : 'نزل عن'} ${target} (الحالي: ${current})`;
    showToast(`🔔 ${msg}`);

    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Leo2Stock تنبيه سعري', { body: msg, icon: '/static/favicon.ico' });
    }
}

// ======= Panels =======
function openTab(id) {
    closeAllPanels();
    const panel = document.getElementById(id);
    panel.classList.remove('hidden');
    setTimeout(() => panel.classList.add('open'), 10);
    document.getElementById('overlay').classList.remove('hidden');

    if (id === 'watchlist-tab') renderWatchlistPanel();
    if (id === 'alerts-tab') renderAlertsPanel();
}

function closePanel(id) {
    const panel = document.getElementById(id);
    panel.classList.remove('open');
    setTimeout(() => panel.classList.add('hidden'), 350);
    document.getElementById('overlay').classList.add('hidden');
}

function closeAllPanels() {
    ['watchlist-tab', 'alerts-tab'].forEach(id => {
        const p = document.getElementById(id);
        if (p && !p.classList.contains('hidden')) closePanel(id);
    });
    closeAlertModal();
}

// ======= PDF Report =======
function downloadReport() {
    if (!currentSymbol) return;
    window.open(`./api/report/${currentSymbol}`, '_blank');
}

// ======= Helpers =======
function formatPrice(val, currency) {
    if (val === null || val === undefined || val === '—') return '—';
    const sym = currency === 'SAR' ? 'ر.س' : '$';
    return `${sym}${parseFloat(val).toFixed(2)}`;
}

function formatVolume(vol) {
    if (!vol) return '—';
    if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`;
    if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `${(vol / 1e3).toFixed(0)}K`;
    return vol.toString();
}

function formatMarketCap(cap) {
    if (!cap) return 'N/A';
    if (cap >= 1e12) return `$${(cap / 1e12).toFixed(2)}T`;
    if (cap >= 1e9) return `$${(cap / 1e9).toFixed(2)}B`;
    if (cap >= 1e6) return `$${(cap / 1e6).toFixed(2)}M`;
    return `$${cap}`;
}

function setSignal(id, type, text) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    styleSignal(id, type);
}

function styleSignal(id, type) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.background = type === 'buy' ? 'rgba(0,230,118,0.15)' :
                          type === 'sell' ? 'rgba(255,23,68,0.15)' : 'rgba(255,255,255,0.05)';
    el.style.color = type === 'buy' ? '#00e676' :
                     type === 'sell' ? '#ff1744' : '#8892a4';
}

function showLoading(show) {
    document.getElementById('loading').classList.toggle('hidden', !show);
}

function showError(msg) {
    showToast('❌ ' + msg, 'error');
}

function showToast(msg, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.cssText = `
        position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
        background: ${type === 'error' ? '#ff1744' : '#141d2e'};
        color: white; padding: 14px 28px; border-radius: 50px;
        font-family: Cairo,sans-serif; font-weight: 600; font-size: 0.9rem;
        border: 1px solid rgba(0,229,255,0.3); z-index: 9999;
        box-shadow: 0 8px 30px rgba(0,0,0,0.5);
        animation: fadeInUp 0.3s ease; white-space: nowrap;
    `;
    toast.textContent = msg;

    const style = document.createElement('style');
    style.textContent = `@keyframes fadeInUp { from { opacity:0; transform:translateX(-50%) translateY(20px); } to { opacity:1; transform:translateX(-50%) translateY(0); } }`;
    document.head.appendChild(style);

    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}
