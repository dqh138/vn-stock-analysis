"""
Early Warning System - Hệ thống Cảnh báo Tài chính Sớm

Module này phát hiện các tín hiệu cảnh báo sớm về sức khỏe tài chính của doanh nghiệp.
Bao gồm:
- Risk Score (0-100, lower is better)
- Phát hiện xu hướng suy giảm (ROE, biên lợi nhuận, thanh khoản)
- Cảnh báo nợ gia tăng
- Dòng tiền âm
- Altman Z-Score trong vùng nguy hiểm
- Piotroski F-Score thấp

Author: Early Warning System
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from .annual_selector import (
    get_financial_ratios_annual,
    get_latest_year,
    get_previous_year,
    select_balance_sheet_annual,
    select_cash_flow_annual,
    select_income_statement_annual,
)
from .period_contract import as_of_period_label, latest_quarter_for_symbol

def calculate_early_warning(
    symbol: str,
    db_path=None,
    year: Optional[int] = None,
    financial_ratios: Optional[Dict[str, Any]] = None,
    balance_sheet: Optional[Dict[str, Any]] = None,
    income_statement: Optional[Dict[str, Any]] = None,
    cash_flow: Optional[Dict[str, Any]] = None,
    altman_z_score: Optional[Dict[str, Any]] = None,
    piotroski_f_score: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Tính toán cảnh báo sớm cho một công ty

    Args:
        symbol: Mã cổ phiếu
        db_path: Ignored; connection comes from DATABASE_URL
        year: Năm phân tích (nếu None, lấy năm gần nhất)
        financial_ratios: Chỉ số tài chính
        balance_sheet: Bảng cân đối kế toán
        income_statement: Báo cáo kết quả kinh doanh
        cash_flow: Báo cáo dòng tiền
        altman_z_score: Kết quả Altman Z-Score
        piotroski_f_score: Kết quả Piotroski F-Score

    Returns:
        Dict chứa:
        - risk_score: 0-100 (lower is better)
        - risk_level: low, medium, high, critical
        - alerts: List of warnings
        - positive_signals: List of positive indicators
        - recommendation: Summary recommendation
    """
    alerts = []
    positive_signals = []

    from .. import db as _db
    with _db.connect() as conn:
        with conn.cursor() as cursor:

            # Lấy năm gần nhất nếu không chỉ định
            if year is None:
                cursor.execute("""
                    SELECT year FROM financial_ratios
                    WHERE symbol = %s AND quarter IS NULL
                    ORDER BY year DESC LIMIT 1
                """, (symbol,))
                row = cursor.fetchone()
                year = row['year'] if row else None

            if year is None:
                return {
                    "risk_score": 50,
                    "risk_level": "medium",
                    "alerts": [],
                    "positive_signals": [],
                    "recommendation": "Không đủ dữ liệu để đánh giá",
                    "period": {
                        "period_type": "ANNUAL",
                        "year": None,
                        "quarter": None,
                        "as_of_period": None,
                        "trend_source": None,
                    },
                }

            # Prefer quarterly trend checks when quarterly ratios exist for the requested year.
            # (Quarterly statements coverage is narrow; financial_ratios quarterly coverage is broad.)
            latest_q = latest_quarter_for_symbol(conn, symbol, year_limit=year)
            use_quarterly_trends = latest_q is not None and latest_q[0] == year

            trend_period_type = "QUARTER" if use_quarterly_trends else "ANNUAL"
            trend_year = latest_q[0] if use_quarterly_trends else year
            trend_quarter = latest_q[1] if use_quarterly_trends else None
            trend_label = as_of_period_label(trend_year, trend_quarter)

            # 1. KIỂM TRA ROE DECLINING (giảm 3 quý liên tiếp)
            _check_roe_decline(cursor, symbol, year, alerts, positive_signals,
                               use_quarterly=use_quarterly_trends,
                               as_of_year=trend_year,
                               as_of_quarter=trend_quarter)

            # 2. KIỂM TRA DEBT TO EQUITY INCREASING (tăng 3 quý)
            _check_debt_increase(cursor, symbol, year, alerts, positive_signals,
                                 use_quarterly=use_quarterly_trends,
                                 as_of_year=trend_year,
                                 as_of_quarter=trend_quarter)

            # 3. KIỂM TRA CURRENT RATIO DECLINING (thanh khoản giảm)
            _check_liquidity_decline(cursor, symbol, year, alerts, positive_signals,
                                     use_quarterly=use_quarterly_trends,
                                     as_of_year=trend_year,
                                     as_of_quarter=trend_quarter)

            # 4. KIỂM TRA NEGATIVE OPERATING CASH FLOW
            _check_cash_flow(conn, symbol, year, alerts, positive_signals)

            # 5. KIỂM TRA ALTMAN Z-SCORE
            if altman_z_score:
                _check_altman_z_score(altman_z_score, alerts, positive_signals)

            # 6. KIỂM TRA PIOTROSKI F-SCORE
            if piotroski_f_score:
                _check_piotroski_f_score(piotroski_f_score, alerts, positive_signals)

            # 7. KIỂM TRA NET MARGIN DECLINING
            _check_margin_decline(cursor, symbol, year, alerts, positive_signals,
                                  use_quarterly=use_quarterly_trends,
                                  as_of_year=trend_year,
                                  as_of_quarter=trend_quarter)

    # TÍNH TOÁN RISK SCORE
    risk_score = _calculate_risk_score(alerts)

    # XÁC ĐỊNH RISK LEVEL
    risk_level = _determine_risk_level(risk_score)

    # TỔNG HỢP KHUYẾN NGHỊ
    recommendation = _generate_recommendation(risk_level, alerts, positive_signals)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "alerts": alerts,
        "positive_signals": positive_signals,
        "recommendation": recommendation,
        "period": {
            "period_type": trend_period_type,
            "year": trend_year,
            "quarter": trend_quarter,
            "as_of_period": trend_label,
            "trend_source": "financial_ratios_quarterly" if use_quarterly_trends else "financial_ratios_annual",
        },
    }


