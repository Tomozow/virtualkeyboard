"""
Configuration Dialogs - 設定ダイアログ
"""

import tkinter as tk
import time
import logging
import customtkinter as ctk
import win32gui
from tkinter import filedialog, messagebox, colorchooser
import emoji
import os
import requests
import threading
from PIL import Image, ImageDraw, ImageFont

# 画像処理ライブラリ（重いImportを初期化時に1回だけ）
try:
    # PIL modules are already imported above
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ..core.interfaces import IConfigManager
from ..core.types import FocusConfig, FocusRestoreMethod
from ..services.focus import FocusManager
from .button_edit_dialog import ButtonEditDialog

logger = logging.getLogger(__name__)

try:
    import tkinterdnd2 as tkdnd
    from tkinterdnd2 import TkinterDnD, DND_TEXT
    TKINTERDND_AVAILABLE = True
    logger.info("tkinterdnd2 successfully imported")
except ImportError:
    TKINTERDND_AVAILABLE = False
    logger.warning("tkinterdnd2 not available, drag & drop functionality will be limited")


class ConfigDialog:
    """ホットキー設定ダイアログ（CustomTkinter版）"""
    
    def __init__(self, parent, config_manager: IConfigManager, callback=None):
        self.config_manager = config_manager
        self.callback = callback
        
        # ダイアログ作成
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.configure(fg_color="#f8f9fa")
        self.dialog.title("⚙️ Hotkey Configuration")
        self.dialog.attributes('-topmost', True)
        self.dialog.resizable(True, True)
        
        # モーダルダイアログにする
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_dialog()
        self.load_current_config()
        # self.auto_resize_dialog()  # 初期化時のリサイズも無効化
    
    def setup_dialog(self):
        """ダイアログUI設定"""
        # メインフレーム
        main_frame = ctk.CTkScrollableFrame(self.dialog, fg_color="#f8f9fa")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # タイトル
        title_label = ctk.CTkLabel(main_frame, 
                                  text="⚙️ Configure Hotkey Sets",
                                  font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(0, 20))
        
        # Set1設定
        set1_frame = ctk.CTkFrame(main_frame)
        set1_frame.pack(fill="x", pady=(0, 15))
        
        # Set1タイトル
        set1_title = ctk.CTkLabel(set1_frame, 
                                 text="🔴 Set 1: F13-F18 (F1-F6 triggers)",
                                 font=ctk.CTkFont(size=16, weight="bold"))
        set1_title.pack(pady=(15, 10))
        
        # Set1有効化チェックボックス
        self.set1_enabled = tk.BooleanVar()
        set1_check = ctk.CTkCheckBox(set1_frame, text="Enable Set 1", 
                                    variable=self.set1_enabled,
                                    command=self.update_preview)
        set1_check.pack(pady=(0, 10))
        
        # Set1修飾キー
        set1_mod_frame = ctk.CTkFrame(set1_frame, fg_color="transparent")
        set1_mod_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(set1_mod_frame, text="Modifiers:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(0, 5))
        
        mod_grid_frame1 = ctk.CTkFrame(set1_mod_frame, fg_color="transparent")
        mod_grid_frame1.pack()
        
        self.set1_mods = {}
        mod_names = ["shift", "ctrl", "alt", "space"]
        mod_labels = ["Shift", "Ctrl", "Alt", "Win"]
        
        for i, (mod_name, mod_label) in enumerate(zip(mod_names, mod_labels)):
            var = tk.BooleanVar()
            check = ctk.CTkCheckBox(mod_grid_frame1, text=mod_label, 
                                   variable=var, command=self.update_preview)
            check.grid(row=0, column=i, padx=10, pady=5)
            self.set1_mods[mod_name] = var
        
        # Set1プレビュー
        self.set1_preview = ctk.CTkLabel(set1_frame, text="Preview: Not configured", 
                                        font=ctk.CTkFont(size=11),
                                        text_color=("blue", "lightblue"))
        self.set1_preview.pack(pady=(0, 15))
        
        # Set2設定
        set2_frame = ctk.CTkFrame(main_frame)
        set2_frame.pack(fill="x", pady=(0, 15))
        
        # Set2タイトル
        set2_title = ctk.CTkLabel(set2_frame, 
                                 text="🟢 Set 2: F19-F24 (F1-F6 triggers)",
                                 font=ctk.CTkFont(size=16, weight="bold"))
        set2_title.pack(pady=(15, 10))
        
        # Set2有効化チェックボックス
        self.set2_enabled = tk.BooleanVar()
        set2_check = ctk.CTkCheckBox(set2_frame, text="Enable Set 2", 
                                    variable=self.set2_enabled,
                                    command=self.update_preview)
        set2_check.pack(pady=(0, 10))
        
        # Set2修飾キー
        set2_mod_frame = ctk.CTkFrame(set2_frame, fg_color="transparent")
        set2_mod_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(set2_mod_frame, text="Modifiers:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(0, 5))
        
        mod_grid_frame2 = ctk.CTkFrame(set2_mod_frame, fg_color="transparent")
        mod_grid_frame2.pack()
        
        self.set2_mods = {}
        for i, (mod_name, mod_label) in enumerate(zip(mod_names, mod_labels)):
            var = tk.BooleanVar()
            check = ctk.CTkCheckBox(mod_grid_frame2, text=mod_label, 
                                   variable=var, command=self.update_preview)
            check.grid(row=0, column=i, padx=10, pady=5)
            self.set2_mods[mod_name] = var
        
        # Set2プレビュー
        self.set2_preview = ctk.CTkLabel(set2_frame, text="Preview: Not configured", 
                                        font=ctk.CTkFont(size=11),
                                        text_color=("blue", "lightblue"))
        self.set2_preview.pack(pady=(0, 15))
        
        # ボタンフレーム
        button_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=20)
        
        # 保存ボタン
        save_btn = ctk.CTkButton(button_frame, text="💾 Save & Apply", 
                                font=ctk.CTkFont(size=14, weight="bold"),
                                height=40,
                                fg_color=("green", "darkgreen"),
                                hover_color=("darkgreen", "green"),
                                command=self.save_config)
        save_btn.pack(side="left", padx=(0, 10), fill="x", expand=True)
        
        # キャンセルボタン
        cancel_btn = ctk.CTkButton(button_frame, text="❌ Cancel", 
                                  font=ctk.CTkFont(size=14, weight="bold"),
                                  height=40,
                                  fg_color=("gray", "darkgray"),
                                  hover_color=("darkgray", "gray"),
                                  command=self.dialog.destroy)
        cancel_btn.pack(side="right", padx=(10, 0), fill="x", expand=True)
    
    def load_current_config(self):
        """現在の設定を読み込み"""
        config = self.config_manager.config
        if not config or "hotkeys" not in config:
            return
        
        # Set1設定読み込み
        if "set1" in config["hotkeys"]:
            set1_data = config["hotkeys"]["set1"]
            self.set1_enabled.set(set1_data.get("enabled", False))
            
            modifiers = set1_data.get("modifiers", {})
            for mod_name, var in self.set1_mods.items():
                var.set(modifiers.get(mod_name, False))
        
        # Set2設定読み込み
        if "set2" in config["hotkeys"]:
            set2_data = config["hotkeys"]["set2"]
            self.set2_enabled.set(set2_data.get("enabled", False))
            
            modifiers = set2_data.get("modifiers", {})
            for mod_name, var in self.set2_mods.items():
                var.set(modifiers.get(mod_name, False))
        
        self.update_preview()
    
    def update_preview(self):
        """プレビュー更新"""
        # Set1プレビュー
        if self.set1_enabled.get():
            mods = [name.title() for name, var in self.set1_mods.items() if var.get()]
            if mods:
                mod_str = " + ".join(mods)
                preview_text = f"Preview: {mod_str} + F1-F6 → F13-F18"
            else:
                preview_text = "Preview: ⚠️ No modifiers selected"
        else:
            preview_text = "Preview: Disabled"
        
        self.set1_preview.configure(text=preview_text)
        
        # Set2プレビュー
        if self.set2_enabled.get():
            mods = [name.title() for name, var in self.set2_mods.items() if var.get()]
            if mods:
                mod_str = " + ".join(mods)
                preview_text = f"Preview: {mod_str} + F1-F6 → F19-F24"
            else:
                preview_text = "Preview: ⚠️ No modifiers selected"
        else:
            preview_text = "Preview: Disabled"
        
        self.set2_preview.configure(text=preview_text)
    
    def save_config(self):
        """設定を保存"""
        try:
            config = self.config_manager.config
            
            # Set1設定保存
            config["hotkeys"]["set1"]["enabled"] = self.set1_enabled.get()
            config["hotkeys"]["set1"]["modifiers"] = {
                name: var.get() for name, var in self.set1_mods.items()
            }
            
            # Set2設定保存
            config["hotkeys"]["set2"]["enabled"] = self.set2_enabled.get()
            config["hotkeys"]["set2"]["modifiers"] = {
                name: var.get() for name, var in self.set2_mods.items()
            }
            
            # 設定を保存
            if self.config_manager.save_config(config):
                # コールバック実行（ホットキーを再適用）
                if self.callback:
                    self.callback()
                
                # 成功メッセージ
                success_dialog = ctk.CTkToplevel(self.dialog)
                success_dialog.title("✅ Success")
                success_dialog.geometry("300x150")
                success_dialog.attributes('-topmost', True)
                success_dialog.transient(self.dialog)
                
                ctk.CTkLabel(success_dialog, 
                            text="✅\n\nConfiguration saved successfully!",
                            font=ctk.CTkFont(size=16),
                            justify="center").pack(expand=True)
                
                def close_all():
                    success_dialog.destroy()
                    self.dialog.destroy()
                
                ctk.CTkButton(success_dialog, text="OK", 
                             command=close_all).pack(pady=10)
                
                # 2秒後に自動で閉じる
                success_dialog.after(2000, close_all)
            else:
                # エラーメッセージ
                error_dialog = ctk.CTkToplevel(self.dialog)
                error_dialog.title("❌ Error")
                error_dialog.geometry("300x150")
                error_dialog.attributes('-topmost', True)
                error_dialog.transient(self.dialog)
                
                ctk.CTkLabel(error_dialog, 
                            text="❌\n\nFailed to save configuration!",
                            font=ctk.CTkFont(size=16),
                            justify="center").pack(expand=True)
                
                ctk.CTkButton(error_dialog, text="OK", 
                             command=error_dialog.destroy).pack(pady=10)
        
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def auto_resize_dialog(self):
        """ダイアログサイズを自動調整"""
        self.dialog.update_idletasks()
        self.dialog.geometry("600x700")
        
        # 画面中央に配置
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 700) // 2
        self.dialog.geometry(f"600x700+{x}+{y}")


