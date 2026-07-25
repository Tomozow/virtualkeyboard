"""
ボタン設定管理ウィンドウ - 高機能なキーパッドボタンの管理
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import json
import os
import copy
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import win32gui
import win32process
import psutil
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class ButtonManagerWindow:
    """ボタン設定管理メインウィンドウ"""
    
    def __init__(self, parent, config_manager, update_callback: Optional[Callable] = None, focus_manager=None):
        self.parent = parent
        self.config_manager = config_manager
        self.update_callback = update_callback
        self.focus_manager = focus_manager  # FocusManagerへの参照
        
        # プリセット関連
        self.presets = {}
        self.current_preset = "default"
        self.app_monitoring = False
        self.last_active_app = None
        
        # ウィンドウ作成
        self._create_window()
        self._load_presets()
        self._setup_app_monitoring()
        
        # 現在のconfig.jsonの設定を表示（プリセットは読み込まない）
        self._load_current_config_to_display()
        
        logger.info("Button manager window created")
    
    def _load_current_config_to_display(self):
        """現在のconfig.jsonの設定をボタン一覧に表示"""
        try:
            # 現在の設定を取得
            config = self.config_manager.config
            floating_config = config.get("floatingWindow", {})
            current_buttons = floating_config.get("buttons", [])
            
            # ボタン一覧を更新
            self._populate_button_list(current_buttons)
            
            # レイアウト設定も読み込み
            if hasattr(self, 'layout_direction_var'):
                self._load_layout_settings_from_config()
            
            self._show_status(f"現在のconfig.jsonを表示中（ボタン数: {len(current_buttons)}）")
            logger.info(f"Loaded current config to display: {len(current_buttons)} buttons")
            
        except Exception as e:
            logger.error(f"Failed to load current config to display: {e}")
            self._show_status("設定読み込みエラー")
    
    def _load_layout_settings_from_config(self):
        """config.jsonからレイアウト設定を読み込み"""
        try:
            config = self.config_manager.config
            floating_config = config.get("floatingWindow", {})
            layout_config = floating_config.get("layout", {})
            
            if hasattr(self, 'layout_direction_var'):
                self.layout_direction_var.set(floating_config.get("layoutDirection", "horizontal"))
            if hasattr(self, 'buttons_per_row_var'):
                self.buttons_per_row_var.set(layout_config.get("buttonsPerRow", 12))
            if hasattr(self, 'icon_size_var'):
                self.icon_size_var.set(layout_config.get("iconSize", 32))
                
        except Exception as e:
            logger.error(f"Failed to load layout settings from config: {e}")
    
    def _create_new_preset_with_options(self):
        """新規プリセット作成（選択ダイアログ付き）"""
        # 選択ダイアログを表示
        dialog = NewPresetTypeDialog(self.window)
        preset_type = dialog.get_result()
        
        if preset_type is None:
            return  # キャンセルされた
            
        # プリセット名入力ダイアログ
        name_dialog = PresetNameDialog(self.window, "新規プリセット作成")
        name, description = name_dialog.get_result()
        
        if not name:
            return
            
        if name in self.presets:
            messagebox.showerror("エラー", "同名のプリセットが既に存在します")
            return
            
        try:
            if preset_type == "from_config":
                # 現在のconfig.jsonから作成
                config = self.config_manager.config
                floating_config = config.get("floatingWindow", {})
                layout_config = floating_config.get("layout", {})
                
                new_preset = {
                    "name": name,
                    "description": description,
                    "buttons": floating_config.get("buttons", []),
                    "settings": {
                        "layoutDirection": floating_config.get("layoutDirection", "horizontal"),
                        "buttonsPerRow": layout_config.get("buttonsPerRow", 12),
                        "iconSize": layout_config.get("iconSize", 32),
                        "darkMode": floating_config.get("darkMode", False),
                        "showTitlebar": floating_config.get("showTitlebar", False)
                    },
                    "appBinding": None,
                    "created": datetime.now().isoformat(),
                    "modified": datetime.now().isoformat()
                }
                logger.info(f"Creating new preset from current config: {len(new_preset['buttons'])} buttons")
            else:
                # 空のプリセットを作成
                new_preset = {
                    "name": name,
                    "description": description,
                    "buttons": [],
                    "settings": {
                        "layoutDirection": "horizontal",
                        "buttonsPerRow": 12,
                        "iconSize": 32,
                        "darkMode": False,
                        "showTitlebar": False
                    },
                    "appBinding": None,
                    "created": datetime.now().isoformat(),
                    "modified": datetime.now().isoformat()
                }
                logger.info("Creating new empty preset")
            
            self.presets[name] = new_preset
            self._save_preset(name)
            self._update_preset_combobox()
            self.preset_combobox.set(name)
            self.current_preset = name
            
            self._show_status(f"プリセット '{name}' を作成しました")
            
        except Exception as e:
            logger.error(f"Failed to create new preset: {e}")
            messagebox.showerror("エラー", f"プリセット作成に失敗しました: {str(e)}")
    
    def _load_preset_to_config(self):
        """選択されたプリセットをconfig.jsonに読み込み"""
        if not self.current_preset or self.current_preset not in self.presets:
            messagebox.showwarning("警告", "読み込むプリセットが選択されていません")
            return
            
        # 確認ダイアログ
        if not messagebox.askyesno(
            "確認",
            f"プリセット '{self.current_preset}' をconfig.jsonに読み込みますか？\\n\\n"
            "現在の設定は上書きされます。"
        ):
            return
            
        try:
            # プリセットをconfig.jsonに適用
            self._apply_preset_to_config()
            self._refresh_floating_window()
            
            # 表示も更新
            self._load_current_config_to_display()
            
            self._show_status(f"プリセット '{self.current_preset}' をconfig.jsonに読み込みました")
            messagebox.showinfo("完了", f"プリセット '{self.current_preset}' を読み込みました")
            
        except Exception as e:
            logger.error(f"Failed to load preset to config: {e}")
            messagebox.showerror("エラー", f"プリセット読み込みに失敗しました: {str(e)}")
    
    def _overwrite_preset_from_config(self):
        """現在のconfig.jsonで選択中のプリセットを上書き"""
        if not self.current_preset:
            messagebox.showwarning("警告", "上書きするプリセットが選択されていません")
            return
            
        # 確認ダイアログ
        if not messagebox.askyesno(
            "確認",
            f"現在のconfig.jsonの設定でプリセット '{self.current_preset}' を上書きしますか？\\n\\n"
            "プリセットの内容は置き換えられます。"
        ):
            return
            
        try:
            # 現在の設定を取得
            config = self.config_manager.config
            floating_config = config.get("floatingWindow", {})
            layout_config = floating_config.get("layout", {})
            
            # プリセットを更新
            preset = self.presets[self.current_preset]
            preset["buttons"] = floating_config.get("buttons", [])
            preset["settings"] = {
                "layoutDirection": floating_config.get("layoutDirection", "horizontal"),
                "buttonsPerRow": layout_config.get("buttonsPerRow", 12),
                "iconSize": layout_config.get("iconSize", 32),
                "darkMode": floating_config.get("darkMode", False),
                "showTitlebar": floating_config.get("showTitlebar", False)
            }
            preset["modified"] = datetime.now().isoformat()
            
            # プリセットファイルを保存
            self._save_preset(self.current_preset)
            
            self._show_status(f"プリセット '{self.current_preset}' を現在の設定で上書きしました")
            messagebox.showinfo("完了", f"プリセット '{self.current_preset}' を上書きしました")
            
        except Exception as e:
            logger.error(f"Failed to overwrite preset from config: {e}")
            messagebox.showerror("エラー", f"プリセット上書きに失敗しました: {str(e)}")
    
    def _create_window(self):
        """メインウィンドウの作成"""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("ボタン設定管理")
        self.window.geometry("900x700")
        self.window.resizable(True, True)
        
        # ウィンドウを中央に配置
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.window.winfo_screenheight() // 2) - (700 // 2)
        self.window.geometry(f"900x700+{x}+{y}")
        
        # メインフレーム
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 上部ツールバー
        self._create_toolbar(main_frame)
        
        # コンテンツ領域（パネル分割）
        self._create_content_area(main_frame)
        
        # 下部ステータスバー
        self._create_status_bar(main_frame)
        
        # ウィンドウ終了時の処理
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_toolbar(self, parent):
        """上部ツールバーの作成"""
        toolbar_frame = ctk.CTkFrame(parent)
        toolbar_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # プリセット管理
        preset_frame = ctk.CTkFrame(toolbar_frame)
        preset_frame.pack(side="left", padx=5, pady=5)
        
        ctk.CTkLabel(preset_frame, text="プリセット:").pack(side="left", padx=5)
        
        # 統合されたプリセット選択・編集コンボボックス
        self.preset_combobox = ctk.CTkComboBox(
            preset_frame,
            values=["default"],
            command=self._on_preset_selection,
            width=200,
            state="normal"  # 編集可能に設定
        )
        self.preset_combobox.pack(side="left", padx=5)
        
        # Enterキーとフォーカスアウトでの名前変更をバインド
        self.preset_combobox.bind("<Return>", self._on_preset_name_edited)
        self.preset_combobox.bind("<FocusOut>", self._on_preset_name_edited)
        
        # 現在編集中かどうかのフラグ
        self._editing_preset_name = False
        
        # プリセット操作ボタン
        ctk.CTkButton(
            preset_frame,
            text="新規",
            command=self._create_new_preset_with_options,
            width=60
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            preset_frame,
            text="読込",
            command=self._load_preset_to_config,
            width=60,
            fg_color="green"
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            preset_frame,
            text="上書き",
            command=self._overwrite_preset_from_config,
            width=60,
            fg_color="orange"
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            preset_frame,
            text="複製",
            command=self._duplicate_preset,
            width=60
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            preset_frame,
            text="削除",
            command=self._delete_preset,
            width=60
        ).pack(side="left", padx=2)
        
        # インポート/エクスポート
        io_frame = ctk.CTkFrame(toolbar_frame)
        io_frame.pack(side="right", padx=5, pady=5)
        
        self.export_button = ctk.CTkButton(
            io_frame,
            text="エクスポート",
            command=self._export_preset,
            width=80
        )
        self.export_button.pack(side="left", padx=2)
        logger.info(f"Export button created: {self.export_button}")
        
        ctk.CTkButton(
            io_frame,
            text="インポート",
            command=self._import_preset,
            width=80
        ).pack(side="left", padx=2)
        
        # アプリ連動設定
        app_frame = ctk.CTkFrame(toolbar_frame)
        app_frame.pack(side="left", padx=10, pady=5)
        
        self.app_monitoring_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            app_frame,
            text="アプリ連動",
            variable=self.app_monitoring_var,
            command=self._toggle_app_monitoring
        ).pack(side="left", padx=5)
    
    def _create_content_area(self, parent):
        """コンテンツ領域の作成"""
        content_frame = ctk.CTkFrame(parent)
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # タブビューを作成
        self.tabview = ctk.CTkTabview(content_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # ボタン一覧タブ
        button_tab = self.tabview.add("ボタン設定")
        self._create_button_list_panel(button_tab)
        
        # レイアウト設定タブ
        layout_tab = self.tabview.add("レイアウト設定")
        self._create_layout_settings_panel(layout_tab)
        
        # アプリ連動タブ
        app_binding_tab = self.tabview.add("アプリ連動")
        self._create_app_binding_panel(app_binding_tab)
        
        # 初期選択をボタン設定タブに
        self.tabview.set("ボタン設定")
    
    def _create_button_list_panel(self, parent):
        """ボタン一覧パネル"""
        # ヘッダー
        header_frame = ctk.CTkFrame(parent)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(header_frame, text="ボタン一覧", font=("", 16, "bold")).pack(side="left")
        
        # ボタン操作
        btn_frame = ctk.CTkFrame(header_frame)
        btn_frame.pack(side="right")
        
        ctk.CTkButton(
            btn_frame,
            text="追加",
            command=self._add_button,
            width=60
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="削除",
            command=self._delete_button,
            width=60
        ).pack(side="left", padx=2)
        
        # ボタンリスト
        list_frame = ctk.CTkFrame(parent)
        list_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        
        # Treeviewを使用（カスタマイズされたリスト表示）
        columns = ("order", "label", "key", "color", "modifiers", "toggle", "highlight_color", "description")
        
        # スタイル設定（フォントサイズを大きく）
        style = ttk.Style()
        style.configure("Custom.Treeview", font=("", 14))  # フォントサイズ14
        style.configure("Custom.Treeview.Heading", font=("", 15, "bold"))  # ヘッダーは15で太字
        
        # 行の高さを設定（アイコン表示のため少し高く）
        style.configure("Custom.Treeview", rowheight=50)  # 行の高さを50pxに
        
        # テキスト左揃えの設定
        style.configure("Custom.Treeview", anchor='w')  # テキストを左揃え
        style.configure("Custom.Treeview.Heading", anchor='w')  # ヘッダーも左揃え
        
        self.button_tree = ttk.Treeview(
            list_frame, 
            columns=columns, 
            show="tree headings",  # treeを追加してアイコン表示を有効化
            height=12,
            style="Custom.Treeview"
        )
        
        # アイコン用のイメージ辞書
        self.tree_images = {}
        
        # カラム設定
        self.button_tree.heading("#0", text="アイコン", anchor='center')  # アイコン列ヘッダーは中央揃え
        self.button_tree.heading("order", text="")  # 順序列（非表示）
        self.button_tree.heading("label", text="ラベル", anchor='w')  # ラベル列ヘッダーは左揃え
        self.button_tree.heading("key", text="キー", anchor='w')  # キー列ヘッダーは左揃え
        self.button_tree.heading("color", text="背景色", anchor='w')
        self.button_tree.heading("modifiers", text="修飾キー", anchor='w')
        self.button_tree.heading("toggle", text="トグル", anchor='w')
        self.button_tree.heading("highlight_color", text="ハイライト色", anchor='w')
        self.button_tree.heading("description", text="説明", anchor='w')  # 説明列ヘッダーは左揃え
        
        self.button_tree.column("#0", width=40, anchor='center')  # アイコン列は中央揃えのまま
        self.button_tree.column("order", width=0, stretch=False)  # 順序列（非表示）
        self.button_tree.column("label", width=100, anchor='w')  # ラベル列を左揃え
        self.button_tree.column("key", width=120, anchor='w')  # キー列を左揃え
        self.button_tree.column("color", width=80, anchor='w')  # 背景色列
        self.button_tree.column("modifiers", width=80, anchor='w')  # 修飾キー列
        self.button_tree.column("toggle", width=50, anchor='center')  # トグル列
        self.button_tree.column("highlight_color", width=80, anchor='w')  # ハイライト色列
        self.button_tree.column("description", width=200, anchor='w')  # 説明列を左揃え
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.button_tree.yview)
        self.button_tree.configure(yscrollcommand=scrollbar.set)
        
        # パック
        self.button_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # イベントバインド
        self.button_tree.bind("<<TreeviewSelect>>", self._on_button_select)
        self.button_tree.bind("<Double-1>", self._on_button_double_click)
        
        # 並び替えボタン
        sort_frame = ctk.CTkFrame(parent)
        sort_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(
            sort_frame,
            text="▲ 上に移動",
            command=self._move_button_up,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            sort_frame,
            text="▼ 下に移動",
            command=self._move_button_down,
            width=100
        ).pack(side="left", padx=5)
    
    def _create_layout_settings_panel(self, parent):
        """レイアウト設定パネル"""
        # スクロール可能なフレーム
        scroll_frame = ctk.CTkScrollableFrame(parent)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # レイアウト方向設定
        direction_frame = ctk.CTkFrame(scroll_frame)
        direction_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(direction_frame, text="レイアウト方向:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.layout_direction_var = tk.StringVar()
        direction_radio_frame = ctk.CTkFrame(direction_frame)
        direction_radio_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkRadioButton(
            direction_radio_frame,
            text="横並び (Horizontal)",
            variable=self.layout_direction_var,
            value="horizontal",
            command=self._on_layout_setting_changed
        ).pack(side="left", padx=10, pady=5)
        
        ctk.CTkRadioButton(
            direction_radio_frame,
            text="縦並び (Vertical)",
            variable=self.layout_direction_var,
            value="vertical",
            command=self._on_layout_setting_changed
        ).pack(side="left", padx=10, pady=5)
        
        # ボタンレイアウト設定
        button_layout_frame = ctk.CTkFrame(scroll_frame)
        button_layout_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(button_layout_frame, text="ボタンレイアウト:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # 一列のボタン数
        buttons_per_row_frame = ctk.CTkFrame(button_layout_frame)
        buttons_per_row_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(buttons_per_row_frame, text="一列のボタン数:", width=120).pack(side="left", padx=5)
        self.buttons_per_row_var = tk.IntVar()
        self.buttons_per_row_slider = ctk.CTkSlider(
            buttons_per_row_frame,
            from_=1,
            to=20,
            number_of_steps=19,
            variable=self.buttons_per_row_var,
            command=self._on_layout_setting_changed
        )
        self.buttons_per_row_slider.pack(side="left", fill="x", expand=True, padx=5)
        
        self.buttons_per_row_entry = ctk.CTkEntry(buttons_per_row_frame, width=50)
        self.buttons_per_row_entry.pack(side="right", padx=5)
        self.buttons_per_row_entry.bind("<Return>", self._on_entry_changed)
        self.buttons_per_row_entry.bind("<FocusOut>", self._on_entry_changed)
        
        # アイコンサイズ設定
        icon_size_frame = ctk.CTkFrame(button_layout_frame)
        icon_size_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkLabel(icon_size_frame, text="アイコンサイズ:", width=120).pack(side="left", padx=5)
        self.icon_size_var = tk.IntVar()
        self.icon_size_slider = ctk.CTkSlider(
            icon_size_frame,
            from_=16,
            to=64,
            number_of_steps=48,
            variable=self.icon_size_var,
            command=self._on_layout_setting_changed
        )
        self.icon_size_slider.pack(side="left", fill="x", expand=True, padx=5)
        
        self.icon_size_entry = ctk.CTkEntry(icon_size_frame, width=50)
        self.icon_size_entry.pack(side="right", padx=5)
        self.icon_size_entry.bind("<Return>", self._on_entry_changed)
        self.icon_size_entry.bind("<FocusOut>", self._on_entry_changed)
        
        # 表示設定
        display_frame = ctk.CTkFrame(scroll_frame)
        display_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(display_frame, text="表示設定:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # チェックボックス設定
        checkbox_frame = ctk.CTkFrame(display_frame)
        checkbox_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.dark_mode_var = tk.BooleanVar()
        self.dark_mode_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text="ダークモード",
            variable=self.dark_mode_var,
            command=self._on_layout_setting_changed
        )
        self.dark_mode_checkbox.pack(side="left", padx=10, pady=5)
        
        self.show_titlebar_var = tk.BooleanVar()
        ctk.CTkCheckBox(
            checkbox_frame,
            text="タイトルバー表示",
            variable=self.show_titlebar_var,
            command=self._on_layout_setting_changed
        ).pack(side="left", padx=10, pady=5)
        
        # 初期値を読み込み
        self._load_layout_settings()
    
    def _create_app_binding_panel(self, parent):
        """アプリ連動設定パネル"""
        # スクロール可能なフレーム
        scroll_frame = ctk.CTkScrollableFrame(parent)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # タイトル
        title_frame = ctk.CTkFrame(scroll_frame)
        title_frame.pack(fill="x", padx=5, pady=(0, 10))
        
        ctk.CTkLabel(
            title_frame, 
            text="アプリ連動設定", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)
        
        ctk.CTkLabel(
            title_frame,
            text="復帰ウィンドウに応じて自動的にプリセットを切り替える機能です。",
            font=ctk.CTkFont(size=12)
        ).pack(pady=(0, 10))
        
        # 基本設定
        basic_frame = ctk.CTkFrame(scroll_frame)
        basic_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(basic_frame, text="基本設定:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # アプリ連動有効/無効
        binding_enabled_frame = ctk.CTkFrame(basic_frame)
        binding_enabled_frame.pack(fill="x", padx=10, pady=5)
        
        self.app_binding_enabled_var = tk.BooleanVar()
        ctk.CTkCheckBox(
            binding_enabled_frame,
            text="このプリセットでアプリ連動を有効にする",
            variable=self.app_binding_enabled_var,
            command=self._on_app_binding_setting_changed,
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=5, pady=5)
        
        # ウィンドウ選択設定
        window_frame = ctk.CTkFrame(scroll_frame)
        window_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(window_frame, text="ウィンドウ選択:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # ウィンドウ名設定
        window_name_frame = ctk.CTkFrame(window_frame)
        window_name_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(window_name_frame, text="連動対象:", width=100).pack(side="left", padx=5)
        self.app_window_name_var = tk.StringVar()
        self.app_window_name_entry = ctk.CTkEntry(
            window_name_frame,
            textvariable=self.app_window_name_var,
            width=300,
            placeholder_text="例: chrome.exe、Google Chrome、Chrome_WidgetWin_1"
        )
        self.app_window_name_entry.pack(side="left", padx=5)
        self.app_window_name_entry.bind('<KeyRelease>', self._on_app_binding_setting_changed)
        
        # ウィンドウ選択ボタン
        ctk.CTkButton(
            window_name_frame,
            text="ウィンドウ一覧から選択",
            command=self._on_select_window,
            width=140
        ).pack(side="left", padx=10)
        
        # マッチング設定
        match_frame = ctk.CTkFrame(scroll_frame)
        match_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(match_frame, text="マッチング設定:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # マッチング対象設定
        match_target_frame = ctk.CTkFrame(match_frame)
        match_target_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(match_target_frame, text="対象:", width=100).pack(side="left", padx=5)
        self.app_match_target_var = tk.StringVar(value="windowTitle")
        
        ctk.CTkRadioButton(
            match_target_frame,
            text="ウィンドウタイトル",
            variable=self.app_match_target_var,
            value="windowTitle",
            command=self._on_app_binding_setting_changed
        ).pack(side="left", padx=5)
        
        ctk.CTkRadioButton(
            match_target_frame,
            text="プロセス名",
            variable=self.app_match_target_var,
            value="processName", 
            command=self._on_app_binding_setting_changed
        ).pack(side="left", padx=5)
        
        ctk.CTkRadioButton(
            match_target_frame,
            text="クラス名",
            variable=self.app_match_target_var,
            value="className",
            command=self._on_app_binding_setting_changed
        ).pack(side="left", padx=5)
        
        # 一致方式設定
        match_type_frame = ctk.CTkFrame(match_frame)
        match_type_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(match_type_frame, text="方式:", width=100).pack(side="left", padx=5)
        self.app_match_type_var = tk.StringVar(value="partial")
        
        ctk.CTkRadioButton(
            match_type_frame,
            text="部分一致",
            variable=self.app_match_type_var,
            value="partial",
            command=self._on_app_binding_setting_changed
        ).pack(side="left", padx=10)
        
        ctk.CTkRadioButton(
            match_type_frame,
            text="完全一致",
            variable=self.app_match_type_var,
            value="exact",
            command=self._on_app_binding_setting_changed
        ).pack(side="left", padx=10)
        
        # 優先度設定
        priority_frame = ctk.CTkFrame(match_frame)
        priority_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(priority_frame, text="優先度:", width=100).pack(side="left", padx=5)
        self.app_priority_var = tk.IntVar(value=1)
        ctk.CTkSlider(
            priority_frame,
            from_=1,
            to=10,
            variable=self.app_priority_var,
            width=200,
            command=self._on_app_binding_setting_changed
        ).pack(side="left", padx=5)
        
        self.priority_label = ctk.CTkLabel(priority_frame, text="1", width=30)
        self.priority_label.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            priority_frame,
            text="(複数プリセットが一致する場合の優先順位)",
            font=ctk.CTkFont(size=10)
        ).pack(side="left", padx=10)
        
        # 監視状態表示のみ
        monitoring_frame = ctk.CTkFrame(scroll_frame)
        monitoring_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(monitoring_frame, text="監視状態:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        status_inner_frame = ctk.CTkFrame(monitoring_frame)
        status_inner_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.monitoring_status_label = ctk.CTkLabel(
            status_inner_frame,
            text="停止中",
            width=100,
            anchor="w",
            font=ctk.CTkFont(size=11)
        )
        self.monitoring_status_label.pack(side="left", padx=5)
        
        # 初期値を読み込み
        self._load_app_binding_settings()
    
    def _create_status_bar(self, parent):
        """ステータスバー"""
        self.status_frame = ctk.CTkFrame(parent)
        self.status_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="準備完了",
            anchor="w"
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
        # 現在の復帰ウィンドウ表示
        self.current_focus_window_status_label = ctk.CTkLabel(
            self.status_frame,
            text="復帰ウィンドウ: 未取得",
            anchor="e"
        )
        self.current_focus_window_status_label.pack(side="right", padx=10, pady=5)
    
    def _load_presets(self):
        """プリセットの読み込み"""
        try:
            # 最新の設定を再読み込み
            self.config_manager.config = self.config_manager.load_config()
            config = self.config_manager.config
            
            # プリセットディレクトリが存在しない場合は作成
            preset_dir = "presets"
            if not os.path.exists(preset_dir):
                os.makedirs(preset_dir)
            
            # プリセットファイルを先に読み込み
            for filename in os.listdir(preset_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(preset_dir, filename), 'r', encoding='utf-8') as f:
                            preset_data = json.load(f)
                            preset_name = preset_data.get("name", filename[:-5])
                            self.presets[preset_name] = preset_data
                    except Exception as e:
                        logger.warning(f"Failed to load preset {filename}: {e}")
            
            # デフォルトプリセットが存在しない場合のみ作成（現在の設定から）
            if "default" not in self.presets:
                floating_config = config.get("floatingWindow", {})
                layout_config = floating_config.get("layout", {})
                default_preset = {
                    "name": "default",
                    "description": "デフォルト設定",
                    "buttons": floating_config.get("buttons", []),
                    "settings": {
                        "layoutDirection": floating_config.get("layoutDirection", "horizontal"),
                        "buttonsPerRow": layout_config.get("buttonsPerRow", 12),
                        "iconSize": layout_config.get("iconSize", 32),
                        "darkMode": floating_config.get("darkMode", False),
                        "showTitlebar": floating_config.get("showTitlebar", False)
                    },
                    "appBinding": None,
                    "created": datetime.now().isoformat(),
                    "modified": datetime.now().isoformat()
                }
                self.presets["default"] = default_preset
                # デフォルトプリセットファイルを保存
                self._save_preset("default")
            
            # コンボボックスを更新（プリセットは選択するが読み込まない）
            self.current_preset = "default"
            self._update_preset_combobox()
            
            # 初期化時はconfig.jsonの内容を表示（プリセットは適用しない）
            # self._load_current_preset()  # コメントアウト
            # self._apply_preset_to_config()  # コメントアウト
            # self._refresh_floating_window()  # コメントアウト
            
            # 全プリセットのデータ検証・修正
            self._validate_and_fix_presets()
            
            logger.info(f"Loaded {len(self.presets)} presets")
            
        except Exception as e:
            logger.error(f"Failed to load presets: {e}")
            self._show_status("プリセット読み込みエラー")
    
    def _validate_and_fix_presets(self):
        """全プリセットのデータを検証・修正"""
        for preset_name, preset_data in self.presets.items():
            try:
                buttons = preset_data.get("buttons", [])
                fixed_buttons = []
                
                for i, button in enumerate(buttons):
                    fixed_button = self._validate_and_fix_button(button, f"{preset_name}[{i}]")
                    fixed_buttons.append(fixed_button)
                
                preset_data["buttons"] = fixed_buttons
                
                # 修復したプリセットを保存
                preset_data["modified"] = datetime.now().isoformat()
                self._save_preset(preset_name)
                
                logger.info(f"Validated preset '{preset_name}': {len(fixed_buttons)} buttons")
                
            except Exception as e:
                logger.error(f"Error validating preset '{preset_name}': {e}")
    
    def _validate_and_fix_button(self, button, location="unknown"):
        """ボタンデータを検証・修正"""
        try:
            # 必須フィールドのデフォルト値
            fixed_button = {
                "key": button.get("key", "F13"),
                "label": button.get("label", ""),
                "icon": button.get("icon", ""),
                "color": button.get("color", "transparent"),
                "toggleHighlight": button.get("toggleHighlight", False),
                "highlightColor": button.get("highlightColor", ""),
                "modifiers": button.get("modifiers", {
                    "ctrl": False,
                    "shift": False,
                    "alt": False,
                    "win": False
                }),
                "description": button.get("description", "")
            }
            
            # 色の値を検証・修正
            fixed_button["color"] = self._validate_color(fixed_button["color"], "transparent")
            fixed_button["highlightColor"] = self._validate_color(fixed_button["highlightColor"], "")
            
            # modifiersの検証
            if not isinstance(fixed_button["modifiers"], dict):
                fixed_button["modifiers"] = {
                    "ctrl": False,
                    "shift": False, 
                    "alt": False,
                    "win": False
                }
            else:
                # 各修飾キーのデフォルト値を設定
                for key in ["ctrl", "shift", "alt", "win"]:
                    if key not in fixed_button["modifiers"]:
                        fixed_button["modifiers"][key] = False
            
            return fixed_button
            
        except Exception as e:
            logger.error(f"Error fixing button at {location}: {e}")
            # 完全に破損したボタンの場合、デフォルトボタンを返す
            return {
                "key": "F13",
                "label": "修復済み",
                "icon": "",
                "color": "transparent", 
                "toggleHighlight": False,
                "highlightColor": "",
                "modifiers": {
                    "ctrl": False,
                    "shift": False,
                    "alt": False,
                    "win": False
                },
                "description": "データが破損していたため修復されました"
            }
    
    def _validate_color(self, color_value, default_value):
        """色の値を検証・修正"""
        if not color_value:
            return default_value
        
        # 透明とdefaultは有効
        if color_value in ["transparent", "default"]:
            return color_value
        
        # HEX色の検証
        if isinstance(color_value, str) and color_value.startswith("#"):
            # 正しいHEX形式かチェック
            hex_part = color_value[1:]
            if len(hex_part) == 6 and all(c in "0123456789ABCDEFabcdef" for c in hex_part):
                return color_value
            else:
                logger.warning(f"Invalid hex color '{color_value}', using default")
                return default_value
        
        # 色名の場合
        valid_color_names = ["red", "green", "blue", "yellow", "orange", "purple", "gray", "grey", "black", "white"]
        if isinstance(color_value, str) and color_value.lower() in valid_color_names:
            return color_value
        
        logger.warning(f"Invalid color value '{color_value}', using default")
        return default_value
    
    def _update_preset_combobox(self):
        """プリセットコンボボックスの更新"""
        preset_names = list(self.presets.keys())
        self.preset_combobox.configure(values=preset_names)
        if self.current_preset in preset_names:
            self.preset_combobox.set(self.current_preset)
    
    def _load_current_preset(self):
        """現在のプリセットを読み込み"""
        if self.current_preset not in self.presets:
            logger.warning(f"Preset '{self.current_preset}' not found, falling back to 'default'")
            self.current_preset = "default"
        
        
        preset = self.presets[self.current_preset]
        button_count = len(preset.get("buttons", []))
        logger.info(f"Loading preset: {self.current_preset}, buttons: {button_count}")
        self._populate_button_list(preset.get("buttons", []))
        
        # レイアウト設定も読み込み
        if hasattr(self, 'layout_direction_var'):
            self._load_layout_settings()
        
        # アプリ連動設定も読み込み
        if hasattr(self, 'app_binding_enabled_var'):
            self._load_app_binding_settings()
        
        self._show_status(f"プリセット '{self.current_preset}' を読み込みました")
    
    def _populate_button_list(self, buttons):
        """ボタン一覧の表示"""
        # 既存項目をクリア
        for item in self.button_tree.get_children():
            self.button_tree.delete(item)
        
        # 古いイメージ参照をクリア
        self.tree_images.clear()
        
        # ボタンを表示
        for i, button in enumerate(buttons):
            label = button.get("label", "")
            key = button.get("key", "")
            description = button.get("description", "")
            
            # 追加設定情報を取得
            color = button.get("color", "transparent")
            color_display = color if color != "transparent" else "透明"
            
            # 修飾キーの表示文字列を生成
            modifiers = button.get("modifiers", {})
            mod_list = []
            if modifiers.get("ctrl", False): mod_list.append("Ctrl")
            if modifiers.get("shift", False): mod_list.append("Shift")  
            if modifiers.get("alt", False): mod_list.append("Alt")
            if modifiers.get("win", False): mod_list.append("Win")
            modifiers_display = "+".join(mod_list) if mod_list else "-"
            
            # トグル機能
            toggle_highlight = button.get("toggleHighlight", False)
            toggle_display = "✓" if toggle_highlight else ""
            
            # ハイライト色
            highlight_color = button.get("highlightColor", "")
            highlight_display = highlight_color if highlight_color else "-"
            
            # アイコン画像を生成
            icon_image = self._create_button_preview_image(button)
            
            # 画像をTreeviewで使用するため保持
            if icon_image:
                self.tree_images[f"button_{i}"] = icon_image
            
            # ボタンを挿入
            item_id = self.button_tree.insert(
                "",
                "end",
                text="",  # アイコン列にはテキスト表示しない（画像のみ）
                image=icon_image if icon_image else "",
                values=("", label, key, color_display, modifiers_display, toggle_display, highlight_display, description),
                tags=(f"button_{i}",)
            )
    
    def _create_button_preview_image(self, button_config):
        """ボタンのプレビュー画像を生成"""
        try:
            # プレビュー画像のサイズ（列幅と同じに）
            width, height = 40, 40  # 列幅40pxと同じサイズに
            
            # ベース画像を作成
            img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # ボタンの背景色を決定（実際の設定値を使用）
            bg_color = button_config.get("color", "default")
            
            # 色の値を正規化
            is_transparent = False
            if bg_color == "transparent":
                is_transparent = True
                bg_color = "#f0f0f0"  # 透明の場合は薄いグレー背景
            elif bg_color == "default" or not bg_color:
                bg_color = "#7f7f7f"  # デフォルトグレー
            elif bg_color.startswith("#"):
                # すでにHEX形式の場合はそのまま使用
                pass
            else:
                # 色名からHEX値にマッピング
                color_map = {
                    "blue": "#1f77b4",
                    "green": "#2ca02c", 
                    "red": "#dc2626",  # 設定ファイルの#dc2626に合わせる
                    "orange": "#ff7f0e",
                    "purple": "#9467bd",
                    "gray": "#7f7f7f",
                    "grey": "#7f7f7f"
                }
                bg_color = color_map.get(bg_color.lower(), "#7f7f7f")
            
            # 背景を画像全体に描画
            bg_left = 2
            bg_right = width - 2
            
            # 角丸の背景を描画（フチなし）
            if is_transparent:
                # 透明背景の場合は薄いグレー背景
                draw.rounded_rectangle(
                    [(bg_left, 2), (bg_right, height-2)],
                    radius=6,
                    fill="#f8f8f8",
                    outline=None  # フチを削除
                )
                # 透明を示す斜線パターンを追加
                for i in range(bg_left, bg_right, 6):
                    if i + 4 <= bg_right:
                        draw.line([(i, 2), (i+4, 6)], fill="#e0e0e0", width=1)
            else:
                draw.rounded_rectangle(
                    [(bg_left, 2), (bg_right, height-2)],
                    radius=6,
                    fill=bg_color,
                    outline=None  # フチを削除
                )
            
            # アイコン・絵文字・ラベルを描画
            icon = button_config.get("icon", "")
            label = button_config.get("label", "")
            
            # 表示するテキストを決定（アイコン優先）
            display_text = icon if icon else label
            
            if display_text:
                try:
                    # フォントサイズを調整
                    # 絵文字や記号の場合はより大きなフォントを使用
                    if self._is_emoji_or_symbol(display_text):
                        font_size = 20  # 絵文字用の大きなフォント
                    else:
                        font_size = 12
                        if len(display_text) > 3:
                            font_size = 10
                        if len(display_text) > 5:
                            font_size = 8
                    
                    # フォントを取得
                    font = self._get_best_font_for_text(display_text, font_size)
                    
                    # テキストのサイズを計算
                    text_bbox = draw.textbbox((0, 0), display_text, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    
                    # テキストを中央に配置
                    text_x = (width - text_width) // 2
                    text_y = (height - text_height) // 2
                    
                    # テキストを描画
                    if self._is_emoji_or_symbol(display_text):
                        # 絵文字や記号の場合は元の色を保持
                        text_color = "black"  # 絵文字は通常黒いアウトラインが見やすい
                    elif is_transparent:
                        # 透明背景の場合は濃い色
                        text_color = "#333333"
                    else:
                        # 通常の背景色の場合は白文字
                        text_color = "white"
                    
                    draw.text(
                        (text_x, text_y),
                        display_text,
                        fill=text_color,
                        font=font
                    )
                    
                except Exception as e:
                    logger.debug(f"Text drawing error: {e}")
                    # フォールバック: シンプルなテキスト表示
                    try:
                        draw.text((width//4, height//3), display_text[:2], fill="white")
                    except:
                        pass
            
            # アイコンファイル（画像）がある場合は優先表示
            if icon and os.path.exists(icon):
                try:
                    icon_img = Image.open(icon)
                    icon_img = icon_img.resize((width-4, height-4), Image.Resampling.LANCZOS)
                    
                    # アイコンを中央に貼り付け
                    if icon_img.mode == 'RGBA':
                        img.paste(icon_img, (2, 2), icon_img)
                    else:
                        img.paste(icon_img, (2, 2))
                        
                except Exception as e:
                    logger.debug(f"Icon loading error: {e}")
            
            # Tkinter用のPhotoImageに変換
            import tkinter as tk
            import io
            import base64
            
            # PIL ImageをPNG形式でBase64エンコード
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_data = buffer.getvalue()
            img_b64 = base64.b64encode(img_data)
            
            # PhotoImageを作成
            photo = tk.PhotoImage(data=img_b64)
            return photo
            
        except Exception as e:
            logger.error(f"Error creating preview image: {e}")
            return None
    
    def _is_emoji_or_symbol(self, text):
        """テキストが絵文字や記号かどうかを判定"""
        if not text:
            return False
        
        # 一般的な絵文字・記号の判定
        emoji_ranges = [
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
            (0x1F680, 0x1F6FF),  # Transport and Map
            (0x1F1E0, 0x1F1FF),  # Regional Indicator Symbols
            (0x2600, 0x26FF),    # Miscellaneous Symbols
            (0x2700, 0x27BF),    # Dingbats
            (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
        ]
        
        # 最初の文字をチェック
        char = text[0]
        char_code = ord(char)
        
        # 絵文字範囲チェック
        for start, end in emoji_ranges:
            if start <= char_code <= end:
                return True
        
        # よく使われる記号文字
        common_symbols = "↔⇅▶◁⛳🟡🟫🔰💾🧺🎦"
        return char in common_symbols
    
    def _get_best_font_for_text(self, text, font_size):
        """テキストに最適なフォントを取得"""
        if self._is_emoji_or_symbol(text):
            # 絵文字・記号用フォント
            emoji_fonts = [
                "Segoe UI Emoji",
                "Apple Color Emoji",
                "Noto Color Emoji",
                "Microsoft YaHei UI",
                "Segoe UI Symbol",
                "Symbola"
            ]
            
            for font_name in emoji_fonts:
                try:
                    return ImageFont.truetype(font_name, font_size)
                except:
                    continue
            
            # Windowsの絵文字フォントパス
            emoji_font_paths = [
                "C:/Windows/Fonts/seguiemj.ttf",
                "C:/Windows/Fonts/NotoColorEmoji.ttf",
                "C:/Windows/Fonts/seguisym.ttf"
            ]
            
            for font_path in emoji_font_paths:
                try:
                    return ImageFont.truetype(font_path, font_size)
                except:
                    continue
        else:
            # 通常テキスト用フォント
            text_fonts = [
                "arial.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/msgothic.ttc",
                "C:/Windows/Fonts/meiryo.ttc"
            ]
            
            for font_path in text_fonts:
                try:
                    return ImageFont.truetype(font_path, font_size)
                except:
                    continue
        
        # フォールバック
        return ImageFont.load_default()
    
    def _setup_app_monitoring(self):
        """アプリケーション監視の設定"""
        self.monitoring_thread = None
        self.monitoring_active = False
    
    def _toggle_app_monitoring(self):
        """アプリ連動の有効/無効切り替え"""
        if self.app_monitoring_var.get():
            self._start_app_monitoring()
        else:
            self._stop_app_monitoring()
    
    def _start_app_monitoring(self):
        """アプリケーション監視開始"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._app_monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            self._show_status("アプリ連動監視を開始しました")
            logger.info("App monitoring started")
    
    def _stop_app_monitoring(self):
        """アプリケーション監視停止"""
        if self.monitoring_active:
            self.monitoring_active = False
            self._show_status("アプリ連動監視を停止しました")
            logger.info("App monitoring stopped")
    
    def _app_monitoring_loop(self):
        """アプリケーション監視ループ"""
        last_focus_window_title = None
        
        while self.monitoring_active:
            try:
                # FocusManagerから復帰ウィンドウ名を取得
                focus_window_title = self._get_focus_window_title()
                
                # 復帰ウィンドウが変更された場合
                if focus_window_title != last_focus_window_title:
                    last_focus_window_title = focus_window_title
                    
                    # UI更新（メインスレッドで実行）
                    self.window.after(0, self._update_focus_window_display, focus_window_title)
                    
                    # プリセット切り替えのチェック（復帰ウィンドウ名ベース）
                    if focus_window_title:
                        self._check_focus_window_preset_binding(focus_window_title)
                
            except Exception as e:
                logger.debug(f"App monitoring error: {e}")
            
            time.sleep(1)  # 1秒間隔で監視
    
    def _get_focus_window_title(self):
        """FocusManagerから復帰ウィンドウのタイトルを取得"""
        try:
            # メインアプリのFocusManagerにアクセス
            if hasattr(self, 'focus_manager') and self.focus_manager:
                focus_window = self.focus_manager.get_last_focus_window()
                if focus_window:
                    import win32gui
                    return win32gui.GetWindowText(focus_window)
            return None
        except Exception as e:
            logger.debug(f"Error getting focus window title: {e}")
            return None
    
    def _update_focus_window_display(self, window_title):
        """復帰ウィンドウ表示の更新（アプリ監視用）"""
        if hasattr(self, 'current_focus_window_label'):
            display_title = window_title if window_title else "未取得"
            self.current_focus_window_label.configure(text=display_title)
    
    def _update_current_focus_window_display(self):
        """現在の復帰ウィンドウ名を取得してステータスバーに表示"""
        focus_window_title = self._get_focus_window_title()
        display_title = focus_window_title if focus_window_title else "未取得"
        
        # ステータスバーのラベルを更新
        if hasattr(self, 'current_focus_window_status_label'):
            self.current_focus_window_status_label.configure(text=f"復帰ウィンドウ: {display_title}")
    
    
    def _check_focus_window_preset_binding(self, window_title):
        """復帰ウィンドウ名とプリセットのバインディングをチェック（拡張版）"""
        if not window_title:
            return
            
        matching_presets = []
        
        # FocusManagerから復帰ウィンドウの詳細情報を取得
        focus_window_info = None
        if hasattr(self, 'focus_manager') and self.focus_manager:
            try:
                focus_window = self.focus_manager.get_last_focus_window()
                if focus_window:
                    from virtual_keyboard.utils.window_utils import WindowEnumerator
                    focus_window_info = WindowEnumerator.get_window_by_hwnd(focus_window)
            except Exception as e:
                logger.debug(f"Error getting focus window info: {e}")
        
        for preset_name, preset in self.presets.items():
            app_binding = preset.get("appBinding", {})
            if isinstance(app_binding, dict) and app_binding.get("enabled", False):
                window_name = app_binding.get("windowName", "")
                match_target = app_binding.get("matchTarget", "windowTitle")
                match_type = app_binding.get("matchType", "partial")
                priority = app_binding.get("priority", 1)
                
                if not window_name:
                    continue
                
                # マッチング判定（拡張版）
                is_match = False
                
                if match_target == "windowTitle":
                    # ウィンドウタイトルでマッチング（従来通り）
                    is_match = self._is_string_match(window_title, window_name, match_type)
                elif focus_window_info:
                    # 詳細情報が取得できた場合の拡張マッチング
                    if match_target == "processName":
                        is_match = self._is_string_match(focus_window_info.process_name, window_name, match_type)
                    elif match_target == "className":
                        is_match = self._is_string_match(focus_window_info.class_name, window_name, match_type)
                    else:
                        # 不明なマッチ対象の場合はタイトルでフォールバック
                        is_match = self._is_string_match(window_title, window_name, match_type)
                
                if is_match:
                    matching_presets.append((preset_name, priority))
                    logger.debug(f"Matched preset '{preset_name}' with {match_target}='{window_name}' (priority={priority})")
        
        # 優先度が最も高いプリセットを選択
        if matching_presets:
            matching_presets.sort(key=lambda x: x[1], reverse=True)  # 優先度降順
            target_preset = matching_presets[0][0]
            
            if target_preset != self.current_preset:
                self.window.after(0, self._switch_to_preset, target_preset)
                logger.info(f"Auto-switched to preset '{target_preset}' based on focus window '{window_title}'")
    
    def _is_string_match(self, target_string, pattern, match_type):
        """文字列の一致判定（統一版）"""
        if not target_string or not pattern:
            return False
        
        target_string = target_string.lower()
        pattern = pattern.lower()
        
        if match_type == "exact":
            return target_string == pattern
        else:  # partial
            return pattern in target_string
    
    def _is_window_name_match(self, window_title, target_name, match_type):
        """ウィンドウ名の一致判定（互換性維持用）"""
        return self._is_string_match(window_title, target_name, match_type)
    
    def _check_app_preset_binding(self, app_name):
        """アプリとプリセットのバインディングをチェック（旧版、互換性用）"""
        for preset_name, preset in self.presets.items():
            app_binding = preset.get("appBinding")
            if isinstance(app_binding, str) and app_binding and app_binding.lower() in app_name.lower():
                if preset_name != self.current_preset:
                    self.window.after(0, self._switch_to_preset, preset_name)
                break
    
    def _switch_to_preset(self, preset_name):
        """プリセットの切り替え（アプリ連動用）"""
        self.current_preset = preset_name
        self.preset_combobox.set(preset_name)
        
        # アプリ連動の場合のみ自動適用（通常の選択では適用しない）
        if hasattr(self, 'app_monitoring_var') and self.app_monitoring_var.get():
            self._load_current_preset()
            # フローティングキーボードを更新
            if self.update_callback:
                self._apply_preset_to_config()
                self.update_callback()
            logger.info(f"Auto-switched to preset: {preset_name}")
        else:
            logger.info(f"Preset selection changed to: {preset_name} (not auto-loading)")
    
    # [続く - 他のメソッドの実装]
    
    def _on_preset_selection(self, selected_preset):
        """プリセット選択時の処理（ドロップダウンから選択された場合）"""
        if self._editing_preset_name:
            # 編集モード中の場合は無視
            return
            
        if selected_preset != self.current_preset:
            logger.info(f"Preset selection changed from {self.current_preset} to {selected_preset} (not loading automatically)")
            self.current_preset = selected_preset
            logger.info(f"Current preset selection updated: {self.current_preset}")
            # 自動読み込みを無効化
            # self._load_current_preset()  # コメントアウト
            # self._apply_preset_to_config()  # コメントアウト
            # self._refresh_floating_window()  # コメントアウト
    
    def _on_preset_name_edited(self, event=None):
        """プリセット名編集完了時の処理"""
        self._editing_preset_name = True
        
        current_value = self.preset_combobox.get().strip()
        
        # 既存のプリセット名から選択された場合（プリセット選択のみ）
        if current_value in self.presets and current_value != self.current_preset:
            self.current_preset = current_value
            logger.info(f"Preset selection updated to: {current_value} (not loading automatically)")
            # 自動読み込みを無効化
            # self._load_current_preset()  # コメントアウト
            # self._apply_preset_to_config()  # コメントアウト
            # self._refresh_floating_window()  # コメントアウト
            self._editing_preset_name = False
            return
        
        # 名前が変更されていない場合は何もしない
        if not current_value or current_value == self.current_preset:
            self.preset_combobox.set(self.current_preset)
            self._editing_preset_name = False
            return
        
        # 名前変更処理
        self._rename_current_preset(current_value)
        self._editing_preset_name = False
    
    def _rename_current_preset(self, new_name):
        """現在のプリセットの名前を変更"""
        # defaultプリセットの名前変更は禁止
        if self.current_preset == "default":
            messagebox.showwarning("警告", "defaultプリセットの名前は変更できません")
            self.preset_combobox.set(self.current_preset)
            return
        
        # 同名のプリセットが既に存在するかチェック
        if new_name in self.presets:
            messagebox.showerror("エラー", f"プリセット名 '{new_name}' は既に存在します")
            self.preset_combobox.set(self.current_preset)
            return
        
        try:
            # プリセット名を変更
            old_name = self.current_preset
            preset_data = self.presets[old_name].copy()
            preset_data["name"] = new_name
            preset_data["modified"] = datetime.now().isoformat()
            
            # 古いプリセットを削除
            del self.presets[old_name]
            
            # 古いファイルを削除
            old_file_path = os.path.join("presets", f"{old_name}.json")
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            # 新しいプリセットを追加
            self.presets[new_name] = preset_data
            self._save_preset(new_name)
            
            # 現在のプリセットを更新
            self.current_preset = new_name
            self._update_preset_combobox()
            self.preset_combobox.set(new_name)
            
            self._show_status(f"プリセット名を '{old_name}' から '{new_name}' に変更しました")
            logger.info(f"Preset renamed: {old_name} -> {new_name}")
            
        except Exception as e:
            logger.error(f"Failed to rename preset: {e}")
            messagebox.showerror("エラー", f"プリセット名の変更に失敗しました: {str(e)}")
            self.preset_combobox.set(self.current_preset)
    
    def _create_new_preset(self):
        """新規プリセット作成"""
        dialog = PresetNameDialog(self.window, "新規プリセット作成")
        name, description = dialog.get_result()
        
        if name:
            if name in self.presets:
                messagebox.showerror("エラー", "同名のプリセットが既に存在します")
                return
            
            # 空の新しいプリセットを作成（複製とは異なり、ボタンは空で開始）
            new_preset = {
                "name": name,
                "description": description,
                "buttons": [],  # 空のボタンリスト
                "settings": {
                    "layoutDirection": "horizontal",
                    "buttonsPerRow": 12,
                    "iconSize": 32,
                    "darkMode": False,
                    "showTitlebar": False
                },
                "appBinding": None,
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            }
            
            self.presets[name] = new_preset
            self._save_preset(name)
            self._update_preset_combobox()
            self.preset_combobox.set(name)
            self.current_preset = name
            logger.info(f"New preset created: {name}, current_preset: {self.current_preset}")
            logger.info(f"Preset combobox value: {self.preset_combobox.get()}")
            logger.info(f"New preset buttons count: {len(new_preset.get('buttons', []))}")
            self._load_current_preset()  # リスト表示を更新
            self._apply_preset_to_config()  # フローティングパネルにも反映
            self._refresh_floating_window()  # フローティングウィンドウを更新
            self._show_status(f"プリセット '{name}' を作成しました")
    
    def _duplicate_preset(self):
        """プリセット複製"""
        if not self.current_preset:
            return
        
        dialog = PresetNameDialog(
            self.window, 
            "プリセット複製",
            f"{self.current_preset}_copy",
            f"{self.presets[self.current_preset].get('description', '')} (複製)"
        )
        name, description = dialog.get_result()
        
        if name:
            if name in self.presets:
                messagebox.showerror("エラー", "同名のプリセットが既に存在します")
                return
            
            # 現在のプリセットを複製
            original = self.presets[self.current_preset]
            new_preset = copy.deepcopy(original)
            new_preset["name"] = name
            new_preset["description"] = description
            new_preset["created"] = datetime.now().isoformat()
            new_preset["modified"] = datetime.now().isoformat()
            
            self.presets[name] = new_preset
            self._save_preset(name)
            self._update_preset_combobox()
            self.preset_combobox.set(name)
            self.current_preset = name
            self._load_current_preset()  # リスト表示を更新
            self._apply_preset_to_config()  # フローティングパネルにも反映
            self._refresh_floating_window()  # フローティングウィンドウを更新
            self._show_status(f"プリセット '{name}' を複製しました")
    
    def _delete_preset(self):
        """プリセット削除"""
        if self.current_preset == "default":
            messagebox.showwarning("警告", "デフォルトプリセットは削除できません")
            return
        
        if messagebox.askyesno("確認", f"プリセット '{self.current_preset}' を削除しますか？"):
            # ファイル削除
            preset_file = f"presets/{self.current_preset}.json"
            if os.path.exists(preset_file):
                os.remove(preset_file)
            
            del self.presets[self.current_preset]
            self.current_preset = "default"
            self.preset_combobox.set("default")
            self._update_preset_combobox()
            self._load_current_preset()
            self._show_status("プリセットを削除しました")
    
    def _export_preset(self):
        """プリセットのエクスポート"""
        logger.info(f"Export button clicked. Current preset: {self.current_preset}")
        if not self.current_preset:
            logger.warning("Export failed: No current preset selected")
            messagebox.showwarning("警告", "エクスポートするプリセットが選択されていません")
            return
        
        try:
            logger.info("Opening file save dialog...")
            file_path = filedialog.asksaveasfilename(
                parent=self.window,  # 親ウィンドウを明示的に指定
                title="プリセットをエクスポート",
                filetypes=[("JSON files", "*.json")],
                defaultextension=".json",
                initialfile=f"{self.current_preset}.json"
            )
            logger.info(f"File save dialog result: {file_path}")
        except Exception as e:
            logger.error(f"File save dialog error: {e}")
            messagebox.showerror("エラー", f"ファイル選択ダイアログでエラーが発生しました: {e}")
            return
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.presets[self.current_preset], f, indent=2, ensure_ascii=False)
                
                self._show_status(f"プリセットを {file_path} にエクスポートしました")
                logger.info(f"Preset exported to: {file_path}")
                
            except Exception as e:
                messagebox.showerror("エラー", f"エクスポートに失敗しました: {e}")
                logger.error(f"Export failed: {e}")
    
    def _import_preset(self):
        """プリセットのインポート"""
        try:
            logger.info("Opening file open dialog...")
            file_path = filedialog.askopenfilename(
                parent=self.window,
                title="プリセットをインポート",
                filetypes=[("JSON files", "*.json")]
            )
            logger.info(f"File open dialog result: {file_path}")
        except Exception as e:
            logger.error(f"File open dialog error: {e}")
            messagebox.showerror("エラー", f"ファイル選択ダイアログでエラーが発生しました: {e}")
            return
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)
                
                # エクスポート形式かプリセット形式かを判定
                if "exportType" in imported_data and "floatingKeypadSettings" in imported_data:
                    # エクスポート形式の場合、プリセット形式に変換
                    floating_settings = imported_data["floatingKeypadSettings"]
                    layout_settings = floating_settings.get("layout", {})
                    preset_data = {
                        "name": "imported_preset",
                        "description": f"インポート ({imported_data.get('exportedAt', 'unknown')})",
                        "buttons": floating_settings.get("buttons", []),
                        "settings": {
                            "layoutDirection": floating_settings.get("layoutDirection", "horizontal"),
                            "buttonsPerRow": layout_settings.get("buttonsPerRow", 12),
                            "iconSize": layout_settings.get("iconSize", 32),
                            "darkMode": floating_settings.get("darkMode", False),
                            "showTitlebar": floating_settings.get("showTitlebar", False)
                        },
                        "appBinding": None,
                        "created": datetime.now().isoformat(),
                        "modified": datetime.now().isoformat()
                    }
                    logger.info("Converted export format to preset format")
                else:
                    # 既存のプリセット形式
                    preset_data = imported_data
                
                preset_name = preset_data.get("name", "imported_preset")
                
                # 同名のプリセットが存在する場合の処理
                if preset_name in self.presets:
                    result = messagebox.askyesnocancel(
                        "確認",
                        f"プリセット '{preset_name}' は既に存在します。\n\n"
                        "はい: 上書きする\n"
                        "いいえ: 別名で保存\n"
                        "キャンセル: インポートを中止"
                    )
                    
                    if result is None:  # キャンセル
                        return
                    elif result is False:  # 別名で保存
                        counter = 1
                        original_name = preset_name
                        while f"{original_name}_{counter}" in self.presets:
                            counter += 1
                        preset_name = f"{original_name}_{counter}"
                        preset_data["name"] = preset_name
                
                # プリセットを追加
                preset_data["modified"] = datetime.now().isoformat()
                self.presets[preset_name] = preset_data
                self._save_preset(preset_name)
                self._update_preset_combobox()
                
                # インポートしたプリセットに切り替え
                self.preset_combobox.set(preset_name)
                self.current_preset = preset_name
                self._load_current_preset()
                self._apply_preset_to_config()  # フローティングパネルにも反映
                self._refresh_floating_window()  # フローティングウィンドウを更新
                
                self._show_status(f"プリセット '{preset_name}' をインポートしました ({len(preset_data.get('buttons', []))}個のボタン)")
                logger.info(f"Preset imported: {preset_name}")
                
            except Exception as e:
                messagebox.showerror("エラー", f"インポートに失敗しました: {e}")
                logger.error(f"Import failed: {e}")
    
    def _save_preset(self, preset_name):
        """プリセットをファイルに保存"""
        try:
            preset_dir = "presets"
            if not os.path.exists(preset_dir):
                os.makedirs(preset_dir)
            
            file_path = os.path.join(preset_dir, f"{preset_name}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.presets[preset_name], f, indent=2, ensure_ascii=False)
            
            logger.info(f"Preset saved: {preset_name}")
            
        except Exception as e:
            logger.error(f"Failed to save preset {preset_name}: {e}")
    
    def _apply_preset_to_config(self):
        """現在のプリセットを設定に適用"""
        if self.current_preset not in self.presets:
            return
        
        preset = self.presets[self.current_preset]
        config = self.config_manager.config
        
        # フローティングウィンドウ設定を更新
        if "floatingWindow" not in config:
            config["floatingWindow"] = {}
        
        config["floatingWindow"]["buttons"] = preset.get("buttons", [])
        
        # プリセット設定を適用（すべてのレイアウト設定を含む）
        preset_settings = preset.get("settings", {})
        
        # layoutDirectionを適用
        if "layoutDirection" in preset_settings:
            config["floatingWindow"]["layoutDirection"] = preset_settings["layoutDirection"]
        
        # ボタンレイアウト設定を適用
        if "layout" not in config["floatingWindow"]:
            config["floatingWindow"]["layout"] = {}
        
        layout_config = config["floatingWindow"]["layout"]
        if "buttonsPerRow" in preset_settings:
            layout_config["buttonsPerRow"] = preset_settings["buttonsPerRow"]
        if "iconSize" in preset_settings:
            layout_config["iconSize"] = preset_settings["iconSize"]
        
        # その他の表示設定を適用
        # ダークモードはプリセット固有の設定を適用
        if "darkMode" in preset_settings:
            config["floatingWindow"]["darkMode"] = preset_settings["darkMode"]
            
        if "showTitlebar" in preset_settings:
            config["floatingWindow"]["showTitlebar"] = preset_settings["showTitlebar"]
        
        # 設定を保存
        self.config_manager.save_config()
        logger.info(f"Applied preset {self.current_preset} to config")
    
    def _refresh_floating_window(self):
        """フローティングウィンドウを更新"""
        if self.update_callback:
            try:
                logger.info("Attempting to refresh floating window...")
                self.update_callback()
                logger.info("Floating window refreshed via callback")
            except Exception as e:
                logger.error(f"Failed to refresh floating window: {e}")
                # 例外が発生してもプログラムを続行
        else:
            logger.debug("No update callback available for floating window refresh")
    
    # ボタン操作メソッド
    def _add_button(self):
        """ボタンの追加"""
        # 新規ボタン用のデフォルト設定
        new_button_data = {
            "label": "新規",
            "key": "F13",  # デフォルトキーを設定
            "icon": "",
            "color": "transparent",
            "description": "",
            "toggleHighlight": False,
            "highlightColor": "",
            "modifiers": {
                "ctrl": False,
                "shift": False,
                "alt": False,
                "win": False
            }
        }
        
        # フローティングウィンドウと同じButton Settingsダイアログを使用
        from virtual_keyboard.ui.button_edit_dialog import ButtonEditDialog
        
        def on_save():
            """ボタン追加時のコールバック"""
            try:
                logger.info(f"on_save called with button_data: {new_button_data}")
                
                # 入力値を検証
                key = new_button_data.get("key", "").strip()
                if not key or key == "":
                    logger.warning("Button key is empty, using default F13")
                    new_button_data["key"] = "F13"  # デフォルトキーを設定
                
                logger.info(f"Adding button with key: {new_button_data.get('key')}")
                
                # 現在のプリセットにボタンを追加
                preset = self.presets.get(self.current_preset)
                if not preset:
                    logger.error(f"Preset not found: {self.current_preset}")
                    self._show_status("プリセットが見つかりません")
                    return
                
                if "buttons" not in preset:
                    preset["buttons"] = []
                
                preset["buttons"].append(new_button_data.copy())  # コピーして安全に追加
                preset["modified"] = datetime.now().isoformat()
                
                self._save_preset(self.current_preset)
                self._populate_button_list(preset["buttons"])
                self._show_status("ボタンを追加しました")
                
                # 現在の設定に即座に反映
                self._apply_preset_to_config()
                self._refresh_floating_window()
                
            except Exception as e:
                import traceback
                logger.error(f"Error adding button: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                logger.error(f"Button data at error: {new_button_data}")
                self._show_status(f"ボタン追加エラー: {str(e)}")
                messagebox.showerror("エラー", f"ボタンの追加に失敗しました: {str(e)}\n\n詳細: {traceback.format_exc()[:200]}")
        
        # Button Settingsダイアログを開く
        dialog = ButtonEditDialog(
            self.window,
            new_button_data,
            on_save
        )
    
    def _delete_button(self):
        """選択されたボタンの削除"""
        selection = self.button_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "削除するボタンを選択してください")
            return
        
        if messagebox.askyesno("確認", "選択されたボタンを削除しますか？"):
            # 選択されたアイテムのインデックスを取得
            item = selection[0]
            # タグからインデックスを取得
            tags = self.button_tree.item(item, "tags")
            if not tags:
                return
            
            tag = tags[0]  # button_0形式
            index = int(tag.split("_")[1])  # button_0から0を抽出
            
            # プリセットからボタンを削除
            preset = self.presets[self.current_preset]
            if "buttons" in preset and 0 <= index < len(preset["buttons"]):
                del preset["buttons"][index]
                preset["modified"] = datetime.now().isoformat()
                
                self._save_preset(self.current_preset)
                self._populate_button_list(preset["buttons"])
                self._show_status("ボタンを削除しました")
                
                # 現在の設定に即座に反映
                if self.current_preset == "default":
                    self._apply_preset_to_config()
                    if self.update_callback:
                        self.update_callback()
    
    def _move_button_up(self):
        """ボタンを上に移動"""
        self._move_button(-1)
    
    def _move_button_down(self):
        """ボタンを下に移動"""
        self._move_button(1)
    
    def _move_button(self, direction):
        """ボタンの移動"""
        selection = self.button_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "移動するボタンを選択してください")
            return
        
        item = selection[0]
        # タグからインデックスを取得
        tags = self.button_tree.item(item, "tags")
        if not tags:
            return
        
        tag = tags[0]  # button_0形式
        index = int(tag.split("_")[1])  # button_0から0を抽出
        
        preset = self.presets[self.current_preset]
        buttons = preset.get("buttons", [])
        
        new_index = index + direction
        if new_index < 0 or new_index >= len(buttons):
            return  # 移動不可
        
        # ボタンを移動
        buttons[index], buttons[new_index] = buttons[new_index], buttons[index]
        preset["modified"] = datetime.now().isoformat()
        
        self._save_preset(self.current_preset)
        self._populate_button_list(buttons)
        self._show_status("ボタンを移動しました")
        
        # 現在の設定に即座に反映
        if self.current_preset == "default":
            self._apply_preset_to_config()
            if self.update_callback:
                self.update_callback()
        
        # 移動後も同じボタンを選択状態にする
        for new_item in self.button_tree.get_children():
            new_tags = self.button_tree.item(new_item, "tags")
            if new_tags:
                new_tag = new_tags[0]  # button_0形式
                new_item_index = int(new_tag.split("_")[1])  # button_0から0を抽出
                if new_item_index == new_index:
                    self.button_tree.selection_set(new_item)
                    self.button_tree.focus(new_item)
                    self.button_tree.see(new_item)  # スクロールして見えるように
                    break
    
    def _on_button_select(self, event):
        """ボタン選択時の処理"""
        # リストをクリックしたときは何もしない（ダブルクリックで編集）
        pass
    
    def _on_button_double_click(self, event):
        """ボタンダブルクリック時の処理"""
        selection = self.button_tree.selection()
        if selection:
            item = selection[0]
            # タグからインデックスを取得（button_0, button_1など）
            tags = self.button_tree.item(item, "tags")
            if tags:
                tag = tags[0]  # button_0形式
                index = int(tag.split("_")[1])  # button_0から0を抽出
                
                preset = self.presets[self.current_preset]
                buttons = preset.get("buttons", [])
                
                if 0 <= index < len(buttons):
                    button_data = buttons[index]
                    
                    # フローティングウィンドウと同じButton Settingsダイアログを使用
                    from virtual_keyboard.ui.button_edit_dialog import ButtonEditDialog
                
                    def on_save():
                        """ボタン設定保存時のコールバック"""
                        # プリセットを更新
                        preset["modified"] = datetime.now().isoformat()
                        self._save_preset(self.current_preset)
                        self._populate_button_list(buttons)
                        self._show_status("ボタンを更新しました")
                        
                        # 現在の設定に即座に反映
                        if self.current_preset == "default":
                            self._apply_preset_to_config()
                            if self.update_callback:
                                self.update_callback()
                    
                    # Button Settingsダイアログを開く
                    dialog = ButtonEditDialog(
                        self.window,
                        button_data,
                        on_save
                    )
    
    
    def _show_status(self, message):
        """ステータス表示"""
        self.status_label.configure(text=message)
        logger.info(f"Status: {message}")
    
    def _load_layout_settings(self):
        """現在のプリセットからレイアウト設定を読み込み"""
        if self.current_preset not in self.presets:
            return
        
        preset = self.presets[self.current_preset]
        settings = preset.get("settings", {})
        
        # 現在のconfig.jsonから設定を取得（プリセットに設定がない場合のフォールバック）
        config = self.config_manager.config
        floating_config = config.get("floatingWindow", {})
        layout_config = floating_config.get("layout", {})
        
        # レイアウト方向
        self.layout_direction_var.set(settings.get("layoutDirection", floating_config.get("layoutDirection", "horizontal")))
        
        # ボタンレイアウト設定
        buttons_per_row = settings.get("buttonsPerRow", layout_config.get("buttonsPerRow", 12))
        self.buttons_per_row_var.set(buttons_per_row)
        self.buttons_per_row_entry.delete(0, tk.END)
        self.buttons_per_row_entry.insert(0, str(buttons_per_row))
        
        # アイコンサイズ
        icon_size = settings.get("iconSize", layout_config.get("iconSize", 32))
        self.icon_size_var.set(icon_size)
        self.icon_size_entry.delete(0, tk.END)
        self.icon_size_entry.insert(0, str(icon_size))
        
        # ダークモードはプリセット固有の設定を読み込み
        dark_mode_value = settings.get("darkMode", floating_config.get("darkMode", False))
        self.dark_mode_var.set(dark_mode_value)
        
        # その他の表示設定
        self.show_titlebar_var.set(settings.get("showTitlebar", floating_config.get("showTitlebar", False)))
        
        # アプリ連動設定の読み込み
        app_binding = preset.get("appBinding", {})
        if hasattr(self, 'app_binding_enabled_var'):
            if isinstance(app_binding, dict):
                self.app_binding_enabled_var.set(app_binding.get("enabled", False))
                self.app_window_name_var.set(app_binding.get("windowName", ""))
                self.app_match_type_var.set(app_binding.get("matchType", "partial"))
                if hasattr(self, 'app_match_target_var'):
                    self.app_match_target_var.set(app_binding.get("matchTarget", "windowTitle"))
                self.app_priority_var.set(app_binding.get("priority", 1))
                
                # 優先度ラベルを更新
                if hasattr(self, 'priority_label'):
                    self.priority_label.configure(text=str(app_binding.get("priority", 1)))
            else:
                # 古い形式のappBinding (文字列) の場合
                self.app_binding_enabled_var.set(bool(app_binding))
                self.app_window_name_var.set(str(app_binding) if app_binding else "")
                self.app_match_type_var.set("partial")
                self.app_priority_var.set(1)
                if hasattr(self, 'priority_label'):
                    self.priority_label.configure(text="1")
        
        print(f"[DEBUG] Loaded settings for preset '{self.current_preset}': darkMode={self.dark_mode_var.get()} (from preset)")
        
        # ダークモード設定を即座に反映
        self._update_floating_keyboard_directly()
        
        # 現在の復帰ウィンドウ名を表示
        self._update_current_focus_window_display()
        
        # プリセットに不足している設定を追加・保存（一度だけ実行）
        self._ensure_preset_has_all_settings()
    
    def _load_app_binding_settings(self):
        """アプリ連動設定を読み込み"""
        if self.current_preset not in self.presets:
            return
        
        preset = self.presets[self.current_preset]
        
        # アプリ連動設定の読み込み
        app_binding = preset.get("appBinding", {})
        if hasattr(self, 'app_binding_enabled_var'):
            if isinstance(app_binding, dict):
                self.app_binding_enabled_var.set(app_binding.get("enabled", False))
                self.app_window_name_var.set(app_binding.get("windowName", ""))
                self.app_match_type_var.set(app_binding.get("matchType", "partial"))
                if hasattr(self, 'app_match_target_var'):
                    self.app_match_target_var.set(app_binding.get("matchTarget", "windowTitle"))
                self.app_priority_var.set(app_binding.get("priority", 1))
                
                # 優先度ラベルを更新
                if hasattr(self, 'priority_label'):
                    self.priority_label.configure(text=str(app_binding.get("priority", 1)))
            else:
                # 古い形式のappBinding (文字列) の場合
                self.app_binding_enabled_var.set(bool(app_binding))
                self.app_window_name_var.set(str(app_binding) if app_binding else "")
                self.app_match_type_var.set("partial")
                if hasattr(self, 'app_match_target_var'):
                    self.app_match_target_var.set("windowTitle")
                self.app_priority_var.set(1)
                if hasattr(self, 'priority_label'):
                    self.priority_label.configure(text="1")
        
        # 監視状態を更新
        self._update_monitoring_status()
        
        # 現在の復帰ウィンドウ名を表示
        self._update_current_focus_window_display()
    
    def _update_monitoring_status(self):
        """監視状態表示を更新"""
        if hasattr(self, 'monitoring_status_label'):
            if hasattr(self, 'monitoring_active') and self.monitoring_active:
                self.monitoring_status_label.configure(text="監視中", text_color="green")
            else:
                self.monitoring_status_label.configure(text="停止中", text_color="gray")

    def _ensure_preset_has_all_settings(self):
        """プリセットに必要な全ての設定項目があることを確認し、不足分を追加"""
        if self.current_preset not in self.presets:
            return
            
        preset = self.presets[self.current_preset]
        settings = preset.setdefault("settings", {})
        
        # 現在のconfig.jsonから設定を取得
        config = self.config_manager.config
        floating_config = config.get("floatingWindow", {})
        layout_config = floating_config.get("layout", {})
        
        # 必要な設定項目とデフォルト値
        required_settings = {
            "layoutDirection": floating_config.get("layoutDirection", "horizontal"),
            "buttonsPerRow": layout_config.get("buttonsPerRow", 12),
            "iconSize": layout_config.get("iconSize", 32),
            "darkMode": floating_config.get("darkMode", False),
            "showTitlebar": floating_config.get("showTitlebar", False)
        }
        
        # 不足している設定を追加
        updated = False
        for key, default_value in required_settings.items():
            if key not in settings:
                settings[key] = default_value
                updated = True
                print(f"[DEBUG] Added missing setting to preset '{self.current_preset}': {key}={default_value}")
        
        # アプリ連動設定のデフォルト値確保
        if "appBinding" not in preset or not isinstance(preset["appBinding"], dict):
            preset["appBinding"] = {
                "enabled": False,
                "windowName": "",
                "matchTarget": "windowTitle",
                "matchType": "partial",
                "priority": 1
            }
            updated = True
            print(f"[DEBUG] Added missing app binding settings to preset '{self.current_preset}'")
        
        # 更新があった場合のみ保存
        if updated:
            preset["modified"] = datetime.now().isoformat()
            self._save_preset(self.current_preset)

    def _on_layout_setting_changed(self, *args):
        """レイアウト設定変更時のイベントハンドラー"""
        try:
            # デバッグメッセージを追加（最初に出力）
            print(f"[DEBUG] _on_layout_setting_changed called - dark mode: {self.dark_mode_var.get()}, args: {args}")
            
            # エントリーフィールドを更新（エントリーフィールドが存在する場合のみ）
            if hasattr(self, 'buttons_per_row_entry'):
                self.buttons_per_row_entry.delete(0, tk.END)
                self.buttons_per_row_entry.insert(0, str(int(self.buttons_per_row_var.get())))
            
            if hasattr(self, 'icon_size_entry'):
                self.icon_size_entry.delete(0, tk.END)
                self.icon_size_entry.insert(0, str(int(self.icon_size_var.get())))
            
            # プリセットに設定を保存
            self._save_layout_settings_to_preset()
            
            print(f"[DEBUG] Layout setting saved to preset - dark mode: {self.dark_mode_var.get()}")
            
        except Exception as e:
            print(f"[ERROR] Layout setting change error: {e}")
            import traceback
            traceback.print_exc()
            # エラーが発生してもプリセット保存は実行
            self._save_layout_settings_to_preset()
    
    def _on_app_binding_setting_changed(self, *args):
        """アプリ連動設定変更時のイベントハンドラー"""
        try:
            # 優先度ラベルを更新
            if hasattr(self, 'priority_label'):
                self.priority_label.configure(text=str(int(self.app_priority_var.get())))
            
            # プリセットに設定を保存
            self._save_layout_settings_to_preset()
            
            print(f"[DEBUG] App binding setting saved: enabled={self.app_binding_enabled_var.get()}, window={self.app_window_name_var.get()}")
            
        except Exception as e:
            print(f"[ERROR] App binding setting change error: {e}")
            logger.error(f"App binding setting change error: {e}")
    
    def _on_select_window(self):
        """ウィンドウ選択ボタン押下時"""
        try:
            from virtual_keyboard.ui.window_selector import show_window_selector
            
            selected_window = show_window_selector(self.window)
            
            if selected_window:
                # 選択されたウィンドウの情報を設定
                match_target = self.app_match_target_var.get()
                
                if match_target == "windowTitle":
                    value = selected_window.title
                elif match_target == "processName":
                    value = selected_window.process_name
                elif match_target == "className":
                    value = selected_window.class_name
                else:
                    value = selected_window.title  # デフォルト
                
                self.app_window_name_var.set(value)
                
                # 設定を保存
                self._on_app_binding_setting_changed()
                
                self._show_status(f"選択されたウィンドウ: {selected_window.process_name} - {selected_window.title}")
                logger.info(f"Window selected: {selected_window.process_name} - {selected_window.title}")
                print(f"[DEBUG] Window selected - Process: {selected_window.process_name}, Title: {selected_window.title}, Class: {selected_window.class_name}, Target: {match_target}, Value: {value}")
        
        except Exception as e:
            print(f"[ERROR] Window selection error: {e}")
            logger.error(f"Window selection error: {e}")
            import tkinter.messagebox as messagebox
            messagebox.showerror("エラー", f"ウィンドウ選択でエラーが発生しました: {e}")
        
    def _on_entry_changed(self, event):
        """エントリーフィールド変更時のハンドラー"""
        try:
            if event.widget == self.buttons_per_row_entry:
                value = int(self.buttons_per_row_entry.get())
                if 1 <= value <= 20:
                    self.buttons_per_row_var.set(value)
                    self._save_layout_settings_to_preset()
                else:
                    # 範囲外の場合は元の値に戻す
                    self.buttons_per_row_entry.delete(0, tk.END)
                    self.buttons_per_row_entry.insert(0, str(int(self.buttons_per_row_var.get())))
            
            elif event.widget == self.icon_size_entry:
                value = int(self.icon_size_entry.get())
                if 16 <= value <= 64:
                    self.icon_size_var.set(value)
                    self._save_layout_settings_to_preset()
                else:
                    # 範囲外の場合は元の値に戻す
                    self.icon_size_entry.delete(0, tk.END)
                    self.icon_size_entry.insert(0, str(int(self.icon_size_var.get())))
        
        except ValueError:
            # 数値以外が入力された場合は元の値に戻す
            if event.widget == self.buttons_per_row_entry:
                self.buttons_per_row_entry.delete(0, tk.END)
                self.buttons_per_row_entry.insert(0, str(int(self.buttons_per_row_var.get())))
            elif event.widget == self.icon_size_entry:
                self.icon_size_entry.delete(0, tk.END)
                self.icon_size_entry.insert(0, str(int(self.icon_size_var.get())))

    def _save_layout_settings_to_preset(self):
        """現在のレイアウト設定をプリセットに保存"""
        if self.current_preset not in self.presets:
            return
        
        preset = self.presets[self.current_preset]
        settings = preset.setdefault("settings", {})
        
        # 設定値を更新
        settings["layoutDirection"] = self.layout_direction_var.get()
        settings["buttonsPerRow"] = int(self.buttons_per_row_var.get())
        settings["iconSize"] = int(self.icon_size_var.get())
        settings["darkMode"] = self.dark_mode_var.get()
        settings["showTitlebar"] = self.show_titlebar_var.get()
        
        # アプリ連動設定を更新
        if hasattr(self, 'app_binding_enabled_var'):
            app_binding = {
                "enabled": self.app_binding_enabled_var.get(),
                "windowName": self.app_window_name_var.get(),
                "matchTarget": self.app_match_target_var.get() if hasattr(self, 'app_match_target_var') else "windowTitle",
                "matchType": self.app_match_type_var.get(),
                "priority": int(self.app_priority_var.get())
            }
            preset["appBinding"] = app_binding
        
        # 修正日時を更新
        preset["modified"] = datetime.now().isoformat()
        
        # プリセットファイルに保存
        self._save_preset(self.current_preset)
        
        # プリセット関係なく即座に設定に反映（特にダークモードなど表示設定）
        self._apply_preset_to_config()
        
        # 設定ウィンドウと同じ方法で、直接フローティングウィンドウを更新
        self._update_floating_keyboard_directly()
        
        if self.update_callback:
            # update_callbackはフローティングウィンドウの再作成を行うので、
            # ダークモード設定も反映される
            self.update_callback()
            print(f"[DEBUG] Called update_callback for dark mode: {self.dark_mode_var.get()}")

    def _update_floating_keyboard_directly(self):
        """設定ウィンドウと同じ方法で、直接フローティングウィンドウのダークモードを更新"""
        try:
            import gc
            from virtual_keyboard.ui.floating import FloatingKeyboard
            
            # フローティングウィンドウオブジェクトを検索
            for obj in gc.get_objects():
                if isinstance(obj, FloatingKeyboard) and hasattr(obj, 'window') and obj.window:
                    try:
                        # ダークテーマ設定を即座反映（設定ウィンドウと同じロジック）
                        if hasattr(obj, 'dark_mode'):
                            obj.dark_mode = self.dark_mode_var.get()
                            if obj.dark_mode and hasattr(obj, 'apply_dark_mode'):
                                obj.apply_dark_mode()
                            elif not obj.dark_mode and hasattr(obj, 'apply_light_mode'):
                                obj.apply_light_mode()
                            
                            print(f"[DEBUG] Directly updated floating keyboard dark mode: {self.dark_mode_var.get()}")
                        
                        # レイアウト更新
                        if hasattr(obj, 'create_buttons'):
                            obj.create_buttons()
                            
                    except Exception as e:
                        print(f"[DEBUG] Failed to update floating keyboard object: {e}")
                        
        except Exception as e:
            print(f"[DEBUG] Failed to find floating keyboard: {e}")
    
    def _sync_with_current_config(self):
        """現在の設定と同期"""
        try:
            # 最新の設定を読み込み
            self.config_manager.config = self.config_manager.load_config()
            config = self.config_manager.config
            
            # 現在のボタン配列を取得
            current_buttons = config.get("floatingWindow", {}).get("buttons", [])
            
            # デフォルトプリセットを現在の設定で更新
            self.presets["default"]["buttons"] = current_buttons
            self.presets["default"]["modified"] = datetime.now().isoformat()
            
            # リストを更新
            self._populate_button_list(current_buttons)
            
            logger.info(f"Synced with current config: {len(current_buttons)} buttons")
            
        except Exception as e:
            logger.error(f"Failed to sync with current config: {e}")
    
    def _on_closing(self):
        """ウィンドウ終了時の処理"""
        self._stop_app_monitoring()
        self.window.destroy()


