"""Wrapper around the official Opinion SDK client."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from opinion_clob_sdk import Client as OpinionSDKClient
from opinion_clob_sdk.chain.py_order_utils.model.order import PlaceOrderDataInput
from opinion_clob_sdk.chain.py_order_utils.model.order_type import LIMIT_ORDER
from opinion_clob_sdk.chain.py_order_utils.model.sides import OrderSide

from ..config.schema import APIConfig


@dataclass
class OrderPlacementResult:
    order_id: str
    payload: Dict[str, Any]


class OpinionClient:
    """Convenience wrapper to keep SDK specifics isolated."""

    def __init__(self, api_config: APIConfig) -> None:
        self._client = OpinionSDKClient(
            host=api_config.host,
            apikey=api_config.api_key,
            chain_id=api_config.chain_id,
            rpc_url=api_config.rpc_url,
            private_key=api_config.private_key,
            multi_sig_addr=api_config.multi_sig_addr,
        )

    def fetch_active_markets(self, limit: int = 20) -> Iterable[Dict[str, Any]]:
        page = 1
        while True:
            response = self._client.get_markets(page=page, limit=limit)
            if response.errno != 0:
                raise RuntimeError(f"Failed to fetch markets: {response.errmsg}")
            markets = response.result.list or []
            if not markets:
                break
            for market in markets:
                if market.get("status") == 2:  # ACTIVATED
                    yield market
            if len(markets) < limit:
                break
            page += 1

    def fetch_orderbook(self, token_id: str) -> Dict[str, Any]:
        response = self._client.get_orderbook(token_id=token_id)
        if response.errno != 0:
            raise RuntimeError(f"Failed to fetch orderbook for {token_id}: {response.errmsg}")
        return response.result.data or {}

    def fetch_latest_price(self, token_id: str) -> Optional[Decimal]:
        response = self._client.get_latest_price(token_id=token_id)
        if response.errno != 0:
            return None
        data = response.result.data
        if not data:
            return None
        price = data.get("price")
        return Decimal(str(price)) if price is not None else None

    def fetch_positions(self, limit: int = 100) -> List[Dict[str, Any]]:
        response = self._client.get_my_positions(limit=limit)
        if response.errno != 0:
            raise RuntimeError(f"Failed to fetch positions: {response.errmsg}")
        return response.result.list or []

    def fetch_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        response = self._client.get_my_orders(limit=limit, status="open")
        if response.errno != 0:
            raise RuntimeError(f"Failed to fetch orders: {response.errmsg}")
        return response.result.list or []

    def fetch_balances(self) -> Dict[str, Any]:
        response = self._client.get_my_balances()
        if response.errno != 0:
            raise RuntimeError(f"Failed to fetch balances: {response.errmsg}")
        return response.result.data or {}

    def place_limit_order(
        self,
        *,
        market_id: int,
        token_id: str,
        side: str,
        price: str,
        amount_in_quote: Optional[str] = None,
        amount_in_base: Optional[str] = None,
    ) -> OrderPlacementResult:
        if bool(amount_in_quote) == bool(amount_in_base):
            raise ValueError("Exactly one of amount_in_quote or amount_in_base must be provided")

        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        order = PlaceOrderDataInput(
            marketId=market_id,
            tokenId=token_id,
            side=side_enum,
            orderType=LIMIT_ORDER,
            price=price,
            makerAmountInQuoteToken=amount_in_quote,
            makerAmountInBaseToken=amount_in_base,
        )
        response = self._client.place_order(order)
        if response.errno != 0:
            raise RuntimeError(f"Order placement failed: {response.errmsg}")
        data = response.result.data or {}
        return OrderPlacementResult(order_id=data.get("order_id", ""), payload=data)

    def cancel_order(self, order_id: str) -> None:
        response = self._client.cancel_order(order_id=order_id)
        if response.errno != 0:
            raise RuntimeError(f"Failed to cancel order {order_id}: {response.errmsg}")

