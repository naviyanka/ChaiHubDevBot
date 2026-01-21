from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable, Dict, Optional
from uuid import uuid4

from .models import ApprovalRequest, ApprovalStatus


class ApprovalStore:
    def __init__(self, timeout_seconds: int) -> None:
        self._requests: Dict[str, ApprovalRequest] = {}
        self._futures: Dict[str, asyncio.Future[ApprovalStatus]] = {}
        self._timeout_seconds = timeout_seconds
        self._notifier: Optional[Callable[[ApprovalRequest], None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_notifier(self, notifier: Callable[[ApprovalRequest], None]) -> None:
        self._notifier = notifier

    def list_pending(self) -> list[ApprovalRequest]:
        return [req for req in self._requests.values() if req.status == ApprovalStatus.WAITING]

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def create_request(self, action_summary: str, risk: str) -> ApprovalRequest:
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        request_id = str(uuid4())
        request = ApprovalRequest(
            request_id=request_id,
            action_summary=action_summary,
            risk=risk,
            status=ApprovalStatus.WAITING,
        )
        self._requests[request_id] = request
        self._futures[request_id] = self._loop.create_future()
        if self._notifier:
            self._notifier(request)
        self._loop.create_task(self._handle_timeout(request_id))
        return request

    async def wait_for_decision(self, request_id: str) -> ApprovalStatus:
        future = self._futures[request_id]
        return await future

    def decide(self, request_id: str, approved: bool) -> ApprovalStatus:
        request = self._requests.get(request_id)
        if not request:
            raise KeyError("Unknown approval request")
        if request.status != ApprovalStatus.WAITING:
            return request.status
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.DENIED
        request.decision_at = datetime.utcnow()
        self._resolve_future(request_id, request.status)
        return request.status

    async def _handle_timeout(self, request_id: str) -> None:
        await asyncio.sleep(self._timeout_seconds)
        request = self._requests.get(request_id)
        if not request or request.status != ApprovalStatus.WAITING:
            return
        request.status = ApprovalStatus.TIMED_OUT
        request.decision_at = datetime.utcnow()
        self._resolve_future(request_id, request.status)

    def _resolve_future(self, request_id: str, status: ApprovalStatus) -> None:
        future = self._futures.get(request_id)
        if not future or future.done():
            return
        if self._loop is None:
            future.set_result(status)
            return
        self._loop.call_soon_threadsafe(future.set_result, status)
