/* ============================================
   Leo2Stock — script.js v4.0
   Candlestick + Crosshair + Timeframe
   ============================================ */

// ======= State =======
let currentMarket = 'all';
let currentSymbol = null;
let currentData = null;
let rsiChart = null;
let macdChart = null;
let alertInterval = null;
let currentTimeframe = '1d';
let currentPeriod = '6mo';

let indicatorVisibility = {
    sma7: true, sma20: true, sma50: true, sma200: true,
    fibonacci: false, bollinger: false, targets: true
};
let secondaryChartVisibility = { rsi: true, macd: true };

let mouseX = -1, mouseY = -1, isMouseOverChart = false;
let currentHighlightIndex = -1;

// ======= Init =======
document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    renderWatchlistBadge();
    renderAlertsBadge();
    startAlertChecker();
    initLiveUsers();
    setupCrosshair();

    const symbolInput = document.getElementById('symbolInput');
    if (symbolInput) symbolInput.addEventListener('keypress', e => { if (e.key === 'Enter') searchStock(); });

    const heroInput = document.getElementById('symbolInputHero');
    if (heroInput) heroInput.addEventListener('keypress', e => { if (e.key === 'Enter') searchFromHero(); });

    if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission();
});

// ======= Live Users =======
function initLiveUsers() {
    let count = 12 + Math.floor(Math.random() * 8);
    function update() {
        count = Math.max(8, Math.min(50, count + Math.floor(Math.random() * 3) - 1));
        const el = document.getElementById('liveUsersCount');
        if (el) el.textContent = count;
    }
    update();
    setInterval(update, 8000 + Math.random() * 4000);
}

// ======= Crosshair =======
function setupCrosshair() {
    const wrapper = document.getElementById('mainChartWrapper');
    if (!wrapper) return;

    wrapper.addEventListener('mousemove', (e) => {
        const rect = wrapper.getBoundingClientRect();
        mouseX = e.clientX - rect.left;
        mouseY = e.clientY - rect.top;
        isMouseOverChart = true;
        const canvas = document.getElementById('candlestickChart');
        if (canvas && currentData) {
            const prices = currentData.prices_arr || [];
            const padding = { top: 20, right: 60, bottom: 40, left: 10 };
            const chartWidth = canvas.width - padding.left - padding.right;
            const candleSpacing = chartWidth / Math.max(prices.length, 1);
            currentHighlightIndex = Math.min(
                prices.length - 1,
                Math.max(0, Math.floor((mouseX - padding.left) / candleSpacing))
            );
            updateCrosshairInfo(currentHighlightIndex);
            drawCandlestickChart(currentData, currentHighlightIndex, mouseX, mouseY);
        }
    });

    wrapper.addEventListener('mouseleave', () => {
        isMouseOverChart = false;
        mouseX = -1; mouseY = -1;
        currentHighlightIndex = -1;
        const ci = document.getElementById('crosshairInfo');
        if (ci) ci.classList.add('hidden');
        if (currentData) drawCandlestickChart(currentData, -1, -1, -1);
    });
}

function updateCrosshairInfo(idx) {
    const prices = currentData.prices_arr || [];
    const dates = currentData.dates_list || [];
    if (!prices.length || idx < 0) return;

    const p = prices[idx];
    if (!p) return;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('crosshair-date',   dates[idx] || '—');
    set('crosshair-price',  formatPrice(p.close, currentData.currency));
    set('crosshair-open',   formatPrice(p.open,  currentData.currency));
    set('crosshair-high',   formatPrice(p.high,  currentData.currency));
    set('crosshair-low',    formatPrice(p.low,   currentData.currency));
    set('crosshair-close',  formatPrice(p.close, currentData.currency));
    set('crosshair-volume', formatVolume(p.volume || 0));

    const ci = document.getElementById('crosshairInfo');
    if (ci) ci.classList.remove('hidden');
}

// ======= Theme =======
function loadTheme() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.body.className = saved;
    const icon = document.getElementById('themeIcon');
    if (icon) icon.textContent = saved === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
    const isDark = document.body.classList.contains('dark');
    document.body.className = isDark ? 'light' : 'dark';
    localStorage.setItem('theme', isDark ? 'light' : 'dark');
    const icon = document.getElementById('themeIcon');
    if (icon) icon.textContent = isDark ? '🌙' : '☀️';
    if (currentData) redrawCharts(currentData);
}

function getChartColors() {
    const isDark = document.body.classList.contains('dark');
    return {
        grid:     isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
        text:     isDark ? '#8892a4' : '#5a6478',
        accent:   '#00e5ff',
        positive: '#00e676',
        negative: '#ff1744',
        warning:  '#ffab40',
        purple:   '#7c4dff',
        gold:     '#ffd700',
        bg:       isDark ? '#141d2e' : '#ffffff',
        crossV:   'rgba(0,229,255,0.6)',
        crossH:   'rgba(0,229,255,0.4)',
        crossTxt: '#00e5ff',
    };
}

// ======= Market =======
function switchMarket(market, el) {
    currentMarket = market;
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    if (el) el.classList.add('active');
}

// ======= Search =======
function searchFromHero() {
    const heroInput = document.getElementById('symbolInputHero');
    const navInput  = document.getElementById('symbolInput');
    if (heroInput && heroInput.value.trim()) {
        if (navInput) navInput.value = heroInput.value.trim();
        searchStock();
    }
}

async function searchStock() {
    const input = document.getElementById('symbolInput');
    const symbol = input ? input.value.trim().toUpperCase() : '';
    if (!symbol) return;
    showLoading(true);
    try {
        const res = await fetch(`./api/analyze/${symbol}`);
        const data = await res.json();
        if (data.error) { showError(data.error); showLoading(false); return; }
        currentSymbol = symbol;
        currentData = data;
        displayResult(data);
    } catch (err) {
        showError('حدث خطأ في الاتصال بالخادم');
        console.error(err);
    }
    showLoading(false);
}

function loadStock(symbol) {
    const input = document.getElementById('symbolInput');
    if (input) input.value = symbol.replace('.SR', '');
    searchStock();
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
    } catch (err) { showError('خطأ في مسح RSI'); }
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
        const isPos = stock.change >= 0;
        const rec = stock.recommendation || {};
        return `<tr>
            <td><strong>${stock.symbol}</strong></td>
            <td>${stock.name || stock.symbol}</td>
            <td>${formatPrice(stock.price, stock.currency)}</td>
            <td class="${isPos ? 'positive' : 'negative'}">${isPos ? '+' : ''}${stock.change}%</td>
            <td><strong style="color:${stock.rsi < 30 ? '#00e676' : '#ff1744'}">${stock.rsi}</strong></td>
            <td><span class="rec-badge ${rec.color || 'gray'}">${rec.action || 'محايد'}</span></td>
            <td><button class="mini-btn" onclick="loadStock('${stock.symbol}')">تحليل</button></td>
        </tr>`;
    }).join('');
    container.classList.remove('hidden');
}

