from __future__ import annotations

import asyncio
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import json
from structlog.contextvars import bind_contextvars

from .agent import LabAgent
from .alerts import check_alerts
from .dashboard_data import build_dashboard_payload
from .incidents import disable, enable, status
from .logging_config import configure_logging, get_logger
from .metrics import record_error, snapshot
from .middleware import CorrelationIdMiddleware
from .pii import hash_user_id, summarize_text
from .schemas import ChatRequest, ChatResponse
from .slo import check_slo_status
from .tracing import tracing_enabled

configure_logging()
log = get_logger()
app = FastAPI(title="Day 13 Observability Lab")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)

agent = LabAgent()


LAST_SLO_STATUS = {}


async def alert_checker() -> None:
    """Background task to evaluate alert rules and SLOs every 5 seconds."""
    global LAST_SLO_STATUS
    while True:
        try:
            check_alerts()
            # Log SLO breaches for visibility
            slo_report = check_slo_status()
            for sli, data in slo_report.items():
                current_status = data["status"]
                if current_status != LAST_SLO_STATUS.get(sli):
                    if "BREACHED" in current_status:
                        log.warning("slo_breach_detected", sli=sli,
                                    actual=data["actual"], objective=data["objective"])
                    elif LAST_SLO_STATUS.get(sli) is not None:
                        log.info("slo_breach_resolved", sli=sli,
                                 actual=data["actual"], objective=data["objective"])
                    LAST_SLO_STATUS[sli] = current_status
        except Exception as e:
            log.error("background_monitoring_failed", error=str(e))
        await asyncio.sleep(5)


@app.on_event("startup")
async def startup() -> None:
    log.info(
        "app_started",
        service=os.getenv("APP_NAME", "day13-observability-lab"),
        env=os.getenv("APP_ENV", "dev"),
        payload={"tracing_enabled": tracing_enabled()},
    )
    asyncio.create_task(alert_checker())


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "tracing_enabled": tracing_enabled(), "incidents": status()}


@app.get("/metrics")
async def metrics() -> dict:
    return snapshot()


@app.get("/slo")
async def slo() -> dict:
    return check_slo_status()


@app.get("/dashboard-data")
async def dashboard_data(window_minutes: int = 60) -> dict:
    return build_dashboard_payload(window_minutes=window_minutes)


@app.get("/dashboard-stream")
async def dashboard_stream(request: Request, window_minutes: int = 60):
    async def event_generator():
        last_payload_hash = None
        while True:
            if await request.is_disconnected():
                break
            payload = build_dashboard_payload(window_minutes=window_minutes)
            # Only send if the overview metrics have changed to save I/O
            current_hash = hash(json.dumps(
                payload["overview"], sort_keys=True))
            if current_hash != last_payload_hash:
                yield f"data: {json.dumps(payload)}\n\n"
                last_payload_hash = current_hash
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    bind_contextvars(
        user_id_hash=hash_user_id(body.user_id),
        session_id=body.session_id,
        feature=body.feature,
        model=agent.model,
    )
    log.info(
        "request_received",
        service="api",
        payload={"message_preview": summarize_text(body.message)},
    )
    try:
        correlation_id = getattr(request.state, "correlation_id", None)
        result = agent.run(
            user_id=body.user_id,
            feature=body.feature,
            session_id=body.session_id,
            message=body.message,
            correlation_id=correlation_id,
        )
        log.info(
            "response_sent",
            service="api",
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            payload={"answer_preview": summarize_text(result.answer)},
        )
        return ChatResponse(
            answer=result.answer,
            correlation_id=request.state.correlation_id,
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
        )
    except Exception as exc:  # pragma: no cover
        error_type = type(exc).__name__
        record_error(error_type)
        log.error(
            "request_failed",
            service="api",
            error_type=error_type,
            payload={"detail": str(
                exc), "message_preview": summarize_text(body.message)},
        )
        raise HTTPException(status_code=500, detail=error_type) from exc


@app.post("/incidents/{name}/enable")
async def enable_incident(name: str) -> JSONResponse:
    try:
        enable(name)
        log.warning("incident_enabled", service="control",
                    payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/incidents/{name}/disable")
async def disable_incident(name: str) -> JSONResponse:
    try:
        disable(name)
        log.warning("incident_disabled", service="control",
                    payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
