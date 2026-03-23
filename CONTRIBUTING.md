# Contributing

このリポジトリは、公開デモとしての見通しのよさと、業務 PoC としての説明責任を重視します。

## 基本方針

- まず README と `docs/` を読み、設計意図を合わせる
- 1 つの PR で 1 つの意図が分かる粒度に保つ
- 生成品質よりも、trace 可能性とレビュー容易性を優先する
- 実装変更時は frontend / backend / docs の整合性をなるべく一緒に更新する

## セットアップ

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 検証

変更時は少なくとも次を実行してください。

```bash
cd frontend
npm run build
```

```bash
cd backend
python3 -m unittest
```

## PR の観点

- 対象シナリオが `examples/scenarios.md` と矛盾していないか
- trace が説明可能になっているか
- rule-based 実装と将来の LLM 実装の境界を壊していないか
- README に公開向けの説明が必要か

## ドキュメント更新が必要なケース

- API 形状を変えたときは `docs/interfaces.md`
- workflow を変えたときは `docs/architecture.md`
- README のスクリーンショットやユースケースが変わるときは `README.md`
