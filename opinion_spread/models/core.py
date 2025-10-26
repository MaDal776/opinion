"""Core data models for the opinion spread strategy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class Market:
    market_id: int
    title: str
    status: int
    yes_token: str
    no_token: str
    volume: Decimal
    quote_token: str


@dataclass
class OrderbookLevel:
    price: Decimal
    size: Decimal


@dataclass
class OrderbookSnapshot:
    token_id: str
    bids: List[OrderbookLevel]
    asks: List[OrderbookLevel]

    def best_bid(self) -> Optional[OrderbookLevel]:
        return self.bids[0] if self.bids else None

    def best_ask(self) -> Optional[OrderbookLevel]:
        return self.asks[0] if self.asks else None


@dataclass
class TokenMetrics:
    token_id: str
    market_id: int
    side: str  # "yes" or "no"
    best_bid: Optional[OrderbookLevel]
    best_ask: Optional[OrderbookLevel]
    spread: Optional[Decimal]
    liquidity_score: Decimal


@dataclass
class Position:
    market_id: int
    token_id: str
    outcome_side: str
    shares: Decimal
    average_price: Optional[Decimal]


@dataclass
class OpenOrder:
    order_id: str
    market_id: int
    token_id: str
    side: str
    price: Decimal
    remaining: Decimal


@dataclass
class AccountState:
    total_balances: Dict[str, Decimal]
    available_balances: Dict[str, Decimal]
    positions: List[Position]
    open_orders: List[OpenOrder]


@dataclass
class OrderCandidate:
    market_id: int
    token_id: str
    side: str
    price: Decimal
    quote_amount: Decimal
    base_amount: Decimal