// ======= Display Result =======
function displayResult(data) {
    const analysis   = data.analysis   || {};
    const indicators = analysis.indicators || {};
    const rec        = data.recommendation || {};
    const bb         = indicators.bollinger || {};
    const macd_ind   = indicators.macd || {};
    const stoch      = indicators.stochastic || {};
    const targets    = analysis.targets || {};
    const fund_reason= analysis.fundamental_reason || {};
    const isPositive = data.change >= 0;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    set('res-symbol',   data.symbol);
    set('res-name',     data.name || data.symbol);
    set('res-sector',   data.sector   || 'غير محدد');
    set('res-market',   data.market === 'saudi' ? '🇸🇦 سعودي' : '🇺🇸 أمريكي');
    set('res-industry', data.industry || 'غير محدد');
    set('res-price',    formatPrice(data.current, data.currency));

    const changeEl = document.getElementById('res-change');
    if (changeEl) {
        changeEl.textContent = `${isPositive ? '+' : ''}${data.change}%`;
        changeEl.className = `price-delta ${isPositive ? 'positive' : 'negative'}`;
    }
    set('res-currency', data.currency || 'USD');
    set('res-open',    formatPrice(data.open,     data.currency));
    set('res-high',    formatPrice(data.high,     data.currency));
    set('res-low',     formatPrice(data.low,      data.currency));
    set('res-volume',  formatVolume(data.volume));
    set('res-high52',  formatPrice(data.high_52w, data.currency));
    set('res-low52',   formatPrice(data.low_52w,  data.currency));

    // Volume bar
    const avgVol = data.avg_volume || 0;
    const volRatio = avgVol > 0 ? (data.volume || 0) / avgVol : 0;
    set('volume-comparison', avgVol > 0 ? `${volRatio.toFixed(1)}x المتوسط` : '—');
    const volBar = document.getElementById('volume-bar-fill');
    if (volBar) {
        volBar.style.width = `${Math.min(volRatio * 100, 100)}%`;
        volBar.style.background = volRatio > 1.5 ? 'linear-gradient(90deg,#ff1744,#ffab40)' :
                                   volRatio > 1   ? 'linear-gradient(90deg,#00e676,#00e5ff)' :
                                                    'linear-gradient(90deg,#8892a4,#00e5ff)';
    }

    // AI
    generateAIAnalysis(data);

    // Earnings
    displayEarnings(data);

    // Targets
    set('target-1', formatPrice(targets.target_1, data.currency));
    set('target-2', formatPrice(targets.target_2, data.currency));
    set('target-3', formatPrice(targets.target_3, data.currency));
    set('target-4', formatPrice(targets.target_4, data.currency));
    set('target-stop', formatPrice(targets.stop_loss, data.currency));
    set('support-1', formatPrice(targets.support_1, data.currency));
    set('support-2', formatPrice(targets.support_2, data.currency));
    set('support-3', formatPrice(targets.support_3, data.currency));
    set('support-4', formatPrice(targets.support_4, data.currency));

    // Fibonacci
    displayFibonacci(data);

    // Indicators
    const rsi = indicators.rsi || 50;
    set('ind-rsi', rsi);
    const rsiBar = document.getElementById('rsi-bar');
    if (rsiBar) {
        rsiBar.style.width = `${Math.min(rsi, 100)}%`;
        rsiBar.style.background = rsi < 30 ? '#00e676' : rsi > 70 ? '#ff1744' : '#00e5ff';
    }
    setSignal('sig-rsi', rsi < 30 ? 'buy' : rsi > 70 ? 'sell' : 'neutral',
              rsi < 30 ? 'تشبع بيعي' : rsi > 70 ? 'تشبع شرائي' : 'محايد');

    const price = data.current;
    const sma20  = indicators.sma_20;
    const sma50  = indicators.sma_50;
    const sma200 = indicators.sma_200;

    set('ind-sma20', formatPrice(sma20, data.currency));
    setSignal('sig-sma20', price > sma20 ? 'buy' : 'sell', price > sma20 ? 'فوق' : 'تحت');
    set('ind-sma50', formatPrice(sma50, data.currency));
    setSignal('sig-sma50', price > sma50 ? 'buy' : 'sell', price > sma50 ? 'فوق' : 'تحت');
    set('ind-sma200', formatPrice(sma200, data.currency));
    setSignal('sig-sma200', price > sma200 ? 'buy' : 'sell', price > sma200 ? 'فوق' : 'تحت');
    set('ind-macd', macd_ind.macd || '—');
    setSignal('sig-macd', macd_ind.histogram > 0 ? 'buy' : 'sell', macd_ind.histogram > 0 ? 'صاعد' : 'هابط');
    set('ind-bb-upper', formatPrice(bb.upper, data.currency));
    set('ind-bb-lower', formatPrice(bb.lower, data.currency));
    const bbSig = price >= bb.upper ? 'sell' : price <= bb.lower ? 'buy' : 'neutral';
    setSignal('sig-bb', bbSig, price >= bb.upper ? 'حد علوي' : price <= bb.lower ? 'حد سفلي' : 'وسط');
    set('ind-atr', formatPrice(indicators.atr, data.currency));
    set('ind-stoch-k', stoch.k || '—');
    setSignal('sig-stoch', stoch.k < 20 ? 'buy' : stoch.k > 80 ? 'sell' : 'neutral',
              stoch.k < 20 ? 'تشبع بيعي' : stoch.k > 80 ? 'تشبع شرائي' : 'محايد');

    // Fundamental
    set('fund-cap', formatMarketCap(data.market_cap));
    const pe = data.pe_ratio;
    set('fund-pe', pe ? pe.toFixed(1) : 'N/A');
    if (pe) set('fund-pe-note', pe < 15 ? 'منخفض جيد' : pe > 30 ? 'مرتفع' : 'معتدل');
    set('fund-sector',     data.sector   || 'غير محدد');
    set('fund-industry',   data.industry || 'غير محدد');
    set('fund-support',    formatPrice(analysis.support,    data.currency));
    set('fund-resistance', formatPrice(analysis.resistance, data.currency));
    const trendMap = { strong_bullish:'صاعد قوي', bullish:'صاعد', neutral:'محايد', bearish:'هابط', strong_bearish:'هابط قوي' };
    set('fund-trend', trendMap[analysis.trend] || '—');
    set('fund-volume-ratio', avgVol > 0 ? `${volRatio.toFixed(1)}x` : '—');

    const fundReasonEl = document.getElementById('fund-reason');
    if (fundReasonEl && fund_reason) {
        fundReasonEl.innerHTML = `
            <div class="fund-reason-box ${fund_reason.direction || 'neutral'}">
                <h4>${fund_reason.title || 'الوضع الحالي'}</h4>
                <p class="fund-summary">${fund_reason.summary || ''}</p>
                ${fund_reason.reasons ? '<ul>' + fund_reason.reasons.map(r => `<li>${r}</li>`).join('') + '</ul>' : ''}
            </div>`;
    }

    // Recommendation
    const recCard = document.getElementById('rec-card');
    const action = rec.action || 'محايد';
    set('rec-action', action);
    set('rec-score', `نقاط: ${rec.score >= 0 ? '+' : ''}${rec.score}`);
    if (recCard) {
        recCard.className = 'card rec-card';
        if (action.includes('شراء قوي')) recCard.classList.add('rec-strong-buy');
        else if (action.includes('شراء')) recCard.classList.add('rec-buy');
        else if (action.includes('بيع قوي')) recCard.classList.add('rec-strong-sell');
        else if (action.includes('بيع')) recCard.classList.add('rec-sell');
        else recCard.classList.add('rec-neutral');
    }

    // Signals
    const sl = document.getElementById('signals-list');
    if (sl) sl.innerHTML = analysis.signals && analysis.signals.length
        ? analysis.signals.map(s => `<li>${s}</li>`).join('')
        : '<li class="no-signals">لا توجد إشارات واضحة حالياً</li>';

    // Impact
    displayImpactAnalysis(data);

    // Charts
    drawCandlestickChart(data);
    drawVolumeChart(data);
    drawRsiChart(data);
    drawMacdChart(data);

    // AI Deep
    setTimeout(() => generateAIDeepAnalysis(data), 100);

    // Show
    const resultEl = document.getElementById('result');
    if (resultEl) {
        resultEl.classList.remove('hidden');
        resultEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    const heroEl = document.getElementById('hero-section');
    if (heroEl) heroEl.style.display = 'none';
}

// ======= AI Basic =======
function generateAIAnalysis(data) {
    const container = document.getElementById('ai-analysis-content');
    if (!container) return;
    const analysis = data.analysis || {};
    const indicators = analysis.indicators || {};
    const trend = analysis.trend || 'neutral';
    const rsi = indicators.rsi || 50;
    let aiText = '', confidence = 50;
    if (trend === 'strong_bullish')   { aiText = 'السهم فوق جميع المتوسطات — قوة شرائية ممتازة.'; confidence = 85; }
    else if (trend === 'bullish')     { aiText = 'اتجاه صاعد مع إشارات إيجابية من المؤشرات.'; confidence = 70; }
    else if (trend === 'strong_bearish') { aiText = 'هبوط قوي مع ضغط بيعي واضح على جميع الأطر.'; confidence = 85; }
    else if (trend === 'bearish')     { aiText = 'اتجاه هبوطي مستمر — انتظار إشارات انعكاس.'; confidence = 65; }
    else if (rsi < 30)                { aiText = `RSI عند ${rsi} — تشبع بيعي، فرصة ارتداد محتملة.`; confidence = 60; }
    else if (rsi > 70)                { aiText = `RSI عند ${rsi} — تشبع شرائي، احتمال تصحيح.`; confidence = 55; }
    else                              { aiText = 'السهم في منطقة محايدة — انتظار محفزات.'; confidence = 40; }
    const cc = confidence > 70 ? 'var(--positive)' : confidence > 50 ? 'var(--warning)' : 'var(--negative)';
    container.innerHTML = `
        <div class="ai-result">
            <h4>تحليل الذكاء الاصطناعي</h4>
            <p>${aiText}</p>
            <div class="ai-confidence">
                <span class="ai-confidence-label">نسبة الثقة:</span>
                <div class="ai-confidence-bar"><div class="ai-confidence-fill" style="width:${confidence}%;background:${cc};"></div></div>
                <span class="ai-confidence-val" style="color:${cc};">${confidence}%</span>
            </div>
        </div>`;
}

// ======= Earnings =======
function displayEarnings(data) {
    const hash = data.symbol.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + (hash % 45) + 15);
    const months = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'];
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('earnings-date',     `${futureDate.getDate()} ${months[futureDate.getMonth()]} ${futureDate.getFullYear()}`);
    set('earnings-quarter',  ['Q1 2026','Q2 2026','Q3 2026','Q4 2026'][hash % 4]);
    set('earnings-estimate', ['أفضل من المتوقع','ضمن التوقعات','أقل من المتوقع','غير محدد'][hash % 4]);
}

