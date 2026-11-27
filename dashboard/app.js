const API_BASE = `http://${window.location.hostname}:8000`;
const searchInput = document.getElementById("search-input");
const symbolSelect = document.getElementById("symbol-select");
const loadBtn = document.getElementById("load-btn");
const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");
const latestCard = document.getElementById("latest-card");
const indicatorsCard = document.getElementById("indicators-card");
const chartCard = document.getElementById("chart-card");
let priceChart = null; let allSymbols = [];

function setStatus(msg, type = "") { statusText.textContent = msg; statusEl.className = "status " + type; }
function fmt(num, decimals = 0) { if (num === null || num === undefined) return "-"; return Number(num).toLocaleString("fa-IR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }); }

async function loadSymbols() {
    try {
        const r = await fetch(`${API_BASE}/api/symbols?limit=1000`);
        const data = await r.json();
        allSymbols = data.items || [];
        populateSelect(allSymbols);
        setStatus(`✅ ${data.total} نماد بارگذاری شد`, "ok");
    } catch (e) { setStatus(`❌ خطا: ${e.message}`, "error"); }
}
function populateSelect(symbols) {
    symbolSelect.innerHTML = '<option value="">-- انتخاب --</option>';
    symbols.forEach(s => { const opt = document.createElement("option"); opt.value = s.ins_code; opt.textContent = `${s.symbol} - ${s.name}`; symbolSelect.appendChild(opt); });
}
async function loadSymbol(insCode) {
    if (!insCode) return; loadBtn.disabled = true; setStatus("در حال دریافت...");
    try {
        const r = await fetch(`${API_BASE}/api/latest/${insCode}`);
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
        if (data.latest_indicators) renderIndicators(data.latest_indicators);
        await renderChart(insCode); setStatus(`✅ ${data.symbol.symbol} بارگذاری شد`, "ok");
    } catch (e) { setStatus(`❌ خطا: ${e.message}`, "error"); } finally { loadBtn.disabled = false; }
}
function renderIndicators(ind) {
    indicatorsCard.style.display = "block";
    const groups = {
        "میانگین": [{ label: "MA5", value: ind.ma5, decimals: 2 }, { label: "MA20", value: ind.ma20, decimals: 2 }, { label: "MA50", value: ind.ma50, decimals: 2 }, { label: "WMA20", value: ind.wma20, decimals: 2 }, { label: "VWMA20", value: ind.vwma20, decimals: 2 }],
        "مومنتوم": [{ label: "RSI14", value: ind.rsi14, decimals: 1 }, { label: "Stoch RSI", value: ind.stoch_rsi, decimals: 1 }, { label: "Stoch %K", value: ind.stoch_k, decimals: 1 }, { label: "CCI20", value: ind.cci20, decimals: 1 }],
        "روند": [{ label: "Supertrend", value: ind.supertrend, decimals: 0 }, { label: "جهت ST", value: ind.supertrend_direction, isText: true }, { label: "Aroon Up", value: ind.aroon_up, decimals: 0 }, { label: "Aroon Down", value: ind.aroon_down, decimals: 0 }, { label: "ADX14", value: ind.adx14, decimals: 1 }],
        "حجم": [{ label: "RVOL", value: ind.rvol, decimals: 2 }, { label: "OBV", value: ind.obv, decimals: 0 }, { label: "VWAP", value: ind.vwap, decimals: 0 }, { label: "MFI14", value: ind.mfi14, decimals: 1 }],
        "Volume Profile": [{ label: "POC", value: ind.vp_poc, decimals: 0 }, { label: "VA Low", value: ind.vp_va_low, decimals: 0 }, { label: "VA High", value: ind.vp_va_high, decimals: 0 }],
        "حمایت/مقاومت": [{ label: "Support", value: ind.nearest_support, decimals: 0 }, { label: "Resistance", value: ind.nearest_resistance, decimals: 0 }],
        "Pivot": [{ label: "Pivot", value: ind.pivot, decimals: 0 }, { label: "R1", value: ind.pivot_r1, decimals: 0 }, { label: "S1", value: ind.pivot_s1, decimals: 0 }]
    };
    const container = document.getElementById("indicator-groups");
    if (!container) return; container.innerHTML = "";
    for (const [groupName, items] of Object.entries(groups)) {
        const groupDiv = document.createElement("div"); groupDiv.className = "indicator-group"; groupDiv.innerHTML = `<h3>${groupName}</h3>`;
        const grid = document.createElement("div"); grid.className = "info-grid";
        items.forEach(item => {
            const div = document.createElement("div"); div.className = "info-item";
            let displayValue = item.isText ? (item.value || "-") : fmt(item.value, item.decimals);
            div.innerHTML = `<span class="label">${item.label}</span><span class="value">${displayValue}</span>`;
            grid.appendChild(div);
        });
        groupDiv.appendChild(grid); container.appendChild(groupDiv);
    }
}
async function renderChart(insCode) {
    const r = await fetch(`${API_BASE}/api/history/${insCode}?limit=100`);
    const data = await r.json(); const items = (data.items || []).slice().reverse();
    chartCard.style.display = "block"; const ctx = document.getElementById("price-chart").getContext("2d");
    if (priceChart) priceChart.destroy();
    priceChart = new Chart(ctx, { type: "line", data: { labels: items.map(i => String(i.date)), datasets: [{ label: "قیمت", data: items.map(i => i.price_close), borderColor: "#e6bd62", borderWidth: 2, pointRadius: 0 }] }, options: { responsive: true, maintainAspectRatio: false } });
}
searchInput.addEventListener("input", (e) => { const q = e.target.value.trim().toLowerCase(); if (!q) return populateSelect(allSymbols); populateSelect(allSymbols.filter(s => (s.symbol||"").toLowerCase().includes(q) || (s.name||"").toLowerCase().includes(q))); });
loadBtn.addEventListener("click", () => loadSymbol(symbolSelect.value));
symbolSelect.addEventListener("change", () => { if (symbolSelect.value) loadSymbol(symbolSelect.value); });
loadSymbols();
