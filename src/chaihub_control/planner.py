from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from .models import Action


@dataclass
class PlanState:
    current_goal: Optional[str] = None
    current_action: Optional[str] = None


class Planner:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._interrupt = asyncio.Event()
        self.state = PlanState()

    def submit_prompt(self, prompt: str) -> None:
        self._drain_queue()
        self._queue.put_nowait(prompt)
        self._interrupt.set()

    def signal_stop(self) -> None:
        self._drain_queue()
        self._queue.put_nowait("")
        self._interrupt.set()

    async def next_prompt(self) -> str:
        prompt = await self._queue.get()
        self._interrupt.clear()
        self.state.current_goal = prompt
        return prompt

    def was_interrupted(self) -> bool:
        return self._interrupt.is_set()

    def plan(self, prompt: str) -> list[Action]:
        action_id = str(uuid4())
        if prompt.strip().lower().startswith("cmd:"):
            command = prompt.split(":", 1)[1].strip()
            summary = f"Execute command: {command}"
            risk = "high"
        else:
            command = None
            summary = f"Process instruction: {prompt}"
            risk = "medium"
        return [Action(action_id=action_id, summary=summary, command=command, risk=risk)]

    def _drain_queue(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                return
