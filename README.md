# 社内申請ナビゲーター

AIエージェントを活用して、申請・承認・問い合わせ業務を半自動化する実践的PoC

> English summary: An internal workflow support PoC for Japanese companies. The system uses multiple AI agents to classify employee requests, retrieve policy documents, ask follow-up questions, draft applications, review compliance, and keep an audit trail.

## 背景 / 課題

日本企業の社内申請業務では、次のような課題が起こりやすくなります。

- 申請ルールが PDF、Excel、メール、社内 Wiki に分散している
- 誰に確認すべきかが分かりにくい
- 申請書ドラフトの作成に時間がかかる
- 情シス、総務、経理への問い合わせが集中しやすい
- 部門間のコミュニケーションコストが高い

本プロジェクトは、これらを「AI で全自動化する」のではなく、`代替ではなく、分業の再設計` として扱います。  
agent が定型的な整理・補問・起草・確認を担い、人は最終判断と例外対応に集中する構成です。

## 解決したいこと

従来は人手で分断されていた業務整理、仕様化、確認、申請ドラフト作成を、AI エージェントの協調によって小さく実装し、現場で試せる形に落とし込むことを目的としています。

この PoC は、次のような利用イメージを想定しています。

- 「出張精算したい」
- 「新しいモニターを買いたい」
- 「この支出はどの科目に入るか知りたい」
- 「申請に必要な添付資料を教えてほしい」
- 「誰が承認者になるか確認したい」
- 「先に申請ドラフトを作ってほしい」

## 対象業務

v0.1 では、初期スコープを以下の 3 類型に絞ります。

- `expense`: 経費申請
- `purchase`: 備品購入申請
- `business_trip`: 出張申請

初版では実データを扱わず、リポジトリ内の Markdown で作成したサンプル規程、FAQ、承認ルール、申請テンプレートを知識ソースとして使用します。

## Before / After

### Before

- ルールが分散していて探しづらい
- 確認先が分かりにくい
- 申請ドラフト作成の負荷が高い
- 問い合わせが特定部門に集中する

### After

- 自然言語で申請相談できる
- 不足情報を agent が補問する
- 申請ドラフトと必要添付を自動生成する
- 承認フロー候補を提示する
- 人は最終確認と承認に集中できる

## Agent 構成

本プロジェクトでは、役割を分けた 6 つの agent を前提にしています。

1. `Intake Agent`
   ユーザー入力を読み、対象の申請類型を判定します。
2. `Policy Retrieval Agent`
   規程、FAQ、承認ルール、テンプレートを検索して必要な文書を集めます。
3. `Clarification Agent`
   金額、用途、見積書の有無、出張先など不足情報を洗い出して補問します。
4. `Draft Generation Agent`
   申請草稿、必要添付、承認経路候補、注意点を生成します。
5. `Review / Compliance Agent`
   不足情報、規程抵触の疑い、上位承認の必要性を確認します。
6. `Logging / Ops Agent`
   入力、判断経路、要人手確認事項を記録して監査性を確保します。

## 業務フロー

1. 社員が Web チャット UI に自然言語で相談を入力する
2. Intake Agent が `expense` `purchase` `business_trip` のいずれかを分類する
3. Policy Retrieval Agent が関連文書を収集する
4. Clarification Agent が不足項目を抽出し、追加質問を返す
5. Draft Generation Agent が申請草稿と必要添付を生成する
6. Review / Compliance Agent が規程上の懸念や人手確認ポイントを返す
7. Logging / Ops Agent が判断ログを残す

## 公開インターフェース

初版で固定する最小インターフェースは以下です。

- `UserRequest`: 自然言語の相談入力
- `CaseType`: `expense` `purchase` `business_trip`
- `PolicyDoc`: Markdown ベースの規程・FAQ・承認ルール
- `ClarificationItem`: 追加で確認すべき項目
- `DraftResult`: 申請草稿、必要添付、承認経路候補、注意点
- `ReviewResult`: 不足情報、規程抵触の疑い、要人手確認事項

詳細は [docs/interfaces.md](/Users/wuzixuan/Documents/codex/syanai/docs/interfaces.md) を参照してください。

## アーキテクチャ

- `frontend/`: Next.js ベースの相談 UI
- `backend/`: Python ベースの agent orchestration とルール判定
- `knowledge/`: サンプル規程、FAQ、承認ルール、申請テンプレート
- `docs/`: 設計資料
- `examples/`: デモシナリオ

設計の詳細は [docs/architecture.md](/Users/wuzixuan/Documents/codex/syanai/docs/architecture.md) にまとめています。

## スクリーンショット

![社内申請ナビゲーターのデモ画面](./docs/images/demo-home.png)

## 開発プロセス

本プロジェクトは、日本式の開発プロセスを README の物語としても中心に置きます。

