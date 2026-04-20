from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any

from .metrics import percentile
from .slo import check_slo_status

LOG_PATH = Path("data/logs.jsonl")
ALERT_RULES_PATH = Path("config/alert_rules.yaml")
SLO_PATH = Path("config/slo.yaml")
EVIDENCE_PATH = Path("docs/grading-evidence.md")
INCIDENTS_PATH = Path("data/incidents.json")


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    root: dict[str, Any] = {}
    current_section: str | None = None
    current_item: dict[str, Any] | None = None
    current_key: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0 and line.endswith(":"):
            current_section = line[:-1]
            root[current_section] = [] if current_section == "alerts" else {}
            current_item = None
            current_key = None
            continue

        if current_section == "alerts" and line.startswith("- "):
            current_item = {}
            root[current_section].append(current_item)
            key, value = line[2:].split(":", 1)
            current_item[key.strip()] = value.strip()
            continue

        if current_section == "alerts" and current_item and ":" in line:
            key, value = line.split(":", 1)
            current_item[key.strip()] = value.strip()
            continue

        if indent == 2 and line.endswith(":") and current_section:
            current_key = line[:-1]
            root[current_section][current_key] = {}
            continue

        if indent >= 4 and current_section and current_key and ":" in line:
            key, value = line.split(":", 1)
            value = value.strip()
            if value.replace(".", "", 1).isdigit():
                parsed: Any = float(value) if "." in value else int(value)
            else:
                parsed = value
            root[current_section][current_key][key.strip()] = parsed

    return root


def _read_evidence_items(path: Path) -> list[str]:
    if not path.exists():
        return []
    items: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("- "):
            items.append(line.strip()[2:])
    return items


def build_dashboard_payload(window_minutes: int = 60) -> dict[str, Any]:
    all_logs = _read_jsonl(LOG_PATH)
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=window_minutes)

    recent_logs = [
        rec
        for rec in all_logs
        if (parsed := _parse_iso(rec.get("ts"))) is not None and parsed >= cutoff
    ]

    api_logs = [rec for rec in recent_logs if rec.get("service") == "api"]
    response_logs = [rec for rec in api_logs if rec.get("event") == "response_sent"]
    error_logs = [rec for rec in api_logs if rec.get("event") == "request_failed"]

    latencies = [int(rec.get("latency_ms", 0)) for rec in response_logs if rec.get("latency_ms") is not None]
    costs = [float(rec.get("cost_usd", 0.0)) for rec in response_logs if rec.get("cost_usd") is not None]
    quality_scores = [
        float(rec.get("quality_score", 0.0))
        for rec in response_logs
        if rec.get("quality_score") is not None
    ]

    points_by_minute: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "requests": 0,
            "errors": 0,
            "cost_usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "quality_sum": 0.0,
            "quality_count": 0,
        }
    )

    for rec in response_logs:
        ts = _parse_iso(rec.get("ts"))
        if not ts:
            continue
        bucket = ts.strftime("%H:%M")
        point = points_by_minute[bucket]
        point["requests"] += 1
        point["cost_usd"] += float(rec.get("cost_usd", 0.0))
        point["tokens_in"] += int(rec.get("tokens_in", 0))
        point["tokens_out"] += int(rec.get("tokens_out", 0))
        if rec.get("quality_score") is not None:
            point["quality_sum"] += float(rec["quality_score"])
            point["quality_count"] += 1

    for rec in error_logs:
        ts = _parse_iso(rec.get("ts"))
        if not ts:
            continue
        bucket = ts.strftime("%H:%M")
        points_by_minute[bucket]["errors"] += 1

    timeseries = []
    for bucket in sorted(points_by_minute.keys()):
        point = points_by_minute[bucket]
        quality_avg = (
            round(point["quality_sum"] / point["quality_count"], 3)
            if point["quality_count"]
            else 0.0
        )
        timeseries.append(
            {
                "time": bucket,
                "requests": int(point["requests"]),
                "errors": int(point["errors"]),
                "cost_usd": round(point["cost_usd"], 6),
                "tokens_in": int(point["tokens_in"]),
                "tokens_out": int(point["tokens_out"]),
                "quality_avg": quality_avg,
            }
        )

    error_breakdown = dict(Counter(rec.get("error_type", "Unknown") for rec in error_logs))
    total_requests = len(response_logs) + len(error_logs)
    error_rate_pct = round((len(error_logs) / total_requests) * 100, 2) if total_requests else 0.0
    qps = round(len(response_logs) / max(window_minutes * 60, 1), 4)

    slo_data = _parse_simple_yaml(SLO_PATH).get("slis", {})
    slo_status = check_slo_status()
    alert_rules = _parse_simple_yaml(ALERT_RULES_PATH).get("alerts", [])
    incidents = json.loads(INCIDENTS_PATH.read_text(encoding="utf-8")) if INCIDENTS_PATH.exists() else {}
    evidence_items = _read_evidence_items(EVIDENCE_PATH)

    recent_request_logs = [
        {
            "ts": rec.get("ts"),
            "event": rec.get("event"),
            "correlation_id": rec.get("correlation_id"),
            "feature": rec.get("feature"),
            "latency_ms": rec.get("latency_ms"),
            "payload": rec.get("payload"),
        }
        for rec in recent_logs[-8:]
    ]

    pii_samples = []
    for rec in recent_logs:
        payload = rec.get("payload") or {}
        preview = payload.get("message_preview") or payload.get("detail") or payload.get("answer_preview")
        if isinstance(preview, str) and "[REDACTED_" in preview:
            pii_samples.append(
                {
                    "ts": rec.get("ts"),
                    "event": rec.get("event"),
                    "correlation_id": rec.get("correlation_id"),
                    "preview": preview,
                }
            )
        if len(pii_samples) == 3:
            break

    return {
        "generated_at": now.isoformat(),
        "window_minutes": window_minutes,
        "overview": {
            "total_requests": total_requests,
            "successful_requests": len(response_logs),
            "failed_requests": len(error_logs),
            "qps": qps,
            "error_rate_pct": error_rate_pct,
            "latency_p50": percentile(latencies, 50),
            "latency_p95": percentile(latencies, 95),
            "latency_p99": percentile(latencies, 99),
            "total_cost_usd": round(sum(costs), 6),
            "avg_cost_usd": round(mean(costs), 6) if costs else 0.0,
            "tokens_in_total": sum(int(rec.get("tokens_in", 0)) for rec in response_logs),
            "tokens_out_total": sum(int(rec.get("tokens_out", 0)) for rec in response_logs),
            "quality_avg": round(mean(quality_scores), 3) if quality_scores else 0.0,
        },
        "timeseries": timeseries,
        "error_breakdown": error_breakdown,
        "slo": slo_data,
        "slo_report": slo_status,
        "alert_rules": alert_rules,
        "incidents": incidents,
        "evidence_checklist": evidence_items,
        "recent_logs": recent_request_logs,
        "pii_samples": pii_samples,
    }

