"""
Main Window - メインアプリケーションウィンドウ
"""

import logging
import customtkinter as ctk
import subprocess
import sys
import os

from ..core.interfaces import IConfigManager, IHotkeyManager, IKeySender, IFocusManager
from ..core.types import FocusConfig, FocusRestoreMethod
from ..config.manager import ConfigManager
from ..services.hotkey import HotkeyManager
from ..services.keysender import KeySender
from ..services.focus import FocusManager
from .floating import FloatingKeyboard
from .dialogs import ConfigDialog, FocusConfigDialog, FloatingKeypadConfigDialog

logger = logging.getLogger(__name__)

# Windows API Constants
VK_F1 = 0x70
VK_F13 = 0x7C


class VirtualKeyboardApp:
    """メインアプリケーションクラス"""
    
    def __init__(self):
        # 依存性注入によるコンポーネント初期化
        self.config_manager = ConfigManager()
        self.key_sender = KeySender()
        self.hotkey_manager = HotkeyManager(callback=self.on_hotkey_pressed)
        
        # フォーカス管理の初期化
        focus_config = self.config_manager.get_focus_config()
        self.focus_manager = FocusManager(focus_config)
        
        # フローティングキーボードの初期化
        self.floating_keyboard = None
        
        # 保存された外観設定を適用
        self.apply_appearance_settings()
        
        # CustomTkinterの基本設定
        ctk.set_default_color_theme("green")  # シンプルなアクセントカラー
        
        # メインウィンドウの背景を白に設定
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
        
        # UI初期化
        self.root = ctk.CTk()
        self.root.title("Virtual Keyboard")
        self.root.resizable(False, False)
        
        self.setup_ui()
        self.apply_hotkey_config()
        
        # サービス開始
        self.hotkey_manager.start_message_loop()
        self.focus_manager.start_monitoring()
        
        # メインウィンドウIDを除外リストに追加（ウィンドウが作成された後）
        self.root.after(100, self.register_excluded_windows)
        
        # 起動時のフローティングウィンドウ自動表示チェック
        self.root.after(200, self.check_auto_show_floating)
        
        # 終了処理の設定
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def apply_appearance_settings(self):
        """保存された外観設定を適用"""
        try:
            appearance_config = self.config_manager.config.get("appearance", {})
            mode = appearance_config.get("mode", "Light").lower()
            
            # CustomTkinterの外観モードを設定
            if mode in ["dark", "ダーク"]:
                ctk.set_appearance_mode("dark")
                logger.info("Applied dark mode from config")
            else:
                ctk.set_appearance_mode("light") 
                logger.info("Applied light mode from config")
                
        except Exception as e:
            logger.warning(f"Failed to apply appearance settings, using default: {e}")
            ctk.set_appearance_mode("light")  # デフォルトはライトモード
    
    def setup_ui(self):
        """UI設定 - ディーター・ラムス風ミニマルデザイン"""
        # テーマに応じた背景色を設定
        current_mode = ctk.get_appearance_mode().lower()
        if current_mode == "dark":
            bg_color = "transparent"
            self.root.configure(fg_color="#212121")
        else:
            bg_color = "transparent"  
            self.root.configure(fg_color="#f8f9fa")
        
        # メインフレーム - 適切な余白
        main_frame = ctk.CTkFrame(self.root, fg_color=bg_color, corner_radius=0)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # グリッド設定
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # ステータス表示 - 控えめに上部に配置
        self.status_label = ctk.CTkLabel(main_frame, 
                                        text="Ready",
                                        font=ctk.CTkFont(size=11, family="Helvetica"),
                                        text_color="#666666")
        self.status_label.grid(row=0, column=0, columnspan=2, pady=(0, 30), sticky="w")
        
        # メインコントロール - 2x2グリッドレイアウト
        self.btn_hotkey = ctk.CTkButton(main_frame, 
                                       text="Hotkey Config",
                                       font=ctk.CTkFont(size=11, family="Helvetica"),
                                       height=36,
                                       corner_radius=2,
                                       fg_color="#f0f0f0",
                                       text_color="#333333",
                                       hover_color="#f0f0f0",
                                       command=self.open_config_dialog)
        self.btn_hotkey.grid(row=1, column=0, padx=(0, 10), pady=(0, 10), sticky="ew")
        
        self.btn_focus = ctk.CTkButton(main_frame, 
                                      text="Focus Config",
                                      font=ctk.CTkFont(size=11, family="Helvetica"),
                                      height=36,
                                      corner_radius=2,
                                      fg_color="#f0f0f0",
                                      text_color="#333333",
                                      hover_color="#f0f0f0",
                                      command=self.open_focus_config_dialog)
        self.btn_focus.grid(row=1, column=1, padx=(10, 0), pady=(0, 10), sticky="ew")
        
        self.btn_floating = ctk.CTkButton(main_frame, 
                                         text="Show Floating",
                                         font=ctk.CTkFont(size=11, family="Helvetica"),
                                         height=36,
                                         corner_radius=2,
                                         fg_color="#333333",
                                         text_color="#ffffff",
                                         hover_color="#555555",
                                         command=self.toggle_floating_window)
        self.btn_floating.grid(row=2, column=0, padx=(0, 10), pady=(0, 20), sticky="ew")
        
        self.btn_floating_config = ctk.CTkButton(main_frame, 
                                                text="Keypad Config",
                                                font=ctk.CTkFont(size=11, family="Helvetica"),
                                                height=36,
                                                corner_radius=2,
                                                fg_color="#f0f0f0",
                                                text_color="#333333",
                                                hover_color="#f0f0f0",
                                                command=self.open_floating_keypad_config_dialog)
        self.btn_floating_config.grid(row=2, column=1, padx=(10, 0), pady=(0, 20), sticky="ew")
        
        # システムコントロール - 下部に小さく配置
        system_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        system_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        self.btn_test = ctk.CTkButton(system_frame, 
                                     text="Test",
                                     font=ctk.CTkFont(size=10, family="Helvetica"),
                                     height=28,
                                     width=60,
                                     corner_radius=2,
                                     fg_color="transparent",
                                     text_color="#666666",
                                     hover_color="#f0f0f0",
                                     border_width=1,
                                     border_color="#d0d0d0",
                                     command=self.test_focus_restore)
        self.btn_test.pack(side="left", padx=(0, 8))
        
        self.btn_debug = ctk.CTkButton(system_frame, 
                                      text="Debug",
                                      font=ctk.CTkFont(size=10, family="Helvetica"),
                                      height=28,
                                      width=60,
                                      corner_radius=2,
                                      fg_color="transparent",
                                      text_color="#666666",
                                      hover_color="#f0f0f0",
                                      border_width=1,
                                      border_color="#d0d0d0",
                                      command=self.show_debug_info)
        self.btn_debug.pack(side="left", padx=(0, 8))
        
        self.btn_export = ctk.CTkButton(system_frame, 
                                       text="Export",
                                       font=ctk.CTkFont(size=10, family="Helvetica"),
                                       height=28,
                                       width=60,
                                       corner_radius=2,
                                       fg_color="transparent",
                                       text_color="#666666",
                                       hover_color="#f0f0f0",
                                       border_width=1,
                                       border_color="#d0d0d0",
                                       command=self.export_config)
        self.btn_export.pack(side="left", padx=(0, 8))
        
        self.btn_import = ctk.CTkButton(system_frame, 
                                       text="Import",
                                       font=ctk.CTkFont(size=10, family="Helvetica"),
                                       height=28,
                                       width=60,
                                       corner_radius=2,
                                       fg_color="transparent",
                                       text_color="#666666",
                                       hover_color="#f0f0f0",
                                       border_width=1,
                                       border_color="#d0d0d0",
                                       command=self.import_config)
        self.btn_import.pack(side="left", padx=(0, 8))
        
        self.btn_exit = ctk.CTkButton(system_frame, 
                                     text="Exit",
                                     font=ctk.CTkFont(size=10, family="Helvetica"),
                                     height=28,
                                     width=60,
                                     corner_radius=2,
                                     fg_color="transparent",
                                     text_color="#666666",
                                     hover_color="#f0f0f0",
                                     border_width=1,
                                     border_color="#d0d0d0",
                                     command=self.on_closing)
        self.btn_exit.pack(side="left")
        
        # グリッド設定
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # コンテンツに合わせてサイズ調整
        self.auto_resize_window()
    
    def auto_resize_window(self):
        """ウィンドウサイズを固定し、中央に配置"""
        self.root.update_idletasks()
        
        # 固定サイズ - コンテンツに合わせたサイズ（エクスポート・インポートボタン追加により幅を拡張）
        window_width = 460
        window_height = 340
        
        # 画面中央に配置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def apply_hotkey_config(self):
        """ホットキー設定を適用"""
        self.hotkey_manager.unregister_all()
        
        hotkey_id = 1000
        registered_count = 0
        
        # Set1の処理
        set1_config = self.config_manager.get_hotkey_config("set1")
        if set1_config and set1_config.enabled:
            modifiers = self.config_manager.get_modifiers_value(set1_config.modifiers)
            # 修飾キーなしでも登録可能にする（modifiers >= 0 に変更）
            if modifiers >= 0:
                for i, target_key in enumerate(set1_config.target_keys[:6]):  # F1-F6のみ
                    trigger_vk = VK_F1 + i
                    target_vk = self.config_manager.key_name_to_vk(target_key)
                    desc = f"Set1: F{i+1} -> {target_key}"
                    
                    if self.hotkey_manager.register_hotkey(hotkey_id, modifiers, trigger_vk, desc):
                        self.hotkey_manager.set_target_key(hotkey_id, target_vk)
                        registered_count += 1
                        hotkey_id += 1
        
        # Set2の処理
        set2_config = self.config_manager.get_hotkey_config("set2")
        if set2_config and set2_config.enabled:
            modifiers = self.config_manager.get_modifiers_value(set2_config.modifiers)
            set1_modifiers = self.config_manager.get_modifiers_value(set1_config.modifiers) if set1_config and set1_config.enabled else -1
            
            # Set2も修飾キーなしでも登録可能にし、Set1と異なる場合のみ登録
            if modifiers >= 0 and modifiers != set1_modifiers:
                for i, target_key in enumerate(set2_config.target_keys[:6]):  # F1-F6のみ
                    trigger_vk = VK_F1 + i
                    target_vk = self.config_manager.key_name_to_vk(target_key)
                    desc = f"Set2: F{i+1} -> {target_key}"
                    
                    if self.hotkey_manager.register_hotkey(hotkey_id, modifiers, trigger_vk, desc):
                        self.hotkey_manager.set_target_key(hotkey_id, target_vk)
                        registered_count += 1
                        hotkey_id += 1
        
        # ステータス更新 - シンプルなテキスト表示
        if registered_count > 0:
            self.status_label.configure(text=f"{registered_count} hotkeys active", 
                                       text_color="#333333")
            logger.info(f"Loaded {registered_count} hotkeys from config")
        else:
            self.status_label.configure(text="No hotkeys active", 
                                       text_color="#999999")
            logger.info("No hotkeys configured")
    
    def on_hotkey_pressed(self, hotkey_id: int, hotkey_info: dict):
        """ホットキー押下時の処理"""
        target_vk = hotkey_info.get('target_key')
        if target_vk:
            # フォーカス復帰
            last_focus = self.focus_manager.get_last_focus_window()
            if last_focus:
                self.focus_manager.restore_focus(last_focus)
            
            # キー送信
            if self.key_sender.send_key(target_vk):
                key_name = KeySender.vk_code_to_name(target_vk)
                logger.info(f"Hotkey: {hotkey_info['description']} -> {key_name}")
    
    def open_config_dialog(self):
        """設定ダイアログを開く"""
        ConfigDialog(self.root, self.config_manager, callback=self.apply_hotkey_config)
    
    def open_focus_config_dialog(self):
        """フォーカス設定ダイアログを開く"""
        FocusConfigDialog(self.root, self.config_manager, callback=self.reload_focus_config)
    
    def open_floating_keypad_config_dialog(self):
        """フローティングキーパッド設定ダイアログを開く"""
        FloatingKeypadConfigDialog(self.root, self.config_manager, callback=self.reload_floating_keypad_config)
    
    def register_excluded_windows(self):
        """除外するウィンドウIDを登録"""
        try:
            # メインウィンドウIDを取得して除外リストに追加
            main_window_id = self.root.winfo_id()
            self.focus_manager.add_excluded_window(main_window_id)
            logger.info(f"Registered main window {main_window_id} as excluded")
        except Exception as e:
            logger.error(f"Error registering excluded windows: {e}")
    
    def check_auto_show_floating(self):
        """起動時のフローティングウィンドウ自動表示チェック"""
        try:
            config = self.config_manager.config
            if config and 'floatingWindow' in config:
                floating_config = config['floatingWindow']
                show_on_startup = floating_config.get('showOnStartup', False)
                
                if show_on_startup:
                    logger.info("Auto-showing floating keypad on startup")
                    self.show_floating_window()
                else:
                    logger.info("Floating keypad auto-show disabled")
            else:
                logger.info("No floating window config found")
        except Exception as e:
            logger.error(f"Error checking auto-show floating: {e}")
    
    def show_floating_window(self):
        """フローティングウィンドウを表示"""
        if not self.floating_keyboard:
            self.floating_keyboard = FloatingKeyboard(
                self.root, self.config_manager, self.key_sender, self.focus_manager
            )
        
        self.floating_keyboard.show_window()
        self.btn_floating.configure(text="Hide Floating")
    
    def toggle_floating_window(self):
        """フローティングウィンドウの切り替え"""
        if not self.floating_keyboard:
            self.floating_keyboard = FloatingKeyboard(
                self.root, self.config_manager, self.key_sender, self.focus_manager
            )
        
        self.floating_keyboard.toggle_window()
        
        # ボタンテキストを更新 - シンプルなラベル
        if hasattr(self, 'btn_floating'):
            if self.floating_keyboard.is_visible:
                self.btn_floating.configure(text="Hide")
            else:
                self.btn_floating.configure(text="Show")
    
    def test_focus_restore(self):
        """フォーカス復帰のテスト"""
        last_focus = self.focus_manager.get_last_focus_window()
        if last_focus:
            success = self.focus_manager.restore_focus(last_focus)
            
            # 結果ダイアログ
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("🧪 Test Result")
            dialog.geometry("350x200")
            dialog.attributes('-topmost', True)
            dialog.resizable(False, False)
            
            icon = "✅" if success else "❌"
            result_text = "成功" if success else "失敗"
            color = ("#16a34a", "#22c55e") if success else ("#dc2626", "#ef4444")
            
            label = ctk.CTkLabel(dialog, 
                                text=f"{icon}\n\nフォーカス復帰テスト:\n{result_text}",
                                font=ctk.CTkFont(size=16, weight="bold"),
                                text_color=color,
                                justify="center")
            label.pack(expand=True)
            
            btn_close = ctk.CTkButton(dialog, text="OK", command=dialog.destroy)
            btn_close.pack(pady=20)
        else:
            # 警告ダイアログ
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("⚠️ Warning")
            dialog.geometry("350x200")
            dialog.attributes('-topmost', True)
            dialog.resizable(False, False)
            
            label = ctk.CTkLabel(dialog, 
                                text="⚠️\n\nターゲットウィンドウが\n記憶されていません",
                                font=ctk.CTkFont(size=16, weight="bold"),
                                text_color=("#f59e0b", "#fbbf24"),
                                justify="center")
            label.pack(expand=True)
            
            btn_close = ctk.CTkButton(dialog, text="OK", command=dialog.destroy)
            btn_close.pack(pady=20)
    
    def show_debug_info(self):
        """デバッグ情報を表示"""
        focus_config = self.config_manager.get_focus_config()
        last_focus = self.focus_manager.get_last_focus_window()
        
        # デバッグダイアログ
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("🔍 Debug Information")
        dialog.geometry("450x350")
        dialog.attributes('-topmost', True)
        dialog.resizable(False, False)
        
        # メインフレーム
        main_frame = ctk.CTkScrollableFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # タイトル
        title = ctk.CTkLabel(main_frame, 
                            text="🔍 Debug Information",
                            font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=(0, 15))
        
        # 情報表示
        info_items = [
            ("🎯 フォーカス復帰", "有効" if focus_config.enabled else "無効"),
            ("⚡ 復帰方法", focus_config.method.value),
            ("⏱️ 遅延", f"{focus_config.delay}ms"),
            ("🪟 最後のウィンドウ", str(last_focus) if last_focus else "なし"),
            ("🔥 登録済みホットキー", f"{len(self.hotkey_manager.hotkeys)}個"),
        ]
        
        for label_text, value_text in info_items:
            item_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            item_frame.pack(fill="x", pady=5)
            
            label = ctk.CTkLabel(item_frame, 
                                text=label_text,
                                font=ctk.CTkFont(size=12, weight="bold"),
                                anchor="w")
            label.pack(side="left", padx=(0, 10))
            
            value = ctk.CTkLabel(item_frame, 
                                text=value_text,
                                font=ctk.CTkFont(size=12),
                                text_color=("gray70", "gray30"),
                                anchor="e")
            value.pack(side="right")
        
        # 閉じるボタン
        btn_close = ctk.CTkButton(dialog, 
                                 text="Close", 
                                 height=35,
                                 command=dialog.destroy)
        btn_close.pack(pady=20)
    
    def on_closing(self):
        """アプリケーション終了時の処理"""
        logger.info("Application closing...")
        
        # フローティングウィンドウの終了処理
        if self.floating_keyboard:
            self.floating_keyboard.destroy()
        
        # その他の終了処理
        self.focus_manager.stop_monitoring()
        self.hotkey_manager.stop_message_loop()
        self.hotkey_manager.unregister_all()
        self.root.destroy()
    
    def reload_focus_config(self):
        """フォーカス設定を再読み込み"""
        try:
            # 新しい設定で FocusManager を再初期化
            focus_config = self.config_manager.get_focus_config()
            old_focus_manager = self.focus_manager
            
            # 古いマネージャーを停止
            old_focus_manager.stop_monitoring()
            
            # 新しいマネージャーを作成して開始
            self.focus_manager = FocusManager(focus_config)
            self.focus_manager.start_monitoring()
            
            # フローティングキーボードの参照も更新
            if self.floating_keyboard:
                self.floating_keyboard.focus_manager = self.focus_manager
            
            logger.info("Focus configuration reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload focus config: {e}")
    
    def reload_floating_keypad_config(self):
        """フローティングキーパッド設定を再読み込み"""
        try:
            # フローティングキーボードが存在する場合は再作成
            if self.floating_keyboard:
                was_visible = self.floating_keyboard.is_visible
                self.floating_keyboard.destroy()
                
                # 新しい設定で再作成
                self.floating_keyboard = FloatingKeyboard(
                    self.root, self.config_manager, self.key_sender, self.focus_manager
                )
                
                # 表示状態を復元
                if was_visible:
                    self.floating_keyboard.show_window()
                    self.btn_floating.configure(text="🪟 Hide Floating")
                else:
                    self.btn_floating.configure(text="🪟 Show Floating")
            
            logger.info("Floating keypad configuration reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload floating keypad config: {e}")
    
    def export_config(self):
        """設定をエクスポート"""
        try:
            if self.config_manager.export_config():
                logger.info("Configuration exported successfully")
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
    
    def import_config(self):
        """設定をインポート"""
        try:
            if self.config_manager.import_config():
                logger.info("Configuration imported successfully")
                # 3秒後に自動再起動
                self.root.after(3000, self.restart_application)
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
    
    def restart_application(self):
        """アプリケーションを再起動"""
        try:
            logger.info("Restarting application...")
            
            # 現在のプロセス情報を取得
            python_executable = sys.executable
            main_script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "main.py")
            
            # フローティングウィンドウを閉じる
            if self.floating_keyboard:
                self.floating_keyboard.destroy()
            
            # サービスを停止
            self.focus_manager.stop_monitoring()
            self.hotkey_manager.stop_message_loop()
            self.hotkey_manager.unregister_all()
            
            # 新しいプロセスを開始
            subprocess.Popen([python_executable, main_script])
            
            # 現在のプロセスを終了
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"Failed to restart application: {e}")
    
    def run(self):
        """アプリケーション実行"""
        logger.info("Virtual Keyboard App (Modular) started")
        self.root.mainloop()