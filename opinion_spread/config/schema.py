"""Configuration schema definitions for the opinion spread strategy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class APIConfig:
    """API and blockchain connectivity settings."""

    host: str
    api_key: str
    chain_id: int
    rpc_url: str
    private_key: str
    multi_sig_addr: str


@dataclass(frozen=True)
class StrategyConfig:
    """Parameters controlling market selection and filtering."""

    top_n_tokens: int = 50
    min_liquidity: float = 10.0
    max_spread: float = 0.1
    min_price: float = 0.05
    max_price: float = 0.95
    order_quote_amount: float = 20.0


@dataclass(frozen=True)
class RiskConfig:
    """Risk constraints applied before submitting orders."""

    max_total_position: float = 1000.0
    max_position_per_market: float = 200.0
    min_available_balance: float = 20.0
    duplicate_order_cooldown: int = 60
    sell_order_threshold: float = 5.0


@dataclass(frozen=True)
class SchedulerConfig:
    """Main loop and polling behaviour settings."""

    poll_interval_seconds: float = 15.0
    order_refresh_interval: float = 60.0


@dataclass(frozen=True)
class LoggingConfig:
    """Logging output configuration."""

    level: str = "INFO"
    log_to_console: bool = True
    log_to_file: bool = False
    log_file: Optional[str] = None
    json_format: bool = False


@dataclass(frozen=True)
class MonitoringConfig:
    """Monitoring and metrics collection settings."""

    enable_metrics: bool = False
    metrics_backend: Optional[str] = None


@dataclass(frozen=True)
class Config:
    """Root configuration object."""

    api: APIConfig
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    enabled_markets: Optional[List[int]] = None

