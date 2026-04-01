/**
 * Main JavaScript - Báo cáo Tài chính
 * Phiên bản: 2.0.0 - Enhanced with Charts, Industry Profiles, Comparison
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const state = {
  currentView: 'dashboard',
  currentSymbol: null,
  // Use 2025 as max year since database has data up to 2025
  currentYear: Math.min(new Date().getFullYear(), 2025),
  currentIndustry: null,
  compareList: [],  // Symbols to compare
  charts: {},       // Chart instances
  industryProfile: null,
  ui: {
    helpTipsBound: false,
    searchBound: false,
    setTabSidebarCollapsed: null,
    isTabSidebarCompact: null,
    chartReflowBound: false,
    valuationResearchBound: false,
    peerDistributionBound: false
  },
  // Metric chart modal state
  metricChart: {
    metric: null,
    table: null,
    label: null,
    unit: null
  }
};

const UI_FEATURES = {
  showDataProvenanceAudit: false
};

const TAB_SIDEBAR_STORAGE_KEY = 'fc.tabs.sidebar.collapsed.v2';

// ============================================================================
// INDUSTRY PROFILES - Match financial_taxonomy.py
// ============================================================================

const INDUSTRY_PROFILES = {
  banks: {
    keywords: ['ngân hàng'],
    metrics: ['price_to_book', 'price_to_earnings', 'eps_vnd', 'bvps_vnd', 'roe', 'roa', 'financial_leverage', 'beta', 'dividend_payout_ratio'],
    keyMetricsShow: ['P/E', 'P/B', 'ROE', 'ROA', 'Fin. Leverage'],
    keyMetricsHide: ['Gross Margin', 'Current Ratio', 'D/E', 'Inventory']
  },
  realEstate: {
    keywords: ['bất động sản'],
    metrics: ['price_to_book', 'price_to_earnings', 'debt_to_equity', 'interest_coverage_ratio', 'current_ratio', 'cash_ratio', 'days_inventory_outstanding', 'cash_conversion_cycle', 'roe', 'net_profit_margin', 'beta'],
    keyMetricsShow: ['P/B', 'D/E', 'Current Ratio', 'ROE', 'Net Margin'],
    keyMetricsHide: []
  },
  manufacturing: {
    keywords: ['xây dựng', 'vật liệu', 'hóa chất', 'kim loại', 'thực phẩm', 'bia', 'đồ uống', 'gia dụng'],
    metrics: ['price_to_earnings', 'ev_to_ebitda', 'gross_margin', 'ebit_margin', 'net_profit_margin', 'asset_turnover', 'days_sales_outstanding', 'cash_conversion_cycle', 'debt_to_equity', 'interest_coverage_ratio', 'beta'],
    keyMetricsShow: ['P/E', 'Gross Margin', 'ROE', 'D/E', 'Asset Turnover'],
    keyMetricsHide: []
  },
  utilities: {
    keywords: ['điện', 'nước', 'khí đốt'],
    metrics: ['ev_to_ebitda', 'price_to_earnings', 'dividend_payout_ratio', 'debt_to_equity', 'interest_coverage_ratio', 'roe', 'beta'],
    keyMetricsShow: ['EV/EBITDA', 'Dividend Payout', 'ROE', 'D/E'],
    keyMetricsHide: ['Gross Margin', 'Inventory']
  },
  tech: {
    keywords: ['phần mềm', 'máy tính', 'viễn thông'],
    metrics: ['price_to_earnings', 'ev_to_ebitda', 'gross_margin', 'ebit_margin', 'roe', 'roic', 'asset_turnover', 'beta'],
    keyMetricsShow: ['P/E', 'Gross Margin', 'ROE', 'ROIC'],
    keyMetricsHide: ['Inventory']
  },
  general: {
    keywords: [],
    metrics: ['price_to_earnings', 'price_to_book', 'ev_to_ebitda', 'roe', 'roa', 'roic', 'gross_margin', 'net_profit_margin', 'debt_to_equity', 'current_ratio', 'cash_conversion_cycle', 'asset_turnover', 'inventory_turnover', 'dividend_payout_ratio'],
    keyMetricsShow: ['P/E', 'P/B', 'ROE', 'ROA', 'D/E'],
    keyMetricsHide: []
  }
};

function detectIndustryProfile(industryName) {
  if (!industryName) return INDUSTRY_PROFILES.general;
  const name = industryName.toLowerCase();

  for (const [key, profile] of Object.entries(INDUSTRY_PROFILES)) {
    if (profile.keywords.some(kw => name.includes(kw))) {
      return profile;
    }
  }
  return INDUSTRY_PROFILES.general;
}

// ============================================================================
// API HELPERS
// ============================================================================

const API = {
  async searchCompanies(query) {
    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    return response.json();
  },

  async getCompany(symbol) {
    const response = await fetch(`/api/company/${symbol}`);
    return response.json();
  },

  async getFinancialRatios(symbol, year) {
    const response = await fetch(`/api/financials/${symbol}/ratios?year=${year}`);
    return response.json();
  },

  async getBalanceSheet(symbol, year) {
    const response = await fetch(`/api/financials/${symbol}/balance?year=${year}`);
    return response.json();
  },

  async getIncomeStatement(symbol, year) {
    const response = await fetch(`/api/financials/${symbol}/income?year=${year}`);
    return response.json();
  },

  async getCashFlow(symbol, year) {
    const response = await fetch(`/api/financials/${symbol}/cashflow?year=${year}`);
    return response.json();
  },

  async getAvailableYears(symbol) {
    const response = await fetch(`/api/financials/${symbol}/years`);
    return response.json();
  },

  async getIndustries() {
    const response = await fetch('/api/industries');
    return response.json();
  },

  async getExchanges() {
    const response = await fetch('/api/exchanges');
    return response.json();
  },

  async getRankings({ sortBy = 'overall', year = null, limit = 50, industry = null, exchange = null } = {}) {
    const params = new URLSearchParams();
    if (sortBy) params.set('sort_by', sortBy);
    if (year !== null && year !== undefined) params.set('year', year);
    if (limit !== null && limit !== undefined) params.set('limit', limit);
    if (industry) params.set('industry', industry);
    if (exchange) params.set('exchange', exchange);
    const qs = params.toString();
    const response = await fetch(`/api/rankings${qs ? `?${qs}` : ''}`);
    return response.json();
  },

  async getRankingsYears() {
    const response = await fetch(`/api/rankings/years`);
    return response.json();
  },

  async getCompaniesByIndustry(industryName) {
    const response = await fetch(`/api/industries/${encodeURIComponent(industryName)}/companies`);
    return response.json();
  },

  async getFinancialHistory(symbol, metrics = 'roe,net_profit_margin,debt_to_equity', years = 5) {
    const response = await fetch(`/api/financials/${symbol}/history?metrics=${metrics}&years=${years}`);
    return response.json();
  },

  async getAnalysis(symbol) {
    const response = await fetch(`/api/analysis/${symbol}`);
    return response.json();
  },

  async getIndustryBenchmark(symbol) {
    const response = await fetch(`/api/industry/benchmark/${symbol}`);
    return response.json();
  },

  async getIndustryBenchmarkForYear(symbol, year) {
    const qs = (year !== null && year !== undefined) ? `?year=${encodeURIComponent(year)}` : '';
    const response = await fetch(`/api/industry/benchmark/${symbol}${qs}`);
    return response.json();
  },

  async getFinancialHistoryBenchmark(symbol, metrics = 'roe,net_profit_margin,debt_to_equity', years = 5) {
    const response = await fetch(`/api/financials/${symbol}/history/benchmark?metrics=${metrics}&years=${years}`);
    return response.json();
  },

  async getValuationAnalysis(symbol, year) {
    const response = await fetch(`/api/valuation/${symbol}?year=${year}`);
    return response.json();
  },

  async getValuationTimeseries(symbol, years = 10) {
    const response = await fetch(`/api/research/valuation/timeseries/${symbol}?years=${encodeURIComponent(years)}`);
    return response.json();
  },

  async getValuationDecomposition(symbol, horizonYears = 5) {
    const response = await fetch(`/api/research/valuation/decomposition/${symbol}?horizon_years=${encodeURIComponent(horizonYears)}`);
    return response.json();
  },

  async getDividendAnalysis(symbol) {
    const response = await fetch(`/api/dividend/${symbol}`);
    return response.json();
  },

  async getEarlyWarning(symbol, year) {
    const response = await fetch(`/api/early-warning/${symbol}?year=${year}`);
    return response.json();
  },

  async getCAGRAnalysis(symbol, years = 5) {
    const response = await fetch(`/api/cagr/${symbol}?years=${years}`);
    return response.json();
  },

  async getMetricSeries(symbol, table, metric, period = 'year', count = 10) {
    const params = new URLSearchParams();
    if (period) params.set('period', period);
    if (count !== null && count !== undefined) params.set('count', count);
    const qs = params.toString();
    const response = await fetch(`/api/financials/${symbol}/series/${table}/${metric}${qs ? `?${qs}` : ''}`);
    return response.json();
  },

  async getRiskAnalysis(symbol, days = 365) {
    const response = await fetch(`/api/financials/${symbol}/risk?days=${days}`);
    return response.json();
  },

  async getTTMFundamentals(symbol, year = null, quarter = null) {
    const params = new URLSearchParams();
    if (year !== null && year !== undefined) params.set('year', year);
    if (quarter !== null && quarter !== undefined) params.set('quarter', quarter);
    const qs = params.toString();
    const response = await fetch(`/api/ttm/${symbol}${qs ? `?${qs}` : ''}`);
    return response.json();
  },

  async getTTMSeries(symbol, count = 12) {
    const response = await fetch(`/api/ttm/${symbol}/series?count=${encodeURIComponent(count)}`);
    return response.json();
  },

  async getPeerScatter(symbol, year, xMetric, yMetric) {
    const params = new URLSearchParams();
    if (year !== null && year !== undefined) params.set('year', year);
    if (xMetric) params.set('x', xMetric);
    if (yMetric) params.set('y', yMetric);
    const qs = params.toString();
    const response = await fetch(`/api/research/peers/scatter/${symbol}${qs ? `?${qs}` : ''}`);
    return response.json();
  },

  async getPeerDistribution(symbol, year, metric, bins = 24) {
    const params = new URLSearchParams();
    if (year !== null && year !== undefined) params.set('year', year);
    if (metric) params.set('metric', metric);
    if (bins) params.set('bins', bins);
    const qs = params.toString();
    const response = await fetch(`/api/research/peers/distribution/${symbol}${qs ? `?${qs}` : ''}`);
    return response.json();
  }
};

// ============================================================================
// UI HELPERS
// ============================================================================

function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('vi-VN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value);
}

function formatCurrency(value, unit = 'tỷ') {
  if (value === null || value === undefined) return '-';
  if (unit === 'tỷ') {
    return formatNumber(value / 1e9, 0) + ' tỷ';
  } else if (unit === 'triệu') {
    return formatNumber(value / 1e6, 0) + ' triệu';
  }
  return formatNumber(value, 0);
}

function formatPercent(value) {
  if (value === null || value === undefined) return '-';
  return (value * 100).toFixed(2) + '%';
}

function formatRatio(value) {
  if (value === null || value === undefined) return '-';
  return value.toFixed(2) + 'x';
}

function isMissing(value) {
  return value === null || value === undefined;
}

function getHealthStatus(score) {
  if (score >= 70) return { emoji: '🟢', text: 'KHỎE', color: '#22c55e' };
  if (score >= 50) return { emoji: '🟡', text: 'TRUNG BÌNH', color: '#f59e0b' };
  return { emoji: '🔴', text: 'YẾU', color: '#ef4444' };
}

// ============================================================================
// CHART HELPERS
// ============================================================================

const CHART_COLORS = {
  roe: '#3b82f6',
  margin: '#22c55e',
  debt: '#f59e0b',
  pe: '#8b5cf6',
  pb: '#ec4899',
  compare1: '#3b82f6',
  compare2: '#22c55e',
  compare3: '#f59e0b',
  compare4: '#ef4444',
  compare5: '#8b5cf6'
};

const CHART_CONFIG = {
  width: 300,
  height: 280  // Increased from 150 for better academic analysis visibility
};

// Metric explanations for enhanced tooltips
const METRIC_EXPLANATIONS = {
  roe: 'ROE (Return on Equity): Hiệu quả sử dụng vốn chủ sở hữu. >15% được coi là tốt.',
  roa: 'ROA (Return on Assets): Hiệu quả sử dụng tài sản. >5% được coi là tốt.',
  net_profit_margin: 'Net Profit Margin: Biên lợi nhuận ròng sau tất cả chi phí.',
  net_margin: 'Net Profit Margin: Biên lợi nhuận ròng sau tất cả chi phí.',
  gross_margin: 'Gross Margin: Biên lợi nhuận gộp, cho thấy hiệu quả sản xuất.',
  debt_to_equity: 'Debt/Equity: Tỷ lệ nợ/vốn chủ sở hữu. <1.0 được coi là an toàn.',
  current_ratio: 'Current Ratio: Khả năng thanh toán ngắn hạn. >1.5 được coi là tốt.',
  asset_turnover: 'Asset Turnover: Hiệu quả sử dụng tài sản tạo doanh thu.',
  eps: 'EPS: Lợi nhuận trên mỗi cổ phiếu (VND).',
  dividend_yield: 'Dividend Yield: Tỷ suất cổ tức hàng năm.',
  pe_ratio: 'P/E Ratio: Giá trên lợi nhuận. <15 được coi là hợp lý tại VN.',
  p_e: 'P/E Ratio: Giá trên lợi nhuận. <15 được coi là hợp lý tại VN.',
  pb_ratio: 'P/B Ratio: Giá trên giá trị sổ sách. <2 được coi là hợp lý.',
  p_b: 'P/B Ratio: Giá trên giá trị sổ sách. <2 được coi là hợp lý.',
  ev_ebitda: 'EV/EBITDA: Giá trị doanh nghiệp trên EBITDA.'
};

function buildHelpTip(title, bodyHtml, ariaLabel = 'Giải thích') {
  return `
    <details class="help-tip">
      <summary aria-label="${ariaLabel}">?</summary>
      <div class="help-tip__content">
        <div class="help-tip__title">${title}</div>
        <div class="help-tip__body">${bodyHtml}</div>
      </div>
    </details>
  `;
}

function setupHelpTips() {
  if (state.ui.helpTipsBound) return;
  state.ui.helpTipsBound = true;

  const closeAll = (except = null) => {
    document.querySelectorAll('details.help-tip[open]').forEach(d => {
      if (except && d === except) return;
      d.removeAttribute('open');
    });
  };

  document.addEventListener('click', (e) => {
    const clicked = e.target.closest ? e.target.closest('details.help-tip') : null;
    if (!clicked) return closeAll();
    return closeAll(clicked);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAll();
  });

  document.addEventListener('toggle', (e) => {
    const details = e.target;
    if (!details || !details.classList || !details.classList.contains('help-tip')) return;
    if (details.hasAttribute('open')) closeAll(details);
  }, true);
}

/**
 * Destroy ALL charts in state.charts to prevent memory leaks
 */
function destroyAllCharts() {
  Object.keys(state.charts).forEach(chartId => {
    if (state.charts[chartId]) {
      state.charts[chartId].destroy();
      delete state.charts[chartId];
    }
  });
}

function destroyChartsByPrefix(prefix) {
  if (!prefix) return;
  Object.keys(state.charts).forEach(chartId => {
    if (!chartId.startsWith(prefix)) return;
    try {
      state.charts[chartId].destroy();
    } catch (e) {
      // Best-effort cleanup
    }
    delete state.charts[chartId];
  });
}

function getCanvasTargetWidth(canvas, fallbackWidth = CHART_CONFIG.width) {
  if (!canvas) return fallbackWidth;
  const parent = canvas.parentElement;
  const measured = parent ? Math.floor(parent.clientWidth) : fallbackWidth;
  if (!Number.isFinite(measured) || measured <= 0) return fallbackWidth;
  return Math.max(220, measured - 2);
}

function applyCanvasDimensions(canvas, height = CHART_CONFIG.height) {
  if (!canvas) return;
  const targetWidth = getCanvasTargetWidth(canvas, CHART_CONFIG.width);
  const targetHeight = Number.isFinite(height) && height > 0 ? Math.floor(height) : CHART_CONFIG.height;

  canvas.width = targetWidth;
  canvas.height = targetHeight;
  canvas.style.width = `${targetWidth}px`;
  canvas.style.height = `${targetHeight}px`;
  canvas.style.maxWidth = '100%';
  canvas.style.maxHeight = `${targetHeight}px`;
}

function reflowVisibleCharts() {
  Object.entries(state.charts).forEach(([chartId, chart]) => {
    if (!chart || typeof chart.resize !== 'function') return;

    const canvas = chart.canvas || document.getElementById(chartId);
    if (!canvas || !document.body.contains(canvas)) return;

    const hiddenPanel = canvas.closest('.tab-content:not(.active)');
    if (hiddenPanel) return;

    const chartHeight = Number(canvas.height) > 0 ? Number(canvas.height) : CHART_CONFIG.height;
    applyCanvasDimensions(canvas, chartHeight);
    chart.resize(canvas.width, canvas.height);
    chart.update('none');
  });
}

function setupChartReflowListeners() {
  if (state.ui.chartReflowBound) return;
  state.ui.chartReflowBound = true;

  let resizeTimer = null;
  window.addEventListener('resize', () => {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      reflowVisibleCharts();
    }, 120);
  });
}

/**
 * Create a trend chart with FIXED dimensions (no responsive mode)
 * Supports industry benchmark comparison (per-year data, not flat line) and 0% baseline
 * Enhanced with ARIA labels and improved tooltips
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} labels - Year labels
 * @param {Array} data - Company data values
 * @param {string} label - Metric label
 * @param {string} color - Chart color
 * @param {Array|number|null} industryBenchmark - Array of benchmark values per year, single value, or null
 */
function createTrendChart(canvasId, labels, data, label, color, industryBenchmark = null, options = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const valueType = options?.valueType || 'percent'; // 'percent' | 'ratio' | 'number'
  const metricKeyOverride = options?.metricKey || null;
  const tooltipDecimals = Number.isInteger(options?.tooltipDecimals)
    ? options.tooltipDecimals
    : (valueType === 'percent' ? 2 : 2);
  const tickDecimals = Number.isInteger(options?.tickDecimals)
    ? options.tickDecimals
    : (valueType === 'percent' ? 1 : 1);
  const unitSuffix = (typeof options?.unitSuffix === 'string')
    ? options.unitSuffix
    : (valueType === 'percent' ? '%' : (valueType === 'ratio' ? 'x' : ''));

  const formatTrendValue = (value, decimals) => {
    if (value === null || value === undefined) return null;
    if (valueType === 'percent') return (value * 100).toFixed(decimals) + '%';
    if (valueType === 'ratio') return value.toFixed(decimals) + 'x';
    if (valueType === 'currency') return formatNumber(value / 1e9, decimals) + ' tỷ';
    const base = formatNumber(value, decimals);
    return unitSuffix ? `${base}${unitSuffix}` : base;
  };

  // Destroy existing chart for this canvas
  if (state.charts[canvasId]) {
    state.charts[canvasId].destroy();
    delete state.charts[canvasId];
  }

  applyCanvasDimensions(canvas, CHART_CONFIG.height);

  // Add ARIA label for accessibility
  const metricKey = (metricKeyOverride || label.toLowerCase().replace(/[^a-z_]/g, '_')).toLowerCase();
  const explanation = METRIC_EXPLANATIONS[metricKey] || `${label}: Chỉ số tài chính`;
  canvas.setAttribute('aria-label', `Biểu đồ xu hướng ${label} qua ${labels.length} năm. ${explanation}`);
  canvas.setAttribute('role', 'img');

  // Build datasets - preserve null/undefined for gaps in chart
  const datasets = [{
    label: label,
    data: data,
    borderColor: color,
    backgroundColor: color + '20',
    fill: true,
    tension: 0.4,
    pointRadius: 4,
    pointHoverRadius: 6,
    spanGaps: false  // Don't connect lines across null/undefined values
  }];

  // Add baseline reference line (dashed) at 0
  const zeroLineData = new Array(labels.length).fill(0);
  const baselineLabel = 'Baseline (0)';
  datasets.push({
    label: baselineLabel,
    data: zeroLineData,
    borderColor: 'rgba(156, 163, 175, 0.6)',
    backgroundColor: 'transparent',
    borderDash: [3, 3],
    borderWidth: 1,
    pointRadius: 0,
    pointHoverRadius: 0,
    fill: false,
    tension: 0
  });

  // Add industry benchmark line if available
  // Support both: array of per-year values (NEW) or single value (LEGACY)
  if (industryBenchmark !== null && industryBenchmark !== undefined) {
    let industryData;
    let showPoints = false;

    if (Array.isArray(industryBenchmark)) {
      // NEW: Per-year benchmark data (historical)
      industryData = industryBenchmark;
      showPoints = true; // Show points for historical benchmark
    } else {
      // LEGACY: Single flat value (backward compatibility)
      industryData = new Array(labels.length).fill(industryBenchmark);
    }

    datasets.push({
      label: 'Trung vị ngành (Median)',
      data: industryData,
      borderColor: 'rgba(249, 115, 22, 1)',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: showPoints ? 3 : 0,  // Show points only for historical data
      pointHoverRadius: 4,
      fill: false,
      tension: 0.3,  // Slight curve for historical benchmark
      spanGaps: false  // Don't connect across missing years
    });
  }

  const chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      // CRITICAL: Turn off responsive to prevent expansion loops
      responsive: false,
      maintainAspectRatio: true,
      layout: {
        padding: { left: 8, right: 12, top: 4, bottom: 0 }
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'start',
          labels: {
            color: '#9ca3af',
            font: { size: 11 },
            usePointStyle: true,
            boxWidth: 6,
            filter: function (item) {
              // Hide baseline from legend
              return item.text !== baselineLabel;
            }
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          titleColor: '#f3f4f6',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 12,
          displayColors: true,
          callbacks: {
            title: function (context) {
              return `Năm ${context[0].label}`;
            },
            label: function (context) {
              let datasetLabel = context.dataset.label || '';
              // Skip baseline in tooltip
              if (datasetLabel === baselineLabel) return null;
              if (datasetLabel) {
                datasetLabel += ': ';
              }
              // Handle missing data
              if (context.parsed.y === null) {
                return datasetLabel + 'Không có dữ liệu năm này';
              }
              const formatted = formatTrendValue(context.parsed.y, tooltipDecimals);
              datasetLabel += formatted ?? 'N/A';
              return datasetLabel;
            },
            afterBody: function (context) {
              // Add explanation for the main metric
              if (context.length > 0) {
                const explanation = METRIC_EXPLANATIONS[metricKey];
                if (explanation) {
                  return ['', '💡 ' + explanation];
                }
              }
              return [];
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#374151' },
          ticks: { color: '#9ca3af' }
        },
        y: {
          grid: { color: '#374151' },
          ticks: {
            color: '#9ca3af',
            callback: value => formatTrendValue(value, tickDecimals) ?? ''
          }
        }
      },
      // Animation for smoother transitions
      animation: {
        duration: 500,
        easing: 'easeOutQuart'
      }
    }
  });

  state.charts[canvasId] = chart;
  return chart;
}

/**
 * Create a multi-line trend chart with consistent formatting and missing-data honesty.
 */
function createMultiLineTrendChart(canvasId, labels, datasetsConfig, options = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  if (state.charts[canvasId]) {
    state.charts[canvasId].destroy();
    delete state.charts[canvasId];
  }

  const valueType = options?.valueType || 'number'; // 'percent' | 'ratio' | 'number' | 'currency'
  const tooltipDecimals = Number.isInteger(options?.tooltipDecimals) ? options.tooltipDecimals : (valueType === 'percent' ? 2 : 2);
  const tickDecimals = Number.isInteger(options?.tickDecimals) ? options.tickDecimals : (valueType === 'percent' ? 1 : 1);
  const unitSuffix = (typeof options?.unitSuffix === 'string')
    ? options.unitSuffix
    : (valueType === 'percent' ? '%' : (valueType === 'ratio' ? 'x' : (valueType === 'currency' ? ' tỷ' : '')));

  const formatTrendValue = (value, decimals) => {
    if (value === null || value === undefined) return null;
    if (valueType === 'percent') return (value * 100).toFixed(decimals) + '%';
    if (valueType === 'ratio') return Number(value).toFixed(decimals) + 'x';
    if (valueType === 'currency') return formatNumber(Number(value) / 1e9, decimals) + ' tỷ';
    const base = formatNumber(Number(value), decimals);
    return unitSuffix ? `${base}${unitSuffix}` : base;
  };

  applyCanvasDimensions(canvas, CHART_CONFIG.height);

  const baselineLabel = 'Baseline (0)';
  const datasets = (Array.isArray(datasetsConfig) ? datasetsConfig : []).map(cfg => {
    const borderColor = cfg.color || '#3b82f6';
    const bg = cfg.backgroundColor !== undefined ? cfg.backgroundColor : (cfg.fill ? (borderColor + '15') : 'transparent');
    return {
      label: cfg.label || '',
      data: cfg.data || [],
      borderColor: borderColor,
      backgroundColor: bg,
      fill: cfg.fill ?? false,
      tension: (typeof cfg.tension === 'number') ? cfg.tension : 0.35,
      borderWidth: (typeof cfg.borderWidth === 'number') ? cfg.borderWidth : 2,
      pointRadius: (typeof cfg.pointRadius === 'number') ? cfg.pointRadius : 3,
      pointHoverRadius: (typeof cfg.pointHoverRadius === 'number') ? cfg.pointHoverRadius : 5,
      spanGaps: false,
      borderDash: cfg.dashed ? [4, 3] : undefined,
      _hideLegend: Boolean(cfg.hideFromLegend),
    };
  });

  if (options?.showBaseline) {
    datasets.unshift({
      label: baselineLabel,
      data: new Array(labels.length).fill(0),
      borderColor: 'rgba(156, 163, 175, 0.6)',
      backgroundColor: 'transparent',
      borderDash: [3, 3],
      borderWidth: 1,
      pointRadius: 0,
      pointHoverRadius: 0,
      fill: false,
      tension: 0,
      spanGaps: false,
      _hideLegend: true,
    });
  }

  const chart = new Chart(canvas, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: false,
      maintainAspectRatio: true,
      layout: {
        padding: { left: 8, right: 12, top: 4, bottom: 0 }
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'start',
          labels: {
            color: '#9ca3af',
            font: { size: 11 },
            usePointStyle: true,
            boxWidth: 6,
            filter: function (item, data) {
              const ds = data?.datasets?.[item.datasetIndex];
              if (ds && ds._hideLegend) return false;
              return item.text !== baselineLabel;
            }
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          titleColor: '#f3f4f6',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 12,
          displayColors: true,
          callbacks: {
            title: function (context) {
              return context?.[0]?.label ? `${context[0].label}` : '';
            },
            label: function (context) {
              const datasetLabel = context.dataset.label || '';
              if (context.parsed.y === null) return datasetLabel ? `${datasetLabel}: Không có dữ liệu` : 'Không có dữ liệu';
              const formatted = formatTrendValue(context.parsed.y, tooltipDecimals);
              return datasetLabel ? `${datasetLabel}: ${formatted ?? 'N/A'}` : (formatted ?? 'N/A');
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#374151' },
          ticks: { color: '#9ca3af' }
        },
        y: {
          grid: { color: '#374151' },
          ticks: {
            color: '#9ca3af',
            callback: value => formatTrendValue(value, tickDecimals) ?? ''
          }
        }
      },
      animation: { duration: 500, easing: 'easeOutQuart' }
    }
  });

  state.charts[canvasId] = chart;
  return chart;
}

function createValuationBandChart(canvasId, labels, companySeries, band, options = {}) {
  const p25 = !isMissing(band?.p25) ? Number(band.p25) : null;
  const p50 = !isMissing(band?.p50) ? Number(band.p50) : null;
  const p75 = !isMissing(band?.p75) ? Number(band.p75) : null;

  const p25Line = new Array(labels.length).fill(p25);
  const p75Line = new Array(labels.length).fill(p75);
  const p50Line = new Array(labels.length).fill(p50);

  const companyColor = options?.companyColor || '#3b82f6';
  const bandFill = options?.bandFill || 'rgba(59, 130, 246, 0.10)';

  return createMultiLineTrendChart(
    canvasId,
    labels,
    [
      { label: 'P25', data: p25Line, color: 'rgba(0,0,0,0)', borderWidth: 0, pointRadius: 0, hideFromLegend: true, fill: false },
      { label: 'P75', data: p75Line, color: 'rgba(0,0,0,0)', borderWidth: 0, pointRadius: 0, hideFromLegend: true, fill: '-1', backgroundColor: bandFill },
      { label: 'P50 (Median)', data: p50Line, color: 'rgba(249, 115, 22, 1)', dashed: true, borderWidth: 2, pointRadius: 0 },
      { label: options?.companyLabel || 'Company', data: companySeries, color: companyColor, borderWidth: 2, pointRadius: 3, fill: false },
    ],
    { valueType: 'ratio', showBaseline: false, tickDecimals: 1, tooltipDecimals: 2 }
  );
}

function createSimpleBarChart(canvasId, labels, data, options = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  if (state.charts[canvasId]) {
    state.charts[canvasId].destroy();
    delete state.charts[canvasId];
  }

  applyCanvasDimensions(canvas, CHART_CONFIG.height);

  const valueType = options?.valueType || 'number';
  const unitSuffix = options?.unitSuffix || '';
  const decimals = Number.isInteger(options?.decimals) ? options.decimals : 1;

  const fmt = (v) => {
    if (v === null || v === undefined) return 'N/A';
    if (valueType === 'percent') return (Number(v) * 100).toFixed(decimals) + '%';
    const base = formatNumber(Number(v), decimals);
    return unitSuffix ? `${base}${unitSuffix}` : base;
  };

  const chart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: options?.label || '',
        data: Array.isArray(data) ? data : [],
        backgroundColor: options?.colors || options?.color || 'rgba(59, 130, 246, 0.6)',
        borderColor: options?.borderColors || options?.borderColor || 'rgba(59, 130, 246, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: false,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (context) {
              return fmt(context.parsed.y);
            }
          }
        }
      },
      scales: {
        x: { grid: { color: '#374151' }, ticks: { color: '#9ca3af', maxRotation: 0 } },
        y: { grid: { color: '#374151' }, ticks: { color: '#9ca3af', callback: value => fmt(value) } }
      },
      animation: { duration: 500, easing: 'easeOutQuart' }
    }
  });

  state.charts[canvasId] = chart;
  return chart;
}

// ============================================================================
// RENDER FUNCTIONS
// ============================================================================

function renderDashboard() {
  // Clean up any existing charts before switching views
  destroyAllCharts();

  const template = document.getElementById('dashboardTemplate');
  const content = template.content.cloneNode(true);
  const mainContent = document.getElementById('mainContent');

  mainContent.innerHTML = '';
  mainContent.appendChild(content);

  loadIndustries();

  const openRankingsBtn = document.getElementById('openRankingsBtn');
  if (openRankingsBtn) {
    openRankingsBtn.addEventListener('click', () => navigateToRankings());
  }
}

function bandToLabel(type, band) {
  if (type === 'valuation') {
    if (band === 'cheap') return 'Rẻ';
    if (band === 'fair') return 'Hợp lý';
    if (band === 'expensive') return 'Đắt';
    return 'N/A';
  }
  if (type === 'growth') {
    if (band === 'high') return 'Cao';
    if (band === 'medium') return 'TB';
    if (band === 'low') return 'Thấp';
    return 'N/A';
  }
  return 'N/A';
}

