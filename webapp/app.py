from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from stock_database.financial_taxonomy import GROUPS, TABLE_METRICS, industry_profile

from . import db, html
from .analysis.annual_selector import (
    get_financial_ratios_annual,
    get_latest_year,
    get_previous_year,
    select_balance_sheet_annual,
    select_balance_sheet_annual_with_provenance,
    select_cash_flow_annual,
    select_cash_flow_annual_with_provenance,
    select_income_statement_annual,
    select_income_statement_annual_with_provenance,
)


def _metric_to_item(table: str, metric_id: str, value: Any) -> Dict[str, Any]:
    metric = TABLE_METRICS[table][metric_id]
    group = GROUPS.get(metric.group, {"label_vi": metric.group})
    return {
        "id": metric.id,
        "label": metric.label,
        "group": metric.group,
        "group_label": group.get("label_vi", metric.group),
        "unit": metric.unit,
        "description": metric.description,
        "value": value,
    }


def _validate_symbol(symbol: str) -> str:
    symbol = (symbol or "").strip().upper()
    if len(symbol) < 2 or len(symbol) > 5 or not symbol.isalpha():
        raise HTTPException(status_code=400, detail="symbol must be a valid ticker (e.g., VCB)")
    return symbol


app = FastAPI(title="Báo cáo tài chính", version="1.0")

STATIC_DIR = Path(__file__).with_name("static")
TEMPLATES_DIR = Path(__file__).with_name("templates")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _compute_asset_version() -> str:
    """
    Compute deterministic asset version from newest static/template mtime.
    Ensures browser always requests latest CSS/JS after local changes.
    """
    tracked_files = [
        STATIC_DIR / "css" / "main.css",
        STATIC_DIR / "css" / "design-system.css",
        STATIC_DIR / "css" / "valuation_analysis.css",
        STATIC_DIR / "js" / "app.js",
        STATIC_DIR / "js" / "valuation_analysis.js",
        TEMPLATES_DIR / "index.html",
    ]
    mtimes = [int(path.stat().st_mtime) for path in tracked_files if path.exists()]
    return str(max(mtimes)) if mtimes else "dev"


def _render_index_html(prefill_symbol: Optional[str] = None) -> HTMLResponse:
    """
    Render index.html with cache-busted static asset URLs.
    """
    template_path = TEMPLATES_DIR / "index.html"
    if not template_path.exists():
        return HTMLResponse(content=html.render_index(prefill_symbol=prefill_symbol))

    asset_version = _compute_asset_version()
    content = template_path.read_text(encoding="utf-8").replace("__ASSET_VERSION__", asset_version)

    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


# ============================================================================
# NEW UI ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve new UI"""
    return _render_index_html(prefill_symbol=None)


@app.get("/company/{symbol}", response_class=HTMLResponse)
def company_page(symbol: str) -> HTMLResponse:
    """Serve company detail page (SPA)"""
    return _render_index_html(prefill_symbol=_validate_symbol(symbol))


# ============================================================================
# NEW API ENDPOINTS FOR SPA
# ============================================================================

@app.get("/api/search")
def api_search(q: Annotated[str, Query(max_length=64)] = "") -> List[Dict[str, Any]]:
    """Search companies for autocomplete"""
    with db.connect() as conn:
        results = db.search_symbols(conn, q=q, limit=20)
    return [{"ticker": r["ticker"], "name": r.get("organ_name", ""), "industry": r.get("icb_name3", "")} for r in results]


@app.get("/api/company/{symbol}")
def api_company(symbol: str) -> Dict[str, Any]:
    """Get company metadata"""
    symbol = _validate_symbol(symbol)
    with db.connect() as conn:
        meta = db.get_symbol_meta(conn, symbol)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {symbol}")
    return {
        "ticker": symbol,
        "name": meta.get("organ_name", ""),
        "industry": meta.get("icb_name3", ""),
        "exchange": meta.get("exchange", ""),
        "icb_code": meta.get("icb_code3", "")
    }


@app.get("/api/exchanges")
def api_exchanges() -> List[Dict[str, Any]]:
    """Get list of exchanges"""
    with db.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT exchange
                FROM stock_exchange
                WHERE exchange IS NOT NULL AND exchange != 'DELISTED' AND exchange != 'BOND'
                ORDER BY exchange
            """)

            results = []
            for row in cursor.fetchall():
                results.append({
                    "name": row["exchange"] or ""
                })

    return results

@app.get("/api/industries")
def api_industries() -> List[Dict[str, Any]]:
    """Get list of industries with company counts"""
    with db.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT icb_name3, COUNT(*) as count
                FROM stock_industry
                WHERE icb_name3 IS NOT NULL
                GROUP BY icb_name3
                ORDER BY count DESC
            """)

            results = []
            for row in cursor.fetchall():
                results.append({
                    "name": row["icb_name3"],
                    "icb_code": "",
                    "count": row["count"]
                })

    return results


@app.get("/api/rankings/years")
def api_rankings_years() -> Dict[str, Any]:
    """Get available years for rankings"""
    with db.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT year
                FROM financial_ratios
                WHERE quarter IS NULL
                ORDER BY year DESC
            """)
            # get distinct financial years (FY data only)
            years = sorted([int(row['year']) for row in cursor.fetchall()], reverse=True)
        # determine a sensible default year using the shared ranking logic
        from .analysis import rankings as _rankings
        default_year = _rankings._suggest_default_year(conn)
        return {"years": years, "default_year": default_year}


@app.get("/api/rankings")
def api_rankings(
    sort_by: Annotated[Literal["overall", "valuation", "growth"], Query()] = "overall",
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None,
    limit: Annotated[int, Query(ge=10, le=200)] = 50,
    industry: Annotated[Optional[str], Query(max_length=64)] = None,
    exchange: Annotated[Optional[str], Query(max_length=64)] = None,
) -> Dict[str, Any]:
    """
    Rank stocks by:
      1) Valuation (cheap/expensive vs peers)
      2) Growth potential (EPS CAGR + profitability)
    """
    from .analysis.rankings import get_stock_rankings

    result = get_stock_rankings(
        year=year,
        sort_by=sort_by,
        limit=limit,
        industry=industry,
        exchange=exchange,
    )
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=500, detail=str(result["error"]))
    return result


@app.get("/api/financials/{symbol}/ratios")
def api_financial_ratios(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None
) -> Dict[str, Any]:
    """Get financial ratios for a company"""
    symbol = _validate_symbol(symbol)

    with db.connect() as conn:
        with conn.cursor() as cursor:
            if year:
                cursor.execute("""
                    SELECT * FROM financial_ratios
                    WHERE symbol = %s AND year = %s AND quarter IS NULL
                """, (symbol, year))
            else:
                cursor.execute("""
                    SELECT * FROM financial_ratios
                    WHERE symbol = %s AND quarter IS NULL
                    ORDER BY year DESC LIMIT 1
                """, (symbol,))

            row = cursor.fetchone()

    if not row:
        return {"symbol": symbol, "year": year, "data": {}, "period_type": "ANNUAL", "as_of_period": None}

    out = dict(row)
    out["period_type"] = "ANNUAL"
    out["as_of_period"] = f"FY {out.get('year')}" if out.get("year") is not None else None
    return out


@app.get("/api/financials/{symbol}/years")
def api_financial_years(symbol: str) -> Dict[str, Any]:
    """Get available annual years for a company (for the period selector)."""
    symbol = _validate_symbol(symbol)

    with db.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT year
                FROM financial_ratios
                WHERE symbol = %s AND quarter IS NULL AND year IS NOT NULL
                ORDER BY year DESC
                """,
                (symbol,),
            )
            years = [int(row["year"]) for row in cursor.fetchall() if row["year"] is not None]

            if not years:
                cursor.execute(
                    """
                    SELECT DISTINCT year
                    FROM (
                        SELECT year FROM balance_sheet WHERE symbol = %s AND quarter IS NULL AND year IS NOT NULL
                        UNION
                        SELECT year FROM income_statement WHERE symbol = %s AND quarter IS NULL AND year IS NOT NULL
                        UNION
                        SELECT year FROM cash_flow_statement WHERE symbol = %s AND quarter IS NULL AND year IS NOT NULL
                    ) sub
                    ORDER BY year DESC
                    """,
                    (symbol, symbol, symbol),
                )
                years = [int(row["year"]) for row in cursor.fetchall() if row["year"] is not None]

        latest_year = max(years) if years else None
        return {"symbol": symbol, "years": years, "latest_year": latest_year}


