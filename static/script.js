/* ============================================
   Leo2Stock — Main JavaScript (Enhanced v2.1)
   Custom Candlestick Chart with Canvas API
   ============================================ */

// ======= State =======
let currentMarket = 'all';
let currentSymbol = null;
let currentData = null;
let candlestickCanvas = null;
let volumeCanvas = null;
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
        purple: '#7c4dff',
        bg: isDark ? '#141d2e' : '#ffffff',
        bg2: isDark ? '#1a2540' : '#f4f7fd',
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

// ======= RSI Scanner =======
async function runRsiScan() {
    const rsiMax = document.getElementById('rsiInput').value || 30;
    const market = document.getElementById('rsiMarket').value;

    showLoading(true);

    try {
        const res = await fetch(`./api/rsi-scan?market=${market}&rsi_max=${rsiMax}`);
        const data = await res.json();

        displayRsiResults(data);
    } catch (err) {
        showError('خطأ في مسح RSI');
        console.error(err);
    }

    showLoading(false);
}

function displayRsiResults(results) {
    const container = document.getElementById('rsiResults');
    const tbody = document.getElementById('rsiTableBody');

    if (!results || results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px;">لا توجد نتائج</td></tr>';
        container.classList.remove('hidden');
        return;
    }

    tbody.innerHTML = results.map(stock => {
        const isPositive = stock.change >= 0;
        const rec = stock.recommendation || {};
        const recColor = rec.color || 'gray';

        return `
            <tr>
                <td><strong>${stock.symbol}</strong></td>
                <td>${stock.name || stock.symbol}</td>
                <td>${formatPrice(stock.price, stock.currency)}</td>
                <td class="${isPositive ? 'positive' : 'negative'}">${isPositive ? '+' : ''}${stock.change}%</td>
                <td><strong style="color:${stock.rsi < 30 ? '#00e676' : '#ff1744'}">${stock.rsi}</strong></td>
                <td><span class="rec-badge ${recColor}">${rec.action || 'محايد'}</span></td>
                <td><button class="mini-btn" onclick="loadStock('${stock.symbol}')">تحليل</button></td>
            </tr>
        `;
    }).join('');

    container.classList.remove('hidden');
}

