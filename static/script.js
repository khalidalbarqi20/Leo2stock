// ===== Leo2Stock - script.js الكامل مع البحث الديناميكي =====

document.addEventListener('DOMContentLoaded', function() {
    console.log('Leo2Stock initializing...');
    initApp();
});

// ====== المتغيرات العامة ======
let currentSymbol = '';
let currentMarket = '';
let currentTimeframe = '1h';
let fearGreedInterval = null;
let autoUpdateInterval = null;
let chartCtx = null;
let chartCanvas = null;

function setVH() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}
window.addEventListener('resize', setVH);
setVH();

// ====== تهيئة التطبيق ======
function initApp() {
    initSidebar();
    initThemeToggle();
    initSearchBox();
    initActionButtons();
    initRiskCalculator();
    initAlertSystem();
    initBacktesting();
    initModals();
    initRsiScan();
    initPdfButton();
    initNewsFilters();
    loadFavorites();
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

// ====== الوضع الليلي ======
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

// ====== خانة البحث الرئيسية ======
function initSearchBox() {
    const input = document.getElementById('main-search-input');
    const btn = document.getElementById('main-search-btn');
    const backBtn = document.getElementById('btn-back-search');

    if (btn) btn.addEventListener('click', doMainSearch);
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') doMainSearch();
        });
    }
    if (backBtn) {
        backBtn.addEventListener('click', showHeroSearch);
    }
}

function doMainSearch() {
    const input = document.getElementById('main-search-input');
    const marketSel = document.getElementById('main-market-select');
    const symbol = input ? input.value.trim().toUpperCase() : '';
    const market = marketSel ? marketSel.value : 'auto';

    if (!symbol) {
        showNotification('يرجى إدخال رمز السهم', 'error');
        return;
    }

    const finalMarket = market === 'auto' ? (isNaN(symbol) ? 'us' : 'saudi') : market;
    loadStock(symbol, finalMarket);
}

function searchFromGolden(symbol, market) {
    loadStock(symbol, market);
}