@app.get("/api/financials/{symbol}/balance")
def api_balance_sheet(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None
) -> Dict[str, Any]:
    """Get balance sheet for a company"""
    symbol = _validate_symbol(symbol)

    with db.connect() as conn:
        effective_year = int(year) if year is not None else get_latest_year(conn, symbol)
        if effective_year is None:
            return {"symbol": symbol, "year": year, "period_type": "ANNUAL", "as_of_period": None}

        ratios_row = get_financial_ratios_annual(conn, symbol, effective_year)
        row, selection = select_balance_sheet_annual_with_provenance(
            conn, symbol, effective_year, financial_ratios_row=ratios_row
        )
        out = row or {"symbol": symbol, "year": effective_year}
        out["period_type"] = "ANNUAL"
        out["as_of_period"] = f"FY {effective_year}"
        out["selection"] = selection
        return out


@app.get("/api/financials/{symbol}/income")
def api_income_statement(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None
) -> Dict[str, Any]:
    """Get income statement for a company"""
    symbol = _validate_symbol(symbol)

    with db.connect() as conn:
        effective_year = int(year) if year is not None else get_latest_year(conn, symbol)
        if effective_year is None:
            return {"symbol": symbol, "year": year, "period_type": "ANNUAL", "as_of_period": None}

        row, selection = select_income_statement_annual_with_provenance(conn, symbol, effective_year)
        out = row or {"symbol": symbol, "year": effective_year}
        out["period_type"] = "ANNUAL"
        out["as_of_period"] = f"FY {effective_year}"
        out["selection"] = selection
        return out


@app.get("/api/financials/{symbol}/cashflow")
def api_cash_flow(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None
) -> Dict[str, Any]:
    """Get cash flow statement for a company"""
    symbol = _validate_symbol(symbol)

    with db.connect() as conn:
        effective_year = int(year) if year is not None else get_latest_year(conn, symbol)
        if effective_year is None:
            return {"symbol": symbol, "year": year, "period_type": "ANNUAL", "as_of_period": None}

        ratios_row = get_financial_ratios_annual(conn, symbol, effective_year)
        balance_row = select_balance_sheet_annual(conn, symbol, effective_year, financial_ratios_row=ratios_row)
        row, selection = select_cash_flow_annual_with_provenance(
            conn, symbol, effective_year, balance_sheet_row=balance_row
        )
        out = row or {"symbol": symbol, "year": effective_year}
        out["period_type"] = "ANNUAL"
        out["as_of_period"] = f"FY {effective_year}"
        out["selection"] = selection
        return out


@app.get("/api/financials/{symbol}/risk")
def api_risk_analysis(
    symbol: str,
    days: Annotated[Optional[int], Query(ge=30, le=730)] = 365
) -> Dict[str, Any]:
    """
    Get risk analysis for a stock based on price history.

    Calculates:
    - Volatility (30d, 90d, 1y)
    - Beta vs VNINDEX
    - Value at Risk (VaR)
    - Sharpe Ratio
    - Maximum Drawdown
    """
    symbol = _validate_symbol(symbol)

    from .analysis.risk_analysis import analyze_stock_risk

    try:
        risk_metrics = analyze_stock_risk(
            symbol=symbol,
            days=days or 365,
            risk_free_rate=0.05  # 5% annual for Vietnam
        )
        return {
            "symbol": symbol,
            "days_analyzed": days,
            **risk_metrics
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "error": str(e),
            "volatility_30d": {},
            "volatility_90d": {},
            "volatility_1y": {},
            "beta": {},
            "var": {},
            "sharpe_ratio": {},
            "max_drawdown": {}
        }


# ============================================================================
# LEGACY API ENDPOINTS
# ============================================================================


