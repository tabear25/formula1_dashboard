import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from config import COLOR_FRAME, COLOR_TEXT, COLOR_ACCENT, COLOR_BG # Assuming these are defined in config
import fastf1 # For type hinting if needed: from fastf1.core import Session

def format_timedelta(td):
    """Pandas Timedeltaを HH:MM:SS.mmm 形式の文字列にフォーマットする"""
    if pd.isna(td):
        return ""
    total_seconds = td.total_seconds()
    # Handle negative timedeltas if they represent something like a gap from leader
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000)) # round to nearest ms

    # Ensure seconds don't roll over to 60 due to rounding
    if milliseconds >= 1000:
        milliseconds -= 1000
        seconds +=1
        if seconds >= 60:
            seconds -= 60
            minutes +=1
            if minutes >= 60:
                minutes -=60
                hours +=1


    if hours > 0:
        return f"{sign}{int(hours):01d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:03d}"
    elif minutes > 0: 
        return f"{sign}{int(minutes):01d}:{int(seconds):02d}.{milliseconds:03d}"
    else:
        return f"{sign}{float(seconds):06.3f}" # Using float for seconds with 3 decimal places for sub-minute times.

def init_results_tab(notebook):
    frame = ttk.Frame(notebook, style="TFrame")
    label = ttk.Label(frame, text="セッションを選択して結果を表示してください。", style="TLabel", anchor="center")
    label.pack(expand=True, fill="both", padx=20, pady=20)
    notebook.add(frame, text="📊 Results")
    return frame