def _fetch_recent_ratio_values(
    cursor,
    symbol: str,
    field: str,
    use_quarterly: bool,
    as_of_year: int,
    as_of_quarter: Optional[int],
    limit: int = 4,
):
    """
    Fetch recent ratio values as a list of tuples:
        (year, quarter_or_None, value)

    - Quarterly mode uses quarter IS NOT NULL and caps at (as_of_year, as_of_quarter).
    - Annual mode uses quarter IS NULL and caps at as_of_year.
    """
    if use_quarterly and as_of_quarter is not None:
        cursor.execute(
            f"""
            SELECT year, quarter, {field} AS value
            FROM financial_ratios
            WHERE symbol = %s
              AND quarter IS NOT NULL
              AND (year < %s OR (year = %s AND quarter <= %s))
              AND {field} IS NOT NULL
            ORDER BY year DESC, quarter DESC
            LIMIT %s
            """,
            (symbol, as_of_year, as_of_year, as_of_quarter, limit),
        )
        return [(r["year"], r["quarter"], r["value"]) for r in cursor.fetchall()]

    cursor.execute(
        f"""
        SELECT year, NULL AS quarter, {field} AS value
        FROM financial_ratios
        WHERE symbol = %s AND quarter IS NULL AND year <= %s AND {field} IS NOT NULL
        ORDER BY year DESC
        LIMIT %s
        """,
        (symbol, as_of_year, limit),
    )
    return [(r["year"], None, r["value"]) for r in cursor.fetchall()]


