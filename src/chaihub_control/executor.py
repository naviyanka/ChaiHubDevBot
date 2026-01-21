from __future__ import annotations

import asyncio
from typing import Optional

from .models import Action, ApprovalStatus, ExecutionState


class Executor:
    def __init__(self) -> None:
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._stop_event = asyncio.Event()
        self.state = ExecutionState.RUNNING
        self.current_action: Optional[str] = None

    def pause(self) -> None:
        self.state = ExecutionState.PAUSED
        self._pause_event.clear()

    def resume(self) -> None:
        self.state = ExecutionState.RUNNING
        self._pause_event.set()

    def stop(self) -> None:
        self.state = ExecutionState.STOPPED
        self._stop_event.set()
        self._pause_event.set()

    async def wait_until_ready(self) -> None:
        await self._pause_event.wait()

    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    async def execute(self, action: Action, approval_layer) -> ApprovalStatus:
        await self.wait_until_ready()
        if self.is_stopped():
            return ApprovalStatus.DENIED
        self.current_action = action.summary
        status = await approval_layer.request_and_wait(action)
        if status != ApprovalStatus.APPROVED:
            self.current_action = None
            return status
        if action.command:
            process = await asyncio.create_subprocess_shell(
                action.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            await process.communicate()
        await asyncio.sleep(0.1)
        self.current_action = None
        return status
