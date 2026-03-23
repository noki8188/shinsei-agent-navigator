# AGENTS.md

このファイルは、人間のコントリビューターと coding agent の両方に向けた、このリポジトリ専用の作業ガイドです。

## このリポジトリで大事にすること

- `agent workflow` としての説明責任を壊さない
- 単に動くより、なぜその結果になったかが追えることを優先する
- README とデモ画面の一貫性を保つ

## 変更時の原則

- backend の差し替えポイントは `agent_interfaces.py` を起点に考える
- 新しいロジックを入れるときは、できるだけ rule-based 実装か LLM 実装かを明確に分ける
- frontend では trace の可視化を後退させない
- knowledge は Markdown を一次ソースとして扱う

## 期待する作業フロー

1. 関連ファイルを読み、既存のシナリオと README を確認する
2. 実装変更が API 形状に影響するなら `docs/interfaces.md` も更新する
3. デモの見え方が変わるならスクリーンショット更新を検討する
4. `frontend` の build と `backend` の unittest を通す

## 変更の置き場所

- UI 変更: `frontend/`
- workflow と API: `backend/app/`
- テスト: `backend/tests/`
- ドキュメント: `README.md`, `docs/`, `examples/`

## 避けたいこと

- README と実装が食い違ったままにすること
- trace を単なる文字列ログに戻すこと
- 複数の責務を 1 つの巨大関数へ戻すこと