def _check_roe_decline(
    cursor,
    symbol: str,
    year: int,
    alerts: List,
    positive_signals: List,
    use_quarterly: bool,
    as_of_year: int,
    as_of_quarter: Optional[int],
):
    """
    Kiểm tra ROE giảm liên tiếp (ưu tiên theo quý nếu có, fallback theo năm).
    """
    rows = _fetch_recent_ratio_values(
        cursor, symbol, "roe",
        use_quarterly=use_quarterly,
        as_of_year=as_of_year,
        as_of_quarter=as_of_quarter,
        limit=4,
    )
    if len(rows) < 2:
        return

    # rows are ordered desc by time: current first
    values = [float(v) for (_, _, v) in rows if v is not None]
    if len(values) < 2:
        return

    label_unit = "quý" if use_quarterly else "năm"
    compare_label = "quý trước" if use_quarterly else "năm trước"

    # Decline across the last 3 periods if available (current < prev < prev2)
    is_declining_3 = False
    if len(values) >= 3:
        is_declining_3 = values[0] < values[1] < values[2]

    if is_declining_3:
        alerts.append({
            "type": "roe_decline",
            "severity": "warning",
            "message": f"ROE giảm liên tiếp trong 3 {label_unit} gần nhất",
            "value": {
                "current": round(values[0] * 100, 2),
                "previous": round(values[1] * 100, 2),
                "trend": "declining"
            }
        })
    elif values[0] > values[1]:
        positive_signals.append({
            "type": "roe_improving",
            "message": f"ROE cải thiện so với {compare_label}"
        })


def _check_debt_increase(
    cursor,
    symbol: str,
    year: int,
    alerts: List,
    positive_signals: List,
    use_quarterly: bool,
    as_of_year: int,
    as_of_quarter: Optional[int],
):
    """
    Kiểm tra Debt to Equity tăng liên tiếp (ưu tiên theo quý nếu có, fallback theo năm).
    """
    rows = _fetch_recent_ratio_values(
        cursor, symbol, "debt_to_equity",
        use_quarterly=use_quarterly,
        as_of_year=as_of_year,
        as_of_quarter=as_of_quarter,
        limit=4,
    )
    if len(rows) < 2:
        return

    values = [float(v) for (_, _, v) in rows if v is not None]
    if len(values) < 2:
        return

    label_unit = "quý" if use_quarterly else "năm"
    compare_label = "quý trước" if use_quarterly else "năm trước"

    is_increasing_3 = False
    if len(values) >= 3:
        is_increasing_3 = values[0] > values[1] > values[2]

    if is_increasing_3:
        current_debt = values[0]
        prev_debt = values[1]

        if current_debt > 2.0:
            severity = "critical"
        elif current_debt > 1.5:
            severity = "warning"
        else:
            severity = "info"

        alerts.append({
            "type": "debt_increase",
            "severity": severity,
            "message": f"Tỷ lệ nợ/vốn chủ sở hữu tăng liên tiếp trong 3 {label_unit} gần nhất",
            "value": {
                "current": round(current_debt, 2),
                "previous": round(prev_debt, 2),
                "trend": "increasing"
            }
        })
    elif values[0] < values[1]:
        positive_signals.append({
            "type": "debt_improving",
            "message": f"Tỷ lệ nợ/vốn chủ sở hữu cải thiện so với {compare_label}"
        })


def _check_liquidity_decline(
    cursor,
    symbol: str,
    year: int,
    alerts: List,
    positive_signals: List,
    use_quarterly: bool,
    as_of_year: int,
    as_of_quarter: Optional[int],
):
    """
    Kiểm tra Current Ratio giảm (ưu tiên theo quý nếu có, fallback theo năm).
    """
    rows = _fetch_recent_ratio_values(
        cursor, symbol, "current_ratio",
        use_quarterly=use_quarterly,
        as_of_year=as_of_year,
        as_of_quarter=as_of_quarter,
        limit=2,
    )
    if len(rows) < 2:
        return

    current_ratio = float(rows[0][2])
    prev_ratio = float(rows[1][2])

    compare_label = "quý trước" if use_quarterly else "năm trước"

    if current_ratio < prev_ratio:
        decline_pct = ((prev_ratio - current_ratio) / prev_ratio) * 100 if prev_ratio > 0 else 0

        if current_ratio < 1.0:
            severity = "critical"
            message = f"Thanh khoản ở mức thấp ({current_ratio:.2f}x)"
        elif current_ratio < 1.2:
            severity = "warning"
            message = f"Tỷ lệ thanh khoản hiện hành giảm ({current_ratio:.2f}x)"
        elif decline_pct > 20:
            severity = "warning"
            message = f"Thanh khoản giảm {decline_pct:.0f}% so với {compare_label}"
        else:
            severity = "info"
            message = f"Thanh khoản giảm nhẹ ({current_ratio:.2f}x)"

        alerts.append({
            "type": "liquidity_decline",
            "severity": severity,
            "message": message,
            "value": {
                "current": round(current_ratio, 2),
                "previous": round(prev_ratio, 2),
                "trend": "declining"
            }
        })
    elif current_ratio >= 1.5:
        positive_signals.append({
            "type": "liquidity_healthy",
            "message": f"Thanh khoản tốt ({current_ratio:.2f}x)"
        })


