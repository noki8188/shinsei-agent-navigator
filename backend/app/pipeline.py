from __future__ import annotations

import re

from app.agent_interfaces import (
    AnalysisState,
    CaseClassifier,
    ClarificationAgent,
    ClassificationDecision,
    DraftAgent,
    MessageAnalyzer,
    ReviewAgent,
    TraceBuilder,
)
from app.knowledge_base import KnowledgeBase
from app.models import (
    CaseType,
    ClarificationItem,
    ClassificationTrace,
    ClarificationTrace,
    DraftResult,
    PipelineResponse,
    PipelineTrace,
    ReviewResult,
    ReviewTrace,
    RuleReferenceTrace,
    UserRequest,
)


CITY_WORDS = ["東京", "大阪", "名古屋", "福岡", "札幌", "沖縄", "京都", "横浜"]
TRANSPORT_WORDS = ["新幹線", "飛行機", "航空", "タクシー", "車", "レンタカー", "電車", "バス"]


class InternalApplicationNavigator:
    def __init__(
        self,
        knowledge_base: KnowledgeBase | None = None,
        case_classifier: CaseClassifier | None = None,
        message_analyzer: MessageAnalyzer | None = None,
        clarification_agent: ClarificationAgent | None = None,
        draft_agent: DraftAgent | None = None,
        review_agent: ReviewAgent | None = None,
        trace_builder: TraceBuilder | None = None,
    ) -> None:
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.case_classifier = case_classifier or RuleBasedCaseClassifier()
        self.message_analyzer = message_analyzer or RuleBasedMessageAnalyzer()
        self.clarification_agent = clarification_agent or RuleBasedClarificationAgent()
        self.draft_agent = draft_agent or RuleBasedDraftAgent()
        self.review_agent = review_agent or RuleBasedReviewAgent()
        self.trace_builder = trace_builder or RuleBasedTraceBuilder()

    def handle(self, request: UserRequest) -> PipelineResponse:
        classification = self.case_classifier.classify(request.message, self.knowledge_base)
        state = self.message_analyzer.analyze(classification.case_type, request.message)
        docs = self.knowledge_base.get_docs(classification.case_type)
        clarification_items = self.clarification_agent.build(
            classification.case_type, request.message, state, self.knowledge_base
        )
        draft_result = self.draft_agent.build(
            classification.case_type,
            request.message,
            state,
            clarification_items,
            self.knowledge_base,
        )
        review_result = self.review_agent.review(
            classification.case_type, state, clarification_items, draft_result
        )
        trace = self.trace_builder.build(
            classification, docs, state, clarification_items, review_result
        )

        return PipelineResponse(
            case_type=classification.case_type,
            policy_docs=docs,
            clarification_items=clarification_items,
            draft_result=draft_result,
            review_result=review_result,
            trace=trace,
        )


def extract_amount_yen(message: str) -> int | None:
    match = re.search(r"(\d[\d,]*)\s*(万円|円)", message)
    if not match:
        return None

    value = int(match.group(1).replace(",", ""))
    unit = match.group(2)
    if unit == "万円":
        return value * 10_000
    return value


def extract_sentence_after_token(message: str, tokens: list[str]) -> str | None:
    for token in tokens:
        if token in message:
            _, _, suffix = message.partition(token)
            return suffix.strip(" 。")
    return None


def clarification_prompt(case_type: CaseType, field: str) -> str:
    prompts: dict[CaseType, dict[str, str]] = {
        CaseType.EXPENSE: {
            "amount": "精算金額はいくらですか。",
            "date": "いつ利用した支出ですか。",
            "purpose": "支出の用途または会食・移動の目的を教えてください。",
            "vendor": "支払先や利用先の名称を教えてください。",
            "receipt": "領収書またはレシートはありますか。",
        },
        CaseType.PURCHASE: {
            "item_name": "購入したい備品名を教えてください。",
            "amount": "予定金額はいくらですか。",
            "purpose": "何のために利用する備品ですか。",
            "delivery_date": "いつまでに必要ですか。",
            "location": "設置場所または利用者を教えてください。",
            "quotation": "見積書はありますか。",
        },
        CaseType.BUSINESS_TRIP: {
            "destination": "出張先を教えてください。",
            "period": "出張期間はいつからいつまでですか。",
            "purpose": "出張の目的を教えてください。",
            "estimate": "概算費用はいくらですか。",
            "transportation": "移動手段は何を予定していますか。",
        },
    }
    return prompts[case_type][field]