@app.get("/api/health")
def health() -> Dict[str, Any]:
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"ok": True, "db": "supabase"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/symbols")
def api_symbols(
    q: Annotated[str, Query(max_length=64)] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> List[Dict[str, Any]]:
    with db.connect() as conn:
        return db.search_symbols(conn, q=q, limit=limit)


@app.get("/api/symbol/{symbol}/meta")
def api_symbol_meta(symbol: str) -> Dict[str, Any]:
    symbol = _validate_symbol(symbol)
    with db.connect() as conn:
        meta = db.get_symbol_meta(conn, symbol)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {symbol}")
    return meta


@app.get("/api/symbol/{symbol}/periods")
def api_symbol_periods(symbol: str) -> Dict[str, Any]:
    symbol = _validate_symbol(symbol)
    with db.connect() as conn:
        return db.get_available_periods(conn, symbol)


@app.get("/api/symbol/{symbol}/financials")
def api_symbol_financials(
    symbol: str,
    mode: Annotated[Literal["industry", "all"], Query()] = "industry",
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None,
    quarter: Annotated[Optional[int], Query(ge=1, le=4)] = None,
) -> Dict[str, Any]:
    symbol = _validate_symbol(symbol)

    with db.connect() as conn:
        meta = db.get_symbol_meta(conn, symbol) or {}

        icb_name3 = meta.get("icb_name3")
        if mode == "industry":
            profile = industry_profile(icb_name3)
        else:
            profile = {t: list(TABLE_METRICS[t].keys()) for t in TABLE_METRICS.keys()}

        tables: Dict[str, Any] = {}
        effective_year: Optional[int] = None
        effective_quarter: Optional[int] = quarter

        for table, metric_ids in profile.items():
            if table not in TABLE_METRICS:
                continue
            row = db.get_latest_row(conn, table, symbol, metric_ids, year=year, quarter=quarter)
            if row is None:
                tables[table] = {"items": [], "row": None}
                continue

            effective_year = effective_year or row.year
            if quarter is None:
                effective_quarter = None
            items = [_metric_to_item(table, m, row.values.get(m)) for m in metric_ids if m in TABLE_METRICS[table]]

            tables[table] = {
                "row": {
                    "year": row.year,
                    "quarter": row.quarter,
                    "period": row.period,
                    "source": row.source,
                    "updated_at": row.updated_at,
                    "selected_row_id": row.selected_row_id,
                    "candidate_source": row.candidate_source,
                    "candidate_count": row.candidate_count,
                    "selection_reason": row.selection_reason,
                    "fallback_used": row.fallback_used,
                },
                "items": items,
            }

    return {
        "symbol": symbol,
        "meta": meta,
        "mode": mode,
        "requested": {"year": year, "quarter": quarter},
        "effective": {"year": effective_year, "quarter": effective_quarter},
        "tables": tables,
    }


@app.get("/api/taxonomy/groups")
def api_taxonomy_groups() -> Dict[str, Any]:
    return GROUPS


@app.get("/api/taxonomy/table/{table}")
def api_taxonomy_table(table: str) -> Dict[str, Any]:
    table = (table or "").strip()
    if table not in TABLE_METRICS:
        raise HTTPException(status_code=404, detail=f"Unknown table: {table}")
    metrics = []
    for metric in TABLE_METRICS[table].values():
        group = GROUPS.get(metric.group, {"label_vi": metric.group})
        metrics.append(
            {
                "id": metric.id,
                "label": metric.label,
                "group": metric.group,
                "group_label": group.get("label_vi", metric.group),
                "unit": metric.unit,
                "description": metric.description,
            }
        )
    return {"table": table, "metrics": metrics}


@app.get("/api/symbol/{symbol}/series")
def api_symbol_series(
    symbol: str,
    table: Annotated[
        Literal["financial_ratios", "balance_sheet", "income_statement", "cash_flow_statement"],
        Query(),
    ] = "financial_ratios",
    metrics: Annotated[str, Query(description="Comma-separated metric ids")] = "",
    period: Annotated[Literal["yearly", "quarterly"], Query()] = "yearly",
    year_from: Annotated[Optional[int], Query(ge=1990, le=2100)] = None,
    year_to: Annotated[Optional[int], Query(ge=1990, le=2100)] = None,
) -> Dict[str, Any]:
    symbol = _validate_symbol(symbol)
    metric_ids = [m.strip() for m in (metrics or "").split(",") if m.strip()]
    if not metric_ids:
        raise HTTPException(status_code=400, detail="metrics is required")

    unknown = [m for m in metric_ids if m not in TABLE_METRICS[table]]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown metrics for {table}: {', '.join(unknown)}")

    series: Dict[str, Any] = {}
    with db.connect() as conn:
        for m in metric_ids:
            series[m] = db.get_metric_series(conn, table, symbol, m, period=period, year_from=year_from, year_to=year_to)
    return {"symbol": symbol, "table": table, "period": period, "series": series}


@app.get("/api/symbol/{symbol}/price_series")
def api_symbol_price_series(
    symbol: str,
    days: Annotated[int, Query(ge=5, le=1000)] = 120,
) -> Dict[str, Any]:
    symbol = _validate_symbol(symbol)
    with db.connect() as conn:
        pts = db.get_price_series(conn, symbol, days=days)
    return {"symbol": symbol, "days": days, "series": pts}


@app.get("/api/industries/{industry_name}/companies")
def api_industry_companies(industry_name: str) -> List[Dict[str, Any]]:
    """Get companies in a specific industry"""
    # Decode URL-encoded industry name
    from urllib.parse import unquote
    industry_name = unquote(industry_name)

    with db.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ticker, icb_name3 as industry
                FROM stock_industry
                WHERE icb_name3 = %s
                ORDER BY ticker
                LIMIT 50
            """, (industry_name,))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "ticker": row["ticker"],
                    "name": "",
                    "industry": row["industry"] or ""
                })

    return results


@app.get("/api/financials/{symbol}/history")
def api_financial_history(
    symbol: str,
    metrics: Annotated[str, Query(description="Comma-separated metric ids")] = "roe,net_profit_margin,debt_to_equity",
    years: Annotated[int, Query(ge=1, le=10)] = 5
) -> Dict[str, Any]:
    """Get historical financial metrics for charts"""
    symbol = _validate_symbol(symbol)

    metric_ids = [m.strip() for m in (metrics or "").split(",") if m.strip()]
    if not metric_ids:
        metric_ids = ["roe", "net_profit_margin", "debt_to_equity"]

    import re
    from datetime import datetime

    with db.connect() as conn:
        with conn.cursor() as cursor:
            # Validate requested metric columns (avoid SQL injection via column names)
            cursor.execute("SELECT column_name AS name FROM information_schema.columns WHERE table_name = 'financial_ratios' AND table_schema = 'public'")
            ratio_columns = {row["name"] for row in cursor.fetchall()}
            safe_metric_ids: List[str] = []
            for m in metric_ids:
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", m or ""):
                    raise HTTPException(status_code=400, detail=f"Invalid metric id: {m!r}")
                if m not in ratio_columns:
                    raise HTTPException(status_code=400, detail=f"Metric '{m}' not found in financial_ratios")
                safe_metric_ids.append(m)
            metric_ids = safe_metric_ids

            # Get the latest available year in the database
            cursor.execute("SELECT MAX(year) FROM financial_ratios WHERE quarter IS NULL")
            result = cursor.fetchone()
            max_db_year = result[0] if result and result[0] else datetime.now().year
            current_year = min(datetime.now().year, max_db_year)
            year_from = current_year - years + 1

            result = {"symbol": symbol, "years": [], "metrics": {}}

            # Get years available
            cursor.execute("""
                SELECT DISTINCT year FROM financial_ratios
                WHERE symbol = %s AND quarter IS NULL AND year >= %s
                ORDER BY year
            """, (symbol, year_from))

            result["years"] = [row["year"] for row in cursor.fetchall()]

            # Get each metric
            for metric in metric_ids:
                cursor.execute("""
                    SELECT year, {} as value
                    FROM financial_ratios
                    WHERE symbol = %s AND quarter IS NULL AND year >= %s
                    ORDER BY year
                """.format(metric), (symbol, year_from))

                # Keep year alignment, but null-out invalid valuation metrics (<= 0)
                out: List[Dict[str, Any]] = []
                for row in cursor.fetchall():
                    v = row["value"]
                    if metric in {"price_to_earnings", "price_to_book", "ev_to_ebitda"}:
                        try:
                            v_f = float(v) if v is not None else None
                        except (TypeError, ValueError):
                            v_f = None
                        if v_f is None or v_f <= 0:
                            v = None
                    out.append({"year": row["year"], "value": v})
                result["metrics"][metric] = out

    return result


@app.get("/api/financials/{symbol}/history/benchmark")
def api_financial_history_benchmark(
    symbol: str,
    metrics: Annotated[str, Query(description="Comma-separated metric ids")] = "roe,net_profit_margin,debt_to_equity",
    years: Annotated[int, Query(ge=1, le=10)] = 5
) -> Dict[str, Any]:
    """
    Get historical industry benchmark data for trend charts.

    Returns industry median values for each requested metric over multiple years,
    allowing trend charts to show benchmark evolution instead of a flat line.

    Returns:
        - symbol: Company ticker
        - industry: Industry name
        - years: List of years in the historical period
        - benchmarks: Object with metric names as keys, each containing
                     an array of {year, median} objects
    """
    import re
    from datetime import datetime

    symbol = _validate_symbol(symbol)

    with db.connect() as conn:
        with conn.cursor() as cursor:
            # Validate requested metric columns (avoid SQL injection via column names)
            cursor.execute("SELECT column_name AS name FROM information_schema.columns WHERE table_name = 'financial_ratios' AND table_schema = 'public'")
            ratio_columns = {row["name"] for row in cursor.fetchall()}

            # Get company industry
            cursor.execute("""
                SELECT ticker, icb_name3, icb_code3
                FROM stock_industry
                WHERE ticker = %s
            """, (symbol,))
            company_meta = cursor.fetchone()

            if not company_meta or not company_meta["icb_name3"]:
                raise HTTPException(status_code=404, detail=f"Symbol or industry not found: {symbol}")

            industry = company_meta["icb_name3"]

            # Parse metrics
            metric_ids = [m.strip() for m in (metrics or "").split(",") if m.strip()]
            if not metric_ids:
                metric_ids = ["roe", "net_profit_margin", "debt_to_equity"]

            safe_metric_ids: List[str] = []
            for m in metric_ids:
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", m or ""):
                    raise HTTPException(status_code=400, detail=f"Invalid metric id: {m!r}")
                if m not in ratio_columns:
                    raise HTTPException(status_code=400, detail=f"Metric '{m}' not found in financial_ratios")
                safe_metric_ids.append(m)
            metric_ids = safe_metric_ids

            # Determine year range - use DB max year instead of current year
            cursor.execute("SELECT MAX(year) FROM financial_ratios WHERE quarter IS NULL")
            result = cursor.fetchone()
            max_db_year = result[0] if result and result[0] else datetime.now().year
            current_year = min(datetime.now().year, max_db_year)
            year_from = current_year - years + 1

            result = {
                "symbol": symbol,
                "industry": industry,
                "period_type": "ANNUAL",
                "as_of_period": None,
                "years": [],
                "benchmarks": {}
            }

            # Get available years
            cursor.execute("""
                SELECT DISTINCT year FROM financial_ratios
                WHERE symbol = %s AND quarter IS NULL AND year >= %s
                ORDER BY year
            """, (symbol, year_from))

            available_years = [row["year"] for row in cursor.fetchall()]
            result["years"] = available_years

            # For each metric, calculate industry median per year
            for metric in metric_ids:
                benchmark_data = []

                for year in available_years:
                    # Get industry median for this metric and year
                    # For valuation metrics, filter positive values only
                    valuation_metrics = ["price_to_earnings", "price_to_book", "ev_to_ebitda"]

                    if metric in valuation_metrics:
                        if metric == "price_to_earnings":
                            extra = "AND f.eps_vnd IS NOT NULL AND f.eps_vnd > 0"
                        elif metric == "price_to_book":
                            extra = "AND f.bvps_vnd IS NOT NULL AND f.bvps_vnd > 0"
                        else:
                            extra = ""
                        cursor.execute(
                            f"""
                            SELECT f.{metric} as value
                            FROM financial_ratios f
                            JOIN stock_industry s ON f.symbol = s.ticker
                            WHERE s.icb_name3 = %s
                              AND f.year = %s
                              AND f.quarter IS NULL
                              AND f.{metric} IS NOT NULL
                              AND f.{metric} > 0
                              {extra}
                            """,
                            (industry, year),
                        )
                    else:
                        cursor.execute(f"""
                            SELECT f.{metric} as value
                            FROM financial_ratios f
                            JOIN stock_industry s ON f.symbol = s.ticker
                            WHERE s.icb_name3 = %s
                              AND f.year = %s
                              AND f.quarter IS NULL
                              AND f.{metric} IS NOT NULL
                        """, (industry, year))

                    peer_values = [row["value"] for row in cursor.fetchall()]

                    if peer_values:
                        median_val = _calculate_percentile_value(peer_values, 50)
                        benchmark_data.append({
                            "year": year,
                            "median": round(median_val, 4) if median_val is not None else None,
                            "peer_count": len(peer_values)
                        })
                    else:
                        # No peers for this year
                        benchmark_data.append({
                            "year": year,
                            "median": None,
                            "peer_count": 0
                        })

                result["benchmarks"][metric] = benchmark_data

    return result


@app.get("/api/financials/{symbol}/series/{table}/{metric}")
def api_metric_series(
    symbol: str,
    table: str,
    metric: str,
    period: Annotated[str, Query(description="year or quarter")] = "year",
    count: Annotated[int, Query(ge=1, le=20, description="Number of periods")] = 5
) -> Dict[str, Any]:
    """Get time series for a single metric - supports yearly and quarterly"""
    symbol = _validate_symbol(symbol)

    valid_tables = ["financial_ratios", "balance_sheet", "income_statement", "cash_flow_statement"]
    if table not in valid_tables:
        raise HTTPException(status_code=400, detail=f"Invalid table. Must be one of: {valid_tables}")

    with db.connect() as conn:
        with conn.cursor() as cursor:
            # Check if column exists
            cursor.execute(f"SELECT column_name AS name FROM information_schema.columns WHERE table_name = '{table}' AND table_schema = 'public'")
            columns = [row["name"] for row in cursor.fetchall()]
            if metric not in columns:
                raise HTTPException(status_code=400, detail=f"Metric '{metric}' not found in {table}")

            result = {
                "symbol": symbol,
                "table": table,
                "metric": metric,
                "period": period,
                "period_type": "QUARTER" if period == "quarter" else "ANNUAL",
                "data": []
            }

            if period == "quarter":
                # Get quarterly data
                cursor.execute(f"""
                    SELECT year, quarter, {metric} as value
                    FROM {table}
                    WHERE symbol = %s AND quarter IS NOT NULL AND quarter BETWEEN 1 AND 4
                    ORDER BY year DESC, quarter DESC
                    LIMIT %s
                """, (symbol, count))

                rows = cursor.fetchall()
                # Reverse to show oldest first
                rows = list(reversed(rows))

                for row in rows:
                    result["data"].append({
                        "period": f"Q{row['quarter']} {row['year']}",
                        "year": row["year"],
                        "quarter": row["quarter"],
                        "period_type": "QUARTER",
                        "as_of_period": f"Q{row['quarter']} {row['year']}",
                        "value": row["value"]
                    })
                result["labels"] = [d["period"] for d in result["data"]]
            else:
                # Get yearly data (statement tables require deterministic annual selection)
                points = db.get_metric_series(conn, table, symbol, metric, period="yearly")
                points = points[-count:] if count is not None else points
                for pt in points:
                    y = pt.get("year")
                    result["data"].append({
                        "period": f"FY {y}",
                        "year": y,
                        "period_type": "ANNUAL",
                        "as_of_period": f"FY {y}",
                        "value": pt.get("value")
                    })
                result["labels"] = [d["period"] for d in result["data"]]

    return result


# ============================================================================
# INTELLIGENT ANALYSIS API
# ============================================================================

@app.get("/api/analysis/supported-industries")
def api_supported_industries_for_analysis() -> Dict[str, Any]:
    """Get list of supported industries for analysis."""
    from .analysis import get_supported_industries
    return {
        "industries": get_supported_industries()
    }


@app.get("/api/analysis/{symbol}")
def api_analysis(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None
) -> Dict[str, Any]:
    """
    Intelligent financial analysis - auto-detects industry and runs appropriate analysis.

    Returns:
        - Industry detection result
        - Core analysis (always): Piotroski F-Score, Altman Z-Score, Health Score, etc.
        - Industry-specific analysis based on detected industry
    """
    from .analysis import (
        detect_industry,
        get_industry_display_name,
        run_industry_analysis,
        analyze_core_financials,
    )

    symbol = _validate_symbol(symbol)

    with db.connect() as conn:
        with conn.cursor() as cursor:
            # Get company metadata for industry detection
            cursor.execute("""
                SELECT ticker, icb_name3, icb_code3
                FROM stock_industry
                WHERE ticker = %s
            """, (symbol,))
            meta_row = cursor.fetchone()
        icb_name = meta_row["icb_name3"] if meta_row else None

        # Detect industry
        industry_type = detect_industry(icb_name=icb_name, ticker=symbol)
        industry_display = get_industry_display_name(industry_type)

        # Get financial data (current year)
        effective_year = int(year) if year is not None else get_latest_year(conn, symbol)

        if effective_year is None:
            return {
                "symbol": symbol,
                "year": year,
                "industry": {
                    "type": industry_type,
                    "display_name": industry_display,
                    "icb_name": icb_name,
                },
                "analysis": {"error": "No annual data available"},
            }

        # Financial ratios are clean 1-row-per-year; statements require annual selection due to duplicated quarter=NULL rows.
        ratios_row = get_financial_ratios_annual(conn, symbol, effective_year)
        income_row, income_sel = select_income_statement_annual_with_provenance(conn, symbol, effective_year)
        balance_row, balance_sel = select_balance_sheet_annual_with_provenance(
            conn, symbol, effective_year, financial_ratios_row=ratios_row
        )
        cashflow_row, cashflow_sel = select_cash_flow_annual_with_provenance(
            conn, symbol, effective_year, balance_sheet_row=balance_row
        )

        # Fetch previous-year snapshots for YoY metrics (Piotroski, etc.)
        prev_ratios_row = None
        prev_balance_row = None
        prev_income_row = None
        prev_cashflow_row = None
        prev_year = get_previous_year(conn, symbol, effective_year)
        prev_income_sel: Optional[Dict[str, Any]] = None
        prev_balance_sel: Optional[Dict[str, Any]] = None
        prev_cashflow_sel: Optional[Dict[str, Any]] = None
        if prev_year is not None:
            prev_ratios_row = get_financial_ratios_annual(conn, symbol, prev_year)
            prev_income_row, prev_income_sel = select_income_statement_annual_with_provenance(conn, symbol, prev_year)
            prev_balance_row, prev_balance_sel = select_balance_sheet_annual_with_provenance(
                conn, symbol, prev_year, financial_ratios_row=prev_ratios_row
            )
            prev_cashflow_row, prev_cashflow_sel = select_cash_flow_annual_with_provenance(
                conn, symbol, prev_year, balance_sheet_row=prev_balance_row
            )

    # Convert to dicts
    financial_ratios = dict(ratios_row) if ratios_row else {}
    balance_sheet = dict(balance_row) if balance_row else {}
    income_statement = dict(income_row) if income_row else {}
    cash_flow = dict(cashflow_row) if cashflow_row else {}
    prev_financial_ratios = dict(prev_ratios_row) if prev_ratios_row else {}
    prev_balance_sheet = dict(prev_balance_row) if prev_balance_row else {}
    prev_income_statement = dict(prev_income_row) if prev_income_row else {}
    prev_cash_flow = dict(prev_cashflow_row) if prev_cashflow_row else {}

    # Determine effective year
    effective_year = financial_ratios.get("year") or balance_sheet.get("year") or income_statement.get("year")

    # Run core analysis (always) + industry-specific analysis (nested)
    market_cap = None
    try:
        mc_b = financial_ratios.get("market_cap_billions")
        if mc_b is not None:
            mc_raw = float(mc_b)
            # Despite the column name, DB may store either:
            # - billions VND (e.g., 164047) OR
            # - raw VND (e.g., 164047735752300)
            market_cap = mc_raw * 1_000_000_000 if mc_raw < 1_000_000_000 else mc_raw
    except (TypeError, ValueError):
        market_cap = None

    core_report = analyze_core_financials(
        financial_ratios=financial_ratios,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cash_flow=cash_flow,
        market_cap=market_cap,
        previous_balance_sheet=prev_balance_sheet,
        previous_income_statement=prev_income_statement,
        previous_cash_flow=prev_cash_flow,
        previous_financial_ratios=prev_financial_ratios,
    )

    try:
        industry_report = run_industry_analysis(
            industry_type=industry_type,
            financial_ratios=financial_ratios,
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            cash_flow=cash_flow,
        )
    except Exception as e:
        industry_report = {"error": str(e), "metrics": {}, "scores": {}}

    analysis_result = {
        **core_report,
        "industry_analysis": industry_report,
    }

    return {
        "symbol": symbol,
        "year": effective_year,
        "period_type": "ANNUAL",
        "as_of_period": f"FY {effective_year}" if effective_year is not None else None,
        "provenance": {
            "annual_selection": {
                "year": effective_year,
                "income_statement": income_sel,
                "balance_sheet": balance_sel,
                "cash_flow_statement": cashflow_sel,
                "previous_year": prev_year,
                "income_statement_prev": prev_income_sel,
                "balance_sheet_prev": prev_balance_sel,
                "cash_flow_statement_prev": prev_cashflow_sel,
            }
        },
        "industry": {
            "type": industry_type,
            "display_name": industry_display,
            "icb_name": icb_name,
        },
        "analysis": analysis_result,
    }


@app.get("/api/industry/benchmark/{symbol}")
def api_industry_benchmark(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None,
    multi_year: Annotated[Optional[int], Query(ge=1, le=5, description="Number of years for median (1-5)")] = None
) -> Dict[str, Any]:
    """
    Get industry benchmark comparisons for a company.

    Calculates industry statistics (median, p25, p75) for key financial metrics
    and compares the company against its industry peers with actual percentile rankings.

    Args:
        symbol: Company ticker
        year: Year of analysis (defaults to latest available)
        multi_year: If specified, calculates median over this many years (1-5)

    Returns:
        - symbol: Company ticker
        - industry: Industry name
        - year: Year of analysis
        - peer_count: Number of companies in comparison
        - statistics: Industry statistics (median, p25, p75) for each metric
        - company_vs_industry: Detailed comparison with actual percentile rank
        - validity_rules_applied: Whether validity filtering was applied
        - excluded_count: Number of peers excluded per metric
        - exclusion_reasons: Reasons for exclusion per metric
    """
    symbol = _validate_symbol(symbol)

    with db.connect() as conn:
        with conn.cursor() as cursor:
            # Get company industry
            cursor.execute("""
                SELECT ticker, icb_name3, icb_code3
                FROM stock_industry
                WHERE ticker = %s
            """, (symbol,))
            company_meta = cursor.fetchone()

            if not company_meta or not company_meta["icb_name3"]:
                raise HTTPException(status_code=404, detail=f"Symbol or industry not found: {symbol}")

            industry = company_meta["icb_name3"]
            icb_code = company_meta["icb_code3"] if "icb_code3" in company_meta.keys() else ""
            icb_code = icb_code or ""

            # Define key metrics to benchmark with validity rules
            # Note: Some metrics require underlying data to be valid (positive)
            # P/E: Only valid when EPS > 0 (exclude negative earnings)
            # P/B: Only valid when Equity > 0 (exclude negative equity)
            # D/E: Only valid when Equity > 0 (avoid division by zero/negative)
            valuation_metrics = ["price_to_earnings", "price_to_book", "ev_to_ebitda"]
            other_metrics = [
                "roe", "roa", "net_profit_margin", "gross_margin",
                "debt_to_equity", "current_ratio",
                "asset_turnover", "inventory_turnover"
            ]
            metrics = valuation_metrics + other_metrics

            # Validity filters (academic rules) - enforced on financial_ratios to avoid statement-table
            # duplication issues (many rows per year with quarter IS NULL) and because income_statement.eps
            # is NULL in this DB.
            #
            # Each entry: metric -> (extra_sql_conditions, exclusion_reason)
            validity_filters = {
                # P/E only meaningful when EPS > 0
                "price_to_earnings": ("AND f.price_to_earnings > 0 AND f.eps_vnd IS NOT NULL AND f.eps_vnd > 0",
                                      "Loại bỏ EPS <= 0 hoặc thiếu EPS"),
                # P/B only meaningful when book value per share > 0 (proxy for equity > 0)
                "price_to_book": ("AND f.price_to_book > 0 AND f.bvps_vnd IS NOT NULL AND f.bvps_vnd > 0",
                                  "Loại bỏ BVPS <= 0 hoặc thiếu BVPS"),
                # D/E only meaningful when equity > 0; approximate by requiring D/E > 0
                "debt_to_equity": ("AND f.debt_to_equity IS NOT NULL AND f.debt_to_equity > 0",
                                   "Loại bỏ D/E <= 0 hoặc thiếu dữ liệu"),
            }

            # Get year filter and multi-year mode
            year_filter = ""
            params = [industry]
            multi_year_mode = multi_year is not None and multi_year > 1

            # NOTE: Multi-year benchmark methodology limitation
            # When multi_year is specified, the current implementation pools values from multiple
            # years together (one company appears multiple times in the pool). This is NOT the
            # correct methodology.
            #
            # Correct approach: First calculate median per company over the multi-year period,
            # THEN calculate industry median from those company medians.
            #
            # This would require a more complex query:
            # 1. Create a CTE that calculates per-company medians over the year range
            # 2. Then calculate industry median from those company-level medians
            #
            # For now, this is a known limitation that should be addressed in a future update.

            if year:
                if multi_year_mode:
                    # Include multiple years ending at the specified year
                    # WARNING: This pools values from multiple years, not company medians
                    year_from = year - multi_year + 1
                    year_filter = f"AND f.year >= {year_from} AND f.year <= {year}"
                else:
                    # Single year mode
                    year_filter = "AND f.year = %s"
                    params.append(year)
            else:
                # Use latest year available for THIS symbol (avoid global max-year 404)
                cursor.execute(
                    """
                    SELECT MAX(year) AS latest_year
                    FROM financial_ratios
                    WHERE symbol = %s AND quarter IS NULL
                    """,
                    (symbol,),
                )
                latest_year_row = cursor.fetchone()
                year = latest_year_row["latest_year"] if latest_year_row else None

                if year:
                    if multi_year_mode:
                        year_from = year - multi_year + 1
                        year_filter = f"AND f.year >= {year_from} AND f.year <= {year}"
                    else:
                        year_filter = "AND f.year = %s"
                        params.append(year)

            # Get company's metrics
            year_filter_plain = f"AND year = {year}" if year else ""
            cursor.execute("""
                SELECT {metrics}
                FROM financial_ratios
                WHERE symbol = %s AND quarter IS NULL {year_filter_plain}
            """.format(metrics=", ".join(metrics), year_filter_plain=year_filter_plain),
            [symbol])

            company_row = cursor.fetchone()

            if not company_row:
                raise HTTPException(status_code=404, detail=f"No financial data found for {symbol}")

            # Get all peer values for percentile calculation
            # For valuation metrics, filter out NULL, 0, and negative values
            # Apply validity rules within financial_ratios (avoid statement-table duplicates).
            peer_data = {}
            excluded_count = {}
            exclusion_reasons = {}

            for metric in metrics:
                # Total peer rows in the comparison scope (industry + year filter)
                cursor.execute(
                    f"""
                    SELECT COUNT(*) as total
                    FROM financial_ratios f
                    JOIN stock_industry s ON f.symbol = s.ticker
                    WHERE s.icb_name3 = %s
                      AND f.quarter IS NULL
                      {year_filter}
                    """,
                    params,
                )
                total_row = cursor.fetchone()
                total_rows = int(total_row["total"]) if total_row and total_row["total"] is not None else 0

                extra_sql, reason = validity_filters.get(metric, ("", None))

                metric_conditions = f"AND f.{metric} IS NOT NULL"
                if metric in valuation_metrics:
                    metric_conditions += f" AND f.{metric} > 0"
                if extra_sql:
                    metric_conditions += f" {extra_sql}"

                cursor.execute(
                    f"""
                    SELECT f.{metric} as value
                    FROM financial_ratios f
                    JOIN stock_industry s ON f.symbol = s.ticker
                    WHERE s.icb_name3 = %s
                      AND f.quarter IS NULL
                      {metric_conditions}
                      {year_filter}
                    """,
                    params,
                )
                values = [row["value"] for row in cursor.fetchall() if row["value"] is not None]

                peer_data[metric] = values
                excluded_count[metric] = max(0, total_rows - len(values))

                if reason:
                    exclusion_reasons[metric] = reason
                elif metric in valuation_metrics:
                    exclusion_reasons[metric] = "Loại bỏ giá trị <= 0 hoặc thiếu dữ liệu"
                else:
                    exclusion_reasons[metric] = "Thiếu dữ liệu"

    # Calculate peer count (use the metric with most data points)
    peer_count = max([len(v) for v in peer_data.values()]) if peer_data else 0

    if peer_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No industry peers found for {symbol} in industry: {industry}"
        )

    # Calculate statistics for each metric
    statistics = {}
    for metric in metrics:
        peer_values = peer_data.get(metric, [])

        if not peer_values:
            statistics[metric] = {
                "median": None,
                "p25": None,
                "p75": None,
                "peer_count": 0
            }
            continue

        # Calculate percentiles using numpy-style linear interpolation
        median_val = _calculate_percentile_value(peer_values, 50)
        p25_val = _calculate_percentile_value(peer_values, 25)
        p75_val = _calculate_percentile_value(peer_values, 75)

        statistics[metric] = {
            "median": round(median_val, 4) if median_val is not None else None,
            "p25": round(p25_val, 4) if p25_val is not None else None,
            "p75": round(p75_val, 4) if p75_val is not None else None,
            "peer_count": len(peer_values)
        }

    # Calculate company percentile and build comparison
    company_vs_industry = {}
    for metric in metrics:
        company_value = company_row[metric]
        peer_values = peer_data.get(metric, [])

        if company_value is None or not peer_values:
            company_vs_industry[metric] = {
                "company": None,
                "median": statistics[metric]["median"],
                "p25": statistics[metric]["p25"],
                "p75": statistics[metric]["p75"],
                "percentile": None,
                "peer_count": statistics[metric]["peer_count"],
                "excluded_count": excluded_count.get(metric, 0),
                "exclusion_reason": exclusion_reasons.get(metric)
            }
            continue

        # Calculate actual percentile rank of the company
        percentile = _calculate_percentile_rank(company_value, peer_values)

        company_vs_industry[metric] = {
            "company": round(company_value, 4),
            "median": statistics[metric]["median"],
            "p25": statistics[metric]["p25"],
            "p75": statistics[metric]["p75"],
            "percentile": percentile,
            "peer_count": statistics[metric]["peer_count"],
            "excluded_count": excluded_count.get(metric, 0),
            "exclusion_reason": exclusion_reasons.get(metric)
        }

    return {
        "symbol": symbol,
        "industry": industry,
        "icb_code": icb_code,
        "year": year,
        "multi_year": multi_year,
        "period_type": "ANNUAL",
        "as_of_period": f"FY {year}" if year is not None else None,
        "peer_count": peer_count,
        "statistics": statistics,
        "company_vs_industry": company_vs_industry,
        "validity_rules_applied": True,
        "excluded_count": excluded_count,
        "exclusion_reasons": exclusion_reasons
    }


def _calculate_percentile_rank(value: float, peer_values: List[float]) -> Optional[float]:
    """
    Calculate the actual percentile rank (0-100) of a value within a list of peer values.

    This calculates what percentile the company's value falls at within the peer distribution.
    For example, if a company's P/E is at the 75th percentile, it means 75% of peers
    have a lower P/E ratio.

    Uses numpy-style percentile calculation with linear interpolation.

    Args:
        value: The company's value
        peer_values: List of peer values to compare against

    Returns:
        Percentile rank from 0-100, or None if insufficient data
    """
    if not peer_values:
        return None

    valid_peers = [v for v in peer_values if v is not None]
    if not valid_peers:
        return None

    n = len(valid_peers)

    # Sort the peer values
    sorted_peers = sorted(valid_peers)

    # Count peers strictly less than the value
    less_than_count = sum(1 for v in sorted_peers if v < value)

    # Count peers equal to the value
    equal_count = sum(1 for v in sorted_peers if v == value)

    # Calculate percentile using the standard method
    # Percentile = (number of values below + 0.5 * number of values equal) / total * 100
    if equal_count > 0:
        # For values that appear multiple times, use midpoint
        percentile = ((less_than_count + 0.5 * equal_count) / n) * 100
    else:
        # For unique values, use linear interpolation
        percentile = (less_than_count / n) * 100

    return round(percentile, 1)


def _calculate_percentile_value(peer_values: List[float], percentile: float) -> Optional[float]:
    """
    Calculate the value at a given percentile in a list of values.

    Uses numpy-style linear interpolation method (type 7 in numpy.percentile).

    Args:
        peer_values: List of peer values
        percentile: Percentile to calculate (0-100)

    Returns:
        Value at the given percentile, or None if insufficient data
    """
    if not peer_values:
        return None

    valid_values = [v for v in peer_values if v is not None]
    if not valid_values:
        return None

    n = len(valid_values)
    if n == 1:
        return valid_values[0]

    # Sort the values
    sorted_values = sorted(valid_values)

    # Calculate the index using numpy's method (linear interpolation)
    # index = (percentile / 100) * (n - 1)
    index = (percentile / 100.0) * (n - 1)

    # Get the integer and fractional parts
    lower_index = int(index)
    upper_index = min(lower_index + 1, n - 1)
    fraction = index - lower_index

    # Linear interpolation
    if lower_index == upper_index:
        return sorted_values[lower_index]
    else:
        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]
        return lower_value + fraction * (upper_value - lower_value)


def _calculate_median(values: List[float]) -> Optional[float]:
    """
    Calculate median of a list of values.
    """
    if not values:
        return None

    sorted_values = sorted(values)
    n = len(sorted_values)

    if n % 2 == 1:
        return sorted_values[n // 2]
    else:
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2


def _filter_outliers(values: List[float], lower_pct: float = 5, upper_pct: float = 95) -> List[float]:
    """
    Filter outliers by removing values outside the given percentiles.

    Args:
        values: List of values
        lower_pct: Lower percentile threshold (default 5%)
        upper_pct: Upper percentile threshold (default 95%)

    Returns:
        Filtered values within the percentile range
    """
    if not values or len(values) < 5:
        return values

    sorted_values = sorted(values)
    n = len(sorted_values)

    lower_idx = int(n * lower_pct / 100)
    upper_idx = int(n * upper_pct / 100)

    # Ensure at least some values remain
    lower_idx = max(0, lower_idx)
    upper_idx = min(n - 1, upper_idx)

    return sorted_values[lower_idx:upper_idx + 1]


@app.get("/api/research/peers/scatter/{symbol}")
def api_research_peer_scatter(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None,
    x: Annotated[str, Query(max_length=64)] = "price_to_earnings",
    y: Annotated[str, Query(max_length=64)] = "roe",
) -> Dict[str, Any]:
    """
    Research-grade peer scatter for a given industry/year (P2 visualization support).

    Notes (data limits):
      - Uses `financial_ratios` annual rows (quarter IS NULL).
      - Validity rules are applied (e.g., valuation multiples must be > 0).
    """
    from datetime import datetime

    symbol = _validate_symbol(symbol)

    # Allow-list to prevent SQL injection via column names
    allowed_metrics = {
        "price_to_earnings",
        "price_to_book",
        "ev_to_ebitda",
        "roe",
        "roa",
        "net_profit_margin",
        "debt_to_equity",
        "current_ratio",
        "asset_turnover",
    }
    x = (x or "").strip()
    y = (y or "").strip()
    if x not in allowed_metrics or y not in allowed_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metrics. Allowed: {sorted(allowed_metrics)}")

    positive_only = {"price_to_earnings", "price_to_book", "ev_to_ebitda", "debt_to_equity", "current_ratio", "asset_turnover"}

    with db.connect() as conn:
        with conn.cursor() as cursor:
            # Determine year default from DB
            if year is None:
                cursor.execute(
                    """
                    SELECT MAX(year) AS y
                    FROM financial_ratios
                    WHERE symbol = %s AND quarter IS NULL
                    """,
                    (symbol,),
                )
                yr = cursor.fetchone()
                year = int(yr["y"]) if yr and yr["y"] else None

            if year is None:
                cursor.execute("SELECT MAX(year) AS y FROM financial_ratios WHERE quarter IS NULL")
                yr = cursor.fetchone()
                year = int(yr["y"]) if yr and yr["y"] else datetime.now().year

            # Get industry for symbol
            cursor.execute(
                """
                SELECT icb_name3 AS industry
                FROM stock_industry
                WHERE ticker = %s
                """,
                (symbol,),
            )
            row = cursor.fetchone()
            if not row or not row["industry"]:
                raise HTTPException(status_code=404, detail=f"Industry not found for symbol: {symbol}")
            industry = str(row["industry"])

            # Metric metadata (labels/units) from taxonomy if available
            def _metric_meta(metric_id: str) -> Dict[str, Any]:
                try:
                    m = TABLE_METRICS.get("financial_ratios", {}).get(metric_id)
                    if m:
                        return {"id": metric_id, "label": m.label, "unit": m.unit, "description": m.description}
                except Exception:
                    pass
                return {"id": metric_id, "label": metric_id, "unit": None, "description": None}

            # Peer universe: same ICB level-3 industry in the given year
            sql = f"""
                SELECT f.symbol AS symbol, f.{x} AS x, f.{y} AS y
                FROM financial_ratios f
                JOIN stock_industry si
                  ON si.ticker = f.symbol
                WHERE si.icb_name3 = %s
                  AND f.year = %s
                  AND f.quarter IS NULL
            """
            cursor.execute(sql, (industry, int(year)))
            raw = cursor.fetchall()

    points: List[Dict[str, Any]] = []
    excluded = 0
    for r in raw:
        xv = r["x"]
        yv = r["y"]
        try:
            xv_f = float(xv) if xv is not None else None
            yv_f = float(yv) if yv is not None else None
        except (TypeError, ValueError):
            excluded += 1
            continue

        if xv_f is None or yv_f is None:
            excluded += 1
            continue
        if x in positive_only and xv_f <= 0:
            excluded += 1
            continue
        if y in positive_only and yv_f <= 0:
            excluded += 1
            continue

        points.append(
            {
                "symbol": str(r["symbol"]),
                "x": xv_f,
                "y": yv_f,
                "is_target": str(r["symbol"]).upper() == symbol,
            }
        )

    # Cap payload (UI purposes)
    max_points = 900
    if len(points) > max_points:
        points = points[:max_points]

    return {
        "symbol": symbol,
        "year": int(year),
        "industry": industry,
        "x": _metric_meta(x),
        "y": _metric_meta(y),
        "peer_count_raw": len(raw),
        "peer_count_valid": len(points),
        "excluded": excluded + max(0, len(raw) - excluded - len(points)),
        "points": points,
    }


@app.get("/api/research/peers/distribution/{symbol}")
def api_research_peer_distribution(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None,
    metric: Annotated[str, Query(max_length=64)] = "price_to_earnings",
    bins: Annotated[int, Query(ge=8, le=60)] = 24,
) -> Dict[str, Any]:
    """
    Research-grade peer distribution (histogram + percentiles) for one metric.

    Notes:
      - Annual `financial_ratios` only (quarter IS NULL).
      - Validity rules:
          * valuation multiples must be > 0
          * P/E requires EPS > 0, P/B requires BVPS > 0
      - Histogram domain is trimmed to [P5, P95] when possible.
    """
    from datetime import datetime

    symbol = _validate_symbol(symbol)
    metric = (metric or "").strip()

    allowed_metrics = {
        "price_to_earnings",
        "price_to_book",
        "ev_to_ebitda",
        "roe",
        "roa",
        "net_profit_margin",
        "debt_to_equity",
        "current_ratio",
        "asset_turnover",
    }
    if metric not in allowed_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Allowed: {sorted(allowed_metrics)}")

    positive_only = {"price_to_earnings", "price_to_book", "ev_to_ebitda", "debt_to_equity", "current_ratio", "asset_turnover"}

    with db.connect() as conn:
        with conn.cursor() as cursor:
            # Determine year default from DB
            if year is None:
                cursor.execute(
                    """
                    SELECT MAX(year) AS y
                    FROM financial_ratios
                    WHERE symbol = %s AND quarter IS NULL
                    """,
                    (symbol,),
                )
                yr = cursor.fetchone()
                year = int(yr["y"]) if yr and yr["y"] else None

            if year is None:
                cursor.execute("SELECT MAX(year) AS y FROM financial_ratios WHERE quarter IS NULL")
                yr = cursor.fetchone()
                year = int(yr["y"]) if yr and yr["y"] else datetime.now().year

            # Industry for symbol
            cursor.execute(
                """
                SELECT icb_name3 AS industry
                FROM stock_industry
                WHERE ticker = %s
                """,
                (symbol,),
            )
            row = cursor.fetchone()
            if not row or not row["industry"]:
                raise HTTPException(status_code=404, detail=f"Industry not found for symbol: {symbol}")
            industry = str(row["industry"])

            def _metric_meta(metric_id: str) -> Dict[str, Any]:
                try:
                    m = TABLE_METRICS.get("financial_ratios", {}).get(metric_id)
                    if m:
                        return {"id": metric_id, "label": m.label, "unit": m.unit, "description": m.description}
                except Exception:
                    pass
                return {"id": metric_id, "label": metric_id, "unit": None, "description": None}

            # Pull peers
            # Include EPS/BVPS for validity filters on valuation metrics.
            cursor.execute(
                f"""
                SELECT
                    f.symbol AS symbol,
                    f.{metric} AS v,
                    f.eps_vnd AS eps_vnd,
                    f.bvps_vnd AS bvps_vnd
                FROM financial_ratios f
                JOIN stock_industry si
                  ON si.ticker = f.symbol
                WHERE si.icb_name3 = %s
                  AND f.year = %s
                  AND f.quarter IS NULL
                """,
                (industry, int(year)),
            )
            raw = cursor.fetchall()

            values: List[float] = []
            excluded = 0
            company_value = None

            for r in raw:
                v = r["v"]
                sym = str(r["symbol"]).upper() if r["symbol"] is not None else ""
                try:
                    v_f = float(v) if v is not None else None
                except (TypeError, ValueError):
                    excluded += 1
                    continue

                if v_f is None:
                    excluded += 1
                    continue
                if metric in positive_only and v_f <= 0:
                    excluded += 1
                    continue

                if metric == "price_to_earnings":
                    try:
                        eps = float(r["eps_vnd"]) if r["eps_vnd"] is not None else None
                    except (TypeError, ValueError):
                        eps = None
                    if eps is None or eps <= 0:
                        excluded += 1
                        continue

                if metric == "price_to_book":
                    try:
                        bvps = float(r["bvps_vnd"]) if r["bvps_vnd"] is not None else None
                    except (TypeError, ValueError):
                        bvps = None
                    if bvps is None or bvps <= 0:
                        excluded += 1
                        continue

                values.append(v_f)
                if sym == symbol:
                    company_value = v_f

            if not values:
                return {
                    "symbol": symbol,
                    "year": int(year),
                    "industry": industry,
                    "metric": _metric_meta(metric),
                    "peer_count_raw": len(raw),
                    "peer_count_valid": 0,
                    "excluded": len(raw),
                    "company_value": company_value,
                    "histogram": {"bins": []},
                    "percentiles": {"p5": None, "p25": None, "p50": None, "p75": None, "p95": None},
                    "notes": ["No valid peer values after filters."],
                }

            pct = {
                "p5": _calculate_percentile_value(values, 5),
                "p25": _calculate_percentile_value(values, 25),
                "p50": _calculate_percentile_value(values, 50),
                "p75": _calculate_percentile_value(values, 75),
                "p95": _calculate_percentile_value(values, 95),
            }

            # Histogram domain: trimmed to [p5, p95] when possible.
            domain_min = min(values)
            domain_max = max(values)
            if pct["p5"] is not None and pct["p95"] is not None and pct["p95"] > pct["p5"]:
                domain_min = float(pct["p5"])
                domain_max = float(pct["p95"])

            # Safety: if domain collapses, widen slightly.
            if domain_max <= domain_min:
                domain_min = min(values)
                domain_max = max(values)
            if domain_max <= domain_min:
                domain_max = domain_min + 1.0

            bins = int(bins)
            width = (domain_max - domain_min) / float(bins)
            edges = [domain_min + i * width for i in range(bins + 1)]
            counts = [0 for _ in range(bins)]

            for v in values:
                if v < domain_min or v > domain_max:
                    continue
                idx = int((v - domain_min) / width) if width > 0 else 0
                if idx == bins:
                    idx = bins - 1
                if 0 <= idx < bins:
                    counts[idx] += 1

            hist_bins = []
            for i in range(bins):
                low = edges[i]
                high = edges[i + 1]
                center = (low + high) / 2.0
                hist_bins.append(
                    {
                        "low": round(low, 4),
                        "high": round(high, 4),
                        "center": round(center, 4),
                        "count": int(counts[i]),
                    }
                )

            return {
                "symbol": symbol,
                "year": int(year),
                "industry": industry,
                "metric": _metric_meta(metric),
                "peer_count_raw": len(raw),
                "peer_count_valid": len(values),
                "excluded": excluded + max(0, len(raw) - excluded - len(values)),
                "company_value": company_value,
                "percentiles": {k: (round(float(v), 4) if v is not None else None) for k, v in pct.items()},
                "histogram": {
                    "bins": hist_bins,
                    "domain": {"min": round(domain_min, 4), "max": round(domain_max, 4)},
                },
                "notes": [
                    "Histogram domain is trimmed to [P5, P95] when possible.",
                    "Filters applied: valuation multiples must be > 0; P/E requires EPS>0; P/B requires BVPS>0.",
                ],
            }


@app.get("/api/valuation/{symbol}")
def api_valuation_analysis(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None
) -> Dict[str, Any]:
    """
    Get advanced valuation analysis for a company.

    Returns:
        - peg_ratio: PEG ratio analysis
        - pe_percentile: P/E historical percentile distribution
        - pb_percentile: P/B historical percentile distribution
        - valuation_summary: Industry comparison and overall assessment
    """
    from .analysis.valuation_analysis import analyze_valuation

    symbol = _validate_symbol(symbol)

    try:
        result = analyze_valuation(symbol=symbol, year=year)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Valuation analysis failed: {str(e)}")


@app.get("/api/research/valuation/timeseries/{symbol}")
def api_research_valuation_timeseries(
    symbol: str,
    years: Annotated[int, Query(ge=3, le=15)] = 10,
) -> Dict[str, Any]:
    """
    Research-grade valuation time series computed from year-end prices + FY EPS/BVPS.

    Motivations:
      - Avoid ambiguous stored multiples semantics by recomputing:
          P/E = year_end_close × 1000 / EPS
          P/B = year_end_close × 1000 / BVPS

    Data limits:
      - Prices are unadjusted for split/rights/bonus.
    """
    from .analysis.valuation_viz import get_valuation_timeseries

    symbol = _validate_symbol(symbol)

    return get_valuation_timeseries(symbol=symbol, years=years)


@app.get("/api/research/valuation/decomposition/{symbol}")
def api_research_valuation_decomposition(
    symbol: str,
    horizon_years: Annotated[int, Query(ge=2, le=10)] = 5,
) -> Dict[str, Any]:
    """
    Decompose cash-dividend-adjusted total return into:
      - EPS growth (log)
      - P/E re-rating (log)
      - Cash dividends (log)
    """
    from .analysis.valuation_viz import get_return_decomposition

    symbol = _validate_symbol(symbol)

    return get_return_decomposition(symbol=symbol, horizon_years=horizon_years)


@app.get("/api/dividend/{symbol}")
def api_dividend_analysis(symbol: str) -> Dict[str, Any]:
    """
    Get comprehensive dividend analysis for a company.

    Returns:
        - dividend_yield: Current dividend yield (%)
        - payout_ratio: Dividend payout ratio (%)
        - consistency: Dividend consistency score and rating
        - history: List of dividend payments by year
        - growth_rate: Dividend CAGR (%)
        - next_ex_date: Next ex-dividend date (if available)
    """
    from .analysis.dividend_analysis import analyze_dividend

    symbol = _validate_symbol(symbol)

    result = analyze_dividend(symbol=symbol)
    return result


@app.get("/api/dupont-extended/{symbol}")
def api_dupont_extended(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None
) -> Dict[str, Any]:
    """
    Get Extended DuPont Analysis (5-Component) for a company.

    Returns:
        - roe: Return on Equity
        - dupont_roe: ROE calculated from DuPont components
        - components: 5 DuPont components (tax burden, interest burden,
                     operating margin, asset turnover, financial leverage)
        - contribution: How much each component contributes to ROE
        - interpretation: Text explanation of the analysis

    Formula: ROE = Tax Burden × Interest Burden × Operating Margin ×
                   Asset Turnover × Financial Leverage
    """
    from .analysis.dupont_extended import get_extended_dupont_from_db

    symbol = _validate_symbol(symbol)

    result = get_extended_dupont_from_db(symbol=symbol, year=year)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@app.get("/api/early-warning/{symbol}")
def api_early_warning(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None
) -> Dict[str, Any]:
    """
    Get Early Warning System analysis for a company.

    Detects warning signals including:
    - ROE declining trend
    - Debt to Equity increasing
    - Current Ratio declining (liquidity squeeze)
    - Negative Operating Cash Flow
    - Altman Z-Score in distress zone
    - Piotroski F-Score weakness

    Returns:
        - risk_score: 0-100 (lower is better)
        - risk_level: low, medium, high, critical
        - alerts: List of warning signals with severity
        - positive_signals: List of positive indicators
        - recommendation: Summary recommendation
    """
    from .analysis.early_warning import get_early_warning_for_company

    symbol = _validate_symbol(symbol)

    result = get_early_warning_for_company(symbol=symbol, year=year)
    return result


@app.get("/api/ttm/{symbol}")
def api_ttm_fundamentals(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None,
    quarter: Annotated[Optional[int], Query(ge=1, le=4)] = None,
) -> Dict[str, Any]:
    """
    Get TTM (Trailing Twelve Months) fundamentals from quarterly statements.

    Period semantics:
        - period_type = TTM
        - as_of_period = "TTM as of Q{quarter} {year}"

    Notes:
        - Uses quarterly rows only (quarter BETWEEN 1 AND 4).
        - Degrades gracefully if quarterly coverage is insufficient.
    """
    from .analysis.ttm_analysis import analyze_ttm_fundamentals

    symbol = _validate_symbol(symbol)

    return analyze_ttm_fundamentals(symbol=symbol, year=year, quarter=quarter)


@app.get("/api/ttm/{symbol}/series")
def api_ttm_series(
    symbol: str,
    count: Annotated[int, Query(ge=4, le=24)] = 12,
) -> Dict[str, Any]:
    """
    Rolling TTM time series (per quarter) for trend charts.
    """
    from .analysis.ttm_analysis import get_ttm_series

    symbol = _validate_symbol(symbol)

    return get_ttm_series(symbol=symbol, count=count)


@app.get("/api/cagr/{symbol}")
def api_cagr(
    symbol: str,
    years: Annotated[int, Query(ge=2, le=10)] = 5
) -> Dict[str, Any]:
    """
    Get Compound Annual Growth Rate (CAGR) analysis for a company.

    Calculates CAGR for:
    - Revenue (Doanh thu)
    - Net Profit (Lợi nhuận sau thuế)
    - Total Assets (Tổng tài sản)
    - Equity (Vốn chủ sở hữu)

    Args:
        symbol: Stock symbol
        years: Number of years to analyze (default: 5)

    Returns:
        - period: Start/end year and number of years
        - metrics: CAGR for each metric with rating and description
        - historical_data: Year-by-year data for charting
        - overall_assessment: Combined evaluation
    """
    from .analysis.cagr_analysis import analyze_cagr

    symbol = _validate_symbol(symbol)

    result = analyze_cagr(symbol=symbol, years=years)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ============================================================================
# RECONCILIATION API
# ============================================================================

@app.get("/api/metrics/{symbol}/reconcile")
def api_reconcile_metrics(
    symbol: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None,
    metrics: Annotated[Optional[str], Query(description="Comma-separated metric names")] = None
) -> Dict[str, Any]:
    """
    Reconcile computed vs provided metrics.

    Compares metrics computed from raw financial statements against
    provided values in financial_ratios table to detect data quality issues.

    Args:
        symbol: Stock ticker (e.g., 'FPT')
        year: Year to reconcile (default: latest available)
        metrics: Comma-separated metric names (default: all hybrid metrics)

    Returns:
        {
            "symbol": "FPT",
            "year": 2024,
            "metrics": [
                {
                    "metric": "roe",
                    "computed": 0.215,
                    "provided": 0.21,
                    "delta_abs": 0.005,
                    "delta_pct": 2.38,
                    "status": "OK",
                    "tolerance": 0.05,
                    "inputs_used": ["net_income=2100B", "equity_total=9767B"],
                    "formula": "net_income / equity_total"
                },
                ...
            ],
            "summary": {
                "total": 10,
                "ok": 8,
                "warn": 1,
                "fail": 0,
                "missing_input": 1,
                "not_applicable": 0
            }
        }

    Status codes:
        - OK: delta_pct < tolerance
        - WARN: delta_pct >= tolerance but < 2*tolerance
        - FAIL: delta_pct >= 2*tolerance
        - MISSING_INPUT: cannot compute due to missing data
        - NOT_APPLICABLE: metric disabled for this industry (e.g., market multiples)
    """
    from .analysis.reconciliation import reconcile_all_metrics

    symbol = _validate_symbol(symbol)

    # Determine year
    if year is None:
        with db.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(year) as year FROM financial_ratios
                    WHERE symbol = %s AND quarter IS NULL
                """, (symbol,))
                row = cursor.fetchone()

        if not row or row[0] is None:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        year = row[0]

    # Parse metrics list
    metric_list = None
    if metrics:
        metric_list = [m.strip() for m in metrics.split(",") if m.strip()]

    try:
        result = reconcile_all_metrics(symbol, year, metric_list)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconciliation failed: {str(e)}")


@app.get("/api/metrics/{symbol}/reconcile/{metric}")
def api_reconcile_single_metric(
    symbol: str,
    metric: str,
    year: Annotated[Optional[int], Query(ge=1990, le=2100)] = None
) -> Dict[str, Any]:
    """
    Reconcile a single metric.

    Returns detailed reconciliation result for one metric including
    formula used, inputs, and discrepancy analysis.

    Args:
        symbol: Stock ticker
        metric: Metric name (e.g., 'roe', 'net_profit_margin')
        year: Year to reconcile (default: latest available)

    Returns:
        Single metric reconciliation result
    """
    from .analysis.reconciliation import reconcile_metric

    symbol = _validate_symbol(symbol)

    # Determine year
    if year is None:
        with db.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(year) as year FROM financial_ratios
                    WHERE symbol = %s AND quarter IS NULL
                """, (symbol,))
                row = cursor.fetchone()

        if not row or row[0] is None:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        year = row[0]

    try:
        result = reconcile_metric(symbol, year, metric)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconciliation failed: {str(e)}")