def _check_cash_flow(conn: Any, symbol: str, year: int, alerts: List, positive_signals: List):
    """
    Kiểm tra dòng tiền hoạt động âm
    """
    # Statement tables may have duplicated quarter=NULL rows; select annual deterministically.
    ratios_row = get_financial_ratios_annual(conn, symbol, year)
    balance_row = select_balance_sheet_annual(conn, symbol, year, financial_ratios_row=ratios_row)
    cash_row = select_cash_flow_annual(conn, symbol, year, balance_sheet_row=balance_row)
    current_ocf = cash_row.get("net_cash_from_operating_activities") if cash_row else None

    if current_ocf is None:
        return

    if current_ocf < 0:
        alerts.append({
            "type": "negative_cash_flow",
            "severity": "critical",
            "message": f"Dòng tiền từ hoạt động kinh doanh âm ({current_ocf/1e9:.1f} tỷ VND)",
            "value": {
                "current": current_ocf,
                "trend": "negative"
            }
        })
    else:
        # Kiểm tra tính nhất quán
        prev_year = get_previous_year(conn, symbol, year)
        if prev_year is not None:
            prev_ratios = get_financial_ratios_annual(conn, symbol, prev_year)
            prev_balance = select_balance_sheet_annual(conn, symbol, prev_year, financial_ratios_row=prev_ratios)
            prev_cash = select_cash_flow_annual(conn, symbol, prev_year, balance_sheet_row=prev_balance)
            prev_ocf = prev_cash.get("net_cash_from_operating_activities") if prev_cash else None
        else:
            prev_ocf = None

        if prev_ocf is not None and prev_ocf > 0 and current_ocf > 0:
            positive_signals.append({
                "type": "cash_flow_positive",
                "message": f"Dòng tiền hoạt động dương và ổn định"
            })


def _check_altman_z_score(altman_z_score: Dict, alerts: List, positive_signals: List):
    """
    Kiểm tra Altman Z-Score
    """
    z_score = altman_z_score.get('z_score')
    if z_score is None:
        return

    if z_score < 1.81:
        alerts.append({
            "type": "altman_distress",
            "severity": "critical",
            "message": f"Altman Z-Score ở vùng nguy hiểm ({z_score:.2f})",
            "value": {
                "current": z_score,
                "threshold": 1.81
            }
        })
    elif z_score < 2.99:
        alerts.append({
            "type": "altman_grey_zone",
            "severity": "warning",
            "message": f"Altman Z-Score ở vùng xám ({z_score:.2f})",
            "value": {
                "current": z_score,
                "threshold": 2.99
            }
        })
    else:
        positive_signals.append({
            "type": "altman_safe",
            "message": f"Altman Z-Score ở mức an toàn ({z_score:.2f})"
        })


def _check_piotroski_f_score(piotroski_f_score: Dict, alerts: List, positive_signals: List):
    """
    Kiểm tra Piotroski F-Score
    """
    score = piotroski_f_score.get('score')
    if score is None:
        return
    criteria_available = piotroski_f_score.get("criteria_available")
    # Academic guardrail: if the score is computed from too few observable criteria,
    # avoid triggering strong warnings (reduces false positives under data limits).
    if isinstance(criteria_available, int) and criteria_available < 6:
        return

    if score < 4:
        alerts.append({
            "type": "piotroski_weak",
            "severity": "warning",
            "message": f"Piotroski F-Score thấp ({score}/9)",
            "value": {
                "current": score,
                "threshold": 4
            }
        })
    elif score >= 7:
        positive_signals.append({
            "type": "piotroski_strong",
            "message": f"Piotroski F-Score mạnh ({score}/9)"
        })


