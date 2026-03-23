from __future__ import annotations

import argparse
from dataclasses import dataclass

from app.models import CaseType, PipelineResponse, UserRequest
from app.runtime import WorkflowSettings, build_navigator


@dataclass(frozen=True, slots=True)
class ScenarioExpectation:
    name: str
    message: str
    expected_case_type: CaseType
    clarification_required: bool
    expected_missing_fields: tuple[str, ...]
    draft_required_terms: tuple[str, ...]
    review_required_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScenarioEvalResult:
    backend: str
    name: str
    success: bool
    issues: tuple[str, ...]
    diagnostics: tuple[str, ...]


REPRESENTATIVE_SCENARIOS: tuple[ScenarioExpectation, ...] = (
    ScenarioExpectation(
        name="monitor_purchase",
        message="在宅勤務用に 27 インチモニターを 1 台買いたいです。予算は 8 万円くらいです",
        expected_case_type=CaseType.PURCHASE,
        clarification_required=True,
        expected_missing_fields=("delivery_date", "quotation"),
        draft_required_terms=("モニター", "80,000", "確認"),
        review_required_terms=("quotation", "見積書"),
    ),
    ScenarioExpectation(
        name="expense_receipt_gap",
        message="先週の会食代を精算したいです。金額は 12,000 円です",
        expected_case_type=CaseType.EXPENSE,
        clarification_required=True,
        expected_missing_fields=("vendor", "receipt"),
        draft_required_terms=("会食", "12,000", "確認"),
        review_required_terms=("receipt", "領収書"),
    ),
    ScenarioExpectation(
        name="business_trip_estimate_gap",
        message="大阪へ 2 日間の出張申請を出したいです。目的は顧客訪問です",
        expected_case_type=CaseType.BUSINESS_TRIP,
        clarification_required=True,
        expected_missing_fields=("estimate", "transportation"),
        draft_required_terms=("大阪", "顧客訪問", "確認"),
        review_required_terms=("estimate", "概算費用"),
    ),
)


def evaluate_backend(settings: WorkflowSettings) -> list[ScenarioEvalResult]:
    navigator = build_navigator(settings)
    return [
        evaluate_scenario(settings.workflow_backend, navigator, scenario)
        for scenario in REPRESENTATIVE_SCENARIOS
    ]


def evaluate_scenario(
    backend: str,
    navigator: object,
    scenario: ScenarioExpectation,
) -> ScenarioEvalResult:
    response = navigator.handle(UserRequest(message=scenario.message))
    issues: list[str] = []

    if response.case_type is not scenario.expected_case_type:
        issues.append(
            "[CaseClassifier] "
            f"expected={scenario.expected_case_type.value} actual={response.case_type.value}"
        )

    has_clarification = bool(response.clarification_items)
    if has_clarification != scenario.clarification_required:
        issues.append(
            "[ClarificationAgent] "
            f"expected_presence={scenario.clarification_required} actual={has_clarification}"
        )

    missing_fields = {item.field for item in response.clarification_items}
    for field in scenario.expected_missing_fields:
        if field not in missing_fields:
            issues.append(f"[ClarificationAgent] missing field={field}")

    draft_text = _draft_text(response)
    for term in scenario.draft_required_terms:
        if term not in draft_text:
            issues.append(f"[DraftAgent] missing term={term}")

    review_text = _review_text(response)
    for term in scenario.review_required_terms:
        if term not in review_text:
            issues.append(f"[ReviewAgent] missing term={term}")

    diagnostics = tuple(
        line
        for line in response.trace.timeline
        if "CaseClassifier:" in line
        or "ClarificationAgent:" in line
        or "DraftAgent:" in line
    )

    return ScenarioEvalResult(
        backend=backend,
        name=scenario.name,
        success=not issues,
        issues=tuple(issues),
        diagnostics=diagnostics,
    )


def _draft_text(response: PipelineResponse) -> str:
    return " ".join(
        [
            response.draft_result.title,
            response.draft_result.body,
            *response.draft_result.attachments,
            *response.draft_result.notes,
        ]
    )


def _review_text(response: PipelineResponse) -> str:
    return " ".join(
        [
            *response.review_result.missing_fields,
            *response.review_result.policy_risks,
            *response.review_result.human_checkpoints,
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backend",
        choices=["rule_based", "llm", "all"],
        default="all",
        help="評価対象 backend",
    )
    args = parser.parse_args()

    base_settings = WorkflowSettings.from_env()
    requested_backends = (
        ["rule_based", "llm"] if args.backend == "all" else [args.backend]
    )

    failed_results: list[ScenarioEvalResult] = []
    for backend in requested_backends:
        settings = WorkflowSettings(
            workflow_backend=backend,
            llm_provider=base_settings.llm_provider,
            llm_model=base_settings.llm_model,
            llm_base_url=base_settings.llm_base_url,
            llm_api_key=base_settings.llm_api_key,
            llm_timeout_seconds=base_settings.llm_timeout_seconds,
            llm_retries=base_settings.llm_retries,
            llm_temperature=base_settings.llm_temperature,
            llm_max_output_tokens=base_settings.llm_max_output_tokens,
        )

        if backend == "llm" and not settings.has_llm_api_key():
            print("[SKIP] llm backend: SHINSEI_LLM_API_KEY / OPENAI_API_KEY is not set.")
            continue

        results = evaluate_backend(settings)
        for result in results:
            status = "PASS" if result.success else "FAIL"
            print(f"[{status}] {result.backend}::{result.name}")
            for issue in result.issues:
                print(f"  - {issue}")
            for diagnostic in result.diagnostics:
                print(f"  - trace: {diagnostic}")
            if not result.success:
                failed_results.append(result)

    return 1 if failed_results else 0


if __name__ == "__main__":
    raise SystemExit(main())
