// dashboard/app.js
// BEHZAD_AI Dashboard logic

const API_BASE = "http://127.0.0.1:8000";

// Elements
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

// ---------- Helpers ----------
function setStatus(msg, type = "") {
  statusText.textContent = msg;
  statusEl.className = "status " + type;
}

function fmt(num, decimals = 0) {
  if (num === null || num === undefined) return "-";
  const n = Number(num);
  if (isNaN(n)) return "-";
  return n.toLocaleString("fa-IR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function classify(value, thresholds) {
  if (value > thresholds.high) return "positive";
  if (value < thresholds.low) return "negative";
  return "neutral";
}

// ---------- Load symbols into dropdown ----------
async function loadSymbols() {
  setStatus("در حال بارگذاری نمادها...");
  try {
    const r = await fetch(`${API_BASE}/api/symbols?limit=1000`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    allSymbols = data.items || [];
    populateSelect(allSymbols);
    setStatus(`✅ ${data.total} نماد بارگذاری شد`, "ok");
  } catch (e) {
    setStatus(`❌ خطا در بارگذاری نمادها: ${e.message}`, "error");
  }
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

// ---------- Load one symbol's data ----------
async function loadSymbol(insCode) {
  if (!insCode) {
    setStatus("لطفاً یک نماد انتخاب کنید");
    return;
  }
  setStatus("در حال دریافت داده...");
  loadBtn.disabled = true;

  try {
    // Latest (price + indicators)
    const r = await fetch(`${API_BASE}/api/latest/${insCode}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();

    renderLatest(data);
    renderIndicators(data);

    // History for chart
    await renderChart(insCode);

    setStatus(`✅ ${data.symbol.symbol} بارگذاری شد`, "ok");
  } catch (e) {
    setStatus(`❌ خطا: ${e.message}`, "error");
  } finally {
    loadBtn.disabled = false;
  }
}

// ---------- Render latest ----------
function renderLatest(data) {
  const sym = data.symbol || {};
  const price = data.latest_price || {};
  latestCard.style.display = "block";
  document.getElementById("symbol-title").textContent = `${sym.symbol} - ${sym.name}`;
  document.getElementById("price-close").textContent = fmt(price.price_close);
  document.getElementById("volume").textContent = fmt(price.volume);
  document.getElementById("trades").textContent = fmt(price.trades);

  const change = Number(price.price_change || 0);
  const changeEl = document.getElementById("price-change");
  changeEl.textContent = (change >= 0 ? "+" : "") + fmt(change);
  changeEl.className = "value " + (change > 0 ? "positive" : change < 0 ? "negative" : "neutral");
}

// ---------- Render indicators ----------
function renderIndicators(data) {
  const ind = data.latest_indicators || {};
  indicatorsCard.style.display = "block";

  const setVal = (id, val, cls = "") => {
    const el = document.getElementById(id);
    el.textContent = fmt(val, 2);
    el.className = "value " + cls;
  };

  setVal("ma5", ind.ma5);
  setVal("ma10", ind.ma10);
  setVal("ma20", ind.ma20);
  setVal("ma50", ind.ma50);

  // RSI: <30 positive (oversold), >70 negative (overbought)
  const rsiClass = ind.rsi14 > 70 ? "negative" : ind.rsi14 < 30 ? "positive" : "neutral";
  setVal("rsi14", ind.rsi14, rsiClass);

  setVal("macd", ind.macd);
  setVal("macd-signal", ind.macd_signal);
  setVal("bb-upper", ind.bb_upper);
  setVal("bb-lower", ind.bb_lower);
}

// ---------- Render chart ----------
async function renderChart(insCode) {
  const r = await fetch(`${API_BASE}/api/history/${insCode}?limit=100`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const data = await r.json();

  // API returns DESC (newest first) — reverse for chart
  const items = (data.items || []).slice().reverse();

  const labels = items.map(i => String(i.date));
  const closes = items.map(i => i.price_close);
  const ma5 = items.map(i => i.ma5 || null);

  // Also fetch indicators for MA5 line
  const rInd = await fetch(`${API_BASE}/api/indicators/${insCode}?limit=100`);
  const indData = rInd.ok ? await rInd.json() : { items: [] };
  const indItems = (indData.items || []).slice().reverse();
  const ma5Line = items.map((item, idx) => {
    const found = indItems.find(x => x.date === item.date);
    return found ? found.ma5 : null;
  });

  chartCard.style.display = "block";
  const ctx = document.getElementById("price-chart").getContext("2d");

  if (priceChart) priceChart.destroy();

  priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "قیمت پایانی",
          data: closes,
          borderColor: "#e6bd62",
          backgroundColor: "rgba(230, 189, 98, 0.1)",
          borderWidth: 2,
          tension: 0.2,
          pointRadius: 0,
          yAxisID: "y",
        },
        {
          label: "MA5",
          data: ma5Line,
          borderColor: "#6ed9df",
          borderWidth: 1.5,
          tension: 0.2,
          pointRadius: 0,
          borderDash: [5, 3],
          yAxisID: "y",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: "#e8f0f8", font: { family: "Tahoma" } } },
        tooltip: { titleFont: { family: "Tahoma" }, bodyFont: { family: "Tahoma" } },
      },
      scales: {
        x: {
          ticks: { color: "#8ba3be", maxRotation: 0, autoSkip: true, maxTicksLimit: 10 },
          grid: { color: "#1e3555" },
        },
        y: {
          ticks: { color: "#8ba3be" },
          grid: { color: "#1e3555" },
        },
      },
    },
  });
}

// ---------- Search filter ----------
searchInput.addEventListener("input", (e) => {
  const q = e.target.value.trim().toLowerCase();
  if (!q) {
    populateSelect(allSymbols);
    return;
  }
  const filtered = allSymbols.filter(s =>
    (s.symbol || "").toLowerCase().includes(q) ||
    (s.name || "").toLowerCase().includes(q)
  );
  populateSelect(filtered);
});

// ---------- Load button ----------
loadBtn.addEventListener("click", () => {
  loadSymbol(symbolSelect.value);
});

// ---------- Auto-select on dropdown change ----------
symbolSelect.addEventListener("change", () => {
  if (symbolSelect.value) loadSymbol(symbolSelect.value);
});

// ---------- Init ----------
loadSymbols();
