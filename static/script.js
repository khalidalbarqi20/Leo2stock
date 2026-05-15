// ===== CRITICAL FIXES =====

document.addEventListener('DOMContentLoaded', function() {
    console.log('Leo2Stock initializing...');
    const criticalElements = ['menu-toggle', 'sidebar', 'main-chart', 'fear-greed-panel', 'theme-toggle'];
    criticalElements.forEach(id => {
        const el = document.getElementById(id);
        if (!el) console.warn(`Missing element: #${id}`);
    });
    if (typeof initApp === 'function') {
        initApp();
    } else {
        console.error('initApp function not found!');
    }
});

function $(id) { return document.getElementById(id); }
function on(el, event, handler) {
    if (typeof el === 'string') el = $(el);
    if (el) el.addEventListener(event, handler);
}

function setVH() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}
window.addEventListener('resize', setVH);
setVH();

// ====== المتغيرات العامة ======
let currentSymbol = 'MOBX';
let currentTimeframe = '1h';
let chartInstance = null;
let fearGreedInterval = null;
let autoUpdateInterval = null;

// ====== تهيئة التطبيق ======
function initApp() {
    initSidebar();
    initChart();
    initFearGreedIndex();
    initNewsFilters();
    initActionButtons();
    initRiskCalculator();
    initAlertSystem();
    initBacktesting();
    initModals();
    initThemeToggle();
    initRsiScan();
    initPdfButton();
    startAutoUpdate();
}

// ====== القائمة الجانبية ======
function initSidebar() {
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => sidebar.classList.toggle('active'));
    }
    document.addEventListener('click', (e) => {
        if (sidebar && menuToggle && !sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
            sidebar.classList.remove('active');
        }
    });
}

// ====== الوضع الليلي/النهاري ======
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const savedTheme = localStorage.getItem('theme') || 'dark';
    body.setAttribute('data-theme', savedTheme);
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = body.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            const icon = themeToggle.querySelector('i');
            if (icon) icon.className = newTheme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
        });
    }
}

// ====== الرسم البياني ======
function initChart() {
    const canvas = document.getElementById('main-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    function resizeCanvas() {
        const container = canvas.parentElement;
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight || 400;
        drawChart(ctx, canvas.width, canvas.height);
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const tfButtons = document.querySelectorAll('.tf-btn');
    tfButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tfButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTimeframe = btn.dataset.tf;
            drawChart(ctx, canvas.width, canvas.height);
        });
    });

    const indicatorCheckboxes = document.querySelectorAll('.indicator-toggle input');
    indicatorCheckboxes.forEach(cb => {
        cb.addEventListener('change', () => drawChart(ctx, canvas.width, canvas.height));
    });
}