### 1. 要件定義

- 相談内容を申請ユースケースへ整理する
- actor、業務イベント、例外条件を抽出する
- 未確定事項と前提条件を洗い出す

### 2. 基本設計

- 画面一覧、agent 一覧、データ項目を定義する
- 申請フローと承認ルートを図式化する
- ログ項目と権限境界を明確にする

### 3. 詳細設計

- prompt と tool interface を具体化する
- 類型別の必須項目と例外条件を設計する
- テスト観点と受入条件を詳細化する

### 4. 開発

- Codex を使ってリポジトリ骨格を作る
- フロントエンドとバックエンドの最小構成を実装する
- 知識ソースとデモシナリオを同期させる

### 5. テスト

- UT で分類、補問、承認ルール判定を確認する
- IT で agent 間の受け渡しを確認する
- ST で業務シナリオを通しで確認する

### 6. リリース

- README を GitHub 公開向けに整える
- 既知の制約と今後の拡張を明記する
- デモ実行手順を固定する

### 7. 運用保守

- ログから問い合わせ傾向を確認する
- FAQ の追加候補を抽出する
- ルール変更時の差分反映をしやすくする

補足は [docs/development-process.md](/Users/wuzixuan/Documents/codex/syanai/docs/development-process.md) に記載しています。

## テスト方針

### UT

- 申請分類が 3 類型で正しく分かれること
- 不足情報抽出が類型ごとの必須項目を落とさないこと
- 承認ルール判定が金額条件や添付要件を反映すること

### IT

- `分類 → 規程参照 → 補問 → 草稿生成 → レビュー` が順につながること
- 各 agent の出力が次の agent に受け渡されること

### ST

- `10万円未満の備品購入`
- `領収書不足の経費申請`
- `見積書未添付の出張関連申請`

## 人が担うこと

agent に任せない領域も明示します。

- 最終的な業務判断
- セキュリティと権限設計
- リリース承認
- 受入判定
- 重要な例外対応
- ガバナンス整備

## セットアップ

### Frontend

```bash
cd frontend
npm install
npm run dev
```

本番ビルド確認:

```bash
cd frontend
npm run build
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

環境変数 `NEXT_PUBLIC_API_BASE_URL` を設定すると、フロントエンドからバックエンドに接続できます。未設定時は `http://127.0.0.1:8000` を使用します。

## 実行手順

1. バックエンドを起動する

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

2. フロントエンドを起動する

```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

3. ブラウザで `http://127.0.0.1:3000` を開く

## 実行例

### 画面からの入力例

- 「在宅勤務用に 27 インチモニターを 1 台買いたいです。予算は 8 万円くらいです」
- 「先週の会食代を精算したいです。金額は 12,000 円です」
- 「営業部で使う商談管理 SaaS を導入したいです。年額 80 万円です。来月から利用開始したいです」

### API 実行例

```bash
curl -X POST http://127.0.0.1:8000/api/chat/demo \
  -H "Content-Type: application/json" \
  -d '{"message":"大阪へ 2 日間の出張申請を出したいです。目的は顧客訪問です"}'
```

返却例の要点:

- `caseType`: `business_trip`
- `clarificationItems`: 概算費用、移動手段、期間などの不足情報
- `draftResult`: 申請草稿、必要添付、承認ルート候補
- `reviewResult`: 規程上の懸念と人手確認ポイント

詳細なシナリオは [examples/scenarios.md](/Users/wuzixuan/Documents/codex/syanai/examples/scenarios.md) を参照してください。

## 制約事項

- v0.1 はサンプル規程と簡易ルール判定を用いた PoC であり、正式な社内規程や承認ワークフロー連携は未実装
- 自然言語理解はキーワードと軽量ルールベースが中心で、複雑な文脈理解や複数案件の同時解釈には未対応
- PDF、社内 Wiki、メール本文、SSO、申請システム連携は未実装
- agent の出力は下書きであり、提出前の最終判断と承認責任は人が持つ

## 今後の展望

- Markdown 以外に PDF、社内 Wiki、フォーム定義書を取り込めるようにする
- 承認経路を固定ルールから外部マスタ参照へ拡張する
- agent の評価指標を整備し、誤分類や補問漏れを継続監視する
- 人と agent の協調を前提とした運用ルールと governance を強化する

## 参考資料

一次情報のみを採用しています。

- [OpenAI Codex](https://openai.com/codex/)
- [OpenAI: Introducing Codex](https://openai.com/index/introducing-codex/)
- [Anthropic: Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [IPA: DX動向2025](https://www.ipa.go.jp/digital/chousa/dx-trend/dx-trend-2025.html)
- [JIPDEC: 企業IT利活用動向調査2025](https://www.jipdec.or.jp/news/news/20250305.html)
