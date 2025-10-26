"""Strategy analysis and token selection logic."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from ..clients.opinion_client import OpinionClient
from ..config.schema import StrategyConfig
from ..models.core import OrderbookLevel, OrderbookSnapshot, TokenMetrics
from ..utils.decimal_utils import safe_div, to_decimal


@dataclass
class MarketTokenInfo:
    market_id: int
    token_id: str
    side: str
    orderbook: OrderbookSnapshot


class SpreadAnalyzer:
    def __init__(self, client: OpinionClient, config: StrategyConfig):
        self._client = client
        self._config = config

    def _build_orderbook(self, token_id: str, data: Dict[str, Iterable[Dict[str, str]]]) -> OrderbookSnapshot:
        bids = [
            OrderbookLevel(price=to_decimal(level["price"]), size=to_decimal(level["size"]))
            for level in data.get("bids", [])
        ]
        asks = [
            OrderbookLevel(price=to_decimal(level["price"]), size=to_decimal(level["size"]))
            for level in data.get("asks", [])
        ]
        return OrderbookSnapshot(token_id=token_id, bids=bids, asks=asks)

    def _calculate_metrics(self, orderbook: OrderbookSnapshot, market_id: int, side: str) -> TokenMetrics:
        best_bid = orderbook.best_bid()
        best_ask = orderbook.best_ask()
        spread: Optional[Decimal] = None
        if best_bid and best_ask:
            spread = best_ask.price - best_bid.price

        liquidity_candidates: List[Decimal] = []
        if best_bid:
            liquidity_candidates.append(best_bid.size)
        if best_ask:
            liquidity_candidates.append(best_ask.size)

        liquidity = min(liquidity_candidates) if liquidity_candidates else Decimal("0")

        return TokenMetrics(
            token_id=orderbook.token_id,
            market_id=market_id,
            side=side,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            liquidity_score=liquidity,
        )

    def analyze_market(self, market: Dict[str, Any]) -> List[TokenMetrics]:
        metrics: List[TokenMetrics] = []
        for side_key in ("yes_token_id", "no_token_id"):
            token_id = market.get(side_key)
            if not token_id:
                continue
            orderbook_data = self._client.fetch_orderbook(token_id)
            orderbook = self._build_orderbook(token_id, orderbook_data)
            side = "yes" if side_key.startswith("yes") else "no"
            metric = self._calculate_metrics(orderbook, int(market.get("market_id")), side)
            metrics.append(metric)
        return metrics

    def select_top_tokens(self, markets: Iterable[Dict[str, Any]]) -> List[TokenMetrics]:
        candidates: List[TokenMetrics] = []
        for market in markets:
            metrics = self.analyze_market(market)
            for metric in metrics:
                if metric.best_bid and metric.best_ask:
                    if metric.liquidity_score < Decimal(str(self._config.min_liquidity)):
                        continue
                    if metric.spread is None or metric.spread > Decimal(str(self._config.max_spread)):
                        continue
                    price_mid = safe_div(metric.best_bid.price + metric.best_ask.price, Decimal("2"))
                    if not (Decimal(str(self._config.min_price)) <= price_mid <= Decimal(str(self._config.max_price))):
                        continue
                    candidates.append(metric)
        candidates.sort(key=lambda m: (m.spread or Decimal("1"), -m.liquidity_score))
        return candidates[: self._config.top_n_tokens]
