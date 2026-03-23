from __future__ import annotations

import os
from dataclasses import dataclass

from app.llm_agents import (
    LLMCaseClassifier,
    LLMClarificationAgent,
    LLMDraftAgent,
    LLMSettings,
    build_llm_client,
)
from app.pipeline import (
    InternalApplicationNavigator,
    RuleBasedCaseClassifier,
    RuleBasedClarificationAgent,
    RuleBasedDraftAgent,
    RuleBasedMessageAnalyzer,
    RuleBasedReviewAgent,
    RuleBasedTraceBuilder,
)
from app.runtime_events import WorkflowRunObserver


def _normalize_backend(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if normalized not in {"rule_based", "llm"}:
        raise ValueError(
            "SHINSEI_WORKFLOW_BACKEND must be either 'rule_based' or 'llm'."
        )
    return normalized


@dataclass(slots=True)
class WorkflowSettings:
    workflow_backend: str = "rule_based"
    llm_provider: str = "openai"
    llm_model: str = "gpt-5.4-mini"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_timeout_seconds: float = 30.0
    llm_retries: int = 2
    llm_temperature: float = 0.0
    llm_max_output_tokens: int = 1200

    @classmethod
    def from_env(cls) -> "WorkflowSettings":
        return cls(
            workflow_backend=_normalize_backend(
                os.getenv("SHINSEI_WORKFLOW_BACKEND", "rule_based")
            ),
            llm_provider=os.getenv("SHINSEI_LLM_PROVIDER", "openai").strip().lower(),
            llm_model=os.getenv("SHINSEI_LLM_MODEL", "gpt-5.4-mini").strip(),
            llm_base_url=os.getenv("SHINSEI_LLM_BASE_URL") or None,
            llm_api_key=(
                os.getenv("SHINSEI_LLM_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or None
            ),
            llm_timeout_seconds=float(
                os.getenv("SHINSEI_LLM_TIMEOUT_SECONDS", "30")
            ),
            llm_retries=int(os.getenv("SHINSEI_LLM_RETRIES", "2")),
            llm_temperature=float(os.getenv("SHINSEI_LLM_TEMPERATURE", "0")),
            llm_max_output_tokens=int(
                os.getenv("SHINSEI_LLM_MAX_OUTPUT_TOKENS", "1200")
            ),
        )

    def to_llm_settings(self) -> LLMSettings:
        return LLMSettings(
            provider=self.llm_provider,
            model=self.llm_model,
            base_url=self.llm_base_url,
            api_key=self.llm_api_key,
            timeout_seconds=self.llm_timeout_seconds,
            retries=self.llm_retries,
            temperature=self.llm_temperature,
            max_output_tokens=self.llm_max_output_tokens,
        )

    def runtime_label(self) -> str:
        if self.workflow_backend == "rule_based":
            return "rule_based"
        return f"llm ({self.llm_provider}:{self.llm_model})"

    def has_llm_api_key(self) -> bool:
        return bool(self.llm_api_key)

def build_navigator(settings: WorkflowSettings) -> InternalApplicationNavigator:
    if settings.workflow_backend == "rule_based":
        return InternalApplicationNavigator(runtime_label=settings.runtime_label())

    run_observer = WorkflowRunObserver()
    client = build_llm_client(settings.to_llm_settings())
    return InternalApplicationNavigator(
        case_classifier=LLMCaseClassifier(
            client,
            fallback_agent=RuleBasedCaseClassifier(),
            run_observer=run_observer,
        ),
        message_analyzer=RuleBasedMessageAnalyzer(),
        clarification_agent=LLMClarificationAgent(
            client,
            fallback_agent=RuleBasedClarificationAgent(),
            run_observer=run_observer,
        ),
        draft_agent=LLMDraftAgent(
            client,
            fallback_agent=RuleBasedDraftAgent(),
            run_observer=run_observer,
        ),
        review_agent=RuleBasedReviewAgent(),
        trace_builder=RuleBasedTraceBuilder(),
        runtime_label=settings.runtime_label(),
        run_observer=run_observer,
    )


def build_navigator_from_env() -> InternalApplicationNavigator:
    return build_navigator(WorkflowSettings.from_env())
