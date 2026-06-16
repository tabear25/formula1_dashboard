# CLAUDE.md

このファイルは、このリポジトリで作業する際の Claude Code 向けガイドです。

## 最重要ルール（Most Important Rule）

**新しい修正や変更は、すべてこの CLAUDE.md に反映すること。**
コードの修正・機能追加・設定変更・バグ修正などを行った場合は、その内容をこの
CLAUDE.md に記録し、常に最新の状態を保つこと。

## プロジェクト概要（Overview）

F1 のレースデータを視覚化・分析するためのアプリケーション。
FastF1 ライブラリで過去のグランプリのセッションデータ（ラップタイム、テレメトリ、
順位など）を取得し、グラフやマップとして表示する。

2つの利用形態がある:
- **デスクトップ版（Tkinter）**: `main.py`
- **Web 版（Streamlit）**: `streamlit_app.py`（Vercel/Netlify では動かないため、
  Streamlit Cloud / Render / Railway / Fly.io 等の Python 対応 PaaS にデプロイする）

プロット生成（`core/charts.py`）とデータ取得ロジックは両版で共有している
（単一の真実のソース）。

- 言語 / フレームワーク: Python 3.9+ / Tkinter / Streamlit
- 主要ライブラリ: fastf1, pandas, matplotlib, seaborn, streamlit

## 主なファイル構成（Structure）

- `main.py`: デスクトップ版（Tkinter）のエントリポイント。GUI の構築と起動。
- `streamlit_app.py`: Web 版（Streamlit）のエントリポイント。
- `config.py`: キャッシュ設定・テーマカラー・Matplotlib スタイルなどの設定値。
- `service.py`: FastF1 を用いたデータ取得ロジック（デスクトップ版が使用）。
- `core/`: フレームワーク非依存の共有コア。
  - `core/charts.py`: matplotlib Figure / 結果テーブルを生成する純粋関数群
    （Tkinter 版・Streamlit 版の双方から呼ぶ）。データ無しは `ChartDataError` を送出。
  - `core/data.py`: Streamlit 用の FastF1 取得アダプタ（`st.cache_data` /
    `st.cache_resource` でスケジュール・セッションを保持）。
- `tabs/`: デスクトップ版の各分析タブ（overview, map, results, telemetry,
  lap scatter, compare, speed, scatter）。図の組み立ては `core/charts` に委譲し、
  `FigureCanvasTkAgg` での埋め込み・Treeview 描画のみ担当する。
- `ui/`: Tkinter UI 補助（`ui/sidebar.py`, `ui/main_tab.py`, `ui/animations.py`）。
- `.streamlit/config.toml`: Streamlit のダークテーマ設定。
- `Dockerfile`: Render/Railway/Fly 等での Streamlit コンテナ実行用。

## 実行方法（Run）

デスクトップ版:
```
pip install -r requirements.txt
python main.py
```

Web 版（ローカル）:
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

デプロイ手順は `README.md` の「Web版 / デプロイ（Streamlit）」を参照。

## 変更履歴（Change Log）

ここに修正・変更の内容を追記していく。新しいものを上に追加すること。

- **Streamlit デプロイ手順書を追加**: `DEPLOY_STREAMLIT.md` を新規作成。Streamlit
  Community Cloud でのデプロイ手順（対象ブランチへのコード配置、Create app での
  Repository/Branch/Main file=`streamlit_app.py` 指定、動作確認、更新の自動再デプロイ、
  無料枠の制約）と、Render/Railway/Fly（Dockerfile）の代替手段を 1 ファイルにまとめた。

- **Streamlit 版のレスポンシブデザイン対応**: PC / タブレット / スマホの各画面幅で
  見やすくなるよう `streamlit_app.py` を調整。
  - `_inject_responsive_css()` を追加し、`main()` 冒頭（`set_page_config` 直後）で注入。
    CSS メディアクエリで、見出しは `clamp()` によりビューポート幅に応じて滑らかに
    スケール、タブは折り返さず横スクロール（`overflow-x:auto`/`white-space:nowrap`）、
    タブレット（≤1024px）／スマホ（≤640px）で本文余白を段階的に縮小、スマホでは
    タブ文字を縮小し matplotlib 画像をコンテナ幅にフィットさせる。
  - 図描画を `st.pyplot(fig, use_container_width=True)` に変更し、列幅に追従させる。
  - `set_page_config` に `initial_sidebar_state="auto"`（狭幅で自動折りたたみ）。
  - 検証: `py_compile` OK / Streamlit health=ok・トップ200 / `AppTest` 例外0・
    タイトル描画・レスポンシブ CSS（`clamp(`＋`@media`）の注入を確認。

- **Web デプロイ対応（Streamlit 化）**: Tkinter GUI は Vercel/Netlify で動かせないため、
  ブラウザ利用できる Streamlit 版を追加した。デスクトップ版は維持。
  - 新規: `streamlit_app.py`（Web エントリ）、`core/charts.py`（Figure/結果テーブル生成の
    共有コア。`pyplot`・`tkinter` 非依存、データ無しは `ChartDataError`）、
    `core/data.py`（Streamlit キャッシュ付き FastF1 取得）、`.streamlit/config.toml`、
    `Dockerfile`。
  - 変更: `tabs/map_tab.py` `tabs/telemetry_tab.py` `tabs/speed_tab.py`
    `tabs/compare_tab.py` `tabs/scatter_tab.py` の各 `_render` を `core/charts.build_*`
    呼び出しへ委譲（図組み立てを共通化、埋め込みは従来どおり `FigureCanvasTkAgg`）。
    `tabs/results_tab.py` は `core/charts.build_results_table()` を使用し、`format_timedelta`
    と結果列構築ロジックを `core/charts` へ移設（後方互換のため再エクスポート）。
  - `requirements.txt` に `streamlit` を追加。`README.md` にデプロイ手順を追記。
  - デプロイ先は Streamlit Cloud / Render / Railway / Fly.io 等（Vercel/Netlify 非対応）。
    キャッシュ先は環境変数 `FASTF1_CACHE` で指定可（未設定時は一時ディレクトリ）。
  - 検証: 全ファイル `py_compile` OK / Xvfb でデスクトップ版がコード0で起動（リグレッション
    無し）/ Streamlit の health=ok・トップ200・`AppTest` 例外0 を確認。実セッションの
    テレメトリ描画はコードスペースの外向き通信制限により未確認（スケジュール取得は成功）。
    実データ確認はデプロイ環境／ローカル推奨。

- `main.py`: `fastf1.plotting.setup_mpl()` から廃止済みの `misc_mpl_mods=False`
  引数を削除（fastf1 3.6.0 で削除され、3.8 系では `FutureWarning` を出すため）。
  これにより起動時の警告が解消。Xvfb 上でのヘッドレス起動テストで GUI が
  正常に構築され、終了コード 0 で終了することを確認済み。
- （初回）CLAUDE.md を作成。「新しい修正や変更はすべて CLAUDE.md に反映する」
  ルールを明記。
