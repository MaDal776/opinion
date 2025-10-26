"""Order execution and management."""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from ..clients.opinion_client import OpinionClient
from ..config.schema import RiskConfig, StrategyConfig
from ..logging_utils.logger import get_logger, log_with_context
from ..models.core import AccountState, OpenOrder, OrderCandidate
from ..risk.checks import RiskDecision, RiskManager, RiskViolation
from ..utils.decimal_utils import format_decimal


class OrderExecutor:
    def __init__(self, client: OpinionClient, strategy_config: StrategyConfig, risk_manager: RiskManager):
        self._client = client
        self._strategy_config = strategy_config
        self._risk_manager = risk_manager
        self._logger = get_logger()

    def submit_buy_order(self, candidate: OrderCandidate) -> bool:
        try:
            decision = self._risk_manager.evaluate(candidate)
        except RiskViolation as exc:
            log_with_context(
                self._logger,
                level=20,
                message="Risk violation for buy order",
                reason=str(exc),
                market_id=candidate.market_id,
                token_id=candidate.token_id,
            )
            return False

        quote_amount_str = format_decimal(candidate.quote_amount)
        log_with_context(
            self._logger,
            level=20,
            message="Submitting buy limit order",
            market_id=candidate.market_id,
            token_id=candidate.token_id,
            price=str(candidate.price),
            quote_amount=quote_amount_str,
        )

        try:
            result = self._client.place_limit_order(
                market_id=candidate.market_id,
                token_id=candidate.token_id,
                side="buy",
                price=str(candidate.price),
                amount_in_quote=quote_amount_str,
            )
        except Exception as exc:  # noqa: BLE001
            log_with_context(
                self._logger,
                level=40,
                message="Failed to place buy order",
                error=str(exc),
                market_id=candidate.market_id,
                token_id=candidate.token_id,
            )
            return False

        self._risk_manager.commit(decision)
        log_with_context(
            self._logger,
            level=20,
            message="Buy order placed",
            market_id=candidate.market_id,
            token_id=candidate.token_id,
            order_id=result.order_id,
        )
        return True

    def submit_sell_order(self, candidate: OrderCandidate) -> bool:
        try:
            decision = self._risk_manager.evaluate(candidate)
        except RiskViolation as exc:
            log_with_context(
                self._logger,
                level=20,
                message="Risk violation for sell order",
                reason=str(exc),
                market_id=candidate.market_id,
                token_id=candidate.token_id,
            )
            return False

        quote_amount_str = format_decimal(candidate.quote_amount)
        log_with_context(
            self._logger,
            level=20,
            message="Submitting sell limit order",
            market_id=candidate.market_id,
            token_id=candidate.token_id,
            price=str(candidate.price),
            quote_amount=quote_amount_str,
        )
        try:
            result = self._client.place_limit_order(
                market_id=candidate.market_id,
                token_id=candidate.token_id,
                side="sell",
                price=str(candidate.price),
                amount_in_base=format_decimal(candidate.base_amount),
            )
        except Exception as exc:  # noqa: BLE001
            log_with_context(
                self._logger,
                level=40,
                message="Failed to place sell order",
                error=str(exc),
                market_id=candidate.market_id,
                token_id=candidate.token_id,
            )
            return False

        self._risk_manager.commit(decision)
        log_with_context(
            self._logger,
            level=20,
            message="Sell order placed",
            market_id=candidate.market_id,
            token_id=candidate.token_id,
            order_id=result.order_id,
        )
        return True


class SellOrderManager:
    def __init__(self, client: OpinionClient, risk_manager: RiskManager, risk_config: RiskConfig):
        self._client = client
        self._risk_manager = risk_manager
        self._risk_config = risk_config
        self._logger = get_logger()

    def manage(self, account: AccountState) -> Dict[str, float]:
        summary: Dict[str, float] = {
            "sell_orders_considered": 0.0,
            "sell_orders_blocked": 0.0,
            "sell_orders_failed": 0.0,
            "sell_orders_success": 0.0,
        }

        grouped_orders: dict[int, List[OpenOrder]] = {}
        for order in account.open_orders:
            if order.side.lower() != "sell":
                continue
            grouped_orders.setdefault(order.market_id, []).append(order)

        for position in account.positions:
            existing_sell_orders = grouped_orders.get(position.market_id, [])
            total_sell_size = sum(order.remaining for order in existing_sell_orders)
            diff = position.shares - total_sell_size
            if diff <= Decimal(str(self._risk_config.sell_order_threshold)):
                continue

            summary["sell_orders_considered"] += 1.0
            candidate = OrderCandidate(
                market_id=position.market_id,
                token_id=position.token_id,
                side="sell",
                price=Decimal("0"),
                quote_amount=Decimal("0"),
                base_amount=diff,
            )
            orderbook = self._client.fetch_orderbook(position.token_id)
            asks = orderbook.get("asks", [])
            if not asks:
                summary["sell_orders_failed"] += 1.0
                continue
            best_ask = asks[0]
            price = Decimal(str(best_ask.get("price", "0")))
            candidate.price = price
            candidate.quote_amount = price * diff
            candidate.base_amount = diff
            try:
                decision = self._risk_manager.evaluate(candidate)
            except RiskViolation as exc:
                log_with_context(
                    self._logger,
                    level=20,
                    message="Sell order blocked by risk manager",
                    reason=str(exc),
                    market_id=position.market_id,
                    token_id=position.token_id,
                )
                summary["sell_orders_blocked"] += 1.0
                continue

            try:
                result = self._client.place_limit_order(
                    market_id=position.market_id,
                    token_id=position.token_id,
                    side="sell",
                    price=str(price),
                    amount_in_base=format_decimal(diff),
                )
            except Exception as exc:  # noqa: BLE001
                log_with_context(
                    self._logger,
                    level=40,
                    message="Failed to place auto sell order",
                    error=str(exc),
                    market_id=position.market_id,
                    token_id=position.token_id,
                )
                summary["sell_orders_failed"] += 1.0
                continue

            self._risk_manager.commit(decision)
            log_with_context(
                self._logger,
                level=20,
                message="Auto sell order placed",
                market_id=position.market_id,
                token_id=position.token_id,
                order_id=result.order_id,
                size=format_decimal(diff),
            )
            summary["sell_orders_success"] += 1.0

        return summary