function renderRankingsBadge(type, band) {
  const span = document.createElement('span');
  span.className = `rating-badge ${band || ''}`.trim();
  span.textContent = bandToLabel(type, band);
  return span;
}

async function renderRankings() {
  destroyAllCharts();
  state.currentView = 'rankings';

  const template = document.getElementById('rankingsTemplate');
  const content = template.content.cloneNode(true);
  const mainContent = document.getElementById('mainContent');

  mainContent.innerHTML = '';
  mainContent.appendChild(content);

  const yearSelect = document.getElementById('rankingsYear');
  const sortSelect = document.getElementById('rankingsSort');
  const industrySelect = document.getElementById('rankingsIndustry');
  const refreshBtn = document.getElementById('rankingsRefreshBtn');
  const subtitle = document.getElementById('rankingsSubtitle');
  const meta = document.getElementById('rankingsMeta');
  const tbody = document.getElementById('rankingsTableBody');
  const exchangeSelect = document.getElementById('rankingsExchange');

  // Populate years dropdown
  try {
    const yearsData = await API.getRankingsYears();
    if (yearSelect && yearsData.years) {
      const cur = new Date().getFullYear();
      const options = yearsData.years.map(y => {
        const label = y === cur ? `${y} (giá mới nhất)` : `${y}`;
        return `<option value="${y}">${label}</option>`;
      });
      yearSelect.innerHTML = options.join('');
      // choose a sensible default: use the value provided by the API if available
      if (yearsData.default_year != null && yearsData.years.includes(yearsData.default_year)) {
        yearSelect.value = yearsData.default_year;
      } else if (yearsData.years.length > 0) {
        yearSelect.value = yearsData.years[0];
      }
    }
  } catch (e) {
    console.warn('Failed to load years for rankings:', e);
  }

  // Populate industries dropdown
  try {
    const industries = await API.getIndustries();
    if (industrySelect) {
      const options = [`<option value="">Tất cả ngành</option>`].concat(
        (industries || []).map(i => `<option value="${i.name}">${i.name} (${i.count || 0})</option>`)
      );
      industrySelect.innerHTML = options.join('');
    }
  } catch (e) {
    console.warn('Failed to load industries for rankings:', e);
  }

  // Populate exchanges dropdown
  try {
    const exchanges = await API.getExchanges();
    if (exchangeSelect) {
      const options = [`<option value="">Tất cả sàn</option>`].concat(
        (exchanges || []).map(e => `<option value="${e.name}">${e.name}</option>`)
      );
      exchangeSelect.innerHTML = options.join('');
    }
  } catch (e) {
    console.warn('Failed to load exchanges for rankings:', e);
  }

  const load = async () => {
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="13" style="padding: var(--space-6); color: var(--text-secondary);">Đang tải...</td></tr>`;
    if (meta) meta.textContent = '';
    if (subtitle) subtitle.textContent = 'Đang tải dữ liệu...';

    try {
      const year = yearSelect ? (yearSelect.value ? parseInt(yearSelect.value) : null) : null;
      const sortBy = sortSelect ? sortSelect.value : 'overall';
      const industry = industrySelect ? industrySelect.value : '';
      const exchange = exchangeSelect ? exchangeSelect.value : '';
      const data = await API.getRankings({ 
        year, 
        sortBy, 
        limit: 50, 
        industry: industry || null, 
        exchange: exchange || null 
      });

      if (data && data.detail) {
        throw new Error(data.detail);
      }

      const responseYear = data?.year;
      const counts = data?.counts || {};
      const items = Array.isArray(data?.items) ? data.items : [];
      // if year == current year we used latest price
      let subtitleLabel = `FY${responseYear}`;
      if (data?.used_latest_price) subtitleLabel = 'Giá mới nhất';

      if (subtitle) {
        const sortLabel = sortBy === 'valuation' ? 'Định giá' : sortBy === 'growth' ? 'Tăng trưởng' : 'Tổng hợp';
        subtitle.textContent = `${subtitleLabel} • Sắp xếp: ${sortLabel} • Nhấn vào 1 dòng để mở chi tiết`;
      }

      if (meta) {
        const eligible = counts.eligible ?? '-';
        const universe = counts.universe ?? '-';
        meta.textContent = `Universe: ${universe} • Eligible: ${eligible} • Hiển thị: ${items.length}`;
      }

      tbody.innerHTML = '';
      if (items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="13" style="padding: var(--space-6); color: var(--text-secondary);">Không có dữ liệu.</td></tr>`;
        return;
      }

      for (const item of items) {
        const tr = document.createElement('tr');
        tr.className = 'rankings-row';
        tr.addEventListener('click', () => navigateToCompany(item.ticker));

        const valuation = item.valuation || {};
        const growth = item.growth || {};
        const scores = item.scores || {};

        const cells = [
          { text: item.rank ?? '', className: '' },
          { text: item.ticker ?? '', className: '' },
          { text: item.name ?? '', className: '' },
          { text: item.industry ?? '', className: '' },
          { text: item.exchanges ?? '', className: '' },
          { text: scores.valuation !== null && scores.valuation !== undefined ? formatNumber(scores.valuation, 1) : '-', className: 'number' },
          { node: renderRankingsBadge('valuation', valuation.band), className: '' },
          { text: valuation.pe !== null && valuation.pe !== undefined ? formatRatio(Number(valuation.pe)) : '-', className: 'number' },
          { text: valuation.pb !== null && valuation.pb !== undefined ? formatRatio(Number(valuation.pb)) : '-', className: 'number' },
          { text: scores.growth !== null && scores.growth !== undefined ? formatNumber(scores.growth, 1) : '-', className: 'number' },
          { node: renderRankingsBadge('growth', growth.band), className: '' },
          { text: growth.eps_cagr_5y !== null && growth.eps_cagr_5y !== undefined ? formatPercent(Number(growth.eps_cagr_5y)) : '-', className: 'number' },
          { text: growth.roe !== null && growth.roe !== undefined ? formatPercent(Number(growth.roe)) : '-', className: 'number' }
        ];

        for (const c of cells) {
          const td = document.createElement('td');
          if (c.className) td.className = c.className;
          if (c.node) td.appendChild(c.node);
          else td.textContent = String(c.text);
          tr.appendChild(td);
        }

        tbody.appendChild(tr);
      }
    } catch (e) {
      console.error('Rankings load failed:', e);
      tbody.innerHTML = `<tr><td colspan="13" style="padding: var(--space-6); color: var(--text-secondary);">Lỗi tải dữ liệu xếp hạng.</td></tr>`;
      if (subtitle) subtitle.textContent = 'Không thể tải dữ liệu.';
      if (meta) meta.textContent = (e && e.message) ? String(e.message) : '';
    }
  };

  refreshBtn?.addEventListener('click', load);
  yearSelect?.addEventListener('change', load);
  sortSelect?.addEventListener('change', load);
  industrySelect?.addEventListener('change', load);
  exchangeSelect?.addEventListener('change', load);

  await load();
}

function populatePeriodSelect(years, selectedYear) {
  const select = document.getElementById('periodSelect');
  if (!select) return;

  const parsed = (Array.isArray(years) ? years : [])
    .map(y => Number(y))
    .filter(y => Number.isFinite(y) && y >= 1990 && y <= 2100)
    .sort((a, b) => b - a);

  const uniqueYears = Array.from(new Set(parsed));

  if (uniqueYears.length > 0) {
    // Keep dropdown practical; show the most recent years first.
    const yearsToShow = uniqueYears.slice(0, 15);
    select.innerHTML = yearsToShow.map(y => `<option value="${y}">${y}</option>`).join('');
  }

  if (Number.isFinite(Number(selectedYear))) {
    select.value = String(selectedYear);
  }
}

async function renderCompanyDetail(symbol) {
  // Clean up any existing charts before switching views
  destroyAllCharts();

  state.currentSymbol = symbol;
  state.currentView = 'company';
  state.compareList = [symbol]; // Reset compare list with current symbol

  const template = document.getElementById('companyDetailTemplate');
  const content = template.content.cloneNode(true);
  const mainContent = document.getElementById('mainContent');

  mainContent.innerHTML = '';
  mainContent.appendChild(content);

  showLoading();

  try {
    const [company, analysis, yearsInfo] = await Promise.all([
      API.getCompany(symbol),
      API.getAnalysis(symbol).catch(() => null) // Analysis might fail for some companies
      ,
      API.getAvailableYears(symbol).catch(() => null)
    ]);

    const availableYears = Array.isArray(yearsInfo?.years) ? yearsInfo.years.map(y => Number(y)).filter(y => Number.isFinite(y)) : [];
    let effectiveYear = Number(state.currentYear);

    if (availableYears.length > 0) {
      if (!availableYears.includes(effectiveYear)) {
        const latest = Number.isFinite(Number(yearsInfo?.latest_year)) ? Number(yearsInfo.latest_year) : availableYears[0];
        effectiveYear = latest;
      }
    }

    // Keep state + UI in sync with DB reality.
    if (Number.isFinite(effectiveYear)) {
      state.currentYear = effectiveYear;
    }
    populatePeriodSelect(availableYears, state.currentYear);

    const [ratios, balance, income, cashflow] = await Promise.all([
      API.getFinancialRatios(symbol, state.currentYear),
      API.getBalanceSheet(symbol, state.currentYear),
      API.getIncomeStatement(symbol, state.currentYear),
      API.getCashFlow(symbol, state.currentYear),
    ]);

    // Detect industry profile
    state.currentIndustry = company.industry;
    state.industryProfile = detectIndustryProfile(company.industry);

    // Update header
    document.getElementById('companyTicker').textContent = symbol;
    document.getElementById('companyName').textContent = company.name || symbol;
    document.getElementById('companyIndustry').textContent = company.industry || 'N/A';
    document.getElementById('companyExchange').textContent = company.exchange || 'N/A';

    // Calculate and render health score
    renderHealthScore(ratios, state.industryProfile);

    // Render key metrics (industry-specific) - needs to be async for peer data
    await renderKeyMetrics(symbol, ratios, company.industry, state.industryProfile);

    // Render Cash Flow Quality card
    if (analysis && analysis.analysis && analysis.analysis.cash_flow_quality) {
      renderCashFlowQualityCard(analysis.analysis.cash_flow_quality);
    }

    // Render Quality Flags Panel (aggregates all quality indicators)
    if (analysis && analysis.analysis) {
      renderQualityFlags(analysis.analysis, ratios);
    }

    // Render data provenance / annual selection audit panel
    if (UI_FEATURES.showDataProvenanceAudit) {
      renderDataProvenance(ratios, balance, income, cashflow, analysis);
    } else {
      const provenanceCard = document.getElementById('dataProvenanceCard');
      if (provenanceCard) provenanceCard.style.display = 'none';
    }

    // Render Percentile Ranking
    renderPercentileRanking(symbol);

    // Render Valuation Analysis
    await renderValuationAnalysis(symbol, state.currentYear);

    // Render CAGR Analysis
    await renderCAGRAnalysis(symbol, 5);

    // Render Altman Z-Score
    if (analysis && analysis.analysis && analysis.analysis.altman_z_score) {
      await renderAltmanZScore(analysis.analysis.altman_z_score, company.industry);
    }

    // Render tables
    renderBalanceSheet(balance);
    renderIncomeStatement(income);
    renderCashFlow(cashflow);
    renderRatios(ratios, state.industryProfile);

    // Load and render charts
    await loadTrendCharts(symbol);

    // Render DuPont Analysis
    renderDuPontAnalysis(ratios);

    // Render Working Capital Efficiency
    renderWorkingCapitalEfficiency(ratios);

    // Setup tabs
    setupTabs();

    // Setup period selector
    const periodSelect = document.getElementById('periodSelect');
    if (periodSelect) periodSelect.value = String(state.currentYear);
    periodSelect?.addEventListener('change', (e) => {
      state.currentYear = parseInt(e.target.value, 10);
      renderCompanyDetail(symbol);
    });

    // Setup comparison
    setupComparison(symbol);

  } catch (error) {
    console.error('Error loading company data:', error);
    showError('Không thể tải dữ liệu công ty');
  }
}

function renderHealthScore(ratios, profile) {
  let score = 50;
  const weights = { roe: 25, margin: 20, leverage: 20, liquidity: 15, efficiency: 20 };

  // ROE (0-25 points)
  if (ratios.roe) {
    if (ratios.roe >= 0.20) score += 25;
    else if (ratios.roe >= 0.15) score += 20;
    else if (ratios.roe >= 0.10) score += 15;
    else if (ratios.roe >= 0.05) score += 10;
    else score += 5;
  }

  // Margin (0-20 points)
  if (ratios.gross_margin) {
    if (ratios.gross_margin >= 0.30) score += 20;
    else if (ratios.gross_margin >= 0.20) score += 15;
    else if (ratios.gross_margin >= 0.10) score += 10;
  } else if (ratios.net_profit_margin) {
    // For banks, use net margin instead
    if (ratios.net_profit_margin >= 0.30) score += 20;
    else if (ratios.net_profit_margin >= 0.20) score += 15;
    else if (ratios.net_profit_margin >= 0.10) score += 10;
  }

  // Leverage (0-20 points) - lower is better
  if (ratios.debt_to_equity !== null && ratios.debt_to_equity !== undefined) {
    if (ratios.debt_to_equity <= 0.5) score += 20;
    else if (ratios.debt_to_equity <= 1.0) score += 15;
    else if (ratios.debt_to_equity <= 2.0) score += 10;
    else score += 5;
  } else if (ratios.financial_leverage) {
    // For banks, use financial leverage
    if (ratios.financial_leverage <= 10) score += 20;
    else if (ratios.financial_leverage <= 15) score += 15;
    else score += 10;
  }

  // Liquidity (0-15 points)
  if (ratios.current_ratio) {
    if (ratios.current_ratio >= 2.0) score += 15;
    else if (ratios.current_ratio >= 1.5) score += 12;
    else if (ratios.current_ratio >= 1.0) score += 8;
  }

  score = Math.min(100, Math.max(0, score));

  const status = getHealthStatus(score);
  document.getElementById('healthScore').innerHTML = `${score}<span style="font-size: var(--text-xl);">/100</span>`;
  document.getElementById('scoreStatus').textContent = `${status.emoji} ${status.text}`;
  document.getElementById('scoreBar').style.width = `${score}%`;
  document.getElementById('scoreBar').style.background = `linear-gradient(90deg, ${status.color}, #3b82f6)`;

  // Sub-scores - hide boxes if data not available
  const profitabilityBox = document.getElementById('scoreProfitabilityBox');
  const efficiencyBox = document.getElementById('scoreEfficiencyBox');
  const structureBox = document.getElementById('scoreStructureBox');
  const liquidityBox = document.getElementById('scoreLiquidityBox');

  if (ratios.roe !== null && ratios.roe !== undefined) {
    document.getElementById('scoreProfitability').textContent = formatPercent(ratios.roe);
  } else if (profitabilityBox) {
    profitabilityBox.style.display = 'none';
  }

  if (ratios.asset_turnover !== null && ratios.asset_turnover !== undefined) {
    document.getElementById('scoreEfficiency').textContent = formatRatio(ratios.asset_turnover);
  } else if (efficiencyBox) {
    efficiencyBox.style.display = 'none';
  }

  if (ratios.debt_to_equity !== null && ratios.debt_to_equity !== undefined) {
    document.getElementById('scoreStructure').textContent = formatRatio(ratios.debt_to_equity);
  } else if (ratios.financial_leverage !== null && ratios.financial_leverage !== undefined) {
    document.getElementById('scoreStructure').textContent = formatRatio(ratios.financial_leverage);
  } else if (structureBox) {
    structureBox.style.display = 'none';
  }

  if (ratios.current_ratio !== null && ratios.current_ratio !== undefined) {
    document.getElementById('scoreLiquidity').textContent = ratios.current_ratio.toFixed(2);
  } else if (liquidityBox) {
    liquidityBox.style.display = 'none';
  }
}

async function renderKeyMetrics(symbol, ratios, industry, profile) {
  // Fetch peer benchmark data for percentile-based badges
  let peerBenchmark = null;
  try {
    peerBenchmark = await API.getIndustryBenchmark(symbol);
  } catch (error) {
    console.warn('Could not load peer benchmark for key metrics:', error);
  }

  // Build metrics based on industry profile
  const allMetrics = [
    { id: 'P/E', key: 'price_to_earnings', format: 'number', invert: true },
    { id: 'P/B', key: 'price_to_book', format: 'number', invert: true },
    { id: 'ROE', key: 'roe', format: 'percent', invert: false },
    { id: 'ROA', key: 'roa', format: 'percent', invert: false },
    { id: 'D/E', key: 'debt_to_equity', format: 'ratio', invert: true },
    { id: 'Gross Margin', key: 'gross_margin', format: 'percent', invert: false },
    { id: 'Net Margin', key: 'net_profit_margin', format: 'percent', invert: false },
    { id: 'Current Ratio', key: 'current_ratio', format: 'ratio', invert: false },
    { id: 'Fin. Leverage', key: 'financial_leverage', format: 'ratio', invert: true },
    { id: 'Asset Turnover', key: 'asset_turnover', format: 'ratio', invert: false },
    { id: 'EV/EBITDA', key: 'ev_to_ebitda', format: 'number', invert: true },
    { id: 'EPS (VND)', key: 'eps_vnd', format: 'currency', invert: false }
  ];

  // Filter based on profile
  const showMetrics = allMetrics.filter(m => {
    if (profile.keyMetricsHide.includes(m.id)) return false;
    return ratios[m.key] !== null && ratios[m.key] !== undefined;
  }).slice(0, 8); // Max 8 metrics

  const metricsHtml = showMetrics.map(m => {
    const value = ratios[m.key];
    let displayValue = '-';
    let badgeHtml = '';

    if (value !== null && value !== undefined) {
      switch (m.format) {
        case 'percent': displayValue = formatPercent(value); break;
        case 'ratio': displayValue = formatRatio(value); break;
        case 'currency': displayValue = formatNumber(value, 0); break;
        default: displayValue = formatNumber(value, 2);
      }

      // Badge logic based on peer percentiles if available
      if (peerBenchmark && peerBenchmark.company_vs_industry && peerBenchmark.company_vs_industry[m.key]) {
        const metricData = peerBenchmark.company_vs_industry[m.key];
        const percentile = metricData.percentile;

        if (percentile !== null && percentile !== undefined) {
          let badgeClass = 'bad';
          let badgeText = '❌';

          // For inverted metrics (lower is better), adjust percentile
          const adjustedPercentile = m.invert ? (100 - percentile) : percentile;

          if (adjustedPercentile >= 75) {
            badgeClass = 'good';
            badgeText = '✅ Top 25%';
          } else if (adjustedPercentile >= 50) {
            badgeClass = 'warning';
            badgeText = '⚠️ Top 50%';
          } else if (adjustedPercentile >= 25) {
            badgeClass = 'warning';
            badgeText = '⚠️ Top 75%';
          } else {
            badgeClass = 'bad';
            badgeText = '❌ Kém';
          }

          badgeHtml = `<div class="metric-badge ${badgeClass}">${badgeText}</div>`;
        }
      } else {
        // Fallback to basic value display if no peer data
        badgeHtml = `<div style="font-size: var(--text-xs); color: var(--text-tertiary);">Không có dữ liệu ngành</div>`;
      }
    }

    return `
      <div class="metric-card">
        <div class="metric-label">${m.id}</div>
        <div class="metric-value">${displayValue}</div>
        ${badgeHtml}
      </div>
    `;
  }).join('');

  document.getElementById('keyMetrics').innerHTML = metricsHtml;
}

async function loadTrendCharts(symbol) {
  try {
    // Fetch historical data and historical industry benchmarks in parallel
    const [history, benchmarkHistory, valuationTs] = await Promise.all([
      API.getFinancialHistory(symbol, 'roe,net_profit_margin', 5),
      API.getFinancialHistoryBenchmark(symbol, 'roe,net_profit_margin', 5)
        .catch(() => null) // Gracefully handle missing industry data
      ,
      API.getValuationTimeseries(symbol, 5).catch(() => null)
    ]);

    function setTrendChartMeta(metaElementId, years, values, benchmarkSeries) {
      const el = document.getElementById(metaElementId);
      if (!el) return;

      if (!Array.isArray(years) || years.length === 0) {
        el.textContent = 'Không có dữ liệu';
        return;
      }

      const firstYear = years[0];
      const lastYear = years[years.length - 1];
      const nonMissing = Array.isArray(values) ? values.filter(v => !isMissing(v)).length : 0;
      const missingCount = years.length - nonMissing;

      const parts = [
        `FY ${firstYear}–${lastYear}`,
        `n=${nonMissing}/${years.length}`,
      ];
      if (missingCount > 0) parts.push(`missing=${missingCount}`);

      if (Array.isArray(benchmarkSeries)) {
        const latest = benchmarkSeries.find(b => b.year === lastYear);
        const peerCount = latest?.peer_count;
        if (typeof peerCount === 'number') {
          parts.push(`peers(FY${lastYear})=${peerCount}`);
        }
      }

      el.textContent = parts.join(' · ');
    }

    if (history.years && history.years.length > 0) {
      const labels = history.years.map(y => y.toString());

      // Extract historical industry benchmarks from the API response
      // The API returns { benchmarks: { roe: [{year: 2020, median: 0.15}, ...], ... } }
      const industryRoeHistory = benchmarkHistory?.benchmarks?.roe || [];
      const industryMarginHistory = benchmarkHistory?.benchmarks?.net_profit_margin || [];

      // Convert to array of medians matching the years
      const industryRoeData = labels.map((yearLabel, index) => {
        const year = parseInt(yearLabel);
        const benchmark = industryRoeHistory.find(b => b.year === year);
        return benchmark?.median ?? null;
      });

      const industryMarginData = labels.map((yearLabel, index) => {
        const year = parseInt(yearLabel);
        const benchmark = industryMarginHistory.find(b => b.year === year);
        return benchmark?.median ?? null;
      });

      // ROE Chart with historical industry benchmark
      const roeData = history.metrics.roe?.map(d => d.value) || [];
      if (roeData.length > 0) {
        createTrendChart('chartROE', labels, roeData, 'ROE', CHART_COLORS.roe, industryRoeData, { valueType: 'percent', metricKey: 'roe' });
      }
      setTrendChartMeta('chartROEMeta', history.years, roeData, industryRoeHistory);

      // Net Margin Chart with historical industry benchmark
      const marginData = history.metrics.net_profit_margin?.map(d => d.value) || [];
      if (marginData.length > 0) {
        createTrendChart('chartMargin', labels, marginData, 'Net Margin', CHART_COLORS.margin, industryMarginData, { valueType: 'percent', metricKey: 'net_profit_margin' });
      }
      setTrendChartMeta('chartMarginMeta', history.years, marginData, industryMarginHistory);

      // P/E & P/B computed from year-end prices (research-grade semantics)
      const valYears = valuationTs?.years || [];
      const valLabels = Array.isArray(valYears) ? valYears.map(y => y.toString()) : [];

      const peSeries = Array.isArray(valuationTs?.series)
        ? valuationTs.series.map(pt => pt?.valuation?.pe_end ?? null)
        : [];
      const pbSeries = Array.isArray(valuationTs?.series)
        ? valuationTs.series.map(pt => pt?.valuation?.pb_end ?? null)
        : [];

      if (valLabels.length > 0) {
        const peData = peSeries.map(v => (!isMissing(v) && v > 0 ? v : null));
        const pbData = pbSeries.map(v => (!isMissing(v) && v > 0 ? v : null));

        if (peData.length > 0) {
          createTrendChart('chartPE', valLabels, peData, 'P/E', CHART_COLORS.pe, null, { valueType: 'ratio', metricKey: 'pe_ratio', tickDecimals: 1, tooltipDecimals: 2 });
        }
        setTrendChartMeta('chartPEMeta', valYears, peData, null);

        if (pbData.length > 0) {
          createTrendChart('chartPB', valLabels, pbData, 'P/B', CHART_COLORS.pb, null, { valueType: 'ratio', metricKey: 'pb_ratio', tickDecimals: 2, tooltipDecimals: 2 });
        }
        setTrendChartMeta('chartPBMeta', valYears, pbData, null);
      } else {
        const peMeta = document.getElementById('chartPEMeta');
        const pbMeta = document.getElementById('chartPBMeta');
        if (peMeta) peMeta.textContent = 'Không có dữ liệu';
        if (pbMeta) pbMeta.textContent = 'Không có dữ liệu';
      }

      window.requestAnimationFrame(() => {
        reflowVisibleCharts();
      });
    }
  } catch (error) {
    console.error('Error loading trend charts:', error);
  }
}

// ============================================================================
// DUPONT ANALYSIS - EXTENDED 5-COMPONENT
// ============================================================================

/**
 * Load Extended DuPont Analysis from API
 * @param {string} symbol - Stock symbol
 * @param {number} year - Year to analyze (optional)
 */
async function loadExtendedDuPontAnalysis(symbol, year = null) {
  try {
    const url = year
      ? `/api/dupont-extended/${symbol}?year=${year}`
      : `/api/dupont-extended/${symbol}`;

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to load Extended DuPont analysis');
    }

    const data = await response.json();
    renderExtendedDuPontAnalysis(data);
  } catch (error) {
    console.error('Error loading Extended DuPont analysis:', error);
    // Fallback to basic 3-component DuPont
    if (window.currentRatios) {
      renderBasicDuPontAnalysis(window.currentRatios);
    }
  }
}

/**
 * Render Extended DuPont Analysis (5-Component)
 * @param {Object} data - Extended DuPont data from API
 */
