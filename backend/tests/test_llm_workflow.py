from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.llm_agents import (
    LLMCaseClassifier,
    LLMClarificationAgent,
    LLMDraftAgent,
    LLMResponseError,
    LLMSettings,
    SchemaValidationError,
    StructuredOutputRequest,
    StructuredOutputResult,
    build_llm_client,
    validate_json_schema,
)
from app.models import CaseType, UserRequest
from app.pipeline import (
    InternalApplicationNavigator,
    RuleBasedCaseClassifier,
    RuleBasedClarificationAgent,
    RuleBasedDraftAgent,
    RuleBasedMessageAnalyzer,
    RuleBasedReviewAgent,
    RuleBasedTraceBuilder,
)
from app.runtime import WorkflowSettings, build_navigator, build_navigator_from_env
from app.runtime_events import WorkflowRunObserver


class FakeLLMClient:
    def __init__(self, *, invalid_task: str | None = None) -> None:
        self.invalid_task = invalid_task

    def generate_structured_output(
        self, request_payload: StructuredOutputRequest
    ) -> StructuredOutputResult:
        if request_payload.task_name == self.invalid_task:
            raise SchemaValidationError(
                f"{request_payload.task_name} schema validation failed in fake client."
            )

        if request_payload.task_name == "CaseClassifier":
            return StructuredOutputResult(
                parsed={
                    "case_type": "purchase",
                    "matched_keywords": ["モニター", "購入"],
                    "rationale": "モニター購入の相談なので purchase と判断しました。",
                },
                response_id="resp_case_123",
                model="gpt-5.4-mini",
            )
        if request_payload.task_name == "ClarificationAgent":
            return StructuredOutputResult(
                parsed={
                    "items": [
                        {
                            "field": "purpose",
                            "reason": "用途または導入理由が必要です。",
                            "prompt": "モニターの利用目的を教えてください。",
                            "required": True,
                        },
                        {
                            "field": "delivery_date",
                            "reason": "納期または利用開始時期が必要です。",
                            "prompt": "いつまでに必要ですか。",
                            "required": True,
                        },
                    ]
                },
                response_id="resp_clarify_123",
                model="gpt-5.4-mini",
            )
        if request_payload.task_name == "DraftAgent":
            return StructuredOutputResult(
                parsed={
                    "title": "在宅勤務モニター購入申請（草稿）",
                    "body": (
                        "申請区分: 備品購入申請\n"
                        "購入対象: 27 インチモニター 1 台\n"
                        "金額: 80,000 円\n"
                        "不足情報: 用途と納期の確認が必要です。"
                    ),
                    "attachments": ["見積書"],
                    "notes": ["LLM 草稿のため提出前に最終確認してください。"],
                },
                response_id="resp_draft_123",
                model="gpt-5.4-mini",
            )
        raise AssertionError(f"unexpected task: {request_payload.task_name}")