function loadStock(symbol, market) {
    currentSymbol = symbol;
    currentMarket = market;

    // إخفاء صفحة البحث وإظهار النتائج
    document.getElementById('hero-search').classList.add('hidden');
    const results = document.getElementById('stock-results');
    results.classList.remove('hidden');

    showNotification(`جاري تحليل ${symbol}...`);

    // جلب البيانات
    fetch(`/api/analyze/${symbol}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error, 'error');
                return;
            }
            renderStockData(data);
            renderChart(data);
            renderNews(data);
            renderMTF(data);
            updateFearGreed(data);
            updateTicker(data);
            updateVolume(data);
            showNotification(`تم تحليل ${symbol} بنجاح`);
            startAutoUpdate();
        })
        .catch(err => {
            showNotification('خطأ في الاتصال بالخادم', 'error');
            console.error(err);
        });

    // تحديث رمز الـ backtest
    const btSymbol = document.getElementById('backtest-symbol');
    if (btSymbol) btSymbol.value = symbol;

    // تمرير للأعلى
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // تهيئة الرسم البياني
    setTimeout(initChart, 100);
}

function showHeroSearch() {
    document.getElementById('hero-search').classList.remove('hidden');
    document.getElementById('stock-results').classList.add('hidden');
    if (autoUpdateInterval) clearInterval(autoUpdateInterval);
    if (fearGreedInterval) clearInterval(fearGreedInterval);
    currentSymbol = '';
}

// ====== تحديث بيانات السهم ======
function renderStockData(data) {
    const sym = document.getElementById('res-symbol');
    const name = document.getElementById('res-name');
    const price = document.getElementById('res-price');
    const change = document.getElementById('res-change');
    const badges = document.getElementById('res-badges');

    if (sym) sym.textContent = data.symbol || currentSymbol;
    if (name) name.textContent = data.name || '';

    const currency = data.currency === 'SAR' ? 'ر.س' : '$';
    if (price) price.textContent = `${currency}${(data.current || 0).toFixed(2)}`;

    if (change) {
        const ch = data.change || 0;
        change.textContent = `${ch >= 0 ? '+' : ''}${ch.toFixed(2)}%`;
        change.className = 'price-change ' + (ch >= 0 ? 'positive' : 'negative');
    }

    if (badges) {
        const mkt = data.market === 'saudi' ? '🇸🇦 سعودي' : '🇺🇸 أمريكي';
        badges.innerHTML = `
            <span class="badge">${mkt}</span>
            <span class="badge">${data.currency || 'USD'}</span>
        `;
    }

    // تحديث حاسبة المخاطر بالسعر الحالي
    const entry = document.getElementById('risk-entry');
    if (entry && data.current) entry.value = data.current.toFixed(2);

    // تحديث مؤشرات المخاطرة
    if (data.analysis && data.analysis.indicators) {
        const atr = document.getElementById('risk-atr');
        if (atr) atr.textContent = data.analysis.indicators.atr || '--';
    }
}

function updateTicker(data) {
    const currency = data.currency === 'SAR' ? 'ر.س' : '$';
    const set = (id, val, prefix = currency) => {
        const el = document.getElementById(id);
        if (el) el.textContent = `${prefix}${val}`;
    };
    set('t-high52', (data.high_52w || 0).toFixed(2));
    set('t-low', (data.low || 0).toFixed(2));
    set('t-high', (data.high || 0).toFixed(2));
    set('t-open', (data.open || 0).toFixed(2));

    const vol = document.getElementById('t-volume');
    if (vol) {
        const v = data.volume || 0;
        vol.textContent = v > 1000000 ? (v/1000000).toFixed(1) + 'M' : v > 1000 ? (v/1000).toFixed(1) + 'K' : v.toString();
    }
}

function updateVolume(data) {
    const ratio = data.avg_volume && data.volume ? (data.volume / data.avg_volume) : 1;
    const pct = Math.min(ratio * 30, 100);
    const bar = document.getElementById('vol-bar');
    const label = document.getElementById('vol-ratio');
    if (bar) bar.style.width = pct + '%';
    if (label) label.textContent = ratio.toFixed(1) + 'x المتوسط';
}

function updateFearGreed(data) {
    let rsi = 50;
    if (data.analysis && data.analysis.indicators) {
        rsi = data.analysis.indicators.rsi || 50;
    }

    // حساب مؤشر الخوف والجشع من RSI
    const fgIndex = Math.round(rsi);

    const indexEl = document.getElementById('fear-greed-index');
    const gaugeEl = document.getElementById('fear-greed-gauge');
    const statusEl = document.getElementById('fear-greed-status');
    const vixEl = document.getElementById('vix-value');
    const predEl = document.getElementById('movement-prediction');
    const probEl = document.getElementById('prediction-probability');

    if (indexEl) indexEl.textContent = fgIndex.toFixed(1);
    if (gaugeEl) gaugeEl.style.width = fgIndex + '%';

    const status = getFearGreedStatus(fgIndex);
    if (statusEl) { statusEl.textContent = status.text; statusEl.className = `status-badge ${status.class}`; }

    const vix = (25 - (fgIndex - 50) * 0.3).toFixed(1);
    if (vixEl) vixEl.textContent = `VIX تقريبي: ${vix}`;

    const pred = predictMovement(fgIndex);
    if (predEl) predEl.textContent = pred.prediction;
    if (probEl) probEl.textContent = `احتمالية: ${pred.probability}% | الإشارة: ${pred.signal}`;
}

function getFearGreedStatus(index) {
    if (index >= 75) return { text: 'جشع مفرط', class: 'extreme-greed' };
    if (index >= 55) return { text: 'جشع', class: 'greed' };
    if (index >= 45) return { text: 'محايد', class: 'neutral' };
    if (index >= 25) return { text: 'خوف', class: 'fear' };
    return { text: 'خوف مفرط', class: 'extreme-fear' };
}

function predictMovement(index) {
    if (index >= 75) return { prediction: 'تصحيح هبوطي محتمل - الجشع المفرط يشير إلى قمة محتملة.', probability: 65, signal: 'انتظار/بيع' };
    if (index >= 55) return { prediction: 'استمرار الصعود محتمل مع احتمالية تصحيح خفيف.', probability: 55, signal: 'شراء حذر' };
    if (index >= 45) return { prediction: 'اتجاه غير واضح - انتظار تأكيد الاتجاه.', probability: 50, signal: 'انتظار' };
    if (index >= 25) return { prediction: 'ارتداد صاعد محتمل - الخوف يشير إلى قاع محتمل. فرصة شراء جيدة.', probability: 60, signal: 'شراء' };
    return { prediction: 'ارتداد صاعد قوي محتمل - الخوف المفرط يشير إلى فرصة شراء ممتازة.', probability: 70, signal: 'شراء قوي' };
}

// ====== الرسم البياني ======
function initChart() {
    chartCanvas = document.getElementById('main-chart');
    if (!chartCanvas) return;

    function resizeCanvas() {
        const container = chartCanvas.parentElement;
        chartCanvas.width = container.clientWidth;
        chartCanvas.height = container.clientHeight || 400;
        if (currentSymbol) return;
        chartCtx = chartCanvas.getContext('2d');
        drawMockChart(chartCtx, chartCanvas.width, chartCanvas.height);
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    chartCtx = chartCanvas.getContext('2d');

    const tfButtons = document.querySelectorAll('.tf-btn');
    tfButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tfButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTimeframe = btn.dataset.tf;
        });
    });
}

function renderChart(data) {
    if (!chartCanvas) chartCanvas = document.getElementById('main-chart');
    if (!chartCanvas) return;
    chartCtx = chartCanvas.getContext('2d');

    if (data.prices_arr && data.prices_arr.length > 0) {
        drawCandleChart(chartCtx, chartCanvas.width, chartCanvas.height, data.prices_arr);
    } else {
        drawMockChart(chartCtx, chartCanvas.width, chartCanvas.height);
    }
}

function drawCandleChart(ctx, width, height, pricesArr) {
    const data = pricesArr.slice(-100);
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--card-bg') || '#141d2e';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i < 6; i++) {
        const y = (height / 5) * i;
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    }

    if (!data.length) return;
    const minPrice = Math.min(...data.map(d => d.low));
    const maxPrice = Math.max(...data.map(d => d.high));
    const priceRange = maxPrice - minPrice || 1;
    const candleWidth = (width / data.length) * 0.6;
    const padding = (width / data.length) * 0.2;

    data.forEach((candle, i) => {
        const x = (width / data.length) * i + padding;
        const toY = v => height - ((v - minPrice) / priceRange) * height * 0.85 - height * 0.07;
        const openY = toY(candle.open);
        const closeY = toY(candle.close);
        const highY = toY(candle.high);
        const lowY = toY(candle.low);
        const isGreen = candle.close >= candle.open;
        ctx.fillStyle = isGreen ? '#00ff88' : '#ff4444';
        ctx.strokeStyle = isGreen ? '#00ff88' : '#ff4444';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(x + candleWidth/2, highY); ctx.lineTo(x + candleWidth/2, lowY); ctx.stroke();
        const bodyTop = Math.min(openY, closeY);
        const bodyH = Math.abs(closeY - openY) || 2;
        ctx.fillRect(x, bodyTop, candleWidth, bodyH);
    });

    // SMA 20
    const closes = data.map(d => d.close);
    drawSMALine(ctx, closes, 20, '#00d4ff', width, height, minPrice, priceRange, data.length);
    drawSMALine(ctx, closes, 50, '#ffd700', width, height, minPrice, priceRange, data.length);
}

function drawSMALine(ctx, closes, period, color, width, height, minPrice, priceRange, count) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < closes.length; i++) {
        if (i < period - 1) continue;
        const sum = closes.slice(i - period + 1, i + 1).reduce((a,b) => a+b, 0);
        const sma = sum / period;
        const x = (width / count) * i + (width / count) / 2;
        const y = height - ((sma - minPrice) / priceRange) * height * 0.85 - height * 0.07;
        if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
    }
    ctx.stroke();
}

function drawMockChart(ctx, width, height) {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#141d2e';
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    for (let i = 0; i < 6; i++) {
        const y = (height / 5) * i;
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    }
    const data = [];
    let price = 100;
    for (let i = 0; i < 80; i++) {
        const ch = (Math.random() - 0.5) * 3;
        const open = price;
        const close = price + ch;
        const high = Math.max(open, close) + Math.random() * 1.5;
        const low = Math.min(open, close) - Math.random() * 1.5;
        data.push({ open, high, low, close });
        price = close;
    }
    const minP = Math.min(...data.map(d => d.low));
    const maxP = Math.max(...data.map(d => d.high));
    const range = maxP - minP || 1;
    const cw = (width / data.length) * 0.6;
    const pad = (width / data.length) * 0.2;
    data.forEach((c, i) => {
        const x = (width / data.length) * i + pad;
        const toY = v => height - ((v - minP) / range) * height * 0.85 - height * 0.07;
        const isGreen = c.close >= c.open;
        ctx.fillStyle = isGreen ? '#00ff88' : '#ff4444';
        ctx.strokeStyle = isGreen ? '#00ff88' : '#ff4444';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(x + cw/2, toY(c.high)); ctx.lineTo(x + cw/2, toY(c.low)); ctx.stroke();
        ctx.fillRect(x, Math.min(toY(c.open), toY(c.close)), cw, Math.abs(toY(c.close) - toY(c.open)) || 2);
    });
}

// ====== الأخبار ======
function renderNews(data) {
    const feed = document.getElementById('news-feed');
    if (!feed) return;

    const news = data.news;
    if (!news || !news.articles || news.articles.length === 0) {
        feed.innerHTML = '<p class="empty-message">لا توجد أخبار متاحة</p>';
        return;
    }

    feed.innerHTML = news.articles.map(article => {
        const sentClass = article.sentiment && article.sentiment.score > 0.1 ? 'hot' :
                          article.sentiment && article.sentiment.score < -0.1 ? 'negative' : 'neutral';
        const sentLabel = article.sentiment ? article.sentiment.label : 'محايد';
        const dateStr = article.datetime ? new Date(article.datetime * 1000).toLocaleDateString('ar') : '';
        return `
            <div class="news-card ${sentClass === 'hot' ? 'featured' : ''}">
                <div class="news-badge ${sentClass}">${sentLabel}</div>
                <div class="news-content">
                    <h3>${article.headline || 'بدون عنوان'}</h3>
                    ${article.summary ? `<p>${article.summary.substring(0, 120)}...</p>` : ''}
                    <div class="news-meta">
                        <span class="news-source">${article.source || ''}</span>
                        <span class="news-date">${dateStr}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    // تحديث المشاعر
    if (news.overall_sentiment) {
        const s = news.overall_sentiment;
        const total = s.total || 1;
        const posPct = Math.round((s.positive_count / total) * 100);
        const negPct = Math.round((s.negative_count / total) * 100);
        const neuPct = 100 - posPct - negPct;

        const setBar = (id, valId, pct) => {
            const el = document.getElementById(id);
            const vel = document.getElementById(valId);
            if (el) el.style.width = pct + '%';
            if (vel) vel.textContent = pct + '%';
        };
        setBar('sent-pos', 'sent-pos-val', posPct);
        setBar('sent-neg', 'sent-neg-val', negPct);
        setBar('sent-neu', 'sent-neu-val', neuPct);
    }
}

// ====== Multi Timeframe ======
function renderMTF(data) {
    const container = document.getElementById('mtf-container');
    if (!container) return;

    const mtf = data.multi_timeframe;
    if (!mtf || !mtf.timeframes) {
        container.innerHTML = '<p class="empty-message">لا توجد بيانات</p>';
        return;
    }

    const trendAr = {
        'bullish': 'صاعد', 'bearish': 'هابط',
        'bullish_weak': 'صاعد ضعيف', 'bearish_weak': 'هابط ضعيف',
        'neutral': 'محايد', 'unknown': 'غير معروف'
    };

    const tfs = mtf.timeframes;
    container.innerHTML = Object.keys(tfs).map(key => {
        const tf = tfs[key];
        const trend = tf.trend || 'neutral';
        const trendClass = trend.includes('bullish') ? 'bullish' : trend.includes('bearish') ? 'bearish' : 'neutral';
        const sig = tf.signal || {};
        return `
            <div class="mtf-signal-card ${trendClass}">
                <div class="mtf-header">
                    <span class="mtf-badge ${trendClass}">${trendAr[trend] || trend}</span>
                    <span class="mtf-timeframe">${tf.timeframe || key} — ${tf.description || ''}</span>
                </div>
                <div class="mtf-body">
                    <div class="mtf-direction">
                        <span class="direction-label">${trendAr[trend] || trend}</span>
                        <i class="fas fa-arrow-trend-${trendClass === 'bullish' ? 'up' : trendClass === 'bearish' ? 'down' : 'right'}"></i>
                    </div>
                    <div class="mtf-metrics">
                        <div class="metric"><span class="metric-label">RSI:</span><span class="metric-value">${(tf.rsi || 50).toFixed(1)}</span></div>
                        <div class="metric"><span class="metric-label">الزخم:</span><span class="metric-value">${(tf.momentum_pct || 0).toFixed(2)}%</span></div>
                        <div class="metric"><span class="metric-label">SMA20:</span><span class="metric-value">${(tf.sma20 || 0).toFixed(2)}</span></div>
                    </div>
                    ${sig.action ? `<div class="rec-signal ${trendClass}" style="margin-top:8px;font-size:0.8rem;">${sig.action}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');

    // التوصية
    const recPanel = document.getElementById('rec-panel');
    const recSignal = document.getElementById('rec-signal');
    const recDetails = document.getElementById('rec-details');

    if (recPanel && mtf.recommendation) {
        recPanel.style.display = 'block';
        const rec = mtf.recommendation;
        if (recSignal) {
            recSignal.textContent = rec.action || '--';
            recSignal.className = `rec-signal ${rec.action && rec.action.includes('شراء') ? 'bullish' : rec.action && rec.action.includes('بيع') ? 'bearish' : 'neutral'}`;
        }
        if (recDetails) recDetails.textContent = `الثقة: ${rec.confidence || '--'} | الأفق: ${rec.time_horizon || '--'}`;
    }
}

// ====== فلترة الأخبار ======
function initNewsFilters() {
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('news-filter')) {
            document.querySelectorAll('.news-filter').forEach(f => f.classList.remove('active'));
            e.target.classList.add('active');
        }
    });
    const refreshBtn = document.getElementById('refresh-news');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            if (currentSymbol) {
                showNotification('جاري تحديث الأخبار...');
                fetch(`/api/news/${currentSymbol}`)
                    .then(r => r.json())
                    .then(data => renderNews({ news: data }))
                    .catch(() => showNotification('خطأ في تحديث الأخبار', 'error'));
            }
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
    const btn = document.getElementById('calculate-position');
    if (btn) btn.addEventListener('click', calculatePosition);
}

