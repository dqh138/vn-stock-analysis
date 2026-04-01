function $(id) { return document.getElementById(id); }

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

const nf0 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 });

let currentPeriods = null;
const taxonomyCache = new Map(); // table -> Map(metric_id -> meta)
let currentSymbol = null;
let metricModalState = null; // { table, metricId, unit, description, series }

function formatValue(value, unit) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);

  const adj = normalizeForUnit(n, unit);

  if (unit === "VND") {
    const abs = Math.abs(adj);
    if (abs >= 1e9) return `${nf2.format(adj / 1e9)} tỷ`;
    return nf0.format(adj);
  }
  if (unit === "tỷ VND") return `${nf2.format(adj)} tỷ`;
  if (unit === "%") return `${nf2.format(adj)}%`;
  if (unit === "x") return nf2.format(adj);
  if (unit === "days") return nf0.format(adj);
  return nf2.format(adj);
}

function normalizeForUnit(n, unit) {
  if (unit === "%") {
    const abs = Math.abs(n);
    if (abs <= 1.5) return n * 100;
    return n;
  }
  return n;
}

function defaultChartTypeForUnit(unit) {
  if (unit === "VND" || unit === "tỷ VND") return "bar";
  return "line";
}

async function apiGet(url) {
  const res = await fetch(url, { headers: { "Accept": "application/json" } });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body && body.detail) detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

async function getTaxonomyTable(table) {
  if (taxonomyCache.has(table)) return taxonomyCache.get(table);
  const data = await apiGet(`/api/taxonomy/table/${encodeURIComponent(table)}`);
  const map = new Map();
  for (const m of (data.metrics || [])) map.set(m.id, m);
  taxonomyCache.set(table, map);
  return map;
}

async function refreshDatalist(prefix) {
  const dl = $("symbolDatalist");
  if (!prefix) {
    dl.innerHTML = "";
    return;
  }
  const items = await apiGet(`/api/symbols?q=${encodeURIComponent(prefix)}&limit=20`);
  dl.innerHTML = items.map((it) => {
    const label = `${it.ticker} • ${it.organ_name || ""}`;
    return `<option value="${escapeHtml(it.ticker)}" label="${escapeHtml(label)}"></option>`;
  }).join("");
}

function renderMeta(meta) {
  const fields = [
    ["Mã", meta.ticker],
    ["Tên", meta.organ_name],
    ["Sàn", meta.exchanges || "-"],
    ["ICB3", meta.icb_name3 || "-"],
    ["ICB4", meta.icb_name4 || "-"],
  ];
  return fields.map(([k, v]) => `
    <div class="meta__item">
      <div class="meta__k">${escapeHtml(k)}</div>
      <div class="meta__v">${escapeHtml(v ?? "-")}</div>
    </div>
  `).join("");
}

function setYearOptions(periods) {
  const yearSelect = $("yearSelect");
  yearSelect.innerHTML = "";
  const years = periods.yearly_years?.length ? periods.yearly_years : (periods.years || []);
  for (const y of years) {
    const opt = document.createElement("option");
    opt.value = String(y);
    opt.textContent = String(y);
    yearSelect.appendChild(opt);
  }
}

function updateQuarterOptions(year) {
  const qSel = $("quarterSelect");
  const quarters = currentPeriods?.quarterly_by_year?.[year] || [];
  const current = qSel.value;

  const opts = [`<option value="">Năm (Yearly)</option>`].concat(
    quarters.map((q) => `<option value="${q}">Q${q}</option>`)
  );
  qSel.innerHTML = opts.join("");

  if (current && !quarters.includes(Number(current))) qSel.value = "";
}

function groupItems(items) {
  const map = new Map();
  for (const it of items || []) {
    const key = it.group_label || it.group || "Other";
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(it);
  }
  return [...map.entries()];
}

function sparklinePath(values, width, height, pad) {
  const pts = [];
  for (const v of values) {
    const n = Number(v);
    if (Number.isFinite(n)) pts.push(n);
  }
  if (pts.length < 2) return "";

  let min = Math.min(...pts);
  let max = Math.max(...pts);
  if (min === max) { min -= 1; max += 1; }

  const w = width - pad * 2;
  const h = height - pad * 2;
  const n = pts.length;

  const out = [];
  for (let i = 0; i < n; i++) {
    const x = pad + (i / (n - 1)) * w;
    const yNorm = (pts[i] - min) / (max - min);
    const y = pad + (1 - yNorm) * h;
    out.push(`${x.toFixed(2)},${y.toFixed(2)}`);
  }
  return out.join(" ");
}