def approval_route(case_type: CaseType, state: AnalysisState) -> list[str]:
    route = ["申請者", "所属長"]
    amount = state.amount_yen or 0

    if amount >= 50_000:
        route.append("部門長")
    if amount >= 200_000:
        route.append("管理部門")
    if case_type is CaseType.PURCHASE and "item_name" in state.extracted_fields:
        route.append("情シス確認")
    if case_type is CaseType.PURCHASE and amount >= 500_000:
        route.append("稟議承認")

    return route


def draft_body(
    case_type: CaseType,
    message: str,
    state: AnalysisState,
    clarification_items: list[ClarificationItem],
) -> str:
    follow_ups = "\n".join(f"- {item.prompt}" for item in clarification_items) or "- 追加確認なし"
    amount_text = f"{state.amount_yen:,} 円" if state.amount_yen is not None else "未確認"

    case_labels = {
        CaseType.EXPENSE: "経費申請",
        CaseType.PURCHASE: "備品購入申請",
        CaseType.BUSINESS_TRIP: "出張申請",
    }

    return (
        f"申請区分: {case_labels[case_type]}\n"
        f"原文: {message}\n"
        f"概算金額: {amount_text}\n"
        f"補足: この内容は agent が生成した下書きです。\n\n"
        "不足情報の確認事項:\n"
        f"{follow_ups}\n"
    )


class RuleBasedCaseClassifier:
    def classify(self, message: str, knowledge_base: KnowledgeBase) -> ClassificationDecision:
        scores: dict[CaseType, int] = {}
        for case_type in CaseType:
            score = sum(keyword in message for keyword in knowledge_base.get_keywords(case_type))
            scores[case_type] = score

        if "出張" in message:
            return ClassificationDecision(
                case_type=CaseType.BUSINESS_TRIP,
                matched_keywords=["出張"],
                rationale="出張という明示的なキーワードを優先して business_trip に分類しました。",
            )
        if any(
            word in message
            for word in ["購入", "備品", "モニター", "ディスプレイ", "ライセンス", "SaaS", "稟議", "契約"]
        ):
            matched_keywords = [
                word
                for word in ["購入", "備品", "モニター", "ディスプレイ", "ライセンス", "SaaS", "稟議", "契約"]
                if word in message
            ]
            return ClassificationDecision(
                case_type=CaseType.PURCHASE,
                matched_keywords=matched_keywords,
                rationale="購入・備品関連の語を優先ルールとして検出しました。",
            )
        if any(word in message for word in ["精算", "領収書", "会食", "交通費", "宿泊費"]):
            matched_keywords = [
                word for word in ["精算", "領収書", "会食", "交通費", "宿泊費"] if word in message
            ]
            return ClassificationDecision(
                case_type=CaseType.EXPENSE,
                matched_keywords=matched_keywords,
                rationale="精算・経費関連の語を優先ルールとして検出しました。",
            )

        selected_case_type = max(scores, key=scores.get)
        matched_keywords = [
            keyword for keyword in knowledge_base.get_keywords(selected_case_type) if keyword in message
        ]
        return ClassificationDecision(
            case_type=selected_case_type,
            matched_keywords=matched_keywords,
            rationale="キーワード一致数が最も多いケースへフォールバック分類しました。",
        )


