"""
Chatbot API route — powered by SAP AI Core (gen_ai_hub) with tool calling.
"""
import json
import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_db
from app.models.analysis import ShorelineAnalysis
from app.models.shoreline import Shoreline
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SAP AI Core helper
# ---------------------------------------------------------------------------

def _get_ai_service():
    llm_config_str = settings.LLM_API_CONFIG
    if not llm_config_str:
        raise RuntimeError("LLM_API_CONFIG environment variable is not set.")

    os.environ["AICORE_SERVICE_KEY"] = llm_config_str
    os.environ["AICORE_RESOURCE_GROUP"] = settings.AICORE_RESOURCE_GROUP

    try:
        from gen_ai_hub.orchestration_v2 import OrchestrationService  # type: ignore
        return OrchestrationService()
    except ImportError as exc:
        raise RuntimeError("gen_ai_hub package is not installed.") from exc


# ---------------------------------------------------------------------------
# Tool schemas (static — no DB dependency)
# ---------------------------------------------------------------------------

def _build_tools():
    from gen_ai_hub.orchestration_v2 import function_tool  # type: ignore

    @function_tool(description=(
        "Lấy số liệu thay đổi đường bờ biển Cửa Tùng giữa hai năm. "
        "Trả về tốc độ xói lở/bồi tụ (m/năm). "
        "Dùng khi hỏi về biến động bờ biển, xói lở, bồi tụ theo năm cụ thể."
    ))
    def get_shoreline_change(year_from: int, year_to: int) -> str:
        """year_from: năm bắt đầu. year_to: năm kết thúc."""
        return ""  # placeholder — executed separately

    @function_tool(description=(
        "Lấy tổng quan dữ liệu bờ biển: các năm có dữ liệu, xu hướng xói lở/bồi tụ chung. "
        "Dùng khi hỏi tổng quan, không biết hỏi năm nào, hoặc hỏi xu hướng chung."
    ))
    def get_coastwatch_summary() -> str:
        """Không cần tham số."""
        return ""

    @function_tool(description=(
        "Lấy điều kiện biển hiện tại: sóng, gió, mực nước, nhiệt độ nước. "
        "Dùng khi hỏi biển hôm nay, sóng cao không, gió mạnh không, đi biển được không."
    ))
    def get_marine_conditions() -> str:
        """Không cần tham số."""
        return ""

    @function_tool(description=(
        "Lấy dự báo sóng và gió N ngày tới. "
        "Dùng khi hỏi dự báo, tuần này biển thế nào, ngày mai sóng cao không."
    ))
    def get_wave_forecast(days: int = 3) -> str:
        """days: số ngày dự báo (1-7)."""
        return ""

    return [get_shoreline_change, get_coastwatch_summary, get_marine_conditions, get_wave_forecast]


# ---------------------------------------------------------------------------
# Tool executors (async, receive DB session)
# ---------------------------------------------------------------------------

async def _exec_tool(name: str, args: dict, db: AsyncSession) -> str:
    if name == "get_marine_conditions":
        return await _exec_marine_conditions()
    if name == "get_wave_forecast":
        return await _exec_wave_forecast(args.get("days", 3))
    if name == "get_coastwatch_summary":
        return await _exec_coastwatch_summary(db)
    if name == "get_shoreline_change":
        return await _exec_shoreline_change(args.get("year_from"), args.get("year_to"), db)
    return json.dumps({"error": f"Unknown tool: {name}"})


