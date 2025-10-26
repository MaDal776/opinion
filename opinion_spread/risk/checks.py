"""Risk management checks for order execution."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional

from ..config.schema import RiskConfig
from ..models.core import AccountState, OrderCandidate


class RiskViolation(Exception):
    """Raised when order placement violates a risk constraint."""


@dataclass(frozen=True)
class RiskDecision:
    candidate: OrderCandidate
    available_quote: Decimal
    total_position: Decimal
    market_position: Decimal
    duplicate_key: str
    timestamp: datetime


class RiskManager:
    def __init__(self, config: RiskConfig):
        self._config = config
        self._last_order_times: Dict[str, datetime] = {}
        self._available_quote: Decimal = Decimal("0")
        self._total_position: Decimal = Decimal("0")
        self._position_by_market: Dict[int, Decimal] = defaultdict(Decimal)
        self._account_snapshot: Optional[AccountState] = None

    def reset(self, account_state: AccountState) -> None:
        """Reset per-iteration aggregates based on the latest account snapshot."""

        self._account_snapshot = account_state
        self._available_quote = account_state.available_balances.get("USDT", Decimal("0"))
        self._total_position = sum(position.shares for position in account_state.positions)
        self._position_by_market = defaultdict(Decimal)
        for position in account_state.positions:
            self._position_by_market[position.market_id] += position.shares

    def _ensure_initialized(self) -> None:
        if self._account_snapshot is None:
            raise RuntimeError("RiskManager.reset must be called before evaluation")

    def evaluate(self, candidate: OrderCandidate) -> RiskDecision:
        self._ensure_initialized()

        cooldown = timedelta(seconds=self._config.duplicate_order_cooldown)
        duplicate_key = f"{candidate.market_id}:{candidate.token_id}:{candidate.side}:{candidate.price}".lower()
        now = datetime.utcnow()
        last_time = self._last_order_times.get(duplicate_key)
        if last_time and now - last_time < cooldown:
            raise RiskViolation("Duplicate order detected within cooldown window")

        available_quote = self._available_quote
        total_position = self._total_position
        market_position = self._position_by_market.get(candidate.market_id, Decimal("0"))

        min_available = Decimal(str(self._config.min_available_balance))
        max_total = Decimal(str(self._config.max_total_position))
        max_market = Decimal(str(self._config.max_position_per_market))

        side = candidate.side.lower()
        if side == "buy":
            quote_amount = candidate.quote_amount
            if quote_amount <= 0:
                raise RiskViolation("Invalid quote amount for buy order")
            if quote_amount > available_quote:
                raise RiskViolation("Quote amount exceeds available balance")
            remaining = available_quote - quote_amount
            if remaining < min_available:
                raise RiskViolation("Insufficient available balance after order")
            available_quote = remaining

            projected_total = total_position + candidate.base_amount
            if projected_total > max_total:
                raise RiskViolation("Total position limit exceeded")
            total_position = projected_total

            projected_market = market_position + candidate.base_amount
            if projected_market > max_market:
                raise RiskViolation("Market position limit exceeded")
            market_position = projected_market

        elif side == "sell":
            if candidate.base_amount > total_position:
                raise RiskViolation("Sell amount exceeds total position")
            total_position = total_position - candidate.base_amount

            if candidate.base_amount > market_position:
                raise RiskViolation("Sell amount exceeds market position")
            market_position = market_position - candidate.base_amount

        else:
            raise RiskViolation(f"Unsupported order side: {candidate.side}")

        return RiskDecision(
            candidate=candidate,
            available_quote=available_quote,
            total_position=total_position,
            market_position=market_position,
            duplicate_key=duplicate_key,
            timestamp=now,
        )

    def commit(self, decision: RiskDecision) -> None:
        self._available_quote = decision.available_quote
        self._total_position = decision.total_position
        if decision.market_position <= 0:
            self._position_by_market.pop(decision.candidate.market_id, None)
        else:
            self._position_by_market[decision.candidate.market_id] = decision.market_position
        self._last_order_times[decision.duplicate_key] = decision.timestamp
