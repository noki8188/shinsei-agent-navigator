from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, request

from app.agent_interfaces import (
    AnalysisState,
    CaseClassifier,
    ClarificationAgent,
    ClassificationDecision,
    DraftAgent,
)
from app.knowledge_base import KnowledgeBase
from app.models import CaseType, ClarificationItem, DraftResult
from app.pipeline import (
    RuleBasedCaseClassifier,
    RuleBasedClarificationAgent,
    RuleBasedDraftAgent,
    approval_route,
)
from app.runtime_events import WorkflowRunObserver


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com"
CASE_TYPE_ENUM = [case_type.value for case_type in CaseType]


class LLMResponseError(RuntimeError):
    pass


class SchemaValidationError(RuntimeError):
    pass


@dataclass(slots=True)
class LLMSettings:
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    timeout_seconds: float = 30.0
    retries: int = 2
    temperature: float = 0.0
    max_output_tokens: int = 1200


@dataclass(slots=True)
class StructuredOutputRequest:
    task_name: str
    schema_name: str
    schema_description: str
    schema: dict[str, Any]
    system_prompt: str
    user_prompt: str


@dataclass(slots=True)
class StructuredOutputResult:
    parsed: dict[str, Any]
    response_id: str | None
    model: str | None


class LLMClient(Protocol):
    def generate_structured_output(
        self, request_payload: StructuredOutputRequest
    ) -> StructuredOutputResult:
        ...


class OpenAIResponsesClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    def generate_structured_output(
        self, request_payload: StructuredOutputRequest
    ) -> StructuredOutputResult:
        if not self.settings.api_key:
            raise LLMResponseError(
                "OpenAI Responses API を使うには SHINSEI_LLM_API_KEY または "
                "OPENAI_API_KEY が必要です。"
            )

        payload = {
            "model": self.settings.model,
            "instructions": request_payload.system_prompt,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": request_payload.user_prompt}
                    ],
                }
            ],
            "temperature": self.settings.temperature,
            "max_output_tokens": self.settings.max_output_tokens,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": request_payload.schema_name,
                    "description": request_payload.schema_description,
                    "schema": request_payload.schema,
                    "strict": True,
                }
            },
        }

        response_body = self._post_with_retries(
            endpoint=((self.settings.base_url or DEFAULT_OPENAI_BASE_URL).rstrip("/") + "/v1/responses"),
            payload=payload,
            task_name=request_payload.task_name,
        )
        parsed = self._parse_response_json(
            response_body=response_body,
            task_name=request_payload.task_name,
            schema=request_payload.schema,
        )
        return StructuredOutputResult(
            parsed=parsed,
            response_id=_string_or_none(response_body.get("id")),
            model=_string_or_none(response_body.get("model")),
        )

    def _post_with_retries(
        self, endpoint: str, payload: dict[str, Any], task_name: str
    ) -> dict[str, Any]:
        request_body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            endpoint,
            data=request_body,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(self.settings.retries + 1):
            try:
                with request.urlopen(
                    http_request, timeout=self.settings.timeout_seconds
                ) as response:
                    return json.loads(response.read().decode("utf-8"))
            except error.HTTPError as exc:
                details = exc.read().decode("utf-8", errors="ignore")
                last_error = LLMResponseError(
                    f"{task_name} failed with HTTP {exc.code}: {details}"
                )
                if not _is_retryable_http_status(exc.code) or attempt >= self.settings.retries:
                    raise last_error from exc
            except (error.URLError, TimeoutError, socket.timeout) as exc:
                reason = getattr(exc, "reason", str(exc))
                last_error = LLMResponseError(f"{task_name} failed: {reason}")
                if attempt >= self.settings.retries:
                    raise last_error from exc

            time.sleep(min(0.5 * (2**attempt), 2.0))

        if last_error is None:
            raise LLMResponseError(f"{task_name} failed for an unknown reason.")
        raise last_error

    def _parse_response_json(
        self, response_body: dict[str, Any], task_name: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        status = _string_or_none(response_body.get("status"))
        if status != "completed":
            error_payload = response_body.get("error")
            incomplete = response_body.get("incomplete_details")
            raise LLMResponseError(
                f"{task_name} returned non-completed status={status}, "
                f"error={error_payload}, incomplete_details={incomplete}"
            )

        content_text = _extract_response_text(response_body)
        try:
            parsed = json.loads(content_text)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"{task_name} returned invalid JSON: {content_text}"
            ) from exc

        validate_json_schema(parsed, schema)
        return parsed


