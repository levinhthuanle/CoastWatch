"""
Erosion risk scoring based on marine conditions.

Wave energy is the primary driver of coastal erosion. This scorer combines:
- Wave height (dominant factor)
- Swell wave height (long-period energy = deep penetration)
- Wind speed (local storm generation)
- Seasonal monsoon context (NE monsoon Oct-Feb is high-energy for central Vietnam)

Risk levels:
  0–25:  low        — calm conditions, minimal erosion risk
  25–50: moderate   — active wave conditions, monitor closely
  50–75: high       — energetic conditions, erosion likely
  75–100: extreme   — storm-wave conditions, severe erosion risk
"""
import math
from datetime import datetime
from typing import Any, Dict, Optional


def _monsoon_multiplier(month: int) -> float:
    """
    Seasonal weight for central Vietnam (Quảng Trị / Cửa Tùng).
    NE monsoon (Oct–Feb) brings the most energetic seas.
    SW monsoon (May–Sep) is milder on this coast.
    """
    # NE monsoon peak
    if month in (10, 11, 12, 1, 2):
        return 1.25
    # Transitional
    if month in (3, 4, 9):
        return 1.0
    # SW monsoon — relatively sheltered by Trường Sơn range
    return 0.85


def score_erosion_risk(
    wave_height_m: Optional[float],
    swell_wave_height_m: Optional[float],
    wind_wave_height_m: Optional[float],
    wind_speed_kmh: Optional[float],
    timestamp: Optional[str] = None,
    historical_epr_m_per_year: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute erosion risk score [0–100] from current marine conditions.

    Args:
        wave_height_m: Significant wave height (total)
        swell_wave_height_m: Swell component (long-period, more erosive)
        wind_wave_height_m: Wind-wave component (short-period, less penetrating)
        wind_speed_kmh: 10-m wind speed
        timestamp: ISO datetime string for seasonal adjustment
        historical_epr_m_per_year: Historical EPR (negative = erosion trend)

    Returns:
        Dict with score, level, explanation, contributing_factors
    """
    wh = wave_height_m or 0.0
    swh = swell_wave_height_m or 0.0
    wwh = wind_wave_height_m or 0.0
    ws = wind_speed_kmh or 0.0

    # Wave energy proportional to H²
    wave_energy = wh ** 2  # m²
    swell_energy = swh ** 2 * 1.3  # swell weighted higher (longer period)
    wind_wave_energy = wwh ** 2 * 0.8

    # Composite wave energy score (normalised: 4m² ≈ full score)
    max_energy = 4.0
    wave_score = min(100.0, (wave_energy + swell_energy * 0.5 + wind_wave_energy * 0.3) / max_energy * 100)

    # Wind contribution (Beaufort 8 = 75 km/h ≈ full contribution)
    wind_score = min(100.0, (ws / 75.0) ** 1.5 * 100)

    # Seasonal adjustment
    month = datetime.now().month
    if timestamp:
        try:
            month = datetime.fromisoformat(timestamp).month
        except ValueError:
            pass
    seasonal = _monsoon_multiplier(month)

    # Weighted composite
    raw_score = (wave_score * 0.65 + wind_score * 0.35) * seasonal

    # Historical trend bonus: if EPR shows ongoing erosion, base risk is elevated
    if historical_epr_m_per_year is not None and historical_epr_m_per_year < 0:
        # Each m/yr of erosion adds up to +10 pts
        trend_bonus = min(10.0, abs(historical_epr_m_per_year) * 2.0)
        raw_score = min(100.0, raw_score + trend_bonus)

    score = round(min(100.0, max(0.0, raw_score)), 1)

    if score < 25:
        level = "low"
        color = "#22d3ee"
        description = "Sóng nhẹ, điều kiện bờ biển ổn định"
    elif score < 50:
        level = "moderate"
        color = "#f59e0b"
        description = "Sóng vừa phải, cần theo dõi"
    elif score < 75:
        level = "high"
        color = "#f97316"
        description = "Năng lượng sóng cao, nguy cơ xói lở"
    else:
        level = "extreme"
        color = "#ef4444"
        description = "Sóng bão, nguy cơ xói lở nghiêm trọng"

    # Human-readable season note
    season_note = {
        10: "Gió mùa Đông Bắc (mùa cao điểm)",
        11: "Gió mùa Đông Bắc (mùa cao điểm)",
        12: "Gió mùa Đông Bắc (mùa cao điểm)",
        1:  "Gió mùa Đông Bắc (mùa cao điểm)",
        2:  "Gió mùa Đông Bắc (mùa cao điểm)",
        3:  "Giai đoạn chuyển tiếp",
        4:  "Giai đoạn chuyển tiếp",
        5:  "Gió mùa Tây Nam (ít ảnh hưởng)",
        6:  "Gió mùa Tây Nam (ít ảnh hưởng)",
        7:  "Gió mùa Tây Nam (ít ảnh hưởng)",
        8:  "Gió mùa Tây Nam (ít ảnh hưởng)",
        9:  "Giai đoạn chuyển tiếp",
    }.get(month, "")

    return {
        "score": score,
        "level": level,
        "color": color,
        "description": description,
        "season_note": season_note,
        "contributing_factors": {
            "wave_energy_score": round(wave_score, 1),
            "wind_score": round(wind_score, 1),
            "seasonal_multiplier": seasonal,
            "historical_trend_adjustment": (
                round(min(10.0, abs(historical_epr_m_per_year) * 2.0), 1)
                if historical_epr_m_per_year is not None and historical_epr_m_per_year < 0
                else 0.0
            ),
        },
    }


def classify_wave_energy_7day(hourly_data: list) -> Dict[str, Any]:
    """
    Summarise 7-day wave forecast into daily risk levels.
    Returns list of {date, avg_wave_height_m, max_wave_height_m, risk_score, risk_level}.
    """
    from collections import defaultdict

    daily: Dict[str, list] = defaultdict(list)
    for row in hourly_data:
        day = row["time"][:10]  # "YYYY-MM-DD"
        if row["wave_height_m"] is not None:
            daily[day].append(row)

    result = []
    for day in sorted(daily.keys()):
        rows = daily[day]
        whs = [r["wave_height_m"] for r in rows if r["wave_height_m"] is not None]
        swhs = [r["swell_wave_height_m"] for r in rows if r["swell_wave_height_m"] is not None]
        wss = [r["wind_speed_kmh"] for r in rows if r["wind_speed_kmh"] is not None]

        avg_wh = sum(whs) / len(whs) if whs else 0.0
        max_wh = max(whs) if whs else 0.0
        avg_swh = sum(swhs) / len(swhs) if swhs else 0.0
        avg_ws = sum(wss) / len(wss) if wss else 0.0

        risk = score_erosion_risk(avg_wh, avg_swh, None, avg_ws, day + "T12:00")
        result.append({
            "date": day,
            "avg_wave_height_m": round(avg_wh, 2),
            "max_wave_height_m": round(max_wh, 2),
            "avg_swell_height_m": round(avg_swh, 2),
            "avg_wind_speed_kmh": round(avg_ws, 1),
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "risk_color": risk["color"],
        })

    return {"daily": result}