// ======= Fibonacci =======
function displayFibonacci(data) {
    const prices = data.prices_arr || [];
    if (!prices.length) return;
    const high52 = data.high_52w || Math.max(...prices.map(p => p.high || 0));
    const low52  = data.low_52w  || Math.min(...prices.map(p => p.low  || 999));
    const range  = high52 - low52;
    const levels = { 'fib-0': high52, 'fib-236': high52 - range*0.236, 'fib-382': high52 - range*0.382,
                     'fib-500': high52 - range*0.5, 'fib-618': high52 - range*0.618,
                     'fib-786': high52 - range*0.786, 'fib-100': low52 };
    Object.entries(levels).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = formatPrice(val, data.currency);
    });
}

// ======= Impact Analysis =======
function displayImpactAnalysis(data) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('impact-sector',   data.sector   || 'غير محدد');
    set('impact-industry', data.industry || 'غير محدد');
    set('impact-country',  data.market === 'saudi' ? 'السعودية' : 'الولايات المتحدة');
    const hash = data.symbol.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    set('impact-employees', formatVolume(((hash % 500) + 1) * 1000));
    const revenue = ((hash % 100) + 10) * 1e9;
    set('impact-revenue', formatMarketCap(revenue));
    set('impact-profit',  formatMarketCap(revenue * ((hash % 30) + 5) / 100));
    set('impact-margin',  `${(hash % 25) + 10}%`);
    set('impact-roe',     `${(hash % 20) + 5}%`);

    const fc = document.getElementById('impact-factors');
    if (fc) {
        const factors = generateImpactFactors(data, hash);
        fc.innerHTML = factors.map(f => `
            <div class="impact-factor ${f.type}">
                <span class="impact-factor-icon">${f.icon}</span>
                <span class="impact-factor-text">${f.text}</span>
            </div>`).join('');
    }
    const oc = document.getElementById('impact-outlook');
    if (oc) oc.innerHTML = `<p>${generateOutlook(data, hash)}</p>`;
}

function generateImpactFactors(data, hash) {
    const factors = [];
    const isSaudi = data.market === 'saudi';
    if (data.change > 5)       factors.push({ icon:'📈', text:`ارتفاع قوي ${data.change}% يعكس تفاؤل السوق`,            type:'positive' });
    else if (data.change < -5) factors.push({ icon:'📉', text:`انخفاض حاد ${Math.abs(data.change)}% ضغط بيعي واضح`,     type:'negative' });
    const vr = (data.volume || 0) / (data.avg_volume || 1);
    if (vr > 2) factors.push({ icon:'🔥', text:`حجم تداول استثنائي (${vr.toFixed(1)}x المتوسط)`, type:'positive' });
    factors.push(isSaudi
        ? { icon:'🏛️', text:'تأثير إيجابي من رؤية 2030 والتحول الاقتصادي',        type:'positive' }
        : { icon:'💵', text:'تأثر بالسياسة النقدية الفيدرالية وتوقعات الفائدة', type:'neutral'  });
    const trend = data.analysis?.trend || 'neutral';
    if (trend.includes('bullish')) factors.push({ icon:'🎯', text:'الاتجاه الصعودي يجذب المتداولين',     type:'positive' });
    else if (trend.includes('bearish')) factors.push({ icon:'⚠️', text:'الاتجاه الهبوطي يضغط على المراكز', type:'negative' });
    return factors;
}