class RuleBasedMessageAnalyzer:
    def analyze(self, case_type: CaseType, message: str) -> AnalysisState:
        amount_yen = extract_amount_yen(message)
        fields: dict[str, object] = {}

        if amount_yen is not None:
            fields["amount"] = amount_yen
            fields["estimate"] = amount_yen

        if any(token in message for token in ["目的", "用途", "顧客訪問", "会食", "在宅勤務", "研修", "展示会", "契約"]):
            fields["purpose"] = extract_sentence_after_token(message, ["目的は", "用途は"]) or "記載あり"

        if any(token in message for token in ["今日", "昨日", "先週", "月", "日"]):
            fields["date"] = "記載あり"
            fields["period"] = "記載あり"

        if any(token in message for token in ["領収書", "レシート"]):
            fields["receipt"] = "あり"

        if "見積" in message:
            fields["quotation"] = "あり"

        if any(token in message for token in ["設置", "利用者", "オフィス", "自宅", "在宅勤務"]):
            fields["location"] = "記載あり"

        if any(token in message for token in ["納期", "までに", "来週", "今月", "利用開始", "導入"]):
            fields["delivery_date"] = "記載あり"

        if any(
            token in message
            for token in ["モニター", "ディスプレイ", "キーボード", "マウス", "ライセンス", "備品", "SaaS", "クラウド", "契約"]
        ):
            fields["item_name"] = "記載あり"

        if any(token in message for token in CITY_WORDS):
            fields["destination"] = next(city for city in CITY_WORDS if city in message)

        if any(token in message for token in ["日間", "泊", "から", "まで"]):
            fields["period"] = "記載あり"

        if any(token in message for token in TRANSPORT_WORDS):
            fields["transportation"] = next(word for word in TRANSPORT_WORDS if word in message)

        if case_type is CaseType.EXPENSE and any(token in message for token in ["会食", "交通", "宿泊"]):
            fields["purpose"] = fields.get("purpose", "記載あり")

        if case_type is CaseType.EXPENSE and any(token in message for token in ["レストラン", "ホテル", "JR", "航空", "タクシー"]):
            fields["vendor"] = "記載あり"

        return AnalysisState(amount_yen=amount_yen, extracted_fields=fields)


class RuleBasedClarificationAgent:
    def build(
        self,
        case_type: CaseType,
        message: str,
        state: AnalysisState,
        knowledge_base: KnowledgeBase,
    ) -> list[ClarificationItem]:
        clarification_items: list[ClarificationItem] = []
        required_fields = knowledge_base.get_required_fields(case_type)

        for field, reason in required_fields.items():
            if field not in state.extracted_fields:
                clarification_items.append(
                    ClarificationItem(
                        field=field,
                        reason=reason,
                        prompt=clarification_prompt(case_type, field),
                    )
                )

        return clarification_items


class RuleBasedDraftAgent:
    def build(
        self,
        case_type: CaseType,
        message: str,
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
        knowledge_base: KnowledgeBase,
    ) -> DraftResult:
        attachments = knowledge_base.get_base_attachments(case_type)
        if case_type is CaseType.EXPENSE and "receipt" not in state.extracted_fields:
            attachments.append("領収書がない場合の理由メモ")
        if case_type is CaseType.PURCHASE and (state.amount_yen or 0) >= 200_000:
            attachments.append("比較資料または選定理由")
        if case_type is CaseType.PURCHASE and (state.amount_yen or 0) >= 500_000:
            attachments.append("稟議書ドラフト")
        if case_type is CaseType.BUSINESS_TRIP:
            attachments.append("訪問先またはイベント情報")

        notes = ["この草稿は提出前に人による最終確認が必要です。"]
        if clarification_items:
            notes.append("不足情報が埋まるまで正式申請は保留です。")

        title_map = {
            CaseType.EXPENSE: "経費精算申請（草稿）",
            CaseType.PURCHASE: "備品購入申請（草稿）",
            CaseType.BUSINESS_TRIP: "出張申請（草稿）",
        }

        return DraftResult(
            title=title_map[case_type],
            body=draft_body(case_type, message, state, clarification_items),
            attachments=attachments,
            approval_route=approval_route(case_type, state),
            notes=notes,
        )


