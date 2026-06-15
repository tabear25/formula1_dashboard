# CLAUDE.md

このファイルは、このリポジトリで作業する際の Claude Code 向けガイドです。

## 最重要ルール（Most Important Rule）

**新しい修正や変更は、すべてこの CLAUDE.md に反映すること。**
コードの修正・機能追加・設定変更・バグ修正などを行った場合は、その内容をこの
CLAUDE.md に記録し、常に最新の状態を保つこと。

## プロジェクト概要（Overview）

F1 のレースデータを視覚化・分析するためのデスクトップアプリケーション。
FastF1 ライブラリで過去のグランプリのセッションデータ（ラップタイム、テレメトリ、
順位など）を取得し、Tkinter GUI 上でインタラクティブなグラフやマップとして表示する。

- 言語 / フレームワーク: Python 3.9+ / Tkinter
- 主要ライブラリ: fastf1, pandas, matplotlib, seaborn

## 主なファイル構成（Structure）

- `main.py`: アプリのエントリポイント。GUI の構築と起動。
- `config.py`: キャッシュ設定・テーマカラー・Matplotlib スタイルなどの設定値。
- `service.py`: FastF1 を用いたデータ取得ロジック。
- `tabs/`: 各分析タブ（overview, map, results, telemetry, lap scatter, compare,
  speed, scatter）の実装。
- `ui/`: アニメーションなどの UI 補助モジュール（`ui/animations.py`）。

## 実行方法（Run）

```
pip install -r requirements.txt
python main.py
```

## 変更履歴（Change Log）

ここに修正・変更の内容を追記していく。新しいものを上に追加すること。

- `main.py`: `fastf1.plotting.setup_mpl()` から廃止済みの `misc_mpl_mods=False`
  引数を削除（fastf1 3.6.0 で削除され、3.8 系では `FutureWarning` を出すため）。
  これにより起動時の警告が解消。Xvfb 上でのヘッドレス起動テストで GUI が
  正常に構築され、終了コード 0 で終了することを確認済み。
- （初回）CLAUDE.md を作成。「新しい修正や変更はすべて CLAUDE.md に反映する」
  ルールを明記。
