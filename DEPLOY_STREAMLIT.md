# Streamlit デプロイ手順（DEPLOY_STREAMLIT.md）

F1 Data Dashboard の **Web 版（`streamlit_app.py`）** を Streamlit Community Cloud に
デプロイするための手順をまとめたファイル。上から順にやれば公開できる。

---

## 0. 前提（必要なもの）

- GitHub アカウント（このリポジトリ `tabear25/formula1_dashboard` にアクセスできること）
- Streamlit Community Cloud アカウント（GitHub でサインインするだけ・無料）
- 特別な API キーや課金は **不要**（FastF1 は公開データ）

---

## 1. デプロイするコードを GitHub の対象ブランチに置く ⚠️最重要

Web 版のファイル（`streamlit_app.py`, `core/`, `.streamlit/config.toml` など）は
作業ブランチ `claude/claude-md-updates-w8v1ze` にある。**`main` にはまだ無い**ので、
次のどちらかを行う。

- **（推奨）`main` にマージする** → デプロイ画面で branch = `main` を選べる
- もしくはデプロイ画面で branch にこの作業ブランチを直接指定する

確認: GitHub 上で対象ブランチに以下が存在すること。
- `streamlit_app.py`（メインファイル）
- `requirements.txt`
- `core/charts.py` / `core/data.py`
- `.streamlit/config.toml`

---

## 2. 必要ファイルのチェック（すでに用意済み）

| ファイル | 役割 | 状態 |
|---|---|---|
| `streamlit_app.py` | Web 版エントリポイント（Main file に指定） | ✅ |
| `requirements.txt` | 依存（streamlit / fastf1 / pandas / matplotlib / seaborn） | ✅ |
| `.streamlit/config.toml` | ダークテーマ等の設定 | ✅ |

追加で作る必要のあるファイルは基本ない。Streamlit Cloud が `requirements.txt` を
自動でインストールする。

---

## 3. Streamlit Community Cloud でデプロイ

1. https://share.streamlit.io にアクセスし、**GitHub でサインイン**（リポジトリ連携を認可）。
2. **「Create app」**（または「New app」→「Deploy a public app from GitHub」）をクリック。
3. 次の 3 項目を指定する。

   | 項目 | 値 |
   |---|---|
   | Repository | `tabear25/formula1_dashboard` |
   | Branch | `main`（または作業ブランチ） |
   | Main file path | `streamlit_app.py` |

4. （任意）**Advanced settings** で Python バージョンを選択（3.9 以上推奨。未指定でも可）。
5. **「Deploy」** を押す。初回ビルド（依存インストール）に数分かかる。
6. 発行された URL（`https://<app-name>.streamlit.app`）でアプリが開けば完了。

> Secrets（環境変数）は不要。キャッシュ先 `FASTF1_CACHE` も未設定なら一時ディレクトリを
> 使う実装になっているため、設定しなくてよい。

---

## 4. 動作確認

1. 公開 URL を開く。
2. サイドバーで **開催年 → グランプリ → セッション** を選び「セッションを読み込む」。
   - 初回はデータ DL のため時間がかかる（2 回目以降はキャッシュで高速）。
3. ドライバーを選び、各タブ（Map / Results / Telemetry / 各種比較）が表示されれば成功。

---

## 5. 更新の反映

対象ブランチに push すると Streamlit Cloud が**自動で再デプロイ**する。
手動で再起動したい場合は、アプリ管理画面の「Reboot」から行う。

---

## 6. 制約・注意点（無料枠）

- **メモリ約 1GB**: FastF1 のフルテレメトリ読み込みはメモリを消費するため、
  非常に大きいセッションで稀に落ちることがある。
- **スリープ**: 一定時間アクセスが無いとアプリが休止する。復帰直後と初回ロードは遅い
  （キャッシュは揮発するため）。
- **公開範囲**: 無料枠の公開アプリは URL を知っていれば誰でも閲覧可。
  リポジトリ自体は private でもデプロイ可能。

---

## 代替: Render / Railway / Fly.io（Docker）

常時起動やメモリ増強が必要なら、リポジトリ同梱の **`Dockerfile`** でデプロイできる。
`$PORT` は各プラットフォームが自動注入する。

起動コマンド（Dockerfile に定義済み）:
```
streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0
```

※ Vercel / Netlify は Python の常時起動サーバーや重い依存に不向きなため非対応。