function calculatePosition() {
    const capital = parseFloat(document.getElementById('risk-capital').value) || 0;
    const riskPercent = parseFloat(document.getElementById('risk-percent').value) || 0;
    const entry = parseFloat(document.getElementById('risk-entry').value) || 0;
    const stop = parseFloat(document.getElementById('risk-stop').value) || 0;
    const target = parseFloat(document.getElementById('risk-target').value) || 0;
    if (!capital || !riskPercent || !entry || !stop) { showNotification('يرجى ملء جميع الحقول', 'error'); return; }
    const riskAmount = capital * (riskPercent / 100);
    const riskPerShare = Math.abs(entry - stop);
    const positionSize = Math.floor(riskAmount / riskPerShare);
    const reward = target ? Math.abs(target - entry) * positionSize : 0;
    const rr = target ? (Math.abs(target - entry) / riskPerShare).toFixed(2) : '--';
    const resultBox = document.getElementById('position-result');
    if (resultBox) {
        resultBox.classList.remove('hidden');
        document.getElementById('pos-size').textContent = positionSize.toLocaleString();
        document.getElementById('pos-risk').textContent = riskAmount.toFixed(2);
        document.getElementById('pos-reward').textContent = target ? reward.toFixed(2) : '--';
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
    const symbol = document.getElementById('alert-symbol').value || currentSymbol;
    const type = document.getElementById('alert-type').value;
    const condition = document.getElementById('alert-condition').value;
    const value = document.getElementById('alert-value').value;
    if (!symbol || !value) { showNotification('يرجى ملء جميع الحقول', 'error'); return; }
    const alertItem = document.createElement('div');
    alertItem.className = 'alert-item active';
    alertItem.innerHTML = `
        <div class="alert-info">
            <span class="alert-symbol">${symbol}</span>
            <span class="alert-condition">${type} ${condition} ${value}</span>
        </div>
        <div class="alert-status"><span class="status-badge active">نشط</span></div>
        <div class="alert-actions">
            <button class="btn-icon small" onclick="removeAlert(this)"><i class="fas fa-trash"></i></button>
        </div>`;
    const alertsGrid = document.getElementById('active-alerts');
    if (alertsGrid) alertsGrid.appendChild(alertItem);
    document.getElementById('alert-form').classList.add('hidden');
    showNotification('تم إنشاء التنبيه بنجاح');
}

function removeAlert(btn) {
    const item = btn.closest('.alert-item');
    if (item) { item.remove(); showNotification('تم حذف التنبيه'); }
}

// ====== الاختبار التاريخي ======
function initBacktesting() {
    const runBtn = document.getElementById('run-backtest');
    if (runBtn) runBtn.addEventListener('click', runBacktest);
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
            const results = document.getElementById('backtest-results');
            if (results) results.classList.remove('hidden');
            const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
            set('bt-return', (data.total_return_pct || 0).toFixed(2) + '%');
            set('bt-winrate', (data.win_rate || 0).toFixed(1) + '%');
            set('bt-drawdown', (data.max_drawdown_pct || 0).toFixed(2) + '%');
            set('bt-sharpe', (data.sharpe_ratio || 0).toFixed(2));
            set('bt-trades', data.total_trades || 0);
            set('bt-avg-profit', (data.avg_trade_return || 0).toFixed(2) + '%');

            const retEl = document.getElementById('bt-return');
            if (retEl) retEl.className = 'metric-value ' + ((data.total_return_pct || 0) >= 0 ? 'positive' : 'negative');
            showNotification('تم الانتهاء من الاختبار التاريخي');
        })
        .catch(() => showNotification('خطأ في الاختبار', 'error'))
        .finally(() => { if (runBtn) runBtn.disabled = false; });
}