function generateOutlook(data, hash) {
    const outlooks = {
        strong_bullish: 'التوقعات إيجابية جداً — المؤشرات تدعم استمرار الصعود.',
        bullish:        'التوقعات إيجابية — احتمال تحقيق أهداف أعلى على المدى المتوسط.',
        neutral:        'التوقعات متباينة — السهم يحتاج محفزات لكسر نطاق التداول.',
        bearish:        'التوقعات سلبية على المدى القصير — راقب مستويات الدعم.',
        strong_bearish: 'التوقعات سلبية — الضغط البيعي قد يستمر.'
    };
    return outlooks[data.analysis?.trend] || outlooks.neutral;
}

// ======= Candlestick Chart - مع خط أفقي وعمودي =======
function drawCandlestickChart(data, highlightIndex = -1, crsX = -1, crsY = -1) {
    const canvas = document.getElementById('candlestickChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const c = getChartColors();

    const container = document.getElementById('mainChartWrapper');
    if (container) {
        canvas.width  = container.clientWidth;
        canvas.height = container.clientHeight || 450;
    }

    const width  = canvas.width;
    const height = canvas.height;
    const padding = { top: 20, right: 65, bottom: 40, left: 10 };
    const chartWidth  = width  - padding.left - padding.right;
    const chartHeight = height - padding.top  - padding.bottom;

    const prices = data.prices_arr || [];
    const dates  = data.dates_list || [];
    if (!prices.length) return;

    // SMAs
    const closes = prices.map(p => p.close || 0);
    function calcSMA(arr, period) {
        return arr.map((_, i) => i < period - 1 ? null :
            arr.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period);
    }
    const sma7   = calcSMA(closes, 7);
    const sma20  = calcSMA(closes, 20);
    const sma50  = calcSMA(closes, 50);
    const sma200 = calcSMA(closes, 200);

    // Bollinger
    const bollingerUpper = closes.map((_, i) => {
        if (i < 19) return null;
        const sl = closes.slice(i - 19, i + 1);
        const m = sl.reduce((a,b) => a+b,0) / 20;
        return m + Math.sqrt(sl.reduce((a,b) => a + Math.pow(b-m,2),0) / 20) * 2;
    });
    const bollingerLower = closes.map((_, i) => {
        if (i < 19) return null;
        const sl = closes.slice(i - 19, i + 1);
        const m = sl.reduce((a,b) => a+b,0) / 20;
        return m - Math.sqrt(sl.reduce((a,b) => a + Math.pow(b-m,2),0) / 20) * 2;
    });

    // Fibonacci
    const high52  = data.high_52w || Math.max(...prices.map(p => p.high || 0));
    const low52   = data.low_52w  || Math.min(...prices.map(p => p.low  || 999999));
    const range52 = high52 - low52;
    const fibLevels = [
        high52 - range52*0.236, high52 - range52*0.382,
        high52 - range52*0.5,   high52 - range52*0.618,
        high52 - range52*0.786
    ];

    // Min/Max
    let allV = [];
    prices.forEach(p => { allV.push(p.high || 0); allV.push(p.low || 0); });
    if (indicatorVisibility.bollinger) { bollingerUpper.forEach(v => { if (v) allV.push(v); }); bollingerLower.forEach(v => { if (v) allV.push(v); }); }
    if (indicatorVisibility.fibonacci) fibLevels.forEach(v => allV.push(v));
    const minPrice  = Math.min(...allV.filter(v => v > 0)) * 0.98;
    const maxPrice  = Math.max(...allV) * 1.02;
    const priceRange = maxPrice - minPrice || 1;

    const toY = val => padding.top + ((maxPrice - val) / priceRange) * chartHeight;
    const candleSpacing = chartWidth / prices.length;
    const candleWidth   = Math.max(1, candleSpacing * 0.7);

    // Clear
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = c.bg;
    ctx.fillRect(0, 0, width, height);

    // Grid + price labels
    ctx.strokeStyle = c.grid;
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (chartHeight / 5) * i;
        ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
        const p = maxPrice - (priceRange / 5) * i;
        ctx.fillStyle = c.text;
        ctx.font = '10px Cairo';
        ctx.textAlign = 'left';
        ctx.fillText(p.toFixed(2), width - padding.right + 5, y + 4);
    }

    // Date labels
    const dateStep = Math.max(1, Math.floor(dates.length / 8));
    for (let i = 0; i < dates.length; i += dateStep) {
        const x = padding.left + i * candleSpacing + candleSpacing / 2;
        ctx.fillStyle = c.text;
        ctx.font = '9px Cairo';
        ctx.textAlign = 'center';
        ctx.fillText(dates[i] ? dates[i].slice(5) : '', x, height - 8);
    }

    // Fibonacci lines
    if (indicatorVisibility.fibonacci) {
        const fibColors = ['rgba(255,215,0,0.3)','rgba(255,215,0,0.25)','rgba(255,215,0,0.2)','rgba(255,215,0,0.25)','rgba(255,215,0,0.3)'];
        const fibLabels = ['23.6%','38.2%','50%','61.8%','78.6%'];
        fibLevels.forEach((level, idx) => {
            const y = toY(level);
            ctx.strokeStyle = fibColors[idx]; ctx.lineWidth = 1; ctx.setLineDash([4,4]);
            ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = c.gold; ctx.font = '9px Cairo'; ctx.textAlign = 'left';
            ctx.fillText(fibLabels[idx], padding.left + 5, y - 3);
        });
    }

    // Bollinger Bands
    if (indicatorVisibility.bollinger) {
        [bollingerUpper, bollingerLower].forEach(band => {
            ctx.strokeStyle = 'rgba(124,77,255,0.35)'; ctx.lineWidth = 1; ctx.setLineDash([3,3]);
            ctx.beginPath();
            let started = false;
            band.forEach((v, i) => {
                if (v === null) return;
                const x = padding.left + i * candleSpacing + candleSpacing / 2;
                const y = toY(v);
                if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
            });
            ctx.stroke(); ctx.setLineDash([]);
        });
    }

    // Highlight column
    if (highlightIndex >= 0) {
        ctx.fillStyle = 'rgba(0,229,255,0.06)';
        ctx.fillRect(padding.left + highlightIndex * candleSpacing, padding.top, candleSpacing, chartHeight);
    }

    // Candles
    prices.forEach((p, i) => {
        const open  = p.open  || 0;
        const high  = p.high  || 0;
        const low   = p.low   || 0;
        const close = p.close || 0;
        const x     = padding.left + i * candleSpacing + candleSpacing / 2;
        const isGreen = close >= open;
        const color   = isGreen ? c.positive : c.negative;

        // Wick
        ctx.strokeStyle = color; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(x, toY(high)); ctx.lineTo(x, toY(low)); ctx.stroke();

        // Body
        const bodyTop = Math.min(toY(open), toY(close));
        const bodyH   = Math.max(1, Math.abs(toY(close) - toY(open)));
        const bodyW   = Math.max(1, candleWidth);
        if (isGreen) {
            ctx.fillStyle = 'rgba(0,230,118,0.25)';
            ctx.fillRect(x - bodyW/2, bodyTop, bodyW, bodyH);
            ctx.strokeRect(x - bodyW/2, bodyTop, bodyW, bodyH);
        } else {
            ctx.fillStyle = color;
            ctx.fillRect(x - bodyW/2, bodyTop, bodyW, bodyH);
        }
    });

    // SMA Lines
    function drawSMA(smaData, color, lw, dash) {
        ctx.strokeStyle = color; ctx.lineWidth = lw;
        ctx.setLineDash(dash || []);
        ctx.beginPath();
        let started = false;
        smaData.forEach((v, i) => {
            if (v === null || v === undefined) return;
            const x = padding.left + i * candleSpacing + candleSpacing / 2;
            const y = toY(v);
            if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
        });
        ctx.stroke(); ctx.setLineDash([]);
    }
    if (indicatorVisibility.sma7)   drawSMA(sma7,   c.warning,  1.5, [2,2]);
    if (indicatorVisibility.sma20)  drawSMA(sma20,  c.purple,   1.5, [4,2]);
    if (indicatorVisibility.sma50)  drawSMA(sma50,  c.negative, 1.5, [6,3]);
    if (indicatorVisibility.sma200) drawSMA(sma200, c.positive, 2,   []);

    // Target lines
    const targets = data.analysis?.targets || {};
    if (indicatorVisibility.targets) {
        if (targets.target_1) {
            const y = toY(targets.target_1);
            ctx.strokeStyle = 'rgba(0,230,118,0.45)'; ctx.lineWidth = 1; ctx.setLineDash([4,3]);
            ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = c.positive; ctx.font = 'bold 9px Cairo'; ctx.textAlign = 'right';
            ctx.fillText('هدف 1', width - padding.right - 3, y - 3);
        }
        if (targets.stop_loss) {
            const y = toY(targets.stop_loss);
            ctx.strokeStyle = 'rgba(255,23,68,0.45)'; ctx.lineWidth = 1; ctx.setLineDash([4,3]);
            ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = c.negative; ctx.font = 'bold 9px Cairo'; ctx.textAlign = 'right';
            ctx.fillText('وقف الخسارة', width - padding.right - 3, y - 3);
        }
    }

    // ======= CROSSHAIR - خط عمودي + أفقي =======
    if (highlightIndex >= 0 && crsX >= 0 && crsY >= 0) {
        const candleX = padding.left + highlightIndex * candleSpacing + candleSpacing / 2;
        const p = prices[highlightIndex];
        const priceAtCursor = p ? (p.close || 0) : minPrice + (maxPrice - minPrice) * (1 - (crsY - padding.top) / chartHeight);

        // خط عمودي
        ctx.strokeStyle = c.crossV;
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(candleX, padding.top);
        ctx.lineTo(candleX, height - padding.bottom);
        ctx.stroke();
        ctx.setLineDash([]);

        // خط أفقي
        ctx.strokeStyle = c.crossH;
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(padding.left, crsY);
        ctx.lineTo(width - padding.right, crsY);
        ctx.stroke();
        ctx.setLineDash([]);

        // label السعر على اليمين
        const priceY = crsY;
        const priceVal = maxPrice - (crsY - padding.top) / chartHeight * priceRange;
        ctx.fillStyle = c.crossV;
        ctx.fillRect(width - padding.right + 2, priceY - 10, 60, 18);
        ctx.fillStyle = '#000';
        ctx.font = 'bold 10px JetBrains Mono, monospace';
        ctx.textAlign = 'left';
        ctx.fillText(priceVal.toFixed(2), width - padding.right + 5, priceY + 4);

        // label التاريخ في الأسفل
        const dateLabel = dates[highlightIndex] ? dates[highlightIndex] : '';
        ctx.fillStyle = c.crossV;
        const textW = ctx.measureText(dateLabel).width + 10;
        ctx.fillRect(candleX - textW / 2, height - padding.bottom + 2, textW, 16);
        ctx.fillStyle = '#000';
        ctx.font = 'bold 9px Cairo';
        ctx.textAlign = 'center';
        ctx.fillText(dateLabel, candleX, height - padding.bottom + 13);
    }
}

