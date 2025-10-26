"""Quick script to verify read-only data access to the Opinion API."""

from __future__ import annotations

import os
from decimal import Decimal

from dotenv import load_dotenv

from opinion_spread.clients.read_only_client import OpinionReadOnlyClient, ReadOnlyConfig


def main() -> None:
    load_dotenv()

    host = os.getenv("OPINION_API_HOST", "https://proxy.opinion.trade:8443")
    api_key = os.getenv("OPINION_API_KEY")

    if not api_key:
        raise SystemError(
            "OPINION_API_KEY environment variable missing. Set it before running this script."
        )

    config = ReadOnlyConfig(host=host, api_key=api_key)
    client = OpinionReadOnlyClient(config)

    markets = client.get_markets(limit=5)
    print(f"Fetched {len(markets)} markets\n")
    for market in markets:
        print(f"Market {market.get('market_id')}: {market.get('market_title')}")
    print()

    if not markets:
        print("No markets returned.")
        return

    first_market = markets[0]
    market_id = first_market["market_id"]
    market_detail = client.get_market(market_id)
    yes_token = market_detail.get("yes_token_id")

    print(f"Details for market {market_id}: {list(market_detail.keys())[:8]}\n")

    if yes_token:
        orderbook = client.get_orderbook(yes_token)
        print(f"Orderbook bids (top 3): {orderbook.get('bids', [])[:3]}")
        print(f"Orderbook asks (top 3): {orderbook.get('asks', [])[:3]}")

        latest_price = client.get_latest_price(yes_token)
        if latest_price is not None:
            pct_price = (Decimal(latest_price) * 100).quantize(Decimal("0.01"))
            print(f"Latest YES price: {latest_price} ({pct_price}% probability)")
        else:
            print("Latest price unavailable for YES token")

        history = client.get_price_history(yes_token, interval="1h", limit=5)
        print(f"Recent history candles (up to 5): {history[:5]}")
    else:
        print("Market lacks yes_token_id; skipping orderbook/price checks.")


if __name__ == "__main__":
    main()