async def _exec_marine_conditions() -> str:
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/api/marine/current", timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                cur = d.get("current", {})
                risk = d.get("risk", {})
                return json.dumps({
                    "wave_height_m": cur.get("wave_height_m"),
                    "wave_period_s": cur.get("wave_period_s"),
                    "wave_direction_deg": cur.get("wave_direction_deg"),
                    "wind_speed_kmh": cur.get("wind_speed_kmh"),
                    "sea_level_height_m": cur.get("sea_level_height_m"),
                    "sea_surface_temp_c": cur.get("sea_surface_temp_c"),
                    "risk_level": risk.get("level"),
                    "risk_score": risk.get("score"),
                    "risk_description": risk.get("description"),
                }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
    return json.dumps({"error": "Không lấy được dữ liệu biển"})


async def _exec_wave_forecast(days: int) -> str:
    try:
        import httpx
        days = max(1, min(7, int(days)))
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/api/marine/current", timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                forecasts = d.get("daily_forecast", [])[:days]
                return json.dumps({
                    "days": days,
                    "forecast": [
                        {
                            "date": f["date"],
                            "max_wave_height_m": f.get("max_wave_height_m"),
                            "avg_wind_speed_kmh": f.get("avg_wind_speed_kmh"),
                            "risk_level": f.get("risk_level"),
                        }
                        for f in forecasts
                    ],
                }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
    return json.dumps({"error": "Không lấy được dự báo"})


async def _exec_coastwatch_summary(db: AsyncSession) -> str:
    try:
        r_sl = await db.execute(select(Shoreline).order_by(Shoreline.year))
        shorelines = r_sl.scalars().all()

        r_an = await db.execute(select(ShorelineAnalysis))
        analyses = r_an.scalars().all()

        sl_by_id = {s.id: s.year for s in shorelines}
        years = [s.year for s in shorelines]
        methods = list({s.method for s in shorelines})

        epr_list = [a.epr_m_per_year for a in analyses if a.epr_m_per_year is not None]
        pairs = [
            {
                "from": sl_by_id.get(a.shoreline_from_id),
                "to": sl_by_id.get(a.shoreline_to_id),
                "epr_m_per_year": round(a.epr_m_per_year, 2) if a.epr_m_per_year else None,
                "trend": ("xói lở" if (a.epr_m_per_year or 0) < 0 else "bồi tụ") if a.epr_m_per_year is not None else "chưa có",
            }
            for a in analyses
        ]

        return json.dumps({
            "years_available": years,
            "data_sources": methods,
            "analysis_pairs": pairs,
            "avg_epr_m_per_year": round(sum(epr_list) / len(epr_list), 2) if epr_list else None,
            "overall_trend": (
                "xói lở" if epr_list and sum(epr_list) / len(epr_list) < 0
                else "bồi tụ" if epr_list else "chưa có đủ dữ liệu"
            ),
        }, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


async def _exec_shoreline_change(year_from: Any, year_to: Any, db: AsyncSession) -> str:
    try:
        if year_from is None or year_to is None:
            return json.dumps({"error": "Cần cung cấp year_from và year_to"})
        year_from, year_to = int(year_from), int(year_to)

        r = await db.execute(select(Shoreline).where(Shoreline.year.in_([year_from, year_to])))
        shorelines = {s.year: s for s in r.scalars().all()}

        if year_from not in shorelines:
            return json.dumps({"error": f"Không có dữ liệu năm {year_from}"})
        if year_to not in shorelines:
            return json.dumps({"error": f"Không có dữ liệu năm {year_to}"})

        sl_from = shorelines[year_from]
        sl_to = shorelines[year_to]

        r2 = await db.execute(
            select(ShorelineAnalysis).where(
                ShorelineAnalysis.shoreline_from_id == sl_from.id,
                ShorelineAnalysis.shoreline_to_id == sl_to.id,
            )
        )
        analysis = r2.scalar_one_or_none()

        if analysis is None:
            return json.dumps({
                "year_from": year_from, "year_to": year_to,
                "status": "no_analysis",
                "note": "Chưa có phân tích cho cặp năm này.",
            })

        return json.dumps({
            "year_from": year_from,
            "year_to": year_to,
            "epr_m_per_year": analysis.epr_m_per_year,
            "total_change_m": analysis.total_change_m,
            "data_source": str(sl_from.method),
            "interpretation": (
                "xói lở" if (analysis.epr_m_per_year or 0) < 0 else "bồi tụ"
            ) if analysis.epr_m_per_year is not None else "chưa rõ",
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Bạn là trợ lý AI của hệ thống CoastWatch — theo dõi bờ biển Cửa Tùng, tỉnh Quảng Trị, Việt Nam.

Nguyên tắc:
- Luôn gọi tool để lấy dữ liệu thực trước khi trả lời. Không được tự bịa số liệu.
- Khi trả lời về đường bờ, BẮT BUỘC phải nêu con số EPR cụ thể (ví dụ: "+2.3 m/năm" hoặc "-1.5 m/năm"), từng giai đoạn nếu có.
- Khi trả lời về điều kiện biển, BẮT BUỘC phải nêu: chiều cao sóng (m), tốc độ gió (km/h), mức độ rủi ro.
- Sau khi nêu số liệu, mới kết luận xu hướng (xói lở hay bồi tụ, an toàn hay không).
- Nói ngắn gọn, dễ hiểu. Không dùng thuật ngữ kỹ thuật.
- Nếu tool trả về lỗi hoặc chưa có dữ liệu, nói thẳng với người dùng.

Ví dụ trả lời TỐT khi hỏi về xói lở:
"Từ 2019→2020: bồi tụ +1.2 m/năm. Từ 2020→2021: xói lở -0.8 m/năm. Trung bình cả giai đoạn 2019–2024 là +0.5 m/năm → xu hướng bồi tụ nhẹ."
"""


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    try:
        from gen_ai_hub.orchestration_v2 import (  # type: ignore
            OrchestrationConfig, ModuleConfig, PromptTemplatingModuleConfig,
            LLMModelDetails, Template, SystemMessage, UserMessage,
            AssistantMessage, ToolChatMessage,
        )
    except ImportError as exc:
        raise HTTPException(status_code=502, detail="gen_ai_hub not installed") from exc

    try:
        service = _get_ai_service()
        tools = _build_tools()
        llm_details = LLMModelDetails(
            name=settings.AICORE_LLM_MODEL,
            params={"max_tokens": 1024, "temperature": 0.3},
        )

        def _make_config(tool_list):
            return OrchestrationConfig(
                modules=ModuleConfig(
                    prompt_templating=PromptTemplatingModuleConfig(
                        prompt=Template(
                            template=[
                                SystemMessage(content=SYSTEM_PROMPT),
                                UserMessage(content=request.message),
                            ],
                            tools=tool_list,
                        ),
                        model=llm_details,
                    ),
                )
            )

        # First call
        response = service.run(config=_make_config(tools))
        assistant_msg = response.final_result.choices[0].message

        # Agentic loop — up to 3 rounds of tool calls
        history = []
        for _round in range(3):
            tool_calls = getattr(assistant_msg, "tool_calls", None)
            if not tool_calls:
                break

            # Execute tools (async, with DB)
            tool_results = []
            for tc in tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    fn_args = {}

                result_str = await _exec_tool(fn_name, fn_args, db)
                logger.info("Tool %s(%s) → %s", fn_name, fn_args, result_str[:200])

                tool_results.append(ToolChatMessage(
                    tool_call_id=tc.id,
                    content=result_str,
                ))

            # Pass tool results back to LLM
            history = [
                AssistantMessage(
                    content=assistant_msg.content or "",
                    tool_calls=tool_calls,
                ),
                *tool_results,
            ]

            followup = service.run(config=_make_config(tools), history=history)
            assistant_msg = followup.final_result.choices[0].message

        reply = (assistant_msg.content or "").strip() or "Xin lỗi, tôi không thể trả lời lúc này."

    except Exception as exc:
        logger.error("Chat request failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")

    return ChatResponse(
        session_id=request.session_id,
        reply=reply,
        model=settings.AICORE_LLM_MODEL,
        context_used=True,
    )