// ====== مسح RSI ======
function initRsiScan() {
    const scanBtn = document.getElementById('scan-rsi');
    if (scanBtn) {
        scanBtn.addEventListener('click', () => {
            const maxRsi = document.getElementById('rsi-max').value;
            const market = document.getElementById('market-select').value;
            const finalMarket = market === 'american' ? 'us' : market;
            showNotification(`جاري مسح الأسهم...`);
            fetch(`/api/rsi-scan?market=${finalMarket}&rsi_max=${maxRsi}`)
                .then(r => r.json())
                .then(data => {
                    const resultsDiv = document.getElementById('rsi-results');
                    if (!resultsDiv) return;
                    if (Array.isArray(data) && data.length > 0) {
                        resultsDiv.innerHTML = data.map(stock => `
                            <div class="rsi-result-item">
                                <div class="result-symbol">${stock.symbol || ''}</div>
                                <div class="result-name">${stock.name || ''}</div>
                                <div class="result-rsi">RSI: ${(stock.rsi || 0).toFixed(1)}</div>
                                <div class="result-price">${stock.currency === 'SAR' ? 'ر.س' : '$'}${(stock.price || 0).toFixed(2)}</div>
                                <button class="btn-primary small" onclick="loadStock('${stock.symbol}', '${finalMarket}')">تحليل</button>
                            </div>`).join('');
                    } else {
                        resultsDiv.innerHTML = '<p class="empty-message">لا توجد أسهم بهذا المعيار</p>';
                    }
                    showNotification('تم الانتهاء من المسح');
                })
                .catch(() => showNotification('خطأ في المسح', 'error'));
        });
    }
}

