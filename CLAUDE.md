# CLAUDE.md

このファイルは、このリポジトリで作業する際の Claude Code 向けガイドです。

## 最重要ルール（Most Important Rule）

**新しい修正や変更は、すべてこの CLAUDE.md に反映すること。**
コードの修正・機能追加・設定変更・バグ修正などを行った場合は、その内容を末尾の「変更履歴（Change Log）」に記録し、常に最新の状態を保つこと。

## プロジェクト概要（Overview）

F1 のレースデータを可視化・分析するアプリケーション。[FastF1](https://docs.fastf1.dev/) で過去グランプリのセッションデータ（ラップ・テレメトリ・順位・位置）を取得して表示する。UI は3系統ある：

1. **Web版 PITWALL（ローカル利用・推奨・2026-07 追加）** — `server.py`（stdlib http.server の JSON API）+ `web/`（vanilla JS の SPA、ビルド不要・自前SVG描画）。`py server.py` で `http://127.0.0.1:8380/`。追加 pip 依存なし。
2. **Web版 Streamlit（PaaSデプロイ用）** — `streamlit_app.py`。Vercel/Netlify では動かないため、Streamlit Cloud / Render / Railway / Fly.io 等の Python 対応 PaaS にデプロイする（手順は `DEPLOY_STREAMLIT.md`）。
3. **Tkinter デスクトップ版（従来）** — `main.py` + `ui/` + `tabs/`（matplotlib / seaborn / Treeview）。

- Tkinter 版と Streamlit 版は、プロット生成（`core/charts.py`）とデータ取得ロジックを共有している（単一の真実のソース）。PITWALL は独立実装で、FastF1 キャッシュ（`_fastf1_cache/`）のみ共用する。
- 言語 / フレームワーク: Python 3.9+ / Tkinter / Streamlit。主要ライブラリ: fastf1, pandas, matplotlib, seaborn, streamlit（PITWALL は stdlib + fastf1 / pandas のみ）。
- Tkinter 版は単一プロセスの GUI。`main.py` の `F1DashboardApp(tk.Tk)` が左サイドバー（`ui/sidebar.py`）＋右のタブ群（`ui/main_tab.py` = `ttk.Notebook`）を `PanedWindow` に並べる構成。
- FastF1 のネットワーク取得は重いので、`service.py` が `ThreadPoolExecutor` で非同期ロードし、ローカルの `_fastf1_cache/` にキャッシュする。
- 永続的な自前データベースは持たない。データ源は FastF1（＝F1 公式タイミング等）のみ。

## リポジトリ構造

> **重要 / 入れ子構造**: このプロジェクトのルートは `private_workplace\formula1_dashboard\formula1_dashboard\`（このファイルがある階層）。1つ上の `private_workplace\formula1_dashboard\` は `_fastf1_cache` のバイナリだけを追跡する**リモート無しの別 Git リポジトリ**で、実体ではない。作業・commit・push はすべてこの内側リポジトリで行う（GitHub リモート `tabear25/formula1_dashboard`）。

```
formula1_dashboard/                 # ← プロジェクトルート（内側）。git remote = tabear25/formula1_dashboard
├── .claude/
│   └── settings.local.json         # 権限allowlist（py *, 依存バージョン確認コマンドを許可）
├── .streamlit/config.toml          # Streamlit のダークテーマ設定
├── .vscode/settings.json           # cSpell の単語登録のみ
├── .gitignore                      # task_tracker.md, project.md, __pycache__/, _fastf1_cache/, *.pyc
├── README.md                       # 日本語の利用ガイド（使い方・タブ説明・デプロイ）
├── DEPLOY_STREAMLIT.md             # Streamlit 版のデプロイ手順書
├── Dockerfile                      # Render/Railway/Fly 等での Streamlit コンテナ実行用
├── cloud.md                        # アニメーション実装メモ＋過去のバグ修正記録（FastF1/seaborn 破壊的変更対応）
├── requirements.txt                # fastf1, pandas, matplotlib, seaborn, streamlit
├── config.py                       # 全定数：テーマ色 COLOR_*, YEAR_LIST, キャッシュ設定, APP_TITLE, MPL_STYLE
├── service.py                      # FastF1Service（非同期ロード）＋ CacheManager（キャッシュ管理・掃除）
├── core/                           # フレームワーク非依存の共有コア（Tkinter版・Streamlit版が使用）
│   ├── charts.py                   # matplotlib Figure / 結果テーブルを生成する純粋関数群。データ無しは ChartDataError
│   └── data.py                     # Streamlit 用の FastF1 取得アダプタ（st.cache_data / st.cache_resource）
├── streamlit_app.py                # 【Streamlit版】Web エントリポイント（レスポンシブCSS注入込み）
├── server.py                       # 【PITWALL】stdlib HTTPサーバ + /api/*（schedule/load/status/session/telemetry/trackmap/replay）
├── start_pitwall.cmd               # 【PITWALL】ダブルクリック起動用ランチャー
├── web/                            # 【PITWALL】フロントエンド（ビルド不要の ES modules）
│   ├── index.html / styles.css     # シェルとデザイントークン（ダーク固定。--surface-1 は server.py の CHART_SURFACE と一致必須）
│   └── js/                         # api / state / derive / svg / format + views/（replay, lapchart, gaps, pace, violin, degradation, strategy, pitstops, sectors, dominance, telemetry, track, quali, results, control）
├── main.py                         # 【Tkinter版】エントリポイント：F1DashboardApp(tk.Tk)・ttkスタイル定義・main()
├── ui/
│   ├── __init__.py                 # 空
│   ├── sidebar.py                  # Sidebar(tk.Frame)：選択UI＋分析ボタン＋プログレスバー。バックグラウンドでロード
│   ├── main_tab.py                 # MainTab(ttk.Notebook)：各タブを init_* で生成し show_* をラップするファサード
│   └── animations.py               # CloudLoader / typewriter_effect / animate_treeview_rows / fade_in_label / show_chart_with_loader
└── tabs/                           # 【Tkinter版】タブ1枚 = 1モジュール。すべて init_X / show_X 関数ペア
    ├── __init__.py                 # 空
    ├── overview.py                 # init_overview / show_overview（タイプライター表示の初期画面）
    ├── map_tab.py                  # init_map / show_map（サーキットマップ＋最速ラップ軌跡）
    ├── results_tab.py              # init_results_tab / show_session_results（結果表。列構築・format_timedelta は core/charts へ移設済み）
    ├── telemetry_tab.py            # init_telemetry / show_telemetry（単一ドライバの速度テレメトリ）
    ├── scatter_tab.py              # init_scatter/show_scatter_compare ＋ init_single_scatter/show_single_driver_scatter
    ├── compare_tab.py              # init_compare / show_compare（複数ドライバのラップタイム バイオリンプロット）
    └── speed_tab.py                # init_speed / show_speed_compare（複数ドライバの最速ラップ速度比較）
```

※ `tabs/*` の図の組み立ては `core/charts.build_*` に委譲済みで、各タブは `FigureCanvasTkAgg` での埋め込み・Treeview 描画のみ担当する。

## セットアップと実行

### 前提

- **このマシンには `python` が PATH に無い。`py`（`C:\WINDOWS\py.exe` / Python 3.13.0）を使う。** README は `python main.py` と書いてあるが、実際のコマンドは `py main.py`。`.claude/settings.local.json` も `py *` を許可済み。
- **Tkinter 版は GUI アプリなのでディスプレイ環境が必須**。ヘッドレス / CI では起動に失敗する。PITWALL / Streamlit はブラウザで動くためこの制約がない。
- 初回ロードやキャッシュが無い場合は FastF1 がネットから取得するため、インターネット接続が必要で時間がかかる。

### インストール

```powershell
py -m pip install -r requirements.txt
```

> 依存追加・更新は無断で行わない（本人確認を取る）。FastF1 のバージョンを上げるときは「よくある落とし穴」の API 差異に注意。

### 実行（Web版 PITWALL）

```powershell
py server.py            # http://127.0.0.1:8380/ が自動で開く。--port / --no-browser あり
```

ヘッドレス検証: ブラウザ実UIの確認は headless Chrome + CDP（`--remote-debugging-port` + Node の WebSocket で Runtime.evaluate / Page.captureScreenshot）で行える。GUI必須の Tkinter 版と違い自動検証が可能。

### 実行（Web版 Streamlit・ローカル）

```powershell
streamlit run streamlit_app.py    # http://localhost:8501
```

デプロイ手順は `DEPLOY_STREAMLIT.md` と README の「Web版 / デプロイ（Streamlit）」を参照。キャッシュ先は環境変数 `FASTF1_CACHE` で指定可（未設定時は一時ディレクトリ）。

### 実行（Tkinter版）

```powershell
py main.py
```

GUI ウィンドウ（既定 1366x865）が立ち上がる。左サイドバーで年 → グランプリ → セッションの順に選ぶとロードが始まり、完了後にドライバー一覧が出る。ドライバーを選んで各分析ボタンを押す。

### 依存バージョン確認（settings.local.json で許可済み）

```powershell
py -c "import fastf1, pandas, matplotlib, seaborn; print('fastf1', fastf1.__version__); print('pandas', pandas.__version__); print('matplotlib', matplotlib.__version__); print('seaborn', seaborn.__version__)"
```

### テスト / lint

**テストも lint も CI も存在しない。** Tkinter 版の確認は手動で `py main.py` を起動して対象タブを実際に描画する。PITWALL は headless Chrome + CDP、Streamlit は `py_compile` + `AppTest` で検証した実績がある。テスト未実施のときはその旨を明示する。

## アーキテクチャと処理フロー（Tkinter版）

### 起動

`main.py` → `F1DashboardApp(tk.Tk)`：`FastF1Service()` 生成 → `CacheManager.cleanup_cache()` → `PanedWindow` に `Sidebar`（weight=0, width=260）と `MainTab`（weight=1）を追加 → ttk スタイル（`clam`/`alt` テーマ＋ `config.py` の色）を全ウィジェットに適用。`sys._f1_dashboard_started` フラグで二重起動をガードしている。

### 選択 → ロード → 描画（`ui/sidebar.py`）

```
年を選択        → service.get_event_schedule_async(year)         → GPリスト更新
GP＋セッション選択 → service.load_session_async(year, gp, ses)      → ドライバー一覧更新
                                                                  → main_tab.show_map(session)
                                                                  → main_tab.show_session_results_data(session)
分析ボタン       → main_tab.show_*（選択ドライバーを渡してチャート描画）
```

- `service.py`：`FastF1Service` は `ThreadPoolExecutor(max_workers=4)` に処理を submit するだけ。`load_session_async` は内部で `session.load(laps=True, telemetry=True, weather=True, messages=True)` を呼ぶ。
- **Tkinter スレッド規約（厳守）**：ロードは `threading.Thread(daemon=True)` ＋ Executor でバックグラウンド実行し、**UI 更新は必ずメインスレッドへ戻す**。パターンは `fut.add_done_callback(lambda f: self.after(0, _done_callback, f))`。バックグラウンドスレッドから直接ウィジェットを触らない（Tkinter はスレッドセーフでない）。ロード中はプログレスバーを `indeterminate` で回す。

### タブのファサード（`ui/main_tab.py`）

`MainTab(ttk.Notebook)` は起動時に各 `tabs/*` の `init_*` を呼んでフレームを生成し保持する。公開メソッド（`show_overview` / `show_map` / `show_single_driver_telemetry` / `show_single_driver_scatter` / `show_laptime_comparison` / `show_speed_comparison` / `show_scatter_comparison` / `show_session_results_data`）は、対応タブを `self.select()` で前面化してから `tabs/*` の `show_*` に委譲する。Sidebar はこのファサード経由でのみタブを操作する。

### タブモジュールの共通形（`tabs/*.py`）

各タブは関数ペアで書く。**新しいタブを足すときもこの形に従う**：

- `init_X(notebook)` … `tk.Frame`/`ttk.Frame` を作り `notebook.add(frame, text="…")` して frame を返す。`main_tab.py` の `__init__` に1行追加する。
- `show_X(frame, session, ...)` … 先頭で `for w in frame.winfo_children(): w.destroy()` して再描画する（毎回作り直す方式）。
- チャート系は直接描かず `show_chart_with_loader(frame, "…読み込み中…", COLOR_FRAME, COLOR_ACCENT, render_fn)` を通す。`render_fn()` は `core/charts.build_*` で `Figure` を得て `FigureCanvasTkAgg(fig, master=frame)` で埋め込む。

## モジュール責務

- **config.py** — 全設定を集約。テーマ色 `COLOR_BG/FRAME/TEXT/ACCENT/HIGHLIGHT`、`YEAR_LIST`（2000〜現在年、開始年を変えるならここ）、`APP_TITLE`、`WINDOW_SIZE`、`MPL_STYLE`（`'fastf1'`）、キャッシュ設定 `CACHE_DIR`/`CACHE_SIZE_LIMIT_GB`(2)/`CACHE_EXPIRE_DAYS`(30)。**色や設定はハードコードせず必ずここから import する。**
- **service.py** — `CacheManager.ensure_cache_dir()`（`fastf1.Cache.enable_cache`）と `cleanup_cache()`（`atime` が 30 日超のファイルを削除、総量が 2GB 超ならキャッシュ全削除）。`FastF1Service.get_event_schedule_async` / `load_session_async` は Executor に submit した `Future` を返す。
- **core/charts.py** — matplotlib Figure / 結果テーブルを生成する純粋関数群（`pyplot`・`tkinter` 非依存）。Tkinter 版・Streamlit 版の双方から呼ぶ。データ無しは `ChartDataError` を送出。`format_timedelta` もここにある。
- **core/data.py** — Streamlit 用の FastF1 取得アダプタ（`st.cache_data` / `st.cache_resource` でスケジュール・セッションを保持）。
- **streamlit_app.py** — Streamlit 版エントリ。`_inject_responsive_css()` でPC/タブレット/スマホ対応のCSSを注入し、図は `st.pyplot(fig, use_container_width=True)` で描画。
- **server.py（PITWALL）** — stdlib `ThreadingHTTPServer`。`web/` の静的配信 + `/api/*`。セッションはバックグラウンドスレッドでロードし（同時1件・LRU 2件保持）、laps/results/天候/レースコントロール等を JSON 化して返す。チームカラーは `ensure_mark_contrast` でダーク背景向けに OKLab 明度+彩度スナップ。
- **web/js（PITWALL）** — `derive.js` がバンドルから派生データ（周回別順位・SC帯・スティント・KDE入力）を計算し、`views/*` が自前SVGで描画（ラップチャート/ギャップ/ペース/ラップ分布バイオリン/戦略/テレメトリ/トラック/リザルト/レースコントロール）。ドライバー選択は `state.js` の focus で全タブ連動。
- **main.py** — Tkinter アプリ本体と ttk スタイル定義（Notebook / Button / Treeview / Progressbar / Sash など）。`main()` は `logging.basicConfig` 後に `mainloop()`。
- **ui/sidebar.py** — スクロール可能キャンバス内に選択 UI（年 Listbox / GP Listbox / セッション Combobox `["FP1","FP2","FP3","Q","R"]` / ドライバー複数選択 Listbox）と分析ボタン、プログレスバーを配置。各 `_cmd_*` はドライバー選択数を検証（単一系は1名、散布図比較は最大4名）してから `main_tab.show_*` を呼ぶ。
- **ui/animations.py** — 演出ユーティリティ。`CloudLoader`（サイン波でバウンドする5ドット, 40ms/frame）、`show_chart_with_loader`（ローダー表示→80ms後に `render_fn`）、`typewriter_effect`（1文字ずつ表示）、`animate_treeview_rows`（1行ずつ挿入）、`fade_in_label`（色補間フェード）。詳細は `cloud.md`。
- **tabs/*** — 各タブの Tkinter 埋め込み層。図の組み立ては `core/charts` に委譲。過去の破壊的修正は `cloud.md` の「Data-display correctness」節に記録済み。

## コード規約

- **命名**：定数 `UPPER_SNAKE_CASE`（config の色・設定）、関数 `snake_case`、クラス `PascalCase`。
- **色は `config.py` から import**（Tkinter 版）。PITWALL のUI色は `web/styles.css` のカスタムプロパティに集約。生の色コードを各所に書かない。
- **タブは `init_X` / `show_X` ペア**（上記「タブモジュールの共通形」）。`show_X` は既存 widget を全 destroy して再描画する方式を踏襲する。
- **UI 文言・メッセージボックス・新規コメントは日本語**（既存トーンに合わせる。英語コメントも一部混在するが現状はそのまま）。
- **一文字変数・過剰な抽象化を避け、可読性優先。** 既存ファイルの全面書き換えは明示指示がない限りしない。

## よくある落とし穴（重要）

- **`python` は PATH に無い → `py` を使う。** `py main.py` / `py -m pip ...`。
- **入れ子ディレクトリ**：作業ルートは内側 `formula1_dashboard\formula1_dashboard\`。外側 `formula1_dashboard\` は `_fastf1_cache` のバイナリだけを追跡するリモート無しの別リポジトリで、混同すると誤った場所に commit してしまう。
- **GUI 依存（Tkinter版）**：ヘッドレスでは起動不可。動作確認は実 GUI 起動が唯一の手段。
- **Tkinter スレッド規約**：バックグラウンドスレッドから UI を直接触らない。必ず `self.after(0, ...)` でメインスレッドに戻す（既存の `add_done_callback` パターンを踏襲）。
- **matplotlib のグローバル状態を避ける**：`plt.subplots()` ではなく `fig = plt.Figure(...)` / `fig.subplots()` を使い `FigureCanvasTkAgg` で埋め込む（`cloud.md` の修正済み事項。pyplot のグローバル figure を汚さない）。
- **FastF1 の API バージョン差異**：コードは概ね FastF1 3.5 / seaborn 0.13 に合わせて修正済み。`pick_driver()` は非推奨で `pick_drivers()` を使う（3.1+）／`get_compound_mapping()` に `weekend` 引数を渡さない／`Session.load_results()` は存在しない（`session.load()` が結果もロード）／`setup_mpl()` の `misc_mpl_mods` 引数は削除済み（3.6 で廃止）。**FastF1 を上げて壊れたら、まず `cloud.md` の修正履歴を見る。**
- **`session.get_driver()` は pandas Series を返す**。`if driver_info:` のような bool 評価は `ValueError`。`driver_info is not None and 'Key' in driver_info` で判定する（`results_tab.py`・`sidebar.py` に対策済み）。
- **キャッシュ**：`_fastf1_cache/` は gitignore 済み（内側）。`cleanup_cache()` が起動時に 30 日超ファイル削除・2GB 超で全削除。初回・キャッシュ無しは遅い。**`fastf1_http_cache.sqlite` は歴史的に追跡されてしまっており、アプリを動かすだけで差分が出る（コミットに含めない）。またサーバ/アプリ起動中はロックされ git の stash/checkout が失敗する。**
- **Sprint 未対応（Tkinter版のみ）**：セッション Combobox は `FP1/FP2/FP3/Q/R` のみ。PITWALL はスケジュール由来で S/SQ も選択できる。
- **PITWALL の要点**：(1) 予選/プラクティスは laps の `Position` が全て NaN → ラップチャート/ギャップ/ピット分析タブは非表示、ペース/ラップ分布はドット中心の描画。予選のみ「予選分析」タブが出る（`qualiOnly`）。(2) `TrackStatus` は `"124"` のような合成文字列 → 含有判定（4=SC, 5=赤旗, 6/7=VSC）。(3) チームカラーはダーク背景向けにサーバ側で OKLab 明度スナップ（`ensure_mark_contrast`、コントラスト3:1未満なら色相保持で明度+彩度を補正）。(4) `styles.css` の `--surface-1` と `server.py` の `CHART_SURFACE` は一致させること。(5) 2018年以降のみ対応（FIRST_YEAR）。(6) `pos_data` の欠損は NaN ではなく **X==0 かつ Y==0 の行**として現れる（`/api/replay` は除外済み）。リタイア車は座標送信が続くことがあるため laps の最終ライン通過+60秒で打ち切る。全ドライバーの SessionTime 軸は共通（実測: 中央値0.24秒間隔）。(7) リプレイのタワー順位は「周回数 → 現在周への到達時刻」のライン通過ベースでソートする（周回内の時間割合はピット中の車の順位を歪めるため使わない）。(8) リプレイタブの再生状態は `replay.js` のモジュール変数 `R` がタブ切替をまたいで保持する。URLハッシュ（`#y=&r=&s=&tab=&drv=`）で状態復元・自動読み込みができる。

## git-ignore 対象（コミット禁止）

- `_fastf1_cache/` — FastF1 のキャッシュ（大量のバイナリ）
- `__pycache__/`, `*.pyc` — Python キャッシュ
- `task_tracker.md`, `project.md` — 作業メモ（ローカル専用）

## Git

- 独立リポジトリ **`https://github.com/tabear25/formula1_dashboard.git`**（branch `main`）。ホームフォルダ（`C:\Users\str06`）の Git リポジトリとは別で、push はこのリモートのみに及ぶ。
- 明示的に依頼されない限り commit / push / branch 作成は行わない。

## 変更履歴（Change Log）

ここに修正・変更の内容を追記していく。新しいものを上に追加すること。

- **PITWALL 大型拡張（究極のインタラクティブF1ダッシュボード化）**: タブを9→15枚に拡張し、
  全車リプレイを核とした機能群を追加（2026-07-25）。
  - サーバ: `/api/replay` を新設。全車の `pos_data` を共通0.5秒グリッドへ `np.interp` で
    再サンプルし、trackmap と同じ回転補正をかけた X/Y を 0.1m 整数配列で返す
    （`{t0, dt, n, race_start, cars:[{abbr, i0, i1, x[], y[]}]}`、gzip 済みを
    `tel_cache["__replay__"]` にキャッシュ。決勝1レースで raw 約3MB / gzip 約1MB）。
    欠損の (0,0) 行は除外し、リタイア車は laps の最終ライン通過+60秒で打ち切る。
    予選バンドルの laps に `seg`（1/2/3、`split_qualifying_sessions()` 由来。失敗時は
    キー自体を付けずクライアントが時間ギャップ推定へ劣化）を付与。
  - 新タブ6枚（`web/js/views/`）:
    `replay.js` — 全車位置リプレイ。タイミングタワー（ライン通過ベースの順位・ギャップ・
    タイヤ・PIT表示。予選/プラクティスは暫定ベスト順に切替）、SC/VSC/赤旗の旗バッジと
    シークバー帯、レースコントロールのティッカー、自動イベント検出（オーバーテイク/
    ピット/FL更新/リタイア/降雨/旗）のマーカーとクリックでシークできるログ、再生速度
    ×1〜×60、Space/←/→ ショートカット。
    `degradation.js` — タイヤ使用周回数×タイムの散布とコンパウンド別最小二乗フィット
    （劣化率 s/周）。レースは燃料補正トグル（0.06s/周の近似と明記）。
    `pitstops.js` — ストップ一覧（推定ロス＝イン+アウト−クリーン中央値×2、SC中表示、
    順位変動）とアンダーカット/オーバーカット検出（近接ペアのピット差し合いの
    タイム差スイング）。レース専用。
    `sectors.js` — ベストセクター・理論値（自己ベスト3セクター合計）・全体ベストとの
    差の積み上げバー。
    `dominance.js` — 最大6名の最速ラップをミニセクター（約170m、20〜40区間）で比較し
    区間最速の色でコースを塗り分け。既存 /api/telemetry と /api/trackmap のみで実装。
    `quali.js` — Q1→Q2→Q3 スロープチャートとトラック進化（セッション時間×タイム、
    その時点までのベスト白線、セグメント境界は seg 優先・無ければ5分ギャップ推定）。
    予選のみ表示（`qualiOnly` フラグを TABS に追加）。
  - 横断UX（`app.js`）: URLハッシュのディープリンク
    `#y=2025&r=1&s=R&tab=replay&drv=VER,NOR`（起動時に自動読み込み→タブ・選択復元、
    操作のたびに `history.replaceState` で更新）。キーボード ←/→＝タブ切替、
    Esc＝選択解除（リプレイタブは Space/←/→ を自前処理）。
  - レビュー（3視点並行の敵対的レビュー＋反証検証）で確定した16件をすべて修正。主要:
    (a) セッション切替中に古い /api/replay 応答が新セッションへ混入するレース条件
    （キー検証を追加）、(b) 第三者のリタイア・ピット降格を実追い抜きと誤検出
    （「前周は前・当周も走行中・現在は後ろ」の車がいる場合のみ記録）、(c) ブラウザ
    タブ非表示→復帰でリプレイ時刻が大ジャンプ（rAFデルタを250msでクランプ）、
    (d) シークバーのモーメントマーカーが親のポインタキャプチャに食われクリック不能、
    (e) アンダーカット検出の計測窓汚染（窓内の追加ピット・双方向重複行を除外）、
    (f) ドミナンスで途中欠損テレメトリが混ざるとコース後半が単色になる（全長95%の
    カバレッジ検証＋補間の範囲外null化）、(g) デグラデーションの外れ値カットが表示
    のみでフィット・表に効かない不整合（収集直後に一括除外）、(h) 予選トラック進化の
    白線がプロット外へはみ出す（クランプ＋クリップ）、(i) スロープチャートのラベル
    衝突解決が列をまたいで押し合う／域外ドライバーのラベルが孤立、(j) URLハッシュの
    tab/drv が別セッションのバンドルに誤適用（sessionKey一致時のみ適用）、(k) タブ
    フォールバック時にタブ列のactive強調が付かない（フォールバックを描画前へ移動）、
    (l) ResizeObserver が自身の高さ変化に反応して冗長再描画（幅変化のみ発火）、
    (m) スタート前タワーが最終結果順＋最終タイヤ表示になるネタバレ（グリッド順＋
    スタートスティント表示）、(n) 停止中もタワーを250msごとに全再構築しクリックを
    取りこぼす（クリックは委譲・再構築は再生中のみ）、(o) ドミナンスで明示選択を
    2名未満に減らすと選択が勝手に復活する。
  - 検証: headless Chrome + CDP で 2025 豪州GP決勝（全14タブ+リプレイ再生+中盤シーク+
    タワー順位確認）と 2025 サウジ予選（7タブ、Q1/Q2/Q3境界表示）をスクリーンショット
    確認。全修正適用後に再実行し、コンソールエラー/警告 0。実データ検証（pos_data の
    構造・時間軸整合・ペイロードサイズ実測）に基づいて実装。
  - 検証時の注意: URLハッシュだけが異なる同一URLへの再ナビゲートはページ再読み込みに
    ならない（same-document navigation）。CDP検証では about:blank を経由すること。

- **Web版 PITWALL を追加**: `server.py`（stdlib http.server の JSON API、追加 pip 依存なし）+
  `web/`（vanilla JS SPA・自前SVG描画）+ `start_pitwall.cmd`。タブ＝ラップチャート
  （davidor/formula1-lap-charts のオマージュ）/ ギャップ（リーダー基準・勝者平均基準）/
  ペース / ラップ分布（自前KDEのバイオリンプロット）/ タイヤ戦略 / テレメトリ比較 /
  トラックマップ（速度着色）/ リザルト / レースコントロール＋天候。ドライバー選択は
  全タブ連動、ヘッダーにサーキット外形ミニマップを常時表示。チームカラーはダーク背景
  向けに OKLab 明度+彩度スナップで補正。検証は headless Chrome + CDP のスクリーン
  ショットで実施（2025 豪州GP決勝 / サウジ予選、コンソールエラー0）。

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

---

# Personal rules for Claude Code

## Language
- ユーザーへの説明、確認、要約は常に日本語で行う。
  - ただし、ユーザーが英語でプロンプトを入力してきたときは、英語で行ってもよい。
- 英語のコマンドやエラーメッセージは、実行前または提示時に日本語で意味を短く説明する。

## Safety
- ファイル削除、ディレクトリ削除、大規模置換、依存関係の追加/削除、DBマイグレーション、git commit、git push は無断で実行しない。
- 破壊的または広範囲に影響する操作の前には、必ず日本語で以下を説明して確認する。
  - 何をするか
  - 影響範囲
  - 元に戻す方法
- `.env`、秘密鍵、トークン、認証情報、本番設定ファイルには触れない。必要なら確認する。
- セキュリティに関連する環境変数以外のファイルの追加、編集はユーザーの許可なく実行して良い

## Workflow
- まずコードやファイルを読んで状況を要約し、その後に短い作業方針を示してから変更する。
- 既存の命名規則、コードスタイル、ディレクトリ構成を優先する。
- 指示が曖昧・不明瞭な場合は、クリアになるまでユーザーに質問を繰り返す。

## Skills
- 現在作業しているディレクトリ内に Skill（例: `skills/*/SKILL.md`、`.agents/skills/*/SKILL.md`、`.claude/skills/*/SKILL.md`）があり、その Skill と同種のタスクを依頼された場合は、必ず該当 Skill を先に読み、その手順に従って作業する。
- 複数の Skill が該当しそうな場合は、最も近いものを選び、必要なら使用する Skill 名と理由を日本語で短く説明する。

## Commands
- コマンド実行前に、日本語で目的を1行で説明する。
- 一見して挙動がわかりにくいスクリプト実行時は、主要な引数や処理内容も日本語で短く添える。
- プロジェクト内に定義された正式な test / lint / format コマンドを優先して使う。
- 不明な場合は勝手に新しいツールやコマンド体系を導入しない。

## Testing
- 変更に最も近い範囲のテストから実行する。
- テストやlintが失敗した場合は、失敗内容と考えられる原因を日本語で要約する。
- テストが未実施の場合は、その理由を明示する。

## Editing policy
- 一文字変数や過剰な抽象化を避け、可読性を優先する。
- 既存ファイルの全面書き換えは明示されていない場合を除き、避ける。
- CSVファイルを書き出す場合は、Excelでの文字化けを避けるため、原則としてUTF-8 BOM付き（utf-8-sig）で保存する。
- Skill などの Markdown ファイル（`.md`）は、コピーを作らず、そのファイル自体を直接変更してよい。

## Git
- 明示的に依頼されない限り commit / push / branch作成 は行わない。
- 変更内容は、最後に日本語で要点を簡潔にまとめる。
