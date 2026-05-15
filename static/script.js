/* ============================================
   Leo2Stock — Main JavaScript v3.0
   Custom Candlestick Chart + AI Analysis
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
let currentTimeframe = '1h';

let indicatorVisibility = {
    sma7: true, sma20: true, sma50: true, sma200: true,
    fibonacci: false, bollinger: false, targets: true
};

let secondaryChartVisibility = { rsi: true, macd: true };

let mouseX = 0, mouseY = 0, isMouseOverChart = false;

// ======= Init =======
document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    renderWatchlistBadge();
    renderAlertsBadge();
    startAlertChecker();
    initLiveUsers();
    setupCrosshair();

    const symbolInput = document.getElementById('symbolInput');
    if (symbolInput) {
        symbolInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchStock();
        });
    }

    const heroInput = document.getElementById('symbolInputHero');
    if (heroInput) {
        heroInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchFromHero();
        });
    }

    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
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
        if (canvas && currentData) updateCrosshairInfo(mouseX, mouseY, canvas);
    });

    wrapper.addEventListener('mouseleave', () => {
        isMouseOverChart = false;
        const ci = document.getElementById('crosshairInfo');
        if (ci) ci.classList.add('hidden');
        if (currentData) drawCandlestickChart(currentData);
    });
}

function updateCrosshairInfo(mx, my, canvas) {
    const prices = currentData.prices_arr || [];
    const dates = currentData.dates_list || [];
    if (!prices.length) return;

    const padding = { top: 20, right: 60, bottom: 40, left: 10 };
    const chartWidth = canvas.width - padding.left - padding.right;
    const candleSpacing = chartWidth / prices.length;
    const candleIndex = Math.min(prices.length - 1, Math.max(0, Math.floor((mx - padding.left) / candleSpacing)));
    const p = prices[candleIndex];
    if (!p) return;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('crosshair-date', dates[candleIndex] || '—');
    set('crosshair-price', p.close || '—');
    set('crosshair-open', p.open || '—');
    set('crosshair-high', p.high || '—');
    set('crosshair-low', p.low || '—');
    set('crosshair-close', p.close || '—');
    set('crosshair-volume', formatVolume(p.volume || 0));

    const ci = document.getElementById('crosshairInfo');
    if (ci) ci.classList.remove('hidden');
    drawCandlestickChart(currentData, candleIndex);
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
        grid: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
        text: isDark ? '#8892a4' : '#5a6478',
        accent: '#00e5ff', positive: '#00e676', negative: '#ff1744',
        warning: '#ffab40', purple: '#7c4dff', gold: '#ffd700',
        bg: isDark ? '#141d2e' : '#ffffff',
        bg2: isDark ? '#1a2540' : '#f4f7fd',
    };
}

// ======= Market Switcher =======
function switchMarket(market, el) {
    currentMarket = market;
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    if (el) el.classList.add('active');
}

// ======= Search =======
function searchFromHero() {
    const heroInput = document.getElementById('symbolInputHero');
    const navInput = document.getElementById('symbolInput');
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
    } catch (err) {
        showError('خطأ في مسح RSI');
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
        return `
            <tr>
                <td><strong>${stock.symbol}</strong></td>
                <td>${stock.name || stock.symbol}</td>
                <td>${formatPrice(stock.price, stock.currency)}</td>
                <td class="${isPositive ? 'positive' : 'negative'}">${isPositive ? '+' : ''}${stock.change}%</td>
                <td><strong style="color:${stock.rsi < 30 ? '#00e676' : '#ff1744'}">${stock.rsi}</strong></td>
                <td><span class="rec-badge ${rec.color || 'gray'}">${rec.action || 'محايد'}</span></td>
                <td><button class="mini-btn" onclick="loadStock('${stock.symbol}')">تحليل</button></td>
            </tr>`;
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

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    set('res-symbol', data.symbol);
    set('res-name', data.name || data.symbol);
    set('res-sector', data.sector || 'غير محدد');
    set('res-market', data.market === 'saudi' ? '🇸🇦 سعودي' : '🇺🇸 أمريكي');
    set('res-industry', data.industry || 'غير محدد');
    set('res-price', formatPrice(data.current, data.currency));

    const changeEl = document.getElementById('res-change');
    if (changeEl) {
        changeEl.textContent = `${isPositive ? '+' : ''}${data.change}%`;
        changeEl.className = `price-delta ${isPositive ? 'positive' : 'negative'}`;
    }
    set('res-currency', data.currency || 'USD');
    set('res-open', formatPrice(data.open, data.currency));
    set('res-high', formatPrice(data.high, data.currency));
    set('res-low', formatPrice(data.low, data.currency));
    set('res-volume', formatVolume(data.volume));
    set('res-high52', formatPrice(data.high_52w, data.currency));
    set('res-low52', formatPrice(data.low_52w, data.currency));

    // Volume bar
    const avgVol = data.avg_volume || 0;
    const todayVol = data.volume || 0;
    const volRatio = avgVol > 0 ? (todayVol / avgVol) : 0;
    set('volume-comparison', avgVol > 0 ? `${volRatio.toFixed(1)}x المتوسط` : '—');
    const volBar = document.getElementById('volume-bar-fill');
    if (volBar) {
        volBar.style.width = `${Math.min(volRatio * 100, 100)}%`;
        volBar.style.background = volRatio > 1.5 ? 'linear-gradient(90deg,#ff1744,#ffab40)' :
                                   volRatio > 1 ? 'linear-gradient(90deg,#00e676,#00e5ff)' :
                                   'linear-gradient(90deg,#8892a4,#00e5ff)';
    }

    // AI Analysis (basic)
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
    styleSignal('sig-rsi', rsi < 30 ? 'buy' : rsi > 70 ? 'sell' : 'neutral');
    set('sig-rsi', rsi < 30 ? 'تشبع بيعي' : rsi > 70 ? 'تشبع شرائي' : 'محايد');

    const price = data.current;
    const sma20 = indicators.sma_20;
    const sma50 = indicators.sma_50;
    const sma200 = indicators.sma_200;

    set('ind-sma20', formatPrice(sma20, data.currency));
    setSignal('sig-sma20', price > sma20 ? 'buy' : 'sell', price > sma20 ? 'فوق' : 'تحت');
    set('ind-sma50', formatPrice(sma50, data.currency));
    setSignal('sig-sma50', price > sma50 ? 'buy' : 'sell', price > sma50 ? 'فوق' : 'تحت');
    set('ind-sma200', formatPrice(sma200, data.currency));
    setSignal('sig-sma200', price > sma200 ? 'buy' : 'sell', price > sma200 ? 'فوق' : 'تحت');
    set('ind-macd', macd.macd || '—');
    setSignal('sig-macd', macd.histogram > 0 ? 'buy' : 'sell', macd.histogram > 0 ? 'صاعد' : 'هابط');
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
    set('fund-sector', data.sector || 'غير محدد');
    set('fund-industry', data.industry || 'غير محدد');
    set('fund-support', formatPrice(analysis.support, data.currency));
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
    const signalsList = document.getElementById('signals-list');
    if (signalsList) {
        signalsList.innerHTML = analysis.signals && analysis.signals.length
            ? analysis.signals.map(s => `<li>${s}</li>`).join('')
            : '<li class="no-signals">لا توجد إشارات واضحة حالياً</li>';
    }

    // Impact Analysis
    displayImpactAnalysis(data);

    // Charts
    drawCandlestickChart(data);
    drawVolumeChart(data);
    drawRsiChart(data);
    drawMacdChart(data);

    // AI Deep Analysis
    setTimeout(() => generateAIDeepAnalysis(data), 100);

    // Show result
    const resultEl = document.getElementById('result');
    if (resultEl) {
        resultEl.classList.remove('hidden');
        resultEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Hide hero
    const heroEl = document.getElementById('hero-section');
    if (heroEl) heroEl.style.display = 'none';
}

// ======= AI Basic Analysis =======
function generateAIAnalysis(data) {
    const container = document.getElementById('ai-analysis-content');
    if (!container) return;
    const analysis = data.analysis || {};
    const indicators = analysis.indicators || {};
    const trend = analysis.trend || 'neutral';
    const rsi = indicators.rsi || 50;

    let aiText = '', confidence = 50;
    if (trend === 'strong_bullish') { aiText = 'السهم يظهر قوة شرائية ملحوظة مع وجوده فوق جميع المتوسطات الرئيسية.'; confidence = 85; }
    else if (trend === 'bullish') { aiText = 'الاتجاه العام صاعد مع إشارات إيجابية من المؤشرات الفنية.'; confidence = 70; }
    else if (trend === 'strong_bearish') { aiText = 'السهم في اتجاه هبوطي قوي مع ضغط بيعي واضح.'; confidence = 85; }
    else if (trend === 'bearish') { aiText = 'الاتجاه الهبوطي مستمر مع ضعف في الزخم الشرائي.'; confidence = 65; }
    else if (rsi < 30) { aiText = 'السهم في منطقة تشبع بيعي (RSI < 30) — احتمال ارتداد صعودي.'; confidence = 60; }
    else if (rsi > 70) { aiText = 'السهم في منطقة تشبع شرائي (RSI > 70) — احتمال تصحيح.'; confidence = 55; }
    else { aiText = 'السهم في منطقة محايدة — انتظار محفزات جديدة.'; confidence = 40; }

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
    const daysAhead = (hash % 45) + 15;
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + daysAhead);
    const months = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'];
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('earnings-date', `${futureDate.getDate()} ${months[futureDate.getMonth()]} ${futureDate.getFullYear()}`);
    set('earnings-quarter', ['Q1 2026','Q2 2026','Q3 2026','Q4 2026'][hash % 4]);
    set('earnings-estimate', ['أفضل من المتوقع','ضمن التوقعات','أقل من المتوقع','غير محدد'][hash % 4]);
}

// ======= Fibonacci =======
function displayFibonacci(data) {
    const prices = data.prices_arr || [];
    if (!prices.length) return;
    const closes = prices.map(p => p.close || 0);
    const high52 = data.high_52w || Math.max(...closes);
    const low52 = data.low_52w || Math.min(...closes);
    const range = high52 - low52;
    const levels = {
        'fib-0': high52, 'fib-236': high52 - range * 0.236,
        'fib-382': high52 - range * 0.382, 'fib-500': high52 - range * 0.5,
        'fib-618': high52 - range * 0.618, 'fib-786': high52 - range * 0.786,
        'fib-100': low52
    };
    Object.entries(levels).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = formatPrice(val, data.currency);
    });
}

// ======= Impact Analysis =======
function displayImpactAnalysis(data) {
    const symbol = data.symbol;
    const market = data.market;
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    set('impact-sector', data.sector || 'غير محدد');
    set('impact-industry', data.industry || 'غير محدد');
    set('impact-country', market === 'saudi' ? 'السعودية' : 'الولايات المتحدة');

    const hash = symbol.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    set('impact-employees', formatVolume(((hash % 500) + 1) * 1000));

    const revenue = ((hash % 100) + 10) * 1e9;
    const profit = revenue * ((hash % 30) + 5) / 100;
    set('impact-revenue', formatMarketCap(revenue));
    set('impact-profit', formatMarketCap(profit));
    set('impact-margin', `${(hash % 25) + 10}%`);
    set('impact-roe', `${(hash % 20) + 5}%`);

    const factorsContainer = document.getElementById('impact-factors');
    if (factorsContainer) {
        const factors = generateImpactFactors(data, hash);
        factorsContainer.innerHTML = factors.map(f => `
            <div class="impact-factor ${f.type}">
                <span class="impact-factor-icon">${f.icon}</span>
                <span class="impact-factor-text">${f.text}</span>
            </div>`).join('');
    }

    const outlookContainer = document.getElementById('impact-outlook');
    if (outlookContainer) {
        outlookContainer.innerHTML = `<p>${generateOutlook(data, hash)}</p>`;
    }
}

function generateImpactFactors(data, hash) {
    const factors = [];
    const isSaudi = data.market === 'saudi';

    if (data.change > 5) factors.push({ icon:'📈', text:`ارتفاع قوي بنسبة ${data.change}% يعكس تفاؤل السوق`, type:'positive' });
    else if (data.change < -5) factors.push({ icon:'📉', text:`انخفاض حاد بنسبة ${Math.abs(data.change)}% قد يعكس أخبار سلبية`, type:'negative' });

    const volRatio = (data.volume || 0) / (data.avg_volume || 1);
    if (volRatio > 2) factors.push({ icon:'🔥', text:`حجم تداول استثنائي (${volRatio.toFixed(1)}x المتوسط)`, type:'positive' });

    factors.push(isSaudi
        ? { icon:'🏛️', text:'تأثير إيجابي من رؤية 2030 والتحول الاقتصادي', type:'positive' }
        : { icon:'💵', text:'تأثر بالسياسة النقدية الفيدرالية وتوقعات الفائدة', type:'neutral' });

    const trend = data.analysis?.trend || 'neutral';
    if (trend.includes('bullish')) factors.push({ icon:'🎯', text:'الاتجاه الفني الصعودي يجذب المتداولين ويخلق زخماً إيجابياً', type:'positive' });
    else if (trend.includes('bearish')) factors.push({ icon:'⚠️', text:'الاتجاه الهبوطي قد يؤدي لمزيد من الضغط البيعي', type:'negative' });

    return factors;
}

function generateOutlook(data, hash) {
    const trend = data.analysis?.trend || 'neutral';
    const outlooks = {
        strong_bullish: 'التوقعات المستقبلية إيجابية جداً. المؤشرات الفنية تدعم استمرار الصعود مع احتمال كسر مستويات مقاومة جديدة.',
        bullish: 'التوقعات إيجابية بشكل عام مع احتمال تحقيق أهداف سعرية أعلى على المدى المتوسط.',
        neutral: 'التوقعات متباينة. السهم يحتاج محفزات جديدة لكسر نطاق التداول الحالي.',
        bearish: 'التوقعات سلبية على المدى القصير. ينصح بمراقبة مستويات الدعم الرئيسية.',
        strong_bearish: 'التوقعات سلبية بشكل واضح. الضغط البيعي قد يستمر لفترة أطول.'
    };
    return outlooks[trend] || outlooks.neutral;
}

// ======= Candlestick Chart =======
function drawCandlestickChart(data, highlightIndex = -1) {
    let canvas = document.getElementById('candlestickChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const c = getChartColors();

    const container = document.getElementById('mainChartWrapper');
    if (container) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight || 450;
    }

    const width = canvas.width;
    const height = canvas.height;
    const padding = { top: 20, right: 60, bottom: 40, left: 10 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const prices = data.prices_arr || [];
    const dates = data.dates_list || [];
    if (!prices.length) return;

    // Calculate SMAs
    const closes = prices.map(p => p.close || p.Close || 0);
    function calcSMA(arr, period) {
        return arr.map((_, i) => i < period - 1 ? null : arr.slice(i - period + 1, i + 1).reduce((a,b) => a+b, 0) / period);
    }
    const sma7 = calcSMA(closes, 7);
    const sma20 = calcSMA(closes, 20);
    const sma50 = calcSMA(closes, 50);
    const sma200 = calcSMA(closes, 200);

    // Bollinger Bands
    const bollingerUpper = closes.map((_, i) => {
        if (i < 19) return null;
        const slice = closes.slice(i - 19, i + 1);
        const mean = slice.reduce((a,b) => a+b, 0) / 20;
        const std = Math.sqrt(slice.reduce((a,b) => a + Math.pow(b - mean, 2), 0) / 20);
        return mean + std * 2;
    });
    const bollingerLower = closes.map((_, i) => {
        if (i < 19) return null;
        const slice = closes.slice(i - 19, i + 1);
        const mean = slice.reduce((a,b) => a+b, 0) / 20;
        const std = Math.sqrt(slice.reduce((a,b) => a + Math.pow(b - mean, 2), 0) / 20);
        return mean - std * 2;
    });

    // Fibonacci levels
    const high52 = data.high_52w || Math.max(...prices.map(p => p.high || 0));
    const low52 = data.low_52w || Math.min(...prices.map(p => p.low || 0));
    const range52 = high52 - low52;
    const fibLevels = [
        high52 - range52 * 0.236, high52 - range52 * 0.382,
        high52 - range52 * 0.5, high52 - range52 * 0.618,
        high52 - range52 * 0.786
    ];

    // Min/Max for scaling
    let allValues = [];
    prices.forEach(p => { allValues.push(p.high || 0); allValues.push(p.low || 0); });
    if (indicatorVisibility.bollinger) {
        bollingerUpper.forEach(v => { if (v) allValues.push(v); });
        bollingerLower.forEach(v => { if (v) allValues.push(v); });
    }
    if (indicatorVisibility.fibonacci) fibLevels.forEach(v => allValues.push(v));

    const minPrice = Math.min(...allValues.filter(v => v > 0)) * 0.98;
    const maxPrice = Math.max(...allValues) * 1.02;
    const priceRange = maxPrice - minPrice;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Grid
    ctx.strokeStyle = c.grid;
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        const p = maxPrice - (priceRange / 5) * i;
        ctx.fillStyle = c.text;
        ctx.font = '10px Cairo';
        ctx.textAlign = 'left';
        ctx.fillText(p.toFixed(2), width - padding.right + 5, y + 3);
    }

    // Date labels
    const dateStep = Math.max(1, Math.floor(dates.length / 8));
    for (let i = 0; i < dates.length; i += dateStep) {
        const x = padding.left + (i / (prices.length - 1)) * chartWidth;
        ctx.fillStyle = c.text;
        ctx.font = '9px Cairo';
        ctx.textAlign = 'center';
        ctx.fillText(dates[i] ? dates[i].slice(5) : '', x, height - 10);
    }

    const candleWidth = Math.max(1, (chartWidth / prices.length) * 0.7);
    const candleSpacing = chartWidth / prices.length;

    // Fibonacci
    if (indicatorVisibility.fibonacci) {
        const fibColors = ['rgba(255,215,0,0.3)','rgba(255,215,0,0.25)','rgba(255,215,0,0.2)','rgba(255,215,0,0.25)','rgba(255,215,0,0.3)'];
        const fibLabels = ['23.6%','38.2%','50%','61.8%','78.6%'];
        fibLevels.forEach((level, idx) => {
            const y = padding.top + ((maxPrice - level) / priceRange) * chartHeight;
            ctx.strokeStyle = fibColors[idx];
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(width - padding.right, y);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = c.gold;
            ctx.font = '9px Cairo';
            ctx.textAlign = 'left';
            ctx.fillText(fibLabels[idx], padding.left + 5, y - 3);
        });
    }

    // Bollinger
    if (indicatorVisibility.bollinger) {
        ctx.strokeStyle = 'rgba(124,77,255,0.3)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        ['Upper','Lower'].forEach((band, bi) => {
            const bandData = bi === 0 ? bollingerUpper : bollingerLower;
            ctx.beginPath();
            let started = false;
            bandData.forEach((v, i) => {
                if (v === null) return;
                const x = padding.left + i * candleSpacing + candleSpacing / 2;
                const y = padding.top + ((maxPrice - v) / priceRange) * chartHeight;
                if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
            });
            ctx.stroke();
        });
        ctx.setLineDash([]);
    }

    // Candles
    prices.forEach((p, i) => {
        const open = p.open || p.Open || p.close || 0;
        const high = p.high || p.High || 0;
        const low = p.low || p.Low || 0;
        const close = p.close || p.Close || 0;

        const x = padding.left + i * candleSpacing + candleSpacing / 2;
        const yOpen = padding.top + ((maxPrice - open) / priceRange) * chartHeight;
        const yHigh = padding.top + ((maxPrice - high) / priceRange) * chartHeight;
        const yLow = padding.top + ((maxPrice - low) / priceRange) * chartHeight;
        const yClose = padding.top + ((maxPrice - close) / priceRange) * chartHeight;
        const isGreen = close >= open;
        const color = isGreen ? c.positive : c.negative;

        if (i === highlightIndex) {
            ctx.fillStyle = 'rgba(0,229,255,0.1)';
            ctx.fillRect(x - candleSpacing / 2, padding.top, candleSpacing, chartHeight);
        }

        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, yHigh);
        ctx.lineTo(x, yLow);
        ctx.stroke();

        const bodyTop = Math.min(yOpen, yClose);
        const bodyH = Math.max(1, Math.abs(yClose - yOpen));
        const bodyW = Math.max(1, candleWidth);

        if (isGreen) {
            ctx.fillStyle = 'rgba(0,230,118,0.3)';
            ctx.fillRect(x - bodyW / 2, bodyTop, bodyW, bodyH);
            ctx.strokeRect(x - bodyW / 2, bodyTop, bodyW, bodyH);
        } else {
            ctx.fillStyle = color;
            ctx.fillRect(x - bodyW / 2, bodyTop, bodyW, bodyH);
        }
    });

    // SMA Lines
    function drawSMALine(smaData, color, lineWidth, dash) {
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.setLineDash(dash || []);
        ctx.beginPath();
        let started = false;
        smaData.forEach((v, i) => {
            if (v === null || v === undefined) return;
            const x = padding.left + i * candleSpacing + candleSpacing / 2;
            const y = padding.top + ((maxPrice - v) / priceRange) * chartHeight;
            if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.setLineDash([]);
    }

    if (indicatorVisibility.sma7) drawSMALine(sma7, c.warning, 1.5, [2, 2]);
    if (indicatorVisibility.sma20) drawSMALine(sma20, c.purple, 1.5, [4, 2]);
    if (indicatorVisibility.sma50) drawSMALine(sma50, c.negative, 1.5, [6, 3]);
    if (indicatorVisibility.sma200) drawSMALine(sma200, c.positive, 2, []);

    // Targets
    const targets = data.analysis?.targets || {};
    if (indicatorVisibility.targets) {
        if (targets.target_1) {
            const y = padding.top + ((maxPrice - targets.target_1) / priceRange) * chartHeight;
            ctx.strokeStyle = 'rgba(0,230,118,0.4)';
            ctx.lineWidth = 1;
            ctx.setLineDash([3, 3]);
            ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = c.positive;
            ctx.font = '9px Cairo';
            ctx.textAlign = 'right';
            ctx.fillText('هدف 1', width - padding.right - 5, y - 3);
        }
        if (targets.stop_loss) {
            const y = padding.top + ((maxPrice - targets.stop_loss) / priceRange) * chartHeight;
            ctx.strokeStyle = 'rgba(255,23,68,0.4)';
            ctx.lineWidth = 1;
            ctx.setLineDash([3, 3]);
            ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = c.negative;
            ctx.font = '9px Cairo';
            ctx.textAlign = 'right';
            ctx.fillText('وقف الخسارة', width - padding.right - 5, y - 3);
        }
    }

    // Crosshair
    if (isMouseOverChart && highlightIndex >= 0) {
        const x = padding.left + highlightIndex * candleSpacing + candleSpacing / 2;
        ctx.strokeStyle = 'rgba(0,229,255,0.5)';
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        ctx.beginPath();
        ctx.moveTo(x, padding.top);
        ctx.lineTo(x, height - padding.bottom);
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
    const volumes = data.volumes_list || prices.map(p => p.volume || 0);
    if (!volumes.length) return;

    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    const width = canvas.width, height = canvas.height;
    const padding = { top: 10, right: 60, bottom: 20, left: 10 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const maxVol = Math.max(...volumes.filter(v => v > 0)) * 1.1;

    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = c.grid;
    ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
        const y = padding.top + (chartHeight / 3) * i;
        ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
        ctx.fillStyle = c.text;
        ctx.font = '9px Cairo';
        ctx.textAlign = 'left';
        ctx.fillText(formatVolumeCompact(maxVol - (maxVol / 3) * i), width - padding.right + 5, y + 3);
    }

    const barWidth = Math.max(1, (chartWidth / volumes.length) * 0.8);
    const barSpacing = chartWidth / volumes.length;
    volumes.forEach((v, i) => {
        const p = prices[i] || {};
        const close = p.close || p.Close || 0;
        const open = p.open || p.Open || close;
        const x = padding.left + i * barSpacing + barSpacing / 2;
        const barH = (v / maxVol) * chartHeight;
        const y = padding.top + chartHeight - barH;
        ctx.fillStyle = close >= open ? 'rgba(0,230,118,0.5)' : 'rgba(255,23,68,0.5)';
        ctx.fillRect(x - barWidth / 2, y, barWidth, barH);
    });
}

function formatVolumeCompact(vol) {
    if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`;
    if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `${(vol / 1e3).toFixed(0)}K`;
    return vol.toString();
}

// ======= RSI Chart =======
function drawRsiChart(data) {
    if (!secondaryChartVisibility.rsi) return;
    const canvas = document.getElementById('rsiChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const c = getChartColors();
    const rsiList = data.rsi_list || [];
    const dates = data.dates_list || [];
    if (!rsiList.length) return;
    if (rsiChart) rsiChart.destroy();

    rsiChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'RSI', data: rsiList,
                borderColor: '#7c4dff', backgroundColor: 'rgba(124,77,255,0.08)',
                borderWidth: 2, fill: true, tension: 0.3, pointRadius: 0, pointHoverRadius: 4,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { display: false },
                tooltip: { backgroundColor: 'rgba(20,29,46,0.95)', titleColor: c.text, bodyColor: c.text, borderColor: '#7c4dff', borderWidth: 1, padding: 10, rtl: true }
            },
            scales: {
                x: { display: false },
                y: { min: 0, max: 100, grid: { color: c.grid }, ticks: { color: c.text, font: { size: 10 } } }
            }
        }
    });
}

// ======= MACD Chart =======
function drawMacdChart(data) {
    if (!secondaryChartVisibility.macd) return;
    const canvas = document.getElementById('macdChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const c = getChartColors();
    const macdList = data.macd_list || [];
    const signalList = data.signal_list || [];
    const histList = data.histogram_list || [];
    const dates = data.dates_list || [];
    if (!macdList.length) return;
    if (macdChart) macdChart.destroy();

    macdChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [
                { label: 'Histogram', data: histList, backgroundColor: histList.map(v => v >= 0 ? 'rgba(0,230,118,0.6)' : 'rgba(255,23,68,0.6)'), type: 'bar', order: 2 },
                { label: 'MACD', data: macdList, borderColor: c.accent, borderWidth: 1.5, fill: false, tension: 0.3, pointRadius: 0, type: 'line', order: 1 },
                { label: 'Signal', data: signalList, borderColor: c.warning, borderWidth: 1.5, fill: false, tension: 0.3, pointRadius: 0, type: 'line', order: 0 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { labels: { color: c.text, font: { family: 'Cairo', size: 11 }, boxWidth: 16 } },
                tooltip: { backgroundColor: 'rgba(20,29,46,0.95)', titleColor: c.text, bodyColor: c.text, borderColor: c.accent, borderWidth: 1, padding: 10, rtl: true }
            },
            scales: {
                x: { display: false },
                y: { grid: { color: c.grid }, ticks: { color: c.text, font: { size: 10 } } }
            }
        }
    });
}

// ======= Toggle Indicators =======
function toggleIndicator(indicator) {
    indicatorVisibility[indicator] = !indicatorVisibility[indicator];
    if (currentData) drawCandlestickChart(currentData);
}

function toggleSecondaryChart(chart) {
    secondaryChartVisibility[chart] = !secondaryChartVisibility[chart];
    const canvas = document.getElementById(chart + 'Chart');
    if (canvas) canvas.style.display = secondaryChartVisibility[chart] ? 'block' : 'none';
    if (currentData && secondaryChartVisibility[chart]) {
        if (chart === 'rsi') drawRsiChart(currentData);
        if (chart === 'macd') drawMacdChart(currentData);
    }
}

function redrawCharts(data) {
    if (!data) return;
    drawCandlestickChart(data);
    drawVolumeChart(data);
    if (secondaryChartVisibility.rsi) drawRsiChart(data);
    if (secondaryChartVisibility.macd) drawMacdChart(data);
}

function updateChartPeriod(period, btn) {
    document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (!currentSymbol) return;
    fetch(`./api/chart-data/${currentSymbol}?period=${period}`)
        .then(r => r.json())
        .then(d => {
            if (d && !d.error) {
                currentData = { ...currentData, ...d };
                redrawCharts(currentData);
            }
        })
        .catch(err => console.error('Chart data error:', err));
}

// ======= Timeframe Switch =======
function switchTimeframe(tf, btn) {
    currentTimeframe = tf;
    document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (!currentSymbol || !currentData) return;

    const tfToPeriod = { '1m':'1mo', '5m':'1mo', '15m':'3mo', '1h':'3mo', '4h':'6mo', '1d':'1y', '1w':'1y' };
    const tfToInterval = { '1m':'1m', '5m':'5m', '15m':'15m', '1h':'1h', '4h':'4h', '1d':'1d', '1w':'1wk' };
    const period = tfToPeriod[tf] || '1mo';
    const interval = tfToInterval[tf] || '1d';

    fetch(`./api/chart-data/${currentSymbol}?period=${period}&interval=${interval}`)
        .then(r => r.json())
        .then(d => {
            if (d && !d.error) {
                currentData = { ...currentData, ...d };
                redrawCharts(currentData);
            }
        })
        .catch(() => { if (currentData) redrawCharts(currentData); });
}

// ======= Watchlist =======
function getWatchlist() { return JSON.parse(localStorage.getItem('watchlist') || '[]'); }
function saveWatchlist(list) { localStorage.setItem('watchlist', JSON.stringify(list)); }

function addToWatchlist() {
    if (!currentSymbol) return;
    let list = getWatchlist();
    if (list.includes(currentSymbol)) { showToast('السهم موجود في المفضلة بالفعل'); return; }
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
function getAlerts() { return JSON.parse(localStorage.getItem('priceAlerts') || '[]'); }
function saveAlerts(list) { localStorage.setItem('priceAlerts', JSON.stringify(list)); }

function openAlertModal() {
    if (!currentSymbol) return;
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('alertSymbolLabel', `السهم: ${currentSymbol}`);
    const ap = document.getElementById('alertPrice');
    if (ap) ap.value = currentData ? currentData.current : '';
    document.getElementById('alertModal').classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
}

function closeAlertModal() {
    const m = document.getElementById('alertModal');
    const o = document.getElementById('overlay');
    if (m) m.classList.add('hidden');
    if (o) o.classList.add('hidden');
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
    if (!alerts.length) { container.innerHTML = '<p class="empty-msg">لا توجد تنبيهات مضافة</p>'; return; }
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
    document.getElementById('overlay').classList.remove('hidden');
    if (id === 'watchlist-tab') renderWatchlistPanel();
    if (id === 'alerts-tab') renderAlertsPanel();
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
    if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`;
    if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `${(vol / 1e3).toFixed(0)}K`;
    return vol.toString();
}

function formatMarketCap(val) {
    if (!val || val === 0) return 'N/A';
    if (val >= 1e12) return `${(val / 1e12).toFixed(2)}T`;
    if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B`;
    if (val >= 1e6) return `${(val / 1e6).toFixed(2)}M`;
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
    el.style.background = type === 'buy' ? 'rgba(0,230,118,0.15)' : type === 'sell' ? 'rgba(255,23,68,0.15)' : 'rgba(255,171,64,0.1)';
    el.style.color = type === 'buy' ? '#00e676' : type === 'sell' ? '#ff1744' : '#ffab40';
}

function showLoading(show) {
    const el = document.getElementById('loading');
    if (el) el.classList.toggle('hidden', !show);
}

function showError(msg) {
    showToast(msg, true);
}

function showToast(msg, isError = false) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    toast.style.cssText = `
        position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
        background: ${isError ? 'rgba(255,23,68,0.95)' : 'rgba(0,229,255,0.95)'};
        color: ${isError ? '#fff' : '#000'};
        padding: 12px 24px; border-radius: 50px; font-family: Cairo, sans-serif;
        font-size: 0.9rem; font-weight: 600; z-index: 9999;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        animation: slideUp 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// ======= AI Deep Analysis =======
function generateAIDeepAnalysis(data) {
    const container = document.getElementById('ai-deep-content');
    if (!container) return;

    const analysis = data.analysis || {};
    const indicators = analysis.indicators || {};
    const rec = data.recommendation || {};
    const targets = analysis.targets || {};
    const trend = analysis.trend || 'neutral';
    const rsi = indicators.rsi || 50;
    const macd = indicators.macd || {};
    const bb = indicators.bollinger || {};
    const price = data.current || 0;
    const change = data.change || 0;
    const sma20 = indicators.sma_20 || price;
    const sma50 = indicators.sma_50 || price;
    const sma200 = indicators.sma_200 || price;

    let directionPct = 0, directionClass = 'neutral', directionIcon = '↔️', directionTitle = 'تذبذب جانبي';
    if (trend === 'strong_bullish') { directionPct = 85; directionClass = 'up'; directionIcon = '🚀'; directionTitle = 'صعود قوي جداً'; }
    else if (trend === 'bullish') { directionPct = 65; directionClass = 'up'; directionIcon = '📈'; directionTitle = 'اتجاه صاعد'; }
    else if (trend === 'strong_bearish') { directionPct = -85; directionClass = 'down'; directionIcon = '📉'; directionTitle = 'هبوط قوي جداً'; }
    else if (trend === 'bearish') { directionPct = -65; directionClass = 'down'; directionIcon = '⬇️'; directionTitle = 'اتجاه هابط'; }

    const signalScore = rec.score || 0;
    const signalPct = Math.min(Math.abs(signalScore) * 20, 100);
    const signalColor = signalScore > 0 ? 'linear-gradient(90deg,#00e676,#00e5ff)' :
                        signalScore < 0 ? 'linear-gradient(90deg,#ff1744,#ff6b6b)' :
                        'linear-gradient(90deg,#ffab40,#ffd700)';

    const reasons = [];
    if (change > 5) reasons.push(`ارتفع السهم ${change.toFixed(2)}% اليوم — زخم شرائي قوي`);
    else if (change < -5) reasons.push(`انخفض السهم ${Math.abs(change).toFixed(2)}% اليوم — ضغط بيعي حاد`);
    else if (change > 0) reasons.push(`ارتفع السهم ${change.toFixed(2)}% — حركة إيجابية معتدلة`);
    else reasons.push(`انخفض السهم ${Math.abs(change).toFixed(2)}% — ضغط بيعي طفيف`);

    if (rsi < 30) reasons.push(`RSI عند ${rsi} — تشبع بيعي، فرصة انتعاش محتملة`);
    else if (rsi > 70) reasons.push(`RSI عند ${rsi} — تشبع شرائي، خطر تصحيح قريب`);
    else reasons.push(`RSI عند ${rsi} — منطقة محايدة`);

    reasons.push(price > sma20
        ? `السعر فوق SMA 20 (${formatPrice(sma20, data.currency)}) — اتجاه قصير المدى إيجابي`
        : `السعر تحت SMA 20 (${formatPrice(sma20, data.currency)}) — ضعف في الاتجاه القصير`);

    reasons.push(price > sma200
        ? `السعر فوق SMA 200 (${formatPrice(sma200, data.currency)}) — الاتجاه الرئيسي صاعد`
        : `السعر تحت SMA 200 (${formatPrice(sma200, data.currency)}) — الاتجاه الرئيسي هابط`);

    if (macd.histogram > 0) reasons.push('MACD إيجابي — زخم صاعد يدعم الحركة');
    else if (macd.histogram < 0) reasons.push('MACD سلبي — زخم هابط يضغط على السعر');

    const volRatio = (data.volume || 0) / (data.avg_volume || 1);
    if (volRatio > 2) reasons.push(`حجم التداول ${volRatio.toFixed(1)}x المتوسط — اهتمام مؤسسي استثنائي`);
    else if (volRatio > 1.2) reasons.push(`حجم التداول ${volRatio.toFixed(1)}x المتوسط — نشاط أعلى من المعتاد`);
    else reasons.push(`حجم التداول طبيعي (${volRatio.toFixed(1)}x المتوسط)`);

    if (price <= bb.lower) reasons.push('السعر لامس الحد السفلي لبولينجر — إشارة انتعاش محتملة');
    else if (price >= bb.upper) reasons.push('السعر لامس الحد العلوي لبولينجر — احتمال تصحيح');

    const target1 = targets.target_1 || price * 1.05;
    const stopLoss = targets.stop_loss || price * 0.95;
    const upPct = ((target1 - price) / price * 100).toFixed(1);
    const downPct = ((price - stopLoss) / price * 100).toFixed(1);

    const summaryMap = {
        strong_bullish: `السهم في صعود قوي جداً. جميع المؤشرات تدعم الاتجاه الصعودي. الهدف الأول عند ${formatPrice(target1, data.currency)} (+${upPct}%).`,
        bullish: `السهم في اتجاه صاعد. معظم المؤشرات إيجابية. يُنصح بالدخول مع وقف خسارة عند ${formatPrice(stopLoss, data.currency)} (-${downPct}%).`,
        neutral: `السهم في تذبذب جانبي. يُنصح بالانتظار حتى ظهور إشارة واضحة.`,
        bearish: `السهم تحت ضغط بيعي. يُنصح بتجنب الدخول حتى ظهور إشارات انتعاش.`,
        strong_bearish: `السهم في هبوط حاد. ينصح بالابتعاد أو البيع مع وقف خسارة صارم.`,
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
                    <span class="ai-stat-value ${parseFloat(upPct) > parseFloat(downPct) ? 'up' : 'down'}">1:${(parseFloat(upPct) / Math.max(parseFloat(downPct), 0.1)).toFixed(1)}</span>
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
styleEl.textContent = `@keyframes slideUp { from { transform: translateX(-50%) translateY(20px); opacity:0; } to { transform: translateX(-50%) translateY(0); opacity:1; } }`;
document.head.appendChild(styleEl);
