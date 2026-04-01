/**
 * Valuation Analysis Module
 * Provides advanced valuation metrics visualization
 */

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

    // Build HTML
    const pegValue = data.peg_ratio.value !== null ? data.peg_ratio.value : 'N/A';
    const pegRating = data.peg_ratio.rating;
    const pegDescription = data.peg_ratio.description;

    let pegDetails = '';
    if (data.peg_ratio.earnings_growth_rate) {
      pegDetails = `
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
      `;
    }

    let html = `
      <div class="valuation-analysis-container">
        <!-- PEG Ratio Section -->
        <div class="valuation-section">
          <h4 class="valuation-section-title">📈 PEG Ratio (Price/Earnings-to-Growth)</h4>
          <div class="peg-ratio-display">
            <div class="peg-value">${pegValue}</div>
            <div class="peg-rating peg-rating-${pegRating}">${pegDescription}</div>
          </div>
          ${pegDetails}
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
  const current = percentileData.current;
  if (current === null) {
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

  if (p5 !== null && current <= p5) {
    position = 5;
    positionText = 'Rất thấp';
  } else if (p25 !== null && current <= p25) {
    position = 25;
    positionText = 'Thấp';
  } else if (p50 !== null && current <= p50) {
    position = 50;
    positionText = 'Trung bình';
  } else if (p75 !== null && current <= p75) {
    position = 75;
    positionText = 'Cao';
  } else {
    position = 95;
    positionText = 'Rất cao';
  }

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
        <span class="percentile-dist-item">P5: ${p5 !== null ? p5.toFixed(1) : 'N/A'}</span>
        <span class="percentile-dist-item">P25: ${p25 !== null ? p25.toFixed(1) : 'N/A'}</span>
        <span class="percentile-dist-item">P50: ${p50 !== null ? p50.toFixed(1) : 'N/A'}</span>
        <span class="percentile-dist-item">P75: ${p75 !== null ? p75.toFixed(1) : 'N/A'}</span>
        <span class="percentile-dist-item">P95: ${p95 !== null ? p95.toFixed(1) : 'N/A'}</span>
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

  const companyValue = comparison.company !== null ? comparison.company.toFixed(2) + 'x' : 'N/A';
  const industryValue = comparison.industry !== null ? comparison.industry.toFixed(2) + 'x' : 'N/A';
  const statusBadge = statusMap[comparison.status] || statusMap['unknown'];

  return `
    <tr>
      <td><strong>${label}</strong></td>
      <td>${companyValue}</td>
      <td>${industryValue}</td>
      <td>${statusBadge}</td>
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
