"""
Approval queue: pending human-in-the-loop escalations. The graph submits
an EscalationEvent here when it needs a human decision; the review UI
(via the API) lists pending items and submits resolutions back.
"""
from __future__ import annotations

import time
from typing import Optional

from src.schemas.models import EscalationEvent


class ApprovalQueue:
    def __init__(self) -> None:
        self._pending: dict[str, EscalationEvent] = {}
    

    def submit(self, event: EscalationEvent) -> str:
        # store event and return its id
        self._pending[event.id] = event
        return event.id

    def list_pending(self) -> list[EscalationEvent]:
        return [
            evt
            for evt in self._pending.values()
            if evt.resolution is None
        ]

    def list_resolved(self, resolution: Optional[str] = None) -> list[EscalationEvent]:
        return [
            evt
            for evt in self._pending.values()
            if evt.resolution is not None
            and (resolution is None or evt.resolution == resolution)
        ]

    def get(self, approval_id: str) -> Optional[EscalationEvent]:
        return self._pending.get(approval_id)
       

    def resolve(self, approval_id: str, resolution: str, notes: str = "") -> Optional[EscalationEvent]:
        event = self._pending.get(approval_id)
        if event is None: 
            return None

        updated = event.model_copy(update={
            "resolution": resolution,
            "resolution_notes": notes,
            "resolved_at": time.time(),
        })
        self._pending[approval_id] = updated
        return updated