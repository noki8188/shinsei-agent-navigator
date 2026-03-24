# Future Work

## v0.33.0 時点で未対応の範囲

- 実システム連携
  - SSO、社員マスタ、稟議システム、経費精算システムとの接続
- ナレッジ取り込み
  - PDF、社内 Wiki、フォーム定義書、メール本文の取り込みと差分更新
- 会話制御
  - 複数案件の同時解釈、会話履歴に基づく長期コンテキスト管理、承認差し戻しの再編集
- コンプライアンス
  - 権限制御、監査ログの永続化、個人情報マスキング、操作証跡の保存
- 評価
  - 類型分類の精度測定、補問漏れ評価、レビュー誤検知率の計測
  - 実 provider を使った継続的な回帰評価と prompt 管理
  - fallback 発生率や retry 率の継続観測

## すでに着手した hardening

- `CaseClassifier`
  - OpenAI Responses API + Structured Outputs で schema 制約付きの実装に更新した
- `ClarificationAgent`
  - knowledge を一次ソースにした Structured Outputs 実装に更新した
- `DraftAgent`
  - rule-based の承認経路を維持しつつ、草稿本文を OpenAI Responses API で生成するようにした
- `Fallback`
  - validation error、API key 不足、OpenAI API 失敗時に agent 単位で rule-based fallback するようにした
- `Integration test`
  - API key がある場合だけ動く OpenAI smoke test を追加した
- `Evaluation`
  - rule_based と llm を同じ eval で比較できるようにした

## 先にやると効果が大きい項目

1. ナレッジソースの拡張と RAG 化
2. `ReviewAgent` の LLM 化と structured review 強化
3. 外部承認マスタ参照
4. 実 provider を含む継続評価と observability
