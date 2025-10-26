"""Tests for candidate generation logic."""

from __future__ import annotations

from decimal import Decimal

from opinion_spread.config.schema import StrategyConfig
from opinion_spread.models.core import AccountState, OpenOrder, OrderCandidate, Position, TokenMetrics
from opinion_spread.strategy.candidates import CandidateBuilder
from opinion_spread.utils.decimal_utils import to_decimal


def make_account(positions=None, open_orders=None) -> AccountState:
    positions = positions or []
    open_orders = open_orders or []
    return AccountState(
        total_balances={"USDT": Decimal("100")},
        available_balances={"USDT": Decimal("100")},
        positions=positions,
        open_orders=open_orders,
    )


def test_candidate_skips_tokens_with_existing_positions() -> None:
    builder = CandidateBuilder(StrategyConfig(order_quote_amount=10))
    metrics = [
        TokenMetrics(
            token_id="token-yes",
            market_id=1,
            side="yes",
            best_bid=None,
            best_ask=None,
            spread=None,
            liquidity_score=Decimal("20"),
        )
    ]
    account = make_account(
        positions=[
            Position(
                market_id=1,
                token_id="token-yes",
                outcome_side="yes",
                shares=Decimal("5"),
                average_price=Decimal("0.5"),
            )
        ]
    )

    candidates = builder.build_buy_candidates(metrics, account)
    assert not candidates


def test_candidate_builds_orders_with_quote_amount() -> None:
    builder = CandidateBuilder(StrategyConfig(order_quote_amount=Decimal("20")))
    metrics = [
        TokenMetrics(
            token_id="token-yes",
            market_id=1,
            side="yes",
            best_bid=type("L", (), {"price": Decimal("0.4"), "size": Decimal("10")})(),
            best_ask=type("L", (), {"price": Decimal("0.45"), "size": Decimal("10")})(),
            spread=Decimal("0.05"),
            liquidity_score=Decimal("10"),
        )
    ]
    account = make_account()

    candidates = builder.build_buy_candidates(metrics, account)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.quote_amount == Decimal("20")
    assert candidate.base_amount > 0
    assert candidate.price == Decimal("0.4")