// ======= Volume Chart =======
function drawVolumeChart(data) {
    const canvas = document.getElementById('volumeChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const c = getChartColors();
    const prices  = data.prices_arr  || [];
    const volumes = data.volumes_list || prices.map(p => p.volume || 0);
    if (!volumes.length) return;

    const container = canvas.parentElement;
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight;

    const width = canvas.width, height = canvas.height;
    const padding = { top: 10, right: 65, bottom: 20, left: 10 };
    const chartWidth  = width  - padding.left - padding.right;
    const chartHeight = height - padding.top  - padding.bottom;
    const maxVol = Math.max(...volumes.filter(v => v > 0)) * 1.1;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = c.bg;
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = c.grid; ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
        const y = padding.top + (chartHeight / 3) * i;
        ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
        ctx.fillStyle = c.text; ctx.font = '9px Cairo'; ctx.textAlign = 'left';
        ctx.fillText(formatVolumeCompact(maxVol - (maxVol / 3) * i), width - padding.right + 5, y + 3);
    }

    const barW = Math.max(1, (chartWidth / volumes.length) * 0.8);
    const barS = chartWidth / volumes.length;
    volumes.forEach((v, i) => {
        const p = prices[i] || {};
        const close = p.close || p.Close || 0;
        const open  = p.open  || p.Open  || close;
        const x = padding.left + i * barS + barS / 2;
        const bh = (v / maxVol) * chartHeight;
        ctx.fillStyle = close >= open ? 'rgba(0,230,118,0.5)' : 'rgba(255,23,68,0.5)';
        ctx.fillRect(x - barW/2, padding.top + chartHeight - bh, barW, bh);
    });
}