def _check_margin_decline(
    cursor,
    symbol: str,
    year: int,
    alerts: List,
    positive_signals: List,
    use_quarterly: bool,
    as_of_year: int,
    as_of_quarter: Optional[int],
):
    """
    Kiểm tra biên lợi nhuận giảm (ưu tiên theo quý nếu có, fallback theo năm).
    """
    # Prefer net_profit_margin, fallback to gross_margin per period.
    net_rows = _fetch_recent_ratio_values(
        cursor, symbol, "net_profit_margin",
        use_quarterly=use_quarterly,
        as_of_year=as_of_year,
        as_of_quarter=as_of_quarter,
        limit=2,
    )
    gross_rows = _fetch_recent_ratio_values(
        cursor, symbol, "gross_margin",
        use_quarterly=use_quarterly,
        as_of_year=as_of_year,
        as_of_quarter=as_of_quarter,
        limit=2,
    )

    def pick_margin(i: int) -> Optional[float]:
        try:
            v = float(net_rows[i][2]) if len(net_rows) > i and net_rows[i][2] is not None else None
        except (TypeError, ValueError):
            v = None
        if v is not None:
            return v
        try:
            return float(gross_rows[i][2]) if len(gross_rows) > i and gross_rows[i][2] is not None else None
        except (TypeError, ValueError):
            return None

    current_margin = pick_margin(0)
    prev_margin = pick_margin(1)
    if current_margin is None or prev_margin is None:
        return

    compare_label = "quý trước" if use_quarterly else "năm trước"

    if current_margin < prev_margin:
        decline_pct = ((prev_margin - current_margin) / prev_margin) * 100 if prev_margin > 0 else 0

        if decline_pct > 30:
            severity = "warning"
            message = f"Biên lợi nhuận giảm mạnh ({decline_pct:.0f}%)"
        elif decline_pct > 10:
            severity = "info"
            message = f"Biên lợi nhuận giảm ({decline_pct:.0f}%) so với {compare_label}"
        else:
            return  # Bỏ qua biến động nhỏ

        alerts.append({
            "type": "margin_compression",
            "severity": severity,
            "message": message,
            "value": {
                "current": round(current_margin * 100, 2),
                "previous": round(prev_margin * 100, 2),
                "trend": "declining"
            }
        })
    elif current_margin > prev_margin:
        positive_signals.append({
            "type": "margin_improving",
            "message": f"Biên lợi nhuận cải thiện so với {compare_label}"
        })


def _calculate_risk_score(alerts: List[Dict]) -> int:
    """
    Tính toán Risk Score từ danh sách alerts

    Scoring:
    - Critical: +15 điểm
    - Warning: +10 điểm
    - Info: +5 điểm
    - Maximum: 100
    """
    score = 0

    for alert in alerts:
        severity = alert.get('severity', 'info')
        if severity == 'critical':
            score += 15
        elif severity == 'warning':
            score += 10
        else:  # info
            score += 5

    return min(score, 100)


def _determine_risk_level(score: int) -> str:
    """
    Xác định mức độ rủi ro từ điểm số
    """
    if score <= 25:
        return "low"
    elif score <= 50:
        return "medium"
    elif score <= 75:
        return "high"
    else:
        return "critical"


def _generate_recommendation(risk_level: str, alerts: List, positive_signals: List) -> str:
    """
    Tạo khuyến nghị dựa trên mức độ rủi ro và các tín hiệu
    """
    if risk_level == "low":
        if positive_signals:
            return "Sức khỏe tài chính tốt. Duy trì các chỉ số hiện tại và theo dõi định kỳ."
        return "Sức khỏe tài chính ổn định. Tiếp tục theo dõi các chỉ số chính."

    elif risk_level == "medium":
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        if critical_alerts:
            return "Có một số vấn đề cần chú ý. Nên xem xét các cảnh báo quan trọng và theo dõi chặt."
        return "Sức khỏe tài chính ở mức trung bình. Cần theo dõi các xu hướng và cải thiện thanh khoản."

    elif risk_level == "high":
        return "Rủi ro tài chính cao. Cần đánh giá lại chiến lược và có biện pháp cải thiện các chỉ số yếu."

    else:  # critical
        return "Rủi ro tài chính rất cao. Cần hành động ngay lập tức để giải quyết các vấn đề tài chính."

# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def get_early_warning_for_company(
    db_path=None,
    symbol: str = "",
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Hàm tiện ích để lấy cảnh báo sớm cho một công ty

    Args:
        db_path: Ignored; connection comes from DATABASE_URL
        symbol: Mã cổ phiếu
        year: Năm phân tích

    Returns:
        Dict chứa kết quả cảnh báo sớm
    """
    from .. import db as _db
    with _db.connect() as conn:
        with conn.cursor() as cursor:
            try:
                # Determine latest year deterministically from financial_ratios (clean annual series)
                if year is None:
                    year = get_latest_year(conn, symbol)

                if year is None:
                    return {
                        "risk_score": 50,
                        "risk_level": "medium",
                        "alerts": [],
                        "positive_signals": [],
                        "recommendation": "Không đủ dữ liệu",
                    }

                # Load annual rows (deterministic selection for statements)
                financial_ratios = get_financial_ratios_annual(conn, symbol, year)
                income_statement = select_income_statement_annual(conn, symbol, year)
                balance_sheet = select_balance_sheet_annual(conn, symbol, year, financial_ratios_row=financial_ratios)
                cash_flow = select_cash_flow_annual(conn, symbol, year, balance_sheet_row=balance_sheet)

                prev_year = get_previous_year(conn, symbol, year)
                prev_financial_ratios = get_financial_ratios_annual(conn, symbol, prev_year) if prev_year else {}
                prev_income_statement = select_income_statement_annual(conn, symbol, prev_year) if prev_year else {}
                prev_balance_sheet = select_balance_sheet_annual(conn, symbol, prev_year, financial_ratios_row=prev_financial_ratios) if prev_year else {}
                prev_cash_flow = select_cash_flow_annual(conn, symbol, prev_year, balance_sheet_row=prev_balance_sheet) if prev_year else {}

                # Compute Altman Z-Score & Piotroski F-Score for warning checks (when applicable)
                from .core_analysis import CoreAnalysisEngine
                from .industry_router import detect_industry

                # Industry validity: Altman Z is not applicable to banks/insurance
                cursor.execute("SELECT icb_name3 FROM stock_industry WHERE ticker = %s", (symbol,))
                meta = cursor.fetchone()
                icb_name = meta["icb_name3"] if meta else None
                industry_type = detect_industry(icb_name=icb_name, ticker=symbol)

                # Market cap heuristic (column may be raw VND despite name)
                market_cap = None
                try:
                    mc_raw = financial_ratios.get("market_cap_billions")
                    if mc_raw is not None:
                        mc_val = float(mc_raw)
                        market_cap = mc_val * 1_000_000_000 if mc_val < 1_000_000_000 else mc_val
                except (TypeError, ValueError):
                    market_cap = None

                engine = CoreAnalysisEngine(
                    financial_ratios=financial_ratios,
                    balance_sheet=balance_sheet,
                    income_statement=income_statement,
                    cash_flow=cash_flow,
                    previous_balance_sheet=prev_balance_sheet,
                    previous_income_statement=prev_income_statement,
                    previous_cash_flow=prev_cash_flow,
                    previous_financial_ratios=prev_financial_ratios,
                )

                piotroski_f_score = engine.calculate_piotroski_f_score()
                altman_z_score = None
                if industry_type not in ("banks", "insurance"):
                    altman_z_score = engine.calculate_altman_z_score(market_cap=market_cap)
                else:
                    altman_z_score = {"z_score": None, "rating": "NOT_APPLICABLE", "vietnamese_rating": "Không áp dụng"}
            except Exception:
                raise

    # Tính toán cảnh báo sớm
    result = calculate_early_warning(
        symbol=symbol,
        db_path=db_path,
        year=year,
        financial_ratios=financial_ratios,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cash_flow=cash_flow,
        altman_z_score=altman_z_score,
        piotroski_f_score=piotroski_f_score
    )

    return result