function renderExtendedDuPontAnalysis(data) {
  const container = document.getElementById('dupontAnalysis');
  if (!container) return;

  if (!data.has_data) {
    container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: var(--space-4);">Không có đủ dữ liệu để phân tích DuPont</p>';
    return;
  }

  const { components, roe, dupont_roe, interpretation } = data;

  // Define component display order and styles
  const componentConfig = [
    { key: 'tax_burden', label: 'Gánh nặng thuế', color: '#8b5cf6', format: formatPercent },
    { key: 'interest_burden', label: 'Gánh nặng lãi vay', color: '#ec4899', format: formatPercent },
    { key: 'operating_margin', label: 'Biên lợi nhuận hoạt động', color: '#22c55e', format: formatPercent },
    { key: 'asset_turnover', label: 'Vòng quay tài sản', color: '#3b82f6', format: formatRatio },
    { key: 'financial_leverage', label: 'Đòn bẩy tài chính', color: '#f59e0b', format: formatRatio }
  ];

  // Build components HTML
  let componentsHTML = '';
  let formulaParts = [];

  componentConfig.forEach(config => {
    const comp = components[config.key];
    if (!comp || comp.value === null) return;

    const display = config.format(comp.value);
    formulaParts.push(display);

    componentsHTML += `
      <div style="padding: var(--space-4); background: var(--bg-tertiary); border-radius: var(--radius-lg);">
        <div style="font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-2);">${comp.label}</div>
        <div style="font-size: var(--text-2xl); font-weight: var(--font-bold); color: ${config.color};">${display}</div>
        <div style="font-size: var(--text-xs); color: var(--text-tertiary); margin-top: var(--space-1);">${comp.description}</div>
        <div style="font-size: var(--text-xs); color: var(--text-tertiary); margin-top: var(--space-1); opacity: 0.6;">${comp.formula}</div>
      </div>
    `;
  });

  // Build formula display
  const formulaHTML = formulaParts.length > 0
    ? `<div style="font-size: var(--text-xs); opacity: 0.7; margin-top: var(--space-1);">
        ${formulaParts.join(' × ')} = ${formatPercent(dupont_roe || roe)}
       </div>`
    : '';

  // Build interpretation
  const interpretationHTML = interpretation
    ? `<div style="grid-column: span 5; padding: var(--space-4); background: var(--bg-secondary); border-radius: var(--radius-lg); margin-top: var(--space-4);">
        <div style="font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-2); font-weight: var(--font-semibold);">Diễn giải</div>
        <div style="font-size: var(--text-sm); color: var(--text-primary); line-height: 1.6;">${interpretation}</div>
       </div>`
    : '';

  // Build ROE result
  const roeHTML = roe !== null
    ? `<div style="grid-column: span 5; padding: var(--space-4); background: linear-gradient(135deg, var(--color-primary-900), var(--color-primary-800)); border-radius: var(--radius-lg); color: white;">
        <div style="font-size: var(--text-sm); opacity: 0.8; margin-bottom: var(--space-2);">ROE (Kết quả)</div>
        <div style="font-size: var(--text-3xl); font-weight: var(--font-bold);">${formatPercent(roe)}</div>
        ${formulaHTML}
       </div>`
    : '';

  container.innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--space-4);">
      ${componentsHTML}
      ${roeHTML}
      ${interpretationHTML}
    </div>
  `;

  // Add waterfall chart if we have contribution data
  if (data.contribution && Object.keys(data.contribution).length > 0) {
    renderDuPontWaterfallChart(data.contribution, dupont_roe || roe);
  }
}

/**
 * Render DuPont Waterfall Chart (Contribution Breakdown)
 * @param {Object} contribution - Contribution data from API
 * @param {number} totalRoe - Total ROE value
 */
function renderDuPontWaterfallChart(contribution, totalRoe) {
  const container = document.getElementById('dupontWaterfallChart');
  if (!container || totalRoe === null || totalRoe === undefined || Number.isNaN(totalRoe)) return;

  const labels = [];
  const legendLabels = [];
  const values = [];
  const colors = [];

  // Define component order
  const order = ['tax_burden', 'interest_burden', 'operating_margin', 'asset_turnover', 'financial_leverage'];
  const labelMap = {
    tax_burden: ['Gánh nặng', 'thuế'],
    interest_burden: ['Gánh nặng', 'lãi vay'],
    operating_margin: ['Biên LN', 'hoạt động'],
    asset_turnover: ['Vòng quay', 'tài sản'],
    financial_leverage: ['Đòn bẩy', 'tài chính']
  };
  const legendLabelMap = {
    tax_burden: 'Gánh nặng thuế',
    interest_burden: 'Gánh nặng lãi vay',
    operating_margin: 'Biên LN hoạt động',
    asset_turnover: 'Vòng quay tài sản',
    financial_leverage: 'Đòn bẩy tài chính'
  };
  const colorMap = {
    tax_burden: '#8b5cf6',
    interest_burden: '#ec4899',
    operating_margin: '#22c55e',
    asset_turnover: '#3b82f6',
    financial_leverage: '#f59e0b'
  };

  order.forEach(key => {
    const contrib = contribution[key];
    if (contrib && contrib.value !== null) {
      labels.push(labelMap[key]);
      legendLabels.push(legendLabelMap[key]);
      values.push(contrib.value);
      colors.push(colorMap[key]);
    }
  });

  if (values.length === 0) return;

  // Create canvas for chart
  const legendHTML = legendLabels.map((label, index) => `
    <div class="dupont-waterfall-legend-item">
      <span class="dupont-waterfall-legend-dot" style="background:${colors[index]};"></span>
      <span>${label}</span>
    </div>
  `).join('');

  container.innerHTML = `
    <div class="dupont-waterfall-card">
      <div class="dupont-waterfall-title">Đóng góp vào ROE</div>
      <canvas id="dupontWaterfallCanvas" class="dupont-waterfall-canvas"></canvas>
      <div class="dupont-waterfall-legend">${legendHTML}</div>
    </div>
  `;

  // Simple bar chart using canvas
  setTimeout(() => {
    const canvas = document.getElementById('dupontWaterfallCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const canvasWidth = Math.max(520, canvas.parentElement.clientWidth - 32);
    const canvasHeight = 320;
    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    canvas.style.height = `${canvasHeight}px`;

    // Chart area
    const padding = { top: 28, right: 28, bottom: 82, left: 56 };
    const plotWidth = canvasWidth - padding.left - padding.right;
    const plotHeight = canvasHeight - padding.top - padding.bottom;

    const dataMin = Math.min(0, ...values, totalRoe);
    const dataMax = Math.max(0, ...values, totalRoe);
    const valueRange = dataMax - dataMin || 1;
    const yFromValue = (value) => padding.top + ((dataMax - value) / valueRange) * plotHeight;
    const zeroY = yFromValue(0);
    const roeY = yFromValue(totalRoe);

    const step = plotWidth / values.length;
    const barWidth = Math.max(48, Math.min(120, step * 0.56));

    // Draw chart
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    ctx.lineWidth = 1;

    // Zero line
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.35)';
    ctx.beginPath();
    ctx.moveTo(padding.left, zeroY);
    ctx.lineTo(padding.left + plotWidth, zeroY);
    ctx.stroke();

    values.forEach((value, index) => {
      const centerX = padding.left + step * (index + 0.5);
      const x = centerX - barWidth / 2;
      const valueY = yFromValue(value);
      const barY = Math.min(valueY, zeroY);
      const barHeight = Math.max(2, Math.abs(valueY - zeroY));

      // Draw bar
      ctx.fillStyle = colors[index];
      if (typeof ctx.roundRect === 'function') {
        ctx.beginPath();
        ctx.roundRect(x, barY, barWidth, barHeight, 5);
        ctx.fill();
      } else {
        ctx.fillRect(x, barY, barWidth, barHeight);
      }

      // Draw value
      ctx.fillStyle = '#e5e7eb';
      ctx.font = '600 12px Inter, sans-serif';
      ctx.textAlign = 'center';
      const valueText = Math.abs(value) > 0.01 ? value.toFixed(2) : value.toFixed(3);
      const valueTextY = value >= 0 ? barY - 8 : barY + barHeight + 14;
      ctx.fillText(valueText, centerX, valueTextY);

      // Draw label (2 lines)
      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px Inter, sans-serif';
      labels[index].forEach((line, lineIndex) => {
        ctx.fillText(line, centerX, canvasHeight - 34 + (lineIndex * 14));
      });
    });

    // Draw ROE line
    ctx.strokeStyle = '#fbbf24';
    ctx.lineWidth = 2.2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(padding.left, roeY);
    ctx.lineTo(padding.left + plotWidth, roeY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw ROE label
    ctx.fillStyle = '#fbbf24';
    ctx.font = '600 11px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`ROE: ${(totalRoe * 100).toFixed(1)}%`, padding.left + 4, roeY - 8);
  }, 100);
}

/**
 * Fallback: Render Basic 3-Component DuPont Analysis
 * @param {Object} ratios - Financial ratios data
 */
function renderBasicDuPontAnalysis(ratios) {
  const container = document.getElementById('dupontAnalysis');
  if (!container) return;

  const netMargin = ratios.net_profit_margin;
  const assetTurnover = ratios.asset_turnover;
  const financialLeverage = ratios.financial_leverage;
  const roe = ratios.roe;

  // Check if we have minimum data for DuPont
  const hasData = (netMargin !== null && netMargin !== undefined) ||
    (assetTurnover !== null && assetTurnover !== undefined) ||
    (financialLeverage !== null && financialLeverage !== undefined);

  if (!hasData) {
    container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: var(--space-4);">Không có đủ dữ liệu để phân tích DuPont</p>';
    return;
  }

  // Calculate DuPont ROE only when all components are available (avoid missing → 0).
  const canComputeDupontRoe =
    netMargin !== null && netMargin !== undefined &&
    assetTurnover !== null && assetTurnover !== undefined &&
    financialLeverage !== null && financialLeverage !== undefined;
  const dupontRoe = canComputeDupontRoe ? (netMargin * assetTurnover * financialLeverage) : null;

  const components = [
    {
      label: 'Net Margin',
      key: 'netMargin',
      value: netMargin,
      display: netMargin !== null && netMargin !== undefined ? formatPercent(netMargin) : 'N/A',
      color: '#22c55e',
      description: 'Hiệu quả chi phí',
      hasData: netMargin !== null && netMargin !== undefined
    },
    {
      label: 'Asset Turnover',
      key: 'assetTurnover',
      value: assetTurnover,
      display: assetTurnover !== null && assetTurnover !== undefined ? formatRatio(assetTurnover) : 'N/A',
      color: '#3b82f6',
      description: 'Hiệu quả tài sản',
      hasData: assetTurnover !== null && assetTurnover !== undefined
    },
    {
      label: 'Fin. Leverage',
      key: 'financialLeverage',
      value: financialLeverage,
      display: financialLeverage !== null && financialLeverage !== undefined ? formatRatio(financialLeverage) : 'N/A',
      color: '#f59e0b',
      description: 'Đòn bẩy vốn',
      hasData: financialLeverage !== null && financialLeverage !== undefined
    }
  ];

  // Only show components that have data
  const visibleComponents = components.filter(c => c.hasData);

  container.innerHTML = visibleComponents.map(comp => `
    <div style="padding: var(--space-4); background: var(--bg-tertiary); border-radius: var(--radius-lg);">
      <div style="font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-2);">${comp.label}</div>
      <div style="font-size: var(--text-2xl); font-weight: var(--font-bold); color: ${comp.color};">${comp.display}</div>
      <div style="font-size: var(--text-xs); color: var(--text-tertiary); margin-top: var(--space-1);">${comp.description}</div>
    </div>
  `).join('');

  // Add ROE result if available
  if (roe !== null && roe !== undefined) {
    const formula = visibleComponents.map(c => c.display).join(' × ');
    container.innerHTML += `
      <div style="grid-column: span ${visibleComponents.length}; padding: var(--space-4); background: linear-gradient(135deg, var(--color-primary-900), var(--color-primary-800)); border-radius: var(--radius-lg); color: white;">
        <div style="font-size: var(--text-sm); opacity: 0.8; margin-bottom: var(--space-2);">ROE (Kết quả)</div>
        <div style="font-size: var(--text-3xl); font-weight: var(--font-bold);">${formatPercent(roe)}</div>
        ${canComputeDupontRoe ? `
        <div style="font-size: var(--text-xs); opacity: 0.7; margin-top: var(--space-1);">
          ${formula} ≈ ${formatPercent(dupontRoe)}
        </div>` : ''}
      </div>
    `;
  }
}

/**
 * Legacy function for backward compatibility - now loads extended DuPont
 * @param {Object} ratios - Financial ratios data
 */
function renderDuPontAnalysis(ratios) {
  const container = document.getElementById('dupontAnalysis');
  if (!container) return;

  // Store ratios for fallback
  window.currentRatios = ratios;

  // Try to load extended DuPont from API if we have a symbol
  const symbolElement = document.querySelector('[data-symbol]');
  if (symbolElement) {
    const symbol = symbolElement.getAttribute('data-symbol');
    if (symbol) {
      loadExtendedDuPontAnalysis(symbol);
      return;
    }
  }

  // Fallback to basic analysis
  renderBasicDuPontAnalysis(ratios);
}



// ============================================================================
// WORKING CAPITAL EFFICIENCY - CASH CONVERSION CYCLE
// ============================================================================

/**
 * Render Working Capital Efficiency - Cash Conversion Cycle
 * @param {Object} ratios - Financial ratios data
 */
function renderWorkingCapitalEfficiency(ratios) {
  const container = document.getElementById('workingCapitalSection');
  if (!container) return;

  const ccc = ratios.cash_conversion_cycle;
  const dso = ratios.days_sales_outstanding;
  const dio = ratios.days_inventory_outstanding;
  const dpo = ratios.days_payable_outstanding;

  // Check if we have working capital data
  const hasData = (ccc !== null && ccc !== undefined) ||
    (dso !== null && dso !== undefined) ||
    (dio !== null && dio !== undefined) ||
    (dpo !== null && dpo !== undefined);

  if (!hasData) {
    // Check industry for appropriate message
    const industry = state.currentIndustry || '';
    const isBank = industry.toLowerCase().includes('ngân hàng') || industry.toLowerCase().includes('bank');
    const isInsurance = industry.toLowerCase().includes('bảo hiểm') || industry.toLowerCase().includes('insurance');

    let message = 'Không có dữ liệu về hiệu quả vốn lưu động';
    let subMessage = '';

    if (isBank) {
      message = 'Không áp dụng cho Ngân hàng';
      subMessage = 'Ngân hàng không có Hàng tồn kho, Phải thu KH, Phải trả NCC như doanh nghiệp sản xuất. Chỉ số này dùng để đánh giá doanh nghiệp sản xuất, thương mại.';
    } else if (isInsurance) {
      message = 'Không áp dụng cho Bảo hiểm';
      subMessage = 'Công ty bảo hiểm có mô hình kinh doanh khác, không sử dụng CCC để đánh giá.';
    }

    container.innerHTML = `
      <div style="text-align: center; padding: var(--space-8);">
        <div style="font-size: 2rem; margin-bottom: var(--space-2);">🏦</div>
        <p style="color: var(--text-secondary); margin-bottom: var(--space-2);">${message}</p>
        ${subMessage ? `<p style="color: var(--text-tertiary); font-size: var(--text-sm); max-width: 400px; margin: 0 auto;">${subMessage}</p>` : ''}
      </div>
    `;
    return;
  }

  // Calculate CCC if not provided
  const canComputeCCC = dso !== null && dso !== undefined && dio !== null && dio !== undefined && dpo !== null && dpo !== undefined;
  const calculatedCCC = canComputeCCC ? (dso + dio - dpo) : null;
  const displayCCC = ccc !== null && ccc !== undefined ? ccc : calculatedCCC;

  // Determine rating and colors
  const getCCCRating = (value) => {
    if (value === null || value === undefined) return { text: 'N/A', color: '#9ca3af', bgColor: 'rgba(148, 163, 184, 0.18)' };
    if (value < 0) return { text: 'Tuyệt vời', color: '#22c55e', bgColor: '#22c55e20' };
    if (value < 30) return { text: 'Rất tốt', color: '#22c55e', bgColor: '#22c55e20' };
    if (value < 45) return { text: 'Tốt', color: '#84cc16', bgColor: '#84cc1620' };
    if (value < 60) return { text: 'Khá', color: '#f59e0b', bgColor: '#f59e0b20' };
    if (value < 90) return { text: 'Trung bình', color: '#f97316', bgColor: '#f9731620' };
    return { text: 'Cần cải thiện', color: '#ef4444', bgColor: '#ef444420' };
  };

  const cccRating = getCCCRating(displayCCC);

  // Component ratings
  const getDSORating = (value) => {
    if (value === null || value === undefined) return { text: 'N/A', color: '#9ca3af' };
    if (value < 30) return { text: 'Tốt', color: '#22c55e' };
    if (value < 45) return { text: 'Khá', color: '#f59e0b' };
    return { text: 'Cần cải thiện', color: '#ef4444' };
  };

  const getDIORating = (value) => {
    if (value === null || value === undefined) return { text: 'N/A', color: '#9ca3af' };
    if (value < 30) return { text: 'Tốt', color: '#22c55e' };
    if (value < 60) return { text: 'Khá', color: '#f59e0b' };
    if (value < 90) return { text: 'Trung bình', color: '#f97316' };
    return { text: 'Cần cải thiện', color: '#ef4444' };
  };

  const getDPORating = (value) => {
    if (value === null || value === undefined) return { text: 'N/A', color: '#9ca3af' };
    if (value > 60) return { text: 'Tốt', color: '#22c55e' };
    if (value > 45) return { text: 'Khá', color: '#f59e0b' };
    return { text: 'Ngắn', color: '#ef4444' };
  };

  // Build HTML
  let html = `
    <!-- CCC Summary Card -->
    <div style="margin-bottom: var(--space-6); padding: var(--space-6); background: linear-gradient(135deg, #1e3a5f, #2d4a6f); border-radius: var(--radius-xl); color: white;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4);">
        <div>
          <div style="font-size: var(--text-sm); opacity: 0.8; margin-bottom: var(--space-2);">Cash Conversion Cycle (CCC)</div>
          <div style="font-size: var(--text-4xl); font-weight: var(--font-bold);">${displayCCC !== null && displayCCC !== undefined ? displayCCC.toFixed(0) : 'N/A'}<span style="font-size: var(--text-xl); opacity: 0.8;"> ngày</span></div>
        </div>
        <div style="text-align: right;">
          <div style="padding: var(--space-2) var(--space-4); background: ${cccRating.bgColor}; border-radius: var(--radius-full); font-size: var(--text-sm); font-weight: var(--font-semibold); color: ${cccRating.color};">
            ${cccRating.text}
          </div>
          <div style="font-size: var(--text-xs); opacity: 0.7; margin-top: var(--space-2);">
            CCC càng thấp = Hiệu quả càng tốt
          </div>
        </div>
      </div>

      <!-- Formula breakdown -->
      ${canComputeCCC ? `
      <div style="display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); opacity: 0.9;">
        <span>CCC = DSO + DIO - DPO</span>
        <span style="opacity: 0.7;">=</span>
        <span>${dso.toFixed(0)} + ${dio.toFixed(0)} - ${dpo.toFixed(0)} = ${displayCCC.toFixed(0)} ngày</span>
      </div>
      ` : ''}
    </div>

    <!-- Component Cards -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--space-4); margin-bottom: var(--space-6);">
      <!-- DSO Card -->
      ${dso !== null && dso !== undefined ? `
      <div style="padding: var(--space-4); background: var(--bg-tertiary); border-radius: var(--radius-lg); border-left: 4px solid ${getDSORating(dso).color};">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--space-2);">
          <div style="font-size: var(--text-sm); color: var(--text-secondary);">DSO</div>
          <span style="padding: 2px 8px; background: ${getDSORating(dso).color}20; color: ${getDSORating(dso).color}; border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--font-medium);">
            ${getDSORating(dso).text}
          </span>
        </div>
        <div style="font-size: var(--text-2xl); font-weight: var(--font-semibold); color: var(--text-primary); margin-bottom: var(--space-1);">
          ${dso.toFixed(0)}<span style="font-size: var(--text-sm); color: var(--text-secondary); font-weight: var(--font-normal);"> ngày</span>
        </div>
        <div style="font-size: var(--text-xs); color: var(--text-tertiary);">
          Days Sales Outstanding - Thu tiền nợ
        </div>
        <div style="padding: var(--space-3); background: var(--bg-secondary); border-radius: var(--radius-md); font-size: var(--text-xs); color: var(--text-secondary); margin-top: var(--space-2);">
          <strong>DSO < 30 ngày:</strong> Tốt<br>
          <strong>30-45 ngày:</strong> Khá<br>
          <strong>> 45 ngày:</strong> Cần cải thiện
        </div>
      </div>
      ` : ''}

      <!-- DIO Card -->
      ${dio !== null && dio !== undefined ? `
      <div style="padding: var(--space-4); background: var(--bg-tertiary); border-radius: var(--radius-lg); border-left: 4px solid ${getDIORating(dio).color};">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--space-2);">
          <div style="font-size: var(--text-sm); color: var(--text-secondary);">DIO</div>
          <span style="padding: 2px 8px; background: ${getDIORating(dio).color}20; color: ${getDIORating(dio).color}; border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--font-medium);">
            ${getDIORating(dio).text}
          </span>
        </div>
        <div style="font-size: var(--text-2xl); font-weight: var(--font-semibold); color: var(--text-primary); margin-bottom: var(--space-1);">
          ${dio.toFixed(0)}<span style="font-size: var(--text-sm); color: var(--text-secondary); font-weight: var(--font-normal);"> ngày</span>
        </div>
        <div style="font-size: var(--text-xs); color: var(--text-tertiary);">
          Days Inventory Outstanding - Hàng tồn kho
        </div>
        <div style="padding: var(--space-3); background: var(--bg-secondary); border-radius: var(--radius-md); font-size: var(--text-xs); color: var(--text-secondary); margin-top: var(--space-2);">
          <strong>DIO < 30 ngày:</strong> Tốt<br>
          <strong>30-60 ngày:</strong> Khá<br>
          <strong>> 60 ngày:</strong> Cần cải thiện
        </div>
      </div>
      ` : ''}

      <!-- DPO Card -->
      ${dpo !== null && dpo !== undefined ? `
      <div style="padding: var(--space-4); background: var(--bg-tertiary); border-radius: var(--radius-lg); border-left: 4px solid ${getDPORating(dpo).color};">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--space-2);">
          <div style="font-size: var(--text-sm); color: var(--text-secondary);">DPO</div>
          <span style="padding: 2px 8px; background: ${getDPORating(dpo).color}20; color: ${getDPORating(dpo).color}; border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--font-medium);">
            ${getDPORating(dpo).text}
          </span>
        </div>
        <div style="font-size: var(--text-2xl); font-weight: var(--font-semibold); color: var(--text-primary); margin-bottom: var(--space-1);">
          ${dpo.toFixed(0)}<span style="font-size: var(--text-sm); color: var(--text-secondary); font-weight: var(--font-normal);"> ngày</span>
        </div>
        <div style="font-size: var(--text-xs); color: var(--text-tertiary);">
          Days Payable Outstanding - Trả nợ
        </div>
        <div style="padding: var(--space-3); background: var(--bg-secondary); border-radius: var(--radius-md); font-size: var(--text-xs); color: var(--text-secondary); margin-top: var(--space-2);">
          <strong>DPO > 60 ngày:</strong> Tốt<br>
          <strong>45-60 ngày:</strong> Khá<br>
          <strong>< 45 ngày:</strong> Ngắn (có thể tốt cho nhà cung cấp)
        </div>
      </div>
      ` : ''}
    </div>

    <!-- Timeline Visualization -->
    ${canComputeCCC ? `
    <div style="margin-top: var(--space-4);">
      <h4 style="font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-3);">Biểu đồ dòng tiền (Timeline)</h4>
      <div style="position: relative; padding: var(--space-4) 0;">
        <!-- Timeline bar -->
        <div style="display: flex; align-items: center; gap: 0; height: 60px; position: relative;">
          <!-- DSO (Outflow) -->
          <div style="flex: ${dso}; min-width: 40px; background: linear-gradient(90deg, #ef4444, #f87171); border-radius: var(--radius-md) 0 0 var(--radius-md); display: flex; flex-direction: column; justify-content: center; align-items: center; color: white; position: relative; cursor: help;" onmouseenter="this.querySelector('.wcc-timeline-tooltip').style.opacity='1'" onmouseleave="this.querySelector('.wcc-timeline-tooltip').style.opacity='0'">
            <span style="font-size: var(--text-xs); font-weight: var(--font-semibold);">DSO</span>
            <span style="font-size: var(--text-lg); font-weight: var(--font-bold);">${dso.toFixed(0)}</span>
            <div class="wcc-timeline-tooltip" style="position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--bg-secondary); border-radius: var(--radius-md); font-size: var(--text-xs); white-space: nowrap; opacity: 0; transition: opacity 0.2s; pointer-events: none;">
              Thu tiền nợ
            </div>
          </div>

          <!-- DIO (Outflow) -->
          <div style="flex: ${dio}; min-width: 40px; background: linear-gradient(90deg, #f59e0b, #fbbf24); display: flex; flex-direction: column; justify-content: center; align-items: center; color: white; position: relative; cursor: help;" onmouseenter="this.querySelector('.wcc-timeline-tooltip').style.opacity='1'" onmouseleave="this.querySelector('.wcc-timeline-tooltip').style.opacity='0'">
            <span style="font-size: var(--text-xs); font-weight: var(--font-semibold);">DIO</span>
            <span style="font-size: var(--text-lg); font-weight: var(--font-bold);">${dio.toFixed(0)}</span>
            <div class="wcc-timeline-tooltip" style="position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--bg-secondary); border-radius: var(--radius-md); font-size: var(--text-xs); white-space: nowrap; opacity: 0; transition: opacity 0.2s; pointer-events: none;">
              Hàng tồn kho
            </div>
          </div>

          <!-- DPO (Inflow - reduces CCC) -->
          <div style="flex: ${dpo}; min-width: 40px; background: linear-gradient(90deg, #22c55e, #4ade80); border-radius: 0 var(--radius-md) var(--radius-md) 0; display: flex; flex-direction: column; justify-content: center; align-items: center; color: white; position: relative; cursor: help;" onmouseenter="this.querySelector('.wcc-timeline-tooltip').style.opacity='1'" onmouseleave="this.querySelector('.wcc-timeline-tooltip').style.opacity='0'">
            <span style="font-size: var(--text-xs); font-weight: var(--font-semibold);">DPO</span>
            <span style="font-size: var(--text-lg); font-weight: var(--font-bold);">-${dpo.toFixed(0)}</span>
            <div class="wcc-timeline-tooltip" style="position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--bg-secondary); border-radius: var(--radius-md); font-size: var(--text-xs); white-space: nowrap; opacity: 0; transition: opacity 0.2s; pointer-events: none;">
              Trì hoãn trả nợ
            </div>
          </div>
        </div>

        <!-- Result indicator -->
        <div style="display: flex; align-items: center; gap: var(--space-4); margin-top: var(--space-3); padding: var(--space-3); background: var(--bg-tertiary); border-radius: var(--radius-md);">
          <span style="font-size: var(--text-sm); color: var(--text-secondary);">Kết quả CCC:</span>
          <span style="font-size: var(--text-xl); font-weight: var(--font-bold); color: ${cccRating.color};">${displayCCC !== null && displayCCC !== undefined ? displayCCC.toFixed(0) : 'N/A'} ngày</span>
          <span style="font-size: var(--text-xs); color: var(--text-tertiary); flex: 1;">(${cccRating.text})</span>
          <span style="font-size: var(--text-xs); color: var(--text-secondary);">DSO + DIO - DPO</span>
        </div>
      </div>
    </div>
    ` : ''}

    <!-- Interpretation -->
    <div style="margin-top: var(--space-4); padding: var(--space-4); background: var(--bg-tertiary); border-radius: var(--radius-lg);">
      <h4 style="font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-2);">Ý nghĩa chỉ số</h4>
      <ul style="font-size: var(--text-sm); color: var(--text-secondary); margin: 0; padding-left: var(--space-4); line-height: 1.6;">
        <li><strong>CCC âm:</strong> Công ty thu tiền trước khi phải trả nợ - Tuyệt vời</li>
        <li><strong>CCC < 30 ngày:</strong> Vòng quay vốn rất nhanh - Hiệu quả cao</li>
        <li><strong>CCC 30-45 ngày:</strong> Vòng quay vốn tốt - Hiệu quả tốt</li>
        <li><strong>CCC 45-60 ngày:</strong> Vòng quay vốn khá - Cần tối ưu</li>
        <li><strong>CCC > 60 ngày:</strong> Vòng quay vốn chậm - Cần cải thiện</li>
      </ul>
    </div>
  `;

  container.innerHTML = html;
}


// ============================================================================
// ALTMAN Z-SCORE ANALYSIS
// ============================================================================

/**
 * Render Altman Z-Score component
 * @param {Object} zscoreData - Z-Score data from API
 * @param {string} industry - Company industry (to check if it's a bank)
 */
async function renderAltmanZScore(zscoreData, industry = null) {
  const container = document.getElementById('altmanZScoreSection');
  if (!container) return;

  // Check if it's a bank/financial institution
  const isBank = industry && industry.toLowerCase().includes('ngân hàng');

  // Check for both 'score' and 'z_score' keys (API/UI contract compatibility)
  const scoreValueRaw = zscoreData ? (zscoreData.score ?? zscoreData.z_score) : null;
  const scoreValue = (scoreValueRaw !== null && scoreValueRaw !== undefined) ? Number(scoreValueRaw) : null;
  const hasZScore = scoreValue !== null && Number.isFinite(scoreValue);

  if (!hasZScore) {
    container.innerHTML = `
      <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
        <p>Không có dữ liệu Altman Z-Score</p>
        ${isBank ? '<p style="font-size: var(--text-sm); color: var(--text-tertiary); margin-top: var(--space-2);">Chỉ số này không áp dụng cho ngành ngân hàng</p>' : ''}
      </div>
    `;
    return;
  }

  const { zone, components } = zscoreData;
  const score = scoreValue;

  // Determine zone styling
  let zoneClass = 'safe';
  let zoneText = 'An toàn';
  let zoneEmoji = '🟢';
  let zoneDescription = 'Công ty có sức khỏe tài chính tốt, nguy cơ phá sản thấp';

  if (zone === 'grey' || (score <= 2.99 && score >= 1.81)) {
    zoneClass = 'grey';
    zoneText = 'Vùng xám';
    zoneEmoji = '🟡';
    zoneDescription = 'Công ty ở mức trung bình, cần theo dõi thêm các chỉ số';
  } else if (zone === 'distress' || score < 1.81) {
    zoneClass = 'distress';
    zoneText = 'Nguy cơ';
    zoneEmoji = '🔴';
    zoneDescription = 'Công ty có dấu hiệu khó khăn tài chính, nguy cơ phá sản cao';
  }

  // Calculate gauge position (normalize 0-6 scale to percentage)
  const minScore = 0;
  const maxScore = 6;
  const gaugePercent = Math.max(0, Math.min(100, ((score - minScore) / (maxScore - minScore)) * 100));
  const distressThreshold = 1.81;
  const safeThreshold = 2.99;
  const distressThresholdPercent = ((distressThreshold - minScore) / (maxScore - minScore)) * 100;
  const safeThresholdPercent = ((safeThreshold - minScore) / (maxScore - minScore)) * 100;

  // Generate HTML
  container.innerHTML = `
    <div class="altman-zscore-card">
      <div class="zscore-header">
        <div class="zscore-title">
          <span>🎯</span>
          <span>Altman Z-Score</span>
        </div>
        ${isBank ? '<div class="zscore-disclaimer">⚠️ Không áp dụng cho ngân hàng/TC</div>' : ''}
      </div>

      <div class="zscore-main">
        <!-- Left: Z-Score Value -->
        <div class="zscore-value-section">
          <div class="zscore-value ${zoneClass}">${score.toFixed(2)}</div>
          <div class="zscore-zone ${zoneClass}">
            <span>${zoneEmoji}</span>
            <span style="margin-left: var(--space-1);">${zoneText}</span>
          </div>
          <p class="zscore-description">${zoneDescription}</p>
        </div>

        <!-- Right: Gauge -->
        <div class="zscore-gauge-section">
          <div class="zscore-scale-card">
            <div class="zscore-scale-title">Thang phân loại</div>
            <div class="zscore-gauge-container">
              <div class="zscore-gauge">
                <div class="zscore-gauge-marker" style="left: ${gaugePercent}%;">
                  <span class="zscore-gauge-marker-value">${score.toFixed(2)}</span>
                </div>
              </div>
              <div class="zscore-gauge-labels">
                <span style="left: 0%;">0</span>
                <span style="left: ${distressThresholdPercent}%;">1.81</span>
                <span style="left: ${safeThresholdPercent}%;">2.99</span>
                <span style="left: 100%;">6</span>
              </div>
            </div>

            <div class="zscore-zone-cards">
              <div class="zscore-zone-card distress ${zoneClass === 'distress' ? 'active' : ''}">
                <div class="zscore-zone-card-name">Nguy cơ</div>
                <div class="zscore-zone-card-range">Z &lt; 1.81</div>
              </div>
              <div class="zscore-zone-card grey ${zoneClass === 'grey' ? 'active' : ''}">
                <div class="zscore-zone-card-name">Vùng xám</div>
                <div class="zscore-zone-card-range">1.81 - 2.99</div>
              </div>
              <div class="zscore-zone-card safe ${zoneClass === 'safe' ? 'active' : ''}">
                <div class="zscore-zone-card-name">An toàn</div>
                <div class="zscore-zone-card-range">Z &gt; 2.99</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      ${components ? `
      <div class="zscore-components">
        <h4 class="zscore-components-title">Thành phần Z-Score</h4>
        <div class="zscore-components-grid">
          ${renderZScoreComponent('X1', 'Vốn lưu động / Tài sản', components.x1_working_capital, 'Tài chính ngắn hạn')}
          ${renderZScoreComponent('X2', 'Lợi nhuận giữ lại / Tài sản', components.x2_retained_earnings, 'Khả năng sinh lời')}
          ${renderZScoreComponent('X3', 'EBIT / Tài sản', components.x3_ebit, 'Hiệu quả hoạt động')}
          ${renderZScoreComponent('X4', 'Vốn hóa / Nợ phải trả', components.x4_market_cap_debt, 'Đòn bẩy tài chính')}
          ${renderZScoreComponent('X5', 'Doanh thu / Tài sản', components.x5_asset_turnover, 'Hiệu quả tài sản')}
        </div>
      </div>
      ` : ''}

      <!-- Formula Info Toggle -->
      <div class="zscore-formula-info">
        <div class="zscore-formula-toggle" onclick="toggleZScoreFormula()">
          <div class="zscore-formula-toggle-header">
            <span>📖</span>
            <span>Giải thích công thức Z-Score</span>
          </div>
          <span class="zscore-formula-toggle-icon" id="zscoreFormulaIcon">▼</span>
        </div>
        <div class="zscore-formula-content" id="zscoreFormulaContent">
          <div class="zscore-formula-details">
            <p><strong>Altman Z-Score</strong> là mô hình dự đoán nguy cơ phá sản của doanh nghiệp, được phát triển bởi giáo sư Edward Altman.</p>

            <div class="zscore-formula-equation">
              Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
            </div>

            <div class="zscore-formula-steps">
              <div class="zscore-formula-step">
                <div class="zscore-formula-step-code">1</div>
                <div class="zscore-formula-step-text">
                  <strong>X1 = Working Capital / Total Assets</strong><br>
                  Đo lường thanh khoản và khả năng đáp ứng các nghĩa vụ ngắn hạn
                </div>
              </div>
              <div class="zscore-formula-step">
                <div class="zscore-formula-step-code">2</div>
                <div class="zscore-formula-step-text">
                  <strong>X2 = Retained Earnings / Total Assets</strong><br>
                  Đo lường tuổi đời và khả năng tái đầu tư của công ty
                </div>
              </div>
              <div class="zscore-formula-step">
                <div class="zscore-formula-step-code">3</div>
                <div class="zscore-formula-step-text">
                  <strong>X3 = EBIT / Total Assets</strong><br>
                  Đo lường hiệu quả hoạt động cốt lõi, không chịu ảnh hưởng của thuế và đòn bẩy
                </div>
              </div>
              <div class="zscore-formula-step">
                <div class="zscore-formula-step-code">4</div>
                <div class="zscore-formula-step-text">
                  <strong>X4 = Market Cap / Total Liabilities</strong><br>
                  Đo lường mức độ suy giảm giá trị khi công ty gặp khó khăn (đối với công ty niêm yết)
                </div>
              </div>
              <div class="zscore-formula-step">
                <div class="zscore-formula-step-code">5</div>
                <div class="zscore-formula-step-text">
                  <strong>X5 = Sales / Total Assets</strong><br>
                  Đo lường khả năng tạo doanh thu từ tài sản
                </div>
              </div>
            </div>

            <p style="margin-top: var(--space-3); padding-top: var(--space-3); border-top: 1px solid var(--border-color);">
              <strong>Phân loại:</strong><br>
              • Z > 2.99: Safe Zone (An toàn) - Nguy cơ phá sản thấp<br>
              • 1.81 < Z < 2.99: Grey Zone (Vùng xám) - Cần theo dõi<br>
              • Z < 1.81: Distress Zone (Nguy cơ) - Nguy cơ phá sản cao
            </p>
          </div>
        </div>
      </div>
    </div>
  `;

  // Animate the gauge marker
  setTimeout(() => {
    const marker = container.querySelector('.zscore-gauge-marker');
    if (marker) {
      marker.style.left = `${gaugePercent}%`;
    }
  }, 100);
}

/**
 * Render a single Z-Score component
 */
function renderZScoreComponent(code, label, value, description) {
  if (value === null || value === undefined) {
    return '';
  }

  const formattedValue = typeof value === 'number' ? value.toFixed(3) : value;

  return `
    <div class="zscore-component-item">
      <div class="zscore-component-label">${code} - ${label}</div>
      <div class="zscore-component-value">${formattedValue}</div>
      <div class="zscore-component-formula">${description}</div>
    </div>
  `;
}

/**
 * Toggle Z-Score formula visibility
 */
function toggleZScoreFormula() {
  const content = document.getElementById('zscoreFormulaContent');
  const icon = document.getElementById('zscoreFormulaIcon');

  if (content && icon) {
    content.classList.toggle('open');
    icon.classList.toggle('open');
  }
}

function renderBalanceSheet(data) {
  if (!data || Object.keys(data).length === 0) {
    document.getElementById('balanceSheetTable').innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-secondary);">Không có dữ liệu</td></tr>';
    return;
  }

  const rows = [
    { label: 'TÀI SẢN', isHeader: true },
    { label: 'Tài sản ngắn hạn', key: 'asset_current', indent: 1 },
    { label: 'Tiền và tương đương', key: 'cash_and_equivalents', indent: 2 },
    { label: 'Đầu tư ngắn hạn', key: 'short_term_investments', indent: 2 },
    { label: 'Các khoản phải thu', key: 'accounts_receivable', indent: 2 },
    { label: 'Hàng tồn kho', key: 'inventory', indent: 2 },
    { label: 'Tài sản dài hạn', key: 'asset_non_current', indent: 1 },
    { label: 'Tài sản cố định', key: 'fixed_assets', indent: 2 },
    { label: 'Đầu tư dài hạn', key: 'long_term_investments', indent: 2 },
    { label: 'TÀI SẢN KHÁC', key: 'non_current_assets_other', indent: 1 },
    { label: 'TỔNG TÀI SẢN', key: 'total_assets', isTotal: true },
    { label: '', isSpacer: true },
    { label: 'NGUỒN VỐN', isHeader: true },
    { label: 'Nợ ngắn hạn', key: 'liabilities_current', indent: 1 },
    { label: 'Nợ dài hạn', key: 'liabilities_non_current', indent: 1 },
    { label: 'TỔNG NỢ PHẢI TRẢ', key: 'liabilities_total', isTotal: true },
    { label: 'Vốn chủ sở hữu', key: 'equity_total', indent: 1 },
    { label: 'Vốn điều lệ', key: 'share_capital', indent: 2 },
    { label: 'Lãi chưa phân phối', key: 'retained_earnings', indent: 2 },
    { label: 'Vốn khác', key: 'equity_other', indent: 2 },
    { label: 'TỔNG NGUỒN VỐN', key: 'total_equity_and_liabilities', isTotal: true }
  ];

  const html = rows.map(row => {
    if (row.isSpacer) return '<tr><td colspan="3">&nbsp;</td></tr>';
    if (row.isHeader) return `<tr class="section-header"><td colspan="3">${row.label}</td></tr>`;

    const value = data[row.key];

    // Skip rows without data (except totals which should always show)
    if (!row.isTotal && (value === null || value === undefined)) {
      return '';
    }

    const formattedValue = isMissing(value) ? '-' : formatCurrency(value);
    const indentClass = row.indent ? `indent-${row.indent}` : '';
    const rowClass = row.isTotal ? 'total-row' : '';

    // Add click handler for rows with key
    const clickHandler = row.key ? `onclick="handleMetricRowClick('${row.key}', 'balance_sheet', '${row.label}', 'tỷ')"` : '';

    return `<tr class="${rowClass}" ${clickHandler}><td class="${indentClass}">${row.label}</td><td class="number">${formattedValue}</td></tr>`;
  }).join('');

  document.getElementById('balanceSheetTable').innerHTML = `
    <thead><tr><th>Chỉ tiêu</th><th style="text-align: right;">${data.year || state.currentYear}</th></tr></thead>
    <tbody>${html}</tbody>
  `;
}

function renderIncomeStatement(data) {
  if (!data || Object.keys(data).length === 0) {
    document.getElementById('incomeStatementTable').innerHTML = '<tr><td colspan="2" style="text-align: center; color: var(--text-secondary);">Không có dữ liệu</td></tr>';
    return;
  }

  const rows = [
    // NOTE (data limits): Some upstream sources store credit items as negative numbers.
    // For readability and consistent ratio math, show magnitudes for revenue/expense flows.
    { label: 'Doanh thu thuần', key: 'net_revenue', magnitude: true },
    { label: 'Giá vốn hàng bán', key: 'cost_of_goods_sold', magnitude: true },
    { label: 'Lợi nhuận gộp', key: 'gross_profit', isHighlight: true },
    { label: 'Doanh thu tài chính', key: 'financial_income', magnitude: true },
    { label: 'Chi phí tài chính', key: 'financial_expense', magnitude: true },
    { label: 'Chi phí bán hàng', key: 'operating_expenses', magnitude: true },
    { label: 'Lợi nhuận hoạt động', key: 'operating_profit', isHighlight: true },
    { label: 'Lợi nhuận khác', key: 'other_income' },
    { label: 'Lợi nhuận trước thuế', key: 'profit_before_tax' },
    { label: 'Thuế TNDN', key: 'corporate_income_tax', magnitude: true },
    { label: 'LỢI NHUẬN SAU THUẾ', key: 'net_profit', isTotal: true }
  ];

  const html = rows.map(row => {
    const value = data[row.key];

    // Skip rows without data (except totals)
    if (!row.isTotal && !row.isHighlight && (value === null || value === undefined)) {
      return '';
    }

    const displayValue = (row.magnitude && typeof value === 'number') ? Math.abs(value) : value;
    const formattedValue = isMissing(value) ? '-' : formatCurrency(displayValue);
    const rowClass = row.isTotal ? 'total-row' : row.isHighlight ? 'section-header' : '';

    // Add click handler
    const clickHandler = row.key ? `onclick="handleMetricRowClick('${row.key}', 'income_statement', '${row.label}', 'tỷ')"` : '';

    return `<tr class="${rowClass}" ${clickHandler}><td>${row.label}</td><td class="number">${formattedValue}</td></tr>`;
  }).join('');

  const noteRow = `
    <tr>
      <td colspan="2" style="font-size: var(--text-xs); color: var(--text-tertiary); padding-top: var(--space-3);">
        Ghi chú: Một số khoản mục doanh thu/chi phí có thể được lưu theo quy ước dấu (credit âm); bảng hiển thị trị tuyệt đối cho dễ đọc.
      </td>
    </tr>
  `;

  document.getElementById('incomeStatementTable').innerHTML = `
    <thead><tr><th>Chỉ tiêu</th><th style="text-align: right;">${data.year || state.currentYear}</th></tr></thead>
    <tbody>${html}${noteRow}</tbody>
  `;
}

function renderCashFlow(data) {
  if (!data || Object.keys(data).length === 0) {
    document.getElementById('cashflowTable').innerHTML = '<tr><td colspan="2" style="text-align: center; color: var(--text-secondary);">Không có dữ liệu</td></tr>';
    return;
  }

  const rows = [
    { label: 'Lợi nhuận trước thuế', key: 'profit_before_tax' },
    { label: 'Khấu hao TSCĐ', key: 'depreciation_fixed_assets' },
    { label: 'Thay đổi vốn lưu động', key: null },
    { label: 'Dòng tiền từ HĐKD', key: 'net_cash_from_operating_activities', isHighlight: true },
    { label: 'Mua sắm TSCĐ', key: 'purchase_purchase_fixed_assets' },
    { label: 'Thanh lý TSCĐ', key: 'sale_fixed_assets' },
    { label: 'Dòng tiền từ HĐĐT', key: 'net_cash_from_investing_activities', isHighlight: true },
    { label: 'Vay mới', key: 'proceeds_from_borrowings' },
    { label: 'Trả nợ vay', key: 'repayments_of_borrowings' },
    { label: 'Cổ tức đã trả', key: 'dividends_paid' },
    { label: 'Phát hành cổ phiếu', key: 'proceeds_issuing_shares' },
    { label: 'Dòng tiền từ HĐTC', key: 'net_cash_from_financing_activities', isHighlight: true },
    { label: 'DÒNG TIỀN THUẦN KỲ', key: 'net_cash_flow_period', isTotal: true }
  ];

  const html = rows.map(row => {
    if (!row.key) return `<tr><td colspan="2" style="color: var(--text-tertiary); font-style: italic;">${row.label}</td></tr>`;

    const value = data[row.key];

    // Skip rows without data (except totals and highlights)
    if (!row.isTotal && !row.isHighlight && (value === null || value === undefined)) {
      return '';
    }

    const formattedValue = isMissing(value) ? '-' : formatCurrency(value);
    const rowClass = row.isTotal ? 'total-row' : row.isHighlight ? 'section-header' : '';

    // Add click handler
    const clickHandler = row.key ? `onclick="handleMetricRowClick('${row.key}', 'cash_flow_statement', '${row.label}', 'tỷ')"` : '';

    return `<tr class="${rowClass}" ${clickHandler}><td>${row.label}</td><td class="number">${formattedValue}</td></tr>`;
  }).join('');

  document.getElementById('cashflowTable').innerHTML = `
    <thead><tr><th>Chỉ tiêu</th><th style="text-align: right;">${data.year || state.currentYear}</th></tr></thead>
    <tbody>${html}</tbody>
  `;
}

function renderRatios(data, profile) {
  if (!data || Object.keys(data).length === 0) {
    document.getElementById('ratiosTable').innerHTML = '<tr><td colspan="2" style="text-align: center; color: var(--text-secondary);">Không có dữ liệu</td></tr>';
    return;
  }

  const ratioGroups = [
    {
      title: 'Chỉ số định giá',
      ratios: [
        { label: 'P/E', key: 'price_to_earnings', format: 'number' },
        { label: 'P/B', key: 'price_to_book', format: 'number' },
        { label: 'P/S', key: 'price_to_sales', format: 'number' },
        { label: 'P/CF', key: 'price_to_cash_flow', format: 'number' },
        { label: 'EV/EBITDA', key: 'ev_to_ebitda', format: 'number' },
        { label: 'EPS (VND)', key: 'eps_vnd', format: 'currency' },
        { label: 'BVPS (VND)', key: 'bvps_vnd', format: 'currency' }
      ]
    },
    {
      title: 'Khả năng sinh lời',
      ratios: [
        { label: 'ROE (%)', key: 'roe', format: 'percent' },
        { label: 'ROA (%)', key: 'roa', format: 'percent' },
        { label: 'ROIC (%)', key: 'roic', format: 'percent' },
        { label: 'Gross Margin (%)', key: 'gross_margin', format: 'percent' },
        { label: 'EBIT Margin (%)', key: 'ebit_margin', format: 'percent' },
        { label: 'Net Margin (%)', key: 'net_profit_margin', format: 'percent' }
      ]
    },
    {
      title: 'Hiệu quả hoạt động',
      ratios: [
        { label: 'Asset Turnover', key: 'asset_turnover', format: 'ratio' },
        { label: 'Fixed Asset Turnover', key: 'fixed_asset_turnover', format: 'ratio' },
        { label: 'Inventory Turnover', key: 'inventory_turnover', format: 'ratio' },
        { label: 'DSO (ngày)', key: 'days_sales_outstanding', format: 'number' },
        { label: 'DIO (ngày)', key: 'days_inventory_outstanding', format: 'number' },
        { label: 'DPO (ngày)', key: 'days_payable_outstanding', format: 'number' },
        { label: 'CCC (ngày)', key: 'cash_conversion_cycle', format: 'number' }
      ]
    },
    {
      title: 'Thanh khoản & Đòn bẩy',
      ratios: [
        { label: 'Current Ratio', key: 'current_ratio', format: 'ratio' },
        { label: 'Quick Ratio', key: 'quick_ratio', format: 'ratio' },
        { label: 'Cash Ratio', key: 'cash_ratio', format: 'ratio' },
        { label: 'D/E', key: 'debt_to_equity', format: 'ratio' },
        { label: 'D/E (Adj.)', key: 'debt_to_equity_adjusted', format: 'ratio' },
        { label: 'Financial Leverage', key: 'financial_leverage', format: 'ratio' },
        { label: 'Interest Coverage', key: 'interest_coverage_ratio', format: 'ratio' }
      ]
    },
    {
      title: 'Khác',
      ratios: [
        { label: 'Market Cap (tỷ)', key: 'market_cap_billions', format: 'number' },
        { label: 'Dividend Payout (%)', key: 'dividend_payout_ratio', format: 'percent' },
        { label: 'Beta', key: 'beta', format: 'number' }
      ]
    }
  ];

  let html = '';
  ratioGroups.forEach(group => {
    // Filter ratios that have values
    const visibleRatios = group.ratios.filter(r => data[r.key] !== null && data[r.key] !== undefined);
    if (visibleRatios.length === 0) return;

    html += `<tr class="section-header"><td colspan="2">${group.title}</td></tr>`;
    visibleRatios.forEach(ratio => {
      const value = data[ratio.key];
      let formattedValue = '-';
      if (value !== null && value !== undefined) {
        switch (ratio.format) {
          case 'percent': formattedValue = formatPercent(value); break;
          case 'ratio': formattedValue = formatRatio(value); break;
          case 'currency': formattedValue = formatNumber(value, 0); break;
          default: formattedValue = formatNumber(value, 2);
        }
      }

      // Get unit for chart
      let unit = '';
      if (ratio.format === 'percent') unit = '%';
      else if (ratio.format === 'ratio') unit = 'x';
      else if (ratio.format === 'currency') unit = 'VND';

      // Add click handler
      const clickHandler = `onclick="handleMetricRowClick('${ratio.key}', 'financial_ratios', '${ratio.label}', '${unit}')"`;

      html += `<tr ${clickHandler}><td class="indent-1">${ratio.label}</td><td class="number">${formattedValue}</td></tr>`;
    });
  });

  document.getElementById('ratiosTable').innerHTML = `
    <thead><tr><th>Chỉ số</th><th style="text-align: right;">Giá trị</th></tr></thead>
    <tbody>${html}</tbody>
  `;
}

// ============================================================================
// COMPARISON FUNCTIONS
// ============================================================================

function setupComparison(currentSymbol) {
  ensureCompareBaseSymbol(currentSymbol);

  const addInput = document.getElementById('compareAddInput');
  const addBtn = document.getElementById('compareAddBtn');
  setupCompareChartsControls();

  if (addBtn && addInput && addBtn.dataset.bound !== '1') {
    addBtn.dataset.bound = '1';
    addBtn.addEventListener('click', () => addCompareCompany(addInput.value));
  }
  if (addInput && addInput.dataset.bound !== '1') {
    addInput.dataset.bound = '1';
    addInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') addCompareCompany(addInput.value);
    });
  }

  renderCompareList();
  renderCompareTable();
  renderCompareCharts();
}

function ensureCompareBaseSymbol(currentSymbol) {
  const base = (currentSymbol || '').trim().toUpperCase();
  if (!base) return;
  const normalized = (Array.isArray(state.compareList) ? state.compareList : [])
    .map(s => (s || '').trim().toUpperCase())
    .filter(Boolean)
    .filter(s => s !== base);
  state.compareList = [base, ...normalized];
}

async function addCompareCompany(symbol) {
  symbol = symbol.trim().toUpperCase();
  if (!symbol || symbol.length < 2) return;
  if (state.compareList[0] && symbol === state.compareList[0]) return;
  if (state.compareList.includes(symbol)) return;

  state.compareList.push(symbol);
  document.getElementById('compareAddInput').value = '';

  await renderCompareList();
  await renderCompareTable();
  await renderCompareCharts();
}

function removeCompareCompany(symbol) {
  const base = state.compareList[0];
  if (base && symbol === base) return;
  state.compareList = state.compareList.filter(s => s !== symbol);
  renderCompareList();
  renderCompareTable();
  renderCompareCharts();
}

async function renderCompareList() {
  const container = document.getElementById('compareSelected');
  if (!container) return;
  const base = state.compareList[0];
  container.innerHTML = state.compareList.map((symbol, idx) => {
    const isBase = Boolean(base) && symbol === base && idx === 0;
    const pillStyle = isBase
      ? 'background: rgba(59, 130, 246, 0.14); border: 1px solid rgba(59, 130, 246, 0.35);'
      : 'background: var(--bg-tertiary);';
    const badge = isBase
      ? '<span style="font-size: 10px; font-weight: 800; letter-spacing: 0.06em; color: #93c5fd;">BASE</span>'
      : '';
    const removeBtn = isBase
      ? ''
      : `<button onclick="removeCompareCompany('${symbol}')" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: var(--text-lg);">×</button>`;
    return `
      <span style="display: inline-flex; align-items: center; gap: var(--space-2); padding: var(--space-1) var(--space-3); ${pillStyle} border-radius: var(--radius-full); font-size: var(--text-sm);">
        ${symbol}
        ${badge}
        ${removeBtn}
      </span>
    `;
  }).join('');
}