// ====== زر PDF ======
function initPdfButton() {
    const btn = document.getElementById('generate-pdf');
    if (btn) {
        btn.addEventListener('click', () => {
            if (!currentSymbol) { showNotification('ابحث عن سهم أولاً', 'error'); return; }
            showNotification('جاري إنشاء التقرير...');
            window.open(`/api/report/${currentSymbol}`, '_blank');
        });
    }
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
            if (targetPrice) {
                showNotification(`تم تعيين تنبيه: ${direction === 'above' ? 'أعلى' : 'أقل'} من ${targetPrice}`);
                closeModal('price-alert-modal');
            }
        });
    }
}

function openModal(id) { const m = document.getElementById(id); if (m) m.classList.add('active'); }
function closeModal(id) { const m = document.getElementById(id); if (m) m.classList.remove('active'); }

// ====== المفضلة ======
function addToFavorites(symbol) {
    if (!symbol) { showNotification('ابحث عن سهم أولاً', 'error'); return; }
    let favs = JSON.parse(localStorage.getItem('favorites') || '[]');
    if (favs.includes(symbol)) { showNotification(`${symbol} موجود بالفعل في المفضلة`); return; }
    favs.push(symbol);
    localStorage.setItem('favorites', JSON.stringify(favs));
    loadFavorites();
    showNotification(`تم إضافة ${symbol} إلى المفضلة`);
}

