"""Configuration loading utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .schema import APIConfig, Config, LoggingConfig, MonitoringConfig, RiskConfig, SchedulerConfig, StrategyConfig


ENV_PREFIX = "OPINION_SPREAD"


def _load_yaml_config(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    if not isinstance(data, dict):
        raise ValueError("Configuration file must contain a mapping at the root level")
    return data


def _env_key(section: str, field: str) -> str:
    return f"{ENV_PREFIX}_{section}_{field}".upper()


def _apply_env_overrides(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}

    def set_override(section: str, field: str, cast=str):
        env_name = _env_key(section, field)
        value = os.getenv(env_name)
        if value is None:
            return
        try:
            overrides.setdefault(section, {})[field] = cast(value)
        except ValueError as exc:
            raise ValueError(f"Invalid value for environment variable {env_name}: {value}") from exc

    # API credentials
    for key in ("host", "api_key", "rpc_url", "private_key", "multi_sig_addr"):
        set_override("api", key)
    set_override("api", "chain_id", int)

    # Strategy
    set_override("strategy", "top_n_tokens", int)
    set_override("strategy", "min_liquidity", float)
    set_override("strategy", "max_spread", float)
    set_override("strategy", "min_price", float)
    set_override("strategy", "max_price", float)

    # Risk
    set_override("risk", "max_total_position", float)
    set_override("risk", "max_position_per_market", float)
    set_override("risk", "min_available_balance", float)
    set_override("risk", "duplicate_order_cooldown", int)
    set_override("risk", "sell_order_threshold", float)

    # Scheduler
    set_override("scheduler", "poll_interval_seconds", float)
    set_override("scheduler", "order_refresh_interval", float)

    # Logging
    set_override("logging", "level")
    set_override("logging", "log_to_console", lambda v: v.lower() in {"1", "true", "yes"})
    set_override("logging", "log_to_file", lambda v: v.lower() in {"1", "true", "yes"})
    set_override("logging", "log_file")
    set_override("logging", "json_format", lambda v: v.lower() in {"1", "true", "yes"})

    # Monitoring
    set_override("monitoring", "enable_metrics", lambda v: v.lower() in {"1", "true", "yes"})
    set_override("monitoring", "metrics_backend")

    value = os.getenv(f"{ENV_PREFIX}_ENABLED_MARKETS")
    if value:
        overrides["enabled_markets"] = [int(i.strip()) for i in value.split(",") if i.strip()]

    def merge(d: Dict[str, Any], o: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in o.items():
            if isinstance(value, dict):
                d[key] = merge(d.get(key, {}), value)
            else:
                d[key] = value
        return d

    return merge(config_dict.copy(), overrides)


def _build_config(data: Dict[str, Any]) -> Config:
    api_data = data.get("api") or {}
    missing_api_fields = {k for k in ("host", "api_key", "chain_id", "rpc_url", "private_key", "multi_sig_addr") if k not in api_data}
    if missing_api_fields:
        raise KeyError(f"Missing required API configuration fields: {sorted(missing_api_fields)}")
    api_cfg = APIConfig(**api_data)

    strategy_cfg = StrategyConfig(**data.get("strategy", {}))
    risk_cfg = RiskConfig(**data.get("risk", {}))
    scheduler_cfg = SchedulerConfig(**data.get("scheduler", {}))
    logging_cfg = LoggingConfig(**data.get("logging", {}))
    monitoring_cfg = MonitoringConfig(**data.get("monitoring", {}))

    enabled_markets_raw = data.get("enabled_markets")
    if isinstance(enabled_markets_raw, str):
        enabled_markets = [int(i.strip()) for i in enabled_markets_raw.split(",") if i.strip()]
    elif isinstance(enabled_markets_raw, list):
        enabled_markets = [int(i) for i in enabled_markets_raw]
    else:
        enabled_markets = None

    return Config(
        api=api_cfg,
        strategy=strategy_cfg,
        risk=risk_cfg,
        scheduler=scheduler_cfg,
        logging=logging_cfg,
        monitoring=monitoring_cfg,
        enabled_markets=enabled_markets,
    )


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML and environment variables."""

    path = Path(config_path) if config_path else None
    config_dict = _load_yaml_config(path)
    config_dict = _apply_env_overrides(config_dict)
    return _build_config(config_dict)

