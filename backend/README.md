# Backend

Python ベースの agent orchestration を担当する最小実装です。`v0.34.0` では、representative eval を 6 シナリオへ拡張し、frontend と README の trace / version 表現を整理しました。

## セットアップ

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 起動

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

LLM backend を使う場合:

```bash
export SHINSEI_WORKFLOW_BACKEND=llm
export SHINSEI_LLM_PROVIDER=openai
export SHINSEI_LLM_MODEL=gpt-5.4-mini
export SHINSEI_LLM_API_KEY=...
```

API key がない場合や Structured Outputs の検証に失敗した場合は、trace に理由を残して rule-based fallback します。

## 検証

```bash
cd backend
python3 -m unittest
python3 -m app.evals --backend all
```
