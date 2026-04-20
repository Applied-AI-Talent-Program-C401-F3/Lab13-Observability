import yaml
from .metrics import snapshot
from .logging_config import get_logger

log = get_logger()

SLO_CONFIG_PATH = "config/slo.yaml"

def load_slo_config():
    try:
        with open(SLO_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f).get("slis", {})
    except Exception as e:
        log.error("failed_to_load_slo_config", error=str(e))
        return {}

def check_slo_status():
    config = load_slo_config()
    stats = snapshot()
    report = {}

    for sli_name, target_cfg in config.items():
        objective = target_cfg["objective"]
        # Map YAML SLI names to snapshot metric names
        metric_map = {
            "latency_p95_ms": "latency_p95",
            "error_rate_pct": "error_rate_pct",
            "daily_cost_usd": "total_cost_usd",
            "quality_score_avg": "quality_avg"
        }
        
        actual_metric = metric_map.get(sli_name, sli_name)
        actual_value = stats.get(actual_metric, 0.0)
        
        # Logic: For latency, error, and cost, "lower is better"
        # For quality, "higher is better"
        if sli_name == "quality_score_avg":
            is_compliant = actual_value >= objective
        else:
            is_compliant = actual_value <= objective

        report[sli_name] = {
            "status": "✅ COMPLIANT" if is_compliant else "❌ BREACHED",
            "objective": objective,
            "actual": actual_value,
            "target_attainment": target_cfg["target"]
        }
        
    return report
