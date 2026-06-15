import tkinter as tk
from tkinter import ttk
import fastf1  # For type hinting: fastf1.core.Session
from core.charts import build_results_table, format_timedelta, ChartDataError  # noqa: F401
from ui.animations import animate_treeview_rows

# format_timedelta は core.charts に移設し、後方互換のため再エクスポートする。


def init_results_tab(notebook):
    frame = ttk.Frame(notebook, style="TFrame")
    label = ttk.Label(frame, text="セッションを選択して結果を表示してください。", style="TLabel", anchor="center")
    label.pack(expand=True, fill="both", padx=20, pady=20)
    notebook.add(frame, text="📊 Results")
    return frame


def show_session_results(frame, session: fastf1.core.Session):
    for widget in frame.winfo_children():
        widget.destroy()

    if session is None:
        ttk.Label(frame, text="セッションデータがありません。", style="TLabel",
                  anchor="center").pack(expand=True, fill="both")
        return

    # 結果テーブルの構築（列メタ + 整形済み行）は core.charts に集約。
    try:
        table = build_results_table(session)
    except ChartDataError as e:
        ttk.Label(frame, text=str(e), style="TLabel", anchor="center",
                  wraplength=max(200, frame.winfo_width() - 40)).pack(expand=True, fill="both")
        return

    tree_frame = ttk.Frame(frame, style="TFrame")
    tree_frame.pack(expand=True, fill="both", padx=5, pady=5)

    column_ids = [str(i) for i in range(len(table.columns))]
    tree = ttk.Treeview(tree_frame, columns=column_ids, show="headings", style="Treeview")
    for col_id, (header_text, col_width) in zip(column_ids, table.columns):
        tree.heading(col_id, text=header_text)
        tree.column(col_id, width=col_width, anchor="w", minwidth=max(30, col_width // 2))

    animate_treeview_rows(tree, table.rows, delay=40)

    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")
    tree.pack(expand=True, fill="both")

    session_info_label = ttk.Label(
        frame,
        text=f"{session.event.year} {session.event['EventName']} - {session.name}",
        style="TLabel",
    )
    session_info_label.pack(side="bottom", fill="x", pady=(5, 0), anchor="w")