function removeFromFavorites(symbol) {
    let favs = JSON.parse(localStorage.getItem('favorites') || '[]');
    favs = favs.filter(s => s !== symbol);
    localStorage.setItem('favorites', JSON.stringify(favs));
    loadFavorites();
    showNotification(`تم إزالة ${symbol} من المفضلة`);
}

function loadFavorites() {
    const container = document.getElementById('favorites-list');
    if (!container) return;
    const favs = JSON.parse(localStorage.getItem('favorites') || '[]');
    if (favs.length === 0) {
        container.innerHTML = '<p class="empty-message">لا توجد أسهم في المفضلة</p>';
        return;
    }
    container.innerHTML = favs.map(sym => `
        <div class="favorite-item">
            <div class="fav-symbol">${sym}</div>
            <button class="btn-primary small" onclick="loadStock('${sym}', '${isNaN(sym) ? 'us' : 'saudi'}')">تحليل</button>
            <button class="btn-icon small" onclick="removeFromFavorites('${sym}')" title="إزالة"><i class="fas fa-times"></i></button>
        </div>`).join('');
}

// ====== التحديث التلقائي ======
function startAutoUpdate() {
    if (autoUpdateInterval) clearInterval(autoUpdateInterval);
    autoUpdateInterval = setInterval(() => {
        if (currentSymbol) {
            fetch(`/api/analyze/${currentSymbol}`)
                .then(r => r.json())
                .then(data => {
                    if (!data.error) {
                        updateTicker(data);
                        updateVolume(data);
                        updateFearGreed(data);
                        const priceEl = document.getElementById('res-price');
                        const changeEl = document.getElementById('res-change');
                        if (priceEl) {
                            const cur = data.currency === 'SAR' ? 'ر.س' : '$';
                            priceEl.textContent = `${cur}${(data.current || 0).toFixed(2)}`;
                        }
                        if (changeEl) {
                            const ch = data.change || 0;
                            changeEl.textContent = `${ch >= 0 ? '+' : ''}${ch.toFixed(2)}%`;
                            changeEl.className = 'price-change ' + (ch >= 0 ? 'positive' : 'negative');
                        }
                    }
                }).catch(() => {});
        }
    }, 60000);
}

