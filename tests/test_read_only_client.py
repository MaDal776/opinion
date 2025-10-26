"""Tests for the read-only Opinion API client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest

from opinion_spread.clients.read_only_client import OpinionReadOnlyClient, ReadOnlyConfig


@dataclass
class DummyResponse:
    errno: int
    result: Any
    errmsg: str | None = None


class DummyResult:
    def __init__(self, data=None, list_=None):
        self.data = data
        self.list = list_


class DummySDKClient:
    def __init__(self) -> None:
        self.get_markets_called = False

    def get_markets(self, **kwargs: Any) -> DummyResponse:
        self.get_markets_called = True
        return DummyResponse(errno=0, result=DummyResult(list_=[{"market_id": 1}]))

    def get_market(self, market_id: int, use_cache: bool = True) -> DummyResponse:
        return DummyResponse(errno=0, result=DummyResult(data={"market_id": market_id}))

    def get_quote_tokens(self, use_cache: bool = True) -> DummyResponse:
        return DummyResponse(errno=0, result=DummyResult(list_=[{"symbol": "USDT"}]))

    def get_orderbook(self, token_id: str) -> DummyResponse:
        return DummyResponse(errno=0, result=DummyResult(data={"token_id": token_id, "bids": []}))

    def get_latest_price(self, token_id: str) -> DummyResponse:
        return DummyResponse(errno=0, result=DummyResult(data={"price": "0.5"}))

    def get_price_history(self, token_id: str, **kwargs: Any) -> DummyResponse:
        return DummyResponse(errno=0, result=DummyResult(list_=[{"close": "0.6"}]))

    def get_fee_rates(self, token_id: str) -> DummyResponse:
        return DummyResponse(errno=0, result=DummyResult(data={"maker_fee": "0.001"}))


@pytest.fixture
def read_only_client(monkeypatch: pytest.MonkeyPatch) -> OpinionReadOnlyClient:
    def _mock_client(*args: Any, **kwargs: Any) -> DummySDKClient:
        return sdk

    sdk = DummySDKClient()
    monkeypatch.setattr("opinion_spread.clients.read_only_client.OpinionSDKClient", _mock_client)
    config = ReadOnlyConfig(host="https://proxy.opinion.trade:8443", api_key="test")
    return OpinionReadOnlyClient(config)


def test_get_markets_returns_list(read_only_client: OpinionReadOnlyClient) -> None:
    markets = list(read_only_client.iter_all_markets())
    assert markets == [{"market_id": 1}]


def test_get_market_returns_dict(read_only_client: OpinionReadOnlyClient) -> None:
    market = read_only_client.get_market(1)
    assert market["market_id"] == 1


def test_latest_price_returns_decimal(read_only_client: OpinionReadOnlyClient) -> None:
    price = read_only_client.get_latest_price("token")
    assert price == Decimal("0.5")


def test_price_history_returns_list(read_only_client: OpinionReadOnlyClient) -> None:
    history = read_only_client.get_price_history("token")
    assert history == [{"close": "0.6"}]


def test_error_raises_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    def _mock_client(*args: Any, **kwargs: Any) -> DummySDKClient:
        return sdk

    class ErrorSDKClient(DummySDKClient):
        def get_markets(self, **kwargs: Any) -> DummyResponse:
            return DummyResponse(errno=400, result=DummyResult())

    sdk = ErrorSDKClient()
    monkeypatch.setattr("opinion_spread.clients.read_only_client.OpinionSDKClient", _mock_client)
    client = OpinionReadOnlyClient(ReadOnlyConfig(host="https://proxy.opinion.trade:8443", api_key="test"))

    with pytest.raises(RuntimeError):
        client.get_markets()