async function renderCompareTable() {
  const container = document.getElementById('compareTable');

  if (state.compareList.length < 2) {
    const base = state.compareList[0] || state.currentSymbol || '';
    container.innerHTML = `<p style="color: var(--text-secondary);">Thêm ít nhất 1 công ty để so sánh với <strong>${base}</strong></p>`;
    return;
  }

  try {
    // Fetch ratios for all companies
    const promises = state.compareList.map(symbol =>
      API.getFinancialRatios(symbol, state.currentYear).then(data => ({ symbol, data }))
    );
    const results = await Promise.all(promises);

    const compareMetrics = [
      { label: 'P/E', key: 'price_to_earnings', format: 'number', direction: 'lower', hint: '↓ tốt' },
      { label: 'P/B', key: 'price_to_book', format: 'number', direction: 'lower', hint: '↓ tốt' },
      { label: 'ROE', key: 'roe', format: 'percent', direction: 'higher', hint: '↑ tốt' },
      { label: 'ROA', key: 'roa', format: 'percent', direction: 'higher', hint: '↑ tốt' },
      { label: 'Gross Margin', key: 'gross_margin', format: 'percent', direction: 'higher', hint: '↑ tốt' },
      { label: 'Net Margin', key: 'net_profit_margin', format: 'percent', direction: 'higher', hint: '↑ tốt' },
      { label: 'D/E', key: 'debt_to_equity', format: 'ratio', direction: 'lower', hint: '↓ tốt' },
      { label: 'Current Ratio', key: 'current_ratio', format: 'ratio', direction: 'context', hint: '1.5-2 tốt' },
      { label: 'Asset Turnover', key: 'asset_turnover', format: 'ratio', direction: 'higher', hint: '↑ tốt' },
      { label: 'EPS (VND)', key: 'eps_vnd', format: 'currency', direction: 'higher', hint: '↑ tốt' }
    ];

    const formatValue = (value, format) => {
      if (value === null || value === undefined) return '-';
      switch (format) {
        case 'percent': return formatPercent(value);
        case 'ratio': return formatRatio(value);
        case 'currency': return formatNumber(value, 0);
        default: return formatNumber(value, 2);
      }
    };

    let html = '<table class="data-table"><thead><tr><th>Chỉ tiêu</th>';
    results.forEach(r => {
      html += `<th style="text-align: right;">${r.symbol}</th>`;
    });
    html += '</tr></thead><tbody>';

    compareMetrics.forEach(metric => {
      const hintSpan = metric.hint ? `<span style="font-size: var(--text-xs); color: var(--text-tertiary); font-weight: normal;"> (${metric.hint})</span>` : '';
      html += `<tr><td>${metric.label}${hintSpan}</td>`;
      results.forEach(r => {
        const value = r.data[metric.key];
        html += `<td class="number">${formatValue(value, metric.format)}</td>`;
      });
      html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;

  } catch (error) {
    console.error('Error loading comparison:', error);
    container.innerHTML = '<p style="color: var(--text-danger);">Lỗi tải dữ liệu so sánh</p>';
  }
}

// ============================================================================
// COMPARISON CHARTS (OVERLAP-AWARE)
// ============================================================================

const COMPARE_CHART_METRICS = [
  { id: 'roe', label: 'ROE (%)', source: 'series', table: 'financial_ratios', metric: 'roe', valueType: 'percent', tickDecimals: 1, tooltipDecimals: 2, showBaseline: true },
  { id: 'net_margin', label: 'Net Margin (%)', source: 'series', table: 'financial_ratios', metric: 'net_profit_margin', valueType: 'percent', tickDecimals: 1, tooltipDecimals: 2, showBaseline: true },
  { id: 'de', label: 'D/E (x)', source: 'series', table: 'financial_ratios', metric: 'debt_to_equity', valueType: 'ratio', tickDecimals: 2, tooltipDecimals: 2 },
  { id: 'cr', label: 'Current Ratio (x)', source: 'series', table: 'financial_ratios', metric: 'current_ratio', valueType: 'ratio', tickDecimals: 2, tooltipDecimals: 2 },
  { id: 'pe_end', label: 'P/E (giá cuối năm)', source: 'valuation', valueType: 'ratio', tickDecimals: 1, tooltipDecimals: 2 },
  { id: 'pb_end', label: 'P/B (giá cuối năm)', source: 'valuation', valueType: 'ratio', tickDecimals: 2, tooltipDecimals: 2 },
  { id: 'revenue', label: 'Doanh thu (tỷ VND)', source: 'series', table: 'income_statement', metric: 'net_revenue', valueType: 'currency', tickDecimals: 0, tooltipDecimals: 0 },
  { id: 'net_profit', label: 'Lợi nhuận (tỷ VND)', source: 'series', table: 'income_statement', metric: 'net_profit', valueType: 'currency', tickDecimals: 0, tooltipDecimals: 0 },
];

function setupCompareChartsControls() {
  const wrapper = document.getElementById('compareCharts');
  if (!wrapper) return;
  if (wrapper.dataset.bound === '1') return;
  wrapper.dataset.bound = '1';

  const refreshBtn = document.getElementById('compareChartsRefreshBtn');
  const aSel = document.getElementById('compareASymbolSelect');
  const bSel = document.getElementById('compareBSymbolSelect');
  const yearsSel = document.getElementById('compareYearsSelect');

  if (refreshBtn) refreshBtn.addEventListener('click', () => renderCompareCharts());
  if (aSel) aSel.addEventListener('change', () => renderCompareCharts());
  if (bSel) bSel.addEventListener('change', () => renderCompareCharts());
  if (yearsSel) yearsSel.addEventListener('change', () => renderCompareCharts());
}

function _setSelectOptions(selectEl, options, selectedValue) {
  if (!selectEl) return;
  const safeOptions = Array.isArray(options) ? options : [];
  const html = safeOptions.map(v => `<option value="${v}" ${v === selectedValue ? 'selected' : ''}>${v}</option>`).join('');
  selectEl.innerHTML = html;
}

function _isFiniteNumber(v) {
  return typeof v === 'number' && Number.isFinite(v);
}

function _formatByType(value, valueType, tickDecimals = 2) {
  if (value === null || value === undefined) return 'N/A';
  if (valueType === 'percent') return formatPercent(value);
  if (valueType === 'ratio') return formatRatio(value);
  if (valueType === 'currency') return formatCurrency(value, 'tỷ');
  return formatNumber(value, tickDecimals);
}

async function renderCompareCharts() {
  const wrapper = document.getElementById('compareCharts');
  const grid = document.getElementById('compareChartsGrid');
  const meta = document.getElementById('compareChartsMeta');
  const aSel = document.getElementById('compareASymbolSelect');
  const bSel = document.getElementById('compareBSymbolSelect');
  const yearsSel = document.getElementById('compareYearsSelect');
  if (!wrapper || !grid) return;

  if (!Array.isArray(state.compareList) || state.compareList.length < 2) {
    wrapper.style.display = 'none';
    destroyChartsByPrefix('compareChart_');
    grid.innerHTML = '';
    if (meta) meta.textContent = '';
    return;
  }

  wrapper.style.display = 'block';

  const symbols = state.compareList.slice();
  const base = symbols[0];
  const defaultB = symbols.find(s => s !== base) || symbols[1];

  const desiredA = (aSel?.value || base || '').toUpperCase();
  const desiredB = (bSel?.value || defaultB || '').toUpperCase();

  const symA = symbols.includes(desiredA) ? desiredA : base;
  const symB = symbols.includes(desiredB) && desiredB !== symA ? desiredB : defaultB;

  _setSelectOptions(aSel, symbols, symA);
  _setSelectOptions(bSel, symbols.filter(s => s !== symA), symB);

  const years = yearsSel ? parseInt(yearsSel.value || '10', 10) : 10;
  const count = Number.isFinite(years) ? Math.max(3, Math.min(10, years)) : 10;

  destroyChartsByPrefix('compareChart_');
  grid.innerHTML = `
    <div class="research-viz-item research-viz-item-wide">
      <div style="text-align: center; padding: var(--space-6); color: var(--text-secondary);">
        <div class="loading-spinner"></div>
        <p style="margin-top: var(--space-3);">Đang tải biểu đồ so sánh...</p>
      </div>
    </div>
  `;

  const toYearMapFromMetricSeries = (resp) => {
    const map = new Map();
    const pts = Array.isArray(resp?.data) ? resp.data : [];
    pts.forEach(pt => {
      const y = pt?.year;
      if (y === null || y === undefined) return;
      map.set(Number(y), pt?.value ?? null);
    });
    return map;
  };

  const toYearMapFromValuation = (resp, key) => {
    const map = new Map();
    const pts = Array.isArray(resp?.series) ? resp.series : [];
    pts.forEach(pt => {
      const y = pt?.year;
      if (y === null || y === undefined) return;
      const v = pt?.valuation?.[key];
      map.set(Number(y), (v === null || v === undefined) ? null : Number(v));
    });
    return map;
  };

  try {
    const [valA, valB] = await Promise.all([
      API.getValuationTimeseries(symA, count).catch(() => null),
      API.getValuationTimeseries(symB, count).catch(() => null),
    ]);

    const valuationMaps = {
      [symA]: {
        pe_end: toYearMapFromValuation(valA, 'pe_end'),
        pb_end: toYearMapFromValuation(valA, 'pb_end'),
      },
      [symB]: {
        pe_end: toYearMapFromValuation(valB, 'pe_end'),
        pb_end: toYearMapFromValuation(valB, 'pb_end'),
      }
    };

    const seriesFetches = COMPARE_CHART_METRICS
      .filter(m => m.source === 'series')
      .map(m => Promise.all([
        API.getMetricSeries(symA, m.table, m.metric, 'year', count).then(r => ({ symbol: symA, id: m.id, resp: r })).catch(() => ({ symbol: symA, id: m.id, resp: null })),
        API.getMetricSeries(symB, m.table, m.metric, 'year', count).then(r => ({ symbol: symB, id: m.id, resp: r })).catch(() => ({ symbol: symB, id: m.id, resp: null })),
      ]));

    const fetchedPairs = (await Promise.all(seriesFetches)).flat();

    const metricYearMaps = {};
    fetchedPairs.forEach(item => {
      const symbol = item.symbol;
      if (!metricYearMaps[symbol]) metricYearMaps[symbol] = {};
      metricYearMaps[symbol][item.id] = toYearMapFromMetricSeries(item.resp);
    });

    const candidates = COMPARE_CHART_METRICS.map(m => {
      const mapA = (m.source === 'valuation')
        ? valuationMaps?.[symA]?.[m.id]
        : metricYearMaps?.[symA]?.[m.id];
      const mapB = (m.source === 'valuation')
        ? valuationMaps?.[symB]?.[m.id]
        : metricYearMaps?.[symB]?.[m.id];

      const yearsA = mapA ? Array.from(mapA.keys()) : [];
      const yearsB = mapB ? Array.from(mapB.keys()) : [];
      const yearSetB = new Set(yearsB);
      const intersect = yearsA.filter(y => yearSetB.has(y)).sort((a, b) => a - b);

      const valuesA = intersect.map(y => (mapA ? (mapA.get(y) ?? null) : null));
      const valuesB = intersect.map(y => (mapB ? (mapB.get(y) ?? null) : null));

      const overlapNonNull = intersect.reduce((acc, _y, idx) => {
        const a = valuesA[idx];
        const b = valuesB[idx];
        return acc + ((_isFiniteNumber(a) && _isFiniteNumber(b)) ? 1 : 0);
      }, 0);

      return { metric: m, years: intersect, valuesA, valuesB, overlapNonNull };
    })
      .filter(x => x.years.length >= 3 && x.overlapNonNull >= 2)
      .sort((a, b) => b.overlapNonNull - a.overlapNonNull);

    const selected = candidates.slice(0, 6);
    if (meta) {
      const totalYears = selected.reduce((acc, s) => acc + s.years.length, 0);
      meta.textContent = `A=${symA} · B=${symB} · charts=${selected.length} · years_total=${totalYears}`;
    }

    if (selected.length === 0) {
      grid.innerHTML = `
        <div class="research-viz-item research-viz-item-wide">
          <div style="color: var(--text-secondary);">
            Không đủ dữ liệu chồng lấn để vẽ biểu đồ so sánh (cần ≥ 3 năm trùng nhau cho từng tiêu chí).
          </div>
        </div>
      `;
      return;
    }

    grid.innerHTML = selected.map(s => {
      const canvasId = `compareChart_${s.metric.id}`;
      const metaId = `compareChartMeta_${s.metric.id}`;
      return `
        <div class="research-viz-item">
          <div class="research-viz-header">
            <div class="research-viz-title">${s.metric.label}</div>
            <div class="research-viz-meta-inline" id="${metaId}"></div>
          </div>
          <div class="chart-wrapper">
            <canvas id="${canvasId}"></canvas>
          </div>
        </div>
      `;
    }).join('');

    selected.forEach(s => {
      const labels = s.years.map(y => `FY ${y}`);
      const canvasId = `compareChart_${s.metric.id}`;
      const metaId = `compareChartMeta_${s.metric.id}`;

      const latestIdx = (() => {
        for (let i = s.years.length - 1; i >= 0; i--) {
          if (_isFiniteNumber(s.valuesA[i]) && _isFiniteNumber(s.valuesB[i])) return i;
        }
        return -1;
      })();

      const latestText = latestIdx >= 0
        ? `latest FY ${s.years[latestIdx]}: ${symA}=${_formatByType(s.valuesA[latestIdx], s.metric.valueType, s.metric.tickDecimals)} · ${symB}=${_formatByType(s.valuesB[latestIdx], s.metric.valueType, s.metric.tickDecimals)}`
        : 'latest: N/A';

      const metaEl = document.getElementById(metaId);
      if (metaEl) metaEl.textContent = `years=${s.years.length} · overlap=${s.overlapNonNull}/${s.years.length} · ${latestText}`;

      createMultiLineTrendChart(
        canvasId,
        labels,
        [
          { label: symA, data: s.valuesA, color: CHART_COLORS.compare1, borderWidth: 2, pointRadius: 2 },
          { label: symB, data: s.valuesB, color: CHART_COLORS.compare2, borderWidth: 2, pointRadius: 2 },
        ],
        {
          valueType: s.metric.valueType,
          tickDecimals: s.metric.tickDecimals,
          tooltipDecimals: s.metric.tooltipDecimals,
          showBaseline: Boolean(s.metric.showBaseline),
        }
      );
    });
  } catch (error) {
    console.error('Error rendering compare charts:', error);
    grid.innerHTML = `
      <div class="research-viz-item research-viz-item-wide">
        <div style="color: var(--color-danger-500);">Lỗi tải biểu đồ so sánh</div>
      </div>
    `;
    if (meta) meta.textContent = 'error';
  }
}

// ============================================================================
// EVENT HANDLERS
// ============================================================================

function setupTabSidebarToggle() {
  const layout = document.getElementById('companyTabs');
  const collapseBtn = layout ? layout.querySelector('#tabsCollapseBtn') : null;
  if (!layout || !collapseBtn) return;

  if (layout.dataset.sidebarBound === '1') return;
  layout.dataset.sidebarBound = '1';

  const isCompactViewport = () => window.matchMedia('(max-width: 1100px)').matches;
  state.ui.isTabSidebarCompact = isCompactViewport;

  const readCollapsedState = () => {
    try {
      return localStorage.getItem(TAB_SIDEBAR_STORAGE_KEY) === '1';
    } catch (_err) {
      return false;
    }
  };

  const writeCollapsedState = (collapsed) => {
    try {
      localStorage.setItem(TAB_SIDEBAR_STORAGE_KEY, collapsed ? '1' : '0');
    } catch (_err) {
      // Ignore storage errors
    }
  };

  const applyCollapsedUI = (collapsed) => {
    layout.classList.toggle('tabs-layout-collapsed', collapsed);
    collapseBtn.textContent = collapsed ? '⮞' : '⮜';
    collapseBtn.title = collapsed ? 'Mở rộng menu' : 'Thu gọn menu';
    collapseBtn.setAttribute('aria-label', collapsed ? 'Mở rộng menu tab' : 'Thu gọn menu tab');
    collapseBtn.setAttribute('aria-expanded', String(!collapsed));
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => reflowVisibleCharts());
    });
  };

  let collapsed = readCollapsedState();
  const setCollapsed = (nextCollapsed, persist = true) => {
    collapsed = Boolean(nextCollapsed);
    if (persist) writeCollapsedState(collapsed);
    applyCollapsedUI(collapsed);
  };

  state.ui.setTabSidebarCollapsed = setCollapsed;
  applyCollapsedUI(collapsed);

  collapseBtn.addEventListener('click', () => {
    setCollapsed(!collapsed, true);
  });
}