def build_llm_client(settings: LLMSettings) -> LLMClient:
    provider = settings.provider.strip().lower()
    if provider == "openai":
        return OpenAIResponsesClient(settings)
    raise ValueError(
        "SHINSEI_LLM_PROVIDER is unsupported. Currently supported value: 'openai'."
    )


class LLMCaseClassifier(CaseClassifier):
    def __init__(
        self,
        client: LLMClient,
        fallback_agent: CaseClassifier | None = None,
        run_observer: WorkflowRunObserver | None = None,
    ) -> None:
        self.client = client
        self.fallback_agent = fallback_agent or RuleBasedCaseClassifier()
        self.run_observer = run_observer

    def classify(
        self, message: str, knowledge_base: KnowledgeBase
    ) -> ClassificationDecision:
        workflow_policy = knowledge_base.read_doc("knowledge/common/workflow-policy.md")
        case_definitions = "\n".join(
            (
                f"- {case_type.value}: "
                f"keywords={knowledge_base.get_keywords(case_type)}"
            )
            for case_type in CaseType
        )

        request_payload = StructuredOutputRequest(
            task_name="CaseClassifier",
            schema_name="case_classifier_response",
            schema_description="Internal application case classification result",
            schema=_case_classifier_schema(),
            system_prompt=(
                "You are the CaseClassifier in an internal application workflow. "
                "Choose exactly one case_type from expense, purchase, business_trip. "
                "Return a concise Japanese rationale."
            ),
            user_prompt=(
                f"相談文:\n{message}\n\n"
                "分類の基準:\n"
                f"{workflow_policy}\n\n"
                "キーワード候補:\n"
                f"{case_definitions}\n"
            ),
        )

        try:
            result = self.client.generate_structured_output(request_payload)
            decision = ClassificationDecision(
                case_type=CaseType(result.parsed["case_type"]),
                matched_keywords=[
                    keyword
                    for keyword in result.parsed["matched_keywords"]
                    if isinstance(keyword, str)
                ],
                rationale=result.parsed["rationale"],
            )
            _record_success(
                self.run_observer,
                "CaseClassifier",
                result,
            )
            return decision
        except (LLMResponseError, SchemaValidationError, ValueError, KeyError) as exc:
            _record_fallback(self.run_observer, "CaseClassifier", exc)
            return self.fallback_agent.classify(message, knowledge_base)


class LLMClarificationAgent(ClarificationAgent):
    def __init__(
        self,
        client: LLMClient,
        fallback_agent: ClarificationAgent | None = None,
        run_observer: WorkflowRunObserver | None = None,
    ) -> None:
        self.client = client
        self.fallback_agent = fallback_agent or RuleBasedClarificationAgent()
        self.run_observer = run_observer

    def build(
        self,
        case_type: CaseType,
        message: str,
        state: AnalysisState,
        knowledge_base: KnowledgeBase,
    ) -> list[ClarificationItem]:
        required_fields = knowledge_base.get_required_fields(case_type)
        request_payload = StructuredOutputRequest(
            task_name="ClarificationAgent",
            schema_name=f"{case_type.value}_clarification_response",
            schema_description="Missing fields that should be clarified before submission",
            schema=_clarification_schema(required_fields),
            system_prompt=(
                "You are the ClarificationAgent in an internal application workflow. "
                "Compare the user message and extracted fields with the required policy fields. "
                "Return only still-missing items."
            ),
            user_prompt=(
                f"case_type: {case_type.value}\n"
                f"相談文:\n{message}\n\n"
                f"既に抽出できた項目: {json.dumps(state.extracted_fields, ensure_ascii=False)}\n\n"
                f"必須項目: {json.dumps(required_fields, ensure_ascii=False)}\n\n"
                "参照 knowledge:\n"
                f"{_build_knowledge_packet(case_type, knowledge_base)}"
            ),
        )

        try:
            result = self.client.generate_structured_output(request_payload)
            items = [
                ClarificationItem(
                    field=item["field"],
                    reason=item["reason"],
                    prompt=item["prompt"],
                    required=item["required"],
                )
                for item in result.parsed["items"]
            ]
            _record_success(
                self.run_observer,
                "ClarificationAgent",
                result,
            )
            return items
        except (LLMResponseError, SchemaValidationError, ValueError, KeyError) as exc:
            _record_fallback(self.run_observer, "ClarificationAgent", exc)
            return self.fallback_agent.build(
                case_type, message, state, knowledge_base
            )