function trendTone(values) {
  const nums = values.map((v) => Number(v)).filter((n) => Number.isFinite(n));
  if (nums.length < 2) return "neutral";
  const last = nums[nums.length - 1];
  const prev = nums[nums.length - 2];
  if (last > prev) return "positive";
  if (last < prev) return "negative";
  return "neutral";
}

function renderSparklineCard({ title, subtitle, values, tone }) {
  const w = 520;
  const h = 80;
  const pad = 6;
  const poly = sparklinePath(values, w, h, pad);
  const lineTone = tone || trendTone(values);
  const sub = subtitle || "";
  return `
    <div class="sparkline-wrap">
      <div class="sparkline-header">
        <div class="sparkline-title">${escapeHtml(title)}</div>
        <div class="sparkline-sub">${escapeHtml(sub)}</div>
      </div>
      <svg class="sparkline-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-label="${escapeHtml(title)}">
        <path class="sparkline-grid" d="M0 ${h - 1} H${w}" />
        ${poly ? `<polyline class="sparkline-line ${lineTone}" points="${poly}"></polyline>` : ""}
      </svg>
    </div>
  `;
}

function renderTableCard(tableName, data) {
  const row = data.row;
  const items = data.items || [];
  const meta = row
    ? `period=${row.period || "-"} year=${row.year ?? "-"} q=${row.quarter ?? "Y"} src=${row.source || "-"} updated=${(row.updated_at || "-").slice(0, 19)}`
    : "no data";

  const groups = groupItems(items);
  const inner = groups.map(([groupLabel, groupItems]) => {
    const rows = groupItems.map((it) => `
      <tr class="metric-row" data-table="${escapeHtml(tableName)}" data-metric="${escapeHtml(it.id)}">
        <td>
          <div style="font-weight: 900;">${escapeHtml(it.label)}</div>
          <div class="desc">${escapeHtml(it.description || "")}</div>
        </td>
        <td class="value">${escapeHtml(formatValue(it.value, it.unit))}</td>
        <td class="unit">${escapeHtml(it.unit || "")}</td>
      </tr>
    `).join("");
    return `
      <div class="group">
        <div class="group__title">${escapeHtml(groupLabel)}</div>
        <table class="metrics">
          <thead>
            <tr>
              <th>Chỉ tiêu</th>
              <th style="text-align:right;">Giá trị</th>
              <th style="text-align:right;">Đơn vị</th>
            </tr>
          </thead>
          <tbody>${rows || `<tr><td colspan="3" class="muted">Không có chỉ tiêu</td></tr>`}</tbody>
        </table>
      </div>
    `;
  }).join("");

  return `
    <div class="table-card">
      <div class="table-card__head">
        <div class="table-card__title">${escapeHtml(tableName)}</div>
        <div class="table-card__meta">${escapeHtml(meta)}</div>
      </div>
      ${inner || `<div class="muted">Không có dữ liệu</div>`}
    </div>
  `;
}

function openModal() {
  $("modalOverlay").hidden = false;
  $("metricModal").hidden = false;
  document.body.style.overflow = "hidden";
}

function closeModal() {
  $("modalOverlay").hidden = true;
  $("metricModal").hidden = true;
  document.body.style.overflow = "";
}

