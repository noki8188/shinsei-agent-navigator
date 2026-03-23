from __future__ import annotations

import re
from dataclasses import dataclass

from app.knowledge_base import KnowledgeBase
from app.models import (
    CaseType,
    ClarificationItem,
    DraftResult,
    PipelineResponse,
    ReviewResult,
    UserRequest,
)


CITY_WORDS = ["東京", "大阪", "名古屋", "福岡", "札幌", "沖縄", "京都", "横浜"]
TRANSPORT_WORDS = ["新幹線", "飛行機", "航空", "タクシー", "車", "レンタカー", "電車", "バス"]


@dataclass(slots=True)
class AnalysisState:
    amount_yen: int | None
    extracted_fields: dict[str, object]


class InternalApplicationNavigator:
    def __init__(self, knowledge_base: KnowledgeBase | None = None) -> None:
        self.knowledge_base = knowledge_base or KnowledgeBase()

    def handle(self, request: UserRequest) -> PipelineResponse:
        case_type = self._classify(request.message)
        state = self._analyze_message(case_type, request.message)
        docs = self.knowledge_base.get_docs(case_type)
        clarification_items = self._build_clarifications(case_type, request.message, state)
        draft_result = self._build_draft(case_type, request.message, state, clarification_items)
        review_result = self._review(case_type, state, clarification_items, draft_result)
        trace = self._build_trace(case_type, docs, clarification_items, review_result)

        return PipelineResponse(
            case_type=case_type,
            policy_docs=docs,
            clarification_items=clarification_items,
            draft_result=draft_result,
            review_result=review_result,
            trace=trace,
        )

    def _classify(self, message: str) -> CaseType:
        scores: dict[CaseType, int] = {}
        for case_type in CaseType:
            score = sum(keyword in message for keyword in self.knowledge_base.get_keywords(case_type))
            scores[case_type] = score

        if "出張" in message:
            return CaseType.BUSINESS_TRIP
        if any(word in message for word in ["購入", "備品", "モニター", "ディスプレイ", "ライセンス", "SaaS", "稟議", "契約"]):
            return CaseType.PURCHASE
        if any(word in message for word in ["精算", "領収書", "会食", "交通費", "宿泊費"]):
            return CaseType.EXPENSE

        return max(scores, key=scores.get)

    def _analyze_message(self, case_type: CaseType, message: str) -> AnalysisState:
        amount_yen = self._extract_amount_yen(message)
        fields: dict[str, object] = {}

        if amount_yen is not None:
            fields["amount"] = amount_yen
            fields["estimate"] = amount_yen

        if any(token in message for token in ["目的", "用途", "顧客訪問", "会食", "在宅勤務", "研修", "展示会", "契約"]):
            fields["purpose"] = self._extract_sentence_after_token(message, ["目的は", "用途は"]) or "記載あり"

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

        if any(token in message for token in ["モニター", "ディスプレイ", "キーボード", "マウス", "ライセンス", "備品", "SaaS", "クラウド", "契約"]):
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

    def _build_clarifications(
        self, case_type: CaseType, message: str, state: AnalysisState
    ) -> list[ClarificationItem]:
        clarification_items: list[ClarificationItem] = []
        required_fields = self.knowledge_base.get_required_fields(case_type)

        for field, reason in required_fields.items():
            if field not in state.extracted_fields:
                clarification_items.append(
                    ClarificationItem(
                        field=field,
                        reason=reason,
                        prompt=self._clarification_prompt(case_type, field, message),
                    )
                )

        return clarification_items

    def _build_draft(
        self,
        case_type: CaseType,
        message: str,
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
    ) -> DraftResult:
        attachments = self.knowledge_base.get_base_attachments(case_type)
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

        body = self._build_body(case_type, message, state, clarification_items)

        return DraftResult(
            title=title_map[case_type],
            body=body,
            attachments=attachments,
            approval_route=self._approval_route(case_type, state),
            notes=notes,
        )

    def _review(
        self,
        case_type: CaseType,
        state: AnalysisState,
        clarification_items: list[ClarificationItem],
        draft_result: DraftResult,
    ) -> ReviewResult:
        missing_fields = [item.field for item in clarification_items]
        policy_risks: list[str] = []
        human_checkpoints = [
            "最終提出前に承認者と正式な社内ルールを確認してください。"
        ]

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

    def _build_trace(
        self,
        case_type: CaseType,
        docs: list[object],
        clarification_items: list[ClarificationItem],
        review_result: ReviewResult,
    ) -> list[str]:
        return [
            f"Intake Agent: '{case_type.value}' に分類",
            f"Policy Retrieval Agent: {len(docs)} 件の関連文書を取得",
            f"Clarification Agent: {len(clarification_items)} 件の不足項目を抽出",
            "Draft Generation Agent: 申請草稿と承認ルート候補を生成",
            f"Review / Compliance Agent: {len(review_result.policy_risks)} 件の規程上の懸念を検出",
            "Logging / Ops Agent: trace を保存可能な形式で出力",
        ]

    def _approval_route(self, case_type: CaseType, state: AnalysisState) -> list[str]:
        route = ["申請者", "所属長"]
        amount = state.amount_yen or 0

        if amount >= 50_000:
            route.append("部門長")
        if amount >= 200_000:
            route.append("管理部門")
        if case_type is CaseType.PURCHASE and any(
            word in str(state.extracted_fields.get("item_name", "")) for word in ["記載あり"]
        ):
            route.append("情シス確認")
        if case_type is CaseType.PURCHASE and amount >= 500_000:
            route.append("稟議承認")

        return route

    def _build_body(
        self,
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

    def _clarification_prompt(self, case_type: CaseType, field: str, message: str) -> str:
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

    def _extract_amount_yen(self, message: str) -> int | None:
        match = re.search(r"(\d[\d,]*)\s*(万円|円)", message)
        if not match:
            return None

        value = int(match.group(1).replace(",", ""))
        unit = match.group(2)
        if unit == "万円":
            return value * 10_000
        return value

    def _extract_sentence_after_token(self, message: str, tokens: list[str]) -> str | None:
        for token in tokens:
            if token in message:
                _, _, suffix = message.partition(token)
                return suffix.strip(" 。")
        return None
