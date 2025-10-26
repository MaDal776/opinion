"""Account state management and caching."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List

from ..clients.opinion_client import OpinionClient
from ..models.core import AccountState, OpenOrder, Position
from ..utils.decimal_utils import to_decimal


@dataclass
class AccountCache:
    balances: Dict[str, Decimal]
    available: Dict[str, Decimal]
    positions: List[Position]
    open_orders: List[OpenOrder]


class AccountStateManager:
    def __init__(self, client: OpinionClient):
        self._client = client

    def refresh(self) -> AccountState:
        balances_response = self._client.fetch_balances()
        positions_response = self._client.fetch_positions()
        orders_response = self._client.fetch_orders()

        total_balances: Dict[str, Decimal] = {}
        available_balances: Dict[str, Decimal] = {}

        for item in balances_response.get("balances", []):
            token = item.get("quote_token")
            if not token:
                continue
            total_balances[token] = to_decimal(item.get("total_balance"))
            available_balances[token] = to_decimal(item.get("available_balance"))

        positions: List[Position] = []
        for pos in positions_response:
            token_id = pos.get("token_id")
            if not token_id:
                continue
            positions.append(
                Position(
                    market_id=int(pos.get("market_id")),
                    token_id=token_id,
                    outcome_side=pos.get("outcome_side_enum", ""),
                    shares=to_decimal(pos.get("shares_owned")),
                    average_price=(to_decimal(pos.get("avg_price")) if pos.get("avg_price") else None),
                )
            )

        open_orders: List[OpenOrder] = []
        for order in orders_response:
            token_id = order.get("token_id")
            if not token_id:
                continue
            open_orders.append(
                OpenOrder(
                    order_id=order.get("order_id", ""),
                    market_id=int(order.get("market_id", 0)),
                    token_id=token_id,
                    side=order.get("side", ""),
                    price=to_decimal(order.get("price")),
                    remaining=to_decimal(order.get("maker_amount")),
                )
            )

        return AccountState(
            total_balances=total_balances,
            available_balances=available_balances,
            positions=positions,
            open_orders=open_orders,
        )