class FocusConfigDialog:
    """フォーカス設定ダイアログ（CustomTkinter版）"""
    
    def __init__(self, parent, config_manager: IConfigManager, callback=None):
        self.config_manager = config_manager
        self.callback = callback
        
        # ダイアログ作成
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.configure(fg_color="#f8f9fa")
        self.dialog.title("🎯 Focus Configuration")
        self.dialog.attributes('-topmost', True)
        self.dialog.resizable(True, True)
        
        # モーダルダイアログにする
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_dialog()
        self.load_current_config()
        # self.auto_resize_dialog()  # 初期化時のリサイズも無効化
    
    def setup_dialog(self):
        """ダイアログUI設定"""
        # メインフレーム
        main_frame = ctk.CTkScrollableFrame(self.dialog, fg_color="#f8f9fa")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # タイトル
        title_label = ctk.CTkLabel(main_frame, 
                                  text="🎯 Focus Restore Configuration",
                                  font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(0, 20))
        
        # 基本設定フレーム
        basic_frame = ctk.CTkFrame(main_frame)
        basic_frame.pack(fill="x", pady=(0, 15))
        
        # 有効/無効
        ctk.CTkLabel(basic_frame, text="🔧 Basic Settings", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))
        
        self.enabled = tk.BooleanVar()
        enable_check = ctk.CTkCheckBox(basic_frame, text="Enable Focus Restore", 
                                      variable=self.enabled,
                                      command=self.update_preview)
        enable_check.pack(pady=(0, 15))
        
        # 復帰方法選択
        method_frame = ctk.CTkFrame(main_frame)
        method_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(method_frame, text="⚡ Restore Method", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))
        
        self.method = tk.StringVar(value="enhanced")
        
        methods = [
            ("simple", "🟢 Simple", "Basic focus restoration using SetForegroundWindow"),
            ("enhanced", "🔵 Enhanced", "Alt-key assisted focus switching (Recommended)"),
            ("force", "🔴 Force", "Multiple methods with fallback (Most aggressive)")
        ]
        
        for value, label, desc in methods:
            method_radio = ctk.CTkRadioButton(method_frame, text=f"{label}\n{desc}", 
                                             variable=self.method, value=value,
                                             command=self.update_preview)
            method_radio.pack(anchor="w", padx=20, pady=5)
        
        # 詳細設定フレーム
        detail_frame = ctk.CTkFrame(main_frame)
        detail_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(detail_frame, text="🛠️ Advanced Settings", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))
        
        # 遅延設定
        delay_frame = ctk.CTkFrame(detail_frame, fg_color="transparent")
        delay_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(delay_frame, text="⏱️ Delay (ms):", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        
        self.delay = tk.IntVar(value=50)
        delay_slider = ctk.CTkSlider(delay_frame, from_=0, to=500, 
                                    variable=self.delay,
                                    command=self.update_preview)
        delay_slider.pack(fill="x", pady=5)
        
        self.delay_label = ctk.CTkLabel(delay_frame, text="50ms", 
                                       text_color=("gray70", "gray30"))
        self.delay_label.pack(anchor="w")
        
        # デバッグモード
        self.debug = tk.BooleanVar()
        debug_check = ctk.CTkCheckBox(detail_frame, text="🐛 Debug Mode (Verbose logging)", 
                                     variable=self.debug,
                                     command=self.update_preview)
        debug_check.pack(padx=20, pady=(10, 15), anchor="w")
        
        # プレビュー表示
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(preview_frame, text="👁️ Preview", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))
        
        self.preview_label = ctk.CTkLabel(preview_frame, 
                                         text="Configuration preview will appear here",
                                         font=ctk.CTkFont(size=11),
                                         text_color=("blue", "lightblue"),
                                         wraplength=500)
        self.preview_label.pack(padx=20, pady=(0, 15))
        
        # ボタンフレーム
        button_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=20)
        
        # テストボタン
        test_btn = ctk.CTkButton(button_frame, text="🧪 Test Focus", 
                                font=ctk.CTkFont(size=14, weight="bold"),
                                height=40,
                                fg_color=("orange", "darkorange"),
                                hover_color=("darkorange", "orange"),
                                command=self.test_focus)
        test_btn.pack(side="left", padx=(0, 10), fill="x", expand=True)
        
        # 保存ボタン
        save_btn = ctk.CTkButton(button_frame, text="💾 Save & Apply", 
                                font=ctk.CTkFont(size=14, weight="bold"),
                                height=40,
                                fg_color=("green", "darkgreen"),
                                hover_color=("darkgreen", "green"),
                                command=self.save_config)
        save_btn.pack(side="left", padx=(5, 5), fill="x", expand=True)
        
        # キャンセルボタン
        cancel_btn = ctk.CTkButton(button_frame, text="❌ Cancel", 
                                  font=ctk.CTkFont(size=14, weight="bold"),
                                  height=40,
                                  fg_color=("gray", "darkgray"),
                                  hover_color=("darkgray", "gray"),
                                  command=self.dialog.destroy)
        cancel_btn.pack(side="right", padx=(5, 0), fill="x", expand=True)
    
    def load_current_config(self):
        """現在の設定を読み込み"""
        config = self.config_manager.config
        if not config or "focusRestore" not in config:
            return
        
        focus_data = config["focusRestore"]
        self.enabled.set(focus_data.get("enabled", True))
        self.method.set(focus_data.get("method", "enhanced"))
        self.delay.set(focus_data.get("delay", 50))
        self.debug.set(focus_data.get("debug", False))
        
        # タイミング設定の読み込み
        timing_data = config.get("timing", {})
        self.focus_wait.set(str(timing_data.get("focusRestoreWait", 100)))
        self.verify_wait.set(str(timing_data.get("focusVerifyWait", 80)))
        self.key_delay.set(str(timing_data.get("keyPressDelay", 20)))
        self.max_retries.set(str(timing_data.get("maxFocusRetries", 3)))
        self.retry_delay.set(str(timing_data.get("retryDelay", 50)))
        
        self.update_preview()
    
    def update_preview(self, *args):
        """プレビュー更新"""
        if self.enabled.get():
            method_desc = {
                "simple": "Simple SetForegroundWindow call",
                "enhanced": "Alt-key assisted focus switching",
                "force": "Multiple methods with fallback"
            }
            
            # タイミング設定の取得
            focus_wait = self.focus_wait.get() if hasattr(self, 'focus_wait') else "100"
            verify_wait = self.verify_wait.get() if hasattr(self, 'verify_wait') else "80"
            key_delay = self.key_delay.get() if hasattr(self, 'key_delay') else "20"
            max_retries = self.max_retries.get() if hasattr(self, 'max_retries') else "3"
            retry_delay = self.retry_delay.get() if hasattr(self, 'retry_delay') else "50"
            
            preview_text = f"""✅ Focus Restore Enabled
Method: {self.method.get().upper()} ({method_desc.get(self.method.get(), "Unknown")})
Delay: {self.delay.get()}ms | Debug: {'ON' if self.debug.get() else 'OFF'}

⏱️ Timing Settings:
Focus Wait: {focus_wait}ms | Verify: {verify_wait}ms | Key Delay: {key_delay}ms
Retries: {max_retries} | Retry Delay: {retry_delay}ms

When a hotkey is pressed, the system will attempt to restore focus to the previously active window using the selected method."""
        else:
            preview_text = "❌ Focus Restore Disabled\n\nFocus will not be restored after key sending."
        
        self.preview_label.configure(text=preview_text)
        self.delay_label.configure(text=f"{self.delay.get()}ms")
    
    def test_focus(self):
        """フォーカステスト"""
        # テスト用の一時的な設定を作成
        test_config = FocusConfig(
            enabled=self.enabled.get(),
            method=FocusRestoreMethod(self.method.get()),
            delay=self.delay.get(),
            debug=True  # テスト時は常にデバッグモード
        )
        
        # 一時的なFocusManagerを作成
        temp_focus_manager = FocusManager(test_config)
        
        # 現在のアクティブウィンドウを取得
        try:
            current_window = win32gui.GetForegroundWindow()
            if current_window:
                # テスト実行
                success = temp_focus_manager.restore_focus(current_window)
                
                # 結果表示
                result_dialog = ctk.CTkToplevel(self.dialog)
                result_dialog.title("🧪 Test Result")
                result_dialog.geometry("350x200")
                result_dialog.attributes('-topmost', True)
                result_dialog.transient(self.dialog)
                
                icon = "✅" if success else "❌"
                result_text = "成功" if success else "失敗"
                color = ("green", "lightgreen") if success else ("red", "pink")
                
                ctk.CTkLabel(result_dialog, 
                            text=f"{icon}\n\nFocus Restore Test:\n{result_text}",
                            font=ctk.CTkFont(size=16, weight="bold"),
                            text_color=color,
                            justify="center").pack(expand=True)
                
                ctk.CTkButton(result_dialog, text="OK", 
                             command=result_dialog.destroy).pack(pady=20)
            else:
                raise Exception("No active window found")
                
        except Exception as e:
            # エラー表示
            error_dialog = ctk.CTkToplevel(self.dialog)
            error_dialog.title("❌ Error")
            error_dialog.geometry("350x200")
            error_dialog.attributes('-topmost', True)
            error_dialog.transient(self.dialog)
            
            ctk.CTkLabel(error_dialog, 
                        text=f"❌\n\nTest failed:\n{str(e)}",
                        font=ctk.CTkFont(size=16),
                        justify="center").pack(expand=True)
            
            ctk.CTkButton(error_dialog, text="OK", 
                         command=error_dialog.destroy).pack(pady=20)
    
    def save_config(self):
        """設定を保存"""
        try:
            config = self.config_manager.config
            
            # フォーカス設定保存
            config["focusRestore"] = {
                "enabled": self.enabled.get(),
                "method": self.method.get(),
                "delay": self.delay.get(),
                "debug": self.debug.get()
            }
            
            # タイミング設定保存
            try:
                config["timing"] = {
                    "focusRestoreWait": int(self.focus_wait.get()) if hasattr(self, 'focus_wait') else 100,
                    "focusVerifyWait": int(self.verify_wait.get()) if hasattr(self, 'verify_wait') else 80,
                    "keyPressDelay": int(self.key_delay.get()) if hasattr(self, 'key_delay') else 20,
                    "maxFocusRetries": int(self.max_retries.get()) if hasattr(self, 'max_retries') else 3,
                    "retryDelay": int(self.retry_delay.get()) if hasattr(self, 'retry_delay') else 50
                }
            except ValueError:
                # 無効な値が入力された場合はデフォルト値を使用
                config["timing"] = {
                    "focusRestoreWait": 100,
                    "focusVerifyWait": 80,
                    "keyPressDelay": 20,
                    "maxFocusRetries": 3,
                    "retryDelay": 50
                }
            
            # 設定を保存
            if self.config_manager.save_config(config):
                # コールバック実行（フォーカス設定を再読み込み）
                if self.callback:
                    self.callback()
                
                # 成功メッセージ
                success_dialog = ctk.CTkToplevel(self.dialog)
                success_dialog.title("✅ Success")
                success_dialog.geometry("300x150")
                success_dialog.attributes('-topmost', True)
                success_dialog.transient(self.dialog)
                
                ctk.CTkLabel(success_dialog, 
                            text="✅\n\nFocus configuration saved successfully!",
                            font=ctk.CTkFont(size=16),
                            justify="center").pack(expand=True)
                
                def close_all():
                    success_dialog.destroy()
                    self.dialog.destroy()
                
                ctk.CTkButton(success_dialog, text="OK", 
                             command=close_all).pack(pady=10)
                
                # 2秒後に自動で閉じる
                success_dialog.after(2000, close_all)
            else:
                raise Exception("Failed to save configuration file")
                
        except Exception as e:
            # エラーメッセージ
            error_dialog = ctk.CTkToplevel(self.dialog)
            error_dialog.title("❌ Error")
            error_dialog.geometry("300x150")
            error_dialog.attributes('-topmost', True)
            error_dialog.transient(self.dialog)
            
            ctk.CTkLabel(error_dialog, 
                        text=f"❌\n\nSave failed:\n{str(e)}",
                        font=ctk.CTkFont(size=16),
                        justify="center").pack(expand=True)
            
            ctk.CTkButton(error_dialog, text="OK", 
                         command=error_dialog.destroy).pack(pady=10)
            
            logger.error(f"Error saving focus config: {e}")
    
    def auto_resize_dialog(self):
        """ダイアログサイズを自動調整"""
        self.dialog.update_idletasks()
        self.dialog.geometry("650x800")
        
        # 画面中央に配置
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        # 初期サイズをより柔軟に（後で自動調整される）
        initial_width = 650
        initial_height = min(800, screen_height - 100)  # 画面に収まるサイズ
        x = (screen_width - initial_width) // 2
        y = (screen_height - initial_height) // 2
        self.dialog.geometry(f"{initial_width}x{initial_height}+{x}+{y}")


