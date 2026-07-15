from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import threading
from typing import Any
from uuid import uuid4

INSPECTION_STAGES = ("prepare", "doctor", "controls", "integrity", "report")
MAX_RECENT_EVENTS = 8


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class InspectionProgress:
    """Thread-safe, session-local progress for one observable inspection operation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {
            "operation_id": None,
            "kind": None,
            "status": "idle",
            "stage": "prepare",
            "stage_index": 0,
            "stage_count": len(INSPECTION_STAGES),
            "current_source": None,
            "event": "idle",
            "started_at": None,
            "updated_at": None,
            "completed_at": None,
            "recent": [],
        }

    def start(self, kind: str) -> None:
        at = _now()
        event = {
            "stage": "prepare",
            "source": ".",
            "event": "inspection_started",
            "at": at,
        }
        with self._lock:
            self._state = {
                "operation_id": str(uuid4()),
                "kind": kind,
                "status": "running",
                "stage": "prepare",
                "stage_index": 1,
                "stage_count": len(INSPECTION_STAGES),
                "current_source": ".",
                "event": "inspection_started",
                "started_at": at,
                "updated_at": at,
                "completed_at": None,
                "recent": [event],
            }

    def emit(self, stage: str, source: str, event: str) -> None:
        if stage not in INSPECTION_STAGES:
            raise ValueError(f"Unknown inspection stage: {stage}")
        at = _now()
        record = {"stage": stage, "source": source, "event": event, "at": at}
        with self._lock:
            recent = [*self._state["recent"], record][-MAX_RECENT_EVENTS:]
            self._state.update(
                {
                    "stage": stage,
                    "stage_index": INSPECTION_STAGES.index(stage) + 1,
                    "current_source": source,
                    "event": event,
                    "updated_at": at,
                    "recent": recent,
                }
            )

    def complete(self) -> None:
        self.emit("report", "Inspector snapshot (memory)", "inspection_completed")
        at = _now()
        with self._lock:
            self._state.update(
                {"status": "completed", "updated_at": at, "completed_at": at}
            )

    def fail(self, error_code: str) -> None:
        at = _now()
        with self._lock:
            record = {
                "stage": self._state["stage"],
                "source": self._state["current_source"] or ".",
                "event": "inspection_failed",
                "at": at,
            }
            self._state.update(
                {
                    "status": "failed",
                    "event": "inspection_failed",
                    "error_code": error_code,
                    "updated_at": at,
                    "completed_at": at,
                    "recent": [*self._state["recent"], record][-MAX_RECENT_EVENTS:],
                }
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)