class LLMDraftAgent(DraftAgent):
    def __init__(
        self,
        client: LLMClient,
        fallback_agent: DraftAgent | None = None,
        run_observer: WorkflowRunObserver | None = None,
    ) -> None:
        self.client = client
        self.fallback_agent = fallback_agent or RuleBasedDraftAgent()
        self.run_observer = run_observer

    def build(
        self,
        case_type: CaseType,
        message: str,
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
        knowledge_base: KnowledgeBase,
    ) -> DraftResult:
        fallback_result = self.fallback_agent.build(
            case_type,
            message,
            state,
            clarification_items,
            knowledge_base,
        )
        request_payload = StructuredOutputRequest(
            task_name="DraftAgent",
            schema_name=f"{case_type.value}_draft_response",
            schema_description="Draft body and user-facing submission notes",
            schema=_draft_schema(),
            system_prompt=(
                "You are the DraftAgent in an internal application workflow. "
                "Generate a concise Japanese application draft using the knowledge documents as the primary source. "
                "Mention unresolved items clearly and do not invent confirmed facts."
            ),
            user_prompt=(
                f"case_type: {case_type.value}\n"
                f"相談文:\n{message}\n\n"
                f"抽出済み項目: {json.dumps(state.extracted_fields, ensure_ascii=False)}\n"
                f"金額: {state.amount_yen}\n\n"
                "未解決の確認事項:\n"
                f"{json.dumps([item.to_dict() for item in clarification_items], ensure_ascii=False)}\n\n"
                "rule-based fallback draft:\n"
                f"{json.dumps(fallback_result.to_dict(), ensure_ascii=False)}\n\n"
                "参照 knowledge:\n"
                f"{_build_knowledge_packet(case_type, knowledge_base)}"
            ),
        )

        try:
            result = self.client.generate_structured_output(request_payload)
            draft_result = DraftResult(
                title=result.parsed["title"],
                body=result.parsed["body"],
                attachments=_merge_unique_strings(
                    fallback_result.attachments, result.parsed["attachments"]
                ),
                approval_route=approval_route(case_type, state),
                notes=_merge_unique_strings(
                    fallback_result.notes, result.parsed["notes"]
                ),
            )
            _record_success(
                self.run_observer,
                "DraftAgent",
                result,
            )
            return draft_result
        except (LLMResponseError, SchemaValidationError, ValueError, KeyError) as exc:
            _record_fallback(self.run_observer, "DraftAgent", exc)
            return fallback_result


