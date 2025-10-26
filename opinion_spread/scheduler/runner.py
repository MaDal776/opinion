"""Main synchronous scheduler for the trading strategy."""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict

from ..clients.opinion_client import OpinionClient
from ..config.loader import load_config
from ..config.schema import Config
from ..logging_utils.logger import configure_logging, get_logger, log_with_context
from ..monitoring.metrics import MetricsRecorder
from ..risk.checks import RiskManager
from ..state.account import AccountStateManager
from ..models.core import AccountState
from ..strategy.analyzer import SpreadAnalyzer
from ..strategy.candidates import CandidateBuilder
from ..executors.orders import OrderExecutor, SellOrderManager


@dataclass
class TradingContext:
    config: Config
    client: OpinionClient
    account_manager: AccountStateManager
    analyzer: SpreadAnalyzer
    candidate_builder: CandidateBuilder
    risk_manager: RiskManager
    executor: OrderExecutor
    sell_manager: SellOrderManager
    metrics: MetricsRecorder


class TradingScheduler:
    def __init__(self, context: TradingContext):
        self._context = context
        self._logger = get_logger()

    def _log_account_snapshot(self, label: str, account_state: AccountState) -> None:
        total_positions_shares = sum((position.shares for position in account_state.positions), Decimal("0"))
        available_balances = {token: str(balance) for token, balance in account_state.available_balances.items()}
        log_with_context(
            self._logger,
            level=20,
            message="Account snapshot",
            label=label,
            positions_count=len(account_state.positions),
            total_position_shares=str(total_positions_shares),
            open_orders_count=len(account_state.open_orders),
            available_balances=available_balances,
        )

    def _summarize_state(self, cycle_index: int) -> None:
        metrics_snapshot = self._context.metrics.snapshot()
        log_with_context(
            self._logger,
            level=20,
            message="Cycle summary",
            cycle_index=cycle_index,
            metrics=metrics_snapshot,
        )

    def _process_buy_candidates(self, account_state: AccountState) -> Dict[str, float]:
        markets = list(self._context.client.fetch_active_markets())
        top_metrics = self._context.analyzer.select_top_tokens(markets)
        candidates = self._context.candidate_builder.build_buy_candidates(top_metrics, account_state)

        log_with_context(
            self._logger,
            level=20,
            message="Buy candidates prepared",
            count=len(candidates),
        )

        success = 0
        failures = 0
        for candidate in candidates:
            if self._context.executor.submit_buy_order(candidate):
                success += 1
            else:
                failures += 1

        log_with_context(
            self._logger,
            level=20,
            message="Buy execution summary",
            attempted=len(candidates),
            success=success,
            failed=failures,
        )

        return {
            "buy_markets_considered": float(len(top_metrics)),
            "buy_orders_attempted": float(len(candidates)),
            "buy_orders_success": float(success),
            "buy_orders_failed": float(failures),
        }

    def _manage_sell_orders(self, account_state: AccountState) -> Dict[str, float]:
        self._context.risk_manager.reset(account_state)
        summary = self._context.sell_manager.manage(account_state)
        log_with_context(
            self._logger,
            level=20,
            message="Sell management summary",
            summary=summary,
        )
        return summary

    def run(self) -> None:
        poll_interval = self._context.config.scheduler.poll_interval_seconds
        cycle_index = 0

        account_state = self._context.account_manager.refresh()
        self._context.risk_manager.reset(account_state)
        self._log_account_snapshot("startup", account_state)

        while True:
            cycle_index += 1
            start_time = time.monotonic()

            try:
                self._context.risk_manager.reset(account_state)
                self._log_account_snapshot(f"cycle_{cycle_index}_start", account_state)

                buy_metrics = self._process_buy_candidates(account_state)
                self._context.metrics.merge_counts(**buy_metrics)

                account_state = self._context.account_manager.refresh()
                sell_metrics = self._manage_sell_orders(account_state)
                self._context.metrics.merge_counts(**sell_metrics)
            except Exception as exc:  # noqa: BLE001
                log_with_context(self._logger, level=40, message="Cycle error", error=str(exc))
                self._context.metrics.increment("cycle_errors")
            finally:
                duration = time.monotonic() - start_time
                self._context.metrics.observe_cycle_duration(duration)
                self._summarize_state(cycle_index)

            account_state = self._context.account_manager.refresh()
            time.sleep(poll_interval)


def build_context(config_path: str | None = None) -> TradingContext:
    config = load_config(config_path)
    logger = configure_logging(config.logging)
    logger.info("Logging configured")

    client = OpinionClient(config.api)
    account_manager = AccountStateManager(client)
    analyzer = SpreadAnalyzer(client, config.strategy)
    candidate_builder = CandidateBuilder(config.strategy)
    risk_manager = RiskManager(config.risk)
    executor = OrderExecutor(client, config.strategy, risk_manager)
    sell_manager = SellOrderManager(client, risk_manager, config.risk)
    metrics = MetricsRecorder()

    return TradingContext(
        config=config,
        client=client,
        account_manager=account_manager,
        analyzer=analyzer,
        candidate_builder=candidate_builder,
        risk_manager=risk_manager,
        executor=executor,
        sell_manager=sell_manager,
        metrics=metrics,
    )


def main(config_path: str | None = None) -> None:
    context = build_context(config_path)
    scheduler = TradingScheduler(context)
    scheduler.run()


if __name__ == "__main__":
    main()
