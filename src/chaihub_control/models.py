from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ApprovalStatus(str, Enum):
    WAITING = "WAITING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    TIMED_OUT = "TIMED_OUT"


class ExecutionState(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


@dataclass
class Action:
    action_id: str
    summary: str
    command: Optional[str]
    risk: str


@dataclass
class ApprovalRequest:
    request_id: str
    action_summary: str
    risk: str
    status: ApprovalStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    decision_at: Optional[datetime] = None
    message_id: Optional[int] = None
    chat_id: Optional[int] = None
