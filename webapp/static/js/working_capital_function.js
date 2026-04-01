
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
    container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: var(--space-8);">Không có dữ liệu về hiệu quả vốn lưu động</p>';
    return;
  }

  // Calculate CCC if not provided
  const calculatedCCC = (dso || 0) + (dio || 0) - (dpo || 0);
  const displayCCC = ccc !== null && ccc !== undefined ? ccc : calculatedCCC;

  // Determine rating and colors
  const getCCCRating = (value) => {
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
    if (!value) return { text: 'N/A', color: '#9ca3af' };
    if (value < 30) return { text: 'Tốt', color: '#22c55e' };
    if (value < 45) return { text: 'Khá', color: '#f59e0b' };
    return { text: 'Cần cải thiện', color: '#ef4444' };
  };

  const getDIORating = (value) => {
    if (!value) return { text: 'N/A', color: '#9ca3af' };
    if (value < 30) return { text: 'Tốt', color: '#22c55e' };
    if (value < 60) return { text: 'Khá', color: '#f59e0b' };
    if (value < 90) return { text: 'Trung bình', color: '#f97316' };
    return { text: 'Cần cải thiện', color: '#ef4444' };
  };

  const getDPORating = (value) => {
    if (!value) return { text: 'N/A', color: '#9ca3af' };
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
          <div style="font-size: var(--text-4xl); font-weight: var(--font-bold);">${displayCCC.toFixed(0)}<span style="font-size: var(--text-xl); opacity: 0.8;"> ngày</span></div>
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
      ${dso !== null && dio !== null && dpo !== null ? `
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
    ${dso !== null && dio !== null && dpo !== null ? `
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
          <span style="font-size: var(--text-xl); font-weight: var(--font-bold); color: ${cccRating.color};">${displayCCC.toFixed(0)} ngày</span>
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