class FloatingKeypadConfigDialog:
    """フローティングキーパッド設定ダイアログ（軽量化版）"""
    
    def __init__(self, parent, config_manager: IConfigManager, callback=None):
        try:
            self.config_manager = config_manager
            self.callback = callback
            
            # ダイアログ作成
            self.dialog = ctk.CTkToplevel(parent)
                
            self.dialog.configure(fg_color="#f8f9fa")
            self.dialog.title("🎹 Floating Keypad Configuration")
            self.dialog.attributes('-topmost', True)
            
            # リサイズを初期段階で有効化
            self.dialog.resizable(True, True)
            
            # モーダルダイアログにする
            self.dialog.transient(parent)
            self.dialog.grab_set()
            
            # 変数の初期化（UI作成前に実行）
            self.display_mode = None
            self.show_titlebar = None
            self.dark_mode = None
            self.show_on_startup = None
            self.layout_direction = None
            self.delay_time = None
            self.tooltip_mode = None
            self.buttons_per_row = None
            self.button_width = None
            self.button_height = None
            
            # ダイアログの基本設定
            self.setup_dialog()
            self.load_current_config()
            
            # 初期化時のみ固定サイズを設定
            self.auto_resize_dialog()
            
            logger.info("FloatingKeypadConfigDialog initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing FloatingKeypadConfigDialog: {e}")
            # エラー時もダイアログを表示しようとする
            try:
                if hasattr(self, 'dialog'):
                    self.dialog.destroy()
            except:
                pass
            raise
    
    
    def setup_dialog(self):
        """ダイアログUI設定 - ディーター・ラムス風ミニマルデザイン"""
        
        # 背景を純白に設定（ラムス風）
        self.dialog.configure(fg_color="#ffffff")
        
        # メインコンテナ - 余白を控えめに
        container = ctk.CTkFrame(self.dialog, fg_color="#ffffff", corner_radius=0)
        container.pack(fill="both", expand=True, padx=32, pady=24)
        
        # 90%幅のラッパーで3ペインを中央配置
        wrapper_frame = ctk.CTkFrame(container, fg_color="transparent")
        wrapper_frame.pack(expand=True, fill="both", padx=16, pady=(16, 0))
        
        # ラッパー内で中央配置用のグリッド設定
        wrapper_frame.grid_columnconfigure(0, weight=1)  # 左の空白
        wrapper_frame.grid_columnconfigure(1, weight=0)  # コンテンツに合わせて自動サイズ
        wrapper_frame.grid_columnconfigure(2, weight=1)  # 右の空白
        wrapper_frame.grid_rowconfigure(0, weight=1)
        
        # メインコンテンツエリア - 3ペイン横長レイアウト（コンテンツ幅に合わせて）
        content_frame = ctk.CTkFrame(wrapper_frame, fg_color="transparent")
        content_frame.grid(row=0, column=1, sticky="n")  # 上寄せで自動幅
        
        # 1列グリッド設定 - Behaviorペインのみ表示
        content_frame.grid_columnconfigure(0, weight=1)
        
        # コンテンツフレーム全体の幅を110pxに固定
        content_frame.configure(width=110)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # 左ペイン：外観設定
        self._setup_basic_pane(content_frame, 0)
        
        # 中央ペイン：動作設定
        self._setup_advanced_pane(content_frame, 0)
        
        # 右ペイン：寸法設定
        self._setup_dimensions_pane(content_frame, 2)
        
        # フッター - 最小限のアクション
        self._setup_footer(container)
    
    def _setup_dimensions_pane(self, parent, column):
        """右ペイン：寸法設定（非表示）"""
        pane_frame = ctk.CTkFrame(parent, fg_color="transparent")
        # grid() をコメントアウトして非表示
        # pane_frame.grid(row=0, column=column, sticky="nw")
        
        # 変数の初期化（関数は動作するように残す）
        self.buttons_per_row = tk.IntVar(value=3)
        self.button_width = tk.IntVar(value=60)
        self.button_height = tk.IntVar(value=60)
        self.icon_size = tk.IntVar(value=32)
        
    def _setup_basic_pane(self, parent, column):
        """左ペイン：外観設定（非表示）"""
        pane_frame = ctk.CTkFrame(parent, fg_color="transparent")
        # grid() をコメントアウトして非表示
        # pane_frame.grid(row=0, column=column, sticky="nw")
        
        # 内部設定変数の初期化（関数は動作するように残す）
        self.display_mode = tk.StringVar(value="mini")
        self.show_titlebar = tk.BooleanVar(value=True)
        self.dark_mode = tk.BooleanVar(value=False)
        self.show_on_startup = tk.BooleanVar(value=False)
        
    def _setup_advanced_pane(self, parent, column):
        """中央ペイン：動作設定（InputDelayのみ表示）"""
        pane_frame = ctk.CTkFrame(parent, fg_color="transparent")
        pane_frame.grid(row=0, column=column, sticky="nw")
        
        # ペインタイトル
        title_label = ctk.CTkLabel(pane_frame,
                                  text="Behavior",
                                  font=ctk.CTkFont(family="Meiryo UI", size=16, weight="bold"),
                                  text_color="#000000")
        title_label.pack(anchor="w", pady=(0, 20))
        
        # レイアウト方向設定（非表示、変数初期化のみ）
        self.layout_direction = tk.StringVar(value="horizontal")
        
        # 入力遅延設定（これだけ表示）
        self._create_delay_settings(pane_frame)
        
        # ツールチップ設定（非表示、変数初期化のみ）
        self.tooltip_mode = tk.StringVar(value="both")
    
    def _create_pane_input(self, parent, label, var_name, default_value):
        """ペイン用数値入力"""
        label_widget = ctk.CTkLabel(parent,
                                   text=label,
                                   font=ctk.CTkFont(family="Meiryo UI", size=14, weight="normal"),
                                   text_color="#333333")
        label_widget.pack(anchor="w", pady=(0, 6))
        
        var = tk.IntVar(value=default_value)
        setattr(self, var_name, var)
        
        entry = ctk.CTkEntry(parent,
                            textvariable=var,
                            width=100,
                            height=32,
                            font=ctk.CTkFont(family="Yu Gothic UI", size=14, weight="normal"),
                            fg_color="#ffffff",
                            text_color="#000000",
                            border_color="#e0e0e0",
                            border_width=1,
                            corner_radius=3)
        entry.pack(anchor="w", pady=(0, 20))
        entry.bind('<KeyRelease>', lambda e: self._on_layout_changed())
    
    def _create_size_input_vertical(self, parent, label):
        """アイコンサイズ入力のみ（未使用だが互換性のため残す）"""
        # この関数は呼び出されないため、icon_sizeの重複定義を避ける
        pass
    
    def _create_radio_group(self, parent, label, var_name, default_value, options):
        """ラジオボタングループ"""
        label_widget = ctk.CTkLabel(parent,
                                   text=label,
                                   font=ctk.CTkFont(family="Meiryo UI", size=14, weight="normal"),
                                   text_color="#333333")
        label_widget.pack(anchor="w", pady=(0, 6))
        
        var = tk.StringVar(value=default_value)
        setattr(self, var_name, var)
        
        for text, value in options:
            radio = ctk.CTkRadioButton(parent,
                                      text=text,
                                      variable=var,
                                      value=value,
                                      font=ctk.CTkFont(family="Meiryo UI", size=13, weight="normal"),
                                      text_color="#000000",
                                      fg_color="#007aff",
                                      command=self._on_option_changed)
            radio.pack(anchor="w", pady=(0, 6))
        
        # グループ間のスペース
        spacer = ctk.CTkFrame(parent, fg_color="transparent", height=14)
        spacer.pack(fill="x")
    
    def _create_delay_settings(self, parent):
        """遅延設定"""
        label_widget = ctk.CTkLabel(parent,
                                   text="Input delay",
                                   font=ctk.CTkFont(family="Meiryo UI", size=14, weight="normal"),
                                   text_color="#333333")
        label_widget.pack(anchor="w", pady=(0, 6))
        
        # 遅延を有効にするチェックボックスは削除
        self.delay_input_mode = tk.BooleanVar(value=True)  # 常に有効
        
        # 遅延時間
        time_label = ctk.CTkLabel(parent,
                                 text="遅延時間 (ms)",
                                 font=ctk.CTkFont(family="Meiryo UI", size=13, weight="normal"),
                                 text_color="#555555")
        time_label.pack(anchor="w", pady=(0, 2))
        
        self.delay_time = tk.IntVar(value=100)
        delay_entry = ctk.CTkEntry(parent,
                                  textvariable=self.delay_time,
                                  width=100,
                                  height=28,
                                  font=ctk.CTkFont(family="Meiryo UI", size=14, weight="normal"),
                                  fg_color="#ffffff",
                                  text_color="#000000",
                                  border_color="#e0e0e0",
                                  border_width=1,
                                  corner_radius=3)
        delay_entry.pack(anchor="w", pady=(0, 20))
        delay_entry.bind('<KeyRelease>', lambda e: self._on_option_changed())
    
    def _setup_footer(self, parent):
        """フッター - ラムス風のミニマルなアクション"""
        
        footer_frame = ctk.CTkFrame(parent, fg_color="transparent", height=60)
        footer_frame.pack(fill="x", side="bottom", pady=(32, 0))
        footer_frame.pack_propagate(False)
        
        # 左側ボタン - エクスポート（非表示）
        # left_button_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        # left_button_frame.pack(side="left")
        
        # # エクスポートボタン
        # export_btn = ctk.CTkButton(left_button_frame,
        #                           text="設定を書き出し ▼",
        #                           font=ctk.CTkFont(family="Meiryo UI", size=14, weight="normal"),
        #                           width=130,
        #                           height=32,
        #                           fg_color="transparent",
        #                           text_color="#666666",
        #                           hover_color="#f5f5f5",
        #                           border_color="#e0e0e0",
        #                           border_width=1,
        #                           corner_radius=2,
        #                           command=self._show_export_menu)
        # export_btn.pack(side="left", padx=(0, 10))
        
        # # インポートボタン
        # import_btn = ctk.CTkButton(left_button_frame,
        #                           text="設定を読み込み ▼",
        #                           font=ctk.CTkFont(family="Meiryo UI", size=14, weight="normal"),
        #                           width=130,
        #                           height=32,
        #                           fg_color="transparent",
        #                           text_color="#666666",
        #                           hover_color="#f5f5f5",
        #                           border_color="#e0e0e0",
        #                           border_width=1,
        #                           corner_radius=2,
        #                           command=self._show_import_menu)
        # import_btn.pack(side="left")
        
        # 右側ボタングループ - 保存・キャンセル
        button_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        button_frame.pack(side="right")
        
        # キャンセルボタン - 控えめ
        cancel_btn = ctk.CTkButton(button_frame,
                                  text="キャンセル",
                                  font=ctk.CTkFont(family="Meiryo UI", size=14, weight="normal"),
                                  width=80,
                                  height=32,
                                  fg_color="transparent",
                                  text_color="#666666",
                                  hover_color="#f5f5f5",
                                  border_color="#e0e0e0",
                                  border_width=1,
                                  corner_radius=2,
                                  command=self._on_closing)
        cancel_btn.pack(side="left", padx=(0, 12))
        
        # 保存ボタン - プライマリーアクション
        save_btn = ctk.CTkButton(button_frame,
                                text="保存",
                                font=ctk.CTkFont(family="Meiryo UI", size=14, weight="bold"),
                                width=80,
                                height=32,
                                fg_color="#007aff",
                                hover_color="#0056d6",
                                corner_radius=2,
                                command=self.save_config)
        save_btn.pack(side="left")
    
    def auto_resize_dialog(self):
        """ダイアログサイズを調整 - コンテンツに基づく自動サイズ計算"""
        self.dialog.update_idletasks()
        
        # コンテンツの実際のサイズを計算
        self.dialog.update_idletasks()
        required_width = self.dialog.winfo_reqwidth()
        required_height = self.dialog.winfo_reqheight()
        
        # 3ペイン横長レイアウトに適切なサイズを設定
        optimal_width = 750  # 3ペインに最適なサイズ
        optimal_height = 550  # 各設定項目が余裕をもって表示される高さ
        
        # 最適なサイズを使用（コンテンツサイズは参考程度）
        width = optimal_width
        height = optimal_height
        
        # 画面サイズの80%を上限とする
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        width = min(width, int(screen_width * 0.8))
        height = min(height, int(screen_height * 0.8))
        
        # ウィンドウサイズを設定
        self.dialog.geometry(f"{width}x{height}")
        
        # 画面中央に配置
        self.dialog.update_idletasks()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def _show_export_menu(self):
        """エクスポート選択メニューを表示"""
        try:
            # メニューダイアログ
            menu_dialog = ctk.CTkToplevel(self.dialog)
            menu_dialog.title("書き出し設定を選択")
            menu_dialog.geometry("300x200")
            menu_dialog.attributes('-topmost', True)
            menu_dialog.transient(self.dialog)
            
            
            # ボタンフレーム
            button_frame = ctk.CTkFrame(menu_dialog, fg_color="transparent")
            button_frame.pack(expand=True, fill="both", padx=20, pady=10)
            
            # 全設定ボタン
            full_btn = ctk.CTkButton(button_frame,
                                    text="📋 全設定を書き出し\n（レイアウト + ボタン内容）",
                                    font=ctk.CTkFont(family="Meiryo UI", size=13),
                                    width=200,
                                    height=50,
                                    fg_color="#007aff",
                                    hover_color="#0056d6",
                                    command=lambda: [menu_dialog.destroy(), self._export_full_config()])
            full_btn.pack(pady=(0, 10))
            
            # ボタンのみボタン
            buttons_btn = ctk.CTkButton(button_frame,
                                       text="🔘 ボタン内容のみを書き出し\n（アイコン・キー・ラベル等）",
                                       font=ctk.CTkFont(family="Meiryo UI", size=13),
                                       width=200,
                                       height=50,
                                       fg_color="#28a745",
                                       hover_color="#1e7e34",
                                       command=lambda: [menu_dialog.destroy(), self._export_buttons_only()])
            buttons_btn.pack(pady=(0, 10))
            
            # キャンセルボタン
            cancel_btn = ctk.CTkButton(button_frame,
                                      text="キャンセル",
                                      font=ctk.CTkFont(family="Meiryo UI", size=12),
                                      width=100,
                                      height=30,
                                      fg_color="transparent",
                                      text_color="#666666",
                                      hover_color="#f5f5f5",
                                      border_color="#e0e0e0",
                                      border_width=1,
                                      command=menu_dialog.destroy)
            cancel_btn.pack()
            
        except Exception as e:
            logger.error(f"Error showing export menu: {e}")
    
    def _export_buttons_only(self):
        """ボタン内容のみを書き出し"""
        try:
            from tkinter import filedialog
            import json
            from datetime import datetime
            
            # ボタン設定のみを取得
            full_config = self.config_manager.config
            buttons_data = []
            
            if full_config and 'floatingWindow' in full_config:
                floating_config = full_config['floatingWindow']
                if 'buttons' in floating_config:
                    buttons_data = floating_config['buttons']
            
            if not buttons_data:
                # ボタンが存在しない場合のメッセージ
                error_dialog = ctk.CTkToplevel(self.dialog)
                error_dialog.title("⚠️ 警告")
                error_dialog.geometry("300x150")
                error_dialog.attributes('-topmost', True)
                error_dialog.transient(self.dialog)
                
                ctk.CTkLabel(error_dialog, 
                            text="⚠️\n\n書き出すボタン設定が\n見つかりません",
                            font=ctk.CTkFont(family="Meiryo UI", size=14),
                            justify="center").pack(expand=True)
                
                ctk.CTkButton(error_dialog, text="OK",
                             font=ctk.CTkFont(family="Meiryo UI", size=12), 
                             command=error_dialog.destroy).pack(pady=10)
                return
            
            # エクスポートデータを作成
            export_data = {
                "exportedAt": datetime.now().isoformat(),
                "version": "1.0",
                "exportType": "buttons_only",
                "buttonSettings": buttons_data
            }
            
            # ファイル選択ダイアログ
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="ボタン設定を書き出し"
            )
            
            if filename:
                # ファイルに保存
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                # 成功メッセージ
                success_dialog = ctk.CTkToplevel(self.dialog)
                success_dialog.title("✅ 成功")
                success_dialog.geometry("400x180")
                success_dialog.attributes('-topmost', True)
                success_dialog.transient(self.dialog)
                
                message = f"✅\n\nボタン設定を書き出しました\n（{len(buttons_data)} 個のボタン）\n\n{filename}"
                
                ctk.CTkLabel(success_dialog, 
                            text=message,
                            font=ctk.CTkFont(family="Meiryo UI", size=14),
                            justify="center").pack(expand=True)
                
                ctk.CTkButton(success_dialog, text="OK", 
                             font=ctk.CTkFont(family="Meiryo UI", size=12),
                             command=success_dialog.destroy).pack(pady=10)
                
        except Exception as e:
            # エラーメッセージ
            error_dialog = ctk.CTkToplevel(self.dialog)
            error_dialog.title("❌ エラー")
            error_dialog.geometry("300x150")
            error_dialog.attributes('-topmost', True)
            error_dialog.transient(self.dialog)
            
            ctk.CTkLabel(error_dialog, 
                        text=f"❌\n\nボタン書き出しに失敗:\n{str(e)}",
                        font=ctk.CTkFont(family="Meiryo UI", size=14),
                        justify="center").pack(expand=True)
            
            ctk.CTkButton(error_dialog, text="OK",
                         font=ctk.CTkFont(family="Meiryo UI", size=12), 
                         command=error_dialog.destroy).pack(pady=10)
            
            logger.error(f"Error exporting buttons only: {e}")
    
    def _export_full_config(self):
        """設定をファイルに書き出し"""
        try:
            from tkinter import filedialog
            import json
            from datetime import datetime
            
            # 現在の設定を取得
            current_config = {}
            if hasattr(self, 'buttons_per_row'):
                current_config['buttonsPerRow'] = self.buttons_per_row.get()
            if hasattr(self, 'icon_size'):
                current_config['iconSize'] = self.icon_size.get()
            if hasattr(self, 'show_titlebar'):
                current_config['showTitlebar'] = self.show_titlebar.get()
            if hasattr(self, 'dark_mode'):
                current_config['darkMode'] = self.dark_mode.get()
            if hasattr(self, 'show_on_startup'):
                current_config['showOnStartup'] = self.show_on_startup.get()
            if hasattr(self, 'layout_direction'):
                current_config['layoutDirection'] = self.layout_direction.get()
            if hasattr(self, 'delay_time'):
                current_config['delayTime'] = self.delay_time.get()
            if hasattr(self, 'tooltip_mode'):
                current_config['tooltipMode'] = self.tooltip_mode.get()
            
            # 完全な設定ファイルから追加情報を取得
            full_config = self.config_manager.config
            if full_config and 'floatingWindow' in full_config:
                floating_config = full_config['floatingWindow']
                
                # ボタン設定を含める
                if 'buttons' in floating_config:
                    current_config['buttons'] = floating_config['buttons']
                
                # 表示モードを含める
                if 'displayMode' in floating_config:
                    current_config['displayMode'] = floating_config['displayMode']
                
                # その他の設定も含める
                if 'delayInputMode' in floating_config:
                    current_config['delayInputMode'] = floating_config['delayInputMode']
            
            # エクスポートデータを作成
            export_data = {
                "exportedAt": datetime.now().isoformat(),
                "version": "1.0",
                "exportType": "full_config",
                "floatingKeypadSettings": current_config
            }
            
            # ファイル選択ダイアログ
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="設定を書き出し"
            )
            
            if filename:
                # ファイルに保存
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                # ボタン数を計算
                button_count = 0
                if 'buttons' in current_config:
                    button_count = len(current_config['buttons'])
                
                # 成功メッセージ
                success_dialog = ctk.CTkToplevel(self.dialog)
                success_dialog.title("✅ 成功")
                success_dialog.geometry("400x180")
                success_dialog.attributes('-topmost', True)
                success_dialog.transient(self.dialog)
                
                message = f"✅\n\n設定を書き出しました"
                if button_count > 0:
                    message += f"\n（ボタン設定 {button_count} 個を含む）"
                message += f"\n\n{filename}"
                
                ctk.CTkLabel(success_dialog, 
                            text=message,
                            font=ctk.CTkFont(family="Meiryo UI", size=14),
                            justify="center").pack(expand=True)
                
                ctk.CTkButton(success_dialog, text="OK", 
                             font=ctk.CTkFont(family="Meiryo UI", size=12),
                             command=success_dialog.destroy).pack(pady=10)
                
        except Exception as e:
            # エラーメッセージ
            error_dialog = ctk.CTkToplevel(self.dialog)
            error_dialog.title("❌ エラー")
            error_dialog.geometry("300x150")
            error_dialog.attributes('-topmost', True)
            error_dialog.transient(self.dialog)
            
            ctk.CTkLabel(error_dialog, 
                        text=f"❌\n\n書き出しに失敗しました:\n{str(e)}",
                        font=ctk.CTkFont(family="Meiryo UI", size=14),
                        justify="center").pack(expand=True)
            
            ctk.CTkButton(error_dialog, text="OK",
                         font=ctk.CTkFont(family="Meiryo UI", size=12), 
                         command=error_dialog.destroy).pack(pady=10)
            
            logger.error(f"Error exporting config: {e}")
    
    def _on_closing(self):
        """ダイアログ終了処理"""
        try:
            self.dialog.grab_release()
            self.dialog.destroy()
        except Exception as e:
            logger.error(f"Error during dialog closing: {e}")
    
    def _on_option_changed(self):
        """オプション変更時の処理"""
        try:
            self._apply_options_immediately()
        except Exception as e:
            logger.error(f"Error applying option changes: {e}")
    
    def _on_layout_changed(self):
        """レイアウト設定変更時の処理"""
        try:
            self._apply_layout_immediately()
        except Exception as e:
            logger.error(f"Error applying layout changes: {e}")
    
    def _apply_options_immediately(self):
        """オプション設定の即時保存"""
        try:
            config = self.config_manager.config
            if not config:
                config = {}
                
            if 'floatingWindow' not in config:
                config['floatingWindow'] = {
                    "enabled": True,
                    "position": {"x": 100, "y": 100}
                }
            
            config['floatingWindow']['showTitlebar'] = self.show_titlebar.get()
            config['floatingWindow']['darkMode'] = self.dark_mode.get() 
            config['floatingWindow']['showOnStartup'] = self.show_on_startup.get()
            config['floatingWindow']['layoutDirection'] = self.layout_direction.get()
            config['floatingWindow']['delayInputMode'] = self.delay_input_mode.get()
            # delay_timeが存在する場合のみ保存
            if hasattr(self, 'delay_time') and self.delay_time:
                config['floatingWindow']['delayTime'] = self.delay_time.get()
            config['floatingWindow']['tooltipMode'] = self.tooltip_mode.get()
            
            self.config_manager.save_config(config)
            # フローティングウィンドウに即座反映
            self._update_floating_keyboard()
            logger.info("Options applied immediately")
            
        except Exception as e:
            logger.error(f"Error applying options immediately: {e}")
    
    def _apply_layout_immediately(self):
        """レイアウト設定の即時保存"""
        try:
            config = self.config_manager.config
            if not config:
                config = {}
                
            if 'floatingWindow' not in config:
                config['floatingWindow'] = {
                    "enabled": True,
                    "position": {"x": 100, "y": 100}
                }
            
            if 'layout' not in config['floatingWindow']:
                config['floatingWindow']['layout'] = {}
            
            # buttons_per_rowが存在する場合のみ保存
            if hasattr(self, 'buttons_per_row') and self.buttons_per_row:
                config['floatingWindow']['layout']['buttonsPerRow'] = self.buttons_per_row.get()
            # icon_sizeが存在する場合のみ保存
            if hasattr(self, 'icon_size') and self.icon_size:
                config['floatingWindow']['layout']['iconSize'] = self.icon_size.get()
            
            self.config_manager.save_config(config)
            # フローティングウィンドウに即座反映
            self._update_floating_keyboard()
            logger.info("Layout settings applied immediately")
            
        except Exception as e:
            logger.error(f"Error applying layout immediately: {e}")
    
    def load_current_config(self):
        """現在の設定を読み込み"""
        try:
            config = self.config_manager.config
            if config and 'floatingWindow' in config:
                floating_config = config['floatingWindow']
                
                # 基本設定
                self.show_titlebar.set(floating_config.get('showTitlebar', True))
                self.dark_mode.set(floating_config.get('darkMode', False))
                self.show_on_startup.set(floating_config.get('showOnStartup', False))
                
                # 高度な設定
                self.layout_direction.set(floating_config.get('layoutDirection', 'horizontal'))
                self.delay_input_mode.set(floating_config.get('delayInputMode', False))
                self.delay_time.set(floating_config.get('delayTime', 100))
                self.tooltip_mode.set(floating_config.get('tooltipMode', 'both'))
                
                # レイアウト設定
                layout_config = floating_config.get('layout', {})
                self.buttons_per_row.set(layout_config.get('buttonsPerRow', 3))
                self.icon_size.set(layout_config.get('iconSize', 32))
            else:
                # デフォルト値を設定
                self._set_default_values()
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self._set_default_values()
    
    def _set_default_values(self):
        """デフォルト値を設定"""
        self.show_titlebar.set(True)
        self.dark_mode.set(False)
        self.show_on_startup.set(False)
        self.layout_direction.set('horizontal')
        self.delay_input_mode.set(False)
        self.delay_time.set(100)
        self.tooltip_mode.set('both')
        self.buttons_per_row.set(3)
        self.icon_size.set(32)
    
    def _show_import_menu(self):
        """インポート選択メニューを表示"""
        try:
            # メニューダイアログ
            menu_dialog = ctk.CTkToplevel(self.dialog)
            menu_dialog.title("読み込み設定を選択")
            menu_dialog.geometry("300x220")
            menu_dialog.attributes('-topmost', True)
            menu_dialog.transient(self.dialog)
            
            
            # ボタンフレーム
            button_frame = ctk.CTkFrame(menu_dialog, fg_color="transparent")
            button_frame.pack(expand=True, fill="both", padx=20, pady=10)
            
            # 全設定ボタン
            full_btn = ctk.CTkButton(button_frame,
                                    text="📂 全設定を読み込み\n（レイアウト + ボタン内容）",
                                    font=ctk.CTkFont(family="Meiryo UI", size=13),
                                    width=200,
                                    height=50,
                                    fg_color="#007aff",
                                    hover_color="#0056d6",
                                    command=lambda: [menu_dialog.destroy(), self._import_full_config()])
            full_btn.pack(pady=(0, 10))
            
            # ボタンのみボタン
            buttons_btn = ctk.CTkButton(button_frame,
                                       text="🔘 ボタン内容のみを読み込み\n（アイコン・キー・ラベル等）",
                                       font=ctk.CTkFont(family="Meiryo UI", size=13),
                                       width=200,
                                       height=50,
                                       fg_color="#28a745",
                                       hover_color="#1e7e34",
                                       command=lambda: [menu_dialog.destroy(), self._import_buttons_only()])
            buttons_btn.pack(pady=(0, 10))
            
            # キャンセルボタン
            cancel_btn = ctk.CTkButton(button_frame,
                                      text="キャンセル",
                                      font=ctk.CTkFont(family="Meiryo UI", size=12),
                                      width=100,
                                      height=32,
                                      fg_color="transparent",
                                      text_color="#666666",
                                      hover_color="#f5f5f5",
                                      border_color="#e0e0e0",
                                      border_width=1,
                                      command=menu_dialog.destroy)
            cancel_btn.pack()
            
            # ダイアログを中央に配置
            menu_dialog.update_idletasks()
            x = self.dialog.winfo_x() + (self.dialog.winfo_width() // 2) - 150
            y = self.dialog.winfo_y() + (self.dialog.winfo_height() // 2) - 100
            menu_dialog.geometry(f"300x220+{x}+{y}")
            
        except Exception as e:
            self._show_error_dialog("インポートメニューエラー", f"エラーが発生しました: {str(e)}")
    
    def _import_full_config(self):
        """全設定をインポート"""
        try:
            # ファイル選択ダイアログ
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="全設定ファイルを選択",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                defaultextension=".json"
            )
            
            if not file_path:
                return
                
            # JSONファイルを読み込み
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # フル設定かどうかを確認
            if 'floatingWindow' not in imported_config:
                self._show_error_dialog("インポートエラー", "全設定ファイルではありません。\n正しい設定ファイルを選択してください。")
                return
            
            # 設定を現在のフォームに反映
            self._load_config_to_form(imported_config)
            
            # 成功メッセージ
            self._show_success_dialog("インポート完了", "全設定を正常に読み込みました。\n「保存」ボタンで設定を適用してください。")
            
        except Exception as e:
            self._show_error_dialog("インポートエラー", f"設定の読み込みに失敗しました: {str(e)}")
    
    def _import_buttons_only(self):
        """ボタン内容のみをインポート"""
        try:
            # ファイル選択ダイアログ
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="ボタン設定ファイルを選択",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                defaultextension=".json"
            )
            
            if not file_path:
                return
                
            # JSONファイルを読み込み
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # ボタンデータかどうかを確認
            if 'buttons' in imported_data:
                buttons_data = imported_data['buttons']
            elif isinstance(imported_data, list):
                buttons_data = imported_data
            else:
                self._show_error_dialog("インポートエラー", "ボタン設定ファイルではありません。\n正しいファイルを選択してください。")
                return
            
            # 現在の設定を取得してボタンのみ更新
            current_config = self._get_current_config()
            current_config['floatingWindow']['buttons'] = buttons_data
            
            # フォームに反映
            self._load_config_to_form(current_config)
            
            # 成功メッセージ
            self._show_success_dialog("インポート完了", f"{len(buttons_data)}個のボタン設定を正常に読み込みました。\n「保存」ボタンで設定を適用してください。")
            
        except Exception as e:
            self._show_error_dialog("インポートエラー", f"ボタン設定の読み込みに失敗しました: {str(e)}")
    
    def _load_config_to_form(self, config):
        """設定をフォームに読み込み"""
        try:
            floating_config = config.get('floatingWindow', {})
            
            # 基本設定
            if hasattr(self, 'show_titlebar'):
                self.show_titlebar.set(floating_config.get('showTitlebar', False))
            if hasattr(self, 'dark_mode'):
                self.dark_mode.set(floating_config.get('darkMode', False))
            
            # レイアウト設定
            layout = floating_config.get('layout', {})
            if hasattr(self, 'buttons_per_row'):
                self.buttons_per_row.set(layout.get('buttonsPerRow', 12))
            if hasattr(self, 'icon_size'):
                self.icon_size.set(layout.get('iconSize', 40))
            
            # その他の設定
            if hasattr(self, 'tooltip_mode'):
                self.tooltip_mode.set(floating_config.get('tooltipMode', 'key'))
            if hasattr(self, 'layout_direction'):
                self.layout_direction.set(floating_config.get('layoutDirection', 'horizontal'))
            if hasattr(self, 'display_mode'):
                self.display_mode.set(floating_config.get('displayMode', 'normal'))
            if hasattr(self, 'delay_time'):
                self.delay_time.set(floating_config.get('delayTime', 100))
            
            # フォームの更新を通知
            self._on_option_changed()
            
        except Exception as e:
            self._show_error_dialog("設定反映エラー", f"設定の反映中にエラーが発生しました: {str(e)}")
    
    def save_config(self):
        """設定を保存"""
        try:
            config = self.config_manager.config
            if not config:
                config = {}
            
            if 'floatingWindow' not in config:
                config['floatingWindow'] = {
                    "enabled": True,
                    "position": {"x": 100, "y": 100}
                }
            
            # 設定保存
            config['floatingWindow']['displayMode'] = "mini"  # 固定値
            config['floatingWindow']['showTitlebar'] = self.show_titlebar.get()
            config['floatingWindow']['darkMode'] = self.dark_mode.get()
            config['floatingWindow']['showOnStartup'] = self.show_on_startup.get()
            config['floatingWindow']['layoutDirection'] = self.layout_direction.get()
            config['floatingWindow']['delayInputMode'] = self.delay_input_mode.get()
            # delay_timeが存在する場合のみ保存
            if hasattr(self, 'delay_time') and self.delay_time:
                config['floatingWindow']['delayTime'] = self.delay_time.get()
            config['floatingWindow']['tooltipMode'] = self.tooltip_mode.get()
            
            # レイアウト設定を保存
            if 'layout' not in config['floatingWindow']:
                config['floatingWindow']['layout'] = {}
            # buttons_per_rowが存在する場合のみ保存
            if hasattr(self, 'buttons_per_row') and self.buttons_per_row:
                config['floatingWindow']['layout']['buttonsPerRow'] = self.buttons_per_row.get()
            # icon_sizeが存在する場合のみ保存
            if hasattr(self, 'icon_size') and self.icon_size:
                config['floatingWindow']['layout']['iconSize'] = self.icon_size.get()
            
            if self.config_manager.save_config(config):
                # フローティングウィンドウに反映
                self._update_floating_keyboard()
                
                if self.callback:
                    self.callback()
                # ダイアログを閉じる
                self._on_closing()
            else:
                raise Exception("Failed to save configuration file")
                
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {str(e)}")
            logger.error(f"Error saving floating keypad config: {e}")
    
    def _update_floating_keyboard(self):
        """フローティングキーボードの設定を反映"""
        try:
            import gc
            from virtual_keyboard.ui.floating import FloatingKeyboard
            
            for obj in gc.get_objects():
                if isinstance(obj, FloatingKeyboard) and hasattr(obj, 'window') and obj.window:
                    try:
                        # ダークテーマ設定を即座反映
                        if hasattr(obj, 'dark_mode'):
                            obj.dark_mode = self.dark_mode.get()
                            if obj.dark_mode and hasattr(obj, 'apply_dark_mode'):
                                obj.apply_dark_mode()
                            elif not obj.dark_mode and hasattr(obj, 'apply_light_mode'):
                                obj.apply_light_mode()
                        
                        # レイアウト更新
                        obj.create_buttons()
                        logger.info("Updated floating keyboard layout and theme")
                    except Exception as e:
                        logger.error(f"Error updating floating keyboard: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error updating floating keyboard: {e}")
    
    def schedule_update(self):
        """更新処理（プレースホルダー）"""
        pass