function setupTabs() {
  setupTabSidebarToggle();
  setupChartReflowListeners();

  const tabsRoot = document.getElementById('companyTabs');
  if (!tabsRoot) return;
  if (tabsRoot.dataset.tabsBound === '1') return;
  tabsRoot.dataset.tabsBound = '1';

  const tabsList = tabsRoot.querySelector('.tabs-list');
  const tabButtons = Array.from(tabsRoot.querySelectorAll('.tab-button'));
  const tabContents = Array.from(tabsRoot.querySelectorAll('.tab-content'));
  if (!tabsList || tabButtons.length === 0 || tabContents.length === 0) return;

  tabsList.addEventListener('click', (e) => {
    const button = e.target.closest('.tab-button');
    if (!button || !tabsList.contains(button)) return;

    const tabId = button.dataset.tab;
    if (!tabId) return;

    tabButtons.forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');

    tabContents.forEach(content => content.classList.remove('active'));
    const panelId = `tab${tabId.charAt(0).toUpperCase() + tabId.slice(1)}`;
    const panel = tabsRoot.querySelector(`#${panelId}`);
    if (panel) panel.classList.add('active');

    // Load Piotroski F-Score and Dividend Analysis when Advanced tab is clicked
    if (tabId === 'advanced') {
      loadValuationResearch();
      loadResearchVisualizations();
      loadPiotroskiFScore();
      loadDividendAnalysis();
      loadEarlyWarning();
      loadRiskAnalysis();
      loadTTMFundamentals();
    }

    if (tabId === 'compare') {
      renderCompareTable();
      renderCompareCharts();
    }

    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => reflowVisibleCharts());
    });
  });
}

function setupSearch() {
  if (state.ui.searchBound) return;
  state.ui.searchBound = true;

  const searchInput = document.getElementById('searchInput');
  const searchResults = document.getElementById('searchResults');
  if (!searchInput || !searchResults) return;
  let debounceTimer;

  const isTypingInInput = (el) => {
    if (!el) return false;
    const tag = String(el.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
    return !!el.isContentEditable;
  };

  const ensureSearchVisible = () => {
    const rect = searchInput.getBoundingClientRect();
    const viewH = window.innerHeight || document.documentElement.clientHeight || 0;
    if (rect.top < 0 || rect.bottom > viewH) {
      try {
        searchInput.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (_err) {
        // Ignore scroll errors
      }
    }
  };

  const focusSearch = ({ select = true } = {}) => {
    ensureSearchVisible();
    try {
      searchInput.focus({ preventScroll: true });
    } catch (_err) {
      searchInput.focus();
    }
    if (select && typeof searchInput.select === 'function') {
      try { searchInput.select(); } catch (_err) { }
    }
  };

  const quickSearchFab = document.getElementById('quickSearchFab');
  if (quickSearchFab) quickSearchFab.addEventListener('click', () => focusSearch({ select: true }));

  document.addEventListener('keydown', (e) => {
    if (!e || e.defaultPrevented) return;

    const isMac = (() => {
      try {
        return /mac|iphone|ipad|ipod/i.test(String(navigator.platform || ''));
      } catch (_err) {
        return false;
      }
    })();

    const key = String(e.key || '');
    const lower = key.toLowerCase();
    const modPressed = isMac ? e.metaKey : e.ctrlKey;
    const isModK = modPressed && lower === 'k' && !e.altKey;
    const isSlash = key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey;

    if (isModK || (isSlash && !isTypingInInput(document.activeElement))) {
      e.preventDefault();
      focusSearch({ select: true });
    }
  });

  searchInput.addEventListener('input', async (e) => {
    const query = e.target.value.trim().toUpperCase();
    clearTimeout(debounceTimer);

    if (query.length < 1) {
      searchResults.style.display = 'none';
      return;
    }

    debounceTimer = setTimeout(async () => {
      try {
        const results = await API.searchCompanies(query);

        if (results.length === 0) {
          searchResults.innerHTML = '<div style="padding: var(--space-4); text-align: center; color: var(--text-secondary);">Không tìm thấy kết quả</div>';
        } else {
          searchResults.innerHTML = results.slice(0, 10).map(company => `
            <div class="search-result-item" data-symbol="${company.ticker}">
              <div class="search-result-ticker">${company.ticker}</div>
              <div class="search-result-info">
                <div class="search-result-name">${company.name || company.ticker}</div>
                <div class="search-result-industry">${company.industry || ''}</div>
              </div>
            </div>
          `).join('');

          searchResults.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
              const symbol = item.dataset.symbol;
              searchResults.style.display = 'none';
              searchInput.value = '';
              navigateToCompany(symbol);
            });
          });
        }

        searchResults.style.display = 'block';
      } catch (error) {
        console.error('Search error:', error);
      }
    }, 300);
  });

  document.addEventListener('click', (e) => {
    const tabSearchBtn = e.target && e.target.closest ? e.target.closest('#tabsSearchBtn') : null;
    if (tabSearchBtn) {
      focusSearch({ select: true });
      return;
    }

    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
      searchResults.style.display = 'none';
    }
  });

  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      const query = searchInput.value.trim().toUpperCase();
      if (query.length >= 1) {
        navigateToCompany(query);
        searchResults.style.display = 'none';
        searchInput.value = '';
      }
    }
  });
}

function setupNav() {
  const rankingsBtn = document.getElementById('rankingsNavBtn');
  if (rankingsBtn && rankingsBtn.dataset.bound !== '1') {
    rankingsBtn.dataset.bound = '1';
    rankingsBtn.addEventListener('click', () => navigateToRankings());
  }
}

async function loadIndustries() {
  try {
    const industries = await API.getIndustries();
    const grid = document.getElementById('industryGrid');

    const industryIcons = {
      'Ngân hàng': '🏦', 'Bất động sản': '🏠', 'Thép': '🏭', 'Công nghệ': '💻',
      'Bán lẻ': '🛒', 'Dược phẩm': '💊', 'Xây dựng': '🏗️', 'Vận tải': '🚚',
      'Điện': '⚡', 'Khí đốt': '🔥', 'default': '🏢'
    };

    grid.innerHTML = industries.map(industry => `
      <div class="industry-card" data-name="${industry.name}">
        <div class="industry-icon">${industryIcons[industry.name] || industryIcons.default}</div>
        <div class="industry-name">${industry.name}</div>
        <div class="industry-count">${industry.count || 0} công ty</div>
      </div>
    `).join('');

    grid.querySelectorAll('.industry-card').forEach(card => {
      card.addEventListener('click', async () => {
        const industryName = card.dataset.name;
        const companies = await API.getCompaniesByIndustry(industryName);
        if (companies.length > 0) {
          // Navigate to first company
          navigateToCompany(companies[0].ticker);
        }
      });
    });
  } catch (error) {
    console.error('Error loading industries:', error);
  }
}

function navigateToCompany(symbol) {
  history.pushState({ symbol }, '', `/company/${symbol}`);
  renderCompanyDetail(symbol);
}

function navigateToRankings() {
  history.pushState({ view: 'rankings' }, '', `/rankings`);
  renderRankings();
}

function showLoading() {
  // Could implement a loading spinner here
}

function showError(message) {
  alert(message);
}

// ============================================================================
// ROUTING
// ============================================================================

function handleRoute() {
  const path = window.location.pathname;

  if (path.startsWith('/company/')) {
    const symbol = path.split('/')[2];
    renderCompanyDetail(symbol);
  } else if (path.startsWith('/rankings')) {
    renderRankings();
  } else {
    renderDashboard();
  }
}

window.addEventListener('popstate', (e) => {
  handleRoute();
});

// ============================================================================
// METRIC CHART MODAL
// ============================================================================

// Metric to table mapping
const METRIC_TABLE_MAP = {
  // Financial Ratios
  'price_to_earnings': { table: 'financial_ratios', label: 'P/E', unit: 'x' },
  'price_to_book': { table: 'financial_ratios', label: 'P/B', unit: 'x' },
  'price_to_sales': { table: 'financial_ratios', label: 'P/S', unit: 'x' },
  'ev_to_ebitda': { table: 'financial_ratios', label: 'EV/EBITDA', unit: 'x' },
  'eps_vnd': { table: 'financial_ratios', label: 'EPS', unit: 'VND' },
  'bvps_vnd': { table: 'financial_ratios', label: 'BVPS', unit: 'VND' },
  'roe': { table: 'financial_ratios', label: 'ROE', unit: '%' },
  'roa': { table: 'financial_ratios', label: 'ROA', unit: '%' },
  'roic': { table: 'financial_ratios', label: 'ROIC', unit: '%' },
  'gross_margin': { table: 'financial_ratios', label: 'Gross Margin', unit: '%' },
  'ebit_margin': { table: 'financial_ratios', label: 'EBIT Margin', unit: '%' },
  'net_profit_margin': { table: 'financial_ratios', label: 'Net Margin', unit: '%' },
  'asset_turnover': { table: 'financial_ratios', label: 'Asset Turnover', unit: 'x' },
  'inventory_turnover': { table: 'financial_ratios', label: 'Inventory Turnover', unit: 'x' },
  'current_ratio': { table: 'financial_ratios', label: 'Current Ratio', unit: 'x' },
  'quick_ratio': { table: 'financial_ratios', label: 'Quick Ratio', unit: 'x' },
  'cash_ratio': { table: 'financial_ratios', label: 'Cash Ratio', unit: 'x' },
  'debt_to_equity': { table: 'financial_ratios', label: 'D/E', unit: 'x' },
  'financial_leverage': { table: 'financial_ratios', label: 'Fin. Leverage', unit: 'x' },
  'interest_coverage_ratio': { table: 'financial_ratios', label: 'Interest Coverage', unit: 'x' },
  'dividend_payout_ratio': { table: 'financial_ratios', label: 'Dividend Payout', unit: '%' },
  'days_sales_outstanding': { table: 'financial_ratios', label: 'DSO', unit: 'ngày' },
  'days_inventory_outstanding': { table: 'financial_ratios', label: 'DIO', unit: 'ngày' },
  'cash_conversion_cycle': { table: 'financial_ratios', label: 'CCC', unit: 'ngày' },
  'beta': { table: 'financial_ratios', label: 'Beta', unit: '' },
  // Balance Sheet
  'asset_current': { table: 'balance_sheet', label: 'Tài sản ngắn hạn', unit: 'tỷ' },
  'asset_non_current': { table: 'balance_sheet', label: 'Tài sản dài hạn', unit: 'tỷ' },
  'total_assets': { table: 'balance_sheet', label: 'Tổng tài sản', unit: 'tỷ' },
  'cash_and_equivalents': { table: 'balance_sheet', label: 'Tiền và tương đương', unit: 'tỷ' },
  'inventory': { table: 'balance_sheet', label: 'Hàng tồn kho', unit: 'tỷ' },
  'fixed_assets': { table: 'balance_sheet', label: 'Tài sản cố định', unit: 'tỷ' },
  'liabilities_current': { table: 'balance_sheet', label: 'Nợ ngắn hạn', unit: 'tỷ' },
  'liabilities_total': { table: 'balance_sheet', label: 'Tổng nợ', unit: 'tỷ' },
  'equity_total': { table: 'balance_sheet', label: 'Vốn chủ sở hữu', unit: 'tỷ' },
  // Income Statement
  'net_revenue': { table: 'income_statement', label: 'Doanh thu thuần', unit: 'tỷ' },
  'gross_profit': { table: 'income_statement', label: 'Lợi nhuận gộp', unit: 'tỷ' },
  'operating_profit': { table: 'income_statement', label: 'Lợi nhuận HĐ', unit: 'tỷ' },
  'profit_before_tax': { table: 'income_statement', label: 'LN trước thuế', unit: 'tỷ' },
  'net_profit': { table: 'income_statement', label: 'LN sau thuế', unit: 'tỷ' },
  // Cash Flow
  'net_cash_from_operating_activities': { table: 'cash_flow_statement', label: 'Dòng tiền HĐKD', unit: 'tỷ' },
  'net_cash_from_investing_activities': { table: 'cash_flow_statement', label: 'Dòng tiền HĐĐT', unit: 'tỷ' },
  'net_cash_from_financing_activities': { table: 'cash_flow_statement', label: 'Dòng tiền HĐTC', unit: 'tỷ' },
  'net_cash_flow_period': { table: 'cash_flow_statement', label: 'Dòng tiền thuần', unit: 'tỷ' }
};

/**
 * Open metric chart modal
 */
function openMetricChart(metric, table, label, unit) {
  if (!state.currentSymbol) return;

  // Update state
  state.metricChart = { metric, table, label, unit };

  // Update modal title
  document.getElementById('metricChartTitle').textContent = `${label} - ${state.currentSymbol}`;

  // Reset selectors
  document.getElementById('chartPeriodSelect').value = 'year';
  document.getElementById('quarterCountGroup').style.display = 'none';
  document.getElementById('yearCountGroup').style.display = 'flex';

  // Show modal
  document.getElementById('metricChartModal').style.display = 'flex';

  // Load chart
  updateMetricChart();
}

/**
 * Close metric chart modal
 */
function closeMetricChart() {
  document.getElementById('metricChartModal').style.display = 'none';

  // Destroy chart
  if (state.charts['metricDetailChart']) {
    state.charts['metricDetailChart'].destroy();
    delete state.charts['metricDetailChart'];
  }
}

/**
 * Update metric chart based on current selections
 */
async function updateMetricChart() {
  const { metric, table, label, unit } = state.metricChart;
  const period = document.getElementById('chartPeriodSelect').value;

  let count;
  if (period === 'quarter') {
    count = parseInt(document.getElementById('chartCountSelect').value);
    document.getElementById('quarterCountGroup').style.display = 'flex';
    document.getElementById('yearCountGroup').style.display = 'none';
  } else {
    count = parseInt(document.getElementById('yearCountSelect').value);
    document.getElementById('quarterCountGroup').style.display = 'none';
    document.getElementById('yearCountGroup').style.display = 'flex';
  }

  try {
    const response = await fetch(
      `/api/financials/${state.currentSymbol}/series/${table}/${metric}?period=${period}&count=${count}`
    );
    const data = await response.json();

    if (!data.data || data.data.length === 0) {
      document.getElementById('metricDetailChart').parentElement.innerHTML =
        '<p style="text-align: center; color: var(--text-secondary); padding: 50px;">Không có dữ liệu</p>';
      return;
    }

    renderMetricDetailChart(data, label, unit);
  } catch (error) {
    console.error('Error loading metric chart:', error);
  }
}

/**
 * Render the metric detail chart
 */
function renderMetricDetailChart(data, label, unit) {
  const canvas = document.getElementById('metricDetailChart');

  // Restore canvas if it was replaced
  const wrapper = canvas.parentElement;
  if (!canvas || canvas.tagName !== 'CANVAS') {
    wrapper.innerHTML = '<canvas id="metricDetailChart"></canvas>';
  }

  const ctx = document.getElementById('metricDetailChart');

  // Destroy existing chart
  if (state.charts['metricDetailChart']) {
    state.charts['metricDetailChart'].destroy();
    delete state.charts['metricDetailChart'];
  }

  // Set fixed dimensions
  ctx.width = 650;
  ctx.height = 280;
  ctx.style.width = '650px';
  ctx.style.height = '280px';

  // Preserve null/undefined values for gaps - don't convert to 0
  const values = data.data.map(d => d.value);
  const labels = data.labels;

  // Determine color based on trend
  const isPositive = values.length >= 2 && values[values.length - 1] >= values[0];
  const lineColor = isPositive ? '#22c55e' : '#ef4444';

  // Format Y axis based on unit
  let yAxisCallback;
  if (unit === '%') {
    yAxisCallback = value => (value * 100).toFixed(1) + '%';
  } else if (unit === 'tỷ') {
    yAxisCallback = value => (value / 1e9).toFixed(0) + ' tỷ';
  } else if (unit === 'VND') {
    yAxisCallback = value => value.toLocaleString('vi-VN');
  } else {
    yAxisCallback = value => value.toFixed(2);
  }

  // Add ARIA label for accessibility
  const metricKey = label.toLowerCase().replace(/[^a-z_]/g, '_');
  const explanation = METRIC_EXPLANATIONS[metricKey] || `${label}: Chỉ số tài chính`;
  ctx.setAttribute('aria-label', `Biểu đồ chi tiết ${label} qua ${labels.length} kỳ. ${explanation}`);
  ctx.setAttribute('role', 'img');

  // Build datasets - preserve null/undefined for gaps in chart
  const datasets = [{
    label: label,
    data: values,
    borderColor: lineColor,
    backgroundColor: lineColor + '20',
    fill: true,
    tension: 0.3,
    pointRadius: 5,
    pointHoverRadius: 7,
    pointBackgroundColor: lineColor,
    spanGaps: false  // Don't connect lines across null/undefined values
  }];

  // Add 0% baseline for percentage metrics
  if (unit === '%') {
    datasets.push({
      label: 'Baseline (0%)',
      data: new Array(labels.length).fill(0),
      borderColor: 'rgba(156, 163, 175, 0.6)',
      backgroundColor: 'transparent',
      borderDash: [3, 3],
      borderWidth: 1,
      pointRadius: 0,
      pointHoverRadius: 0,
      fill: false,
      tension: 0
    });
  }

  const chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: false,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
          labels: {
            filter: function (item) {
              return item.text !== 'Baseline (0%)';
            }
          }
        },
        tooltip: {
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          titleColor: '#f3f4f6',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            title: function (context) {
              return `Kỳ ${context[0].label}`;
            },
            label: function (context) {
              // Skip baseline in tooltip
              if (context.dataset.label === 'Baseline (0%)') return null;

              // Handle missing data
              if (context.parsed.y === null) {
                return `${label}: Không có dữ liệu`;
              }

              let value = context.parsed.y;
              if (unit === '%') {
                return `${label}: ${(value * 100).toFixed(2)}%`;
              } else if (unit === 'tỷ') {
                return `${label}: ${(value / 1e9).toFixed(1)} tỷ VND`;
              }
              return `${label}: ${value.toLocaleString('vi-VN')} ${unit}`;
            },
            afterBody: function (context) {
              // Add explanation
              const metricKey = label.toLowerCase().replace(/[^a-z_]/g, '_');
              const explanation = METRIC_EXPLANATIONS[metricKey];
              if (explanation) {
                return ['', '💡 ' + explanation];
              }
              return [];
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#374151' },
          ticks: { color: '#9ca3af' }
        },
        y: {
          grid: { color: '#374151' },
          ticks: {
            color: '#9ca3af',
            callback: yAxisCallback
          }
        }
      },
      animation: {
        duration: 500,
        easing: 'easeOutQuart'
      }
    }
  });

  state.charts['metricDetailChart'] = chart;
}

/**
 * Handle click on table row - show chart for that metric
 */
function handleMetricRowClick(metric, table, label, unit) {
  openMetricChart(metric, table, label, unit);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  setupHelpTips();
  setupSearch();
  setupNav();
  handleRoute();
});

// ============================================================================
// PIOTROSKI F-SCORE ANALYSIS
// ============================================================================

/**
 * Render Piotroski F-Score component
 * @param {Object} fScoreData - F-Score data from API
 */
function renderPiotroskiFScore(fScoreData) {
  const container = document.getElementById('piotroskiSection');
  if (!container) return;

  if (!fScoreData || fScoreData.score === undefined || fScoreData.score === null) {
    container.innerHTML = `
      <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
        <p>Không có dữ liệu Piotroski F-Score</p>
      </div>
    `;
    return;
  }

  const score = fScoreData.score;
  const criteria = fScoreData.criteria || {};

  // Determine rating and color class
  let ratingClass, ratingText;
  if (score >= 7) {
    ratingClass = 'strong';
    ratingText = 'Mạnh';
  } else if (score >= 4) {
    ratingClass = 'medium';
    ratingText = 'Trung bình';
  } else {
    ratingClass = 'weak';
    ratingText = 'Yếu';
  }

  // Calculate progress percentage (score is 0-9)
  const progressPercent = (score / 9) * 100;

  // Build criteria groups
  const profitabilityCriteria = [
    { key: 'roa_positive', name: 'ROA > 0', desc: 'Lợi nhuận trên tài sản dương' },
    { key: 'ocf_positive', name: 'Dòng tiền KD > 0', desc: 'Dòng tiền từ hoạt động kinh doanh dương' },
    { key: 'roa_improving', name: 'ROA cải thiện', desc: 'ROA năm nay tốt hơn năm trước' },
    { key: 'ocf_gt_net_income', name: 'Dòng tiền > LN', desc: 'Dòng tiền KD lớn hơn lợi nhuận ròng' }
  ];

  const leverageCriteria = [
    { key: 'leverage_decreasing', name: 'Đòn bẩy giảm', desc: 'Tỷ lệ nợ trên tài sản giảm' },
    { key: 'current_ratio_increasing', name: 'Thanh khoản ↑', desc: 'Tỷ lệ thanh khoản hiện hành cải thiện' },
    { key: 'no_new_shares', name: 'Không phát hành mới', desc: 'Không phát hành thêm cổ phiếu' }
  ];

  const efficiencyCriteria = [
    { key: 'gross_margin_increasing', name: 'Biên LN gộp ↑', desc: 'Biên lợi nhuận gộp cải thiện' },
    { key: 'asset_turnover_increasing', name: 'Vòng quay TS ↑', desc: 'Vòng quay tài sản cải thiện' }
  ];

  const renderCriterion = (criterion) => {
    const passed = criteria[criterion.key] === true;
    const statusClass = passed ? 'pass' : 'fail';
    const statusText = passed ? 'Đạt' : 'Chưa đạt';

    return `
      <div class="f-score-criterion-card ${statusClass}">
        <div class="f-score-criterion-top">
          <div class="f-score-criterion-name-wrap">
            <span class="f-score-criterion-marker ${statusClass}" aria-hidden="true"></span>
            <div class="f-score-criterion-name">${criterion.name}</div>
          </div>
          <span class="f-score-status-chip ${statusClass}">${statusText}</span>
        </div>
        <div class="f-score-criterion-content">
          <div class="f-score-criterion-desc">${criterion.desc}</div>
        </div>
      </div>
    `;
  };

  const renderCriteriaGroup = (groupTitle, icon, groupCriteria) => {
    const passedCount = groupCriteria.filter((criterion) => criteria[criterion.key] === true).length;
    const totalCount = groupCriteria.length;

    return `
      <div class="f-score-criteria-group">
        <div class="f-score-group-header">
          <div class="f-score-group-title">
            <span class="icon">${icon}</span>
            ${groupTitle}
          </div>
          <div class="f-score-group-score">${passedCount}/${totalCount} đạt</div>
        </div>
        <div class="f-score-group-list">
          ${groupCriteria.map(renderCriterion).join('')}
        </div>
      </div>
    `;
  };

  container.innerHTML = `
    <div class="f-score-container">
      <!-- Header with Score -->
      <div class="f-score-header">
        <div class="f-score-main">
          <div class="f-score-value-container">
            <div class="f-score-value ${ratingClass}">${score}<span class="f-score-denominator">/9</span></div>
            <div class="f-score-label">Piotroski F-Score</div>
          </div>
          
          <div class="f-score-rating ${ratingClass}">
            <span class="f-score-rating-dot ${ratingClass}" aria-hidden="true"></span>
            <span>${ratingText}</span>
          </div>
        </div>

        <div class="f-score-progress">
          <div class="f-score-progress-bar">
            <div class="f-score-progress-fill ${ratingClass}" style="width: ${progressPercent}%;"></div>
          </div>
          <div class="f-score-legend">
            <span>0 (Yếu)</span>
            <span>9 (Mạnh)</span>
          </div>
        </div>
      </div>

      <!-- Criteria Breakdown -->
      <div class="f-score-criteria">
        ${renderCriteriaGroup('Khả năng sinh lời', '💰', profitabilityCriteria)}
        ${renderCriteriaGroup('Đòn bẩy', '⚖️', leverageCriteria)}
        ${renderCriteriaGroup('Hiệu quả', '📈', efficiencyCriteria)}
      </div>
    </div>
  `;
}

// ============================================================================
// VALUATION RESEARCH (P2): Bands / Fair-price overlay / Decomposition / Peers
// ============================================================================

function setupValuationResearchControls() {
  const refreshBtn = document.getElementById('valuationResearchRefreshBtn');
  const peerRefreshBtn = document.getElementById('peerDistRefreshBtn');

  if (refreshBtn && refreshBtn.dataset.bound !== '1') {
    refreshBtn.dataset.bound = '1';
    refreshBtn.addEventListener('click', () => {
      loadValuationResearch();
    });

    const yearsSelect = document.getElementById('valuationYearsSelect');
    const horizonSelect = document.getElementById('valuationHorizonSelect');
    if (yearsSelect) yearsSelect.addEventListener('change', () => loadValuationResearch());
    if (horizonSelect) horizonSelect.addEventListener('change', () => loadValuationResearch());
  }

  if (peerRefreshBtn && peerRefreshBtn.dataset.bound !== '1') {
    peerRefreshBtn.dataset.bound = '1';
    peerRefreshBtn.addEventListener('click', () => {
      loadPeerDistributionChart();
    });

    const metricSelect = document.getElementById('peerDistMetricSelect');
    if (metricSelect) metricSelect.addEventListener('change', () => loadPeerDistributionChart());
  }
}

function _setText(elId, text) {
  const el = document.getElementById(elId);
  if (el) el.textContent = text || '';
}

async function loadValuationResearch() {
  if (!state.currentSymbol) return;

  setupValuationResearchControls();

  const years = parseInt(document.getElementById('valuationYearsSelect')?.value || '10');
  const horizonYears = parseInt(document.getElementById('valuationHorizonSelect')?.value || '5');

  _setText('valuationResearchMeta', 'Đang tải...');

  try {
    const [ts, decomp] = await Promise.all([
      API.getValuationTimeseries(state.currentSymbol, years),
      API.getValuationDecomposition(state.currentSymbol, horizonYears)
    ]);

    if (ts?.error) {
      _setText('valuationResearchMeta', ts.error);
      _setText('peBandMeta', 'N/A');
      _setText('pbBandMeta', 'N/A');
      _setText('fairOverlayMeta', 'N/A');
    } else {
      renderValuationBands(ts);
      renderFairOverlay(ts);
      const y = Array.isArray(ts.years) ? ts.years : [];
      if (y.length > 0) _setText('valuationResearchMeta', `FY ${y[0]}–${y[y.length - 1]} · close=year-end · n=${y.length}`);
      else _setText('valuationResearchMeta', 'Không có dữ liệu');
    }

    if (decomp?.error) {
      _setText('returnDecompMeta', decomp.error);
    } else {
      renderReturnDecomposition(decomp);
    }

    await loadPeerDistributionChart();
  } catch (error) {
    console.error('Error loading valuation research:', error);
    _setText('valuationResearchMeta', 'Lỗi tải dữ liệu');
  }
}

function renderValuationBands(ts) {
  const years = Array.isArray(ts?.years) ? ts.years : [];
  const labels = years.map(y => y.toString());
  const series = Array.isArray(ts?.series) ? ts.series : [];

  const pe = series.map(pt => pt?.valuation?.pe_end ?? null).map(v => (!isMissing(v) && v > 0 ? v : null));
  const pb = series.map(pt => pt?.valuation?.pb_end ?? null).map(v => (!isMissing(v) && v > 0 ? v : null));

  const peBand = ts?.bands?.pe_end || {};
  const pbBand = ts?.bands?.pb_end || {};

  const peNonMissing = pe.filter(v => !isMissing(v)).length;
  const pbNonMissing = pb.filter(v => !isMissing(v)).length;

  createValuationBandChart('peBandChart', labels, pe, peBand, {
    companyLabel: 'P/E',
    companyColor: CHART_COLORS.pe,
    bandFill: 'rgba(139, 92, 246, 0.12)',
  });
  createValuationBandChart('pbBandChart', labels, pb, pbBand, {
    companyLabel: 'P/B',
    companyColor: CHART_COLORS.pb,
    bandFill: 'rgba(236, 72, 153, 0.10)',
  });

  const fmtBand = (b) => {
    const p25 = b?.p25;
    const p50 = b?.p50;
    const p75 = b?.p75;
    if (isMissing(p25) || isMissing(p50) || isMissing(p75)) return 'band: N/A';
    return `band(P25–P75)=${Number(p25).toFixed(1)}–${Number(p75).toFixed(1)} · P50=${Number(p50).toFixed(1)}`;
  };

  _setText('peBandMeta', `n=${peNonMissing}/${years.length} · ${fmtBand(peBand)}`);
  _setText('pbBandMeta', `n=${pbNonMissing}/${years.length} · ${fmtBand(pbBand)}`);
}