def validate_json_schema(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(value, dict):
            raise SchemaValidationError(f"{path} must be an object.")

        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise SchemaValidationError(f"{path}.{key} is required.")

        if schema.get("additionalProperties") is False:
            extra_keys = set(value.keys()) - set(properties.keys())
            if extra_keys:
                raise SchemaValidationError(
                    f"{path} has unexpected properties: {sorted(extra_keys)}"
                )

        for key, nested_schema in properties.items():
            if key in value:
                validate_json_schema(value[key], nested_schema, f"{path}.{key}")
        _validate_enum(value, schema, path)
        return

    if schema_type == "array":
        if not isinstance(value, list):
            raise SchemaValidationError(f"{path} must be an array.")
        items_schema = schema.get("items")
        if items_schema is not None:
            for index, item in enumerate(value):
                validate_json_schema(item, items_schema, f"{path}[{index}]")
        _validate_enum(value, schema, path)
        return

    if schema_type == "string":
        if not isinstance(value, str):
            raise SchemaValidationError(f"{path} must be a string.")
        _validate_enum(value, schema, path)
        return

    if schema_type == "boolean":
        if not isinstance(value, bool):
            raise SchemaValidationError(f"{path} must be a boolean.")
        _validate_enum(value, schema, path)
        return

    raise SchemaValidationError(f"{path} uses unsupported schema type: {schema_type}")


def _validate_enum(value: Any, schema: dict[str, Any], path: str) -> None:
    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        raise SchemaValidationError(
            f"{path} must be one of {enum_values}, got {value!r}."
        )


def _extract_response_text(response_body: dict[str, Any]) -> str:
    output_items = response_body.get("output", [])
    if not isinstance(output_items, list):
        raise LLMResponseError(f"Unexpected response output: {response_body}")

    text_parts: list[str] = []
    for item in output_items:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content_items = item.get("content", [])
        if not isinstance(content_items, list):
            continue
        for content_item in content_items:
            if (
                isinstance(content_item, dict)
                and content_item.get("type") == "output_text"
                and isinstance(content_item.get("text"), str)
            ):
                text_parts.append(content_item["text"])

    text = "".join(text_parts).strip()
    if not text:
        raise LLMResponseError(f"OpenAI Responses API returned no output_text: {response_body}")
    return text


def _case_classifier_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "case_type": {"type": "string", "enum": CASE_TYPE_ENUM},
            "matched_keywords": {
                "type": "array",
                "items": {"type": "string"},
            },
            "rationale": {"type": "string"},
        },
        "required": ["case_type", "matched_keywords", "rationale"],
        "additionalProperties": False,
    }


def _clarification_schema(
    required_fields: dict[str, str]
) -> dict[str, Any]:
    field_enum = list(required_fields.keys())
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "enum": field_enum},
                        "reason": {"type": "string"},
                        "prompt": {"type": "string"},
                        "required": {"type": "boolean"},
                    },
                    "required": ["field", "reason", "prompt", "required"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }


def _draft_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
            "attachments": {
                "type": "array",
                "items": {"type": "string"},
            },
            "notes": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["title", "body", "attachments", "notes"],
        "additionalProperties": False,
    }


def _build_knowledge_packet(
    case_type: CaseType, knowledge_base: KnowledgeBase
) -> str:
    sections: list[str] = []
    for doc in knowledge_base.get_docs(case_type):
        content = knowledge_base.read_doc(_relative_path_from_repo(doc.path))
        sections.append(
            f"## {doc.title}\nsummary: {doc.summary}\npath: {doc.path}\n{content}"
        )
    return "\n\n".join(sections)


def _merge_unique_strings(
    base_values: list[str], candidate_values: Any
) -> list[str]:
    merged = list(base_values)
    if not isinstance(candidate_values, list):
        return merged

    for value in candidate_values:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged


def _relative_path_from_repo(absolute_path: str) -> str:
    marker = "/knowledge/"
    if marker not in absolute_path:
        raise RuntimeError(f"Unexpected knowledge path: {absolute_path}")
    return "knowledge/" + absolute_path.split(marker, maxsplit=1)[1]


def _is_retryable_http_status(status_code: int) -> bool:
    return status_code in {408, 409, 429} or 500 <= status_code < 600


def _record_success(
    run_observer: WorkflowRunObserver | None,
    agent_name: str,
    result: StructuredOutputResult,
) -> None:
    if run_observer is None:
        return
    detail = "OpenAI Responses API + Structured Outputs succeeded"
    metadata: list[str] = []
    if result.response_id:
        metadata.append(f"response_id={result.response_id}")
    if result.model:
        metadata.append(f"model={result.model}")
    if metadata:
        detail = f"{detail} ({', '.join(metadata)})."
    else:
        detail = f"{detail}."
    run_observer.record_success(agent_name, detail)


def _record_fallback(
    run_observer: WorkflowRunObserver | None,
    agent_name: str,
    exc: Exception,
) -> None:
    if run_observer is None:
        return
    detail = _truncate_message(str(exc))
    run_observer.record_fallback(agent_name, detail)


def _truncate_message(message: str, limit: int = 240) -> str:
    compact = " ".join(message.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
