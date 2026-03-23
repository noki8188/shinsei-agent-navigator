from __future__ import annotations

from pathlib import Path

from app.models import CaseType, PolicyDoc


REPO_ROOT = Path(__file__).resolve().parents[2]


CASE_CONFIG: dict[CaseType, dict[str, object]] = {
    CaseType.EXPENSE: {
        "keywords": ["精算", "経費", "領収書", "会食", "交通費", "宿泊費", "立替"],
        "required_fields": {
            "amount": "金額が必要です。",
            "date": "利用日が必要です。",
            "purpose": "用途または支出目的が必要です。",
            "vendor": "支払先または利用先が必要です。",
            "receipt": "領収書またはレシートの有無が必要です。",
        },
        "docs": [
            ("経費申請ポリシー", "knowledge/expense/policy.md", "経費精算の対象と必須項目を定義"),
            ("経費申請テンプレート", "knowledge/expense/template.md", "申請本文のひな形"),
            ("共通承認ルール", "knowledge/common/approval-rules.md", "金額帯ごとの承認ルール"),
            ("申請・稟議運用ガイド", "knowledge/common/workflow-policy.md", "起票時の基本ルール"),
        ],
        "base_attachments": ["領収書"],
    },
    CaseType.PURCHASE: {
        "keywords": ["購入", "備品", "モニター", "ディスプレイ", "キーボード", "ライセンス", "SaaS", "稟議", "契約"],
        "required_fields": {
            "item_name": "購入対象が必要です。",
            "amount": "予定金額が必要です。",
            "purpose": "利用目的が必要です。",
            "delivery_date": "納期または利用開始時期が必要です。",
            "location": "設置場所または利用者が必要です。",
            "quotation": "見積書の有無が必要です。",
        },
        "docs": [
            ("備品購入申請ポリシー", "knowledge/purchase/policy.md", "備品購入時の条件と注意点"),
            ("備品購入申請テンプレート", "knowledge/purchase/template.md", "購入申請の本文ひな形"),
            ("共通承認ルール", "knowledge/common/approval-rules.md", "金額帯ごとの承認ルール"),
            ("申請・稟議運用ガイド", "knowledge/common/workflow-policy.md", "起票時の基本ルール"),
        ],
        "base_attachments": ["見積書", "製品リンクまたはカタログ"],
    },
    CaseType.BUSINESS_TRIP: {
        "keywords": ["出張", "顧客訪問", "研修", "展示会", "宿泊", "新幹線", "飛行機", "訪問"],
        "required_fields": {
            "destination": "出張先が必要です。",
            "period": "出張期間が必要です。",
            "purpose": "出張目的が必要です。",
            "estimate": "概算費用が必要です。",
            "transportation": "移動手段が必要です。",
        },
        "docs": [
            ("出張申請ポリシー", "knowledge/business_trip/policy.md", "出張申請の必須項目と注意点"),
            ("出張申請テンプレート", "knowledge/business_trip/template.md", "出張申請の本文ひな形"),
            ("共通承認ルール", "knowledge/common/approval-rules.md", "金額帯ごとの承認ルール"),
            ("申請・稟議運用ガイド", "knowledge/common/workflow-policy.md", "起票時の基本ルール"),
        ],
        "base_attachments": ["旅程表", "概算費用メモ"],
    },
}


class KnowledgeBase:
    def get_docs(self, case_type: CaseType) -> list[PolicyDoc]:
        docs: list[PolicyDoc] = []
        for title, relative_path, summary in CASE_CONFIG[case_type]["docs"]:
            path = REPO_ROOT / relative_path
            docs.append(
                PolicyDoc(
                    case_type=case_type.value,
                    title=title,
                    path=str(path),
                    summary=summary,
                )
            )
        return docs

    def read_doc(self, relative_path: str) -> str:
        return (REPO_ROOT / relative_path).read_text(encoding="utf-8")

    def get_required_fields(self, case_type: CaseType) -> dict[str, str]:
        return CASE_CONFIG[case_type]["required_fields"]  # type: ignore[return-value]

    def get_keywords(self, case_type: CaseType) -> list[str]:
        return CASE_CONFIG[case_type]["keywords"]  # type: ignore[return-value]

    def get_base_attachments(self, case_type: CaseType) -> list[str]:
        return list(CASE_CONFIG[case_type]["base_attachments"])  # type: ignore[arg-type]