function renderFairOverlay(ts) {
  const years = Array.isArray(ts?.years) ? ts.years : [];
  const labels = years.map(y => y.toString());
  const series = Array.isArray(ts?.series) ? ts.series : [];
  const fairLines = Array.isArray(ts?.fair_lines) ? ts.fair_lines : [];

  const priceEnd = series.map(pt => pt?.price_end?.close ?? null).map(v => (!isMissing(v) && v > 0 ? v : null));

  const fairPe = fairLines.map(pt => pt?.fair_close?.pe_p50 ?? null).map(v => (!isMissing(v) && v > 0 ? v : null));
  const fairPb = fairLines.map(pt => pt?.fair_close?.pb_p50 ?? null).map(v => (!isMissing(v) && v > 0 ? v : null));
  const graham = fairLines.map(pt => pt?.fair_close?.graham ?? null).map(v => (!isMissing(v) && v > 0 ? v : null));

  createMultiLineTrendChart(
    'fairOverlayChart',
    labels,
    [
      { label: 'Giá cuối năm', data: priceEnd, color: '#3b82f6', borderWidth: 2, pointRadius: 3 },
      { label: 'Fair (P/E P50)', data: fairPe, color: CHART_COLORS.pe, dashed: true, borderWidth: 2, pointRadius: 0 },
      { label: 'Fair (P/B P50)', data: fairPb, color: CHART_COLORS.pb, dashed: true, borderWidth: 2, pointRadius: 0 },
      { label: 'Graham', data: graham, color: '#22c55e', dashed: true, borderWidth: 2, pointRadius: 0 },
    ],
    { valueType: 'number', unitSuffix: 'k', tickDecimals: 1, tooltipDecimals: 2, showBaseline: false }
  );

  const nonMissingPrice = priceEnd.filter(v => !isMissing(v)).length;
  _setText('fairOverlayMeta', `FY ${years[0] ?? 'N/A'}–${years[years.length - 1] ?? 'N/A'} · price(n)=${nonMissingPrice}/${years.length} · fair=EPS/BVPS×multiple`);
}

function renderReturnDecomposition(decomp) {
  const p = decomp?.period || {};
  const c = decomp?.components_log_pct || {};

  const labels = ['EPS', 'P/E', 'Div', 'Total'];
  const values = [
    c.eps_growth ?? null,
    c.pe_rerating ?? null,
    c.cash_dividends ?? null,
    c.total ?? null,
  ];

  const colors = values.map((v, idx) => {
    if (idx === labels.length - 1) return 'rgba(59, 130, 246, 0.7)'; // total
    if (isMissing(v)) return 'rgba(148, 163, 184, 0.35)';
    return Number(v) >= 0 ? 'rgba(34, 197, 94, 0.65)' : 'rgba(239, 68, 68, 0.65)';
  });

  createSimpleBarChart('returnDecompositionChart', labels, values, {
    colors,
    borderColor: 'rgba(148, 163, 184, 0.35)',
    unitSuffix: '%',
    decimals: 1,
  });

  const startYear = p.start_year;
  const endYear = p.end_year;
  const used = p.intervals_used;
  _setText('returnDecompMeta', `FY ${startYear ?? 'N/A'}→${endYear ?? 'N/A'} · intervals=${used ?? 'N/A'} · log-return additive`);
}

async function loadPeerDistributionChart() {
  if (!state.currentSymbol) return;
  setupValuationResearchControls();

  const metric = document.getElementById('peerDistMetricSelect')?.value || 'price_to_earnings';
  const year = state.currentYear;

  _setText('peerDistMeta', 'Đang tải...');

  try {
    const data = await API.getPeerDistribution(state.currentSymbol, year, metric, 24);
    if (data?.error) {
      _setText('peerDistMeta', data.error);
      return;
    }

    const bins = data?.histogram?.bins || [];
    const counts = bins.map(b => b.count ?? 0);
    const labels = bins.map(b => (b.center !== null && b.center !== undefined) ? Number(b.center).toFixed(2) : '');

    const companyValue = data?.company_value;
    let highlightIdx = null;
    if (!isMissing(companyValue)) {
      highlightIdx = bins.findIndex((b, idx) => {
        const low = b.low;
        const high = b.high;
        if (isMissing(low) || isMissing(high)) return false;
        if (idx === bins.length - 1) return companyValue >= low && companyValue <= high;
        return companyValue >= low && companyValue < high;
      });
      if (highlightIdx < 0) highlightIdx = null;
    }

    const bgColors = counts.map((_, idx) => (highlightIdx === idx)
      ? 'rgba(59, 130, 246, 0.85)'
      : 'rgba(148, 163, 184, 0.35)'
    );
    const borderColors = counts.map((_, idx) => (highlightIdx === idx)
      ? 'rgba(59, 130, 246, 1)'
      : 'rgba(148, 163, 184, 0.18)'
    );

    createSimpleBarChart('peerDistributionChart', labels, counts, {
      colors: bgColors,
      borderColors: borderColors,
      decimals: 0,
      unitSuffix: '',
    });

    const p = data?.percentiles || {};
    const companyText = !isMissing(companyValue) ? `${Number(companyValue).toFixed(2)}x` : 'N/A';
    const p50 = !isMissing(p.p50) ? `${Number(p.p50).toFixed(2)}x` : 'N/A';
    const meta = `FY${data.year} · peers=${data.peer_count_valid}/${data.peer_count_raw} · excluded=${data.excluded} · company=${companyText} · P50=${p50}`;
    _setText('peerDistMeta', meta);
  } catch (error) {
    console.error('Error loading peer distribution:', error);
    _setText('peerDistMeta', 'Lỗi tải peer distribution');
  }
}

// ============================================================================
// RESEARCH VISUALIZATIONS (P2): Scatter / Radar / Correlation Heatmap
// ============================================================================

function _formatMetricValue(value, unit) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  const v = Number(value);
  if (unit === 'decimal') return (v * 100).toFixed(2) + '%';
  if (unit === 'x') return v.toFixed(2) + 'x';
  if (unit === 'VND') return formatNumber(v, 0) + ' VND';
  return v.toFixed(4);
}

function _metricLabelFromId(metricId) {
  const map = {
    roe: 'ROE',
    roa: 'ROA',
    net_profit_margin: 'Net Margin',
    gross_margin: 'Gross Margin',
    debt_to_equity: 'D/E',
    current_ratio: 'Current Ratio',
    asset_turnover: 'Asset Turnover',
    price_to_earnings: 'P/E',
    price_to_book: 'P/B',
    ev_to_ebitda: 'EV/EBITDA'
  };
  return map[metricId] || metricId;
}

function createPeerScatterChart(canvasId, points, xMeta, yMeta) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  if (state.charts[canvasId]) {
    state.charts[canvasId].destroy();
    delete state.charts[canvasId];
  }

  const height = 320;
  applyCanvasDimensions(canvas, height);

  const peers = (points || []).filter(p => !p.is_target).map(p => ({ x: p.x, y: p.y, symbol: p.symbol }));
  const target = (points || []).filter(p => p.is_target).map(p => ({ x: p.x, y: p.y, symbol: p.symbol }));

  const chart = new Chart(canvas, {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: 'Peers',
          data: peers,
          backgroundColor: 'rgba(148, 163, 184, 0.55)',
          borderColor: 'rgba(148, 163, 184, 0.45)',
          pointRadius: 3,
          pointHoverRadius: 5
        },
        {
          label: state.currentSymbol || 'Target',
          data: target,
          backgroundColor: 'rgba(59, 130, 246, 0.95)',
          borderColor: 'rgba(59, 130, 246, 1)',
          pointRadius: 6,
          pointHoverRadius: 8
        }
      ]
    },
    options: {
      responsive: false,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { color: '#9ca3af', font: { size: 11 }, usePointStyle: true, boxWidth: 6 }
        },
        tooltip: {
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          titleColor: '#f3f4f6',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            title: (items) => {
              const raw = items && items[0] ? items[0].raw : null;
              return raw && raw.symbol ? raw.symbol : 'Peer';
            },
            label: (ctx) => {
              const raw = ctx.raw || {};
              const xText = `${xMeta?.label || 'X'}: ${_formatMetricValue(raw.x, xMeta?.unit)}`;
              const yText = `${yMeta?.label || 'Y'}: ${_formatMetricValue(raw.y, yMeta?.unit)}`;
              return [xText, yText];
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#374151' },
          ticks: {
            color: '#9ca3af',
            callback: (value) => _formatMetricValue(value, xMeta?.unit)
          },
          title: {
            display: true,
            text: xMeta?.label || 'X',
            color: '#9ca3af',
            font: { size: 12, weight: '600' }
          }
        },
        y: {
          grid: { color: '#374151' },
          ticks: {
            color: '#9ca3af',
            callback: (value) => _formatMetricValue(value, yMeta?.unit)
          },
          title: {
            display: true,
            text: yMeta?.label || 'Y',
            color: '#9ca3af',
            font: { size: 12, weight: '600' }
          }
        }
      }
    }
  });

  state.charts[canvasId] = chart;
  return chart;
}

async function loadPeerScatter() {
  if (!state.currentSymbol) return;
  const meta = document.getElementById('peerScatterMeta');
  const xSel = document.getElementById('scatterXSelect');
  const ySel = document.getElementById('scatterYSelect');
  if (!meta || !xSel || !ySel) return;

  meta.textContent = 'Đang tải peer scatter...';

  try {
    const xMetric = xSel.value;
    const yMetric = ySel.value;
    const data = await API.getPeerScatter(state.currentSymbol, state.currentYear, xMetric, yMetric);

    createPeerScatterChart('peerScatterChart', data.points || [], data.x, data.y);

    meta.textContent = `FY ${data.year} · Peers(valid): ${data.peer_count_valid}/${data.peer_count_raw} · Excluded: ${data.excluded}`;
  } catch (error) {
    console.error('Error loading peer scatter:', error);
    meta.textContent = 'Lỗi tải peer scatter';
  }
}

function createPeerRadarChart(canvasId, labels, values) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  if (state.charts[canvasId]) {
    state.charts[canvasId].destroy();
    delete state.charts[canvasId];
  }

  const height = 320;
  applyCanvasDimensions(canvas, height);

  const baseline = new Array(labels.length).fill(50);

  const chart = new Chart(canvas, {
    type: 'radar',
    data: {
      labels,
      datasets: [
        {
          label: 'Company (Percentile, adjusted)',
          data: values,
          borderColor: 'rgba(59, 130, 246, 1)',
          backgroundColor: 'rgba(59, 130, 246, 0.18)',
          pointBackgroundColor: 'rgba(59, 130, 246, 1)',
          pointRadius: 3,
          spanGaps: false
        },
        {
          label: 'Baseline (50)',
          data: baseline,
          borderColor: 'rgba(156, 163, 175, 0.65)',
          backgroundColor: 'transparent',
          borderDash: [4, 4],
          pointRadius: 0,
          spanGaps: false
        }
      ]
    },
    options: {
      responsive: false,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { color: '#9ca3af', font: { size: 11 }, usePointStyle: true, boxWidth: 6 }
        },
        tooltip: {
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          titleColor: '#f3f4f6',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => {
              const v = ctx.parsed?.r;
              if (v === null || v === undefined) return 'N/A';
              return `${ctx.label}: ${Number(v).toFixed(1)}/100`;
            }
          }
        }
      },
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: { display: true, color: '#9ca3af', showLabelBackdrop: false },
          grid: { color: 'rgba(148, 163, 184, 0.22)' },
          angleLines: { color: 'rgba(148, 163, 184, 0.22)' },
          pointLabels: { color: '#d1d5db', font: { size: 11 } }
        }
      }
    }
  });

  state.charts[canvasId] = chart;
  return chart;
}

async function loadPeerRadar() {
  if (!state.currentSymbol) return;
  const meta = document.getElementById('peerRadarMeta');
  if (!meta) return;

  meta.textContent = 'Đang tải radar...';

  try {
    const b = await API.getIndustryBenchmarkForYear(state.currentSymbol, state.currentYear);
    const cvi = b.company_vs_industry || {};

    const metrics = [
      { id: 'roe', lowerBetter: false },
      { id: 'net_profit_margin', lowerBetter: false },
      { id: 'asset_turnover', lowerBetter: false },
      { id: 'current_ratio', lowerBetter: false },
      { id: 'debt_to_equity', lowerBetter: true },
      { id: 'price_to_earnings', lowerBetter: true },
      { id: 'price_to_book', lowerBetter: true },
      { id: 'ev_to_ebitda', lowerBetter: true }
    ];

    const labels = metrics.map(m => _metricLabelFromId(m.id));
    const values = metrics.map(m => {
      const p = cvi[m.id]?.percentile;
      if (p === null || p === undefined) return null;
      const pv = Number(p);
      if (!Number.isFinite(pv)) return null;
      return m.lowerBetter ? (100 - pv) : pv;
    });

    const missing = values.filter(v => v === null || v === undefined).length;
    createPeerRadarChart('peerRadarChart', labels, values);

    meta.textContent = `FY ${b.year} · Peer count: ${b.peer_count} · Missing: ${missing}/${values.length}`;
  } catch (error) {
    console.error('Error loading peer radar:', error);
    meta.textContent = 'Lỗi tải radar';
  }
}

function _pearsonCorr(xs, ys) {
  const n = xs.length;
  if (n < 3) return null;
  let mx = 0, my = 0;
  for (let i = 0; i < n; i++) { mx += xs[i]; my += ys[i]; }
  mx /= n; my /= n;
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < n; i++) {
    const vx = xs[i] - mx;
    const vy = ys[i] - my;
    num += vx * vy;
    dx += vx * vx;
    dy += vy * vy;
  }
  const den = Math.sqrt(dx * dy);
  if (den <= 0) return null;
  return num / den;
}

function _corrCellStyle(r) {
  if (r === null || r === undefined) return '';
  const v = Math.max(-1, Math.min(1, Number(r)));
  const a = 0.10 + 0.35 * Math.abs(v);
  if (v >= 0) return `background: rgba(34, 197, 94, ${a});`;
  return `background: rgba(239, 68, 68, ${a});`;
}

async function loadCorrelationHeatmap() {
  if (!state.currentSymbol) return;
  const container = document.getElementById('metricCorrelationHeatmap');
  const meta = document.getElementById('corrHeatmapMeta');
  if (!container || !meta) return;

  meta.textContent = 'Đang tải data...';
  container.innerHTML = `
    <div style="text-align: center; padding: var(--space-6); color: var(--text-secondary);">
      <div class="loading-spinner"></div>
      <p style="margin-top: var(--space-3);">Đang tính correlation...</p>
    </div>
  `;

  try {
    const metricIds = [
      'roe',
      'net_profit_margin',
      'debt_to_equity',
      'current_ratio',
      'asset_turnover',
      'price_to_earnings',
      'price_to_book',
      'ev_to_ebitda'
    ];
    const history = await API.getFinancialHistory(state.currentSymbol, metricIds.join(','), 10);
    const years = history.years || [];
    const series = {};

    metricIds.forEach(m => {
      const arr = (history.metrics && history.metrics[m]) ? history.metrics[m] : [];
      const map = {};
      arr.forEach(it => {
        const yr = it.year;
        const val = it.value;
        if (val === null || val === undefined) return;
        const fv = Number(val);
        if (!Number.isFinite(fv)) return;
        map[yr] = fv;
      });
      series[m] = map;
    });

    const header = metricIds.map(m => `<th>${_metricLabelFromId(m)}</th>`).join('');
    let body = '';

    for (const mi of metricIds) {
      let row = `<tr><th>${_metricLabelFromId(mi)}</th>`;
      for (const mj of metricIds) {
        const xs = [];
        const ys = [];
        years.forEach(yr => {
          const xi = series[mi][yr];
          const yj = series[mj][yr];
          if (xi === undefined || yj === undefined) return;
          xs.push(xi);
          ys.push(yj);
        });

        let r = null;
        if (mi === mj) {
          r = xs.length ? 1.0 : null;
        } else {
          r = _pearsonCorr(xs, ys);
        }

        const n = xs.length;
        const text = (r === null || n < 3) ? '-' : Number(r).toFixed(2);
        const title = `n=${n}${r === null ? '' : `, r=${Number(r).toFixed(4)}`}`;
        const style = (r === null || n < 3) ? '' : _corrCellStyle(r);
        row += `<td style="${style}" title="${title}">${text}<div style="opacity:0.7; font-size: 10px;">n=${n}</div></td>`;
      }
      row += '</tr>';
      body += row;
    }

    container.innerHTML = `<table><thead><tr><th>Metric</th>${header}</tr></thead><tbody>${body}</tbody></table>`;

    const yrFrom = years.length ? Math.min(...years) : null;
    const yrTo = years.length ? Math.max(...years) : null;
    meta.textContent = (yrFrom && yrTo) ? `FY ${yrFrom}–${yrTo} · Years: ${years.length} (pairwise n varies)` : 'Không đủ dữ liệu years';
  } catch (error) {
    console.error('Error loading correlation heatmap:', error);
    meta.textContent = 'Lỗi tải/calc correlation';
    container.innerHTML = `<div style="padding: var(--space-4); color: var(--color-danger-500);">Lỗi tính correlation</div>`;
  }
}

function _bindResearchVizControlsOnce() {
  const btn = document.getElementById('scatterRefreshBtn');
  const xSel = document.getElementById('scatterXSelect');
  const ySel = document.getElementById('scatterYSelect');

  if (btn && !btn.dataset.bound) {
    btn.dataset.bound = '1';
    btn.addEventListener('click', () => loadPeerScatter());
  }
  if (xSel && !xSel.dataset.bound) {
    xSel.dataset.bound = '1';
    xSel.addEventListener('change', () => loadPeerScatter());
  }
  if (ySel && !ySel.dataset.bound) {
    ySel.dataset.bound = '1';
    ySel.addEventListener('change', () => loadPeerScatter());
  }
}

async function loadResearchVisualizations() {
  if (!state.currentSymbol) return;
  _bindResearchVizControlsOnce();
  await Promise.all([
    loadPeerScatter(),
    loadPeerRadar(),
    loadCorrelationHeatmap()
  ]);
}

/**
 * Load and render Piotroski F-Score when Advanced tab is clicked
 */
async function loadPiotroskiFScore() {
  if (!state.currentSymbol) return;

  try {
    const analysis = await API.getAnalysis(state.currentSymbol);

    if (analysis && analysis.analysis && analysis.analysis.piotroski_f_score) {
      renderPiotroskiFScore(analysis.analysis.piotroski_f_score);
    } else {
      document.getElementById('piotroskiSection').innerHTML = `
        <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
          <p>Không có dữ liệu Piotroski F-Score</p>
        </div>
      `;
    }
  } catch (error) {
    console.error('Error loading Piotroski F-Score:', error);
    document.getElementById('piotroskiSection').innerHTML = `
      <div style="text-align: center; padding: var(--space-8); color: var(--color-danger-500);">
        <p>Lỗi tải dữ liệu Piotroski F-Score</p>
      </div>
    `;
  }
}

// ============================================================================
// DIVIDEND ANALYSIS
// ============================================================================

/**
 * Load dividend analysis for current symbol
 */
async function loadDividendAnalysis() {
  if (!state.currentSymbol) return;

  try {
    const dividendData = await API.getDividendAnalysis(state.currentSymbol);
    renderDividendAnalysis(dividendData);
  } catch (error) {
    console.error('Error loading dividend analysis:', error);
    const container = document.getElementById('dividendAnalysisSection');
    if (container) {
      container.innerHTML = `
        <div style="text-align: center; padding: var(--space-8); color: var(--color-danger-500);">
          <p>Lỗi tải dữ liệu cổ tức</p>
        </div>
      `;
    }
  }
}

/**
 * Render dividend analysis section
 * @param {Object} data - Dividend data from API
 */
function renderDividendAnalysis(data) {
  const container = document.getElementById('dividendAnalysisSection');
  if (!container) return;

  if (!data || data.error) {
    container.innerHTML = `
      <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
        <p>Không có dữ liệu cổ tức</p>
      </div>
    `;
    return;
  }

  const { dividend_yield, payout_ratio, consistency, history, growth_rate, next_ex_date } = data;

  // Format percentage
  const formatPct = (val) => !isMissing(val) ? `${(val * 100).toFixed(2)}%` : 'N/A';

  // Get yield rating
  const getYieldRating = (yield) => {
    if (isMissing(yield)) return { label: 'N/A', class: 'neutral' };
    if (yield >= 0.08) return { label: 'Rất cao', class: 'excellent' };
    if (yield >= 0.06) return { label: 'Cao', class: 'good' };
    if (yield >= 0.04) return { label: 'Trung bình', class: 'neutral' };
    if (yield >= 0.02) return { label: 'Thấp', class: 'low' };
    return { label: 'Rất thấp', class: 'very-low' };
  };

  const yieldRating = getYieldRating(dividend_yield);
  const growthClass = !isMissing(growth_rate) ? (growth_rate >= 0 ? 'positive' : 'negative') : '';

  // Build history HTML
  const historyHtml = history && history.length > 0
    ? history.map(item => `
        <div class="dividend-history-item">
          <div class="div-history-year">${item.year}</div>
          <div class="div-history-amount">${formatNumber(item.dividend_per_share, 0)} ₫</div>
          <div class="div-history-yield">${!isMissing(item.yield) ? formatPct(item.yield) : 'N/A'}</div>
        </div>
      `).join('')
    : '<p style="color: var(--text-secondary);">Không có lịch sử cổ tức</p>';

  // Build consistency stars
  const consistencyScore = consistency ? consistency.score : 0;
  const starsCount = Math.round(consistencyScore * 5);
  const stars = '★'.repeat(starsCount) + '☆'.repeat(5 - starsCount);

  container.innerHTML = `
    <div class="dividend-analysis-card">
      <!-- Header -->
      <div class="div-header">
        <div class="div-title-section">
          <div class="div-icon">💰</div>
          <div>
            <h3 class="div-title">Phân tích Cổ tức</h3>
            <div class="div-subtitle">Lịch sử trả cổ tức và đánh giá</div>
          </div>
        </div>
      </div>

      <!-- Key Metrics -->
      <div class="div-metrics-grid">
        <!-- Dividend Yield -->
        <div class="div-metric-card">
          <div class="div-metric-label">Tỷ suất cổ tức</div>
          <div class="div-metric-value ${yieldRating.class}">${formatPct(dividend_yield)}</div>
          <div class="div-metric-rating">${yieldRating.label}</div>
        </div>

        <!-- Payout Ratio -->
        <div class="div-metric-card">
          <div class="div-metric-label">Tỷ lệ trả cổ tức</div>
          <div class="div-metric-value">${formatPct(payout_ratio)}</div>
          <div class="div-metric-desc">Từ lợi nhuận</div>
        </div>

        <!-- Consistency -->
        <div class="div-metric-card">
          <div class="div-metric-label">Tính nhất quán</div>
          <div class="div-metric-stars">${stars}</div>
          <div class="div-metric-desc">${consistency ? consistency.rating : 'N/A'}</div>
          <div class="div-metric-sub">${consistency ? consistency.years_with_dividend + '/' + consistency.total_years + ' năm' : ''}</div>
        </div>

        <!-- Growth Rate -->
        <div class="div-metric-card">
          <div class="div-metric-label">Tăng trưởng CAGR</div>
          <div class="div-metric-value ${growthClass}">
            ${!isMissing(growth_rate) ? formatPct(growth_rate) : 'N/A'}
          </div>
          <div class="div-metric-desc">Tốc độ tăng trưởng</div>
        </div>
      </div>

      <!-- History Timeline -->
      <div class="div-history-section">
        <h4 class="div-history-title">Lịch sử trả cổ tức</h4>
        <div class="div-history-list">
          ${historyHtml}
        </div>
      </div>

      ${next_ex_date ? `
        <div class="div-next-date">
          <span style="color: var(--text-secondary);">Ngày chia cổ tức gần nhất: </span>
          <strong>${next_ex_date}</strong>
        </div>
      ` : ''}
    </div>
  `;
}

// ============================================================================
// TTM FUNDAMENTALS (QUARTERLY-BASED)
// ============================================================================

async function loadTTMFundamentals() {
  if (!state.currentSymbol) return;
  const container = document.getElementById('ttmFundamentalsSection');
  if (!container) return;

  const ttmHelp = buildHelpTip(
    'Giải thích: Quarterly & TTM',
    `
      <ul>
        <li><b>TTM</b> = tổng 4 quý gần nhất (từ báo cáo quý) để giảm lệch mùa vụ.</li>
        <li>Nếu thiếu đủ 4 quý liên tiếp, trạng thái sẽ <b>PENDING</b> và một số chỉ tiêu sẽ N/A.</li>
        <li><b>P/E, P/B (snapshot)</b> dùng giá close mới nhất và EPS/BVPS (proxy); chỉ hợp lệ khi EPS/BVPS &gt; 0.</li>
        <li>Biểu đồ trend giữ gap (null), không tự nội suy.</li>
      </ul>
    `,
    'Giải thích TTM'
  );

  container.innerHTML = `
    <div class="card">
      <div class="card-title-row" style="margin-bottom: var(--space-2);">
        <h3 class="card-title">📅 Quarterly & TTM</h3>
        ${ttmHelp}
      </div>
      <div style="text-align: center; padding: var(--space-6); color: var(--text-secondary);">
        <div class="loading-spinner"></div>
        <p style="margin-top: var(--space-3);">Đang tải dữ liệu TTM...</p>
      </div>
    </div>
  `;

  try {
    const [data, series] = await Promise.all([
      API.getTTMFundamentals(state.currentSymbol, state.currentYear),
      API.getTTMSeries(state.currentSymbol, 12).catch(() => null)
    ]);
    renderTTMFundamentals(data, series);
  } catch (error) {
    console.error('Error loading TTM fundamentals:', error);
    container.innerHTML = `
      <div class="card">
        <div class="card-title-row" style="margin-bottom: var(--space-2);">
          <h3 class="card-title">📅 Quarterly & TTM</h3>
          ${ttmHelp}
        </div>
        <p style="color: var(--color-danger-500); margin: 0;">Lỗi tải dữ liệu TTM</p>
      </div>
    `;
  }
}

function renderTTMFundamentals(data, seriesData = null) {
  const container = document.getElementById('ttmFundamentalsSection');
  if (!container) return;

  const ttmHelp = buildHelpTip(
    'Giải thích: Quarterly & TTM',
    `
      <ul>
        <li><b>TTM</b> = tổng 4 quý gần nhất (từ báo cáo quý).</li>
        <li>Snapshot P/E, P/B dựa trên giá close mới nhất; có thể sai nếu thiếu corporate actions (split/rights/bonus).</li>
        <li>Meta sẽ hiển thị coverage để bạn biết mức độ tin cậy của từng chỉ tiêu.</li>
      </ul>
    `,
    'Giải thích TTM'
  );

  if (!data || data.error) {
    container.innerHTML = `
      <div class="card">
        <div class="card-title-row" style="margin-bottom: var(--space-2);">
          <h3 class="card-title">📅 Quarterly & TTM</h3>
          ${ttmHelp}
        </div>
        <p style="color: var(--text-secondary); margin: 0;">Không có dữ liệu TTM</p>
      </div>
    `;
    return;
  }

  const period = data.period || {};
  const asOf = period.as_of_period || 'N/A';
  const status = data.status || 'unknown';
  const coverage = data.coverage?.income_statement || {};

  const ttm = data.ttm || {};
  const derived = data.derived || {};
  const growth = data.growth || {};

  const statusBadge = status === 'OK'
    ? '<span class="company-badge ttm-status-badge ttm-status-ok">OK</span>'
    : '<span class="company-badge ttm-status-badge ttm-status-pending">PENDING</span>';

  const fmtVND = (v) => (v === null || v === undefined) ? '-' : formatCurrency(v, 'tỷ');
  const fmtPct = (v) => (v === null || v === undefined) ? '-' : formatPercent(v);
  const fmtRatio = (v) => (v === null || v === undefined) ? '-' : formatRatio(v);
  const fmtNum = (v, d = 2) => (v === null || v === undefined) ? '-' : formatNumber(v, d);

  const message = status !== 'OK'
    ? `<div class="ttm-message">
         Chưa đủ dữ liệu quý để tính TTM đầy đủ (income_statement: ${coverage.have || 0}/${coverage.need || 4}, consecutive=${coverage.consecutive ? 'yes' : 'no'}).
       </div>`
    : '';

  container.innerHTML = `
    <div class="card ttm-panel">
      <div class="ttm-header">
        <div class="ttm-title-wrap">
          <h3 class="card-title ttm-title">📅 Quarterly & TTM</h3>
          <div class="card-subtitle ttm-subtitle">As of: <strong>${asOf}</strong></div>
        </div>
        <div class="ttm-header-actions">
          ${statusBadge}
          ${ttmHelp}
        </div>
      </div>

      <div class="ttm-kpi-grid">
        <div class="ttm-kpi-card">
          <div class="ttm-kpi-label">Doanh thu TTM</div>
          <div class="ttm-kpi-value ttm-kpi-value-lg">${fmtVND(ttm.revenue)}</div>
          <div class="ttm-kpi-meta">TTM YoY: ${fmtPct(growth?.ttm_yoy?.revenue)}</div>
        </div>

        <div class="ttm-kpi-card">
          <div class="ttm-kpi-label">Lợi nhuận TTM</div>
          <div class="ttm-kpi-value ttm-kpi-value-lg">${fmtVND(ttm.net_profit)}</div>
          <div class="ttm-kpi-meta">TTM YoY: ${fmtPct(growth?.ttm_yoy?.net_profit)}</div>
        </div>

        <div class="ttm-kpi-card">
          <div class="ttm-kpi-label">Gross / Net Margin (TTM)</div>
          <div class="ttm-kpi-value">
            ${fmtPct(derived.gross_margin_ttm)} / ${fmtPct(derived.net_margin_ttm)}
          </div>
          <div class="ttm-kpi-meta">Operating margin: ${fmtPct(derived.operating_margin_ttm)}</div>
        </div>

        <div class="ttm-kpi-card">
          <div class="ttm-kpi-label">ROE / ROA (TTM)</div>
          <div class="ttm-kpi-value">
            ${fmtPct(derived.roe_ttm)} / ${fmtPct(derived.roa_ttm)}
          </div>
          <div class="ttm-kpi-meta">EPS TTM (proxy): ${fmtNum(ttm.eps_ttm_proxy, 0)} ₫</div>
        </div>

        <div class="ttm-kpi-card">
          <div class="ttm-kpi-label">P/E / P/B (snapshot)</div>
          <div class="ttm-kpi-value">
            ${fmtRatio(derived.pe_snapshot)} / ${fmtRatio(derived.pb_snapshot)}
          </div>
          <div class="ttm-kpi-meta">Quarter YoY (rev/NP): ${fmtPct(growth?.quarter_yoy?.revenue)} / ${fmtPct(growth?.quarter_yoy?.net_profit)}</div>
        </div>

        <div class="ttm-kpi-card">
          <div class="ttm-kpi-label">OCF / FCF (TTM)</div>
          <div class="ttm-kpi-value">
            ${fmtVND(ttm.cfo)} / ${fmtVND(ttm.fcf)}
          </div>
          <div class="ttm-kpi-meta">OCF margin: ${fmtPct(derived.cfo_margin_ttm)}</div>
        </div>
      </div>

      ${message}

      <div class="ttm-trends">
        <div class="ttm-trend-item">
          <div class="chart-meta" id="ttmTrendRevMeta"></div>
          <div class="chart-wrapper">
            <canvas id="ttmTrendRevenueProfitChart"></canvas>
          </div>
        </div>
        <div class="ttm-trend-item">
          <div class="chart-meta" id="ttmTrendCfMeta"></div>
          <div class="chart-wrapper">
            <canvas id="ttmTrendCashflowChart"></canvas>
          </div>
        </div>
      </div>
    </div>
  `;

  renderTTMSeriesCharts(seriesData);
}

