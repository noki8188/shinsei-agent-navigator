from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentExecutionEvent:
    agent_name: str
    status: str
    detail: str


class WorkflowRunObserver:
    def __init__(self) -> None:
        self._events: list[AgentExecutionEvent] = []

    def reset(self) -> None:
        self._events = []

    def record_success(self, agent_name: str, detail: str) -> None:
        self._events.append(
            AgentExecutionEvent(agent_name=agent_name, status="success", detail=detail)
        )

    def record_fallback(self, agent_name: str, detail: str) -> None:
        self._events.append(
            AgentExecutionEvent(agent_name=agent_name, status="fallback", detail=detail)
        )

    def timeline_entries(self) -> list[str]:
        entries: list[str] = []
        for event in self._events:
            if event.status == "success":
                entries.append(f"{event.agent_name}: {event.detail}")
            else:
                entries.append(
                    f"{event.agent_name}: {event.detail} rule-based fallback を使用しました。"
                )
        return entries
