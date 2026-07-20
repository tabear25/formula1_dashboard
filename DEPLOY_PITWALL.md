# PITWALL デプロイ手順（DEPLOY_PITWALL.md）

**ローカルでサーバを立てたときと同じデザイン**（`server.py` + `web/` の PITWALL）を
そのまま Web に公開するための手順。Streamlit 版とは別アプリで、見た目・インタラクションは
ローカルの PITWALL と**完全に一致**する（同じフロントエンドを配信するため）。

---

## なぜ Vercel / Netlify では動かないのか

PITWALL は「プロセス常駐型の HTTP サーバ（stdlib `http.server`）＋セッションを
バックグラウンドスレッドでロード＋インメモリの LRU キャッシュ（2件保持）」という構造。
Vercel / Netlify はサーバーレス（リクエストごとに関数が起動・終了し、常駐プロセスや
プロセス内メモリを持てない）なので、この構造とは根本的に噛み合わない。

→ **常駐プロセスを動かせる PaaS**（Render / Railway / Fly.io 等）を使う。以下は Render 前提。

---

## 0. 前提

- GitHub アカウント（このリポジトリ `tabear25/formula1_dashboard` にアクセスできること）
- Render アカウント（GitHub でサインイン・無料枠あり）
- API キーや課金は不要（FastF1 は公開データ）

---

## 1. デプロイするコードを対象ブランチに置く ⚠️最重要

Render 用の設定（`render.yaml`）と `$PORT`/`0.0.0.0` 対応済みの `server.py` は
作業ブランチにある。`main` にマージするか、Render 側で対象ブランチを直接指定する。

対象ブランチに以下が存在することを確認:
- `server.py`（`--host` / `--port $PORT` / `FASTF1_CACHE` 対応済み）
- `render.yaml`（Render Blueprint）
- `web/`（`index.html` / `styles.css` / `js/` 一式）
- `requirements.txt`

---

## 2. Render でサービスを作成（Blueprint 推奨）

1. Render ダッシュボード → **New +** → **Blueprint**。
2. このリポジトリを選択。`render.yaml` が自動検出される。
3. 内容を確認して **Apply**。以下の設定でデプロイされる:
   - `runtime: python` / `plan: free`
   - build: `pip install -r requirements.txt`
   - start: `python server.py --host 0.0.0.0 --port $PORT --no-browser`
   - env: `PYTHON_VERSION=3.11.9`, `FASTF1_CACHE=/tmp/f1_cache`

Blueprint を使わず手動で作る場合は **New + → Web Service** を選び、
Runtime=Python、Build/Start コマンドと環境変数を上記と同じに設定すればよい。

---

## 3. 動作確認

- デプロイ完了後に払い出される `https://<service>.onrender.com/` を開く。
- 年 → グランプリ → セッションを選んで「読み込み」。
- **ローカルの `py server.py` と同じ画面**（ヘッダー / ドライバーチップ / スタッツ /
  各タブの自前 SVG チャート）が出れば成功。

---

## 4. 無料枠の制約（重要）

- **スリープ**: 無料 Web サービスは一定時間アクセスが無いと停止し、次アクセス時に
  コールドスタート（数十秒〜）する。
- **キャッシュ揮発**: `/tmp` は再デプロイ・スリープ復帰で消えるため、初回セッションの
  FastF1 ダウンロード（数分かかることがある）が都度発生する。永続ディスク（Render の
  Disk / 有料）を `FASTF1_CACHE` にマウントすれば高速化できる。
- **メモリ**: 無料枠は RAM 512MB 程度。決勝のフルセッション（laps + telemetry）は
  メモリを食うため、重いセッションで落ちる場合は有料インスタンスへ。

---

## 代替: Railway / Fly.io

いずれも常駐プロセスを動かせる。起動コマンドは Render と同じ考え方:

```
python server.py --host 0.0.0.0 --port $PORT --no-browser
```

- **Railway**: リポジトリを接続し、Start Command に上記を設定。`$PORT` は自動注入。
- **Fly.io**: `fly launch` で Python を検出。`fly.toml` の `internal_port` を `$PORT`
  ではなく固定値にする場合は、Start Command 側もその値に合わせる。

環境変数 `FASTF1_CACHE` を書き込み可能パスに向ける点は各社共通。
