"""Read-only Opinion API client for safe data retrieval tests."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

try:
    from opinion_clob_sdk import Client as OpinionSDKClient
except ImportError:  # pragma: no cover - handled for test environments without SDK
    OpinionSDKClient = None  # type: ignore[assignment]


_DEFAULT_PRIVATE_KEY = "0x" + "0" * 64
_DEFAULT_MULTISIG = "0x0000000000000000000000000000000000000000"

from ._response_utils import extract_data, extract_list, normalize  # noqa: E402


@dataclass(frozen=True)
class ReadOnlyConfig:
    host: str
    api_key: str
    chain_id: int = 56
    rpc_url: str = ""
    private_key: str = _DEFAULT_PRIVATE_KEY
    multi_sig_addr: str = _DEFAULT_MULTISIG


class OpinionReadOnlyClient:
    """Thin wrapper around SDK Client exposing read-only methods only."""

    def __init__(self, config: ReadOnlyConfig) -> None:
        if OpinionSDKClient is None:
            raise ImportError(
                "opinion_clob_sdk is required for OpinionReadOnlyClient. "
                "Install it via 'pip install opinion-clob-sdk' or provide a mock in tests."
            )
        self._client = OpinionSDKClient(
            host=config.host,
            apikey=config.api_key,
            chain_id=config.chain_id,
            rpc_url=config.rpc_url,
            private_key=config.private_key or _DEFAULT_PRIVATE_KEY,
            multi_sig_addr=config.multi_sig_addr or _DEFAULT_MULTISIG,
        )

    def get_markets(self, **kwargs: Any) -> List[Dict[str, Any]]:
        return extract_list(self._client.get_markets(**kwargs))

    def iter_all_markets(self, *, page_size: int = 20, **kwargs: Any) -> Iterable[Dict[str, Any]]:
        page = 1
        while True:
            response = self._client.get_markets(page=page, limit=page_size, **kwargs)
            markets = extract_list(response)
            if not markets:
                break
            for market in markets:
                yield market
            if len(markets) < page_size:
                break
            page += 1

    def get_market(self, market_id: int, *, use_cache: bool = True) -> Dict[str, Any]:
        return extract_data(self._client.get_market(market_id=market_id, use_cache=use_cache))

    def get_market_raw(self, market_id: int, *, use_cache: bool = True) -> Any:
        return self._client.get_market(market_id=market_id, use_cache=use_cache)

    def get_quote_tokens(self, *, use_cache: bool = True) -> List[Dict[str, Any]]:
        return extract_list(self._client.get_quote_tokens(use_cache=use_cache))

    def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        return extract_data(self._client.get_orderbook(token_id=token_id))

    def get_latest_price(self, token_id: str) -> Optional[Decimal]:
        response = self._client.get_latest_price(token_id=token_id)
        if response.errno != 0:
            return None
        data = normalize(response.result.data)
        price = data.get("price") if isinstance(data, dict) else None
        return Decimal(str(price)) if price is not None else None

    def get_price_history(self, token_id: str, **kwargs: Any) -> List[Dict[str, Any]]:
        limit = kwargs.pop("limit", None)
        candles = extract_list(self._client.get_price_history(token_id=token_id, **kwargs))
        if limit is not None:
            return candles[: int(limit)]
        return candles

    def get_fee_rates(self, token_id: str) -> Dict[str, Any]:
        return extract_data(self._client.get_fee_rates(token_id=token_id))