function renderSeriesTable(series, unit) {
  const rows = (series || []).slice().reverse().map((p) => {
    const v = formatValue(p.value, unit);
    return `<tr><td>${escapeHtml(p.label)}</td><td class="v">${escapeHtml(v)}</td></tr>`;
  }).join("");
  return `
    <table>
      <thead><tr><th>Kỳ</th><th style="text-align:right;">Giá trị</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="2" class="muted">Không có dữ liệu</td></tr>`}</tbody>
    </table>
  `;
}

/**
 * Render Cash Flow Quality Score Card
 * @param {Object} cashFlowQuality - Cash flow quality data from API
 */
function renderCashFlowQualityCard(cashFlowQuality) {
  if (!cashFlowQuality || !cashFlowQuality.overall_score) {
    $("cashFlowQualityCard").style.display = "none";
    return;
  }

  // Show the card
  $("cashFlowQualityCard").style.display = "block";

  const score = cashFlowQuality.overall_score;
  const rating = cashFlowQuality.rating || cashFlowQuality.vietnamese_rating || "Không có dữ liệu";

  // Update score and rating
  $("cfqScore").textContent = score;
  $("cfqRating").textContent = rating;

  // Update progress bar with animation
  setTimeout(() => {
    $("cfqProgress").style.width = `${score}%`;
  }, 100);

  // Color-code the progress bar based on score
  const progressBar = $("cfqProgress");
  if (score >= 80) {
    progressBar.style.background = "linear-gradient(90deg, #22c55e 0%, #16a34a 100%)";
  } else if (score >= 60) {
    progressBar.style.background = "linear-gradient(90deg, #84cc16 0%, #22c55e 100%)";
  } else if (score >= 40) {
    progressBar.style.background = "linear-gradient(90deg, #f59e0b 0%, #f97316 100%)";
  } else {
    progressBar.style.background = "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)";
  }

  // Build metrics HTML
  const metricsHtml = [];

  // OCF to Net Income
  const ocfToNi = cashFlowQuality.ocf_to_net_income;
  if (ocfToNi !== null && ocfToNi !== undefined) {
    const ocfStatus = ocfToNi >= 1.0 ? "pass" : ocfToNi >= 0.8 ? "warning" : "fail";
    const ocfIcon = ocfStatus === "pass" ? "✅" : ocfStatus === "warning" ? "⚠️" : "❌";
    const ocfClass = `cfq-status-${ocfStatus}`;
    metricsHtml.push(`
      <div class="cfq-metric-item">
        <div class="cfq-metric-header">
          <div class="cfq-metric-label">OCF / Lợi nhuận</div>
          <div class="cfq-metric-status ${ocfClass}">${ocfIcon}</div>
        </div>
        <div class="cfq-metric-value">${nf2.format(ocfToNi)}x</div>
        <div class="cfq-metric-description">
          ${ocfToNi >= 1.0 ? "Chất lượng lợi nhuận cao" : ocfToNi >= 0.8 ? "Chất lượng lợi nhuận khá" : "Cần chú ý chất lượng lợi nhuận"}
        </div>
      </div>
    `);
  }

  // FCF to Net Income
  const fcfToNi = cashFlowQuality.fcf_to_net_income;
  if (fcfToNi !== null && fcfToNi !== undefined) {
    const fcfStatus = fcfToNi >= 0.8 ? "pass" : fcfToNi >= 0.5 ? "warning" : "fail";
    const fcfIcon = fcfStatus === "pass" ? "✅" : fcfStatus === "warning" ? "⚠️" : "❌";
    const fcfClass = `cfq-status-${fcfStatus}`;
    metricsHtml.push(`
      <div class="cfq-metric-item">
        <div class="cfq-metric-header">
          <div class="cfq-metric-label">FCF / Lợi nhuận</div>
          <div class="cfq-metric-status ${fcfClass}">${fcfIcon}</div>
        </div>
        <div class="cfq-metric-value">${nf2.format(fcfToNi)}x</div>
        <div class="cfq-metric-description">
          ${fcfToNi >= 0.8 ? "Tạo tiền mặt tự do tốt" : fcfToNi >= 0.5 ? "Tạo tiền mặt tự do khá" : "Tiền mặt tự do thấp"}
        </div>
      </div>
    `);
  }

  // OCF Consistency
  const positiveYears = cashFlowQuality.ocf_consistency_years || 0;
  const totalYears = cashFlowQuality.total_years || 0;
  if (totalYears > 0) {
    const consistencyRatio = positiveYears / totalYears;
    const consistencyStatus = consistencyRatio >= 0.8 ? "pass" : consistencyRatio >= 0.6 ? "warning" : "fail";
    const consistencyIcon = consistencyStatus === "pass" ? "✅" : consistencyStatus === "warning" ? "⚠️" : "❌";
    const consistencyClass = `cfq-status-${consistencyStatus}`;
    metricsHtml.push(`
      <div class="cfq-metric-item">
        <div class="cfq-metric-header">
          <div class="cfq-metric-label">Ổn định OCF</div>
          <div class="cfq-metric-status ${consistencyClass}">${consistencyIcon}</div>
        </div>
        <div class="cfq-metric-value">${positiveYears}/${totalYears} năm</div>
        <div class="cfq-metric-description">
          ${Math.round(consistencyRatio * 100)}% các năm có dòng tiền hoạt động dương
        </div>
      </div>
    `);
  }

  // Overall assessment
  const assessmentStatus = score >= 60 ? "pass" : score >= 40 ? "warning" : "fail";
  const assessmentIcon = score >= 80 ? "🌟" : score >= 60 ? "✅" : score >= 40 ? "⚠️" : "❌";
  const assessmentClass = `cfq-status-${assessmentStatus}`;
  metricsHtml.push(`
    <div class="cfq-metric-item">
      <div class="cfq-metric-header">
        <div class="cfq-metric-label">Đánh giá tổng quan</div>
        <div class="cfq-metric-status ${assessmentClass}">${assessmentIcon}</div>
      </div>
      <div class="cfq-metric-value">${score}/100</div>
      <div class="cfq-metric-description">
        ${score >= 80 ? "Chất lượng dòng tiền xuất sắc" : score >= 60 ? "Chất lượng dòng tiền tốt" : score >= 40 ? "Chất lượng dòng tiền trung bình" : "Chất lượng dòng tiền yếu"}
      </div>
    </div>
  `);

  $("cfqMetrics").innerHTML = metricsHtml.join("");

  // Add interpretation
  const interpretation = cashFlowQuality.interpretation || "";
  if (interpretation) {
    $("cfqInterpretation").innerHTML = `
      <div class="cfq-interpretation-title">💡 Diễn giải</div>
      <div class="cfq-interpretation-text">${interpretation}</div>
    `;
  } else {
    $("cfqInterpretation").innerHTML = "";
  }
}

function renderInteractiveLineChart(containerEl, series, unit, { fillArea = false } = {}) {
  containerEl.innerHTML = "";
  const pts = (series || []).map((p) => ({ label: p.label, raw: p.value, value: normalizeForUnit(Number(p.value), unit) }))
    .filter((p) => Number.isFinite(p.value));

  if (pts.length < 2) {
    containerEl.innerHTML = `<div class="muted">Không đủ dữ liệu để vẽ biểu đồ</div>`;
    return;
  }

  const w = 920;
  const h = 320;
  const padL = 54;
  const padR = 18;
  const padT = 18;
  const padB = 38;

  let min = Math.min(...pts.map((p) => p.value));
  let max = Math.max(...pts.map((p) => p.value));
  if (min === max) { min -= 1; max += 1; }
  const span = max - min;
  const margin = span * 0.08;
  min -= margin;
  max += margin;

  const x = (i) => padL + (i / (pts.length - 1)) * (w - padL - padR);
  const y = (v) => padT + (1 - (v - min) / (max - min)) * (h - padT - padB);

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.classList.add("sparkline-svg");
  svg.style.height = "260px";

  const grid = document.createElementNS("http://www.w3.org/2000/svg", "path");
  grid.setAttribute("d", `M${padL} ${h - padB} H${w - padR}`);
  grid.setAttribute("class", "sparkline-grid");
  svg.appendChild(grid);

  if (fillArea) {
    const area = document.createElementNS("http://www.w3.org/2000/svg", "path");
    let da = "";
    pts.forEach((p, i) => {
      const xi = x(i);
      const yi = y(p.value);
      da += (i === 0 ? "M" : "L") + xi.toFixed(2) + " " + yi.toFixed(2) + " ";
    });
    da += `L${x(pts.length - 1).toFixed(2)} ${(h - padB).toFixed(2)} L${x(0).toFixed(2)} ${(h - padB).toFixed(2)} Z`;
    area.setAttribute("d", da.trim());
    area.setAttribute("fill", "rgba(79, 172, 254, 0.14)");
    area.setAttribute("stroke", "none");
    svg.appendChild(area);
  }

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  let d = "";
  pts.forEach((p, i) => {
    const xi = x(i);
    const yi = y(p.value);
    d += (i === 0 ? "M" : "L") + xi.toFixed(2) + " " + yi.toFixed(2) + " ";
  });
  path.setAttribute("d", d.trim());
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "rgba(79, 172, 254, 0.95)");
  path.setAttribute("stroke-width", "2.8");
  path.setAttribute("stroke-linecap", "round");
  svg.appendChild(path);

  const tooltip = document.createElement("div");
  tooltip.className = "chart-tooltip";
  containerEl.appendChild(tooltip);

  const circles = [];
  pts.forEach((p, i) => {
    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("cx", String(x(i)));
    c.setAttribute("cy", String(y(p.value)));
    c.setAttribute("r", "4.3");
    c.setAttribute("fill", "rgba(0,0,0,0)");
    c.setAttribute("stroke", "rgba(79, 172, 254, 0.8)");
    c.setAttribute("stroke-width", "1.8");
    c.style.cursor = "pointer";
    c.addEventListener("mouseenter", (e) => {
      tooltip.style.display = "block";
      tooltip.textContent = `${p.label}: ${formatValue(p.raw, unit)}`;
      c.setAttribute("fill", "rgba(79, 172, 254, 0.25)");
      c.setAttribute("r", "5.4");
    });
    c.addEventListener("mouseleave", () => {
      tooltip.style.display = "none";
      c.setAttribute("fill", "rgba(0,0,0,0)");
      c.setAttribute("r", "4.3");
    });
    c.addEventListener("mousemove", (e) => {
      const rect = containerEl.getBoundingClientRect();
      tooltip.style.left = `${e.clientX - rect.left}px`;
      tooltip.style.top = `${e.clientY - rect.top}px`;
    });
    circles.push(c);
    svg.appendChild(c);
  });

  const tMin = document.createElementNS("http://www.w3.org/2000/svg", "text");
  tMin.setAttribute("x", "8");
  tMin.setAttribute("y", String(h - padB + 4));
  tMin.setAttribute("fill", "rgba(182, 194, 210, 0.85)");
  tMin.setAttribute("font-size", "12");
  tMin.setAttribute("font-family", "ui-monospace, Menlo, monospace");
  tMin.textContent = formatValue(min, unit);
  svg.appendChild(tMin);

  const tMax = document.createElementNS("http://www.w3.org/2000/svg", "text");
  tMax.setAttribute("x", "8");
  tMax.setAttribute("y", String(padT + 12));
  tMax.setAttribute("fill", "rgba(182, 194, 210, 0.85)");
  tMax.setAttribute("font-size", "12");
  tMax.setAttribute("font-family", "ui-monospace, Menlo, monospace");
  tMax.textContent = formatValue(max, unit);
  svg.appendChild(tMax);

  const tStart = document.createElementNS("http://www.w3.org/2000/svg", "text");
  tStart.setAttribute("x", String(padL));
  tStart.setAttribute("y", String(h - 12));
  tStart.setAttribute("fill", "rgba(182, 194, 210, 0.75)");
  tStart.setAttribute("font-size", "12");
  tStart.setAttribute("font-family", "ui-monospace, Menlo, monospace");
  tStart.textContent = pts[0].label;
  svg.appendChild(tStart);

  const tEnd = document.createElementNS("http://www.w3.org/2000/svg", "text");
  tEnd.setAttribute("x", String(w - padR));
  tEnd.setAttribute("y", String(h - 12));
  tEnd.setAttribute("fill", "rgba(182, 194, 210, 0.75)");
  tEnd.setAttribute("font-size", "12");
  tEnd.setAttribute("font-family", "ui-monospace, Menlo, monospace");
  tEnd.setAttribute("text-anchor", "end");
  tEnd.textContent = pts[pts.length - 1].label;
  svg.appendChild(tEnd);

  containerEl.appendChild(svg);
}

function renderInteractiveBarChart(containerEl, series, unit) {
  containerEl.innerHTML = "";
  const pts = (series || []).map((p) => ({ label: p.label, raw: p.value, value: normalizeForUnit(Number(p.value), unit) }))
    .filter((p) => Number.isFinite(p.value));

  if (pts.length < 1) {
    containerEl.innerHTML = `<div class="muted">Không có dữ liệu để vẽ biểu đồ</div>`;
    return;
  }

  const w = 920;
  const h = 320;
  const padL = 54;
  const padR = 18;
  const padT = 18;
  const padB = 38;

  let min = Math.min(...pts.map((p) => p.value));
  let max = Math.max(...pts.map((p) => p.value));
  if (min === max) { min -= 1; max += 1; }
  const span = max - min;
  const margin = span * 0.08;
  min -= margin;
  max += margin;
  if (min > 0) min = 0;
  if (max < 0) max = 0;

  const y = (v) => padT + (1 - (v - min) / (max - min)) * (h - padT - padB);
  const y0 = y(0);
  const x0 = padL;
  const x1 = w - padR;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.classList.add("sparkline-svg");
  svg.style.height = "260px";

  const axis = document.createElementNS("http://www.w3.org/2000/svg", "path");
  axis.setAttribute("d", `M${x0} ${y0} H${x1}`);
  axis.setAttribute("class", "sparkline-grid");
  svg.appendChild(axis);

  const tooltip = document.createElement("div");
  tooltip.className = "chart-tooltip";
  containerEl.appendChild(tooltip);

  const n = pts.length;
  const innerW = x1 - x0;
  const step = innerW / Math.max(1, n);
  const barW = Math.max(6, Math.min(26, step * 0.62));

  pts.forEach((p, i) => {
    const cx = x0 + step * (i + 0.5);
    const v = p.value;
    const yv = y(v);
    const top = Math.min(y0, yv);
    const height = Math.abs(y0 - yv);
    const left = cx - barW / 2;
    const tone = v >= 0 ? "rgba(16, 185, 129, 0.80)" : "rgba(239, 68, 68, 0.80)";

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", left.toFixed(2));
    rect.setAttribute("y", top.toFixed(2));
    rect.setAttribute("width", barW.toFixed(2));
    rect.setAttribute("height", Math.max(1, height).toFixed(2));
    rect.setAttribute("rx", "4");
    rect.setAttribute("fill", tone);
    rect.style.cursor = "pointer";
    rect.addEventListener("mouseenter", () => {
      tooltip.style.display = "block";
      tooltip.textContent = `${p.label}: ${formatValue(p.raw, unit)}`;
      rect.setAttribute("fill", tone.replace("0.80", "0.95"));
    });
    rect.addEventListener("mouseleave", () => {
      tooltip.style.display = "none";
      rect.setAttribute("fill", tone);
    });
    rect.addEventListener("mousemove", (e) => {
      const b = containerEl.getBoundingClientRect();
      tooltip.style.left = `${e.clientX - b.left}px`;
      tooltip.style.top = `${e.clientY - b.top}px`;
    });
    svg.appendChild(rect);
  });

  const tMin = document.createElementNS("http://www.w3.org/2000/svg", "text");
  tMin.setAttribute("x", "8");
  tMin.setAttribute("y", String(h - padB + 4));
  tMin.setAttribute("fill", "rgba(182, 194, 210, 0.85)");
  tMin.setAttribute("font-size", "12");
  tMin.setAttribute("font-family", "ui-monospace, Menlo, monospace");
  tMin.textContent = formatValue(min, unit);
  svg.appendChild(tMin);

  const tMax = document.createElementNS("http://www.w3.org/2000/svg", "text");
  tMax.setAttribute("x", "8");
  tMax.setAttribute("y", String(padT + 12));
  tMax.setAttribute("fill", "rgba(182, 194, 210, 0.85)");
  tMax.setAttribute("font-size", "12");
  tMax.setAttribute("font-family", "ui-monospace, Menlo, monospace");
  tMax.textContent = formatValue(max, unit);
  svg.appendChild(tMax);

  const tStart = document.createElementNS("http://www.w3.org/2000/svg", "text");
  tStart.setAttribute("x", String(padL));
  tStart.setAttribute("y", String(h - 12));
  tStart.setAttribute("fill", "rgba(182, 194, 210, 0.75)");
  tStart.setAttribute("font-size", "12");
  tStart.setAttribute("font-family", "ui-monospace, Menlo, monospace");
  tStart.textContent = pts[0].label;
  svg.appendChild(tStart);

  const tEnd = document.createElementNS("http://www.w3.org/2000/svg", "text");
  tEnd.setAttribute("x", String(w - padR));
  tEnd.setAttribute("y", String(h - 12));
  tEnd.setAttribute("fill", "rgba(182, 194, 210, 0.75)");
  tEnd.setAttribute("font-size", "12");
  tEnd.setAttribute("font-family", "ui-monospace, Menlo, monospace");
  tEnd.setAttribute("text-anchor", "end");
  tEnd.textContent = pts[pts.length - 1].label;
  svg.appendChild(tEnd);

  containerEl.appendChild(svg);
}

function renderMetricModalCharts() {
  if (!metricModalState) return;
  const { unit, series } = metricModalState;
  const chartTypeSel = $("metricChartType").value || "auto";
  const chartType = chartTypeSel === "auto" ? defaultChartTypeForUnit(unit) : chartTypeSel;

  if (chartType === "bar") {
    renderInteractiveBarChart($("metricChartWrap"), series, unit);
  } else if (chartType === "area") {
    renderInteractiveLineChart($("metricChartWrap"), series, unit, { fillArea: true });
  } else {
    renderInteractiveLineChart($("metricChartWrap"), series, unit, { fillArea: false });
  }
  $("metricSeriesTable").innerHTML = renderSeriesTable(series, unit);
}

async function showMetricDetail(table, metricId) {
  if (!currentSymbol) return;
  const tax = await getTaxonomyTable(table);
  const meta = tax.get(metricId) || { id: metricId, label: metricId, unit: "", description: "" };

  $("metricModalTitle").textContent = `${meta.label || metricId}`;
  $("metricModalSub").textContent = `${table} • ${metricId} • unit=${meta.unit || "-"}`;
  $("metricModalDesc").textContent = meta.description || "";
  $("metricChartWrap").innerHTML = `<div class="muted">Đang tải...</div>`;
  $("metricSeriesTable").innerHTML = "";

  $("metricChartType").value = "auto";
  openModal();

  const period = $("metricPeriod").value || "yearly";
  const qs = new URLSearchParams({ table, metrics: metricId, period });
  const data = await apiGet(`/api/symbol/${encodeURIComponent(currentSymbol)}/series?${qs.toString()}`);
  const series = (data.series && data.series[metricId]) ? data.series[metricId] : [];

  metricModalState = {
    table,
    metricId,
    unit: meta.unit || "",
    description: meta.description || "",
    series,
  };
  renderMetricModalCharts();
}

async function renderOverviewCharts(symbol) {
  const defs = [
    { table: "financial_ratios", metric: "roe" },
    { table: "financial_ratios", metric: "price_to_earnings" },
    { table: "financial_ratios", metric: "price_to_book" },
    { table: "financial_ratios", metric: "debt_to_equity" },
    { table: "income_statement", metric: "net_revenue" },
    { table: "income_statement", metric: "net_profit" },
    { table: "cash_flow_statement", metric: "net_cash_from_operating_activities" },
    { table: "balance_sheet", metric: "total_assets" },
  ];

  const byTable = new Map();
  for (const d of defs) {
    if (!byTable.has(d.table)) byTable.set(d.table, []);
    byTable.get(d.table).push(d.metric);
  }

  const chartHtml = [];
  for (const [table, metrics] of byTable.entries()) {
    const tax = await getTaxonomyTable(table);
    const qs = new URLSearchParams({
      table,
      metrics: metrics.join(","),
      period: "yearly",
    });
    const data = await apiGet(`/api/symbol/${encodeURIComponent(symbol)}/series?${qs.toString()}`);

    for (const metricId of metrics) {
      const meta = tax.get(metricId) || { label: metricId, unit: "" };
      const pts = (data.series && data.series[metricId]) ? data.series[metricId] : [];
      const values = pts.map((p) => p.value);
      const last = pts.length ? pts[pts.length - 1].value : null;
      const sub = `${formatValue(last, meta.unit)} ${meta.unit || ""}`.trim();
      chartHtml.push(renderSparklineCard({ title: meta.label, subtitle: sub, values }));
    }
  }

  $("overviewCharts").innerHTML = chartHtml.join("") || `<div class="muted">Không có dữ liệu để vẽ biểu đồ</div>`;
}

async function renderPrice(symbol) {
  const data = await apiGet(`/api/symbol/${encodeURIComponent(symbol)}/price_series?days=160`);
  const pts = data.series || [];
  const values = pts.map((p) => p.close);
  const last = pts.length ? pts[pts.length - 1].close : null;
  const prev = pts.length >= 2 ? pts[pts.length - 2].close : null;
  let delta = "";
  if (Number.isFinite(Number(last)) && Number.isFinite(Number(prev))) {
    const d = Number(last) - Number(prev);
    const pct = prev ? (d / Number(prev)) * 100 : 0;
    delta = `${d >= 0 ? "+" : ""}${nf2.format(d)} (${d >= 0 ? "+" : ""}${nf2.format(pct)}%)`;
  }
  $("priceMeta").textContent = `points=${pts.length} close=${last ?? "-"} ${delta}`;
  $("priceChart").innerHTML = renderSparklineCard({
    title: "Close",
    subtitle: `${last ?? "-"} ${delta}`.trim(),
    values,
  });
}

async function loadAll(symbol) {
  $("status").textContent = "Đang tải...";
  currentSymbol = symbol;
  const meta = await apiGet(`/api/symbol/${encodeURIComponent(symbol)}/meta`);
  $("companyMeta").innerHTML = renderMeta(meta);

  currentPeriods = await apiGet(`/api/symbol/${encodeURIComponent(symbol)}/periods`);
  setYearOptions(currentPeriods);
  updateQuarterOptions(Number($("yearSelect").value));

  const year = $("yearSelect").value ? Number($("yearSelect").value) : null;
  const quarter = $("quarterSelect").value ? Number($("quarterSelect").value) : null;
  const mode = $("modeSelect").value || "both";

  const buildParams = (m) => {
    const params = new URLSearchParams({ mode: m });
    if (year) params.set("year", String(year));
    if (quarter) params.set("quarter", String(quarter));
    return params;
  };

  const industryLabel = meta.icb_name3 ? `ICB3=${meta.icb_name3}` : "ICB3=-";
  $("tables").innerHTML = `<div class="muted">Đang tải bảng chỉ tiêu...</div>`;

  let finIndustry = null;
  let finAll = null;
  if (mode === "both") {
    [finIndustry, finAll] = await Promise.all([
      apiGet(`/api/symbol/${encodeURIComponent(symbol)}/financials?${buildParams("industry").toString()}`),
      apiGet(`/api/symbol/${encodeURIComponent(symbol)}/financials?${buildParams("all").toString()}`),
    ]);
  } else if (mode === "industry") {
    finIndustry = await apiGet(`/api/symbol/${encodeURIComponent(symbol)}/financials?${buildParams("industry").toString()}`);
  } else {
    finAll = await apiGet(`/api/symbol/${encodeURIComponent(symbol)}/financials?${buildParams("all").toString()}`);
  }

  const order = ["financial_ratios", "income_statement", "balance_sheet", "cash_flow_statement"];
  const sections = [];

  if (finIndustry) {
    const tables = finIndustry.tables || {};
    const html = order.filter((k) => k in tables).map((k) => renderTableCard(k, tables[k])).join("");
    sections.push(`
      <div class="table-card">
        <div class="table-card__head">
          <div class="table-card__title">Bảng đặc trưng theo ngành</div>
          <div class="table-card__meta">Industry profile • ${escapeHtml(industryLabel)} • year=${finIndustry.effective.year ?? "-"} q=${finIndustry.effective.quarter ?? "Y"}</div>
        </div>
        ${html || `<div class="muted">Không có dữ liệu</div>`}
      </div>
    `);
  }

  if (finAll) {
    const tables = finAll.tables || {};
    const html = order.filter((k) => k in tables).map((k) => renderTableCard(k, tables[k])).join("");
    sections.push(`
      <div class="table-card">
        <div class="table-card__head">
          <div class="table-card__title">Bảng đầy đủ</div>
          <div class="table-card__meta">All metrics • ${escapeHtml(industryLabel)} • year=${finAll.effective.year ?? "-"} q=${finAll.effective.quarter ?? "Y"}</div>
        </div>
        ${html || `<div class="muted">Không có dữ liệu</div>`}
      </div>
    `);
  }

  $("tables").innerHTML = sections.join("") || `<div class="muted">Không có dữ liệu</div>`;
  $("periodMeta").textContent = `Hiển thị=${mode} • ${industryLabel} • year=${year || "-"} • quarter=${quarter || "Y"}`;

  $("status").textContent = `${meta.ticker} • ${meta.icb_name3 || "Unknown industry"}`;

  try { await renderOverviewCharts(symbol); } catch (_) {}
  try { await renderPrice(symbol); } catch (_) {}
}

function setActiveTab(name) {
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("is-active", b.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("is-active", p.id === `panel-${name}`));
}

function bind() {
  const input = $("symbolInput");
  const btn = $("loadBtn");
  const yearSelect = $("yearSelect");
  const quarterSelect = $("quarterSelect");
  const modeSelect = $("modeSelect");

  document.querySelectorAll(".tab").forEach((b) => {
    b.addEventListener("click", () => setActiveTab(b.dataset.tab));
  });

  $("metricModalClose").addEventListener("click", closeModal);
  $("modalOverlay").addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("metricModal").hidden) closeModal();
  });

  $("metricChartType").addEventListener("change", () => {
    if ($("metricModal").hidden) return;
    try { renderMetricModalCharts(); } catch (_) {}
  });

  $("metricPeriod").addEventListener("change", async () => {
    const modal = $("metricModal");
    if (modal.hidden) return;
    const sub = $("metricModalSub").textContent || "";
    const parts = sub.split(" • ");
    const table = (parts[0] || "").trim();
    const metricId = (parts[1] || "").trim();
    if (table && metricId) {
      try { await showMetricDetail(table, metricId); } catch (_) {}
    }
  });

  $("tables").addEventListener("click", async (e) => {
    const tr = e.target.closest("tr.metric-row");
    if (!tr) return;
    const table = tr.getAttribute("data-table");
    const metricId = tr.getAttribute("data-metric");
    if (!table || !metricId) return;
    try { await showMetricDetail(table, metricId); } catch (err) {
      $("metricChartWrap").innerHTML = `<div class="muted">Lỗi: ${escapeHtml(err.message || String(err))}</div>`;
    }
  });

  input.addEventListener("input", async () => {
    const v = input.value.trim().toUpperCase();
    if (v.length >= 1) {
      try { await refreshDatalist(v); } catch (_) {}
    }
  });

  async function doLoad() {
    const symbol = input.value.trim().toUpperCase();
    if (!symbol) return;
    try {
      await loadAll(symbol);
      history.replaceState(null, "", `/symbol/${encodeURIComponent(symbol)}`);
    } catch (e) {
      $("status").textContent = `Lỗi: ${e.message || e}`;
      $("tables").innerHTML = `<div class="muted">${escapeHtml(e.message || String(e))}</div>`;
    }
  }

  btn.addEventListener("click", doLoad);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doLoad();
  });

  yearSelect.addEventListener("change", () => {
    updateQuarterOptions(Number(yearSelect.value));
    doLoad();
  });
  quarterSelect.addEventListener("change", doLoad);
  modeSelect.addEventListener("change", doLoad);

  const prefill = document.body.getAttribute("data-prefill-symbol") || "";
  if (prefill) {
    input.value = prefill;
    doLoad();
  }
}

window.addEventListener("DOMContentLoaded", bind);