function renderTTMSeriesCharts(seriesData) {
  const pts = Array.isArray(seriesData?.points) ? seriesData.points : [];
  if (pts.length === 0) {
    _setText('ttmTrendRevMeta', 'Không có TTM series');
    _setText('ttmTrendCfMeta', 'Không có TTM series');
    return;
  }

  const labels = pts.map(p => p.period || '');
  const revenue = pts.map(p => p?.ttm?.revenue ?? null);
  const netProfit = pts.map(p => p?.ttm?.net_profit ?? null);
  const cfo = pts.map(p => p?.ttm?.cfo ?? null);
  const fcf = pts.map(p => p?.ttm?.fcf ?? null);

  createMultiLineTrendChart(
    'ttmTrendRevenueProfitChart',
    labels,
    [
      { label: 'Revenue (TTM)', data: revenue, color: '#3b82f6', borderWidth: 2, pointRadius: 2 },
      { label: 'Net Profit (TTM)', data: netProfit, color: '#22c55e', borderWidth: 2, pointRadius: 2 },
    ],
    { valueType: 'currency', tickDecimals: 0, tooltipDecimals: 0, showBaseline: true }
  );

  createMultiLineTrendChart(
    'ttmTrendCashflowChart',
    labels,
    [
      { label: 'OCF (TTM)', data: cfo, color: '#f59e0b', borderWidth: 2, pointRadius: 2 },
      { label: 'FCF (TTM)', data: fcf, color: '#ec4899', borderWidth: 2, pointRadius: 2 },
    ],
    { valueType: 'currency', tickDecimals: 0, tooltipDecimals: 0, showBaseline: true }
  );

  const okCount = pts.filter(p => p?.status === 'OK').length;
  const revenueCol = seriesData?.inputs?.revenue_col;
  const profitCol = seriesData?.inputs?.profit_col;
  _setText('ttmTrendRevMeta', `points=${pts.length} · ok=${okCount} · revenue_col=${revenueCol || 'N/A'} · profit_col=${profitCol || 'N/A'}`);
  _setText('ttmTrendCfMeta', `Cashflow TTM phụ thuộc coverage cash_flow_statement (gaps giữ null)`);
}

// ============================================================================
// PRICE-BASED RISK ANALYSIS
// ============================================================================

async function loadRiskAnalysis(days = 365) {
  if (!state.currentSymbol) return;
  const container = document.getElementById('riskAnalysisSection');
  if (!container) return;

  const riskHelp = buildHelpTip(
    'Giải thích: Rủi ro (giá lịch sử)',
    `
      <ul>
        <li>Tính từ giá close theo ngày (log returns) trong <code>stock_price_history</code>.</li>
        <li><b>Volatility</b>, <b>Max Drawdown</b>, <b>VaR/ES (95%)</b> là rủi ro thống kê, không phải dự báo chắc chắn.</li>
        <li><b>Beta</b> so với VNINDEX trên cửa sổ 1Y; phụ thuộc coverage và benchmark.</li>
        <li>Data limits: chưa điều chỉnh corporate actions (split/rights/bonus) nên có thể làm sai return/risk.</li>
      </ul>
    `,
    'Giải thích rủi ro'
  );

  container.innerHTML = `
    <div class="card">
      <div class="card-title-row" style="margin-bottom: var(--space-2);">
        <h3 class="card-title">⚠️ Rủi ro (giá lịch sử)</h3>
        ${riskHelp}
      </div>
      <div style="text-align: center; padding: var(--space-6); color: var(--text-secondary);">
        <div class="loading-spinner"></div>
        <p style="margin-top: var(--space-3);">Đang tải dữ liệu rủi ro...</p>
      </div>
    </div>
  `;

  try {
    const data = await API.getRiskAnalysis(state.currentSymbol, days);
    renderRiskAnalysis(data);
  } catch (error) {
    console.error('Error loading risk analysis:', error);
    container.innerHTML = `
      <div class="card">
        <div class="card-title-row" style="margin-bottom: var(--space-2);">
          <h3 class="card-title">⚠️ Rủi ro (giá lịch sử)</h3>
          ${riskHelp}
        </div>
        <p style="color: var(--color-danger-500); margin: 0;">Lỗi tải dữ liệu rủi ro</p>
      </div>
    `;
  }
}