// ======= Display Result =======
function displayResult(data) {
    const analysis = data.analysis || {};
    const indicators = analysis.indicators || {};
    const rec = data.recommendation || {};
    const bb = indicators.bollinger || {};
    const macd = indicators.macd || {};
    const stoch = indicators.stochastic || {};
    const targets = analysis.targets || {};
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

    // Targets
    document.getElementById('target-1').textContent = formatPrice(targets.target_1, data.currency);
    document.getElementById('target-2').textContent = formatPrice(targets.target_2, data.currency);
    document.getElementById('target-3').textContent = formatPrice(targets.target_3, data.currency);
    document.getElementById('target-4').textContent = formatPrice(targets.target_4, data.currency);
    document.getElementById('target-stop').textContent = formatPrice(targets.stop_loss, data.currency);

    // Supports
    document.getElementById('support-1').textContent = formatPrice(targets.support_1, data.currency);
    document.getElementById('support-2').textContent = formatPrice(targets.support_2, data.currency);
    document.getElementById('support-3').textContent = formatPrice(targets.support_3, data.currency);
    document.getElementById('support-4').textContent = formatPrice(targets.support_4, data.currency);

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

    // Fundamental Reason
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
    drawCandlestickChart(data);
    drawVolumeChart(data);
    drawRsiChart(data);
    drawMacdChart(data);

    // Show result
    document.getElementById('result').classList.remove('hidden');
    document.getElementById('result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ======= Custom Candlestick Chart with Canvas API =======
function drawCandlestickChart(data) {
    const canvas = document.getElementById('candlestickChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const c = getChartColors();

    const prices = data.prices_arr || [];
    const dates = data.dates_list || [];
    const sma20 = data.sma20_list || [];
    const sma50 = data.sma50_list || [];
    const sma200 = data.sma200_list || [];

    if (!prices.length || prices.length < 5) {
        console.warn('No price data for candlestick chart');
        return;
    }

    // Set canvas size
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    const width = canvas.width;
    const height = canvas.height;
    const padding = { top: 20, right: 60, bottom: 40, left: 10 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // Calculate SMA 7
    const sma7 = [];
    const closes = prices.map(p => p.close || p.Close || 0);
    for (let i = 0; i < closes.length; i++) {
        if (i >= 6) {
            sma7.push(closes.slice(i - 6, i + 1).reduce((a, b) => a + b, 0) / 7);
        } else {
            sma7.push(null);
        }
    }

    // Find min/max for scaling
    let allValues = [];
    prices.forEach(p => {
        allValues.push(p.high || p.High || 0);
        allValues.push(p.low || p.Low || 0);
    });
    sma20.forEach(v => { if (v) allValues.push(v); });
    sma50.forEach(v => { if (v) allValues.push(v); });
    sma200.forEach(v => { if (v) allValues.push(v); });
    sma7.forEach(v => { if (v) allValues.push(v); });

    const minPrice = Math.min(...allValues.filter(v => v > 0)) * 0.98;
    const maxPrice = Math.max(...allValues) * 1.02;
    const priceRange = maxPrice - minPrice;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw grid
    ctx.strokeStyle = c.grid;
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();

        // Price labels
        const price = maxPrice - (priceRange / 5) * i;
        ctx.fillStyle = c.text;
        ctx.font = '10px Cairo';
        ctx.textAlign = 'left';
        ctx.fillText(price.toFixed(2), width - padding.right + 5, y + 3);
    }

    // Draw date labels (show every ~10th date)
    const dateStep = Math.max(1, Math.floor(dates.length / 8));
    for (let i = 0; i < dates.length; i += dateStep) {
        const x = padding.left + (i / (prices.length - 1)) * chartWidth;
        ctx.fillStyle = c.text;
        ctx.font = '9px Cairo';
        ctx.textAlign = 'center';
        const dateStr = dates[i] ? dates[i].slice(5) : ''; // MM-DD
        ctx.fillText(dateStr, x, height - 10);
    }

    // Calculate candle width
    const candleWidth = Math.max(1, (chartWidth / prices.length) * 0.7);
    const candleSpacing = chartWidth / prices.length;

    // Draw candles
    prices.forEach((p, i) => {
        const open = p.open || p.Open || p.close || p.Close || 0;
        const high = p.high || p.High || p.close || p.Close || 0;
        const low = p.low || p.Low || p.close || p.Close || 0;
        const close = p.close || p.Close || 0;

        const x = padding.left + i * candleSpacing + candleSpacing / 2;
        const yOpen = padding.top + ((maxPrice - open) / priceRange) * chartHeight;
        const yHigh = padding.top + ((maxPrice - high) / priceRange) * chartHeight;
        const yLow = padding.top + ((maxPrice - low) / priceRange) * chartHeight;
        const yClose = padding.top + ((maxPrice - close) / priceRange) * chartHeight;

        const isGreen = close >= open;
        const color = isGreen ? c.positive : c.negative;

        // Draw wick
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, yHigh);
        ctx.lineTo(x, yLow);
        ctx.stroke();

        // Draw body
        const bodyTop = Math.min(yOpen, yClose);
        const bodyHeight = Math.abs(yClose - yOpen);
        ctx.fillStyle = isGreen ? color : color;
        if (!isGreen) {
            ctx.fillStyle = color;
        } else {
            ctx.fillStyle = 'rgba(0,230,118,0.3)';
            ctx.strokeStyle = color;
        }

        const bodyWidth = Math.max(1, candleWidth);
        ctx.fillRect(x - bodyWidth / 2, bodyTop, bodyWidth, Math.max(1, bodyHeight));

        if (isGreen) {
            ctx.strokeRect(x - bodyWidth / 2, bodyTop, bodyWidth, Math.max(1, bodyHeight));
        }
    });

    // Draw SMA lines
    function drawSMALine(smaData, color, lineWidth, dash) {
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        if (dash) ctx.setLineDash(dash);
        else ctx.setLineDash([]);

        ctx.beginPath();
        let started = false;
        smaData.forEach((v, i) => {
            if (v === null || v === undefined) return;
            const x = padding.left + i * candleSpacing + candleSpacing / 2;
            const y = padding.top + ((maxPrice - v) / priceRange) * chartHeight;
            if (!started) {
                ctx.moveTo(x, y);
                started = true;
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.stroke();
        ctx.setLineDash([]);
    }

    drawSMALine(sma7, c.warning, 1.5, [2, 2]);
    drawSMALine(sma20, c.purple, 1.5, [4, 2]);
    drawSMALine(sma50, c.negative, 1.5, [6, 3]);
    drawSMALine(sma200, c.positive, 2, []);

    // Draw targets/supports as horizontal lines
    const targets = (data.analysis && data.analysis.targets) || {};
    if (targets.target_1) {
        ctx.strokeStyle = 'rgba(0,230,118,0.4)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        const y = padding.top + ((maxPrice - targets.target_1) / priceRange) * chartHeight;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    if (targets.stop_loss) {
        ctx.strokeStyle = 'rgba(255,23,68,0.4)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        const y = padding.top + ((maxPrice - targets.stop_loss) / priceRange) * chartHeight;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        ctx.setLineDash([]);
    }
}

// ======= Volume Chart =======
function drawVolumeChart(data) {
    const canvas = document.getElementById('volumeChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const c = getChartColors();

    const prices = data.prices_arr || [];
    const dates = data.dates_list || [];
    const volumes = data.volumes_list || [];

    if (!volumes.length) {
        console.warn('No volume data');
        return;
    }

    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    const width = canvas.width;
    const height = canvas.height;
    const padding = { top: 10, right: 60, bottom: 20, left: 10 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const maxVol = Math.max(...volumes.filter(v => v > 0)) * 1.1;

    ctx.clearRect(0, 0, width, height);

    // Draw grid
    ctx.strokeStyle = c.grid;
    ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
        const y = padding.top + (chartHeight / 3) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();

        const vol = maxVol - (maxVol / 3) * i;
        ctx.fillStyle = c.text;
        ctx.font = '9px Cairo';
        ctx.textAlign = 'left';
        ctx.fillText(formatVolumeCompact(vol), width - padding.right + 5, y + 3);
    }

    const barWidth = Math.max(1, (chartWidth / volumes.length) * 0.8);
    const barSpacing = chartWidth / volumes.length;

    volumes.forEach((v, i) => {
        const p = prices[i] || {};
        const close = p.close || p.Close || 0;
        const open = p.open || p.Open || close;
        const isGreen = close >= open;

        const x = padding.left + i * barSpacing + barSpacing / 2;
        const barHeight = (v / maxVol) * chartHeight;
        const y = padding.top + chartHeight - barHeight;

        ctx.fillStyle = isGreen ? 'rgba(0,230,118,0.5)' : 'rgba(255,23,68,0.5)';
        ctx.fillRect(x - barWidth / 2, y, barWidth, barHeight);
    });
}

function formatVolumeCompact(vol) {
    if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`;
    if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `${(vol / 1e3).toFixed(0)}K`;
    return vol.toString();
}

// ======= RSI Chart (Chart.js) =======
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
            maintainAspectRatio: false,
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
                x: { display: false },
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

// ======= MACD Chart (Chart.js) =======
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
            maintainAspectRatio: false,
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
                x: { display: false },
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
    drawCandlestickChart(data);
    drawVolumeChart(data);
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
                drawCandlestickChart(currentData);
                drawVolumeChart(currentData);
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
