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

        if (data.latest_indicators) {
            indicatorsCard.style.display = "block";
            const ind = data.latest_indicators;
            const setVal = (id, val, cls = "") => {
                const el = document.getElementById(id);
                el.textContent = fmt(val, 2);
                el.className = "value " + cls;
            };
            setVal("ma5", ind.ma5); setVal("ma10", ind.ma10); setVal("ma20", ind.ma20); setVal("ma50", ind.ma50);
            const rsiClass = ind.rsi14 > 70 ? "negative" : ind.rsi14 < 30 ? "positive" : "neutral";
            setVal("rsi14", ind.rsi14, rsiClass);
            setVal("macd", ind.macd); setVal("macd-signal", ind.macd_signal); setVal("bb-upper", ind.bb_upper); setVal("bb-lower", ind.bb_lower);
        }

        await renderChart(insCode);
        setStatus(`✅ ${data.symbol.symbol} بارگذاری شد`, "ok");
    } catch (e) { setStatus(`❌ خطا: ${e.message}`, "error"); }
    finally { loadBtn.disabled = false; }
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
        setStatus("⏳ در حال اسکن کل بازار (ممکن است چند ثانیه طول بکشد)...");
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