class RuleBasedReviewAgent:
    def review(
        self,
        case_type: CaseType,
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
        draft_result: DraftResult,
    ) -> ReviewResult:
        missing_fields = [item.field for item in clarification_items]
        policy_risks: list[str] = []
        human_checkpoints = ["最終提出前に承認者と正式な社内ルールを確認してください。"]

        if case_type is CaseType.EXPENSE and "receipt" in missing_fields:
            policy_risks.append("領収書の有無が未確認です。理由説明が必要になる可能性があります。")

        if case_type is CaseType.PURCHASE and (state.amount_yen or 0) >= 50_000 and "quotation" in missing_fields:
            policy_risks.append("5万円以上の備品購入は見積書が必要です。")
        if case_type is CaseType.PURCHASE and (state.amount_yen or 0) >= 500_000:
            policy_risks.append("50万円以上の購入は稟議起票を前提に確認してください。")

        if case_type is CaseType.BUSINESS_TRIP and "estimate" in missing_fields:
            policy_risks.append("概算費用がないため、事前承認の妥当性を判断できません。")
        if case_type is CaseType.BUSINESS_TRIP and "period" in missing_fields:
            policy_risks.append("出張期間が未記載のため、旅程確認ができません。")

        if "管理部門" in draft_result.approval_route:
            human_checkpoints.append("高額申請のため、管理部門の確認条件を個別に見直してください。")
        if case_type is CaseType.PURCHASE:
            human_checkpoints.append("IT 機器や SaaS の場合は情シス確認要否を人が確定してください。")

        return ReviewResult(
            missing_fields=missing_fields,
            policy_risks=policy_risks,
            human_checkpoints=human_checkpoints,
        )


class RuleBasedTraceBuilder:
    def build(
        self,
        classification: ClassificationDecision,
        docs: list[object],
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
        review_result: ReviewResult,
    ) -> PipelineTrace:
        verdict = "ready_with_review" if not clarification_items and not review_result.policy_risks else "needs_follow_up"
        documents = [getattr(doc, "title", "") for doc in docs]

        return PipelineTrace(
            classification=ClassificationTrace(
                case_type=classification.case_type.value,
                matched_keywords=classification.matched_keywords,
                rationale=classification.rationale,
            ),
            clarification=ClarificationTrace(
                extracted_fields=sorted(state.extracted_fields.keys()),
                missing_fields=[item.field for item in clarification_items],
                questions=[item.prompt for item in clarification_items],
            ),
            rule_references=RuleReferenceTrace(
                documents=documents,
                applied_rules=self._build_applied_rules(
                    classification.case_type, state, clarification_items, review_result
                ),
            ),
            review=ReviewTrace(
                verdict=verdict,
                policy_risks=review_result.policy_risks,
                human_checkpoints=review_result.human_checkpoints,
            ),
            timeline=[
                f"Intake Agent: '{classification.case_type.value}' に分類",
                f"Policy Retrieval Agent: {len(docs)} 件の関連文書を取得",
                f"Clarification Agent: {len(clarification_items)} 件の不足項目を抽出",
                "Draft Generation Agent: 申請草稿と承認ルート候補を生成",
                f"Review / Compliance Agent: {len(review_result.policy_risks)} 件の規程上の懸念を検出",
                "Logging / Ops Agent: trace を保存可能な形式で出力",
            ],
        )

    def _build_applied_rules(
        self,
        case_type: CaseType,
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
        review_result: ReviewResult,
    ) -> list[str]:
        rules = [
            "類型ごとの必須項目は knowledge/ 配下の policy と template を基準に確認",
            "共通承認ルールは金額帯ごとの承認レベル候補に反映",
        ]

        if case_type is CaseType.PURCHASE and (state.amount_yen or 0) >= 50_000:
            rules.append("備品購入が 5 万円以上のため見積書チェックを強化")
        if case_type is CaseType.PURCHASE and (state.amount_yen or 0) >= 500_000:
            rules.append("備品購入が 50 万円以上のため稟議承認を追加")
        if case_type is CaseType.BUSINESS_TRIP:
            rules.append("出張申請では旅程・概算費用・移動手段を必須項目として扱う")
        if case_type is CaseType.EXPENSE and any(item.field == "receipt" for item in clarification_items):
            rules.append("経費精算で領収書未確認の場合は理由メモと人手確認を要求")
        if review_result.policy_risks:
            rules.append("レビューで検出した規程リスクは trace にそのまま残す")

        return rules