class PresetNameDialog:
    """プリセット名入力ダイアログ"""
    
    def __init__(self, parent, title, default_name="", default_desc=""):
        self.result_name = None
        self.result_desc = None
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        
        # モーダルにする
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 中央配置
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 150
        self.dialog.geometry(f"400x300+{x}+{y}")
        
        # フォーム作成
        self._create_form(default_name, default_desc)
        
        # Enterキーでも保存
        self.dialog.bind("<Return>", lambda e: self._save())
        self.name_entry.focus()
        
        # 結果を待つ
        self.dialog.wait_window()
    
    def _create_form(self, default_name, default_desc):
        # メインフレーム
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # プリセット名
        ctk.CTkLabel(main_frame, text="プリセット名:").pack(anchor="w", pady=(10, 0))
        self.name_entry = ctk.CTkEntry(main_frame, placeholder_text="プリセット名を入力")
        self.name_entry.pack(fill="x", pady=(0, 10))
        
        if default_name:
            self.name_entry.insert(0, default_name)
        
        # 説明
        ctk.CTkLabel(main_frame, text="説明:").pack(anchor="w", pady=(10, 0))
        self.desc_entry = ctk.CTkTextbox(main_frame, height=80)
        self.desc_entry.pack(fill="x", pady=(0, 20))
        
        if default_desc:
            self.desc_entry.insert("1.0", default_desc)
        
        # ボタン
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 5))
        
        ctk.CTkButton(
            button_frame,
            text="作成",
            command=self._save,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="キャンセル",
            command=self._cancel,
            width=100
        ).pack(side="right", padx=5)
    
    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("警告", "プリセット名を入力してください")
            return
        
        self.result_name = name
        self.result_desc = self.desc_entry.get("1.0", "end").strip()
        self.dialog.destroy()
    
    def _cancel(self):
        self.dialog.destroy()
    
    def get_result(self):
        return self.result_name, self.result_desc