def show_session_results(frame, session: fastf1.core.Session): # Added type hint for session
    for widget in frame.winfo_children():
        widget.destroy()

    if session is None:
        ttk.Label(frame, text="セッションデータがありません。", style="TLabel", anchor="center").pack(expand=True, fill="both")
        return

    try:
        # Explicitly load results data for the session
        # This is now the primary way to get results data.
        if not hasattr(session, 'results') or session.results is None or session.results.empty:
            if hasattr(session, 'load_results') and callable(session.load_results):
                # Some session types (e.g., Test Day) might not have 'results' in a typical sense.
                # FastF1 might raise an error or return None/empty for such cases.
                session.load_results() # Attempt to load results
            else: # Should not happen with standard FastF1 Session objects
                raise AttributeError("Session object does not have a 'load_results' method.")

        if session.results is None or session.results.empty:
            ttk.Label(frame, text="このセッションの結果データはありません。\n(または、このセッションタイプには結果がありません)", style="TLabel", anchor="center").pack(expand=True, fill="both")
            return

    except AttributeError as ae: # Handle case where load_results might not exist for some custom/mock object
         ttk.Label(frame, text=f"セッションオブジェクトエラー: {ae}", style="TLabel", wraplength=frame.winfo_width()-40, anchor="center").pack(expand=True, fill="both")
         return
    except fastf1.api.SessionNotAvailableError as snae: # Specific error for unavailable data
         ttk.Label(frame, text=f"結果データ利用不可: {snae}", style="TLabel", wraplength=frame.winfo_width()-40, anchor="center").pack(expand=True, fill="both")
         return
    except Exception as e: # Catch other potential errors during load_results
        # messagebox.showerror("結果データエラー", f"結果データのロード中にエラーが発生しました: {e}")
        ttk.Label(frame, text=f"結果データのロードエラー: {type(e).__name__}: {e}", style="TLabel", wraplength=frame.winfo_width()-40, anchor="center").pack(expand=True, fill="both")
        return

    results_df = session.results.copy()

    session_type_name = session.name # e.g., 'Race', 'Qualifying', 'Practice 1'
    
    # Define base columns
    columns_config = {
        # id: (Header Text, Default Width, Data Type Hint for formatting)
        'Position': ('Pos', 40, 'int'),
        'Abbreviation': ('Driver', 70, 'str'),
        # 'FullName': ('Full Name', 150, 'str'), # We'll add this manually
        'TeamName': ('Team', 130, 'str'),
        'Time': ('Time/Gap', 100, 'timedelta'), # For race results
        'Status': ('Status', 100, 'str'),
        'Laps': ('Laps', 40, 'int'),
        'GridPosition': ('Grid', 40, 'int'),
        'Points': ('Pts', 40, 'float'), # Points can be .5
    }

    # Add/adjust columns based on session type
    if session_type_name == 'Qualifying':
        columns_config.update({
            'Q1': ('Q1', 80, 'timedelta'),
            'Q2': ('Q2', 80, 'timedelta'),
            'Q3': ('Q3', 80, 'timedelta'),
        })
        columns_config.pop('Time', None) # Qualifying doesn't have a final "Time" like a race
        columns_config.pop('Status', None)
        columns_config.pop('FastestLapTime', None) # Usually Q1/Q2/Q3 are more relevant than a single fastest lap in Q
    elif session_type_name in ['Race', 'Sprint Race', 'Sprint']: # Sprint Shootout might be 'SQ'
         columns_config.update({
            'FastestLapTime': ('Fastest Lap', 90, 'timedelta'),
         })
         # For races, 'Time' is usually the total time or gap to leader.
    else: # Practice sessions
        columns_config.pop('GridPosition', None)
        columns_config.pop('Points', None)
        columns_config.pop('Status', None)
        # 'Time' column in practice usually means fastest lap time
        if 'Time' in results_df.columns:
            columns_config['Time'] = ('Best Lap', 90, 'timedelta')
        elif 'FastestLapTime' in results_df.columns: # Sometimes it's under FastestLapTime
            columns_config['FastestLapTime'] = ('Best Lap', 90, 'timedelta')
            results_df.rename(columns={'FastestLapTime': 'Time'}, inplace=True) # Standardize for display
        columns_config.pop('FastestLapTime', None) # remove original if renamed

    # Add FullName using get_driver, place it after Abbreviation
    if 'DriverNumber' in results_df.columns:
        full_names = []
        for driver_number in results_df['DriverNumber']:
            try:
                driver_info = session.get_driver(driver_number)
                full_names.append(driver_info['FullName'] if driver_info and 'FullName' in driver_info else "")
            except:
                full_names.append("") # Fallback
        results_df['FullName'] = full_names
        # Insert FullName into columns_config in the desired order
        temp_cols = list(columns_config.items())
        try:
            abbr_index = [i for i, (k,v) in enumerate(temp_cols) if k == 'Abbreviation'][0]
            temp_cols.insert(abbr_index + 1, ('FullName', ('Full Name', 150, 'str')))
            columns_config = dict(temp_cols)
        except IndexError: # Abbreviation not found, add FullName at start or end
            columns_config['FullName'] = ('Full Name', 150, 'str')


    # Filter out columns from config that are not in the actual DataFrame
    tree_columns_ids = [col_id for col_id in columns_config.keys() if col_id in results_df.columns]
    
    if not tree_columns_ids:
        ttk.Label(frame, text="表示できる結果の列が見つかりませんでした。", style="TLabel", anchor="center").pack(expand=True, fill="both")
        return

    tree_frame = ttk.Frame(frame, style="TFrame")
    tree_frame.pack(expand=True, fill="both", padx=5, pady=5)
    tree = ttk.Treeview(tree_frame, columns=tree_columns_ids, show="headings", style="Treeview")

    for col_id in tree_columns_ids:
        header_text, col_width, _ = columns_config[col_id]
        tree.heading(col_id, text=header_text)
        tree.column(col_id, width=col_width, anchor='w', minwidth=max(30, col_width // 2))

    rows_data = []
    for _, row in results_df.iterrows():
        values_for_row = []
        for col_id in tree_columns_ids:
            val = row.get(col_id)
            _, _, data_type = columns_config[col_id]

            if pd.isna(val):
                values_for_row.append("")
            elif data_type == 'timedelta':
                values_for_row.append(format_timedelta(val))
            elif data_type == 'int':
                try:
                    values_for_row.append(str(int(float(str(val)))))
                except ValueError:
                    values_for_row.append(str(val))
            elif data_type == 'float':
                try:
                    values_for_row.append(f"{float(str(val)):.1f}")
                except ValueError:
                    values_for_row.append(str(val))
            else:
                values_for_row.append(str(val))
        rows_data.append(tuple(values_for_row))

    from ui.animations import animate_treeview_rows
    animate_treeview_rows(tree, rows_data, delay=40)

    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")
    tree.pack(expand=True, fill="both")

    session_info_label = ttk.Label(frame, text=f"{session.event.year} {session.event['EventName']} - {session.name}", style="TLabel")
    session_info_label.pack(side="bottom", fill="x", pady=(5,0), anchor='w')