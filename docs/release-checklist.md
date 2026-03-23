# Release Checklist

GitHub 公開前に最低限確認したい項目をまとめたチェックリストです。

## README / Docs

- README 冒頭 3 行で、何のプロジェクトかが伝わる
- README の相対リンクがすべて開ける
- README の画像パスがすべて存在する
- README の代表ユースケースと `examples/scenarios.md` が一致している
- `docs/architecture.md` `docs/interfaces.md` `docs/future-work.md` の説明が現実装と矛盾していない

## Commands

- backend のセットアップ手順が第三者視点で再現できる
- frontend のセットアップ手順が第三者視点で再現できる
- backend の起動コマンドが `127.0.0.1:8000` で動く
- frontend の起動コマンドが `127.0.0.1:3000` で動く
- `curl` の API 実行例がそのまま成功する

## Repository Metadata

- `frontend/package.json` と `frontend/package-lock.json` の package 名と version が一致している
- `backend/pyproject.toml` の package 名と version が README の説明と矛盾していない
- ライセンス表記と `LICENSE` の内容が公開方針に合っている
- `.env.example` が最小構成として分かりやすい
- `.gitignore` が `.venv` `node_modules` `.next` などの生成物を漏らしていない

## Content Quality

- 誤字脱字と表記ゆれがない
- 日本語として不自然な説明がない
- スクリーンショットが現行 UI と一致している
- 不要ファイルや一時生成物が混ざっていない
