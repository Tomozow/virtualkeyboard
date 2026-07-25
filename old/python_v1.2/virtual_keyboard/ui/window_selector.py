"""
Window Selector Dialog - ウィンドウ選択ダイアログ
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import threading
import logging
from typing import Optional, Dict, Any, List
from ..utils.window_utils import WindowEnumerator, WindowInfo, WindowMatcher

logger = logging.getLogger(__name__)


class WindowSelectorDialog:
    """ウィンドウ選択ダイアログ"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        self.selected_window = None
        self.windows = []
        self.filtered_windows = []
        
        # ダイアログウィンドウ作成
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("ウィンドウ選択")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        
        # モーダル設定
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # ウィンドウを中央に配置
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self._create_ui()
        self._load_windows()
        
        # ダイアログが閉じられたときの処理
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _create_ui(self):
        """UI要素を作成"""
        # メインフレーム
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 上部フレーム（検索とボタン）
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # 検索フィルタ
        ctk.CTkLabel(top_frame, text="🔍 検索:").pack(side="left", padx=(10, 5), pady=10)
        
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self.search_var,
            placeholder_text="プロセス名やウィンドウタイトルで検索",
            width=300
        )
        self.search_entry.pack(side="left", padx=5, pady=10)
        self.search_entry.bind('<KeyRelease>', self._on_search_changed)
        
        # 更新ボタン
        ctk.CTkButton(
            top_frame,
            text="🔄 更新",
            command=self._refresh_windows,
            width=80
        ).pack(side="left", padx=10, pady=10)
        
        # 表示オプション
        self.show_hidden_var = tk.BooleanVar()
        ctk.CTkCheckBox(
            top_frame,
            text="非表示ウィンドウも表示",
            variable=self.show_hidden_var,
            command=self._on_show_hidden_changed
        ).pack(side="right", padx=10, pady=10)
        
        # ウィンドウ一覧フレーム
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # ツリービュー（テーブル表示）
        columns = ('process', 'title', 'class', 'pid')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # 列の設定
        self.tree.heading('process', text='プロセス名', anchor='w')
        self.tree.heading('title', text='ウィンドウタイトル', anchor='w')
        self.tree.heading('class', text='クラス名', anchor='w')
        self.tree.heading('pid', text='PID', anchor='w')
        
        self.tree.column('process', width=150, minwidth=100)
        self.tree.column('title', width=300, minwidth=200)
        self.tree.column('class', width=200, minwidth=150)
        self.tree.column('pid', width=80, minwidth=60)
        
        # スクロールバー
        scrollbar_v = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar_h = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        # ツリービューとスクロールバーを配置
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_v.grid(row=0, column=1, sticky="ns")
        scrollbar_h.grid(row=1, column=0, sticky="ew")
        
        # グリッドの重み設定
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 選択イベント
        self.tree.bind('<<TreeviewSelect>>', self._on_selection_changed)
        self.tree.bind('<Double-1>', self._on_double_click)
        
        # 詳細情報フレーム
        detail_frame = ctk.CTkFrame(main_frame)
        detail_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(detail_frame, text="選択中のウィンドウ詳細:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.detail_text = ctk.CTkTextbox(detail_frame, height=80, wrap="word")
        self.detail_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # ボタンフレーム
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkButton(
            button_frame,
            text="OK",
            command=self._on_ok,
            width=100
        ).pack(side="right", padx=(5, 10), pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="キャンセル",
            command=self._on_cancel,
            width=100
        ).pack(side="right", padx=5, pady=10)
        
        # ステータスラベル
        self.status_label = ctk.CTkLabel(
            button_frame,
            text="ウィンドウを読み込み中...",
            anchor="w"
        )
        self.status_label.pack(side="left", padx=10, pady=10)
    
    def _load_windows(self):
        """ウィンドウ一覧を読み込み"""
        def load_thread():
            try:
                include_hidden = self.show_hidden_var.get()
                self.windows = WindowEnumerator.get_all_windows(include_hidden=include_hidden)
                
                # メインスレッドでUI更新
                self.dialog.after(0, self._update_tree)
                
            except Exception as e:
                logger.error(f"Error loading windows: {e}")
                self.dialog.after(0, lambda: self.status_label.configure(text=f"エラー: {e}"))
        
        # バックグラウンドで実行
        threading.Thread(target=load_thread, daemon=True).start()
    
    def _update_tree(self):
        """ツリービューを更新"""
        try:
            # 既存のアイテムをクリア
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 検索フィルタを適用
            self._apply_filter()
            
            # ウィンドウを追加
            for window in self.filtered_windows:
                self.tree.insert('', 'end', values=(
                    window.process_name,
                    window.title[:80] + ('...' if len(window.title) > 80 else ''),
                    window.class_name,
                    window.process_id
                ), tags=(str(window.hwnd),))
            
            self.status_label.configure(text=f"{len(self.filtered_windows)} 個のウィンドウが見つかりました")
            
        except Exception as e:
            logger.error(f"Error updating tree: {e}")
            self.status_label.configure(text=f"更新エラー: {e}")
    
    def _apply_filter(self):
        """検索フィルタを適用"""
        search_text = self.search_var.get().lower()
        
        if not search_text:
            self.filtered_windows = self.windows[:]
        else:
            self.filtered_windows = []
            for window in self.windows:
                if (search_text in window.process_name.lower() or
                    search_text in window.title.lower() or
                    search_text in window.class_name.lower()):
                    self.filtered_windows.append(window)
    
    def _on_search_changed(self, event):
        """検索テキスト変更時"""
        self._update_tree()
    
    def _on_show_hidden_changed(self):
        """表示オプション変更時"""
        self._load_windows()
    
    def _refresh_windows(self):
        """ウィンドウ一覧を再取得"""
        self.status_label.configure(text="更新中...")
        self._load_windows()
    
    def _on_selection_changed(self, event):
        """選択変更時"""
        try:
            selection = self.tree.selection()
            if not selection:
                self.selected_window = None
                self.detail_text.delete('1.0', 'end')
                return
            
            item = selection[0]
            hwnd = int(self.tree.item(item, 'tags')[0])
            
            # 選択されたウィンドウを検索
            self.selected_window = None
            for window in self.filtered_windows:
                if window.hwnd == hwnd:
                    self.selected_window = window
                    break
            
            # 詳細情報を表示
            if self.selected_window:
                detail_info = f"""ウィンドウハンドル: {self.selected_window.hwnd}
プロセス名: {self.selected_window.process_name}
プロセスID: {self.selected_window.process_id}
ウィンドウタイトル: {self.selected_window.title}
クラス名: {self.selected_window.class_name}
実行ファイル: {self.selected_window.exe_path}
表示状態: {'表示' if self.selected_window.is_visible else '非表示'}
有効状態: {'有効' if self.selected_window.is_enabled else '無効'}"""
                
                self.detail_text.delete('1.0', 'end')
                self.detail_text.insert('1.0', detail_info)
        
        except Exception as e:
            logger.error(f"Error in selection changed: {e}")
    
    def _on_double_click(self, event):
        """ダブルクリック時（OK扱い）"""
        if self.selected_window:
            self._on_ok()
    
    def _on_ok(self):
        """OK ボタン押下時"""
        if not self.selected_window:
            tk.messagebox.showwarning("警告", "ウィンドウが選択されていません")
            return
        
        self.result = self.selected_window
        self.dialog.destroy()
    
    def _on_cancel(self):
        """キャンセル ボタン押下時"""
        self.result = None
        self.dialog.destroy()
    
    def show(self) -> Optional[WindowInfo]:
        """ダイアログを表示して結果を返す"""
        # ダイアログの表示を待機
        self.parent.wait_window(self.dialog)
        return self.result


def show_window_selector(parent) -> Optional[WindowInfo]:
    """ウィンドウ選択ダイアログを表示（便利関数）"""
    dialog = WindowSelectorDialog(parent)
    return dialog.show()


# テスト用
if __name__ == "__main__":
    # テストウィンドウ
    root = ctk.CTk()
    root.geometry("300x200")
    
    def test_selector():
        result = show_window_selector(root)
        if result:
            print(f"Selected: {result}")
        else:
            print("Cancelled")
    
    ctk.CTkButton(root, text="ウィンドウ選択", command=test_selector).pack(pady=50)
    
    root.mainloop()