// ====== نظام الإشعارات ======
function showNotification(message, type = 'success') {
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i><span>${message}</span>`;
    notification.style.cssText = `position:fixed;top:20px;left:50%;transform:translateX(-50%);background:${type === 'success' ? 'linear-gradient(135deg,#00ff88,#00cc6a)' : 'linear-gradient(135deg,#ff4444,#ff0000)'};color:${type === 'success' ? '#000' : '#fff'};padding:12px 22px;border-radius:12px;font-size:14px;z-index:10000;display:flex;align-items:center;gap:10px;box-shadow:0 4px 15px rgba(0,0,0,0.3);animation:slideDown 0.3s ease;font-family:Cairo,sans-serif;`;
    document.body.appendChild(notification);
    setTimeout(() => { notification.style.opacity = '0'; notification.style.transition = 'opacity 0.3s'; setTimeout(() => notification.remove(), 300); }, 3000);
}

// ====== CSS Animations ======
const styleEl = document.createElement('style');
styleEl.textContent = `
@keyframes slideDown { from { transform: translate(-50%,-100%); opacity:0; } to { transform: translate(-50%,0); opacity:1; } }
.hidden { display: none !important; }
`;
document.head.appendChild(styleEl);

// ====== تصدير ======
window.Leo2Stock = {
    loadStock, searchFromGolden, showHeroSearch,
    addToFavorites, removeFromFavorites, removeAlert,
    openModal, closeModal, showNotification, calculatePosition, runBacktest
};
