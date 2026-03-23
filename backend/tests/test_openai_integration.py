from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.models import CaseType, UserRequest
from app.runtime import build_navigator_from_env


class OpenAIIntegrationSmokeTest(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("OPENAI_API_KEY") or os.getenv("SHINSEI_LLM_API_KEY"),
        "OPENAI_API_KEY または SHINSEI_LLM_API_KEY がないため skip",
    )
    def test_openai_responses_api_smoke(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SHINSEI_WORKFLOW_BACKEND": "llm",
                "SHINSEI_LLM_PROVIDER": "openai",
                "SHINSEI_LLM_MODEL": os.getenv("SHINSEI_LLM_MODEL", "gpt-5.4-mini"),
                "SHINSEI_LLM_TIMEOUT_SECONDS": os.getenv(
                    "SHINSEI_LLM_TIMEOUT_SECONDS", "60"
                ),
                "SHINSEI_LLM_RETRIES": os.getenv("SHINSEI_LLM_RETRIES", "1"),
            },
            clear=False,
        ):
            navigator = build_navigator_from_env()
            result = navigator.handle(
                UserRequest(
                    message="在宅勤務用に 27 インチモニターを 1 台買いたいです。予算は 8 万円くらいです"
                )
            )

        self.assertEqual(result.case_type, CaseType.PURCHASE)
        self.assertTrue(result.clarification_items)
        self.assertTrue(result.draft_result.title)
        self.assertTrue(result.draft_result.body)

        timeline_text = "\n".join(result.trace.timeline)
        self.assertIn(
            "CaseClassifier: OpenAI Responses API + Structured Outputs succeeded",
            timeline_text,
        )
        self.assertIn(
            "ClarificationAgent: OpenAI Responses API + Structured Outputs succeeded",
            timeline_text,
        )
        self.assertIn(
            "DraftAgent: OpenAI Responses API + Structured Outputs succeeded",
            timeline_text,
        )
        self.assertNotIn("rule-based fallback を使用しました", timeline_text)


if __name__ == "__main__":
    unittest.main()