class LLMWorkflowTest(unittest.TestCase):
    def test_llm_agents_can_be_wired_into_navigator(self) -> None:
        observer = WorkflowRunObserver()
        client = FakeLLMClient()
        navigator = InternalApplicationNavigator(
            case_classifier=LLMCaseClassifier(
                client,
                fallback_agent=RuleBasedCaseClassifier(),
                run_observer=observer,
            ),
            message_analyzer=RuleBasedMessageAnalyzer(),
            clarification_agent=LLMClarificationAgent(
                client,
                fallback_agent=RuleBasedClarificationAgent(),
                run_observer=observer,
            ),
            draft_agent=LLMDraftAgent(
                client,
                fallback_agent=RuleBasedDraftAgent(),
                run_observer=observer,
            ),
            review_agent=RuleBasedReviewAgent(),
            trace_builder=RuleBasedTraceBuilder(),
            runtime_label="llm (openai:gpt-5.4-mini)",
            run_observer=observer,
        )

        result = navigator.handle(
            UserRequest(message="在宅勤務用に 27 インチモニターを 1 台買いたいです。予算は 8 万円くらいです")
        )

        self.assertEqual(result.case_type, CaseType.PURCHASE)
        self.assertEqual(result.trace.timeline[0], "Workflow Runtime: llm (openai:gpt-5.4-mini)")
        self.assertIn(
            "CaseClassifier: OpenAI Responses API + Structured Outputs succeeded",
            " ".join(result.trace.timeline),
        )
        self.assertIn("purpose", result.review_result.missing_fields)
        self.assertIn("在宅勤務モニター購入申請", result.draft_result.title)
        self.assertIn("80,000 円", result.draft_result.body)

    def test_llm_fallback_reason_is_left_in_trace(self) -> None:
        observer = WorkflowRunObserver()
        client = FakeLLMClient(invalid_task="ClarificationAgent")
        navigator = InternalApplicationNavigator(
            case_classifier=LLMCaseClassifier(
                client,
                fallback_agent=RuleBasedCaseClassifier(),
                run_observer=observer,
            ),
            message_analyzer=RuleBasedMessageAnalyzer(),
            clarification_agent=LLMClarificationAgent(
                client,
                fallback_agent=RuleBasedClarificationAgent(),
                run_observer=observer,
            ),
            draft_agent=LLMDraftAgent(
                client,
                fallback_agent=RuleBasedDraftAgent(),
                run_observer=observer,
            ),
            review_agent=RuleBasedReviewAgent(),
            trace_builder=RuleBasedTraceBuilder(),
            runtime_label="llm (openai:gpt-5.4-mini)",
            run_observer=observer,
        )

        result = navigator.handle(
            UserRequest(message="先週の会食代を精算したいです。金額は 12,000 円です")
        )

        trace_text = " ".join(result.trace.timeline)
        self.assertIn("ClarificationAgent:", trace_text)
        self.assertIn("rule-based fallback", trace_text)

    def test_workflow_settings_read_env_values(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SHINSEI_WORKFLOW_BACKEND": "llm",
                "SHINSEI_LLM_PROVIDER": "openai",
                "SHINSEI_LLM_MODEL": "gpt-5.4-mini",
                "SHINSEI_LLM_API_KEY": "test-key",
                "SHINSEI_LLM_TIMEOUT_SECONDS": "45",
                "SHINSEI_LLM_RETRIES": "3",
                "SHINSEI_LLM_MAX_OUTPUT_TOKENS": "900",
            },
            clear=False,
        ):
            settings = WorkflowSettings.from_env()

        self.assertEqual(settings.workflow_backend, "llm")
        self.assertEqual(settings.llm_provider, "openai")
        self.assertEqual(settings.llm_model, "gpt-5.4-mini")
        self.assertEqual(settings.llm_api_key, "test-key")
        self.assertEqual(settings.llm_timeout_seconds, 45.0)
        self.assertEqual(settings.llm_retries, 3)
        self.assertEqual(settings.llm_max_output_tokens, 900)

    def test_build_navigator_from_env_uses_llm_backend(self) -> None:
        fake_client = FakeLLMClient()
        with patch.dict(
            os.environ,
            {
                "SHINSEI_WORKFLOW_BACKEND": "llm",
                "SHINSEI_LLM_PROVIDER": "openai",
                "SHINSEI_LLM_MODEL": "gpt-5.4-mini",
            },
            clear=False,
        ):
            with patch("app.runtime.build_llm_client", return_value=fake_client):
                navigator = build_navigator_from_env()

        result = navigator.handle(
            UserRequest(message="在宅勤務用に 27 インチモニターを 1 台買いたいです。予算は 8 万円くらいです")
        )
        self.assertEqual(result.case_type, CaseType.PURCHASE)
        self.assertEqual(result.trace.timeline[0], "Workflow Runtime: llm (openai:gpt-5.4-mini)")

    def test_build_llm_client_supports_openai_responses(self) -> None:
        client = build_llm_client(
            LLMSettings(provider="openai", model="gpt-5.4-mini", api_key="test-key")
        )
        self.assertEqual(client.__class__.__name__, "OpenAIResponsesClient")

    def test_validate_json_schema_rejects_invalid_enum(self) -> None:
        with self.assertRaises(SchemaValidationError):
            validate_json_schema(
                {"case_type": "other"},
                {
                    "type": "object",
                    "properties": {
                        "case_type": {
                            "type": "string",
                            "enum": ["expense", "purchase"],
                        }
                    },
                    "required": ["case_type"],
                    "additionalProperties": False,
                },
            )

    def test_build_navigator_can_be_called_with_settings(self) -> None:
        navigator = build_navigator(WorkflowSettings(workflow_backend="rule_based"))
        result = navigator.handle(
            UserRequest(message="大阪へ 2 日間の出張申請を出したいです。目的は顧客訪問です")
        )
        self.assertEqual(result.case_type, CaseType.BUSINESS_TRIP)


if __name__ == "__main__":
    unittest.main()
