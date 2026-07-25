"""
Floating Keyboard - フローティングキーボードウィンドウ
"""

import time
import logging
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import win32con
import win32gui
import os
from PIL import Image, ImageTk

from ..core.interfaces import IConfigManager, IKeySender, IFocusManager

logger = logging.getLogger(__name__)


class FloatingKeyboard:
    """フローティングキーボードウィンドウ（CustomTkinter版）"""
    
    def __init__(self, parent, config_manager: IConfigManager, key_sender: IKeySender, focus_manager: IFocusManager):
        self.parent = parent
        self.config_manager = config_manager
        self.key_sender = key_sender
        self.focus_manager = focus_manager
        self.window = None
        self.buttons = []
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_visible = False
        self.image_cache = {}  # 画像キャッシュ（キーは "path_sizeWxH" 形式）
        self._icon_cache = {}  # 処理済みアイコンの高速キャッシュ（キーは "icon_type_size" 形式）
        self.pre_drag_focus_window = None  # ドラッグ前のフォーカスウィンドウ
        
        # 設定からダークモード状態を読み込み
        config = self.config_manager.config
        self.dark_mode = config.get('floatingWindow', {}).get('darkMode', False)
        self.delay_input_mode = False  # 遅延入力モードフラグ
        self.transparent_color = '#000001'  # Windows用透明色
        self.context_menu_callback = None  # 右クリックメニューコールバック
        self.key_delay_ms = 0  # キー送信遅延時間
        self.tooltip = None  # ツールチップウィンドウ
        self.tooltip_timer = None  # ツールチップタイマー
        self.button_toggle_states = {}  # ボタンのトグル状態を管理
    
    def create_window(self):
        """フローティングウィンドウを作成"""
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.is_visible = True
            return
        
        # CustomTkinter フローティングウィンドウ
        self.window = ctk.CTkToplevel(self.parent)
        self._update_window_title()  # レイアウトに応じてタイトルを設定
        
        # アイコンを設定
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'icon.ico')
            if os.path.exists(icon_path):
                self.window.iconbitmap(icon_path)
        except Exception as e:
            logger.debug(f"Could not set icon: {e}")
        
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.85)  # 全体の透明度を上げて透けるように
        
        # Windows用の透明背景設定（角丸実現のため）
        import sys
        if sys.platform.startswith("win"):
            self.transparent_color = '#000001'
            self.window.attributes("-transparentcolor", self.transparent_color)
            self.window.configure(fg_color=self.transparent_color)
        
        # フォーカスを取らないように設定
        try:
            hwnd = self.window.winfo_id()
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style |= 0x08000000  # WS_EX_NOACTIVATE
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            
            # フローティングウィンドウIDを除外リストに追加
            self.focus_manager.add_excluded_window(hwnd)
            logger.info(f"Registered floating window {hwnd} as excluded")
        except Exception as e:
            logger.error(f"Error configuring floating window: {e}")
        
        # 位置設定とダークモード、遅延入力設定を読み込み
        config = self.config_manager.config
        if config and 'floatingWindow' in config:
            x = config['floatingWindow']['position']['x']
            y = config['floatingWindow']['position']['y']
            # ダークモード設定を読み込み
            self.dark_mode = config['floatingWindow'].get('darkMode', False)
            # 遅延入力設定を読み込み
            self.delay_input_mode = config['floatingWindow'].get('delayInputMode', False)
            delay_time = 3000  # 3秒固定
            self.set_key_delay(delay_time if self.delay_input_mode else 0)
            # ツールチップモード設定を読み込み
            self.tooltip_mode = config['floatingWindow'].get('tooltipMode', 'both')
        else:
            x, y = 100, 100
            self.dark_mode = False
            self.delay_input_mode = False
            self.set_key_delay(0)
            self.tooltip_mode = 'both'
        
        self.window.geometry(f"+{x}+{y}")
        
        # メインフレーム - 角丸実現のためのフレーム
        # 初期の背景色設定（ダークモードと遅延入力モードを考慮）
        if self.dark_mode:
            frame_color = "#404040"
        else:
            frame_color = "gray90"
            
        # bg_colorを透明色に設定（Windowsの場合）
        bg_color = self.transparent_color if sys.platform.startswith("win") else "transparent"
        
        # 遅延入力モードの場合は青い縁取りを追加
        if self.delay_input_mode:
            self.main_frame = ctk.CTkFrame(self.window, 
                                          corner_radius=5, 
                                          fg_color=frame_color,
                                          bg_color=bg_color,
                                          border_width=3,
                                          border_color="#2563eb")
        else:
            self.main_frame = ctk.CTkFrame(self.window, 
                                          corner_radius=5, 
                                          fg_color=frame_color,
                                          bg_color=bg_color)
        self.main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # タイトルバー（ドラッグ用）- レイアウトに応じて幅調整
        title_width = self._get_title_frame_width()
        if title_width:
            self.title_frame = ctk.CTkFrame(self.main_frame, height=30, width=title_width, corner_radius=10)
            self.title_frame.pack(side="top", padx=5, pady=(5, 0))
        else:
            self.title_frame = ctk.CTkFrame(self.main_frame, height=30, corner_radius=10)
            self.title_frame.pack(side="top", fill="x", padx=5, pady=(5, 0))
        self.title_frame.pack_propagate(False)
        
        # タイトルとコントロール
        # レイアウト方向に応じてタイトルを設定
        title_text = self._get_title_text()
        self.title_label = ctk.CTkLabel(self.title_frame, 
                                       text=title_text,
                                       font=ctk.CTkFont(size=12, weight="bold"))
        # レイアウトに応じてタイトルの配置を調整
        layout_direction = self._get_layout_direction()
        if layout_direction == 'vertical':
            self.title_label.pack(expand=True, padx=2, pady=5)  # 縦レイアウトは中央揃え
        else:
            self.title_label.pack(side="left", padx=10, pady=5)  # 横レイアウトは左揃え
        
        # モード切り替えボタン
        self.mode_btn = ctk.CTkButton(self.title_frame, 
                                     text="🌙",  # 月アイコン（ダークモード用）
                                     width=25, height=20,
                                     font=ctk.CTkFont(size=12, weight="bold"),
                                     fg_color="transparent",
                                     text_color=("gray70", "gray90"),
                                     hover_color=("gray80", "gray70"),
                                     command=self.toggle_mode)
        self.mode_btn.pack(side="right", padx=(0, 5), pady=5)
        
        # 閉じるボタン
        self.close_btn = ctk.CTkButton(self.title_frame, 
                                      text="✕",
                                      width=25, height=20,
                                      font=ctk.CTkFont(size=12, weight="bold"),
                                      fg_color="transparent",
                                      text_color=("gray70", "gray90"),
                                      hover_color=("gray80", "gray70"),
                                      command=self.hide_window)
        self.close_btn.pack(side="right", padx=5, pady=5)
        
        # ボタンフレーム - 透明背景（ドラッグ用のパディングを増やす）
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.pack(side="bottom", fill="both", expand=True, padx=10, pady=(5, 10))
        
        # 全体的なドラッグイベントを設定
        self.setup_global_drag_events()
        
        self.create_buttons()
        
        # 初期状態でダークモードを適用
        if self.dark_mode:
            self.apply_dark_mode()
        else:
            self.apply_light_mode()
        
        self.is_visible = True
        
        # ウィンドウ作成後、再度除外リストに追加（確実に登録するため）
        try:
            hwnd = self.window.winfo_id()
            self.focus_manager.add_excluded_window(hwnd)
            logger.info(f"Re-registered floating window {hwnd} as excluded")
        except:
            pass
        
        # ウィンドウ作成後、現在のフォーカスを記録（初期表示時）
        self.record_current_focus()
    
    def _update_window_title(self):
        """レイアウトに応じてウィンドウタイトルを更新"""
        if not hasattr(self, 'window') or not self.window:
            return
            
        try:
            config = self.config_manager.config
            layout_direction = config.get('floatingWindow', {}).get('layoutDirection', 'horizontal')
            
            if layout_direction == 'vertical':
                title = "VF"  # 縦並びの時は短縮形
            else:
                title = "Virtual Functions"  # 横並びの時は完全形
                
            self.window.title(title)
            logger.debug(f"Window title updated to: {title} (layout: {layout_direction})")
            
        except Exception as e:
            logger.error(f"Failed to update window title: {e}")
            # フォールバック
            self.window.title("Virtual Functions")
    
    def create_buttons(self):
        """ボタン作成"""
        config = self.config_manager.config
        if not config or 'floatingWindow' not in config:
            # デフォルトボタン設定
            default_buttons = [
                {"key": "F13", "label": "F13", "icon": "🔴", "color": "#dc2626"},
                {"key": "F14", "label": "F14", "icon": "🟢", "color": "#16a34a"},
                {"key": "F15", "label": "F15", "icon": "🔵", "color": "#2563eb"},
                {"key": "F16", "label": "F16", "icon": "🟡", "color": "#ca8a04"},
                {"key": "F17", "label": "F17", "icon": "🟣", "color": "#9333ea"},
                {"key": "F18", "label": "F18", "icon": "🟠", "color": "#ea580c"}
            ]
            buttons = default_buttons
            display_mode = "normal"
            show_titlebar = True
        else:
            floating_config = config['floatingWindow']
            buttons = floating_config.get('buttons', [])
            display_mode = floating_config.get('displayMode', 'normal')
            show_titlebar = floating_config.get('showTitlebar', True)
        
        # 既存のボタンをクリア
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        self.buttons.clear()
        
        # タイトルバーの表示/非表示を適用
        self.apply_titlebar_setting(show_titlebar)
        
        # タイトルバーが表示されている場合のみ更新
        if show_titlebar and hasattr(self, 'title_label'):
            self.title_label.configure(text=self._get_title_text())
            # タイトルラベルの配置も更新
            layout_direction = self._get_layout_direction()
            if layout_direction == 'vertical':
                self.title_label.pack_configure(side="top", expand=True, padx=2, pady=5)
            else:
                self.title_label.pack_configure(side="left", expand=False, padx=10, pady=5)
        
        # タイトルフレームの幅を更新（表示されている場合のみ）
        if show_titlebar and hasattr(self, 'title_frame') and self.title_frame:
            try:
                title_width = self._get_title_frame_width()
                if title_width:
                    self.title_frame.configure(width=title_width)
                    self.title_frame.pack_configure(fill="none")  # 固定幅
                else:
                    self.title_frame.pack_configure(fill="x")  # 自動幅に戻す
            except Exception as e:
                # ウィンドウが破棄されている場合は無視
                logger.warning(f"Title frame update failed: {e}")
        
        if display_mode == "mini":
            # ミニバーモード：一行に全て配置
            self.create_mini_buttons(buttons)
        else:
            # ノーマルモード：グリッド配置
            self.create_normal_buttons(buttons)
        
        # ボタン作成後にタイトルを更新
        self._update_window_title()
    
    def create_normal_buttons(self, buttons):
        """ノーマルモードでボタン作成"""
        config = self.config_manager.config
        floating_config = config.get('floatingWindow', {})
        layout_direction = floating_config.get('layoutDirection', 'horizontal')
        
        # レイアウト設定を取得
        layout_config = floating_config.get('layout', {})
        buttons_per_row = layout_config.get('buttonsPerRow', 3)
        icon_size = layout_config.get('iconSize', 16)
        # ボタンサイズはアイコンサイズに基づいて計算
        button_width = max(50, icon_size + 20)
        button_height = max(40, icon_size + 15)
        
        # レイアウト方向に応じてグリッド計算を分岐
        if layout_direction == "vertical":
            # 垂直レイアウト：列→行の順で配置
            grid_columns = (len(buttons) + buttons_per_row - 1) // buttons_per_row
            grid_rows = buttons_per_row
        else:
            # 水平レイアウト：行→列の順で配置（従来通り）
            grid_columns = buttons_per_row
            grid_rows = (len(buttons) + buttons_per_row - 1) // buttons_per_row
            
        for i, btn_config in enumerate(buttons):
            if layout_direction == "vertical":
                # 垂直：列→行の順で配置
                col = i // buttons_per_row
                row = i % buttons_per_row
            else:
                # 水平：行→列の順で配置（従来通り）
                row = i // buttons_per_row
                col = i % buttons_per_row
            
            key = btn_config.get('key', f"F{13+i}")
            label = btn_config.get('label', key)
            icon = btn_config.get('icon', '🔘')
            button_color = btn_config.get('color', None)  # ボタンの個別色
            
            # 画像アイコンの処理
            processed_icon = self.process_icon(icon, size=(icon_size, icon_size))
            
            # 絵文字フォントサイズを計算（アイコンサイズの75%、最小8px）
            emoji_font_size = max(8, int(icon_size * 0.75))
            
            # ボタンの色とスタイルを決定
            btn_fg_color, btn_text_color, btn_hover_color = self.get_button_colors(button_color)
            
            # トグルハイライトが有効で、トグル状態がONの場合はハイライトカラーを使用
            toggle_highlight = btn_config.get('toggleHighlight', False)
            if toggle_highlight and self.button_toggle_states.get(key, False):
                highlight_color = btn_config.get('highlightColor', self._brighten_color(btn_fg_color, 1.3))
                btn_fg_color = highlight_color
            
            if isinstance(processed_icon, ctk.CTkImage):
                # 画像の場合
                btn = ctk.CTkButton(self.button_frame,
                                   text="",
                                   image=processed_icon,
                                   compound="center",
                                   width=button_width, height=button_height,
                                   corner_radius=10,
                                   fg_color=btn_fg_color,
                                   text_color=btn_text_color,
                                   hover_color=btn_hover_color,
                                   command=lambda k=key: self.send_key_with_focus(k))
            else:
                # テキスト（絵文字）の場合
                btn = ctk.CTkButton(self.button_frame,
                                   text=processed_icon,
                                   font=ctk.CTkFont(size=emoji_font_size, weight="bold"),
                                   width=button_width, height=button_height,
                                   corner_radius=10,
                                   anchor="center",
                                   fg_color=btn_fg_color,
                                   text_color=btn_text_color,
                                   hover_color=btn_hover_color,
                                   command=lambda k=key: self.send_key_with_focus(k))
            
            # ボタンにクリックイベントを明示的にバインド（ドラッグイベントの伝播を防ぐ）
            # CTkButtonのシンプルなコールバック設定
            btn.configure(command=lambda k=key: self._handle_button_press(k))
            
            # ドラッグ防止のための最小限イベントバインディング
            btn.bind("<B1-Motion>", lambda e: "break")  # ドラッグ動作を阻止
            
            # ツールチップ＋ハイライトイベントバインディング
            btn.bind("<Enter>", lambda e, k=key, l=label: self._on_button_enter(e, k, l))
            btn.bind("<Leave>", lambda e, k=key: self._on_button_leave(e, k))
            
            # ボタン固有の右クリックメニュー
            btn.bind("<Button-3>", lambda e, k=key, l=label: self._on_button_right_click(e, k, l))
            
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            self.buttons.append((btn, key))
        
        # グリッド設定を動的列数に対応
        for i in range(grid_columns):
            self.button_frame.grid_columnconfigure(i, weight=1)
    
    def create_mini_buttons(self, buttons):
        """ミニバーモードでボタン作成"""
        # ウィンドウサイズを調整
        self.window.overrideredirect(True)
        
        # レイアウト設定を取得（ミニモード用のサイズは小さく設定）
        config = self.config_manager.config
        floating_config = config.get('floatingWindow', {})
        layout_config = floating_config.get('layout', {})
        icon_size = layout_config.get('iconSize', 32)
        buttons_per_row = layout_config.get('buttonsPerRow', 3)
        
        # ミニモードではアイコンサイズに基づいてボタンサイズを計算し縮小
        mini_icon_size = max(12, int(icon_size * 0.5))  # アイコンを50%に縮小
        mini_width = max(20, mini_icon_size + 15)
        mini_height = max(20, mini_icon_size + 10)
        
        # レイアウト方向を取得
        layout_direction = floating_config.get('layoutDirection', 'horizontal')
        
        # レイアウト方向に応じてグリッド計算を分岐
        if layout_direction == "vertical":
            # 垂直レイアウト：列→行の順で配置
            grid_columns = (len(buttons) + buttons_per_row - 1) // buttons_per_row
            grid_rows = buttons_per_row
        else:
            # 水平レイアウト：行→列の順で配置（従来通り）
            grid_columns = buttons_per_row
            grid_rows = (len(buttons) + buttons_per_row - 1) // buttons_per_row
        
        for i, btn_config in enumerate(buttons):
            if layout_direction == "vertical":
                # 垂直：列→行の順で配置
                col = i // buttons_per_row
                row = i % buttons_per_row
            else:
                # 水平：行→列の順で配置（従来通り）
                row = i // buttons_per_row
                col = i % buttons_per_row
            
            key = btn_config.get('key', f"F{13+i}")
            icon = btn_config.get('icon', '🔘')
            button_color = btn_config.get('color', None)
            
            # 画像アイコンの処理
            processed_icon = self.process_icon(icon, size=(mini_icon_size, mini_icon_size))
            
            # ミニモード用絵文字フォントサイズを計算（ミニアイコンサイズの75%、最小6px）
            mini_emoji_font_size = max(6, int(mini_icon_size * 0.75))
            
            # ボタンの色とスタイルを決定（color 変数が未定義だった問題を修正）
            btn_fg_color, btn_text_color, btn_hover_color = self.get_button_colors(button_color)
            
            # トグルハイライトが有効で、トグル状態がONの場合はハイライトカラーを使用
            toggle_highlight = btn_config.get('toggleHighlight', False)
            if toggle_highlight and self.button_toggle_states.get(key, False):
                highlight_color = btn_config.get('highlightColor', self._brighten_color(btn_fg_color, 1.3))
                btn_fg_color = highlight_color
            
            if isinstance(processed_icon, ctk.CTkImage):
                # 画像の場合
                btn = ctk.CTkButton(self.button_frame,
                                   text="",
                                   image=processed_icon,
                                   font=ctk.CTkFont(size=10),
                                   width=mini_width, height=mini_height,
                                   corner_radius=5,
                                   fg_color=btn_fg_color,
                                   text_color=btn_text_color,
                                   hover_color=btn_hover_color,
                                   command=lambda k=key: self.send_key_with_focus(k))
            else:
                # テキスト（絵文字）の場合
                btn = ctk.CTkButton(self.button_frame,
                                   text=processed_icon,
                                   font=ctk.CTkFont(size=mini_emoji_font_size),
                                   width=mini_width, height=mini_height,
                                   corner_radius=5,
                                   anchor="center",
                                   fg_color=btn_fg_color,
                                   text_color=btn_text_color,
                                   hover_color=btn_hover_color,
                                   command=lambda k=key: self.send_key_with_focus(k))
            
            # ボタンにクリックイベントを明示的にバインド（ドラッグイベントの伝播を防ぐ）
            # CTkButtonのシンプルなコールバック設定
            btn.configure(command=lambda k=key: self._handle_button_press(k))
            
            # ドラッグ防止のための最小限イベントバインディング
            btn.bind("<B1-Motion>", lambda e: "break")  # ドラッグ動作を阻止
            
            # ツールチップイベントバインディング
            label = btn_config.get('label', key)
            btn.bind("<Enter>", lambda e, k=key, l=label: self._on_button_enter(e, k, l))
            btn.bind("<Leave>", lambda e, k=key: self._on_button_leave(e, k))
            
            # ボタン固有の右クリックメニュー
            btn.bind("<Button-3>", lambda e, k=key, l=label: self._on_button_right_click(e, k, l))
            
            # grid配置でボタン数による強制改行を実装
            btn.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
            self.buttons.append((btn, key))
        
        # グリッド設定を動的列数に対応
        for i in range(grid_columns):
            self.button_frame.grid_columnconfigure(i, weight=1)
    
    def process_icon(self, icon, size=(32, 32)):
        """アイコンを処理（画像ファイルパス対応）- 高速キャッシュ付き"""
        # 高速キャッシュをまず確認
        cache_key = f"{icon}_{size[0]}x{size[1]}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        processed_icon = None
        
        if icon.startswith("file://"):
            # 画像ファイルの場合、PILで読み込み
            try:
                file_path = icon.replace("file://", "")
                if os.path.exists(file_path):
                    # PILキャッシュを確認
                    pil_cache_key = f"{file_path}_{size[0]}x{size[1]}"
                    if pil_cache_key in self.image_cache:
                        processed_icon = self.image_cache[pil_cache_key]
                    else:
                        # 画像を読み込み、リサイズ
                        img = Image.open(file_path)
                        # アスペクト比を保持してリサイズ
                        img.thumbnail(size, Image.Resampling.LANCZOS)
                        
                        # 透明度対応
                        if img.mode != 'RGBA':
                            img = img.convert('RGBA')
                        
                        # CustomTkinter用のCTkImageを作成
                        processed_icon = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                        
                        # PILキャッシュに保存
                        self.image_cache[pil_cache_key] = processed_icon
                else:
                    processed_icon = "❓"
            except Exception as e:
                logger.error(f"Error loading image {icon}: {e}")
                processed_icon = "🖼️"
        else:
            # テキスト/絵文字の場合はそのまま
            processed_icon = icon
        
        # 高速キャッシュに保存
        self._icon_cache[cache_key] = processed_icon
        return processed_icon
    
    def clear_icon_cache(self):
        """アイコンキャッシュをクリア"""
        self._icon_cache.clear()
        logger.info("Icon cache cleared")
    
    def setup_global_drag_events(self):
        """全体的なドラッグイベントを設定"""
        # ウィンドウ全体、メインフレーム、タイトルバー、ボタンフレームにドラッグイベントを設定
        draggable_widgets = [
            self.window,
            self.main_frame,
            self.title_frame,
            self.title_label,
            self.button_frame
        ]
        
        for widget in draggable_widgets:
            if widget:
                widget.bind("<Button-1>", self.start_drag)
                widget.bind("<B1-Motion>", self.on_drag)
                widget.bind("<ButtonRelease-1>", self.stop_drag)
        
        # 右クリックメニューをボタンフレームとメインフレームに設定（コールバック優先）
        if self.button_frame:
            self.button_frame.bind("<Button-3>", self._on_right_click)
        if self.main_frame:
            self.main_frame.bind("<Button-3>", self._on_right_click)
    
    def apply_titlebar_setting(self, show_titlebar):
        """タイトルバーの表示/非表示を適用"""
        if hasattr(self, 'title_frame') and self.title_frame:
            if show_titlebar:
                # タイトルバーを表示 - レイアウトに応じた設定で
                title_width = self._get_title_frame_width()
                try:
                    # まずpack_forget()で既存の配置をクリア
                    self.title_frame.pack_forget()
                    if title_width:
                        # 縦レイアウト時は固定幅でトップに配置
                        self.title_frame.pack(side="top", padx=5, pady=(5, 0))
                    else:
                        # 横レイアウト時は自動幅でトップに配置
                        self.title_frame.pack(side="top", fill="x", padx=5, pady=(5, 0))
                except Exception as e:
                    # エラー時はシンプルな設定
                    try:
                        self.title_frame.pack_forget()
                        self.title_frame.pack(side="top", padx=5, pady=(5, 0))
                    except:
                        pass
            else:
                # タイトルバーを隠す
                try:
                    self.title_frame.pack_forget()
                except Exception as e:
                    # 既に破棄されている場合は無視
                    pass
        
        # ドラッグイベントは常に全体に設定されているので、追加設定は不要
    
    def show_context_menu(self, event):
        """右クリックメニューを表示"""
        try:
            logger.warning(f"Legacy show_context_menu called from {event.widget} - should not happen!")
            # コンテキストメニューを作成
            context_menu = tk.Menu(self.window, tearoff=0)
            
            # モード切り替えメニュー
            mode_text = "ライトモード" if self.dark_mode else "ダークモード"
            context_menu.add_command(label=mode_text, command=self.toggle_mode)
            context_menu.add_separator()
            context_menu.add_command(label="閉じる", command=self.hide_window)
            
            # メニューを表示
            context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            logger.error(f"Error showing context menu: {e}")
    
    def send_key_with_focus(self, key_name: str):
        """フォーカス復帰してからキー送信"""
        focus_success = False  # 事前に初期化
        try:
            logger.info(f"=== Send key with focus: {key_name} ===")
            
            # 複数のフォーカスターゲット候補を試行（リアルタイム重視）
            target_window = None
            
            # 1. 最新のFocusManager情報を最優先で使用
            latest_focus = self.focus_manager.get_last_focus_window()
            if latest_focus and self.is_window_valid(latest_focus):
                try:
                    import win32gui
                    window_title = win32gui.GetWindowText(latest_focus)
                    is_vk_window = ("Virtual Key" in window_title or 
                                   "Virtual Keyboard" in window_title or
                                   "[VKEYPAD]" in window_title or
                                   "🎹" in window_title)
                    if not is_vk_window:
                        target_window = latest_focus
                        logger.info(f"Using latest focus manager window: {target_window} - '{window_title}'")
                        # 成功した場合はpre_drag_focus_windowも更新
                        self.pre_drag_focus_window = target_window
                    else:
                        logger.warning(f"Rejecting VK latest focus window: {latest_focus} - '{window_title}'")
                except Exception as e:
                    logger.warning(f"Error validating latest focus window {latest_focus}: {e}")
            
            # 2. FocusManagerからの取得が失敗した場合のみpre_drag_focus_windowを使用
            if not target_window and self.pre_drag_focus_window and self.is_window_valid(self.pre_drag_focus_window):
                try:
                    import win32gui
                    window_title = win32gui.GetWindowText(self.pre_drag_focus_window)
                    is_vk_window = ("Virtual Key" in window_title or 
                                   "Virtual Keyboard" in window_title or
                                   "[VKEYPAD]" in window_title or
                                   "🎹" in window_title)
                    if not is_vk_window:
                        target_window = self.pre_drag_focus_window
                        logger.info(f"Using fallback pre-drag focus window: {target_window} - '{window_title}'")
                    else:
                        logger.warning(f"Rejecting VK pre-drag window: {self.pre_drag_focus_window} - '{window_title}'")
                        self.pre_drag_focus_window = None  # Clear invalid window
                except Exception as e:
                    logger.warning(f"Error validating pre-drag window {self.pre_drag_focus_window}: {e}")
            
            if not target_window:
                if not latest_focus:
                    logger.info("No focus manager window available")
                if not self.pre_drag_focus_window:
                    logger.info("No pre_drag_focus_window available")
            
            # 3. フォーカス復帰の実行と確実な確認
            focus_success = False
            
            # 設定からタイミングパラメータを取得
            config = self.config_manager.config if self.config_manager else {}
            timing = config.get('timing', {})
            focus_wait = (timing.get('focusRestoreWait') or 100) / 1000.0  # msを秒に変換
            verify_wait = (timing.get('focusVerifyWait') or 80) / 1000.0
            max_retries = timing.get('maxFocusRetries') or 3
            retry_delay = (timing.get('retryDelay') or 50) / 1000.0
            key_delay = (timing.get('keyPressDelay') or 20) / 1000.0
            
            if target_window:
                logger.info(f"Attempting to restore focus to window: {target_window}")
                logger.info(f"Focus timing: wait={(focus_wait or 0)*1000}ms, verify={(verify_wait or 0)*1000}ms, retries={max_retries or 3}")
                
                # 設定可能な回数だけフォーカス復帰を試行
                for attempt in range(int(max_retries)):
                    success = self.focus_manager.restore_focus(target_window)
                    time.sleep(focus_wait)  # フォーカス復帰待機
                    
                    try:
                        import win32gui as wgui
                        current_focus = wgui.GetForegroundWindow()
                        attempt_num = (attempt if attempt is not None else 0) + 1
                        if current_focus == target_window:
                            logger.info(f"Focus restore SUCCESS on attempt {attempt_num}: {current_focus}")
                            focus_success = True
                            break
                        else:
                            logger.warning(f"Focus restore attempt {attempt_num} failed: Expected {target_window}, got {current_focus}")
                            if attempt < max_retries - 1:  # 最後の試行でない場合
                                time.sleep(retry_delay)  # 設定可能な遅延
                    except Exception as e:
                        logger.error(f"Error checking focus on attempt {attempt_num}: {e}")
                        
                if not focus_success:
                    logger.error(f"Focus restore FAILED after {max_retries} attempts - ABORTING key send for {key_name}")
                    return  # フォーカス復帰に失敗した場合はキー送信を中止
                    
            else:
                logger.warning("No valid target window available for focus restore - ABORTING key send")
                return  # ターゲットウィンドウがない場合はキー送信を中止
            
            # フォーカス復帰が成功した場合のみキー送信
            # キー送信前の追加待機（設定可能）
            if key_delay > 0:
                time.sleep(key_delay)
                
            logger.info(f"Focus confirmed - Sending key: {key_name} after {(key_delay or 0)*1000:.0f}ms delay")
            
            # キー送信（修飾キーの組み合わせに対応）
            if '+' in key_name and hasattr(self.key_sender, 'send_key_combination'):
                # 修飾キーの組み合わせを送信
                if self.key_sender.send_key_combination(key_name):
                    logger.info(f"Floating button: {key_name} combination sent successfully to focused window")
                else:
                    logger.error(f"Failed to send key combination: {key_name}")
            else:
                # 単一キーを送信（KeySenderの包括的なマッピングを使用）
                vk_code = self.key_sender.key_name_to_vk(key_name)
                logger.info(f"VK code for '{key_name}': {vk_code}")
                if vk_code == 0:
                    logger.error(f"Unknown key name: {key_name}")
                elif self.key_sender.send_key(vk_code):
                    logger.info(f"Floating button: {key_name} sent successfully to focused window")
                else:
                    logger.error(f"Failed to send key: {key_name}")
            
            logger.info(f"=== Send key with focus complete: {key_name} (focus_success: {focus_success}) ===")
                
        except Exception as e:
            import traceback
            logger.error(f"Error in send_key_with_focus for key '{key_name}': {e}")
            tb_lines = traceback.format_exc().split('\n')
            for line in tb_lines:
                if line.strip():
                    logger.error(f"TB: {line}")
    
    def is_window_valid(self, hwnd):
        """ウィンドウハンドルが有効かチェック"""
        try:
            return win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd)
        except:
            return False
    
    def record_current_focus(self):
        """現在のフォーカスウィンドウを記録"""
        try:
            # 少し待ってからフォーカスを記録（ウィンドウ作成完了まで）
            self.window.after(100, self._record_focus_delayed)
        except Exception as e:
            logger.error(f"Error scheduling focus record: {e}")
    
    def _record_focus_delayed(self):
        """遅延実行でフォーカスを記録"""
        try:
            current_focus = win32gui.GetForegroundWindow()
            my_window_id = self.window.winfo_id()
            main_app_id = self.parent.winfo_id()
            
            # 自分自身やメインアプリでない場合のみ記録
            if (current_focus and current_focus != my_window_id and 
                current_focus != main_app_id):
                self.pre_drag_focus_window = current_focus
                logger.info(f"Recorded current focus window: {current_focus}")
            else:
                # 現在のフォーカスが自分自身/メインアプリの場合は、FocusManagerの記録を使用
                last_focus = self.focus_manager.get_last_focus_window()
                if (last_focus and last_focus != my_window_id and 
                    last_focus != main_app_id and self.is_window_valid(last_focus)):
                    self.pre_drag_focus_window = last_focus
                    logger.info(f"Used FocusManager last window for initial record: {last_focus}")
                else:
                    logger.info("No valid focus window available for initial record")
        except Exception as e:
            logger.error(f"Error recording current focus window: {e}")
    
    def on_button_click(self, event):
        """ボタンクリック時の処理（フォーカスウィンドウ記録とイベント伝播防止）"""
        logger.debug(f"Button click event triggered at ({getattr(event, 'x_root', 'N/A')}, {getattr(event, 'y_root', 'N/A')})")
        
        # イベントが本当にボタン上でのクリックか確認
        if not self.is_button_click(event):
            logger.debug("Event not recognized as button click - ignoring")
            return
            
        try:
            # ボタンクリック時のフォーカスウィンドウ処理
            my_window_id = self.window.winfo_id()
            main_app_id = self.parent.winfo_id()
            
            # 既存のpre_drag_focus_windowが Virtual Keyboard関連でないか厳密にチェック
            current_pre_drag_valid = False
            if self.pre_drag_focus_window and self.is_window_valid(self.pre_drag_focus_window):
                if (self.pre_drag_focus_window != my_window_id and 
                    self.pre_drag_focus_window != main_app_id):
                    try:
                        import win32gui
                        window_title = win32gui.GetWindowText(self.pre_drag_focus_window)
                        is_vk_window = ("Virtual Key" in window_title or 
                                       "Virtual Keyboard" in window_title or
                                       "[VKEYPAD]" in window_title or
                                       "🎹" in window_title)
                        current_pre_drag_valid = not is_vk_window
                        if is_vk_window:
                            logger.warning(f"Button click: Clearing invalid pre-drag window: {self.pre_drag_focus_window} - '{window_title}'")
                            self.pre_drag_focus_window = None
                    except Exception as e:
                        logger.warning(f"Button click: Error checking pre-drag window: {e}")
                        current_pre_drag_valid = False
            
            if not current_pre_drag_valid:
                # ボタンクリック時は、ドラッグ時と違って現在アクティブなウィンドウは使わない
                # 代わりに、FocusManagerに記録された「最後に実際に作業していたウィンドウ」を探す
                last_focus = self.focus_manager.get_last_focus_window()
                logger.info(f"Button click: FocusManager suggests window: {last_focus}")
                
                if (last_focus and self.is_window_valid(last_focus) and
                    last_focus != my_window_id and last_focus != main_app_id):
                    # FocusManagerが返すウィンドウは既にVK以外でフィルタリング済み
                    self.pre_drag_focus_window = last_focus
                    logger.info(f"Button click: Using FocusManager window: {last_focus}")
                else:
                    logger.warning(f"Button click: Invalid FocusManager window: {last_focus}")
                
                if not self.pre_drag_focus_window:
                    logger.warning("Button click: No valid focus window available - keeping None")
            else:
                logger.info(f"Button click: Using existing valid pre-drag focus window: {self.pre_drag_focus_window}")
                
        except Exception as e:
            logger.error(f"Error recording focus window in button click: {e}")
        
        # イベントの伝播を停止し、ドラッグ動作を防ぐ
        logger.debug("Button click processing completed - stopping event propagation")
        return "break"
    
    def _handle_button_press(self, key):
        """ボタンプレスのメインハンドラー（CTkButton command用）"""
        try:
            logger.info(f"Button pressed: '{key}' - Using improved drag-like focus restore with delay")
            
            # デバッグ：ボタン設定を確認
            buttons_config = self.config_manager.config.get('floatingWindow', {}).get('buttons', [])
            for btn_config in buttons_config:
                if btn_config.get('key') == key:
                    logger.info(f"Button config found: key='{btn_config.get('key')}', modifiers={btn_config.get('modifiers', {})}")
                    break
            else:
                logger.warning(f"No config found for button key: '{key}'")
            
            # トグル機能の処理
            self._handle_toggle_highlight(key)
            
            # 遅延設定に応じてキー送信を処理
            self.handle_key_with_delay(key)
            
        except Exception as e:
            logger.error(f"Button press error for {key}: {e}")
    
    def _handle_toggle_highlight(self, key):
        """トグルハイライト機能の処理"""
        try:
            # 設定からトグルハイライトが有効かチェック
            config = self.config_manager.config
            if not config or 'floatingWindow' not in config:
                return
            
            floating_config = config['floatingWindow']
            buttons = floating_config.get('buttons', [])
            
            # 該当するボタンの設定を取得
            button_config = None
            for btn_config in buttons:
                if btn_config.get('key') == key:
                    button_config = btn_config
                    break
            
            # トグルハイライト設定がONでない場合は何もしない
            if not button_config or not button_config.get('toggleHighlight', False):
                return
            
            # トグル状態を切り替え
            current_state = self.button_toggle_states.get(key, False)
            new_state = not current_state
            self.button_toggle_states[key] = new_state
            
            # ボタンの見た目を更新
            self._update_button_appearance(key, new_state)
            
            # わずかに遅延させて強制的に色を再適用（ホバー状態との競合を防ぐ）
            self.window.after(10, lambda: self._force_color_update(key, new_state))
            
            logger.info(f"Toggle highlight for {key}: {new_state}")
            
        except Exception as e:
            logger.error(f"Error handling toggle highlight for {key}: {e}")
    
    def _update_button_appearance(self, key, toggle_state):
        """トグル状態に基づいてボタンの見た目を更新（即座反映）"""
        try:
            # 該当するボタンを検索
            target_button = None
            for button, button_key in self.buttons:
                if button_key == key:
                    target_button = button
                    break
            
            if not target_button:
                logger.warning(f"Button not found for key: {key}")
                return
            
            # 設定から色情報を取得
            config = self.config_manager.config
            if not config or 'floatingWindow' not in config:
                return
            
            buttons = config['floatingWindow'].get('buttons', [])
            button_config = None
            for btn_config in buttons:
                if btn_config.get('key') == key:
                    button_config = btn_config
                    break
            
            if not button_config:
                return
            
            # ベース色とトグル時の色を決定
            base_color = button_config.get('color', '#2563eb')
            
            # トグル状態に応じた色を即座に適用
            if toggle_state:
                # トグルON時：設定されたハイライトカラーを使用
                highlight_color = button_config.get('highlightColor', self._brighten_color(base_color, 1.3))
                target_button.configure(fg_color=highlight_color)
            else:
                # トグルOFF時：元の色
                target_button.configure(fg_color=base_color)
            
            # UIを即座に更新
            target_button.update()
            logger.debug(f"Updated button appearance for {key}, toggle: {toggle_state}")
            
        except Exception as e:
            logger.error(f"Error updating button appearance for {key}: {e}")
    
    def _force_color_update(self, key, toggle_state):
        """強制的に色を再適用（遅延実行用）"""
        try:
            # 該当するボタンを検索
            target_button = None
            for button, button_key in self.buttons:
                if button_key == key:
                    target_button = button
                    break
            
            if not target_button:
                return
            
            # 設定から色情報を取得
            config = self.config_manager.config
            if not config or 'floatingWindow' not in config:
                return
            
            buttons = config['floatingWindow'].get('buttons', [])
            button_config = None
            for btn_config in buttons:
                if btn_config.get('key') == key:
                    button_config = btn_config
                    break
            
            if not button_config or not button_config.get('toggleHighlight', False):
                return
                
            base_color = button_config.get('color', '#2563eb')
            
            # 現在マウスがボタン上にあるかチェック
            mouse_x = self.window.winfo_pointerx() - target_button.winfo_rootx()
            mouse_y = self.window.winfo_pointery() - target_button.winfo_rooty()
            is_hovering = (0 <= mouse_x <= target_button.winfo_width() and 
                          0 <= mouse_y <= target_button.winfo_height())
            
            if is_hovering:
                # ホバー時の色を計算
                if toggle_state:
                    # トグルON時: ハイライトカラーから計算
                    highlight_color = button_config.get('highlightColor', self._brighten_color(base_color, 1.3))
                    color = self._brighten_color(highlight_color, 1.2)
                else:
                    # トグルOFF時: ベースカラーから計算
                    if base_color == "transparent":
                        # 透明色の場合はget_button_colorsのホバー色を使用
                        _, _, hover_color = self.get_button_colors(base_color)
                        color = hover_color
                    else:
                        color = self._brighten_color(base_color, 1.2)
            else:
                # ホバーしていない時
                if toggle_state:
                    # トグルON: 設定されたハイライトカラーを使用
                    highlight_color = button_config.get('highlightColor', self._brighten_color(base_color, 1.3))
                    color = highlight_color
                else:
                    # トグルOFF: 通常色
                    color = base_color
            
            target_button.configure(fg_color=color)
            logger.debug(f"Force updated color for {key}, toggle: {toggle_state}, hover: {is_hovering}")
            
        except Exception as e:
            logger.error(f"Error in force color update for {key}: {e}")
    
    def _handle_button_press_original(self, key):
        """元のボタンプレスハンドラー（バックアップ用）"""
        try:
            logger.info(f"Button pressed: {key} - Using improved drag-like focus restore")
            
            # 安全なシングル試行（ウィンドウ表示問題を防ぐ）
            try:
                logger.debug(f"Button press execution for {key}")
                self._send_key_with_simple_focus_restore(key)
                logger.info(f"Button press completed for {key}")
            except Exception as attempt_error:
                logger.error(f"Button press failed for {key}: {attempt_error}")
                # シンプルなフォールバック：直接キー送信
                try:
                    vk_code = self.config_manager.key_name_to_vk(key)
                    logger.info(f"Fallback: Direct key send for {key}")
                    self.key_sender.send_key(vk_code)
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed for {key}: {fallback_error}")
                    
        except Exception as e:
            logger.error(f"Error in button press handler for {key} after all attempts: {e}")
    
    def _send_key_with_simple_focus_restore(self, key):
        """ドラッグ時のパターンを再現：Virtual Keysにフォーカスを移してから復帰"""
        try:
            logger.info(f"=== Drag-like focus pattern for key: {key} ===")
            
            # Step 1: 確実にVirtual Keysウィンドウにフォーカスを移す（複数の方法で試行）
            focus_moved = False
            my_window_id = self.window.winfo_id()
            logger.info(f"Attempting to bring Virtual Keys window to front: {my_window_id}")
            
            # 方法1: Tkinterレベルでの安全なフォーカス移動
            try:
                self.window.lift()  # ウィンドウを前面に
                self.window.focus_force()  # 強制的にフォーカスを設定
                self.window.update()  # 変更を即座反映
                focus_moved = True
                logger.debug("Tkinter level focus move: SUCCESS")
            except Exception as e:
                logger.warning(f"Tkinter focus move failed: {e}")
            
            # 方法2: Windows APIレベルでの安全なフォーカス移動
            try:
                import win32gui
                # BringWindowToTopは比較的安全
                win32gui.BringWindowToTop(my_window_id)
                focus_moved = True
                logger.debug("Windows API BringWindowToTop: SUCCESS")
                
                # SetForegroundWindowはオプショナル（失敗しても継続）
                try:
                    win32gui.SetForegroundWindow(my_window_id)
                    logger.debug("Windows API SetForegroundWindow: SUCCESS")
                except Exception as api_error:
                    logger.debug(f"SetForegroundWindow failed (this is normal): {api_error}")
                    # 失敗しても継続
                    
            except Exception as e:
                logger.warning(f"Windows API focus move failed: {e}")
            
            # 方法3: 安全な待機と状態確認
            if focus_moved:
                # FocusManagerが変更を認識する時間を与える
                time.sleep(0.06)  # 60msに短縮して安全性と速度をバランス
                logger.info("Virtual Keys window focus change completed")
            else:
                logger.warning("Focus move attempts failed - using fallback method")
                time.sleep(0.03)  # 短い待機
            
            # Step 2: ドラッグ時と同じ方法でターゲットウィンドウを取得
            target_window = self.focus_manager.get_last_focus_window()
            logger.info(f"FocusManager returned target window: {target_window} (focus_moved: {focus_moved})")
            
            if target_window and self.is_window_valid(target_window):
                try:
                    window_title = win32gui.GetWindowText(target_window)
                    # ドラッグ時と同じチェック
                    if "Virtual Key" not in window_title and "🎹" not in window_title:
                        logger.info(f"Restoring focus to: {target_window} - '{window_title}' (drag-like)")
                        # シンプルなフォーカス復帰（ドラッグ時と同じ）
                        success = self.focus_manager.restore_focus(target_window)
                        # 復帰成功時のみ短い待機
                        if success:
                            time.sleep(0.06)  # 確実なフォーカス復帰待機
                        else:
                            time.sleep(0.03)  # 失敗時は短い待機
                    else:
                        logger.info(f"Skipping VK window: {target_window} - '{window_title}'")
                        target_window = None
                except Exception as e:
                    logger.warning(f"Error getting window title, using ID check: {e}")
                    if target_window != my_window_id:
                        logger.info(f"Restoring focus to: {target_window} (no title check, drag-like)")
                        success = self.focus_manager.restore_focus(target_window)
                        if success:
                            time.sleep(0.06)
                        else:
                            time.sleep(0.03)
                    else:
                        target_window = None
            else:
                logger.warning("No valid target window for focus restore")
                target_window = None
            
            # Step 3: シンプルなキー送信
            vk_code = self.config_manager.key_name_to_vk(key)
            logger.info(f"Sending key: {key} (VK: {vk_code}) to {'target window' if target_window else 'current focus'}")
            
            # キー送信実行（修飾キーの組み合わせに対応）
            try:
                if '+' in key and hasattr(self.key_sender, 'send_key_combination'):
                    # 修飾キーの組み合わせを送信
                    if self.key_sender.send_key_combination(key):
                        logger.info(f"Key combination {key} sent successfully")
                        key_success = True
                    else:
                        logger.warning(f"Key combination send returned False for {key}")
                        key_success = False
                else:
                    # 単一キーを送信
                    if self.key_sender.send_key(vk_code):
                        logger.info(f"Key {key} sent successfully")
                        key_success = True
                    else:
                        logger.warning(f"Key send returned False for {key}")
                        key_success = False
            except Exception as key_error:
                logger.error(f"Key send failed for {key}: {key_error}")
                key_success = False
                
            logger.info(f"=== Drag-like focus pattern complete: {key} (success: {key_success if 'key_success' in locals() else 'unknown'}) ===")
            
        except Exception as e:
            logger.error(f"Error in drag-like focus restore for {key}: {e}")
    
    
    def start_drag(self, event):
        """ドラッグ開始"""
        # ボタンをクリックした場合はドラッグしない
        if self.is_button_click(event):
            logger.debug("Button click detected - preventing drag")
            # ドラッグ関連の変数をクリアして確実にドラッグを無効化
            if hasattr(self, 'drag_start_x'):
                delattr(self, 'drag_start_x')
            if hasattr(self, 'drag_start_y'):
                delattr(self, 'drag_start_y')
            return "break"  # イベント伝播を停止
        
        logger.debug(f"Starting drag at ({event.x_root}, {event.y_root})")
        
        # ドラッグ開始時は既存のpre_drag_focus_windowを保持し、FocusManagerの最新記録を使用
        try:
            my_window_id = self.window.winfo_id()
            main_app_id = self.parent.winfo_id()
            
            # 既にpre_drag_focus_windowが設定されていて有効な場合はそれを維持
            if (self.pre_drag_focus_window and self.is_window_valid(self.pre_drag_focus_window) and
                self.pre_drag_focus_window != my_window_id and 
                self.pre_drag_focus_window != main_app_id):
                logger.info(f"Keeping existing pre-drag focus window: {self.pre_drag_focus_window}")
            else:
                # 無効または未設定の場合は、FocusManagerの最後のウィンドウを使用
                last_focus = self.focus_manager.get_last_focus_window()
                
                if (last_focus and last_focus != my_window_id and 
                    last_focus != main_app_id and self.is_window_valid(last_focus)):
                    self.pre_drag_focus_window = last_focus
                    logger.info(f"Recorded pre-drag focus window from FocusManager: {last_focus}")
                else:
                    logger.info("No valid focus window available for pre-drag record")
        except Exception as e:
            logger.error(f"Error recording pre-drag focus window: {e}")
        
        self.drag_start_x = event.x_root - self.window.winfo_x()
        self.drag_start_y = event.y_root - self.window.winfo_y()
    
    def is_button_click(self, event):
        """クリックがボタン上で発生したかチェック（高速化版）"""
        try:
            # ウィジェットベースの高速チェック（最優先）
            if hasattr(event, 'widget') and event.widget:
                widget = event.widget
                # CTkButtonの直接チェック
                if isinstance(widget, ctk.CTkButton):
                    return True
                    
                # ウィジェット名でのクイックチェック
                widget_name = str(widget)
                if 'button' in widget_name.lower():
                    return True
                    
                # 親を1レベルだけチェック（高速化）
                if hasattr(widget, 'master') and widget.master:
                    parent = widget.master
                    if isinstance(parent, ctk.CTkButton):
                        return True
                    if 'button' in str(parent).lower():
                        return True
                        
            # 座標ベースのチェック（全ボタンをチェック）
            if hasattr(event, 'x_root') and hasattr(event, 'y_root') and self.buttons:
                x_root, y_root = event.x_root, event.y_root
                
                # 全ボタンをチェック（修正）
                for btn, key in self.buttons:
                    if btn and btn.winfo_exists():
                        try:
                            btn_x = btn.winfo_rootx()
                            btn_y = btn.winfo_rooty()
                            btn_w = btn.winfo_width()
                            btn_h = btn.winfo_height()
                            
                            # マージンを付けてクリックエリアを拡大
                            margin = 3
                            if (btn_x - margin <= x_root <= btn_x + btn_w + margin and
                                btn_y - margin <= y_root <= btn_y + btn_h + margin):
                                logger.debug(f"Click detected on button {key} at ({x_root}, {y_root})")
                                return True
                        except Exception as e:
                            logger.debug(f"Error checking button {key}: {e}")
                            continue
                            
            logger.debug(f"Click NOT on any button at ({x_root}, {y_root})")
            return False
            
        except Exception as e:
            logger.debug(f"Error in is_button_click: {e}")
            return False
    
    def on_drag(self, event):
        """ドラッグ中"""
        # ドラッグが開始されていない場合（ボタンクリック等）は何もしない
        if not hasattr(self, 'drag_start_x') or not hasattr(self, 'drag_start_y'):
            return
        
        # 念のため、ボタンクリックの場合は何もしない
        if self.is_button_click(event):
            return
        
        x = event.x_root - self.drag_start_x
        y = event.y_root - self.drag_start_y
        self.window.geometry(f"+{x}+{y}")
    
    def stop_drag(self, event):
        """ドラッグ終了"""
        # ドラッグが実際に開始されていた場合のみ処理
        if not hasattr(self, 'drag_start_x') or not hasattr(self, 'drag_start_y'):
            return
        
        # ボタンクリックの場合は位置保存やフォーカス復帰をしない
        if self.is_button_click(event):
            return
        
        self.save_position()
        
        # ドラッグ終了後、フローティングウィンドウ以外の最後のウィンドウにフォーカスを戻す
        try:
            target_window = self.focus_manager.get_last_focus_window()
            
            if target_window and self.is_window_valid(target_window):
                # ウィンドウタイトルをチェックして、バーチャルキーボード関連でないことを確認
                try:
                    window_title = win32gui.GetWindowText(target_window)
                    if "Virtual Key" not in window_title and "🎹" not in window_title:
                        self.focus_manager.restore_focus(target_window)
                        logger.info(f"Restored focus after drag to window: {target_window} - '{window_title}'")
                    else:
                        logger.info(f"Skipped focus restore to virtual keyboard window: {window_title}")
                except:
                    # タイトル取得に失敗した場合でも、IDで判定
                    my_window_id = self.window.winfo_id()
                    if target_window != my_window_id:
                        self.focus_manager.restore_focus(target_window)
                        logger.info(f"Restored focus after drag to window: {target_window}")
            else:
                logger.info(f"No valid target window for focus restore after drag")
        except Exception as e:
            logger.error(f"Error restoring focus after drag: {e}")
    
    def save_position(self):
        """位置を保存"""
        try:
            x = self.window.winfo_x()
            y = self.window.winfo_y()
            
            config = self.config_manager.config
            if config and 'floatingWindow' in config:
                config['floatingWindow']['position']['x'] = x
                config['floatingWindow']['position']['y'] = y
                self.config_manager.save_config()
        except Exception as e:
            logger.error(f"Failed to save floating window position: {e}")
    
    def show_window(self):
        """ウィンドウを表示"""
        # ウィンドウを表示する前に、現在のフォーカスウィンドウを記録
        try:
            current_focus = win32gui.GetForegroundWindow()
            my_window_id = getattr(self.window, 'winfo_id', lambda: 0)()
            main_app_id = self.parent.winfo_id()
            
            # 自分自身やメインアプリでない場合のみ記録
            if (current_focus and current_focus != my_window_id and 
                current_focus != main_app_id):
                self.pre_drag_focus_window = current_focus
                logger.info(f"Recorded focus window on show: {current_focus}")
            else:
                # 現在のフォーカスが自分自身/メインアプリまたは無効な場合は、FocusManagerの記録を使用
                last_focus = self.focus_manager.get_last_focus_window()
                if (last_focus and last_focus != my_window_id and 
                    last_focus != main_app_id and self.is_window_valid(last_focus)):
                    self.pre_drag_focus_window = last_focus
                    logger.info(f"Using FocusManager last window as fallback: {last_focus}")
                else:
                    logger.info("No valid focus window found for show window")
        except Exception as e:
            logger.error(f"Error recording focus window on show: {e}")
        
        if not self.window or not self.window.winfo_exists():
            self.create_window()
        else:
            self.window.deiconify()
            self.is_visible = True
            
            # 再表示時も除外リストに追加（確実に登録するため）
            try:
                hwnd = self.window.winfo_id()
                self.focus_manager.add_excluded_window(hwnd)
                logger.info(f"Re-registered showing window {hwnd} as excluded")
            except:
                pass
        
        # ウィンドウ表示後、少し待ってから追加のフォーカス記録を実行
        self.window.after(200, self._ensure_focus_target)
    
    def _ensure_focus_target(self):
        """フローティングウィンドウ表示後にフォーカスターゲットを確保"""
        try:
            # pre_drag_focus_windowがまだ設定されていない場合
            if not self.pre_drag_focus_window or not self.is_window_valid(self.pre_drag_focus_window):
                # FocusManagerの最新記録を使用
                last_focus = self.focus_manager.get_last_focus_window()
                my_window_id = self.window.winfo_id() if self.window else 0
                main_app_id = self.parent.winfo_id()
                
                if (last_focus and last_focus != my_window_id and 
                    last_focus != main_app_id and self.is_window_valid(last_focus)):
                    self.pre_drag_focus_window = last_focus
                    logger.info(f"Ensured focus target after show: {last_focus}")
                else:
                    # それでも見つからない場合は、現在のアクティブウィンドウをチェック
                    current_focus = win32gui.GetForegroundWindow()
                    if (current_focus and current_focus != my_window_id and 
                        current_focus != main_app_id and self.is_window_valid(current_focus)):
                        try:
                            window_title = win32gui.GetWindowText(current_focus)
                            # Virtual Keyboard関連でなければ記録
                            if "Virtual Key" not in window_title and "[VKEYPAD]" not in window_title:
                                self.pre_drag_focus_window = current_focus
                                logger.info(f"Set current active window as focus target: {current_focus} - '{window_title}'")
                        except:
                            # タイトル取得失敗でも、IDベースでチェック
                            if current_focus not in [my_window_id, main_app_id]:
                                self.pre_drag_focus_window = current_focus
                                logger.info(f"Set current active window as focus target: {current_focus}")
            
            # 最終的にターゲットが見つからない場合の警告
            if not self.pre_drag_focus_window or not self.is_window_valid(self.pre_drag_focus_window):
                logger.warning("No valid focus target available - buttons may require multiple clicks")
                
        except Exception as e:
            logger.error(f"Error ensuring focus target: {e}")
    
    def hide_window(self):
        """ウィンドウを隠す"""
        if self.window and self.window.winfo_exists():
            self.save_position()
            self.window.withdraw()
            self.is_visible = False
            # ウィンドウを隠すときはフォーカス記録をクリア
            self.pre_drag_focus_window = None
    
    def toggle_window(self):
        """ウィンドウ表示/非表示切り替え"""
        if self.is_visible and self.window and self.window.winfo_exists():
            self.hide_window()
        else:
            self.show_window()
    
    def destroy(self):
        """ウィンドウを破棄"""
        if self.window and self.window.winfo_exists():
            try:
                # 除外リストから削除
                hwnd = self.window.winfo_id()
                self.focus_manager.remove_excluded_window(hwnd)
                logger.info(f"Removed floating window {hwnd} from exclusion list")
            except:
                pass
            
            self.save_position()
            self.window.destroy()
        self.is_visible = False
    
    def get_button_colors(self, custom_color=None):
        """ボタンの色を取得（ダーク/ライトモード対応）"""
        # デフォルト値を設定
        if self.dark_mode:
            fg_color = "#404040"
            text_color = "white"
            hover_color = "#505050"
        else:
            fg_color = "#999999"
            text_color = "black"
            hover_color = "#e0e0e0"
        
        # カスタム色が指定されている場合
        if custom_color:
            # "default"色を適切な値に変換
            if custom_color == "default":
                custom_color = "#808080"  # グレー色に変換
                logger.debug(f"Converted 'default' color to {custom_color}")
            elif custom_color and not custom_color.startswith("#") and custom_color not in ["transparent"]:
                # 不正な色名の場合はデフォルト色に変換
                logger.warning(f"Invalid color name '{custom_color}', converting to default gray")
                custom_color = "#808080"
            
            # 透明色の場合は特別処理
            if custom_color == "transparent":
                if self.dark_mode:
                    return "transparent", "white", "gray20"
                else:
                    return "transparent", "black", "gray80"
            
            # HEX色の処理
            if custom_color.startswith("#") and len(custom_color) == 7:
                try:
                    # 元の色成分を取得
                    r = int(custom_color[1:3], 16)
                    g = int(custom_color[3:5], 16)
                    b = int(custom_color[5:7], 16)
                    
                    if self.dark_mode:
                        # ダークモードでは色を少し暗くする
                        r_dark = max(0, int(r * 0.8))
                        g_dark = max(0, int(g * 0.8))
                        b_dark = max(0, int(b * 0.8))
                        fg_color = f"#{r_dark:02x}{g_dark:02x}{b_dark:02x}"
                        
                        # ホバー色
                        r_hover = max(0, int(r * 0.9))
                        g_hover = max(0, int(g * 0.9))
                        b_hover = max(0, int(b * 0.9))
                        hover_color = f"#{r_hover:02x}{g_hover:02x}{b_hover:02x}"
                        text_color = "white"
                    else:
                        # ライトモードではカスタム色をそのまま使用
                        fg_color = custom_color
                        
                        # ホバー色（少し暗く）
                        r_hover = max(0, int(r * 0.9))
                        g_hover = max(0, int(g * 0.9))
                        b_hover = max(0, int(b * 0.9))
                        hover_color = f"#{r_hover:02x}{g_hover:02x}{b_hover:02x}"
                        text_color = "black"
                        
                except ValueError as e:
                    logger.error(f"Invalid hex color '{custom_color}': {e}")
                    # エラー時はデフォルト値を使用（既に設定済み）
        
        return fg_color, text_color, hover_color
    
    def toggle_mode(self):
        """ダーク/ライトモードを切り替え"""
        self.dark_mode = not self.dark_mode
        
        # モードボタンのアイコンを更新
        if self.dark_mode:
            self.mode_btn.configure(text="☀")  # 太陽アイコン（ライトモード用）
        else:
            self.mode_btn.configure(text="🌙")  # 月アイコン（ダークモード用）
        
        # ボタンの色を更新（ダークモード時は明るい灰色、ライトモード時は暗い灰色）
        if self.dark_mode:
            # ダークモード時：明るい灰色
            self.mode_btn.configure(text_color="gray90", hover_color="gray70")
            self.close_btn.configure(text_color="gray90", hover_color="gray70")
        else:
            # ライトモード時：暗い灰色
            self.mode_btn.configure(text_color="gray70", hover_color="gray80")
            self.close_btn.configure(text_color="gray70", hover_color="gray80")
        
        # ウィンドウとタイトルバーの背景色を更新（縁取りも考慮）
        self.update_window_border()
        self.window.attributes('-alpha', 0.85)  # 透明度を設定
        
        if self.dark_mode:
            self.title_frame.configure(fg_color="#505050")
            self.title_label.configure(text_color="white")
        else:
            self.title_frame.configure(fg_color="white")  # 白
            self.title_label.configure(text_color="#2c2c2c")  # 暗めのグレー
        
        # ボタンを再作成
        self.create_buttons()
        
        # 設定を保存して再起動時に保持
        self._save_dark_mode_setting()
        
        logger.info(f"Switched to {'dark' if self.dark_mode else 'light'} mode")
    
    def _get_title_text(self):
        """レイアウト方向に応じてタイトルテキストを取得"""
        try:
            config = self.config_manager.config
            layout_direction = config.get('floatingWindow', {}).get('layoutDirection', 'horizontal')
            
            if layout_direction == 'vertical':
                return "VF"  # 縦レイアウト時はシンプルに
            else:
                return "Virtual Functions"  # 横レイアウト時は通常表示
        except:
            return "Virtual Functions"  # デフォルト
    
    def _get_layout_direction(self):
        """現在のレイアウト方向を取得"""
        try:
            config = self.config_manager.config
            return config.get('floatingWindow', {}).get('layoutDirection', 'horizontal')
        except:
            return 'horizontal'  # デフォルト
    
    def _get_title_frame_width(self):
        """レイアウト方向に応じてタイトルフレームの幅を取得"""
        try:
            layout_direction = self._get_layout_direction()
            
            if layout_direction == 'vertical':
                return 40  # 縦レイアウト時はさらにコンパクトに（半分の幅）
            else:
                return None  # 横レイアウト時は自動幅（fill="x"）
        except:
            return None  # デフォルト
    
    def _save_dark_mode_setting(self):
        """ダークモード設定を設定ファイルに保存"""
        try:
            config = self.config_manager.config
            if not config:
                config = {}
            
            if 'floatingWindow' not in config:
                config['floatingWindow'] = {}
            
            config['floatingWindow']['darkMode'] = self.dark_mode
            
            if self.config_manager.save_config(config):
                logger.info(f"Dark mode setting saved: {self.dark_mode}")
            else:
                logger.error("Failed to save dark mode setting")
                
        except Exception as e:
            logger.error(f"Error saving dark mode setting: {e}")
    
    def apply_theme(self):
        """現在のテーマ設定を適用（ダーク/ライト）"""
        # モードボタンのアイコンを更新
        if hasattr(self, 'mode_btn'):
            if self.dark_mode:
                self.mode_btn.configure(text="☀")  # 太陽アイコン（ライトモード用）
            else:
                self.mode_btn.configure(text="🌙")  # 月アイコン（ダークモード用）
        
        # ボタンの色を更新（ダークモード時は明るい灰色、ライトモード時は暗い灰色）
        if hasattr(self, 'mode_btn') and hasattr(self, 'close_btn'):
            if self.dark_mode:
                # ダークモード時：明るい灰色
                self.mode_btn.configure(text_color="gray90", hover_color="gray70")
                self.close_btn.configure(text_color="gray90", hover_color="gray70")
            else:
                # ライトモード時：暗い灰色
                self.mode_btn.configure(text_color="gray70", hover_color="gray80")
                self.close_btn.configure(text_color="gray70", hover_color="gray80")
        
        # ウィンドウとタイトルバーの背景色を更新（縁取りも考慮）
        self.update_window_border()
        self.window.attributes('-alpha', 0.85)  # 透明度を設定
        
        if hasattr(self, 'title_frame'):
            if self.dark_mode:
                self.title_frame.configure(fg_color="#505050")
                if hasattr(self, 'title_label'):
                    self.title_label.configure(text_color="white")
            else:
                self.title_frame.configure(fg_color="white")  # 白
                if hasattr(self, 'title_label'):
                    self.title_label.configure(text_color="#2c2c2c")  # 暗めのグレー
        
        logger.info(f"Applied {'dark' if self.dark_mode else 'light'} mode theme")
    
    def apply_dark_mode(self):
        """ダークモードのスタイルを適用"""
        self.update_window_border()  # 縁取りも考慮してウィンドウ背景設定
        self.window.attributes('-alpha', 0.85)  # 透明度を設定
        self.title_frame.configure(fg_color="#505050")
        self.title_label.configure(text_color="white")
        self.mode_btn.configure(text="☀")  # 太陽アイコン（ライトモード用）
        # ボタンの色をダークモード用に更新
        self.mode_btn.configure(text_color="gray90", hover_color="gray70")
        self.close_btn.configure(text_color="gray90", hover_color="gray70")
    
    def apply_light_mode(self):
        """ライトモードのスタイルを適用"""
        self.update_window_border()  # 縁取りも考慮してウィンドウ背景設定
        self.window.attributes('-alpha', 0.85)  # 透明度を設定
        self.title_frame.configure(fg_color="white")  # 白
        self.title_label.configure(text_color="#2c2c2c")  # 暗めのグレー
        self.mode_btn.configure(text="🌙")  # 月アイコン（ダークモード用）
        # ボタンの色をライトモード用に更新
        self.mode_btn.configure(text_color="gray70", hover_color="gray80")
        self.close_btn.configure(text_color="gray70", hover_color="gray80")
    
    def toggle_delay_input_mode(self):
        """遅延入力モードを切り替え"""
        self.delay_input_mode = not self.delay_input_mode
        
        # 設定を保存
        config = self.config_manager.config
        if not config:
            config = {}
        if 'floatingWindow' not in config:
            config['floatingWindow'] = {}
        
        config['floatingWindow']['delayInputMode'] = self.delay_input_mode
        
        # 遅延時間の設定（3秒固定）
        delay_time = 3000  # 3秒固定
        self.set_key_delay(delay_time if self.delay_input_mode else 0)
        
        # ウィンドウの縁取りを更新
        self.update_window_border()
        
        # 設定を保存
        self.config_manager.save_config(config)
        
        mode_text = "ON" if self.delay_input_mode else "OFF"
        logger.info(f"Delay input mode toggled to {mode_text}")
    
    def update_window_border(self):
        """遅延入力モードに応じてウィンドウの縁取りを更新"""
        # メインフレームの背景色を設定
        if self.dark_mode:
            frame_color = "#404040"
        else:
            frame_color = "gray90"
            
        if self.delay_input_mode:
            # 遅延入力モードON: 青い縁取り
            self.main_frame.configure(fg_color=frame_color, border_width=3, border_color="#2563eb")
        else:
            # 遅延入力モードOFF: 縁取りなし
            self.main_frame.configure(fg_color=frame_color, border_width=0)
    
    def set_context_menu_callback(self, callback):
        """右クリックメニューコールバックを設定"""
        self.context_menu_callback = callback
        logger.info("Context menu callback set")
    
    def setup_context_menu_bindings(self):
        """右クリックメニューのイベントバインドを設定"""
        if not self.window:
            return
        
        try:
            # ウィンドウ全体に右クリックイベントをバインド
            self.window.bind("<Button-3>", self._on_right_click)
            
            # 各フレームにも右クリックイベントをバインド
            if hasattr(self, 'main_frame'):
                self.main_frame.bind("<Button-3>", self._on_right_click)
            if hasattr(self, 'title_frame'):
                self.title_frame.bind("<Button-3>", self._on_right_click)
            if hasattr(self, 'button_frame'):
                self.button_frame.bind("<Button-3>", self._on_right_click)
            
            # 各ボタンには既に個別の右クリックハンドラーが設定されているため、
            # ここでは一般的なright_clickバインドは行わない
            
            logger.info("Context menu bindings set up successfully")
            
        except Exception as e:
            logger.error(f"Failed to set up context menu bindings: {e}")
    
    def _on_right_click(self, event):
        """右クリック時のイベントハンドラ"""
        try:
            logger.info(f"Floating right click from {event.widget}")
            if self.context_menu_callback:
                # イベント伝播を停止
                event.widget.focus_set()
                self.context_menu_callback(event)
                return "break"
            else:
                # コールバックが設定されていない場合はイベント伝播を停止してフォールバックメニューを防ぐ
                logger.info("No context menu callback set, suppressing default menu")
                return "break"
        except Exception as e:
            logger.error(f"Error handling right click: {e}")
            return "break"
    
    def _on_button_right_click(self, event, key, label):
        """ボタン固有の右クリックメニュー"""
        try:
            logger.info(f"Button right click: {key} ({label})")
            
            # 既存のメインメニューを呼び出し、ボタン固有の情報を渡す
            if self.context_menu_callback:
                # ボタン情報を event に追加
                event.button_key = key
                event.button_label = label
                self.context_menu_callback(event)
                return "break"
            
            # フォールバック: 基本メニューのみ表示
            context_menu = tk.Menu(self.window, tearoff=0)
            context_menu.add_command(
                label=f"このボタンの設定 ({label})",
                command=lambda: self._open_button_config(key, label)
            )
            context_menu.tk_popup(event.x_root, event.y_root)
            
            # イベント伝播を停止
            return "break"
            
        except Exception as e:
            logger.error(f"Error showing button context menu: {e}")
            return "break"
    
    def _open_button_config(self, key, label):
        """指定されたボタンの設定画面を開く"""
        try:
            logger.info(f"Opening button config for: {key} ({label})")
            
            # 設定からボタン設定を検索
            config = self.config_manager.config
            if not config or 'floatingWindow' not in config:
                logger.error("No floating window config found")
                return
            
            buttons_config = config['floatingWindow'].get('buttons', [])
            button_index = -1
            button_config = None
            
            # キーまたはラベルでボタンを特定
            for i, btn_config in enumerate(buttons_config):
                if (btn_config.get('key') == key or 
                    btn_config.get('label') == label):
                    button_index = i
                    button_config = btn_config
                    break
            
            if button_config is None:
                logger.error(f"Button config not found for key: {key}")
                return
            
            # ButtonEditDialogを開く
            from virtual_keyboard.ui.dialogs import ButtonEditDialog
            
            def on_button_save():
                """ボタン設定保存後のコールバック"""
                try:
                    # 設定を保存
                    if self.config_manager.save_config(config):
                        logger.info(f"Button {key} config saved successfully")
                        # フローティングキーボードのボタンを再作成
                        self.create_buttons()
                    else:
                        logger.error("Failed to save button config")
                except Exception as e:
                    logger.error(f"Error saving button config: {e}")
            
            # ボタン設定ダイアログを開く
            dialog = ButtonEditDialog(
                self.window,
                button_config,
                on_button_save
            )
            
        except Exception as e:
            logger.error(f"Error opening button config: {e}")
    
    def set_key_delay(self, delay_ms: int):
        """キー送信遅延時間を設定"""
        self.key_delay_ms = max(0, delay_ms)
        logger.info(f"Key delay set to {self.key_delay_ms}ms")
    
    def _on_button_enter(self, event, key, label):
        """ボタンにマウスが入った時の処理（ツールチップ＋ハイライト）"""
        try:
            # 通常のツールチップ表示
            self.show_tooltip(event, key, label)
            
            # トグルハイライトが有効な場合、追加のハイライトを適用
            self._apply_hover_highlight(key, True)
            
        except Exception as e:
            logger.error(f"Error in button enter event for {key}: {e}")
    
    def _on_button_leave(self, event, key):
        """ボタンからマウスが離れた時の処理（ツールチップ非表示＋ハイライト解除）"""
        try:
            # ツールチップを非表示
            self.hide_tooltip()
            
            # ホバーハイライトを解除
            self._apply_hover_highlight(key, False)
            
        except Exception as e:
            logger.error(f"Error in button leave event for {key}: {e}")
    
    def _apply_hover_highlight(self, key, is_hovering):
        """ホバー時の追加ハイライトを適用"""
        try:
            # トグルハイライト機能が有効でない場合は何もしない
            config = self.config_manager.config
            if not config or 'floatingWindow' not in config:
                return
            
            buttons = config['floatingWindow'].get('buttons', [])
            button_config = None
            for btn_config in buttons:
                if btn_config.get('key') == key:
                    button_config = btn_config
                    break
            
            if not button_config or not button_config.get('toggleHighlight', False):
                return
            
            # 該当するボタンを検索
            target_button = None
            for button, button_key in self.buttons:
                if button_key == key:
                    target_button = button
                    break
            
            if not target_button:
                return
            
            # 現在のトグル状態を取得
            is_toggled = self.button_toggle_states.get(key, False)
            base_color = button_config.get('color', '#2563eb')
            
            if is_hovering:
                # ホバー時の色を計算
                if is_toggled:
                    # トグルON時: ハイライトカラーから計算
                    highlight_color = button_config.get('highlightColor', '#fef3c7')
                    if highlight_color == '#fef3c7':
                        # デフォルトハイライト色の場合、透明色対応
                        hover_color = self._brighten_color(highlight_color, 1.2)
                    else:
                        # 設定されたハイライト色から計算
                        hover_color = self._brighten_color(highlight_color, 1.2)
                    logger.debug(f"Toggle ON hover for {key}: highlight={highlight_color}, hover={hover_color}")
                else:
                    # トグルOFF時: ベースカラーから計算
                    if base_color == "transparent":
                        # 透明色の場合はget_button_colorsのホバー色を使用
                        _, _, hover_color = self.get_button_colors(base_color)
                    else:
                        hover_color = self._brighten_color(base_color, 1.2)
                    logger.debug(f"Toggle OFF hover for {key}: base={base_color}, hover={hover_color}")
                target_button.configure(fg_color=hover_color)
            else:
                # ホバー終了: 元の状態に戻す
                if is_toggled:
                    # トグルON状態の色に戻す：設定されたハイライトカラーを使用
                    highlight_color = button_config.get('highlightColor', self._brighten_color(base_color, 1.3))
                    target_button.configure(fg_color=highlight_color)
                else:
                    # 通常色に戻す
                    target_button.configure(fg_color=base_color)
                    
        except Exception as e:
            logger.error(f"Error applying hover highlight for {key}: {e}")
    
    def _brighten_color(self, color, factor):
        """色を明るくする"""
        try:
            if color == "transparent":
                # 透明色の場合はデフォルトのハイライト色を返す
                return "#fef3c7"
            elif color.startswith('#') and len(color) == 7:
                # RGB値を取得
                try:
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                except ValueError as e:
                    logger.error(f"Invalid hex color '{color}' in _brighten_color: {e}")
                    return "#fef3c7"  # フォールバック色
                
                # 各値をfactor倍して明るくする（255を超えない）
                r = min(255, int(r * factor))
                g = min(255, int(g * factor))
                b = min(255, int(b * factor))
                
                return f"#{r:02x}{g:02x}{b:02x}"
            else:
                return "#fef3c7"  # フォールバック色（淡い黄色）
        except:
            return "#fef3c7"  # フォールバック色（淡い黄色）
    
    def get_key_delay(self) -> int:
        """キー送信遅延時間を取得"""
        return self.key_delay_ms
    
    def send_key_with_delay(self, key: str):
        """遅延付きでキーを送信"""
        if self.key_delay_ms > 0:
            # 遅延がある場合は、after()を使用して遅延実行
            logger.info(f"Sending key {key} with {self.key_delay_ms}ms delay")
            self.window.after(self.key_delay_ms, lambda: self._send_key_immediate(key))
        else:
            # 遅延がない場合は即座送信
            self._send_key_immediate(key)
    
    def _send_key_immediate(self, key: str):
        """即座にキーを送信（内部メソッド）"""
        self.on_button_click(key)
    
    def handle_key_with_delay(self, key):
        """キー送信を遅延設定に応じて処理"""
        # 遅延入力モードがONかつ遅延時間が設定されている場合
        if self.delay_input_mode and self.key_delay_ms > 0:
            logger.info(f"Button {key} clicked - will send with {self.key_delay_ms}ms delay")
            # カウントダウン表示開始
            self.show_countdown(key, self.key_delay_ms)
            self.window.after(self.key_delay_ms, lambda: self.send_key_with_focus(key))
        else:
            # 遅延なしの場合は即座実行
            self.send_key_with_focus(key)
    
    def show_countdown(self, key, delay_ms):
        """カウントダウンウィンドウを表示"""
        try:
            # 既存のカウントダウンがあれば削除
            if hasattr(self, 'countdown_window') and self.countdown_window:
                try:
                    self.countdown_window.destroy()
                except:
                    pass
            
            # カウントダウンウィンドウを作成
            self.countdown_window = tk.Toplevel(self.window)
            self.countdown_window.overrideredirect(True)  # タイトルバーなし
            self.countdown_window.attributes('-topmost', True)  # 最前面
            self.countdown_window.attributes('-alpha', 0.9)  # 半透明
            
            # ウィンドウサイズと位置
            countdown_width = 200
            countdown_height = 100
            
            # フローティングキーボードの位置を取得
            kb_x = self.window.winfo_x()
            kb_y = self.window.winfo_y()
            kb_width = self.window.winfo_width()
            
            # カウントダウンを中央上部に表示
            x = kb_x + (kb_width - countdown_width) // 2
            y = kb_y - countdown_height - 10  # キーボードの上に表示
            
            self.countdown_window.geometry(f"{countdown_width}x{countdown_height}+{x}+{y}")
            
            # 背景設定
            if self.dark_mode:
                bg_color = "#2b2b2b"
                fg_color = "#ffffff"
            else:
                bg_color = "#999999"
                fg_color = "#000000"
            
            self.countdown_window.configure(bg=bg_color)
            
            # メインフレーム
            main_frame = tk.Frame(self.countdown_window, bg=bg_color)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # キー名表示
            key_label = tk.Label(main_frame, text=f"🔑 {key}", 
                                font=("Arial", 14, "bold"),
                                bg=bg_color, fg=fg_color)
            key_label.pack(pady=(0, 5))
            
            # カウントダウン表示
            self.countdown_label = tk.Label(main_frame, 
                                          text="",
                                          font=("Arial", 24, "bold"),
                                          bg=bg_color, fg=fg_color)
            self.countdown_label.pack()
            
            # カウントダウン開始
            self.remaining_ms = delay_ms
            self.update_countdown()
            
            # 遅延時間後に自動で閉じる
            self.countdown_window.after(delay_ms, self.close_countdown)
            
        except Exception as e:
            logger.error(f"Error showing countdown: {e}")
    
    def update_countdown(self):
        """カウントダウン表示を更新"""
        try:
            if hasattr(self, 'countdown_window') and self.countdown_window and hasattr(self, 'countdown_label'):
                # 残り秒数を計算（小数点1位まで表示）
                remaining_sec = self.remaining_ms / 1000.0
                self.countdown_label.config(text=f"⏱️ {remaining_sec:.1f}秒")
                
                # まだ時間が残っている場合は更新を続ける
                if self.remaining_ms > 100:
                    self.remaining_ms -= 100
                    self.countdown_window.after(100, self.update_countdown)
        except Exception as e:
            logger.error(f"Error updating countdown: {e}")
    
    def close_countdown(self):
        """カウントダウンウィンドウを閉じる"""
        try:
            if hasattr(self, 'countdown_window') and self.countdown_window:
                self.countdown_window.destroy()
                self.countdown_window = None
        except Exception as e:
            logger.error(f"Error closing countdown: {e}")
    
    def show(self):
        """ウィンドウを表示（エイリアス）"""
        self.show_window()
    
    def hide(self):
        """ウィンドウを非表示（エイリアス）"""
        self.hide_window()
    
    def show_tooltip(self, event, key, label):
        """ツールチップを表示"""
        try:
            # 既存のツールチップを隠す
            self.hide_tooltip()
            
            # 少し遅延してからツールチップを表示
            self.tooltip_timer = self.window.after(500, lambda: self._show_tooltip_delayed(event, key, label))
            
        except Exception as e:
            logger.error(f"Error showing tooltip: {e}")
    
    def _show_tooltip_delayed(self, event, key, label):
        """遅延実行でツールチップを表示"""
        try:
            # ボタンの位置を取得
            widget = event.widget
            x = widget.winfo_rootx()
            y = widget.winfo_rooty()
            height = widget.winfo_height()
            
            # ツールチップウィンドウを作成
            self.tooltip = tk.Toplevel(self.window)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.configure(bg="black")
            
            # ツールチップのテキストを設定に応じて作成
            if self.tooltip_mode == 'label':
                tooltip_text = label
            elif self.tooltip_mode == 'key':
                tooltip_text = key
            else:  # 'both'
                tooltip_text = f"{label}\nKey: {key}"
            label_widget = tk.Label(self.tooltip, 
                                  text=tooltip_text,
                                  bg="black", 
                                  fg="white",
                                  font=("Arial", 9),
                                  padx=5,
                                  pady=3)
            label_widget.pack()
            
            # ツールチップを適切な位置に表示（ボタンの上側）
            tooltip_height = 40  # ツールチップの推定高さ
            self.tooltip.geometry(f"+{x}+{y - tooltip_height - 5}")
            self.tooltip.attributes('-topmost', True)
            
        except Exception as e:
            logger.error(f"Error creating tooltip: {e}")
    
    def hide_tooltip(self):
        """ツールチップを隠す"""
        try:
            # タイマーをキャンセル
            if self.tooltip_timer:
                self.window.after_cancel(self.tooltip_timer)
                self.tooltip_timer = None
            
            # ツールチップウィンドウを破棄
            if self.tooltip:
                self.tooltip.destroy()
                self.tooltip = None
                
        except Exception as e:
            logger.debug(f"Error hiding tooltip: {e}")