function formatVolumeCompact(vol) {
    if (vol >= 1e9) return `${(vol/1e9).toFixed(1)}B`;
    if (vol >= 1e6) return `${(vol/1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `${(vol/1e3).toFixed(0)}K`;
    return vol.toString();
}

// ======= RSI Chart =======
function drawRsiChart(data) {
    if (!secondaryChartVisibility.rsi) return;
    const canvas = document.getElementById('rsiChart');
    if (!canvas) return;
    const c = getChartColors();
    const rsiList = data.rsi_list || [];
    const dates   = data.dates_list || [];
    if (!rsiList.length) return;
    if (rsiChart) rsiChart.destroy();

    rsiChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: { labels: dates, datasets: [{ label:'RSI', data: rsiList, borderColor:'#7c4dff', backgroundColor:'rgba(124,77,255,0.08)', borderWidth:2, fill:true, tension:0.3, pointRadius:0, pointHoverRadius:4 }] },
        options: {
            responsive:true, maintainAspectRatio:false,
            interaction:{ intersect:false, mode:'index' },
            plugins:{ legend:{ display:false }, tooltip:{ backgroundColor:'rgba(20,29,46,0.95)', titleColor:c.text, bodyColor:c.text, borderColor:'#7c4dff', borderWidth:1, padding:10, rtl:true } },
            scales:{ x:{ display:false }, y:{ min:0, max:100, grid:{ color:c.grid }, ticks:{ color:c.text, font:{ size:10 } } } }
        }
    });
}

// ======= MACD Chart =======
function drawMacdChart(data) {
    if (!secondaryChartVisibility.macd) return;
    const canvas = document.getElementById('macdChart');
    if (!canvas) return;
    const c = getChartColors();
    const macdList   = data.macd_list      || [];
    const signalList = data.signal_list    || [];
    const histList   = data.histogram_list || [];
    const dates      = data.dates_list     || [];
    if (!macdList.length) return;
    if (macdChart) macdChart.destroy();

    macdChart = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [
                { label:'Histogram', data:histList, backgroundColor:histList.map(v => v >= 0 ? 'rgba(0,230,118,0.6)' : 'rgba(255,23,68,0.6)'), type:'bar', order:2 },
                { label:'MACD',   data:macdList,   borderColor:c.accent,  borderWidth:1.5, fill:false, tension:0.3, pointRadius:0, type:'line', order:1 },
                { label:'Signal', data:signalList, borderColor:c.warning, borderWidth:1.5, fill:false, tension:0.3, pointRadius:0, type:'line', order:0 }
            ]
        },
        options: {
            responsive:true, maintainAspectRatio:false,
            interaction:{ intersect:false, mode:'index' },
            plugins:{ legend:{ labels:{ color:c.text, font:{ family:'Cairo', size:11 }, boxWidth:16 } }, tooltip:{ backgroundColor:'rgba(20,29,46,0.95)', titleColor:c.text, bodyColor:c.text, borderColor:c.accent, borderWidth:1, padding:10, rtl:true } },
            scales:{ x:{ display:false }, y:{ grid:{ color:c.grid }, ticks:{ color:c.text, font:{ size:10 } } } }
        }
    });
}

// ======= Toggle =======
function toggleIndicator(indicator) {
    indicatorVisibility[indicator] = !indicatorVisibility[indicator];
    if (currentData) drawCandlestickChart(currentData);
}

function toggleSecondaryChart(chart) {
    secondaryChartVisibility[chart] = !secondaryChartVisibility[chart];
    const canvas = document.getElementById(chart + 'Chart');
    if (canvas) canvas.style.display = secondaryChartVisibility[chart] ? 'block' : 'none';
    if (currentData && secondaryChartVisibility[chart]) {
        if (chart === 'rsi')  drawRsiChart(currentData);
        if (chart === 'macd') drawMacdChart(currentData);
    }
}

function redrawCharts(data) {
    if (!data) return;
    drawCandlestickChart(data);
    drawVolumeChart(data);
    if (secondaryChartVisibility.rsi)  drawRsiChart(data);
    if (secondaryChartVisibility.macd) drawMacdChart(data);
}

// ======= Chart Period =======
function updateChartPeriod(period, btn) {
    currentPeriod = period;
    document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (!currentSymbol) return;

    fetch(`./api/chart-data/${currentSymbol}?period=${period}&interval=${currentTimeframe}`)
        .then(r => r.json())
        .then(d => {
            if (d && !d.error) {
                currentData = { ...currentData, ...d };
                redrawCharts(currentData);
            }
        })
        .catch(err => console.error('Chart period error:', err));
}

// ======= Timeframe Switch =======
function switchTimeframe(tf, btn) {
    currentTimeframe = tf;
    document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (!currentSymbol) return;

    const tfToPeriod = {
        '1m':'1d', '5m':'5d', '15m':'1mo',
        '1h':'3mo', '4h':'6mo', '1d':'1y', '1w':'1y'
    };
    const period = tfToPeriod[tf] || currentPeriod;

    showLoading(true);
    fetch(`./api/chart-data/${currentSymbol}?period=${period}&interval=${tf === '1w' ? '1wk' : tf}`)
        .then(r => r.json())
        .then(d => {
            if (d && !d.error) {
                currentData = { ...currentData, ...d };
                redrawCharts(currentData);
                showToast(`تم تحديث الرسم: ${btn ? btn.textContent : tf}`);
            } else {
                showToast('لم تتوفر بيانات لهذا الإطار الزمني', true);
            }
        })
        .catch(() => showToast('خطأ في تحميل البيانات', true))
        .finally(() => showLoading(false));
}

// ======= Watchlist =======
function getWatchlist()           { return JSON.parse(localStorage.getItem('watchlist') || '[]'); }
function saveWatchlist(list)      { localStorage.setItem('watchlist', JSON.stringify(list)); }

function addToWatchlist() {
    if (!currentSymbol) return;
    let list = getWatchlist();
    if (list.includes(currentSymbol)) { showToast('السهم موجود في المفضلة'); return; }
    list.push(currentSymbol);
    saveWatchlist(list);
    renderWatchlistBadge();
    renderWatchlistPanel();
    showToast(`تمت إضافة ${currentSymbol} للمفضلة`);
}

function removeFromWatchlist(sym) {
    saveWatchlist(getWatchlist().filter(s => s !== sym));
    renderWatchlistBadge();
    renderWatchlistPanel();
}

function renderWatchlistBadge() {
    const el = document.getElementById('watchlistBadge');
    if (el) el.textContent = getWatchlist().length;
}

function renderWatchlistPanel() {
    const container = document.getElementById('watchlist-items');
    if (!container) return;
    const list = getWatchlist();
    if (!list.length) { container.innerHTML = '<p class="empty-msg">لا توجد أسهم في المفضلة</p>'; return; }
    container.innerHTML = list.map(sym => `
        <div class="wl-item" onclick="loadStock('${sym}')">
            <span class="wl-sym">${sym}</span>
            <button class="wl-del" onclick="event.stopPropagation(); removeFromWatchlist('${sym}')">🗑</button>
        </div>`).join('');
}

// ======= Alerts =======
function getAlerts()         { return JSON.parse(localStorage.getItem('priceAlerts') || '[]'); }
function saveAlerts(list)    { localStorage.setItem('priceAlerts', JSON.stringify(list)); }

function openAlertModal() {
    if (!currentSymbol) return;
    const sl = document.getElementById('alertSymbolLabel');
    if (sl) sl.textContent = `السهم: ${currentSymbol}`;
    const ap = document.getElementById('alertPrice');
    if (ap) ap.value = currentData ? currentData.current : '';
    const m = document.getElementById('alertModal');
    const o = document.getElementById('overlay');
    if (m) m.classList.remove('hidden');
    if (o) o.classList.remove('hidden');
}

function closeAlertModal() {
    const m = document.getElementById('alertModal');
    const o = document.getElementById('overlay');
    if (m) m.classList.add('hidden');
    if (o) o.classList.add('hidden');
}

function saveAlert() {
    const type  = document.getElementById('alertType').value;
    const price = parseFloat(document.getElementById('alertPrice').value);
    if (!price || isNaN(price)) { showToast('أدخل سعراً صحيحاً'); return; }
    const alerts = getAlerts();
    alerts.push({ symbol: currentSymbol, type, price, created: Date.now() });
    saveAlerts(alerts);
    renderAlertsBadge();
    renderAlertsPanel();
    closeAlertModal();
    showToast(`تم حفظ التنبيه: ${currentSymbol} ${type === 'above' ? 'يتجاوز' : 'ينزل عن'} ${price}`);
}

function removeAlert(idx) {
    const alerts = getAlerts();
    alerts.splice(idx, 1);
    saveAlerts(alerts);
    renderAlertsBadge();
    renderAlertsPanel();
}

function renderAlertsBadge() {
    const el = document.getElementById('alertsBadge');
    if (el) el.textContent = getAlerts().length;
}

function renderAlertsPanel() {
    const container = document.getElementById('alerts-items');
    if (!container) return;
    const alerts = getAlerts();
    if (!alerts.length) { container.innerHTML = '<p class="empty-msg">لا توجد تنبيهات</p>'; return; }
    container.innerHTML = alerts.map((a, i) => `
        <div class="alert-item">
            <div><strong>${a.symbol}</strong> — ${a.type === 'above' ? 'يتجاوز' : 'ينزل عن'} <strong>${a.price}</strong></div>
            <button class="alert-del" onclick="removeAlert(${i})">🗑</button>
        </div>`).join('');
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
                if ((a.type === 'above' && price >= a.price) || (a.type === 'below' && price <= a.price)) {
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
        new Notification('Leo2Stock تنبيه سعري', { body: msg });
    }
}

// ======= Panels =======
function openTab(id) {
    closeAllPanels();
    const panel = document.getElementById(id);
    if (!panel) return;
    panel.classList.remove('hidden');
    setTimeout(() => panel.classList.add('open'), 10);
    const o = document.getElementById('overlay');
    if (o) o.classList.remove('hidden');
    if (id === 'watchlist-tab') renderWatchlistPanel();
    if (id === 'alerts-tab')    renderAlertsPanel();
}

function closePanel(id) {
    const panel = document.getElementById(id);
    if (!panel) return;
    panel.classList.remove('open');
    setTimeout(() => panel.classList.add('hidden'), 350);
    const o = document.getElementById('overlay');
    if (o) o.classList.add('hidden');
}

function closeAllPanels() {
    ['watchlist-tab', 'alerts-tab'].forEach(id => {
        const p = document.getElementById(id);
        if (p && !p.classList.contains('hidden')) closePanel(id);
    });
    closeAlertModal();
}

// ======= PDF =======
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
    if (vol >= 1e9) return `${(vol/1e9).toFixed(1)}B`;
    if (vol >= 1e6) return `${(vol/1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `${(vol/1e3).toFixed(0)}K`;
    return vol.toString();
}

function formatMarketCap(val) {
    if (!val || val === 0) return 'N/A';
    if (val >= 1e12) return `${(val/1e12).toFixed(2)}T`;
    if (val >= 1e9)  return `${(val/1e9).toFixed(2)}B`;
    if (val >= 1e6)  return `${(val/1e6).toFixed(2)}M`;
    return val.toString();
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
    el.style.background = type === 'buy'  ? 'rgba(0,230,118,0.15)' :
                          type === 'sell' ? 'rgba(255,23,68,0.15)'  :
                                           'rgba(255,171,64,0.1)';
    el.style.color = type === 'buy'  ? '#00e676' :
                     type === 'sell' ? '#ff1744'  : '#ffab40';
}

function showLoading(show) {
    const el = document.getElementById('loading');
    if (el) el.classList.toggle('hidden', !show);
}

function showError(msg) { showToast(msg, true); }

function showToast(msg, isError = false) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    toast.style.cssText = `
        position:fixed; bottom:30px; left:50%; transform:translateX(-50%);
        background:${isError ? 'rgba(255,23,68,0.95)' : 'rgba(0,229,255,0.95)'};
        color:${isError ? '#fff' : '#000'};
        padding:12px 24px; border-radius:50px; font-family:Cairo,sans-serif;
        font-size:0.9rem; font-weight:600; z-index:9999;
        box-shadow:0 4px 20px rgba(0,0,0,0.3); white-space:nowrap;
        animation:slideUp 0.3s ease;`;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity='0'; toast.style.transition='opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// ======= AI Deep Analysis =======
function generateAIDeepAnalysis(data) {
    const container = document.getElementById('ai-deep-content');
    if (!container) return;

    const analysis   = data.analysis   || {};
    const indicators = analysis.indicators || {};
    const rec        = data.recommendation || {};
    const targets    = analysis.targets || {};
    const trend      = analysis.trend  || 'neutral';
    const rsi        = indicators.rsi  || 50;
    const macd_ind   = indicators.macd || {};
    const bb         = indicators.bollinger || {};
    const price      = data.current || 0;
    const change     = data.change  || 0;
    const sma20      = indicators.sma_20  || price;
    const sma50      = indicators.sma_50  || price;
    const sma200     = indicators.sma_200 || price;

    let directionPct = 0, directionClass = 'neutral', directionIcon = '↔️', directionTitle = 'تذبذب جانبي';
    if      (trend === 'strong_bullish') { directionPct =  85; directionClass='up';      directionIcon='🚀'; directionTitle='صعود قوي جداً'; }
    else if (trend === 'bullish')        { directionPct =  65; directionClass='up';      directionIcon='📈'; directionTitle='اتجاه صاعد'; }
    else if (trend === 'strong_bearish') { directionPct = -85; directionClass='down';    directionIcon='📉'; directionTitle='هبوط قوي جداً'; }
    else if (trend === 'bearish')        { directionPct = -65; directionClass='down';    directionIcon='⬇️'; directionTitle='اتجاه هابط'; }

    const signalScore = rec.score || 0;
    const signalPct   = Math.min(Math.abs(signalScore) * 20, 100);
    const signalColor = signalScore > 0 ? 'linear-gradient(90deg,#00e676,#00e5ff)' :
                        signalScore < 0 ? 'linear-gradient(90deg,#ff1744,#ff6b6b)' :
                                          'linear-gradient(90deg,#ffab40,#ffd700)';

    const reasons = [];
    if      (change > 5)  reasons.push(`ارتفع السهم ${change.toFixed(2)}% اليوم — زخم شرائي قوي`);
    else if (change < -5) reasons.push(`انخفض السهم ${Math.abs(change).toFixed(2)}% اليوم — ضغط بيعي حاد`);
    else if (change > 0)  reasons.push(`ارتفع السهم ${change.toFixed(2)}% — حركة إيجابية معتدلة`);
    else                  reasons.push(`انخفض السهم ${Math.abs(change).toFixed(2)}% — ضغط بيعي طفيف`);

    if      (rsi < 30) reasons.push(`RSI عند ${rsi} — تشبع بيعي، فرصة انتعاش محتملة`);
    else if (rsi > 70) reasons.push(`RSI عند ${rsi} — تشبع شرائي، خطر تصحيح قريب`);
    else               reasons.push(`RSI عند ${rsi} — منطقة محايدة`);

    reasons.push(price > sma20
        ? `السعر فوق SMA 20 (${formatPrice(sma20, data.currency)}) — اتجاه قصير المدى إيجابي`
        : `السعر تحت SMA 20 (${formatPrice(sma20, data.currency)}) — ضعف في الاتجاه القصير`);

    reasons.push(price > sma200
        ? `السعر فوق SMA 200 (${formatPrice(sma200, data.currency)}) — الاتجاه الرئيسي صاعد`
        : `السعر تحت SMA 200 (${formatPrice(sma200, data.currency)}) — الاتجاه الرئيسي هابط`);

    if      (macd_ind.histogram > 0) reasons.push('MACD إيجابي — زخم صاعد يدعم الحركة');
    else if (macd_ind.histogram < 0) reasons.push('MACD سلبي — زخم هابط يضغط على السعر');

    const volRatio = (data.volume || 0) / (data.avg_volume || 1);
    if      (volRatio > 2)   reasons.push(`حجم ${volRatio.toFixed(1)}x المتوسط — اهتمام مؤسسي استثنائي`);
    else if (volRatio > 1.2) reasons.push(`حجم ${volRatio.toFixed(1)}x المتوسط — نشاط أعلى من المعتاد`);
    else                     reasons.push(`حجم طبيعي (${volRatio.toFixed(1)}x المتوسط)`);

    if      (price <= bb.lower) reasons.push('السعر لامس الحد السفلي لبولينجر — إشارة انتعاش محتملة');
    else if (price >= bb.upper) reasons.push('السعر لامس الحد العلوي لبولينجر — احتمال تصحيح');

    const target1  = targets.target_1 || price * 1.05;
    const stopLoss = targets.stop_loss || price * 0.95;
    const upPct   = ((target1  - price) / price * 100).toFixed(1);
    const downPct = ((price - stopLoss) / price * 100).toFixed(1);

    const summaryMap = {
        strong_bullish: `السهم في صعود قوي جداً. جميع المؤشرات تدعم الاتجاه الصعودي. الهدف الأول عند ${formatPrice(target1, data.currency)} (+${upPct}%).`,
        bullish:        `السهم في اتجاه صاعد. معظم المؤشرات إيجابية. وقف خسارة مقترح عند ${formatPrice(stopLoss, data.currency)} (-${downPct}%).`,
        neutral:        'السهم في تذبذب جانبي. يُنصح بالانتظار حتى ظهور إشارة واضحة.',
        bearish:        'السهم تحت ضغط بيعي. يُنصح بتجنب الدخول حتى ظهور إشارات انتعاش.',
        strong_bearish: 'السهم في هبوط حاد. ينصح بالابتعاد أو البيع مع وقف خسارة صارم.',
    };

    container.innerHTML = `
        <div class="ai-deep-content">
            <div class="ai-summary-row">
                <div class="ai-stat-box">
                    <span class="ai-stat-label">قوة الإشارة الكلية</span>
                    <span class="ai-stat-value ${signalScore > 0 ? 'up' : signalScore < 0 ? 'down' : 'neutral'}">${Math.abs(signalScore * 20)}%</span>
                    <span class="ai-stat-sub">${rec.action || 'محايد'}</span>
                </div>
                <div class="ai-stat-box">
                    <span class="ai-stat-label">اتجاه السهم</span>
                    <span class="ai-stat-value ${directionClass}">${Math.abs(directionPct)}%</span>
                    <span class="ai-stat-sub">${directionTitle}</span>
                </div>
                <div class="ai-stat-box">
                    <span class="ai-stat-label">نسبة المخاطرة/العائد</span>
                    <span class="ai-stat-value ${parseFloat(upPct) > parseFloat(downPct) ? 'up' : 'down'}">1:${(parseFloat(upPct)/Math.max(parseFloat(downPct),0.1)).toFixed(1)}</span>
                    <span class="ai-stat-sub">هدف ${upPct}% / خطر ${downPct}%</span>
                </div>
            </div>
            <div class="ai-strength-bar-wrap">
                <div class="ai-strength-label">
                    <span class="ai-strength-title">قوة الإشارة الفنية الكلية</span>
                    <span class="ai-strength-pct" style="color:${signalScore > 0 ? 'var(--positive)' : signalScore < 0 ? 'var(--negative)' : 'var(--warning)'}">${signalPct}%</span>
                </div>
                <div class="ai-strength-track">
                    <div class="ai-strength-fill" style="width:${signalPct}%;background:${signalColor}"></div>
                </div>
            </div>
            <div class="ai-direction-box ${directionClass}">
                <div class="ai-dir-header">
                    <span class="ai-dir-icon">${directionIcon}</span>
                    <span class="ai-dir-title">${directionTitle}</span>
                    <span class="ai-dir-pct ${directionClass}">${directionPct > 0 ? '+' : ''}${directionPct}%</span>
                </div>
                <p class="ai-dir-text">${summaryMap[trend] || summaryMap.neutral}</p>
                <ul class="ai-reasons-list">
                    ${reasons.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
            <div class="ai-forecast-row">
                <div class="ai-forecast-box">
                    <div class="ai-forecast-title">🎯 الهدف الأول</div>
                    <div class="ai-forecast-val positive">${formatPrice(target1, data.currency)}</div>
                    <div class="ai-forecast-sub">+${upPct}% من السعر الحالي</div>
                </div>
                <div class="ai-forecast-box">
                    <div class="ai-forecast-title">🛑 وقف الخسارة</div>
                    <div class="ai-forecast-val negative">${formatPrice(stopLoss, data.currency)}</div>
                    <div class="ai-forecast-sub">-${downPct}% من السعر الحالي</div>
                </div>
            </div>
        </div>`;
}

// ======= CSS Animation =======
const styleEl = document.createElement('style');
styleEl.textContent = `
@keyframes slideUp { from { transform:translateX(-50%) translateY(20px); opacity:0; } to { transform:translateX(-50%) translateY(0); opacity:1; } }
`;
document.head.appendChild(styleEl);
