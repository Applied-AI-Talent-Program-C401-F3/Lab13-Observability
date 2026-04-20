import yaml
import re
from .metrics import snapshot
from .logging_config import get_logger

log = get_logger()

ALERT_RULES_PATH = "config/alert_rules.yaml"
ACTIVE_ALERTS = set()

def load_rules():
    try:
        with open(ALERT_RULES_PATH, "r") as f:
            return yaml.safe_load(f).get("alerts", [])
    except Exception as e:
        log.error("failed_to_load_alert_rules", error=str(e))
        return []

def evaluate_condition(condition: str, stats: dict) -> bool:
    # Basic parser for "metric > value" or "metric < value"
    # Example: "latency_p95_ms > 5000 for 30m"
    # We focus on the numeric comparison part
    match = re.search(r"(\w+)\s*([><=]+)\s*([\d.]+)", condition)
    if not match:
        return False
    
    metric_name, operator, threshold = match.groups()
    # Normalize metric name (mapping YAML names to snapshot names)
    metric_map = {
        "latency_p95_ms": "latency_p95",
        "error_rate_pct": "error_rate_pct",
        "hourly_cost_usd": "total_cost_usd" # simplified
    }
    
    actual_name = metric_map.get(metric_name, metric_name)
    actual_value = stats.get(actual_name)
    
    if actual_value is None:
        return False
    
    threshold = float(threshold)
    if operator == ">":
        return actual_value > threshold
    elif operator == "<":
        return actual_value < threshold
    elif operator == ">=":
        return actual_value >= threshold
    elif operator == "<=":
        return actual_value <= threshold
    
    return False

def check_alerts():
    rules = load_rules()
    stats = snapshot()
    
    for rule in rules:
        name = rule["name"]
        is_firing = evaluate_condition(rule["condition"], stats)
        
        if is_firing and name not in ACTIVE_ALERTS:
            ACTIVE_ALERTS.add(name)
            
            # Map the correct value for the log output
            val_map = {
                "high_latency_p95": stats.get("latency_p95"),
                "high_error_rate": stats.get("error_rate_pct"),
                "cost_budget_spike": stats.get("total_cost_usd")
            }
            
            log.critical(
                "alert_triggered",
                alert_name=name,
                severity=rule["severity"],
                condition=rule["condition"],
                actual_value=val_map.get(name),
                payload={"stats": stats}
            )
        elif not is_firing and name in ACTIVE_ALERTS:
            ACTIVE_ALERTS.remove(name)
            log.info(
                "alert_resolved",
                alert_name=name,
                payload={"stats": stats}
            )
