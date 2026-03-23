from __future__ import annotations

import unittest

from app.models import CaseType, UserRequest
from app.pipeline import InternalApplicationNavigator


class InternalApplicationNavigatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.navigator = InternalApplicationNavigator()

    def test_classifies_purchase_request(self) -> None:
        result = self.navigator.handle(
            UserRequest(message="在宅勤務用に 27 インチモニターを 1 台買いたいです。予算は 8 万円くらいです")
        )
        self.assertEqual(result.case_type, CaseType.PURCHASE)

    def test_flags_missing_receipt_for_expense(self) -> None:
        result = self.navigator.handle(
            UserRequest(message="先週の会食代を精算したいです。金額は 12,000 円です")
        )
        self.assertEqual(result.case_type, CaseType.EXPENSE)
        self.assertIn("receipt", result.review_result.missing_fields)

    def test_flags_missing_estimate_for_business_trip(self) -> None:
        result = self.navigator.handle(
            UserRequest(message="大阪へ 2 日間の出張申請を出したいです。目的は顧客訪問です")
        )
        self.assertEqual(result.case_type, CaseType.BUSINESS_TRIP)
        self.assertIn("estimate", result.review_result.missing_fields)
        self.assertTrue(result.review_result.policy_risks)

    def test_adds_department_head_for_high_amount(self) -> None:
        result = self.navigator.handle(
            UserRequest(message="サーバー検証用に備品を購入したいです。金額は 12 万円です。用途は検証です。")
        )
        self.assertIn("部門長", result.draft_result.approval_route)

    def test_requires_ringi_for_large_purchase(self) -> None:
        result = self.navigator.handle(
            UserRequest(message="営業部向けに SaaS を導入したいです。金額は 80 万円です。用途は商談管理です。")
        )
        self.assertEqual(result.case_type, CaseType.PURCHASE)
        self.assertIn("稟議承認", result.draft_result.approval_route)
        self.assertIn("50万円以上の購入は稟議起票を前提に確認してください。", result.review_result.policy_risks)


if __name__ == "__main__":
    unittest.main()