class NewPresetTypeDialog:
    """新規プリセット作成タイプ選択ダイアログ"""
    
    def __init__(self, parent):
        self.result = None
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("新規プリセット作成")
        self.dialog.geometry("450x380")
        self.dialog.resizable(False, False)
        
        # モーダルにする
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 中央配置
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 225
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 190
        self.dialog.geometry(f"450x380+{x}+{y}")
        
        # フォーム作成
        self._create_form()
        
        # 結果を待つ
        self.dialog.wait_window()
    
    def _create_form(self):
        # メインフレーム
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # タイトル
        ctk.CTkLabel(
            main_frame, 
            text="新規プリセットの作成方法を選択してください",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 20))
        
        # 選択肢フレーム
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(fill="x", pady=10)
        
        self.preset_type_var = tk.StringVar(value="from_config")
        
        # 現在の設定から作成
        config_option = ctk.CTkRadioButton(
            options_frame,
            text="現在のconfig.jsonから作成",
            variable=self.preset_type_var,
            value="from_config",
            font=ctk.CTkFont(size=14)
        )
        config_option.pack(anchor="w", padx=20, pady=10)
        
        config_desc = ctk.CTkLabel(
            options_frame,
            text="現在フローティングウィンドウに表示されているボタン設定を\n元に新しいプリセットを作成します。",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        config_desc.pack(anchor="w", padx=40, pady=(0, 15))
        
        # 空のプリセット作成
        empty_option = ctk.CTkRadioButton(
            options_frame,
            text="空のプリセットを作成",
            variable=self.preset_type_var,
            value="empty",
            font=ctk.CTkFont(size=14)
        )
        empty_option.pack(anchor="w", padx=20, pady=10)
        
        empty_desc = ctk.CTkLabel(
            options_frame,
            text="ボタンが設定されていない空のプリセットを作成し、\n後からボタンを追加していきます。",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        empty_desc.pack(anchor="w", padx=40, pady=(0, 10))
        
        # ボタン
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(25, 10))
        
        ctk.CTkButton(
            button_frame,
            text="次へ",
            command=self._next,
            width=100,
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=5, pady=5)
        
        ctk.CTkButton(
            button_frame,
            text="キャンセル",
            command=self._cancel,
            width=100
        ).pack(side="right", padx=5, pady=5)
    
    def _next(self):
        self.result = self.preset_type_var.get()
        self.dialog.destroy()
    
    def _cancel(self):
        self.result = None
        self.dialog.destroy()
    
    def get_result(self):
        return self.result


