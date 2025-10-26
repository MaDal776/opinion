"""Dump all market data with associated orderbooks and price snapshots."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

from dotenv import load_dotenv

from opinion_spread.clients._response_utils import normalize
from opinion_spread.clients.read_only_client import OpinionReadOnlyClient, ReadOnlyConfig


def _build_token_snapshot(client: OpinionReadOnlyClient, token_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token_id:
        return None
    orderbook = client.get_orderbook(token_id)
    latest_price = client.get_latest_price(token_id)
    history = client.get_price_history(token_id, interval="1h")
    return {
        "token_id": token_id,
        "orderbook": orderbook,
        "latest_price": str(latest_price) if latest_price is not None else None,
        "history": history,
    }


def _dump_raw_orderbook(client: OpinionReadOnlyClient, token_id: str, label: str) -> None:
    try:
        response = client._client.get_orderbook(token_id=token_id)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover
        print(f"    [raw] Failed to fetch raw orderbook for {label}: {exc}")
        return
    raw_payload = getattr(getattr(response, "result", None), "data", None)
    normalized = normalize(raw_payload)
    print(f"    [raw] Payload type: {type(raw_payload)}")
    print(f"    [raw] Normalized keys: {list(normalized.keys()) if isinstance(normalized, dict) else type(normalized)}")
    if isinstance(normalized, dict):
        bids = normalized.get("bids")
        asks = normalized.get("asks")
        print(f"    [raw] bids sample: {bids[:3] if isinstance(bids, list) else bids}")
        print(f"    [raw] asks sample: {asks[:3] if isinstance(asks, list) else asks}")


def main() -> None:
    load_dotenv()

    host = os.getenv("OPINION_API_HOST", "https://proxy.opinion.trade:8443")
    api_key = os.getenv("OPINION_API_KEY")

    if not api_key:
        raise SystemExit("OPINION_API_KEY environment variable missing.")

    config = ReadOnlyConfig(host=host, api_key=api_key)
    client = OpinionReadOnlyClient(config)

    target_market_ids = os.getenv("MARKET_IDS")
    show_raw_market = os.getenv("SHOW_RAW_MARKET", "0").lower() in {"1", "true", "yes"}
    if target_market_ids:
        ids = [int(mid.strip()) for mid in target_market_ids.split(",") if mid.strip()]
        markets: Iterable[Dict[str, Any]] = (
            client.get_market(market_id) | {"market_id": market_id}
            for market_id in ids
        )
    else:
        markets = client.iter_all_markets(page_size=20)

    total = 0
    for market in markets:
        total += 1
        market_id = market.get("market_id")
        raw_market_response = None
        if target_market_ids:
            detail = market
            title = market.get("market_title")
            if show_raw_market:
                raw_market_response = normalize(client.get_market_raw(int(market_id)))
        else:
            title = market.get("market_title")
            detail = client.get_market(int(market_id))
            if show_raw_market:
                raw_market_response = normalize(client.get_market_raw(int(market_id)))

        detail_normalized = normalize(detail)
        volume = detail_normalized.get("volume")
        liquidity = detail_normalized.get("liquidity")
        volume24h = detail_normalized.get("volume24h") or detail_normalized.get("vol24h")
        fee_rate = detail_normalized.get("feeRate")
        yes_label = detail_normalized.get("yesLabel") or detail_normalized.get("yes_label")
        no_label = detail_normalized.get("noLabel") or detail_normalized.get("no_label")
        quote_token = detail_normalized.get("quoteToken")
        market_type = detail_normalized.get("marketType") or detail_normalized.get("topicType")
        volume_quote = detail_normalized.get("volumeQuoteToken")

        yes_snapshot = _build_token_snapshot(client, detail.get("yes_token_id"))
        no_snapshot = _build_token_snapshot(client, detail.get("no_token_id"))

        print(f"Market {market_id}: {title}")
        print(f"  Status: {detail.get('status')} | Type: {market_type} | Cutoff: {detail.get('cutoff_at')}")
        print(f"  Quote token: {quote_token} | Fee rate: {fee_rate}")
        print(f"  Volume total: {volume} | Volume 24h: {volume24h} | Volume quote token: {volume_quote}")
        print(f"  Liquidity: {liquidity} | YES label: {yes_label} | NO label: {no_label}")
        if show_raw_market:
            print("  Raw market detail:")
            print(detail_normalized)
            if raw_market_response is not None:
                print("  Raw market response body:")
                print(raw_market_response)

        for label, snapshot in ("YES", yes_snapshot), ("NO", no_snapshot):
            if not snapshot:
                print(f"  {label} token unavailable")
                continue
            bids = snapshot["orderbook"].get("bids", [])
            asks = snapshot["orderbook"].get("asks", [])
            print(f"  {label} token: {snapshot['token_id']}")
            print(f"    Bids ({len(bids)}): {bids[:3]}")
            print(f"    Asks ({len(asks)}): {asks[:3]}")
            print(f"    Latest price: {snapshot['latest_price']}")
            # print(f"    History points: {len(snapshot['history'])}")
            # if snapshot["history"]:
            #     print(f"    History sample: {snapshot['history'][:3]}")
            _dump_raw_orderbook(client, snapshot["token_id"], label)
        print("-" * 80)

    print(f"Total markets processed: {total}")


if __name__ == "__main__":
    main()
