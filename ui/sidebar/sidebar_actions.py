import tkinter as tk
from tkinter import messagebox
from service import FastF1Service

class SidebarActions:
    """Sidebar の動作ロジック（イベントハンドラ）"""

    def on_year(self, event):
        sel = event.widget.curselection()
        self.current_session = None
        if not sel:
            return
        year = int(event.widget.get(sel[0]))
        self.year_var.set(year)
        self.load_schedule(year)

    def on_gp(self, event):
        sel = event.widget.curselection()
        self.current_session = None
        if not sel:
            return
        self.gp_var.set(event.widget.get(sel[0]))

    def on_ses(self, _):
        year = self.year_var.get()
        if not year:
            messagebox.showinfo("選択が不足しています", "先に開催年を選択してください")
            return
        gp = self.gp_var.get()
        if not gp:
            messagebox.showinfo("選択が不足しています", "先にグランプリを選択してください")
            return
        ses = self.ses_var.get()
        if not ses:
            messagebox.showinfo("選択が不足しています", "先にセッションを選択してください")
            return
        self.load_session(year, gp, ses)

    def selected_drivers(self):
        return [self.drv_lb.get(i) for i in self.drv_lb.curselection()]

    def show_speed(self):
        if not self.current_session:
            messagebox.showinfo("セッション未ロード", "先にセッションを読み込んでください")
            return
        drvs = self.selected_drivers()
        if len(drvs) != 1:
            messagebox.showinfo("ドライバー選択", "1名だけ選択してください")
            return
        self.main_tab.show_multi_driver_speed(self.current_session, drvs)

    def show_scatter(self):
        if not self.current_session:
            messagebox.showinfo("セッション未ロード", "先にセッションを読み込んでください")
            return
        drvs = self.selected_drivers()
        if len(drvs) != 1:
            messagebox.showinfo("ドライバー選択", "1名だけ選択してください")
            return
        self.main_tab.show_multi_lap_scatter(self.current_session, drvs)

    def show_compare(self):
        if not self.current_session:
            messagebox.showinfo("選択エラー", "セッション読み込み後に実行してください")
            return
        drvs = self.selected_drivers()
        self.main_tab.show_multi_driver_compare(self.current_session, drvs)

    def show_speed_compare(self):
        if not self.current_session:
            messagebox.showinfo("選択エラー", "セッション読み込み後に実行してください")
            return
        drvs = self.selected_drivers()
        self.main_tab.show_multi_driver_speed(self.current_session, drvs)

    def show_scatter_compare(self):
        if not self.current_session:
            messagebox.showinfo("選択エラー", "セッション読み込み後に実行してください")
            return
        drvs = self.selected_drivers()
        self.main_tab.show_multi_lap_scatter(self.current_session, drvs)

    def load_schedule(self, year: int):
        self.progress.start(8)
        fut = self.svc.get_event_schedule_async(year)
        def _done(f):
            self.progress.stop()
            try:
                df = f.result()
            except Exception as e:
                messagebox.showerror("失敗", str(e))
                return
            self.gp_lb.delete(0, tk.END)
            for gp in df['EventName']:
                self.gp_lb.insert(tk.END, gp)
        fut.add_done_callback(lambda f: self.after(0, _done, f))

    def load_session(self, year: int, gp: str, ses: str):
        self.progress.start(8)
        fut = self.svc.load_session_async(year, gp, ses)
        def _done(f):
            self.progress.stop()
            try:
                sess = f.result()
            except Exception as e:
                messagebox.showerror("失敗", str(e))
                return
            self.drv_lb.delete(0, tk.END)
            for d in sess.drivers:
                self.drv_lb.insert(tk.END, sess.get_driver(d)['Abbreviation'])
            self.current_session = sess
            self.main_tab.show_map(sess)
            messagebox.showinfo("ロード完了", f"{gp} – {ses} を読み込みました")
        fut.add_done_callback(lambda f: self.after(0, _done, f))