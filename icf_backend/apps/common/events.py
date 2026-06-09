"""
Domain event bus — docs/14 (Event-Driven Architecture).

Usage:
    from apps.common.events import event_bus

    event_bus.emit('lead.created', tenant_id=tenant.pk, lead_id=lead.pk)

Consumers subscribe by decorating a Celery task and registering it:
    event_bus.subscribe('lead.created', tasks.on_lead_created)

Processing guarantees (BRU-16):
- Tasks must be idempotent: emitting the same event twice must not double-apply effects.
- Every event carries tenant_id for BRU-01 isolation in consumers.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)

_registry: dict[str, list[Callable]] = {}


class EventBus:
    def subscribe(self, event_name: str, handler: Callable) -> None:
        _registry.setdefault(event_name, []).append(handler)

    def emit(self, event_name: str, **payload) -> None:
        """
        Dispatch event to all registered handlers asynchronously via Celery.
        Each handler is an independent Celery task (idempotent, BRU-16).
        tenant_id must always be in payload (BRU-01).
        """
        if 'tenant_id' not in payload:
            logger.error("Event '%s' emitted without tenant_id — rejecting (BRU-01).", event_name)
            return

        handlers = _registry.get(event_name, [])
        if not handlers:
            logger.debug("No handlers registered for event '%s'.", event_name)
            return

        for handler in handlers:
            try:
                # .delay() sends the task to the Celery broker asynchronously
                handler.delay(event_name=event_name, **payload)
            except Exception:
                logger.exception(
                    "Failed to dispatch event '%s' to handler '%s'.",
                    event_name,
                    handler.__name__,
                )


event_bus = EventBus()
