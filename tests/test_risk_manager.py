"""Tests for the RiskManager logic."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from opinion_spread.config.schema import RiskConfig
from opinion_spread.models.core import AccountState, OpenOrder, OrderCandidate, Position
from opinion_spread.risk.checks import RiskDecision, RiskManager, RiskViolation


@pytest.fixture
def risk_config() -> RiskConfig:
    return RiskConfig(
        max_total_position=100,
        max_position_per_market=50,
        min_available_balance=10,
        duplicate_order_cooldown=60,
        sell_order_threshold=5,
    )


def make_account(total_balance: Decimal = Decimal("100"), positions=None, open_orders=None) -> AccountState:
    positions = positions or []
    open_orders = open_orders or []
    return AccountState(
        total_balances={"USDT": total_balance},
        available_balances={"USDT": total_balance},
        positions=positions,
        open_orders=open_orders,
    )


def test_buy_order_exceeds_total_position(risk_config: RiskConfig) -> None:
    manager = RiskManager(risk_config)
    account = make_account()
    manager.reset(account)

    candidate = OrderCandidate(
        market_id=1,
        token_id="token-1",
        side="buy",
        price=Decimal("0.5"),
        quote_amount=Decimal("120"),
        base_amount=Decimal("240"),
    )

    with pytest.raises(RiskViolation):
        manager.evaluate(candidate)


def test_duplicate_order_cooldown(risk_config: RiskConfig) -> None:
    manager = RiskManager(risk_config)
    account = make_account()
    manager.reset(account)

    candidate = OrderCandidate(
        market_id=1,
        token_id="token-1",
        side="buy",
        price=Decimal("0.4"),
        quote_amount=Decimal("20"),
        base_amount=Decimal("50"),
    )

    decision = manager.evaluate(candidate)
    manager.commit(decision)

    with pytest.raises(RiskViolation):
        manager.evaluate(candidate)


def test_sell_order_exceeds_market_position(risk_config: RiskConfig) -> None:
    manager = RiskManager(risk_config)
    account = make_account(
        positions=[
            Position(
                market_id=1,
                token_id="token-1",
                outcome_side="yes",
                shares=Decimal("5"),
                average_price=Decimal("0.5"),
            )
        ]
    )
    manager.reset(account)

    candidate = OrderCandidate(
        market_id=1,
        token_id="token-1",
        side="sell",
        price=Decimal("0.6"),
        quote_amount=Decimal("3"),
        base_amount=Decimal("6"),
    )

    with pytest.raises(RiskViolation):
        manager.evaluate(candidate)


def test_sell_order_within_limits(risk_config: RiskConfig) -> None:
    manager = RiskManager(risk_config)
    account = make_account(
        positions=[
            Position(
                market_id=1,
                token_id="token-1",
                outcome_side="yes",
                shares=Decimal("10"),
                average_price=Decimal("0.5"),
            )
        ]
    )
    manager.reset(account)

    candidate = OrderCandidate(
        market_id=1,
        token_id="token-1",
        side="sell",
        price=Decimal("0.6"),
        quote_amount=Decimal("6"),
        base_amount=Decimal("5"),
    )

    decision = manager.evaluate(candidate)
    manager.commit(decision)

    assert manager._total_position == Decimal("5")  # type: ignore[attr-defined]
    assert manager._position_by_market[candidate.market_id] == Decimal("5")  # type: ignore[attr-defined]