function renderRiskAnalysis(data) {
  const container = document.getElementById('riskAnalysisSection');
  if (!container) return;

  const riskHelp = buildHelpTip(
    'Giải thích: Rủi ro (giá lịch sử)',
    `
      <ul>
        <li>Dùng log returns theo ngày; coverage thấp có thể làm metric PENDING hoặc thiếu chính xác.</li>
        <li>VaR/ES là ước lượng rủi ro tail theo lịch sử, không đảm bảo cho tương lai.</li>
        <li>Data limits: chưa có total-return adjust đầy đủ split/rights/bonus.</li>
      </ul>
    `,
    'Giải thích rủi ro'
  );

  if (!data || data.error) {
    container.innerHTML = `
      <div class="card">
        <div class="card-title-row" style="margin-bottom: var(--space-2);">
          <h3 class="card-title">⚠️ Rủi ro (giá lịch sử)</h3>
          ${riskHelp}
        </div>
        <p style="color: var(--text-secondary); margin: 0;">Không có dữ liệu rủi ro</p>
      </div>
    `;
    return;
  }

  const asOf = data.as_of || 'N/A';
  const overall = data.overall_status || 'N/A';
  const coverage = (data.coverage_pct !== undefined) ? `${data.coverage_pct}% (${data.ok_metrics}/${data.total_metrics})` : 'N/A';
  const metrics = data.metrics || {};

  const metricDefs = [
    { key: 'volatility_1y', label: 'Volatility (1Y)', format: (m) => m?.status === 'OK' ? `${formatNumber(m.value, 2)}%` : '-' },
    { key: 'beta', label: 'Beta (VNINDEX)', format: (m) => m?.status === 'OK' ? formatNumber(m.value, 2) : '-' },
    { key: 'var', label: 'VaR (95%)', format: (m) => m?.status === 'OK' ? `${formatNumber(m.value, 2)}%` : '-' },
    { key: 'expected_shortfall', label: 'ES/CVaR (95%)', format: (m) => m?.status === 'OK' ? `${formatNumber(m.value, 2)}%` : '-' },
    { key: 'sharpe_ratio', label: 'Sharpe', format: (m) => m?.status === 'OK' ? formatNumber(m.value, 2) : '-' },
    { key: 'sortino_ratio', label: 'Sortino', format: (m) => m?.status === 'OK' ? formatNumber(m.value, 2) : '-' },
    { key: 'max_drawdown', label: 'Max Drawdown', format: (m) => m?.status === 'OK' ? `${formatNumber(m.value, 2)}%` : '-' },
    { key: 'calmar_ratio', label: 'Calmar', format: (m) => m?.status === 'OK' ? formatNumber(m.value, 2) : '-' },
  ];

  const statusBadge = (status) => {
    if (status === 'OK') return '<span class="company-badge" style="background: rgba(34,197,94,0.15); border-color: rgba(34,197,94,0.35);">OK</span>';
    if (status && status.startsWith('PENDING')) return '<span class="company-badge" style="background: rgba(245,158,11,0.12); border-color: rgba(245,158,11,0.35);">PENDING</span>';
    return '<span class="company-badge" style="background: rgba(239,68,68,0.12); border-color: rgba(239,68,68,0.35);">ERROR</span>';
  };

  const tiles = metricDefs.map(def => {
    const m = metrics[def.key];
    const st = m?.status || 'UNKNOWN';
    const msg = (st !== 'OK' && m?.message) ? m.message : '';
    return `
      <div style="padding: var(--space-4); border: 1px solid var(--border-color); border-radius: var(--radius-lg); background: var(--bg-tertiary);">
        <div style="display:flex; justify-content: space-between; align-items:center; gap: var(--space-2);">
          <div style="color: var(--text-secondary); font-size: var(--text-sm);">${def.label}</div>
          ${statusBadge(st)}
        </div>
        <div style="margin-top: var(--space-2); font-size: var(--text-xl); font-weight: 700;">${def.format(m)}</div>
        ${msg ? `<div style="margin-top: var(--space-2); color: var(--text-tertiary); font-size: var(--text-xs);">${msg}</div>` : ''}
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="card">
      <div style="display:flex; justify-content: space-between; align-items: flex-start; gap: var(--space-3); margin-bottom: var(--space-4);">
        <div>
          <h3 class="card-title" style="margin: 0;">⚠️ Rủi ro (giá lịch sử)</h3>
          <div class="card-subtitle" style="margin-top: var(--space-1);">As of: <strong>${asOf}</strong> · Overall: <strong>${overall}</strong> · Coverage: <strong>${coverage}</strong></div>
        </div>
        ${riskHelp}
      </div>

      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--space-4);">
        ${tiles}
      </div>
    </div>
  `;
}

// ============================================================================
// EARLY WARNING LOADER (FINANCIAL)
// ============================================================================

async function loadEarlyWarning() {
  if (!state.currentSymbol) return;
  const container = document.getElementById('earlyWarningSection');
  if (!container) return;

  // Render loading state via existing renderer
  await renderEarlyWarning(null);

  try {
    const warningData = await API.getEarlyWarning(state.currentSymbol, state.currentYear);
    await renderEarlyWarning(warningData);
  } catch (error) {
    console.error('Error loading early warning:', error);
    container.innerHTML = `
      <div class="card">
        <h3 class="card-title" style="margin-bottom: var(--space-2);">🚨 Hệ thống Cảnh báo Sớm</h3>
        <p style="color: var(--color-danger-500); margin: 0;">Lỗi tải dữ liệu cảnh báo sớm</p>
      </div>
    `;
  }
}

// ============================================================================
// QUALITY FLAGS SYSTEM
// ============================================================================

/**
 * Calculate quality flag from a score
 * @param {number} score - Score value
 * @param {Object} thresholds - Thresholds for green/yellow/red
 * @returns {Object} - Flag color and label
 */
function calculateQualityFlag(score, thresholds) {
  if (score === null || score === undefined) {
    return { color: 'gray', label: 'N/A', icon: '○' };
  }
  if (score >= thresholds.green) {
    return { color: 'green', label: 'Tốt', icon: '●' };
  }
  if (score >= thresholds.yellow) {
    return { color: 'yellow', label: 'Trung bình', icon: '◐' };
  }
  return { color: 'red', label: 'Yếu', icon: '●' };
}

/**
 * Render Quality Flags Panel
 * Aggregates all quality indicators into a unified view
 * @param {Object} analysis - Analysis data from API
 * @param {Object} ratios - Financial ratios
 */
function renderQualityFlags(analysis, ratios) {
  const panel = document.getElementById('qualityFlagsPanel');
  if (!panel) return;

  const flags = [];
  let totalGreen = 0;
  let totalYellow = 0;
  let totalRed = 0;

  // 1. Piotroski F-Score (0-9)
  if (analysis && analysis.piotroski_f_score) {
    const fScore = analysis.piotroski_f_score.score;
    const flag = calculateQualityFlag(fScore, { green: 7, yellow: 4 });
    flags.push({
      name: 'Piotroski F-Score',
      value: `${fScore}/9 điểm`,
      ...flag
    });
    if (flag.color === 'green') totalGreen++;
    else if (flag.color === 'yellow') totalYellow++;
    else if (flag.color === 'red') totalRed++;
  }

  // 2. Altman Z-Score
  if (analysis && analysis.altman_z_score) {
    const zScoreRaw = analysis.altman_z_score.score ?? analysis.altman_z_score.z_score;
    const zScore = (zScoreRaw !== null && zScoreRaw !== undefined) ? Number(zScoreRaw) : null;
    const zone = analysis.altman_z_score.zone;
    let flag;
    if (zScore === null || !Number.isFinite(zScore)) {
      flag = { color: 'gray', label: 'N/A', icon: '○' };
    } else if (zone === 'safe' || zScore > 2.99) {
      flag = { color: 'green', label: 'An toàn', icon: '●' };
      totalGreen++;
    } else if (zone === 'grey' || (zScore >= 1.81 && zScore <= 2.99)) {
      flag = { color: 'yellow', label: 'Vùng xám', icon: '◐' };
      totalYellow++;
    } else {
      flag = { color: 'red', label: 'Nguy cơ', icon: '●' };
      totalRed++;
    }
    flags.push({
      name: 'Altman Z-Score',
      value: zScore === null || !Number.isFinite(zScore) ? 'N/A' : `${zScore.toFixed(2)} - ${flag.label}`,
      ...flag
    });
  }

  // 3. Cash Flow Quality
  if (analysis && analysis.cash_flow_quality) {
    const cfqScore = analysis.cash_flow_quality.score;
    const flag = calculateQualityFlag(cfqScore, { green: 70, yellow: 40 });
    flags.push({
      name: 'Chất lượng Dòng tiền',
      value: `${cfqScore}/100`,
      ...flag
    });
    if (flag.color === 'green') totalGreen++;
    else if (flag.color === 'yellow') totalYellow++;
    else if (flag.color === 'red') totalRed++;
  }

  // 4. Working Capital (CCC)
  if (ratios && ratios.cash_conversion_cycle !== null && ratios.cash_conversion_cycle !== undefined) {
    const ccc = ratios.cash_conversion_cycle;
    let flag;
    if (ccc < 30) {
      flag = { color: 'green', label: 'Hiệu quả', icon: '●' };
      totalGreen++;
    } else if (ccc <= 60) {
      flag = { color: 'yellow', label: 'Khá', icon: '◐' };
      totalYellow++;
    } else {
      flag = { color: 'red', label: 'Cần cải thiện', icon: '●' };
      totalRed++;
    }
    flags.push({
      name: 'Vòng quay Tiền mặt (CCC)',
      value: `${ccc.toFixed(0)} ngày`,
      ...flag
    });
  }

  // 5. ROE (Return on Equity)
  if (ratios && ratios.roe !== null && ratios.roe !== undefined) {
    const roe = ratios.roe * 100; // Convert to percentage
    const flag = calculateQualityFlag(roe, { green: 15, yellow: 8 });
    flags.push({
      name: 'ROE (Tỷ suất Lợi nhuận Vốn)',
      value: `${roe.toFixed(1)}%`,
      ...flag
    });
    if (flag.color === 'green') totalGreen++;
    else if (flag.color === 'yellow') totalYellow++;
    else if (flag.color === 'red') totalRed++;
  }

  // 6. Debt to Equity
  if (ratios && ratios.debt_to_equity !== null && ratios.debt_to_equity !== undefined) {
    const de = ratios.debt_to_equity;
    let flag;
    if (de <= 0.5) {
      flag = { color: 'green', label: 'Thấp', icon: '●' };
      totalGreen++;
    } else if (de <= 1.5) {
      flag = { color: 'yellow', label: 'Trung bình', icon: '◐' };
      totalYellow++;
    } else {
      flag = { color: 'red', label: 'Cao', icon: '●' };
      totalRed++;
    }
    flags.push({
      name: 'Đòn bẩy Tài chính (D/E)',
      value: `${de.toFixed(2)}x`,
      ...flag
    });
  }

  // Calculate overall quality
  const totalFlags = totalGreen + totalYellow + totalRed;
  let overallColor = 'yellow';
  let overallLabel = 'Trung bình';
  let overallEmoji = '◐';

  if (totalFlags > 0) {
    const greenRatio = totalGreen / totalFlags;
    const redRatio = totalRed / totalFlags;

    if (greenRatio >= 0.6) {
      overallColor = 'green';
      overallLabel = 'Chất lượng cao';
      overallEmoji = '●';
    } else if (redRatio >= 0.4) {
      overallColor = 'red';
      overallLabel = 'Cần lưu ý';
      overallEmoji = '●';
    } else {
      overallColor = 'yellow';
      overallLabel = 'Trung bình';
      overallEmoji = '◐';
    }
  }

  // If no flags available, hide panel
  if (flags.length === 0) {
    panel.style.display = 'none';
    return;
  }

  // Render flags grid
  const flagsGrid = document.getElementById('qfFlagsGrid');
  flagsGrid.innerHTML = flags.map(flag => `
    <div class="qf-flag-item">
      <div class="qf-flag-indicator ${flag.color}">${flag.icon}</div>
      <div class="qf-flag-content">
        <div class="qf-flag-name">${flag.name}</div>
        <div class="qf-flag-value">${flag.value}</div>
      </div>
    </div>
  `).join('');

  // Update overall score
  const scoreBadge = document.getElementById('qfScoreBadge');
  scoreBadge.className = `qf-score-badge ${overallColor}`;
  scoreBadge.textContent = overallEmoji;

  // Update rating text
  const ratingText = document.getElementById('qfOverallRating');
  ratingText.textContent = `${overallLabel} (${totalGreen} xanh, ${totalYellow} vàng, ${totalRed} đỏ)`;

  // Generate summary
  const summaryEl = document.getElementById('qfSummary');
  let summaryText = '';

  if (overallColor === 'green') {
    summaryText = `Công ty có chất lượng tài chính tốt với ${totalGreen}/${totalFlags} chỉ số đạt mức tốt. Đây là tín hiệu tích cực cho nhà đầu tư.`;
  } else if (overallColor === 'red') {
    summaryText = `Công ty có ${totalRed}/${totalFlags} chỉ số ở mức yếu. Cần xem xét kỹ trước khi ra quyết định đầu tư.`;
  } else {
    summaryText = `Công ty có chất lượng tài chính ở mức trung bình với ${totalYellow}/${totalFlags} chỉ số ở mức trung bình. Nên kết hợp với các yếu tố khác khi phân tích.`;
  }

  summaryEl.innerHTML = `
    <div class="qf-summary-title">
      <span>📋</span> Đánh giá tổng quan
    </div>
    <p class="qf-summary-text">${summaryText}</p>
  `;

  // Show panel
  panel.style.display = 'block';
}

// ============================================================================
// DATA PROVENANCE (ANNUAL SELECTION AUDIT)
// ============================================================================

function renderDataProvenance(ratios, balance, income, cashflow, analysisResponse) {
  const card = document.getElementById('dataProvenanceCard');
  const grid = document.getElementById('dataProvenanceGrid');
  const subtitle = document.getElementById('dataProvenanceSubtitle');

  if (!card || !grid || !subtitle) return;

  const bsSel = balance?.selection || analysisResponse?.provenance?.annual_selection?.balance_sheet;
  const isSel = income?.selection || analysisResponse?.provenance?.annual_selection?.income_statement;
  const cfSel = cashflow?.selection || analysisResponse?.provenance?.annual_selection?.cash_flow_statement;

  const hasAny = !!(bsSel || isSel || cfSel);
  if (!hasAny) {
    card.style.display = 'none';
    return;
  }

  function sourceLabel(tag) {
    if (tag === 'quarter_null') return 'quarter=NULL';
    if (tag === 'quarter_4') return 'Q4 fallback';
    if (tag === 'any') return 'any-year fallback';
    return 'N/A';
  }

  function formatNum(value, digits = 2) {
    if (value === null || value === undefined) return 'N/A';
    const n = Number(value);
    if (!Number.isFinite(n)) return 'N/A';
    return n.toFixed(digits);
  }

  function buildItem(title, row, sel, extraLines = []) {
    const candidateCount = sel?.candidate_count;
    const candidateSource = sel?.candidate_source;
    const selectedRowId = sel?.selected_row_id;
    const reason = sel?.selection_reason;
    const updatedAt = row?.updated_at;

    const lines = [];
    if (typeof candidateCount === 'number') {
      lines.push(`Candidates: <code>${candidateCount}</code> <span style="color: var(--text-tertiary);">(${sourceLabel(candidateSource)})</span>`);
    }
    if (selectedRowId !== null && selectedRowId !== undefined) {
      lines.push(`Selected ID: <code>${selectedRowId}</code>`);
    }
    if (reason) {
      lines.push(`Reason: <code>${reason}</code>`);
    }
    if (updatedAt) {
      lines.push(`Updated: <code>${updatedAt}</code>`);
    }
    extraLines.forEach(l => lines.push(l));

    const badge = (sel?.selection_reason || '').startsWith('fallback_')
      ? '<span class="dp-item-badge" style="background: rgba(234, 179, 8, 0.12); color: #a16207; border-color: rgba(234, 179, 8, 0.25);">FALLBACK</span>'
      : '<span class="dp-item-badge">ANNUAL</span>';

    return `
      <div class="dp-item">
        <div class="dp-item-title">
          <span>${title}</span>
          ${badge}
        </div>
        <div class="dp-item-meta">${lines.map(l => `<div>${l}</div>`).join('')}</div>
      </div>
    `;
  }

  const effectiveYear =
    balance?.year ||
    income?.year ||
    cashflow?.year ||
    ratios?.year ||
    analysisResponse?.year ||
    state.currentYear;

  subtitle.textContent = `FY ${effectiveYear} · Provenance của annual selector (DB có thể trùng quarter=NULL)`;

  const items = [];

  items.push(buildItem('Income Statement', income, isSel));

  const bsExtra = [];
  const sem = bsSel?.liquidity_semantics;
  if (sem) {
    if (sem.derived_current_liabilities_used) {
      bsExtra.push('Liquidity: <code>derived_current_liabilities_used=true</code>');
    }
    const crRep = sem.current_ratio_reported;
    const crEff = sem.current_ratio_effective;
    if (crRep !== null && crRep !== undefined) bsExtra.push(`CR reported: <code>${formatNum(crRep, 2)}x</code>`);
    if (crEff !== null && crEff !== undefined) bsExtra.push(`CR effective: <code>${formatNum(crEff, 2)}x</code>`);
  }
  items.push(buildItem('Balance Sheet', balance, bsSel, bsExtra));

  const cfExtra = [];
  const cashDiff = cfSel?.cash_diff;
  if (cashDiff !== null && cashDiff !== undefined) {
    cfExtra.push(`Cash diff (end vs BS): <code>${formatNum(cashDiff, 0)}</code>`);
  }
  items.push(buildItem('Cash Flow', cashflow, cfSel, cfExtra));

  grid.innerHTML = items.join('');
  card.style.display = 'block';
}

// ============================================================================
// PERCENTILE RANKING COMPONENT
// ============================================================================

/**
 * Render Percentile Ranking card
 * @param {string} symbol - Company symbol
 */
async function renderPercentileRanking(symbol) {
  const content = document.getElementById('prContent');
  const industryEl = document.getElementById('prIndustry');
  const peerCountEl = document.getElementById('prPeerCount');

  if (!content) return;

  // Show loading state
  content.innerHTML = `
    <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
      <div class="loading-spinner"></div>
      <p style="margin-top: var(--space-4);">Đang tải dữ liệu xếp hạng...</p>
    </div>
  `;

  try {
    const response = await fetch(`/api/industry/benchmark/${symbol}`);
    const data = await response.json();

    // Handle edge cases: no data or no peers
    if (!data || !data.company_vs_industry) {
      content.innerHTML = `
        <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
          <p>Không có dữ liệu xếp hạng percentile</p>
        </div>
      `;
      return;
    }

    // Check if there are valid peer comparisons
    const peerCount = data.peer_count || 0;
    if (peerCount === 0) {
      content.innerHTML = `
        <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
          <p>Không có công ty cùng ngành để so sánh</p>
        </div>
      `;
      return;
    }

    // Update header info with peer count
    industryEl.textContent = data.industry || 'N/A';
    peerCountEl.innerHTML = `
      <span style="font-size: var(--text-xs); color: var(--text-tertiary);">${peerCount} công ty cùng ngành</span>
    `;

    // Render metrics
    const metrics = data.company_vs_industry;
    const metricsHtml = renderPercentileMetrics(metrics, peerCount);

    content.innerHTML = metricsHtml;

  } catch (error) {
    console.error('Error loading percentile ranking:', error);
    content.innerHTML = `
      <div style="text-align: center; padding: var(--space-8); color: var(--color-danger-500);">
        <p>Lỗi tải dữ liệu xếp hạng percentile</p>
      </div>
    `;
  }
}

/**
 * Render percentile metrics
 * @param {Object} metrics - Metrics data from API
 * @param {number} peerCount - Number of peer companies for comparison
 * @returns {string} HTML string
 */
function renderPercentileMetrics(metrics, peerCount) {
  // Define metric configurations
  const metricConfigs = [
    {
      key: 'roe',
      label: 'ROE',
      description: 'Tỷ suất sinh lời trên vốn chủ sở hữu',
      invert: false,
      format: 'percent'
    },
    {
      key: 'net_profit_margin',
      label: 'Net Margin',
      description: 'Biên lợi nhuận ròng',
      invert: false,
      format: 'percent'
    },
    {
      key: 'price_to_earnings',
      label: 'P/E',
      description: 'Giá trên lợi nhuận (thấp hơn tốt hơn)',
      invert: true,
      format: 'number'
    },
    {
      key: 'debt_to_equity',
      label: 'Debt to Equity',
      description: 'Đòn bẩy tài chính (thấp hơn tốt hơn)',
      invert: true,
      format: 'ratio'
    }
  ];

  let html = '';

  metricConfigs.forEach(config => {
    const metricData = metrics[config.key];
    // Skip if no metric data or if percentile is null/undefined (missing data)
    if (!metricData || metricData.percentile === null || metricData.percentile === undefined) {
      return;
    }

    const companyValue = metricData.company;
    const industryValue = metricData.industry || metricData.median || metricData.p50;
    const percentile = metricData.percentile;
    const metricPeerCount = metricData.peer_count || peerCount;
    const excludedCount = metricData.excluded_count || 0;
    const exclusionReason = metricData.exclusion_reason;

    // Determine color class based on percentile
    // For "lower is better" metrics (P/E, D/E, etc.), invert the percentile for color logic
    const effectivePercentile = config.invert ? (100 - percentile) : percentile;

    let colorClass = 'pr-red';
    if (effectivePercentile >= 75) {
      colorClass = 'pr-green';
    } else if (effectivePercentile >= 25) {
      colorClass = 'pr-yellow';
    }

    // Format values - handle null/undefined
    let formattedCompany, formattedIndustry;
    if (config.format === 'percent') {
      formattedCompany = companyValue !== null && companyValue !== undefined ? formatPercent(companyValue) : 'N/A';
      formattedIndustry = industryValue !== null && industryValue !== undefined ? formatPercent(industryValue) : 'N/A';
    } else if (config.format === 'ratio') {
      formattedCompany = companyValue !== null && companyValue !== undefined ? formatRatio(companyValue) : 'N/A';
      formattedIndustry = industryValue !== null && industryValue !== undefined ? formatRatio(industryValue) : 'N/A';
    } else {
      formattedCompany = companyValue !== null && companyValue !== undefined ? formatNumber(companyValue, 1) : 'N/A';
      formattedIndustry = industryValue !== null && industryValue !== undefined ? formatNumber(industryValue, 1) : 'N/A';
    }

    // Build peer count display with coverage info
    let peerCountDisplay = `So sánh với ${metricPeerCount} công ty cùng ngành`;
    if (excludedCount > 0) {
      const totalPeers = metricPeerCount + excludedCount;
      const coverage = Math.round((metricPeerCount / totalPeers) * 100);
      peerCountDisplay += ` (${coverage}% đủ dữ liệu${exclusionReason ? ', ' + exclusionReason : ''})`;
    }

    // For inverted metrics (lower is better), adjust display percentile
    const displayPercentile = Math.round((config.invert ? (100 - percentile) : percentile) * 10) / 10;

    html += `
      <div class="pr-metric-item">
        <div class="pr-metric-header">
          <div>
            <div class="pr-metric-label">${config.label}</div>
            <div class="pr-metric-description">${config.description}</div>
            ${metricPeerCount > 0 ? `<div style="font-size: var(--text-xs); color: var(--text-tertiary); margin-top: 4px;">${peerCountDisplay}</div>` : ''}
          </div>
          <div class="pr-metric-values">
            <div class="pr-value-group">
              <span class="pr-value-label">Công ty:</span>
              <span class="pr-value pr-value-company">${formattedCompany}</span>
            </div>
            <div class="pr-value-group">
              <span class="pr-value-label">Ngành:</span>
              <span class="pr-value pr-value-industry">${formattedIndustry}</span>
            </div>
          </div>
        </div>

        <div class="pr-percentile-bar-container">
          <div class="pr-percentile-bar">
            <div class="pr-percentile-fill ${colorClass}" style="width: ${displayPercentile}%;"></div>
          </div>
          <div class="pr-percentile-label">
            <span class="pr-percentile-text ${colorClass}">Percentile ${Math.round(displayPercentile)}</span>
            ${config.invert ? '<span class="pr-invert-note">(Thấp hơn = Tốt hơn)</span>' : '<span class="pr-invert-note">(Càng cao càng tốt)</span>'}
          </div>
        </div>
      </div>
    `;
  });

  if (!html) {
    html = `
      <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
        <p>Không có đủ dữ liệu để so sánh</p>
      </div>
    `;
  }

  return html;
}

/**
 * Stub function for renderCashFlowQualityCard (if not defined elsewhere)
 */
function renderCashFlowQualityCard(data) {
  const card = document.getElementById('cashFlowQualityCard');
  if (!card || !data) {
    if (card) card.style.display = 'none';
    return;
  }

  card.style.display = 'block';

  const score = (data.score !== null && data.score !== undefined)
    ? data.score
    : (data.overall_score !== null && data.overall_score !== undefined ? data.overall_score : null);
  const rating = data.rating || 'N/A';
  const boundedScore = score !== null ? Math.max(0, Math.min(100, Number(score))) : null;

  const scoreLevel = (() => {
    if (boundedScore === null || Number.isNaN(boundedScore)) return 'unknown';
    if (boundedScore >= 80) return 'excellent';
    if (boundedScore >= 60) return 'good';
    if (boundedScore >= 40) return 'average';
    if (boundedScore >= 20) return 'weak';
    return 'very-weak';
  })();

  const getMetricClass = (value, kind) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return 'neutral';
    const v = Number(value);
    if (kind === 'ocf') {
      if (v >= 1.0) return 'good';
      if (v >= 0.8) return 'warning';
      return 'bad';
    }
    if (kind === 'fcf') {
      if (v >= 0.8) return 'good';
      if (v >= 0.3) return 'warning';
      return 'bad';
    }
    return 'neutral';
  };

  // Update score
  const scoreEl = document.getElementById('cfqScore');
  scoreEl.textContent = boundedScore !== null ? Math.round(boundedScore) : 'N/A';
  scoreEl.className = `cfq-score ${scoreLevel}`;
  document.getElementById('cfqRating').textContent = rating;
  const progressEl = document.getElementById('cfqProgress');
  progressEl.style.width = `${boundedScore !== null ? boundedScore : 0}%`;
  progressEl.className = `cfq-progress-fill ${scoreLevel}`;
  card.className = `cash-flow-quality-card ${scoreLevel}`;

  // Update metrics
  const metricsEl = document.getElementById('cfqMetrics');
  if (metricsEl && data.metrics) {
    const metrics = data.metrics;
    const consistencyYears = data.ocf_consistency_years;
    const totalYears = data.total_years;
    const consistencyText = (consistencyYears !== null && consistencyYears !== undefined && totalYears)
      ? `${consistencyYears}/${totalYears} năm dương`
      : 'N/A';
    const ocfClass = getMetricClass(metrics.ocf_to_net_income, 'ocf');
    const fcfClass = getMetricClass(metrics.fcf_to_net_income, 'fcf');

    metricsEl.innerHTML = `
      <div class="cfq-metric-card ${ocfClass}">
        <div class="cfq-metric-label">OCF / Net Income</div>
        <div class="cfq-metric-value">${metrics.ocf_to_net_income !== null && metrics.ocf_to_net_income !== undefined ? formatRatio(metrics.ocf_to_net_income) : 'N/A'}</div>
      </div>
      <div class="cfq-metric-card ${fcfClass}">
        <div class="cfq-metric-label">FCF / Net Income</div>
        <div class="cfq-metric-value">${metrics.fcf_to_net_income !== null && metrics.fcf_to_net_income !== undefined ? formatRatio(metrics.fcf_to_net_income) : 'N/A'}</div>
      </div>
      <div class="cfq-metric-card neutral">
        <div class="cfq-metric-label">OCF Consistency</div>
        <div class="cfq-metric-value">${consistencyText}</div>
      </div>
    `;
  }

  // Update interpretation
  const interpEl = document.getElementById('cfqInterpretation');
  if (interpEl) {
    const note = data.interpretation || 'Không đủ dữ liệu để diễn giải.';
    interpEl.innerHTML = `
      <div class="cfq-interpretation-title">Nhận định</div>
      <p class="cfq-interpretation-text">${note}</p>
    `;
  }
}

/**
 * Render Valuation Analysis Card
 */
async function renderValuationAnalysis(symbol, year = new Date().getFullYear()) {
  const container = document.getElementById('valuationAnalysisSection');
  if (!container) return;

  try {
    container.innerHTML = `
      <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
        <div class="loading-spinner"></div>
        <p style="margin-top: var(--space-4);">Đang tải phân tích định giá...</p>
      </div>
    `;

    const data = await API.getValuationAnalysis(symbol, year);

    if (data.error) {
      container.innerHTML = `
        <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
          <p>${data.error}</p>
        </div>
      `;
      return;
    }

    const currentClose = data?.price?.close;
    const currentAsOf = data?.price?.as_of;
    const currentCloseVnd = data?.price?.close_vnd;
    const priceScale = data?.price?.close_scale_vnd;
    const epsVnd = data?.fundamentals_used?.eps_vnd;
    const bvpsVnd = data?.fundamentals_used?.bvps_vnd;
    const currentPe = data?.multiples_current?.pe;
    const currentPb = data?.multiples_current?.pb;

    const fmtCloseK = (v, decimals = 2) => !isMissing(v) ? `${formatNumber(v, decimals)}k` : 'N/A';
    const fmtVnd = (v) => !isMissing(v) ? `${formatNumber(v, 0)} VND` : 'N/A';
    const fmtMultiple = (v) => !isMissing(v) ? `${Number(v).toFixed(2)}x` : 'N/A';
    const fmtUpside = (fairClose) => {
      if (isMissing(currentClose) || isMissing(fairClose) || Number(currentClose) === 0) return 'N/A';
      const pct = (Number(fairClose) / Number(currentClose) - 1) * 100;
      const sign = pct > 0 ? '+' : '';
      return `${sign}${pct.toFixed(1)}%`;
    };

    const fairBadge = (status) => {
      const map = {
        cheap: '<span class="status-badge status-cheaper">Rẻ</span>',
        fair: '<span class="status-badge status-similar">Hợp lý</span>',
        expensive: '<span class="status-badge status-expensive">Đắt</span>',
        unknown: '<span class="status-badge status-unknown">N/A</span>'
      };
      return map[status] || map.unknown;
    };

    const fair = data?.fair_price || {};
    const fairPeHist = fair?.pe_hist || {};
    const fairPbHist = fair?.pb_hist || {};
    const fairPeInd = fair?.pe_industry || {};
    const fairPbInd = fair?.pb_industry || {};
    const fairGraham = fair?.graham_number || {};

    const fmtRangeK = (p25, p75) => (!isMissing(p25) && !isMissing(p75)) ? `${fmtCloseK(p25)}–${fmtCloseK(p75)}` : 'N/A';

    // Build HTML
    let html = `
      <div class="valuation-analysis-container">
        <!-- Current Price & Multiples -->
        <div class="valuation-section">
          <h4 class="valuation-section-title">💵 Giá hiện tại & Multiples</h4>
          <div class="valuation-price-grid">
            <div class="valuation-price-card">
              <div class="valuation-price-label">Giá đóng cửa</div>
              <div class="valuation-price-value">${fmtCloseK(currentClose)}</div>
              <div class="valuation-price-meta">${!isMissing(currentAsOf) ? `as-of ${currentAsOf}` : 'N/A'}</div>
            </div>
            <div class="valuation-price-card">
              <div class="valuation-price-label">P/E (giá/EPS)</div>
              <div class="valuation-price-value">${fmtMultiple(currentPe)}</div>
              <div class="valuation-price-meta">EPS FY${data.year}: ${fmtVnd(epsVnd)}</div>
            </div>
            <div class="valuation-price-card">
              <div class="valuation-price-label">P/B (giá/BVPS)</div>
              <div class="valuation-price-value">${fmtMultiple(currentPb)}</div>
              <div class="valuation-price-meta">BVPS FY${data.year}: ${fmtVnd(bvpsVnd)}</div>
            </div>
          </div>
          <div class="valuation-price-note">
            ${!isMissing(currentCloseVnd) ? `≈ ${fmtVnd(currentCloseVnd)} (scale=${priceScale ?? 'N/A'} VND)` : ' '}
          </div>
        </div>

        <!-- Fair Price Heuristics -->
        <div class="valuation-section">
          <h4 class="valuation-section-title">🎯 Ước tính Giá hợp lý (heuristics)</h4>
          <div class="industry-comparison-table">
            <table class="valuation-table">
              <thead>
                <tr>
                  <th>Phương pháp</th>
                  <th style="text-align: right;">Giá hợp lý</th>
                  <th style="text-align: right;">Upside</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>P/E (phân vị 5y)</strong></td>
                  <td style="text-align: right;">
                    ${fmtRangeK(fairPeHist?.fair_close?.p25, fairPeHist?.fair_close?.p75)}
                    ${!isMissing(fairPeHist?.fair_close?.p50) ? `<div class="valuation-subnote">P50: ${fmtCloseK(fairPeHist.fair_close.p50)}</div>` : ''}
                  </td>
                  <td style="text-align: right;">${fmtUpside(fairPeHist?.fair_close?.p50)}</td>
                  <td>${fairBadge(fairPeHist?.status)}</td>
                </tr>
                <tr>
                  <td><strong>P/B (phân vị 5y)</strong></td>
                  <td style="text-align: right;">
                    ${fmtRangeK(fairPbHist?.fair_close?.p25, fairPbHist?.fair_close?.p75)}
                    ${!isMissing(fairPbHist?.fair_close?.p50) ? `<div class="valuation-subnote">P50: ${fmtCloseK(fairPbHist.fair_close.p50)}</div>` : ''}
                  </td>
                  <td style="text-align: right;">${fmtUpside(fairPbHist?.fair_close?.p50)}</td>
                  <td>${fairBadge(fairPbHist?.status)}</td>
                </tr>
                <tr>
                  <td><strong>P/E (median ngành)</strong></td>
                  <td style="text-align: right;">${!isMissing(fairPeInd?.fair_close) ? fmtCloseK(fairPeInd.fair_close) : 'N/A'}</td>
                  <td style="text-align: right;">${fmtUpside(fairPeInd?.fair_close)}</td>
                  <td>${fairBadge(fairPeInd?.status)}</td>
                </tr>
                <tr>
                  <td><strong>P/B (median ngành)</strong></td>
                  <td style="text-align: right;">${!isMissing(fairPbInd?.fair_close) ? fmtCloseK(fairPbInd.fair_close) : 'N/A'}</td>
                  <td style="text-align: right;">${fmtUpside(fairPbInd?.fair_close)}</td>
                  <td>${fairBadge(fairPbInd?.status)}</td>
                </tr>
                <tr>
                  <td><strong>Graham Number</strong></td>
                  <td style="text-align: right;">${!isMissing(fairGraham?.fair_close) ? fmtCloseK(fairGraham.fair_close) : 'N/A'}</td>
                  <td style="text-align: right;">${fmtUpside(fairGraham?.fair_close)}</td>
                  <td>${fairBadge(fairGraham?.status)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="valuation-disclaimer">
            Chỉ mang tính tham khảo: dùng EPS/BVPS annual và giá close; không có điều chỉnh đầy đủ cho split/rights/bonus (data limits).
          </div>
        </div>

        <!-- PEG Ratio Section -->
        <div class="valuation-section">
          <h4 class="valuation-section-title">📈 PEG Ratio (Price/Earnings-to-Growth)</h4>
          <div class="peg-ratio-display">
            <div class="peg-value">${!isMissing(data.peg_ratio.value) ? data.peg_ratio.value : 'N/A'}</div>
            <div class="peg-rating peg-rating-${data.peg_ratio.rating}">${data.peg_ratio.description}</div>
          </div>
          ${!isMissing(data.peg_ratio.earnings_growth_rate) ? `
            <div class="peg-details">
              <div class="peg-detail-item">
                <span class="peg-detail-label">Tăng trưởng lợi nhuận:</span>
                <span class="peg-detail-value">${data.peg_ratio.earnings_growth_rate}%</span>
              </div>
              <div class="peg-detail-item">
                <span class="peg-detail-label">P/E hiện tại:</span>
                <span class="peg-detail-value">${data.peg_ratio.pe_used}x</span>
              </div>
            </div>
          ` : ''}
          <div class="peg-scale">
            <div class="peg-scale-item peg-scale-very-cheap">
              <div class="peg-scale-label">&lt; 1.0</div>
              <div class="peg-scale-desc">Rẻ</div>
            </div>
            <div class="peg-scale-item peg-scale-cheap">
              <div class="peg-scale-label">1.0 - 2.0</div>
              <div class="peg-scale-desc">Khá rẻ</div>
            </div>
            <div class="peg-scale-item peg-scale-fair">
              <div class="peg-scale-label">2.0 - 3.0</div>
              <div class="peg-scale-desc">Hợp lý</div>
            </div>
            <div class="peg-scale-item peg-scale-expensive">
              <div class="peg-scale-label">&gt; 3.0</div>
              <div class="peg-scale-desc">Đắt</div>
            </div>
          </div>
        </div>

        <!-- Historical Percentile Section -->
        <div class="valuation-section">
          <h4 class="valuation-section-title">📊 Phân vị Lịch sử (5 năm)</h4>
          <div class="percentile-grid">
            ${renderPercentileChart('P/E', data.pe_percentile)}
            ${renderPercentileChart('P/B', data.pb_percentile)}
          </div>
        </div>

        <!-- Industry Comparison Section -->
        <div class="valuation-section">
          <h4 class="valuation-section-title">⚖️ So sánh Ngành</h4>
          <div class="industry-comparison-table">
            <table class="valuation-table">
              <thead>
                <tr>
                  <th>Chỉ số</th>
                  <th>Công ty</th>
                  <th>Ngành trung bình</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                ${renderIndustryComparisonRow('P/E', data.valuation_summary.pe_vs_industry)}
                ${renderIndustryComparisonRow('P/B', data.valuation_summary.pb_vs_industry)}
              </tbody>
            </table>
          </div>
          <div class="overall-valuation">
            <div class="overall-valuation-label">Đánh giá tổng quan:</div>
            <div class="overall-valuation-badge overall-valuation-${data.valuation_summary.overall}">
              ${getOverallValuationText(data.valuation_summary.overall)}
            </div>
          </div>
        </div>
      </div>
    `;

    container.innerHTML = html;

  } catch (error) {
    console.error('Error loading valuation analysis:', error);
    container.innerHTML = `
      <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
        <p>Lỗi khi tải dữ liệu định giá</p>
      </div>
    `;
  }
}

/**
 * Render percentile chart
 */
function renderPercentileChart(label, percentileData) {
  if (!percentileData) {
    return `
      <div class="percentile-chart">
        <div class="percentile-chart-label">${label}</div>
        <div class="percentile-chart-value">N/A</div>
      </div>
    `;
  }

  const current = percentileData.current;
  const n = percentileData.n;
  if (isMissing(current)) {
    return `
      <div class="percentile-chart">
        <div class="percentile-chart-label">${label}</div>
        <div class="percentile-chart-value">N/A</div>
      </div>
    `;
  }

  const p5 = percentileData.p5;
  const p25 = percentileData.p25;
  const p50 = percentileData.p50;
  const p75 = percentileData.p75;
  const p95 = percentileData.p95;

  let position = 50;
  let positionText = 'Trung bình';

  const cutoffs = [
    { p: 5, value: p5, text: 'Rất thấp' },
    { p: 25, value: p25, text: 'Thấp' },
    { p: 50, value: p50, text: 'Trung bình' },
    { p: 75, value: p75, text: 'Cao' },
    { p: 95, value: p95, text: 'Rất cao' }
  ].filter(c => !isMissing(c.value));

  if (cutoffs.length > 0) {
    const found = cutoffs.find(c => current <= c.value);
    if (found) {
      position = found.p;
      positionText = found.text;
    } else {
      position = 95;
      positionText = 'Rất cao';
    }
  }

  const fmtCutoff = (v) => !isMissing(v) ? v.toFixed(1) : 'N/A';

  return `
    <div class="percentile-chart">
      <div class="percentile-chart-label">${label}</div>
      <div class="percentile-chart-value">${current.toFixed(2)}x</div>
      <div class="percentile-bar-container">
        <div class="percentile-bar">
          <div class="percentile-marker" style="left: ${position}%;"></div>
        </div>
      </div>
      <div class="percentile-position">${positionText}</div>
      <div class="percentile-distribution">
        <span class="percentile-dist-item">P5: ${fmtCutoff(p5)}</span>
        <span class="percentile-dist-item">P25: ${fmtCutoff(p25)}</span>
        <span class="percentile-dist-item">P50: ${fmtCutoff(p50)}</span>
        <span class="percentile-dist-item">P75: ${fmtCutoff(p75)}</span>
        <span class="percentile-dist-item">P95: ${fmtCutoff(p95)}</span>
        ${!isMissing(n) ? `<span class="percentile-dist-item">n=${n}</span>` : ''}
      </div>
    </div>
  `;
}

/**
 * Render industry comparison row
 */
function renderIndustryComparisonRow(label, comparison) {
  const statusMap = {
    'cheaper': '<span class="status-badge status-cheaper">Rẻ hơn</span>',
    'expensive': '<span class="status-badge status-expensive">Đắt hơn</span>',
    'similar': '<span class="status-badge status-similar">Tương đương</span>',
    'better': '<span class="status-badge status-better">Tốt hơn</span>',
    'worse': '<span class="status-badge status-worse">Kém hơn</span>',
    'unknown': '<span class="status-badge status-unknown">N/A</span>'
  };

  return `
    <tr>
      <td><strong>${label}</strong></td>
      <td>${!isMissing(comparison.company) ? comparison.company.toFixed(2) + 'x' : 'N/A'}</td>
      <td>${!isMissing(comparison.industry) ? comparison.industry.toFixed(2) + 'x' : 'N/A'}</td>
      <td>${statusMap[comparison.status] || statusMap['unknown']}</td>
    </tr>
  `;
}

/**
 * Get overall valuation text in Vietnamese
 */
function getOverallValuationText(status) {
  const statusMap = {
    'undervalued': 'Định giá thấp - Tiềm năng tăng trưởng',
    'fair': 'Định giá hợp lý - Giá công bằng',
    'overvalued': 'Định giá cao - Cần thận trọng',
    'unknown': 'Không đủ dữ liệu'
  };
  return statusMap[status] || statusMap['unknown'];
}

// ============================================================================
// CAGR ANALYSIS
// ============================================================================

/**
 * Render CAGR Analysis component
 * @param {string} symbol - Stock symbol
 * @param {number} years - Number of years to analyze (default: 5)
 */
let cagrChartInstance = null;

async function renderCAGRAnalysis(symbol, years = 5) {
  const tableBody = document.getElementById('cagrTableBody');
  const chartCanvas = document.getElementById('cagrChart');

  if (!tableBody || !chartCanvas) return;

  try {
    tableBody.innerHTML = `
      <tr>
        <td colspan="4" style="text-align: center; padding: var(--space-4);">
          <div class="loading-spinner"></div>
          <p style="margin-top: var(--space-2); color: var(--text-secondary);">Đang tải dữ liệu CAGR...</p>
        </td>
      </tr>
    `;

    const data = await API.getCAGRAnalysis(symbol, years);

    if (data.error) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align: center; padding: var(--space-4); color: var(--text-secondary);">
            <p>${data.error}</p>
          </td>
        </tr>
      `;
      return;
    }

    // Render table
    const metrics = data.metrics;
    const metricKeys = ['revenue', 'net_profit', 'total_assets', 'equity_total'];

    let tableHtml = '';
    for (const key of metricKeys) {
      const m = metrics[key];
      if (!m) continue;

      const ratingClass = getCAGRRatingClass(m.rating);
      tableHtml += `
        <tr>
          <td>
            <span style="font-weight: 500;">${m.name}</span>
          </td>
          <td>
            <span class="${ratingClass}" style="font-weight: 600;">
              ${m.cagr_percent !== null ? m.cagr_percent + '%' : 'N/A'}
            </span>
          </td>
          <td>
            <span class="cagr-description">${m.description}</span>
          </td>
          <td>
            <span class="cagr-rating-badge ${ratingClass}">${getCAGRRatingText(m.rating)}</span>
          </td>
        </tr>
      `;
    }
    tableBody.innerHTML = tableHtml;

    // Render chart
    renderCAGRChart(data);

    // Update period info
    const periodInfo = document.getElementById('cagrPeriodInfo');
    if (periodInfo && data.period) {
      periodInfo.textContent = `Giai đoạn: ${data.period.start_year} - ${data.period.end_year} (${data.period.years} năm)`;
    }

  } catch (error) {
    console.error('Error loading CAGR analysis:', error);
    tableBody.innerHTML = `
      <tr>
        <td colspan="4" style="text-align: center; padding: var(--space-4); color: var(--error-color);">
          <p>Lỗi tải dữ liệu CAGR</p>
        </td>
      </tr>
    `;
  }
}

function renderCAGRChart(data) {
  const canvas = document.getElementById('cagrChart');
  if (!canvas || !data || !data.metrics) return;

  const ctx = canvas.getContext('2d');

  // Destroy existing chart
  if (cagrChartInstance) {
    cagrChartInstance.destroy();
  }

  const metrics = data.metrics;
  const labels = ['Doanh thu', 'Lợi nhuận', 'Tài sản', 'Vốn CSH'];
  // Preserve null/undefined for missing data - don't use 0 fallback
  const values = [
    metrics.revenue?.cagr_percent ?? null,
    metrics.net_profit?.cagr_percent ?? null,
    metrics.total_assets?.cagr_percent ?? null,
    metrics.equity_total?.cagr_percent ?? null
  ];

  const colors = values.map(v => v !== null ? getCAGRColor(v) : 'rgba(156, 163, 175, 0.5)');

  cagrChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'CAGR (%)',
        data: values,
        backgroundColor: colors,
        borderColor: colors.map(c => c.replace('0.7', '1')),
        borderWidth: 1,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              const value = context.raw;
              if (value === null || value === undefined) {
                return 'CAGR: Không có dữ liệu';
              }
              return `CAGR: ${value.toFixed(2)}%/năm`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function (value) {
              return value + '%';
            }
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.05)'
          }
        },
        x: {
          grid: {
            display: false
          }
        }
      }
    }
  });
}

function getCAGRColor(cagrPercent) {
  if (cagrPercent >= 15) return 'rgba(34, 197, 94, 0.7)';  // Green - excellent
  if (cagrPercent >= 10) return 'rgba(59, 130, 246, 0.7)'; // Blue - good
  if (cagrPercent >= 5) return 'rgba(234, 179, 8, 0.7)';   // Yellow - moderate
  if (cagrPercent >= 0) return 'rgba(249, 115, 22, 0.7)';  // Orange - low
  return 'rgba(239, 68, 68, 0.7)';                         // Red - negative
}

function getCAGRRatingClass(rating) {
  const classMap = {
    'excellent': 'cagr-excellent',
    'strong': 'cagr-strong',
    'good': 'cagr-good',
    'moderate': 'cagr-moderate',
    'low': 'cagr-low',
    'negative': 'cagr-negative',
    'unknown': 'cagr-unknown'
  };
  return classMap[rating] || 'cagr-unknown';
}

function getCAGRRatingText(rating) {
  const textMap = {
    'excellent': 'Xuất sắc',
    'strong': 'Mạnh',
    'good': 'Tốt',
    'moderate': 'Khá',
    'low': 'Thấp',
    'negative': 'Âm',
    'unknown': 'N/A'
  };
  return textMap[rating] || 'N/A';
}

// ============================================================================
// EARLY WARNING SYSTEM
// ============================================================================

/**
 * Render Early Warning System component
 * @param {Object} warningData - Early warning data from API
 */
async function renderEarlyWarning(warningData) {
  const container = document.getElementById('earlyWarningSection');
  if (!container) return;

  if (!warningData) {
    container.innerHTML = `
      <div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);">
        <p>Đang tải cảnh báo sớm...</p>
      </div>
    `;
    return;
  }

  const { risk_score, risk_level, alerts, positive_signals, recommendation } = warningData;
  const period = warningData.period || {};
  const subtitleParts = ['Phát hiện rủi ro tài chính'];
  if (period.as_of_period) subtitleParts.push(`Kỳ: ${period.as_of_period}`);
  if (period.trend_source) subtitleParts.push(`Trend: ${period.trend_source}`);
  const subtitleText = subtitleParts.join(' · ');

  // Determine risk level styling
  let riskClass = 'low';
  let riskEmoji = '🟢';
  let riskText = 'Thấp';
  let riskColor = '#22c55e';

  if (risk_level === 'medium') {
    riskClass = 'medium';
    riskEmoji = '🟡';
    riskText = 'Trung bình';
    riskColor = '#f59e0b';
  } else if (risk_level === 'high') {
    riskClass = 'high';
    riskEmoji = '🟠';
    riskText = 'Cao';
    riskColor = '#f97316';
  } else if (risk_level === 'critical') {
    riskClass = 'critical';
    riskEmoji = '🔴';
    riskText = 'Nguy hiểm';
    riskColor = '#ef4444';
  }

  // Generate alerts HTML
  let alertsHtml = '';
  if (alerts && alerts.length > 0) {
    alertsHtml = alerts.map(alert => {
      const severityIcon = alert.severity === 'critical' ? '🔴' :
        alert.severity === 'warning' ? '⚠️' : 'ℹ️';
      const severityClass = `ew-alert-${alert.severity}`;

      return `
        <div class="ew-alert-card ${severityClass}">
          <div class="ew-alert-icon">${severityIcon}</div>
          <div class="ew-alert-content">
            <div class="ew-alert-message">${alert.message}</div>
            ${alert.value ? `<div class="ew-alert-value">${formatAlertValue(alert.value)}</div>` : ''}
          </div>
        </div>
      `;
    }).join('');
  } else {
    alertsHtml = `
      <div class="ew-no-alerts">
        <div class="ew-no-alerts-icon">✅</div>
        <div class="ew-no-alerts-text">Không phát hiện cảnh báo nào</div>
      </div>
    `;
  }

  // Generate positive signals HTML
  let positiveHtml = '';
  if (positive_signals && positive_signals.length > 0) {
    positiveHtml = positive_signals.map(signal => `
      <div class="ew-positive-item">
        <span class="ew-positive-icon">✓</span>
        <span class="ew-positive-text">${signal.message}</span>
      </div>
    `).join('');
  }

  // Generate HTML
  container.innerHTML = `
    <div class="early-warning-card">
      <div class="ew-header">
        <div class="ew-title-section">
          <div class="ew-icon">🚨</div>
          <div>
            <h3 class="ew-title">Hệ thống Cảnh báo Sớm</h3>
            <div class="ew-subtitle">${subtitleText}</div>
          </div>
        </div>
        <div class="ew-risk-badge">
          <div class="ew-risk-score ${riskClass}" style="--risk-color: ${riskColor};">
            <div class="ew-risk-score-value">${risk_score}</div>
            <div class="ew-risk-score-label">/100</div>
          </div>
          <div class="ew-risk-level ${riskClass}" style="--risk-color: ${riskColor};">
            <span class="ew-risk-emoji">${riskEmoji}</span>
            <span class="ew-risk-text">${riskText}</span>
          </div>
        </div>
      </div>

      <div class="ew-gauge-container">
        <div class="ew-gauge-bar">
          <div class="ew-gauge-fill ew-gauge-low" style="width: 25%;"></div>
          <div class="ew-gauge-fill ew-gauge-medium" style="width: 25%;"></div>
          <div class="ew-gauge-fill ew-gauge-high" style="width: 25%;"></div>
          <div class="ew-gauge-fill ew-gauge-critical" style="width: 25%;"></div>
          <div class="ew-gauge-marker" style="left: ${risk_score}%;"></div>
        </div>
        <div class="ew-gauge-labels">
          <span>Thấp</span>
          <span>Trung bình</span>
          <span>Cao</span>
          <span>Nguy hiểm</span>
        </div>
      </div>

      ${alerts ? `
      <div class="ew-alerts-section">
        <h4 class="ew-section-title">Cảnh báo</h4>
        <div class="ew-alerts-grid">
          ${alertsHtml}
        </div>
      </div>
      ` : ''}

      ${positive_signals && positive_signals.length > 0 ? `
      <div class="ew-positive-section">
        <h4 class="ew-section-title">Tín hiệu tích cực</h4>
        <div class="ew-positive-list">
          ${positiveHtml}
        </div>
      </div>
      ` : ''}

      ${recommendation ? `
      <div class="ew-recommendation">
        <div class="ew-recommendation-title">💡 Khuyến nghị</div>
        <div class="ew-recommendation-text">${recommendation}</div>
      </div>
      ` : ''}
    </div>
  `;
}

/**
 * Format alert value for display
 */
function formatAlertValue(value) {
  if (!value) return '';

  const parts = [];
  if (value.current !== undefined) {
    const current = typeof value.current === 'number' ?
      (value.current > 10 ? value.current.toFixed(2) : (value.current * 100).toFixed(2) + '%') :
      value.current;
    parts.push(`Hiện tại: <strong>${current}</strong>`);
  }
  if (value.previous !== undefined) {
    const previous = typeof value.previous === 'number' ?
      (value.previous > 10 ? value.previous.toFixed(2) : (value.previous * 100).toFixed(2) + '%') :
      value.previous;
    parts.push(`Trước: ${previous}`);
  }
  if (value.trend) {
    const trendIcon = value.trend === 'declining' ? '📉' :
      value.trend === 'increasing' ? '📈' : '➡️';
    parts.push(`${trendIcon} ${value.trend === 'declining' ? 'Giảm' : value.trend === 'increasing' ? 'Tăng' : 'Ổn định'}`);
  }

  return parts.join(' | ');
}

// ============================================================================
// EARLY WARNING SYSTEM
// ============================================================================

/**
 * Render Early Warning System component
 */
// Legacy duplicate kept for backward compatibility (do not use; superseded above)
async function renderEarlyWarningLegacy(warningData) {
  const container = document.getElementById('earlyWarningSection');
  if (!container) return;

  if (!warningData) {
    container.innerHTML = '<div style="text-align: center; padding: var(--space-8); color: var(--text-secondary);"><p>Đang tải cảnh báo sớm...</p></div>';
    return;
  }

  const { risk_score, risk_level, alerts, positive_signals, recommendation } = warningData;

  let riskClass = 'low';
  let riskEmoji = '🟢';
  let riskText = 'Thấp';
  let riskColor = '#22c55e';

  if (risk_level === 'medium') {
    riskClass = 'medium';
    riskEmoji = '🟡';
    riskText = 'Trung bình';
    riskColor = '#f59e0b';
  } else if (risk_level === 'high') {
    riskClass = 'high';
    riskEmoji = '🟠';
    riskText = 'Cao';
    riskColor = '#f97316';
  } else if (risk_level === 'critical') {
    riskClass = 'critical';
    riskEmoji = '🔴';
    riskText = 'Nguy hiểm';
    riskColor = '#ef4444';
  }

  let alertsHtml = '';
  if (alerts && alerts.length > 0) {
    alertsHtml = alerts.map(alert => {
      const severityIcon = alert.severity === 'critical' ? '🔴' : alert.severity === 'warning' ? '⚠️' : 'ℹ️';
      const severityClass = 'ew-alert-' + alert.severity;
      return '<div class="ew-alert-card ' + severityClass + '"><div class="ew-alert-icon">' + severityIcon + '</div><div class="ew-alert-content"><div class="ew-alert-message">' + alert.message + '</div>' + (alert.value ? '<div class="ew-alert-value">' + formatAlertValue(alert.value) + '</div>' : '') + '</div></div>';
    }).join('');
  } else {
    alertsHtml = '<div class="ew-no-alerts"><div class="ew-no-alerts-icon">✅</div><div class="ew-no-alerts-text">Không phát hiện cảnh báo nào</div></div>';
  }

  let positiveHtml = '';
  if (positive_signals && positive_signals.length > 0) {
    positiveHtml = positive_signals.map(signal => '<div class="ew-positive-item"><span class="ew-positive-icon">✓</span><span class="ew-positive-text">' + signal.message + '</span></div>').join('');
  }

  container.innerHTML = '<div class="early-warning-card"><div class="ew-header"><div class="ew-title-section"><div class="ew-icon">🚨</div><div><h3 class="ew-title">Hệ thống Cảnh báo Sớm</h3><div class="ew-subtitle">Phát hiện rủi ro tài chính</div></div></div><div class="ew-risk-badge"><div class="ew-risk-score ' + riskClass + '" style="--risk-color: ' + riskColor + ';"><div class="ew-risk-score-value">' + risk_score + '</div><div class="ew-risk-score-label">/100</div></div><div class="ew-risk-level ' + riskClass + '" style="--risk-color: ' + riskColor + ';"><span class="ew-risk-emoji">' + riskEmoji + '</span><span class="ew-risk-text">' + riskText + '</span></div></div></div><div class="ew-gauge-container"><div class="ew-gauge-bar"><div class="ew-gauge-fill ew-gauge-low" style="width: 25%;"></div><div class="ew-gauge-fill ew-gauge-medium" style="width: 25%;"></div><div class="ew-gauge-fill ew-gauge-high" style="width: 25%;"></div><div class="ew-gauge-fill ew-gauge-critical" style="width: 25%;"></div><div class="ew-gauge-marker" style="left: ' + risk_score + '%;"></div></div><div class="ew-gauge-labels"><span>Thấp</span><span>Trung bình</span><span>Cao</span><span>Nguy hiểm</span></div></div>' + (alerts ? '<div class="ew-alerts-section"><h4 class="ew-section-title">Cảnh báo</h4><div class="ew-alerts-grid">' + alertsHtml + '</div></div>' : '') + (positive_signals && positive_signals.length > 0 ? '<div class="ew-positive-section"><h4 class="ew-section-title">Tín hiệu tích cực</h4><div class="ew-positive-list">' + positiveHtml + '</div></div>' : '') + (recommendation ? '<div class="ew-recommendation"><div class="ew-recommendation-title">💡 Khuyến nghị</div><div class="ew-recommendation-text">' + recommendation + '</div></div>' : '') + '</div>';
}

/**
 * Format alert value for display
 */
function formatAlertValueLegacy(value) {
  if (!value) return '';
  const parts = [];
  if (value.current !== undefined) {
    const current = typeof value.current === 'number' ? (value.current > 10 ? value.current.toFixed(2) : (value.current * 100).toFixed(2) + '%') : value.current;
    parts.push('Hiện tại: <strong>' + current + '</strong>');
  }
  if (value.previous !== undefined) {
    const previous = typeof value.previous === 'number' ? (value.previous > 10 ? value.previous.toFixed(2) : (value.previous * 100).toFixed(2) + '%') : value.previous;
    parts.push('Trước: ' + previous);
  }
  if (value.trend) {
    const trendIcon = value.trend === 'declining' ? '📉' : value.trend === 'increasing' ? '📈' : '➡️';
    const trendText = value.trend === 'declining' ? 'Giảm' : value.trend === 'increasing' ? 'Tăng' : 'Ổn định';
    parts.push(trendIcon + ' ' + trendText);
  }
  return parts.join(' | ');
}
