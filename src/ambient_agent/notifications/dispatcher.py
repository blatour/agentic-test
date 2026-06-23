from __future__ import annotations

from typing import Iterable, List

from ambient_agent.contracts.interfaces import ActionDecision, DeliveryReceipt, SinkAdapter


class NotificationDispatcher:
    def __init__(self, sink: SinkAdapter) -> None:
        self._sink = sink

    def dispatch_all(self, decisions: Iterable[ActionDecision]) -> List[DeliveryReceipt]:
        return [self._sink.dispatch(item) for item in decisions if item.should_execute]
