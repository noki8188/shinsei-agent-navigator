# アーキテクチャ概要

## 目的

`社内申請ナビゲーター` は、社内申請に関する自然言語相談を受け取り、複数 agent の役割分担で申請支援結果を返す PoC です。  
`v0.2` では、公開デモとして理解しやすいことに加えて、rule-based 実装と将来の LLM 実装の境界を明文化しました。

## システム構成

```mermaid
flowchart LR
    U["社員"] --> F["Next.js Web UI"]
    F --> API["FastAPI /api/chat/demo"]
    API --> O["Workflow Orchestrator"]
    O --> CC["CaseClassifier"]
    O --> MA["MessageAnalyzer"]
    O --> CA["ClarificationAgent"]
    O --> DA["DraftAgent"]
    O --> RA["ReviewAgent"]
    O --> TB["TraceBuilder"]
    O --> KB["KnowledgeBase"]
    KB --> K["knowledge/*.md"]
    CC --> R1["Rule-based implementation"]
    MA --> R1
    CA --> R1
    DA --> R1
    RA --> R1
    TB --> R1
    CC -. swap .-> L1["Future LLM implementation"]
    CA -. swap .-> L1
    DA -. swap .-> L1
    RA -. swap .-> L1
```

## コンポーネント

### Frontend

- Next.js による単一ページの相談 UI
- 分類結果、補問候補、申請草稿、承認経路、レビュー結果を表示
- `v0.2` では classification / clarification / rule references / review を含む `agent trace` を可視化

### Backend

- `InternalApplicationNavigator` が workflow orchestration を担当
- 各ステージは抽象インターフェース経由で差し替え可能
- 現在の既定実装は rule-based だが、同じ interface を満たす LLM 実装へ移行できる

### Knowledge

- Markdown ベースの規程、FAQ、承認ルール、テンプレート
- 類型別文書と共通ルールを分離
- 将来は PDF 抽出結果や外部ナレッジベースを追加予定

## 差し替えポイント

`backend/app/agent_interfaces.py` で定義している主な差し替えポイントは次の通りです。

- `CaseClassifier`
- `MessageAnalyzer`
- `ClarificationAgent`
- `DraftAgent`
- `ReviewAgent`
- `TraceBuilder`

rule-based 実装は `backend/app/pipeline.py` にあり、将来の LLM 実装は同じ interface を満たす別モジュールとして追加できます。

## データフロー

1. UI が自然言語メッセージを送る
2. `CaseClassifier` が申請類型を判定する
3. `KnowledgeBase` が関連文書を取得する
4. `ClarificationAgent` が不足項目を抽出する
5. `DraftAgent` が草稿と必要添付を作る
6. `ReviewAgent` が規程抵触や要確認事項を返す
7. `TraceBuilder` が判断過程をレビュー可能な trace として残す

## 設計上の前提

- `v0.2` は実データ非対応
- 対象業務は `expense` `purchase` `business_trip` のみ
- 生成結果は提案であり、最終判断は人が行う
- 承認ルートはサンプル規程に基づく候補表示であり、正式ワークフロー連携は未実装
