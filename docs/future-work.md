# Future Work

## v0.2 時点で未対応の範囲

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

## LLM 実装へ進めるときの差し替え候補

- `CaseClassifier`
  - ルールベース分類を intent classification モデルへ置換
- `ClarificationAgent`
  - 必須項目検出を schema-guided extraction へ置換
- `DraftAgent`
  - Markdown テンプレート埋め込み中心の実装を、規程引用付きの生成へ置換
- `ReviewAgent`
  - 固定ルール中心のチェックを、理由付き compliance review へ置換
- `TraceBuilder`
  - 単純な文字列 trace を、根拠付き reasoning trace と評価メタデータへ拡張

## 先にやると効果が大きい項目

1. ナレッジソースの拡張
2. 類型ごとのテストケース増強
3. 外部承認マスタ参照
4. LLM 実装の PoC と比較評価
