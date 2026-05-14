/* ============================================
   Leo2Stock — Main JavaScript (Enhanced v3.0)
   Custom Candlestick Chart with Canvas API
   AI Analysis, Fibonacci, Crosshair, Volume Analysis
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

// Indicator visibility state
let indicatorVisibility = {
    sma7: true,
    sma20: true,
    sma50: true,
    sma200: true,
    fibonacci: false,
    bollinger: false,
    targets: true
};

let secondaryChartVisibility = {
    rsi: true,
    macd: true
};

// Mouse tracking for crosshair
let mouseX = 0;
let mouseY = 0;
let isMouseOverChart = false;

// ======= Init =======
document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    renderWatchlistBadge();
    renderAlertsBadge();
    startAlertChecker();

    document.getElementById('symbolInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchStock();
    });

    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }

    setupCrosshair();
});

// ======= Crosshair Setup =======
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
            updateCrosshairInfo(mouseX, mouseY, canvas);
        }
    });

    wrapper.addEventListener('mouseleave', () => {
        isMouseOverChart = false;
        document.getElementById('crosshairInfo').classList.add('hidden');
        if (currentData) drawCandlestickChart(currentData);
    });
}

function updateCrosshairInfo(mx, my, canvas) {
    const prices = currentData.prices_arr || [];
    const dates = currentData.dates_list || [];
    if (!prices.length) return;

    const padding = { top: 20, right: 60, bottom: 40, left: 10 };
    const width = canvas.width;
    const height = canvas.height;
    const chartWidth = width - padding.left - padding.right;

    const candleSpacing = chartWidth / prices.length;
    const candleIndex = Math.min(
        prices.length - 1,
        Math.max(0, Math.floor((mx - padding.left) / candleSpacing))
    );

    const p = prices[candleIndex];
    if (!p) return;

    document.getElementById('crosshair-date').textContent = dates[candleIndex] || '—';
    document.getElementById('crosshair-price').textContent = p.close || p.Close || '—';
    document.getElementById('crosshair-open').textContent = p.open || p.Open || '—';
    document.getElementById('crosshair-high').textContent = p.high || p.High || '—';
    document.getElementById('crosshair-low').textContent = p.low || p.Low || '—';
    document.getElementById('crosshair-close').textContent = p.close || p.Close || '—';
    document.getElementById('crosshair-volume').textContent = formatVolume(p.volume || p.Volume || 0);

    document.getElementById('crosshairInfo').classList.remove('hidden');
    drawCandlestickChart(currentData, candleIndex);
}

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
        gold: '#ffd700',
        bg: isDark ? '#141d2e' : '#ffffff',
        bg2: isDark ? '#1a2540' : '#f4f7fd',
    };
}

// ======= Market Switcher =======
function switchMarket(market, el) {
    currentMarket = market;
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
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
    document.getElementById('res-industry').textContent = data.industry || 'غير محدد';
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

    // Volume Analysis Bar
    const avgVol = data.avg_volume || 0;
    const todayVol = data.volume || 0;
    const volRatio = avgVol > 0 ? (todayVol / avgVol) : 0;
    const volPercentage = Math.min(volRatio * 100, 200);

    document.getElementById('volume-comparison').textContent =
        avgVol > 0 ? `${volRatio.toFixed(1)}x المتوسط` : '—';

    const volBar = document.getElementById('volume-bar-fill');
    volBar.style.width = `${Math.min(volPercentage, 100)}%`;

    if (volRatio > 1.5) {
        volBar.style.background = 'linear-gradient(90deg, #ff1744, #ffab40)';
    } else if (volRatio > 1) {
        volBar.style.background = 'linear-gradient(90deg, #00e676, #00e5ff)';
    } else {
        volBar.style.background = 'linear-gradient(90deg, #8892a4, #00e5ff)';
    }

    // AI Analysis
    generateAIAnalysis(data);

    // Earnings
    displayEarnings(data);

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

    // Fibonacci
    displayFibonacci(data);

    // Indicators
    const rsi = indicators.rsi || 50;
    document.getElementById('ind-rsi').textContent = rsi;
    const rsiBar = document.getElementById('rsi-bar');
    rsiBar.style.width = `${Math.min(rsi, 100)}%`;
    rsiBar.style.background = rsi < 30 ? '#00e676' : rsi > 70 ? '#ff1744' : '#00e5ff';
    document.getElementById('sig-rsi').textContent = rsi < 30 ? 'تشبع بيعي' : rsi > 70 ? 'تشبع شرائي' : 'محايد';
    styleSignal('sig-rsi', rsi < 30 ? 'buy' : rsi > 70 ? 'sell' : 'neutral');

    const price = data.current;
    const sma20 = indicators.sma_20;
    const sma50 = indicators.sma_50;
    const sma200 = indicators.sma_200;

    document.getElementById('ind-sma20').textContent = formatPrice(sma20, data.currency);
    setSignal('sig-sma20', price > sma20 ? 'buy' : 'sell', price > sma20 ? 'فوق' : 'تحت');

    document.getElementById('ind-sma50').textContent = formatPrice(sma50, data.currency);
    setSignal('sig-sma50', price > sma50 ? 'buy' : 'sell', price > sma50 ? 'فوق' : 'تحت');

    document.getElementById('ind-sma200').textContent = formatPrice(sma200, data.currency);
    setSignal('sig-sma200', price > sma200 ? 'buy' : 'sell', price > sma200 ? 'فوق' : 'تحت');

    document.getElementById('ind-macd').textContent = macd.macd || '—';
    setSignal('sig-macd', macd.histogram > 0 ? 'buy' : 'sell', macd.histogram > 0 ? 'صاعد' : 'هابط');

    document.getElementById('ind-bb-upper').textContent = formatPrice(bb.upper, data.currency);
    document.getElementById('ind-bb-lower').textContent = formatPrice(bb.lower, data.currency);
    const bbSig = price >= bb.upper ? 'sell' : price <= bb.lower ? 'buy' : 'neutral';
    setSignal('sig-bb', bbSig, price >= bb.upper ? 'حد علوي' : price <= bb.lower ? 'حد سفلي' : 'وسط');

    document.getElementById('ind-atr').textContent = formatPrice(indicators.atr, data.currency);
    document.getElementById('ind-stoch-k').textContent = stoch.k || '—';
    setSignal('sig-stoch', stoch.k < 20 ? 'buy' : stoch.k > 80 ? 'sell' : 'neutral',
              stoch.k < 20 ? 'تشبع بيعي' : stoch.k > 80 ? 'تشبع شرائي' : 'محايد');

    // Fundamental
    document.getElementById('fund-cap').textContent = formatMarketCap(data.market_cap);
    const pe = data.pe_ratio;
    document.getElementById('fund-pe').textContent = pe ? pe.toFixed(1) : 'N/A';
    if (pe) {
        document.getElementById('fund-pe-note').textContent = pe < 15 ? 'منخفض جيد' : pe > 30 ? 'مرتفع تقييم عال' : 'معتدل';
    }
    document.getElementById('fund-sector').textContent = data.sector || 'غير محدد';
    document.getElementById('fund-industry').textContent = data.industry || 'غير محدد';
    document.getElementById('fund-support').textContent = formatPrice(analysis.support, data.currency);
    document.getElementById('fund-resistance').textContent = formatPrice(analysis.resistance, data.currency);

    const trendMap = {
        strong_bullish: 'صاعد قوي',
        bullish: 'صاعد',
        neutral: 'محايد',
        bearish: 'هابط',
        strong_bearish: 'هابط قوي'
    };
    document.getElementById('fund-trend').textContent = trendMap[analysis.trend] || '—';

    const volRatioText = avgVol > 0 ? `${volRatio.toFixed(1)}x` : '—';
    document.getElementById('fund-volume-ratio').textContent = volRatioText;

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

    // Impact Analysis
    displayImpactAnalysis(data);

    // Draw Charts
    drawCandlestickChart(data);
    drawVolumeChart(data);
    drawRsiChart(data);
    drawMacdChart(data);

    // Show result
    document.getElementById('result').classList.remove('hidden');
    document.getElementById('result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ======= AI Analysis =======
function generateAIAnalysis(data) {
    const container = document.getElementById('ai-analysis-content');
    const analysis = data.analysis || {};
    const indicators = analysis.indicators || {};
    const rec = data.recommendation || {};

    const trend = analysis.trend || 'neutral';
    const rsi = indicators.rsi || 50;

    let aiText = '';
    let confidence = 50;

    if (trend === 'strong_bullish') {
        aiText = 'السهم يظهر قوة شرائية ملحوظة مع وجوده فوق جميع المتوسطات المتحركة الرئيسية. المؤشرات الفنية تدعم استمرار الاتجاه الصعودي. ينصح بمراقبة مستويات الدعم للدخول في فرص شراء.';
        confidence = 85;
    } else if (trend === 'bullish') {
        aiText = 'الاتجاه العام للسهم صاعد مع وجود إشارات إيجابية من المؤشرات الفنية. MACD إيجابي و RSI في منطقة مريحة. فرصة جيدة للشراء مع وقف خسارة مناسب.';
        confidence = 70;
    } else if (trend === 'strong_bearish') {
        aiText = 'السهم في اتجاه هبوطي قوي مع ضغط بيعي واضح. جميع المؤشرات سلبية و السعر تحت المتوسطات المتحركة. ينصح بالانتظار أو البحث عن فرص بيعية.';
        confidence = 85;
    } else if (trend === 'bearish') {
        aiText = 'الاتجاه الهبوطي مستمر مع ضعف في الزخم الشرائي. المؤشرات تظهر إشارات سلبية. يفضل الانتظار حتى ظهور إشارات انعكاس واضحة.';
        confidence = 65;
    } else {
        if (rsi < 30) {
            aiText = 'السهم في منطقة تشبع بيعي (RSI < 30) مما يشير إلى احتمال ارتداد صعودي قريب. فرصة جيدة للمضاربة اللحظية مع مراقبة حجم التداول.';
            confidence = 60;
        } else if (rsi > 70) {
            aiText = 'السهم في منطقة تشبع شرائي (RSI > 70) مما يشير إلى احتمال تصحيح هبوطي. ينصح بحذر للمشترين الجدد.';
            confidence = 55;
        } else {
            aiText = 'السهم في منطقة محايدة بدون اتجاه واضح. المؤشرات متباينة ولا توجد إشارات قوية. ينصح بالانتظار حتى ظهور محفزات جديدة.';
            confidence = 40;
        }
    }

    const confidenceColor = confidence > 70 ? 'var(--positive)' : confidence > 50 ? 'var(--warning)' : 'var(--negative)';

    container.innerHTML = `
        <div class="ai-result">
            <h4>تحليل الذكاء الاصطناعي</h4>
            <p>${aiText}</p>
            <div class="ai-confidence">
                <span class="ai-confidence-label">نسبة الثقة:</span>
                <div class="ai-confidence-bar">
                    <div class="ai-confidence-fill" style="width: ${confidence}%; background: ${confidenceColor};"></div>
                </div>
                <span class="ai-confidence-val" style="color: ${confidenceColor};">${confidence}%</span>
            </div>
        </div>
    `;
}

// ======= Earnings Display =======
function displayEarnings(data) {
    const earningsDate = document.getElementById('earnings-date');
    const earningsQuarter = document.getElementById('earnings-quarter');
    const earningsEstimate = document.getElementById('earnings-estimate');

    const symbolHash = data.symbol.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    const daysAhead = (symbolHash % 45) + 15;
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + daysAhead);

    const monthNames = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                       'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];

    earningsDate.textContent = `${futureDate.getDate()} ${monthNames[futureDate.getMonth()]} ${futureDate.getFullYear()}`;

    const quarters = ['Q1 2026', 'Q2 2026', 'Q3 2026', 'Q4 2026'];
    earningsQuarter.textContent = quarters[symbolHash % 4];

    const estimates = ['أفضل من المتوقع', 'ضمن التوقعات', 'أقل من المتوقع', 'غير محدد'];
    earningsEstimate.textContent = estimates[symbolHash % 4];
}

// ======= Fibonacci Display =======
function displayFibonacci(data) {
    const prices = data.prices_arr || [];
    if (!prices.length) return;

    const closes = prices.map(p => p.close || p.Close || 0);
    const high52 = data.high_52w || Math.max(...closes);
    const low52 = data.low_52w || Math.min(...closes);
    const range = high52 - low52;

    const levels = {
        'fib-0': high52,
        'fib-236': high52 - range * 0.236,
        'fib-382': high52 - range * 0.382,
        'fib-500': high52 - range * 0.5,
        'fib-618': high52 - range * 0.618,
        'fib-786': high52 - range * 0.786,
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
    const sector = data.sector || 'غير محدد';
    const industry = data.industry || 'غير محدد';

    document.getElementById('impact-sector').textContent = sector;
    document.getElementById('impact-industry').textContent = industry;
    document.getElementById('impact-country').textContent = market === 'saudi' ? 'السعودية' : 'الولايات المتحدة';

    const hash = symbol.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    const employees = ((hash % 500) + 1) * 1000;
    document.getElementById('impact-employees').textContent = formatVolume(employees);

    const revenue = ((hash % 100) + 10) * 1e9;
    const profit = revenue * ((hash % 30) + 5) / 100;
    const margin = ((hash % 25) + 10);
    const roe = ((hash % 20) + 5);

    document.getElementById('impact-revenue').textContent = formatMarketCap(revenue);
    document.getElementById('impact-profit').textContent = formatMarketCap(profit);
    document.getElementById('impact-margin').textContent = `${margin}%`;
    document.getElementById('impact-roe').textContent = `${roe}%`;

    const factorsContainer = document.getElementById('impact-factors');
    const factors = generateImpactFactors(data, hash);
    factorsContainer.innerHTML = factors.map(f => `
        <div class="impact-factor ${f.type}">
            <span class="impact-factor-icon">${f.icon}</span>
            <span class="impact-factor-text">${f.text}</span>
        </div>
    `).join('');

    const outlookContainer = document.getElementById('impact-outlook');
    const outlook = generateOutlook(data, hash);
    outlookContainer.innerHTML = `<p>${outlook}</p>`;
}

function generateImpactFactors(data, hash) {
    const factors = [];
    const isSaudi = data.market === 'saudi';

    if (data.change > 5) {
        factors.push({
            icon: '📈',
            text: `ارتفاع قوي بنسبة ${data.change}% يعكس تفاؤل السوق وتوقعات إيجابية`,
            type: 'positive'
        });
    } else if (data.change < -5) {
        factors.push({
            icon: '📉',
            text: `انخفاض حاد بنسبة ${Math.abs(data.change)}% قد يعكس أخبار سلبية أو جني أرباح`,
            type: 'negative'
        });
    }

    const volRatio = (data.volume || 0) / (data.avg_volume || 1);
    if (volRatio > 2) {
        factors.push({
            icon: '🔥',
            text: `حجم تداول استثنائي (${volRatio.toFixed(1)}x المتوسط) يشير إلى اهتمام مؤسسي كبير`,
            type: 'positive'
        });
    }

    if (isSaudi) {
        factors.push({
            icon: '🏛️',
            text: 'تأثير إيجابي من رؤية 2030 والتحول الاقتصادي في المملكة',
            type: 'positive'
        });
    } else {
        factors.push({
            icon: '💵',
            text: 'تأثر بالسياسة النقدية الفيدرالية وتوقعات أسعار الفائدة',
            type: 'neutral'
        });
    }

    const trend = data.analysis?.trend || 'neutral';
    if (trend.includes('bullish')) {
        factors.push({
            icon: '🎯',
            text: 'الاتجاه الفني الصعودي يجذب المتداولين الفنيين ويخلق زخماً إيجابياً',
            type: 'positive'
        });
    } else if (trend.includes('bearish')) {
        factors.push({
            icon: '⚠️',
            text: 'الاتجاه الهبوطي قد يؤدي إلى مزيد من الضغط البيعي من المحافظ الاستثمارية',
            type: 'negative'
        });
    }

    return factors;
}

function generateOutlook(data, hash) {
    const rec = data.recommendation?.action || 'محايد';

    if (rec.includes('شراء')) {
        return 'التوقعات المستقبلية إيجابية بناءً على المؤشرات الفنية الحالية. السهم يظهر قوة شرائية مع وجود دعوم قوية. من المتوقع استمرار الاتجاه الصعودي في المدى القصير إلى المتوسط، خاصة مع دعم الأداء المالي للشركة.';
    } else if (rec.includes('بيع')) {
        return 'التوقعات المستقبلية سلبية بناءً على المؤشرات الفنية الحالية. السهم يواجه مقاومات قوية وضغط بيعي. من المتوقع استمرار الاتجاه الهبوطي أو التذبذب السلبي في المدى القصير.';
    } else {
        return 'السهم في منطقة محايدة حالياً. المؤشرات متباينة ولا توجد إشارات واضحة. من المتوقع استمرار التذبذب الجانبي حتى ظهور محفزات جديدة.';
    }
}

// ======= Custom Candlestick Chart =======
function drawCandlestickChart(data, highlightIndex = -1) {
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

    // Calculate Bollinger if enabled
    let bollingerUpper = [];
    let bollingerLower = [];
    if (indicatorVisibility.bollinger) {
        for (let i = 0; i < closes.length; i++) {
            if (i >= 19) {
                const slice = closes.slice(i - 19, i + 1);
                const mean = slice.reduce((a, b) => a + b, 0) / 20;
                const variance = slice.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / 20;
                const std = Math.sqrt(variance);
                bollingerUpper.push(mean + std * 2);
                bollingerLower.push(mean - std * 2);
            } else {
                bollingerUpper.push(null);
                bollingerLower.push(null);
            }
        }
    }

    // Calculate Fibonacci if enabled
    let fibLevels = [];
    if (indicatorVisibility.fibonacci) {
        const high52 = data.high_52w || Math.max(...closes);
        const low52 = data.low_52w || Math.min(...closes);
        const range = high52 - low52;
        fibLevels = [
            high52 - range * 0.236,
            high52 - range * 0.382,
            high52 - range * 0.5,
            high52 - range * 0.618,
            high52 - range * 0.786
        ];
    }

    // Find min/max for scaling
    let allValues = [];
    prices.forEach(p => {
        allValues.push(p.high || p.High || 0);
        allValues.push(p.low || p.Low || 0);
    });

    if (indicatorVisibility.sma20) sma20.forEach(v => { if (v) allValues.push(v); });
    if (indicatorVisibility.sma50) sma50.forEach(v => { if (v) allValues.push(v); });
    if (indicatorVisibility.sma200) sma200.forEach(v => { if (v) allValues.push(v); });
    if (indicatorVisibility.sma7) sma7.forEach(v => { if (v) allValues.push(v); });
    if (indicatorVisibility.bollinger) {
        bollingerUpper.forEach(v => { if (v) allValues.push(v); });
        bollingerLower.forEach(v => { if (v) allValues.push(v); });
    }
    if (indicatorVisibility.fibonacci) fibLevels.forEach(v => allValues.push(v));

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

        const price = maxPrice - (priceRange / 5) * i;
        ctx.fillStyle = c.text;
        ctx.font = '10px Cairo';
        ctx.textAlign = 'left';
        ctx.fillText(price.toFixed(2), width - padding.right + 5, y + 3);
    }

    // Draw date labels
    const dateStep = Math.max(1, Math.floor(dates.length / 8));
    for (let i = 0; i < dates.length; i += dateStep) {
        const x = padding.left + (i / (prices.length - 1)) * chartWidth;
        ctx.fillStyle = c.text;
        ctx.font = '9px Cairo';
        ctx.textAlign = 'center';
        const dateStr = dates[i] ? dates[i].slice(5) : '';
        ctx.fillText(dateStr, x, height - 10);
    }

    const candleWidth = Math.max(1, (chartWidth / prices.length) * 0.7);
    const candleSpacing = chartWidth / prices.length;

    // Draw Fibonacci horizontal lines
    if (indicatorVisibility.fibonacci) {
        const fibColors = ['rgba(255,215,0,0.3)', 'rgba(255,215,0,0.25)', 'rgba(255,215,0,0.2)', 'rgba(255,215,0,0.25)', 'rgba(255,215,0,0.3)'];
        const fibLabels = ['23.6%', '38.2%', '50%', '61.8%', '78.6%'];

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

    // Draw Bollinger bands
    if (indicatorVisibility.bollinger) {
        ctx.strokeStyle = 'rgba(124,77,255,0.3)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);

        ctx.beginPath();
        let started = false;
        bollingerUpper.forEach((v, i) => {
            if (v === null) return;
            const x = padding.left + i * candleSpacing + candleSpacing / 2;
            const y = padding.top + ((maxPrice - v) / priceRange) * chartHeight;
            if (!started) { ctx.moveTo(x, y); started = true; }
            else { ctx.lineTo(x, y); }
        });
        ctx.stroke();

        ctx.beginPath();
        started = false;
        bollingerLower.forEach((v, i) => {
            if (v === null) return;
            const x = padding.left + i * candleSpacing + candleSpacing / 2;
            const y = padding.top + ((maxPrice - v) / priceRange) * chartHeight;
            if (!started) { ctx.moveTo(x, y); started = true; }
            else { ctx.lineTo(x, y); }
        });
        ctx.stroke();
        ctx.setLineDash([]);
    }

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

    if (indicatorVisibility.sma7) drawSMALine(sma7, c.warning, 1.5, [2, 2]);
    if (indicatorVisibility.sma20) drawSMALine(sma20, c.purple, 1.5, [4, 2]);
    if (indicatorVisibility.sma50) drawSMALine(sma50, c.negative, 1.5, [6, 3]);
    if (indicatorVisibility.sma200) drawSMALine(sma200, c.positive, 2, []);

    // Draw targets/supports
    const targets = (data.analysis && data.analysis.targets) || {};
    if (indicatorVisibility.targets && targets.target_1) {
        ctx.strokeStyle = 'rgba(0,230,118,0.4)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        const y = padding.top + ((maxPrice - targets.target_1) / priceRange) * chartHeight;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = c.positive;
        ctx.font = '9px Cairo';
        ctx.textAlign = 'right';
        ctx.fillText('هدف 1', width - padding.right - 5, y - 3);
    }

    if (indicatorVisibility.targets && targets.stop_loss) {
        ctx.strokeStyle = 'rgba(255,23,68,0.4)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        const y = padding.top + ((maxPrice - targets.stop_loss) / priceRange) * chartHeight;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = c.negative;
        ctx.font = '9px Cairo';
        ctx.textAlign = 'right';
        ctx.fillText('وقف الخسارة', width - padding.right - 5, y - 3);
    }

    // Draw crosshair vertical line
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

// ======= RSI Chart =======
function drawRsiChart(data) {
    if (!secondaryChartVisibility.rsi) return;

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

// ======= MACD Chart =======
function drawMacdChart(data) {
    if (!secondaryChartVisibility.macd) return;

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

// ======= Toggle Indicators =======
function toggleIndicator(indicator) {
    indicatorVisibility[indicator] = !indicatorVisibility[indicator];
    if (currentData) drawCandlestickChart(currentData);
}

function toggleSecondaryChart(chart) {
    secondaryChartVisibility[chart] = !secondaryChartVisibility[chart];
    const canvas = document.getElementById(chart + 'Chart');
    if (canvas) {
        canvas.style.display = secondaryChartVisibility[chart] ? 'block' : 'none';
    }
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
    btn.classList.add('active');
    if (!currentSymbol) return;

    fetch(`./api/chart-data/${currentSymbol}?period=${period}`)
        .then(r => r.json())
        .then(d => {
            if (d && !d.error) {
                currentData = { ...currentData, ...d };
                drawCandlestickChart(currentData);
                drawVolumeChart(currentData);
                if (secondaryChartVisibility.rsi) drawRsiChart(currentData);
                if (secondaryChartVisibility.macd) drawMacdChart(currentData);
            }
        })
        .catch(err => console.error('Chart data error:', err));
}

// ======= Market Overview (REMOVED) =======
async function loadMarketOverview() {
    // Market overview section removed per user request
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
    showToast(`تمت إضافة ${currentSymbol} للمفضلة`);
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