function drawChart(ctx, width, height) {
    const data = generateMockChartData();
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--card-bg') || '#1a1a2e';
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
        const y = (height / 4) * i;
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    }
    const candleWidth = width / data.length * 0.6;
    const padding = width / data.length * 0.2;
    const minPrice = Math.min(...data.map(d => d.low));
    const maxPrice = Math.max(...data.map(d => d.high));
    const priceRange = maxPrice - minPrice || 1;

    data.forEach((candle, i) => {
        const x = (width / data.length) * i + padding;
        const openY = height - ((candle.open - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        const closeY = height - ((candle.close - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        const highY = height - ((candle.high - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        const lowY = height - ((candle.low - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        const isGreen = candle.close > candle.open;
        ctx.fillStyle = isGreen ? '#00ff88' : '#ff4444';
        ctx.strokeStyle = isGreen ? '#00ff88' : '#ff4444';
        ctx.beginPath(); ctx.moveTo(x + candleWidth / 2, highY); ctx.lineTo(x + candleWidth / 2, lowY); ctx.stroke();
        const bodyTop = Math.min(openY, closeY);
        const bodyHeight = Math.abs(closeY - openY) || 2;
        ctx.fillRect(x, bodyTop, candleWidth, bodyHeight);
    });
    drawMovingAverages(ctx, data, width, height, minPrice, priceRange);
}

function drawMovingAverages(ctx, data, width, height, minPrice, priceRange) {
    const closes = data.map(d => d.close);
    const sma20 = calculateSMA(closes, 20);
    ctx.strokeStyle = '#00d4ff'; ctx.lineWidth = 2; ctx.beginPath();
    sma20.forEach((value, i) => {
        if (value === null) return;
        const x = (width / data.length) * i + (width / data.length) / 2;
        const y = height - ((value - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        (i === 0 || sma20[i-1] === null) ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    const sma50 = calculateSMA(closes, 50);
    ctx.strokeStyle = '#ffd700'; ctx.beginPath();
    sma50.forEach((value, i) => {
        if (value === null) return;
        const x = (width / data.length) * i + (width / data.length) / 2;
        const y = height - ((value - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        (i === 0 || sma50[i-1] === null) ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
}

function calculateSMA(data, period) {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) { result.push(null); continue; }
        let sum = 0;
        for (let j = 0; j < period; j++) sum += data[i - j];
        result.push(sum / period);
    }
    return result;
}

function generateMockChartData() {
    const data = [];
    let price = 3.0;
    for (let i = 0; i < 100; i++) {
        const change = (Math.random() - 0.5) * 0.2;
        const open = price;
        const close = price + change;
        const high = Math.max(open, close) + Math.random() * 0.1;
        const low = Math.min(open, close) - Math.random() * 0.1;
        data.push({ open, high, low, close, volume: Math.random() * 1000000 });
        price = close;
    }
    return data;
}

function drawChartFromAPI(ctx, width, height, pricesArr) {
    if (!pricesArr || pricesArr.length === 0) { drawChart(ctx, width, height); return; }
    const data = pricesArr.slice(-100).map(p => ({ open: p.open, high: p.high, low: p.low, close: p.close, volume: p.volume }));
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--card-bg') || '#1a1a2e';
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
        const y = (height / 4) * i;
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    }
    const minPrice = Math.min(...data.map(d => d.low));
    const maxPrice = Math.max(...data.map(d => d.high));
    const priceRange = maxPrice - minPrice || 1;
    const candleWidth = width / data.length * 0.6;
    const padding = width / data.length * 0.2;

    data.forEach((candle, i) => {
        const x = (width / data.length) * i + padding;
        const openY = height - ((candle.open - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        const closeY = height - ((candle.close - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        const highY = height - ((candle.high - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        const lowY = height - ((candle.low - minPrice) / priceRange) * height * 0.8 - height * 0.1;
        const isGreen = candle.close >= candle.open;
        ctx.fillStyle = isGreen ? '#00ff88' : '#ff4444';
        ctx.strokeStyle = isGreen ? '#00ff88' : '#ff4444';
        ctx.beginPath(); ctx.moveTo(x + candleWidth / 2, highY); ctx.lineTo(x + candleWidth / 2, lowY); ctx.stroke();
        const bodyTop = Math.min(openY, closeY);
        const bodyHeight = Math.abs(closeY - openY) || 2;
        ctx.fillRect(x, bodyTop, candleWidth, bodyHeight);
    });
    drawMovingAverages(ctx, data, width, height, minPrice, priceRange);
}

// ====== مؤشر الخوف والجشع ======
function initFearGreedIndex() {
    updateFearGreedIndex();
    if (fearGreedInterval) clearInterval(fearGreedInterval);
    fearGreedInterval = setInterval(updateFearGreedIndex, 30000);
}

function updateFearGreedIndex() {
    const stockData = fetchStockData(currentSymbol);
    const index = calculateFearGreedIndex(stockData);
    displayFearGreedIndex(index);
    const prediction = predictMovement(index);
    displayPrediction(prediction);
}

function fetchStockData(symbol) {
    return {
        priceChange: (Math.random() * 10) - 5,
        volumeRatio: 0.5 + Math.random() * 2,
        rsi: 20 + Math.random() * 60,
        volatility: 15 + Math.random() * 25,
        marketTrend: Math.random() > 0.5 ? 'bullish' : 'bearish',
        newsSentiment: Math.random(),
        technicalScore: Math.random() * 100
    };
}

function calculateFearGreedIndex(data) {
    const { priceChange, volumeRatio, rsi, volatility, marketTrend, newsSentiment } = data;
    let score = 50;
    if (priceChange > 5) score += 15;
    else if (priceChange > 2) score += 10;
    else if (priceChange > 0) score += 5;
    else if (priceChange > -2) score -= 5;
    else if (priceChange > -5) score -= 10;
    else score -= 15;
    if (volumeRatio > 2) score += 10;
    else if (volumeRatio > 1.5) score += 5;
    else if (volumeRatio < 0.5) score -= 10;
    else if (volumeRatio < 0.8) score -= 5;
    if (rsi > 80) score += 10;
    else if (rsi > 70) score += 5;
    else if (rsi < 20) score -= 10;
    else if (rsi < 30) score -= 5;
    if (volatility > 30) score -= 10;
    else if (volatility > 25) score -= 5;
    else if (volatility < 15) score += 5;
    if (marketTrend === 'bullish') score += 5;
    else if (marketTrend === 'bearish') score -= 5;
    if (newsSentiment > 0.7) score += 5;
    else if (newsSentiment < 0.3) score -= 5;
    return Math.max(0, Math.min(100, score));
}

function displayFearGreedIndex(index) {
    const indexElement = document.getElementById('fear-greed-index');
    const statusElement = document.getElementById('fear-greed-status');
    const gaugeElement = document.getElementById('fear-greed-gauge');
    if (indexElement) indexElement.textContent = index.toFixed(1);
    const status = getFearGreedStatus(index);
    if (statusElement) { statusElement.textContent = status.text; statusElement.className = `status-badge ${status.class}`; }
    if (gaugeElement) { gaugeElement.style.width = `${index}%`; gaugeElement.style.background = status.gradient; }
}

function getFearGreedStatus(index) {
    if (index >= 75) return { text: 'جشع مفرط', class: 'extreme-greed', gradient: 'linear-gradient(90deg, #00ff88, #00cc6a)', color: '#00ff88' };
    if (index >= 55) return { text: 'جشع', class: 'greed', gradient: 'linear-gradient(90deg, #00cc6a, #66ff99)', color: '#00cc6a' };
    if (index >= 45) return { text: 'محايد', class: 'neutral', gradient: 'linear-gradient(90deg, #ffd700, #ffcc00)', color: '#ffd700' };
    if (index >= 25) return { text: 'خوف', class: 'fear', gradient: 'linear-gradient(90deg, #ff6b6b, #ff4444)', color: '#ff6b6b' };
    return { text: 'خوف مفرط', class: 'extreme-fear', gradient: 'linear-gradient(90deg, #ff4444, #ff0000)', color: '#ff4444' };
}

function predictMovement(index) {
    let prediction = '', probability = 0, signal = '';
    if (index >= 75) { prediction = 'تصحيح هبوطي محتمل - الجشع المفرط يشير إلى قمة محتملة. يُنصح بأخذ الأرباح أو الانتظار.'; probability = 65; signal = 'انتظار/بيع'; }
    else if (index >= 55) { prediction = 'استمرار الصعود محتمل مع احتمالية تصحيح خفيف. فرصة شراء محدودة.'; probability = 55; signal = 'شراء حذر'; }
    else if (index >= 45) { prediction = 'اتجاه غير واضح - انتظار تأكيد الاتجاه. لا يُنصح بالدخول الآن.'; probability = 50; signal = 'انتظار'; }
    else if (index >= 25) { prediction = 'ارتداد صاعد محتمل - الخوف يشير إلى قاع محتمل. فرصة شراء جيدة.'; probability = 60; signal = 'شراء'; }
    else { prediction = 'ارتداد صاعد قوي محتمل - الخوف المفرط يشير إلى فرصة شراء ممتازة.'; probability = 70; signal = 'شراء قوي'; }
    return { prediction, probability, signal };
}

function displayPrediction(prediction) {
    const predictionElement = document.getElementById('movement-prediction');
    const probabilityElement = document.getElementById('prediction-probability');
    if (predictionElement) predictionElement.textContent = prediction.prediction;
    if (probabilityElement) {
        probabilityElement.textContent = `احتمالية: ${prediction.probability}% | الإشارة: ${prediction.signal}`;
        probabilityElement.style.color = prediction.probability >= 60 ? '#00ff88' : prediction.probability >= 50 ? '#ffd700' : '#ff6b6b';
    }
}

// ====== فلترة الأخبار ======
function initNewsFilters() {
    const filters = document.querySelectorAll('.news-filter');
    const newsCards = document.querySelectorAll('.news-card');
    filters.forEach(filter => {
        filter.addEventListener('click', () => {
            filters.forEach(f => f.classList.remove('active'));
            filter.classList.add('active');
            newsCards.forEach(card => card.style.display = 'block');
        });
    });
    const refreshBtn = document.getElementById('refresh-news');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshBtn.querySelector('i').classList.add('fa-spin');
            setTimeout(() => {
                refreshBtn.querySelector('i').classList.remove('fa-spin');
                showNotification('تم تحديث الأخبار بنجاح');
            }, 1000);
        });
    }
}

// ====== أزرار الإجراءات ======
function initActionButtons() {
    const riskBtn = document.getElementById('btn-risk');
    if (riskBtn) riskBtn.addEventListener('click', () => scrollToSection('risk-manager'));
    const backtestBtn = document.getElementById('btn-backtest');
    if (backtestBtn) backtestBtn.addEventListener('click', () => scrollToSection('backtesting'));
    const pdfBtn = document.getElementById('btn-pdf');
    if (pdfBtn) pdfBtn.addEventListener('click', () => scrollToSection('pdf-report'));
    const alertBtn = document.getElementById('btn-alert');
    if (alertBtn) alertBtn.addEventListener('click', () => openModal('price-alert-modal'));
    const favBtn = document.getElementById('btn-fav');
    if (favBtn) favBtn.addEventListener('click', () => addToFavorites(currentSymbol));
}

function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) section.scrollIntoView({ behavior: 'smooth' });
}

// ====== حاسبة المخاطر ======
function initRiskCalculator() {
    const calculateBtn = document.getElementById('calculate-position');
    if (calculateBtn) calculateBtn.addEventListener('click', calculatePosition);
}

function calculatePosition() {
    const capital = parseFloat(document.getElementById('risk-capital').value) || 0;
    const riskPercent = parseFloat(document.getElementById('risk-percent').value) || 0;
    const entry = parseFloat(document.getElementById('risk-entry').value) || 0;
    const stop = parseFloat(document.getElementById('risk-stop').value) || 0;
    const target = parseFloat(document.getElementById('risk-target').value) || 0;
    if (!capital || !riskPercent || !entry || !stop) { showNotification('يرجى ملء جميع الحقول المطلوبة', 'error'); return; }
    const riskAmount = capital * (riskPercent / 100);
    const riskPerShare = Math.abs(entry - stop);
    const positionSize = Math.floor(riskAmount / riskPerShare);
    const reward = target ? Math.abs(target - entry) * positionSize : 0;
    const rr = target ? (Math.abs(target - entry) / riskPerShare).toFixed(2) : '--';
    const resultBox = document.getElementById('position-result');
    if (resultBox) {
        resultBox.classList.remove('hidden');
        document.getElementById('pos-size').textContent = positionSize.toLocaleString();
        document.getElementById('pos-risk').textContent = '$' + riskAmount.toFixed(2);
        document.getElementById('pos-reward').textContent = target ? '$' + reward.toFixed(2) : '--';
        document.getElementById('pos-rr').textContent = '1:' + rr;
    }
}

// ====== نظام التنبيهات ======
function initAlertSystem() {
    const addAlertBtn = document.getElementById('add-alert');
    const alertForm = document.getElementById('alert-form');
    const createAlertBtn = document.getElementById('create-alert');
    const cancelAlertBtn = document.getElementById('cancel-alert');
    if (addAlertBtn && alertForm) addAlertBtn.addEventListener('click', () => alertForm.classList.toggle('hidden'));
    if (cancelAlertBtn && alertForm) cancelAlertBtn.addEventListener('click', () => alertForm.classList.add('hidden'));
    if (createAlertBtn) createAlertBtn.addEventListener('click', createAlert);
}

function createAlert() {
    const symbol = document.getElementById('alert-symbol').value;
    const type = document.getElementById('alert-type').value;
    const condition = document.getElementById('alert-condition').value;
    const value = document.getElementById('alert-value').value;
    if (!symbol || !value) { showNotification('يرجى ملء جميع الحقول', 'error'); return; }
    const alertItem = document.createElement('div');
    alertItem.className = 'alert-item active';
    alertItem.innerHTML = `
        <div class="alert-info">
            <span class="alert-symbol">${symbol}</span>
            <span class="alert-condition">${type} ${condition} $${value}</span>
        </div>
        <div class="alert-status"><span class="status-badge active">نشط</span></div>
        <div class="alert-actions">
            <button class="btn-icon small" title="حذف" onclick="removeAlert(this)"><i class="fas fa-trash"></i></button>
        </div>`;
    const alertsGrid = document.getElementById('active-alerts');
    if (alertsGrid) alertsGrid.appendChild(alertItem);
    document.getElementById('alert-form').classList.add('hidden');
    showNotification('تم إنشاء التنبيه بنجاح');
}

function removeAlert(btn) {
    const alertItem = btn.closest('.alert-item');
    if (alertItem) { alertItem.remove(); showNotification('تم حذف التنبيه'); }
}

// ====== الاختبار التاريخي ======
function initBacktesting() {
    const runBtn = document.getElementById('run-backtest');
    if (runBtn) runBtn.addEventListener('click', runBacktest);
    const strategySelect = document.getElementById('backtest-strategy');
    if (strategySelect) strategySelect.addEventListener('change', updateStrategyParams);
}

function updateStrategyParams() {
    const strategy = document.getElementById('backtest-strategy').value;
    const paramsDiv = document.getElementById('strategy-params');
    let paramsHTML = '';
    if (strategy === 'sma') paramsHTML = `<div class="input-group"><label>فترة SMA السريع</label><input type="number" value="20" id="sma-fast"></div><div class="input-group"><label>فترة SMA البطيء</label><input type="number" value="50" id="sma-slow"></div>`;
    else if (strategy === 'rsi') paramsHTML = `<div class="input-group"><label>فترة RSI</label><input type="number" value="14" id="rsi-period"></div><div class="input-group"><label>مستوى الشراء</label><input type="number" value="30" id="rsi-oversold"></div><div class="input-group"><label>مستوى البيع</label><input type="number" value="70" id="rsi-overbought"></div>`;
    else if (strategy === 'macd') paramsHTML = `<div class="input-group"><label>فترة MACD السريع</label><input type="number" value="12" id="macd-fast"></div><div class="input-group"><label>فترة MACD البطيء</label><input type="number" value="26" id="macd-slow"></div><div class="input-group"><label>فترة الإشارة</label><input type="number" value="9" id="macd-signal"></div>`;
    else if (strategy === 'bollinger') paramsHTML = `<div class="input-group"><label>فترة المتوسط</label><input type="number" value="20" id="bb-period"></div><div class="input-group"><label>عدد الانحرافات</label><input type="number" value="2" step="0.1" id="bb-std"></div>`;
    if (paramsDiv) paramsDiv.innerHTML = paramsHTML;
}

function runBacktest() {
    const symbol = document.getElementById('backtest-symbol').value || currentSymbol || 'AAPL';
    const strategy = document.getElementById('backtest-strategy').value;
    showNotification('جاري تشغيل الاختبار التاريخي...');
    const runBtn = document.getElementById('run-backtest');
    if (runBtn) runBtn.disabled = true;

    fetch(`/api/backtest/${symbol}?strategy=${strategy}&capital=10000&stop_loss=0.05&take_profit=0.10`)
        .then(r => r.json())
        .then(data => {
            if (data.error) { showNotification(data.error, 'error'); return; }
            displayBacktestResults({
                totalReturn: data.total_return_pct || 0,
                winRate: data.win_rate || 0,
                maxDrawdown: data.max_drawdown_pct || 0,
                sharpeRatio: data.sharpe_ratio || 0,
                totalTrades: data.total_trades || 0,
                avgProfit: data.avg_trade_return || 0
            });
            showNotification('تم الانتهاء من الاختبار التاريخي');
        })
        .catch(() => {
            displayBacktestResults(generateBacktestResults());
            showNotification('تم الانتهاء من الاختبار (بيانات تجريبية)');
        })
        .finally(() => { if (runBtn) runBtn.disabled = false; });
}

function generateBacktestResults() {
    return {
        totalReturn: (Math.random() * 40 - 10).toFixed(2),
        winRate: (Math.random() * 30 + 40).toFixed(1),
        maxDrawdown: (Math.random() * 20).toFixed(2),
        sharpeRatio: (Math.random() * 2).toFixed(2),
        totalTrades: Math.floor(Math.random() * 100 + 50),
        avgProfit: (Math.random() * 5).toFixed(2)
    };
}

function displayBacktestResults(results) {
    const resultsDiv = document.getElementById('backtest-results');
    if (resultsDiv) resultsDiv.classList.remove('hidden');
    const btReturn = document.getElementById('bt-return');
    if (btReturn) { btReturn.textContent = results.totalReturn + '%'; btReturn.className = 'metric-value ' + (results.totalReturn > 0 ? 'positive' : 'negative'); }
    if (document.getElementById('bt-winrate')) document.getElementById('bt-winrate').textContent = results.winRate + '%';
    if (document.getElementById('bt-drawdown')) document.getElementById('bt-drawdown').textContent = results.maxDrawdown + '%';
    if (document.getElementById('bt-sharpe')) document.getElementById('bt-sharpe').textContent = results.sharpeRatio;
    if (document.getElementById('bt-trades')) document.getElementById('bt-trades').textContent = results.totalTrades;
    if (document.getElementById('bt-avg-profit')) document.getElementById('bt-avg-profit').textContent = '$' + results.avgProfit;
}

// ====== النوافذ المنبثقة ======
function initModals() {
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) modal.classList.remove('active');
        });
    });
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('active'); });
    });
    const setAlertBtn = document.getElementById('set-price-alert');
    if (setAlertBtn) {
        setAlertBtn.addEventListener('click', () => {
            const targetPrice = document.getElementById('target-price').value;
            const direction = document.getElementById('alert-direction').value;
            if (targetPrice) { showNotification(`تم تعيين تنبيه: ${direction === 'above' ? 'أعلى' : 'أقل'} من $${targetPrice}`); closeModal('price-alert-modal'); }
        });
    }
}

function openModal(modalId) { const modal = document.getElementById(modalId); if (modal) modal.classList.add('active'); }
function closeModal(modalId) { const modal = document.getElementById(modalId); if (modal) modal.classList.remove('active'); }

// ====== المفضلة ======
function addToFavorites(symbol) {
    let favorites = JSON.parse(localStorage.getItem('favorites') || '[]');
    if (favorites.includes(symbol)) { showNotification(`${symbol} موجود بالفعل في المفضلة`); return; }
    favorites.push(symbol);
    localStorage.setItem('favorites', JSON.stringify(favorites));
    updateFavoritesList();
    showNotification(`تم إضافة ${symbol} إلى المفضلة`);
}

function removeFromFavorites(symbol) {
    let favorites = JSON.parse(localStorage.getItem('favorites') || '[]');
    favorites = favorites.filter(s => s !== symbol);
    localStorage.setItem('favorites', JSON.stringify(favorites));
    updateFavoritesList();
    showNotification(`تم إزالة ${symbol} من المفضلة`);
}

function updateFavoritesList() {
    const container = document.getElementById('favorites-list');
    if (!container) return;
    const favorites = JSON.parse(localStorage.getItem('favorites') || '[]');
    if (favorites.length === 0) { container.innerHTML = '<p class="empty-message">لا توجد أسهم في المفضلة</p>'; return; }
    container.innerHTML = favorites.map(symbol => `
        <div class="favorite-item">
            <div class="fav-symbol">${symbol}</div>
            <div class="fav-price">$${(Math.random() * 200 + 50).toFixed(2)}</div>
            <div class="fav-change ${Math.random() > 0.5 ? 'positive' : 'negative'}">${(Math.random() * 5).toFixed(2)}%</div>
            <button class="btn-icon small remove-fav" title="إزالة" onclick="removeFromFavorites('${symbol}')"><i class="fas fa-times"></i></button>
        </div>`).join('');
}

// ====== التحديث التلقائي ======
function startAutoUpdate() {
    if (autoUpdateInterval) clearInterval(autoUpdateInterval);
    autoUpdateInterval = setInterval(() => { updateStockPrice(); updateFearGreedIndex(); }, 60000);
}

function updateStockPrice() {
    const priceElement = document.querySelector('.current-price');
    if (priceElement) {
        const currentPrice = parseFloat(priceElement.textContent.replace('$', '').replace('ر.س', ''));
        const change = (Math.random() - 0.5) * 0.1;
        const newPrice = (currentPrice + change).toFixed(2);
        priceElement.textContent = '$' + newPrice;
        const changeElement = document.querySelector('.price-change');
        if (changeElement) {
            const changePercent = (change / currentPrice * 100).toFixed(2);
            changeElement.textContent = (change >= 0 ? '+' : '') + '$' + change.toFixed(2) + ' (' + changePercent + '%)';
            changeElement.className = 'price-change ' + (change >= 0 ? 'positive' : 'negative');
        }
    }
}

// ====== نظام الإشعارات ======
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i><span>${message}</span>`;
    notification.style.cssText = `position:fixed;top:20px;left:50%;transform:translateX(-50%);background:${type === 'success' ? 'linear-gradient(135deg,#00ff88,#00cc6a)' : 'linear-gradient(135deg,#ff4444,#ff0000)'};color:#fff;padding:15px 25px;border-radius:12px;font-size:14px;z-index:10000;display:flex;align-items:center;gap:10px;box-shadow:0 4px 15px rgba(0,0,0,0.3);animation:slideDown 0.3s ease;`;
    document.body.appendChild(notification);
    setTimeout(() => { notification.style.animation = 'slideUp 0.3s ease'; setTimeout(() => notification.remove(), 300); }, 3000);
}

// ====== مسح RSI ======
function initRsiScan() {
    const scanRsiBtn = document.getElementById('scan-rsi');
    if (scanRsiBtn) {
        scanRsiBtn.addEventListener('click', () => {
            const maxRsi = document.getElementById('rsi-max').value;
            const market = document.getElementById('market-select').value;
            showNotification(`جاري مسح الأسهم بقيمة RSI أقل من ${maxRsi}...`);
            fetch(`/api/rsi-scan?market=${market === 'american' ? 'us' : market}&rsi_max=${maxRsi}`)
                .then(r => r.json())
                .then(data => {
                    const resultsDiv = document.getElementById('rsi-results');
                    if (resultsDiv) {
                        if (Array.isArray(data) && data.length > 0) {
                            resultsDiv.innerHTML = data.map(stock => `
                                <div class="rsi-result-item">
                                    <div class="result-symbol">${stock.symbol || ''}</div>
                                    <div class="result-name">${stock.name || ''}</div>
                                    <div class="result-rsi">RSI: ${(stock.rsi || 0).toFixed(1)}</div>
                                    <div class="result-price">${stock.currency === 'SAR' ? 'ر.س' : '$'}${(stock.price || 0).toFixed(2)}</div>
                                    <button class="btn-primary small" onclick="selectStock('${stock.symbol}')">اختيار</button>
                                </div>`).join('');
                        } else {
                            resultsDiv.innerHTML = '<p class="empty-message">لا توجد أسهم بهذا المعيار حالياً</p>';
                        }
                    }
                    showNotification('تم الانتهاء من المسح');
                })
                .catch(() => {
                    const resultsDiv = document.getElementById('rsi-results');
                    if (resultsDiv) resultsDiv.innerHTML = generateRSIResults();
                    showNotification('تم الانتهاء من المسح');
                });
        });
    }
}

function generateRSIResults() {
    const stocks = [
        { symbol: 'AAPL', name: 'Apple Inc.', rsi: 28.5, price: 150.25 },
        { symbol: 'GOOGL', name: 'Alphabet Inc.', rsi: 32.1, price: 2800.50 },
        { symbol: 'TSLA', name: 'Tesla Inc.', rsi: 25.8, price: 750.00 },
        { symbol: 'MSFT', name: 'Microsoft', rsi: 35.2, price: 300.00 },
        { symbol: 'AMZN', name: 'Amazon', rsi: 29.7, price: 3200.00 }
    ];
    return stocks.map(stock => `
        <div class="rsi-result-item">
            <div class="result-symbol">${stock.symbol}</div>
            <div class="result-name">${stock.name}</div>
            <div class="result-rsi">RSI: ${stock.rsi}</div>
            <div class="result-price">$${stock.price}</div>
            <button class="btn-primary small" onclick="selectStock('${stock.symbol}')">اختيار</button>
        </div>`).join('');
}

function selectStock(symbol) {
    currentSymbol = symbol;
    showNotification(`جاري تحميل بيانات: ${symbol}...`);
    const stockSymbolEl = document.querySelector('.stock-symbol h1');
    if (stockSymbolEl) stockSymbolEl.textContent = symbol;
    fetch(`/api/analyze/${symbol}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) { showNotification(data.error, 'error'); return; }
            updateStockDisplay(data);
            showNotification(`تم تحميل بيانات: ${symbol}`);
        })
        .catch(() => {
            showNotification('خطأ في الاتصال بالخادم', 'error');
            const canvas = document.getElementById('main-chart');
            if (canvas) drawChart(canvas.getContext('2d'), canvas.width, canvas.height);
        });
    updateFearGreedIndex();
}

function updateStockDisplay(data) {
    const priceEl = document.querySelector('.current-price');
    if (priceEl) priceEl.textContent = `${data.currency === 'SAR' ? 'ر.س' : '$'}${(data.current || 0).toFixed(2)}`;
    const changeEl = document.querySelector('.price-change');
    if (changeEl) {
        const change = data.change || 0;
        changeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
        changeEl.className = 'price-change ' + (change >= 0 ? 'positive' : 'negative');
    }
    const canvas = document.getElementById('main-chart');
    if (canvas && data.prices_arr && data.prices_arr.length > 0) {
        drawChartFromAPI(canvas.getContext('2d'), canvas.width, canvas.height, data.prices_arr);
    }
    const tickerItems = document.querySelectorAll('.ticker-value');
    if (tickerItems.length > 0 && data.high_52w) {
        const cur = data.currency === 'SAR' ? 'ر.س ' : '$';
        if (tickerItems[0]) tickerItems[0].textContent = cur + (data.high_52w || 0).toFixed(2);
        if (tickerItems[2]) tickerItems[2].textContent = cur + (data.low || 0).toFixed(2);
        if (tickerItems[3]) tickerItems[3].textContent = cur + (data.high || 0).toFixed(2);
        if (tickerItems[4]) tickerItems[4].textContent = cur + (data.open || 0).toFixed(2);
    }
}

// ====== تقرير PDF ======
function initPdfButton() {
    const generatePdfBtn = document.getElementById('generate-pdf');
    if (generatePdfBtn) {
        generatePdfBtn.addEventListener('click', () => {
            showNotification('جاري إنشاء التقرير...');
            window.open(`/api/report/${currentSymbol}`, '_blank');
        });
    }
}

// ====== CSS Animations ======
const style = document.createElement('style');
style.textContent = `
    @keyframes slideDown { from { transform: translate(-50%, -100%); opacity: 0; } to { transform: translate(-50%, 0); opacity: 1; } }
    @keyframes slideUp { from { transform: translate(-50%, 0); opacity: 1; } to { transform: translate(-50%, -100%); opacity: 0; } }
    .notification { font-family: 'Segoe UI', Tahoma, sans-serif; }
    .hidden { display: none !important; }
`;
document.head.appendChild(style);

// ====== تصدير الدوال ======
window.Leo2Stock = {
    selectStock, addToFavorites, removeFromFavorites,
    openModal, closeModal, showNotification,
    calculatePosition, createAlert, removeAlert, runBacktest
};
