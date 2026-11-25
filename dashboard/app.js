const API_BASE = `http://${window.location.hostname}:8000`;

const searchInput = document.getElementById("search-input");
const symbolSelect = document.getElementById("symbol-select");
const loadBtn = document.getElementById("load-btn");
const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");
const latestCard = document.getElementById("latest-card");
const indicatorsCard = document.getElementById("indicators-card");
const chartCard = document.getElementById("chart-card");
let priceChart = null;
let allSymbols = [];

function setStatus(msg, type = "") {
    statusText.textContent = msg;
    statusEl.className = "status " + type;
}
function fmt(num, decimals = 0) {
    if (num === null || num === undefined) return "-";
    return Number(num).toLocaleString("fa-IR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

async function loadSymbols() {
    setStatus("در حال بارگذاری نمادها...");
    try {
        const r = await fetch(`${API_BASE}/api/symbols?limit=1000`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        allSymbols = data.items || [];
        populateSelect(allSymbols);
        setStatus(`✅ ${data.total} نماد بارگذاری شد`, "ok");
    } catch (e) { setStatus(`❌ خطا: ${e.message}`, "error"); }
}

function populateSelect(symbols) {
    symbolSelect.innerHTML = '<option value="">-- انتخاب --</option>';
    symbols.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s.ins_code;
        opt.textContent = `${s.symbol} - ${s.name}`;
        symbolSelect.appendChild(opt);
    });
}

async function loadSymbol(insCode) {
    if (!insCode) return;
    setStatus("در حال دریافت داده...");
    loadBtn.disabled = true;
    try {
        const r = await fetch(`${API_BASE}/api/latest/${insCode}`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        
        latestCard.style.display = "block";
        document.getElementById("symbol-title").textContent = `${data.symbol.symbol} - ${data.symbol.name}`;
        document.getElementById("price-close").textContent = fmt(data.latest_price?.price_close);
        document.getElementById("volume").textContent = fmt(data.latest_price?.volume);
        document.getElementById("trades").textContent = fmt(data.latest_price?.trades);
        
        const change = Number(data.latest_price?.price_change || 0);
        const changeEl = document.getElementById("price-change");
        changeEl.textContent = (change >= 0 ? "+" : "") + fmt(change);
        changeEl.className = "value " + (change > 0 ? "positive" : change < 0 ? "negative" : "neutral");

        // ==========================================
        // نمایش همه ۳۳ اندیکاتور
        // ==========================================
        if (data.latest_indicators) {
            const ind = data.latest_indicators;
            renderIndicators(ind);
        }

        await renderChart(insCode);
        setStatus(`✅ ${data.symbol.symbol} بارگذاری شد`, "ok");
    } catch (e) { setStatus(`❌ خطا: ${e.message}`, "error"); }
    finally { loadBtn.disabled = false; }
}

function renderIndicators(ind) {
    // بخش اصلی
    indicatorsCard.style.display = "block";
    
    // گروه‌بندی اندیکاتورها
    const groups = {
        "میانگین‌های متحرک": [
            { label: "MA5", value: ind.ma5, decimals: 2 },
            { label: "MA10", value: ind.ma10, decimals: 2 },
            { label: "MA20", value: ind.ma20, decimals: 2 },
            { label: "MA50", value: ind.ma50, decimals: 2 },
        ],
        "مومنتوم": [
            { label: "RSI14", value: ind.rsi14, decimals: 1, classify: "rsi" },
            { label: "Stoch %K", value: ind.stoch_k, decimals: 1, classify: "stoch" },
            { label: "Stoch %D", value: ind.stoch_d, decimals: 1, classify: "stoch" },
            { label: "Williams %R", value: ind.williams_r, decimals: 1 },
            { label: "ROC12", value: ind.roc12, decimals: 2 },
        ],
        "MACD": [
            { label: "MACD", value: ind.macd, decimals: 2 },
            { label: "Signal", value: ind.macd_signal, decimals: 2 },
            { label: "Histogram", value: ind.macd_histogram, decimals: 2, classify: "hist" },
        ],
        "بولینگر": [
            { label: "BB Upper", value: ind.bb_upper, decimals: 0 },
            { label: "BB Middle", value: ind.bb_middle, decimals: 0 },
            { label: "BB Lower", value: ind.bb_lower, decimals: 0 },
        ],
        "نوسان و روند": [
            { label: "ATR14", value: ind.atr14, decimals: 2 },
            { label: "ADX14", value: ind.adx14, decimals: 1, classify: "adx" },
            { label: "+DI", value: ind.plus_di, decimals: 1 },
            { label: "-DI", value: ind.minus_di, decimals: 1 },
            { label: "PSAR", value: ind.psar, decimals: 0 },
        ],
        "حجم": [
            { label: "OBV", value: ind.obv, decimals: 0 },
            { label: "VWAP", value: ind.vwap, decimals: 0 },
            { label: "MFI14", value: ind.mfi14, decimals: 1, classify: "mfi" },
        ],
        "CCI": [
            { label: "CCI20", value: ind.cci20, decimals: 1, classify: "cci" },
        ],
        "Ichimoku": [
            { label: "Tenkan", value: ind.ichimoku_tenkan, decimals: 0 },
            { label: "Kijun", value: ind.ichimoku_kijun, decimals: 0 },
            { label: "Senkou A", value: ind.ichimoku_senkou_a, decimals: 0 },
            { label: "Senkou B", value: ind.ichimoku_senkou_b, decimals: 0 },
        ],
        "فیبوناچی": [
            { label: "Fib 23.6%", value: ind.fib_236, decimals: 0 },
            { label: "Fib 38.2%", value: ind.fib_382, decimals: 0 },
            { label: "Fib 50.0%", value: ind.fib_500, decimals: 0 },
            { label: "Fib 61.8%", value: ind.fib_618, decimals: 0 },
            { label: "Fib 78.6%", value: ind.fib_786, decimals: 0 },
        ],
    };

    // روند
    const trendDiv = document.getElementById("trend-info");
    if (trendDiv) {
        const dir = ind.trend_direction || "SIDEWAYS";
        const str = ind.trend_strength || "WEAK";
        const dirFa = { UP: "صعودی", DOWN: "نزولی", SIDEWAYS: "خنثی" }[dir] || dir;
        const strFa = { STRONG: "قوی", MEDIUM: "متوسط", WEAK: "ضعیف" }[str] || str;
        const cls = dir === "UP" ? "positive" : dir === "DOWN" ? "negative" : "neutral";
        trendDiv.innerHTML = `<span class="label">روند:</span> <span class="value ${cls}">${dirFa}</span> | <span class="label">قدرت:</span> <span class="value">${strFa}</span>`;
    }

    // رندر گروه‌ها
    const container = document.getElementById("indicator-groups");
    if (!container) return;
    container.innerHTML = "";
    
    for (const [groupName, items] of Object.entries(groups)) {
        const groupDiv = document.createElement("div");
        groupDiv.className = "indicator-group";
        groupDiv.innerHTML = `<h3>${groupName}</h3>`;
        
        const grid = document.createElement("div");
        grid.className = "info-grid";
        
        items.forEach(item => {
            const div = document.createElement("div");
            div.className = "info-item";
            
            let cls = "";
            if (item.classify === "rsi" && item.value !== null) {
                if (item.value > 70) cls = "negative";
                else if (item.value < 30) cls = "positive";
            } else if (item.classify === "stoch" && item.value !== null) {
                if (item.value > 80) cls = "negative";
                else if (item.value < 20) cls = "positive";
            } else if (item.classify === "hist" && item.value !== null) {
                cls = item.value > 0 ? "positive" : "negative";
            } else if (item.classify === "adx" && item.value !== null) {
                if (item.value > 25) cls = "positive";
                else if (item.value < 20) cls = "neutral";
            } else if (item.classify === "mfi" && item.value !== null) {
                if (item.value > 80) cls = "negative";
                else if (item.value < 20) cls = "positive";
            } else if (item.classify === "cci" && item.value !== null) {
                if (item.value > 100) cls = "negative";
                else if (item.value < -100) cls = "positive";
            }
            
            div.innerHTML = `
                <span class="label">${item.label}</span>
                <span class="value ${cls}">${fmt(item.value, item.decimals)}</span>
            `;
            grid.appendChild(div);
        });
        
        groupDiv.appendChild(grid);
        container.appendChild(groupDiv);
    }
}

async function renderChart(insCode) {
    const r = await fetch(`${API_BASE}/api/history/${insCode}?limit=100`);
    const data = await r.json();
    const items = (data.items || []).slice().reverse();
    
    chartCard.style.display = "block";
    const ctx = document.getElementById("price-chart").getContext("2d");
    if (priceChart) priceChart.destroy();
    
    priceChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: items.map(i => String(i.date)),
            datasets: [{ label: "قیمت پایانی", data: items.map(i => i.price_close), borderColor: "#e6bd62", borderWidth: 2, tension: 0.2, pointRadius: 0 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color: "#e8f0f8", font: { family: "Tahoma" } } } },
            scales: {
                x: { ticks: { color: "#8ba3be", maxRotation: 0, autoSkip: true, maxTicksLimit: 10 }, grid: { color: "#1e3555" } },
                y: { ticks: { color: "#8ba3be" }, grid: { color: "#1e3555" } },
            }
        }
    });
}

