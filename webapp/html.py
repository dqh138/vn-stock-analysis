from __future__ import annotations

from html import escape
from typing import Optional


def render_index(*, prefill_symbol: Optional[str] = None) -> str:
    symbol_attr = escape((prefill_symbol or "").strip().upper())
    return f"""<!doctype html>
<html lang="vi" data-theme="dark">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Báo cáo tài chính • Cổ phiếu Việt Nam</title>
    <link rel="stylesheet" href="/static/glm.css" />
  </head>
  <body data-prefill-symbol="{symbol_attr}">
    <header class="topbar">
      <div class="topbar__inner">
        <a class="brand" href="/" aria-label="Trang chủ">
          <div class="brand__title">Báo cáo tài chính</div>
          <div class="brand__subtitle">Cổ phiếu Việt Nam • Chỉ số theo ngành (ICB3)</div>
        </a>
        <div class="search">
          <input id="symbolInput" class="input" placeholder="Nhập mã (VD: VCB, HPG)..." autocomplete="off" list="symbolDatalist" />
          <datalist id="symbolDatalist"></datalist>
          <button id="loadBtn" class="btn btn--primary">Mở</button>
        </div>
      </div>
    </header>

    <main class="container">
      <section class="grid">
        <div class="card">
          <div class="card__head">
            <div class="card__title">Công ty</div>
            <div id="status" class="muted">Chưa chọn mã</div>
          </div>
          <div id="companyMeta" class="meta"></div>
        </div>

        <div class="card">
          <div class="card__head">
            <div class="card__title">Kỳ dữ liệu</div>
            <div class="muted">Lấy theo dữ liệu có sẵn trong DB</div>
          </div>
          <div class="controls">
            <label class="field">
              <span class="field__label">Hiển thị</span>
              <select id="modeSelect" class="select">
                <option value="both" selected>Đầy đủ + Đặc trưng</option>
                <option value="industry">Chỉ đặc trưng theo ngành</option>
                <option value="all">Chỉ bảng đầy đủ</option>
              </select>
            </label>
            <label class="field">
              <span class="field__label">Năm</span>
              <select id="yearSelect" class="select"></select>
            </label>
            <label class="field">
              <span class="field__label">Quý</span>
              <select id="quarterSelect" class="select">
                <option value="">Năm (Yearly)</option>
                <option value="1">Q1</option>
                <option value="2">Q2</option>
                <option value="3">Q3</option>
                <option value="4">Q4</option>
              </select>
            </label>
          </div>
        </div>
      </section>

      <nav class="tabs" aria-label="Tabs">
        <button class="tab is-active" data-tab="overview" type="button">Tổng quan</button>
        <button class="tab" data-tab="tables" type="button">Bảng chỉ tiêu</button>
        <button class="tab" data-tab="price" type="button">Giá</button>
      </nav>

      <section id="panel-overview" class="card tab-panel is-active">
        <div class="card__head">
          <div class="card__title">Diễn dịch nhanh</div>
          <div class="muted">Xu hướng theo năm + giá gần đây</div>
        </div>
        <div id="overviewCharts" class="charts-grid"></div>
      </section>

      <section id="panel-tables" class="card tab-panel">
        <div class="card__head">
          <div class="card__title">Chỉ tiêu</div>
          <div id="periodMeta" class="muted"></div>
        </div>
        <div id="tables" class="tables"></div>
      </section>

      <section id="panel-price" class="card tab-panel">
        <div class="card__head">
          <div class="card__title">Giá (close)</div>
          <div id="priceMeta" class="muted"></div>
        </div>
        <div id="priceChart" class="price-panel"></div>
      </section>
    </main>

    <div id="modalOverlay" class="modal-overlay" hidden></div>
    <div id="metricModal" class="modal" hidden role="dialog" aria-modal="true" aria-labelledby="metricModalTitle">
      <div class="modal__head">
        <div>
          <div id="metricModalTitle" class="modal__title">Chỉ tiêu</div>
          <div id="metricModalSub" class="modal__sub"></div>
        </div>
        <div class="modal__actions">
          <label class="field">
            <span class="field__label">Chart</span>
            <select id="metricChartType" class="select">
              <option value="auto" selected>Auto</option>
              <option value="line">Line</option>
              <option value="area">Area</option>
              <option value="bar">Bar</option>
            </select>
          </label>
          <label class="field">
            <span class="field__label">Series</span>
            <select id="metricPeriod" class="select">
              <option value="yearly" selected>Yearly</option>
              <option value="quarterly">Quarterly</option>
            </select>
          </label>
          <button id="metricModalClose" class="btn">Đóng</button>
        </div>
      </div>
      <div class="modal__body">
        <div id="metricModalDesc" class="muted"></div>
        <div id="metricChartWrap" class="metric-chart"></div>
        <div id="metricSeriesTable" class="series-table"></div>
      </div>
    </div>

    <script src="/static/app.js"></script>
  </body>
</html>
"""
