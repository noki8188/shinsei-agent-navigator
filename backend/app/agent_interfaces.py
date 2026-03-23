from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.knowledge_base import KnowledgeBase
from app.models import (
    CaseType,
    ClarificationItem,
    DraftResult,
    PipelineTrace,
    PolicyDoc,
    ReviewResult,
)


@dataclass(slots=True)
class AnalysisState:
    amount_yen: int | None
    extracted_fields: dict[str, object]


@dataclass(slots=True)
class ClassificationDecision:
    case_type: CaseType
    matched_keywords: list[str]
    rationale: str


class CaseClassifier(Protocol):
    def classify(self, message: str, knowledge_base: KnowledgeBase) -> ClassificationDecision:
        ...


class MessageAnalyzer(Protocol):
    def analyze(self, case_type: CaseType, message: str) -> AnalysisState:
        ...


class ClarificationAgent(Protocol):
    def build(
        self,
        case_type: CaseType,
        message: str,
        state: AnalysisState,
        knowledge_base: KnowledgeBase,
    ) -> list[ClarificationItem]:
        ...


class DraftAgent(Protocol):
    def build(
        self,
        case_type: CaseType,
        message: str,
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
        knowledge_base: KnowledgeBase,
    ) -> DraftResult:
        ...


class ReviewAgent(Protocol):
    def review(
        self,
        case_type: CaseType,
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
        draft_result: DraftResult,
    ) -> ReviewResult:
        ...


class TraceBuilder(Protocol):
    def build(
        self,
        classification: ClassificationDecision,
        docs: list[PolicyDoc],
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
        review_result: ReviewResult,
    ) -> PipelineTrace:
        ...
