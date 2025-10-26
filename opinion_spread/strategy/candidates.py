"""Candidate generation for trading strategy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List, Set

from ..config.schema import StrategyConfig
from ..models.core import AccountState, OrderCandidate, OpenOrder, Position, TokenMetrics
from ..utils.decimal_utils import format_decimal, quantize_down


@dataclass
class CandidateBuilder:
    config: StrategyConfig

    def _has_open_buy_order(self, token_id: str, open_orders: Iterable[OpenOrder]) -> bool:
        for order in open_orders:
            if order.token_id == token_id and order.side.lower() == "buy":
                return True
        return False

    def _positions_by_token(self, positions: Iterable[Position]) -> Set[str]:
        return {position.token_id for position in positions if position.shares > 0}

    def build_buy_candidates(self, metrics: Iterable[TokenMetrics], account: AccountState) -> List[OrderCandidate]:
        candidates: List[OrderCandidate] = []
        open_buy_exists = {order.token_id for order in account.open_orders if order.side.lower() == "buy"}
        positions_tokens = self._positions_by_token(account.positions)

        quote_amount = Decimal(str(self.config.order_quote_amount))
        if quote_amount <= 0:
            return candidates

        for metric in metrics:
            if metric.best_bid is None or metric.best_ask is None:
                continue
            if metric.token_id in open_buy_exists:
                continue
            if metric.token_id in positions_tokens:
                continue
            price = metric.best_bid.price
            if price <= 0:
                continue
            base_amount = quantize_down(quote_amount / price)
            if base_amount <= 0:
                continue
            candidate = OrderCandidate(
                market_id=metric.market_id,
                token_id=metric.token_id,
                side="buy",
                price=price,
                quote_amount=quote_amount,
                base_amount=base_amount,
            )
            candidates.append(candidate)
        return candidates
