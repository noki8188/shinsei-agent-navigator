from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class CaseType(str, Enum):
    EXPENSE = "expense"
    PURCHASE = "purchase"
    BUSINESS_TRIP = "business_trip"


@dataclass(slots=True)
class UserRequest:
    message: str
    applicant: str | None = None
    department: str | None = None


@dataclass(slots=True)
class PolicyDoc:
    case_type: str
    title: str
    path: str
    summary: str

    def to_dict(self) -> dict[str, str]:
        return {
            "caseType": self.case_type,
            "title": self.title,
            "path": self.path,
            "summary": self.summary,
        }


@dataclass(slots=True)
class ClarificationItem:
    field: str
    reason: str
    prompt: str
    required: bool = True

    def to_dict(self) -> dict[str, str | bool]:
        return asdict(self)


@dataclass(slots=True)
class DraftResult:
    title: str
    body: str
    attachments: list[str]
    approval_route: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "title": self.title,
            "body": self.body,
            "attachments": self.attachments,
            "approvalRoute": self.approval_route,
            "notes": self.notes,
        }


@dataclass(slots=True)
class ReviewResult:
    missing_fields: list[str]
    policy_risks: list[str]
    human_checkpoints: list[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "missingFields": self.missing_fields,
            "policyRisks": self.policy_risks,
            "humanCheckpoints": self.human_checkpoints,
        }


@dataclass(slots=True)
class ClassificationTrace:
    case_type: str
    matched_keywords: list[str]
    rationale: str

    def to_dict(self) -> dict[str, object]:
        return {
            "caseType": self.case_type,
            "matchedKeywords": self.matched_keywords,
            "rationale": self.rationale,
        }


@dataclass(slots=True)
class ClarificationTrace:
    extracted_fields: list[str]
    missing_fields: list[str]
    questions: list[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "extractedFields": self.extracted_fields,
            "missingFields": self.missing_fields,
            "questions": self.questions,
        }


@dataclass(slots=True)
class RuleReferenceTrace:
    documents: list[str]
    applied_rules: list[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "documents": self.documents,
            "appliedRules": self.applied_rules,
        }


@dataclass(slots=True)
class ReviewTrace:
    verdict: str
    policy_risks: list[str]
    human_checkpoints: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "policyRisks": self.policy_risks,
            "humanCheckpoints": self.human_checkpoints,
        }


@dataclass(slots=True)
class PipelineTrace:
    classification: ClassificationTrace
    clarification: ClarificationTrace
    rule_references: RuleReferenceTrace
    review: ReviewTrace
    timeline: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification.to_dict(),
            "clarification": self.clarification.to_dict(),
            "ruleReferences": self.rule_references.to_dict(),
            "review": self.review.to_dict(),
            "timeline": self.timeline,
        }


@dataclass(slots=True)
class PipelineResponse:
    case_type: CaseType
    policy_docs: list[PolicyDoc]
    clarification_items: list[ClarificationItem]
    draft_result: DraftResult
    review_result: ReviewResult
    trace: PipelineTrace

    def to_dict(self) -> dict[str, object]:
        return {
            "caseType": self.case_type.value,
            "policyDocs": [item.to_dict() for item in self.policy_docs],
            "clarificationItems": [item.to_dict() for item in self.clarification_items],
            "draftResult": self.draft_result.to_dict(),
            "reviewResult": self.review_result.to_dict(),
            "trace": self.trace.to_dict(),
        }