searchInput.addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    if (!q) return populateSelect(allSymbols);
    populateSelect(allSymbols.filter(s => (s.symbol||"").toLowerCase().includes(q) || (s.name||"").toLowerCase().includes(q)));
});

loadBtn.addEventListener("click", () => loadSymbol(symbolSelect.value));
symbolSelect.addEventListener("change", () => { if (symbolSelect.value) loadSymbol(symbolSelect.value); });

// --- موتور جستجوی هوشمند ---
const smartBtn = document.getElementById("smart-btn");
if (smartBtn) {
    smartBtn.addEventListener("click", async () => {
        setStatus("⏳ در حال اسکن کل بازار...");
        smartBtn.disabled = true;
        smartBtn.textContent = "⏳ در حال اسکن...";
        try {
            const r = await fetch(`${API_BASE}/api/smart-scan`);
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const data = await r.json();
            const container = document.getElementById("smart-results");
            
            if (!data.items || data.items.length === 0) {
                container.innerHTML = "<p style='color:#8ba3be'>هیچ نمادی پیدا نشد.</p>";
                setStatus("✅ اسکن شد (۰ نتیجه)", "ok");
                return;
            }
            
            let html = '<table class="setup-table"><thead><tr><th>#</th><th>نماد</th><th>امتیاز</th><th>RSI</th><th>حجم</th><th>دلایل</th></tr></thead><tbody>';
            data.items.forEach((item, idx) => {
                const scoreClass = item.score >= 70 ? "positive" : item.score >= 50 ? "neutral" : "";
                html += `<tr>
                    <td>${idx + 1}</td>
                    <td><b>${item.symbol}</b></td>
                    <td class="${scoreClass}">${item.score}</td>
                    <td>${item.rsi || '-'}</td>
                    <td>${item.volume_ratio ? item.volume_ratio + 'x' : '-'}</td>
                    <td style="font-size:11px; color:#8ba3be;">${(item.reasons||[]).join(', ')}</td>
                </tr>`;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
            setStatus(`✅ ${data.count} نماد مستعد رشد پیدا شد`, "ok");
        } catch (e) {
            setStatus(`❌ خطا: ${e.message}`, "error");
        } finally {
            smartBtn.disabled = false;
            smartBtn.textContent = "🚀 اسکن کل بازار";
        }
    });
}

loadSymbols();
