#!/usr/bin/env python3
"""
Virtual Functions - Floating Window Main Entry Point
フローティングウィンドウ直接起動版
"""

import logging
import sys
import os
import tkinter as tk
import customtkinter as ctk
from logging.handlers import RotatingFileHandler

# ログ設定
rotating_handler = RotatingFileHandler(
    'debug_log.txt', 
    maxBytes=1024*1024,  # 1MB
    backupCount=3,
    encoding='utf-8'
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[rotating_handler]
)
logger = logging.getLogger(__name__)

# コンソールウィンドウの制御
if sys.platform.startswith('win'):
    import win32console
    import win32gui
    import win32con
    import atexit
    
    console_window = None
    try:
        console_window = win32console.GetConsoleWindow()
        if console_window:
            # 起動時にコンソールを非表示にする
            win32gui.ShowWindow(console_window, win32con.SW_HIDE)
            
            def cleanup_console():
                try:
                    if console_window:
                        win32gui.ShowWindow(console_window, 0)
                except:
                    pass
            atexit.register(cleanup_console)
    except:
        pass


class FloatingKeyboardApp:
    """フローティングキーボード専用アプリケーション"""
    
    def __init__(self):
        # CustomTkinter設定
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # 非表示のメインウィンドウ（フローティングウィンドウの親として必要）
        self.root = ctk.CTk()
        self.root.withdraw()  # 非表示にする
        self.root.title("Virtual Functions Controller")
        
        # アイコンを設定
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            logger.debug(f"Could not set icon: {e}")
        
        # 設定とサービスの初期化
        self._initialize_services()
        
        # フローティングウィンドウの作成
        self._create_floating_window()
        
        # ウィンドウ終了時の処理設定
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _initialize_services(self):
        """サービスの初期化"""
        try:
            # 設定管理
            from virtual_keyboard.config.manager import ConfigManager
            self.config_manager = ConfigManager()
            
            # キー送信サービス
            from virtual_keyboard.services.keysender import KeySender
            self.key_sender = KeySender()
            
            # フォーカス管理サービス
            from virtual_keyboard.services.focus import FocusManager
            from virtual_keyboard.core.types import FocusConfig, FocusRestoreMethod
            
            focus_config = FocusConfig(
                enabled=True,
                method=FocusRestoreMethod.ENHANCED,
                delay=10,
                debug=True
            )
            self.focus_manager = FocusManager(focus_config)
            
            # ホットキーサービス
            from virtual_keyboard.services.hotkey import HotkeyManager
            self.hotkey_manager = HotkeyManager()
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _create_floating_window(self):
        """フローティングウィンドウの作成"""
        try:
            from virtual_keyboard.ui.floating import FloatingKeyboard
            
            # フローティングキーボード作成
            self.floating_keyboard = FloatingKeyboard(
                self.root,
                self.config_manager,
                self.key_sender,
                self.focus_manager
            )
            
            # コンテキストメニューのコールバック設定
            self.floating_keyboard.set_context_menu_callback(self._show_context_menu)
            
            # 起動時に自動表示
            self.floating_keyboard.create_window()
            self.floating_keyboard.show()
            
            # 右クリックメニューのバインド設定（ウィンドウ作成後）
            self.root.after(100, self._setup_context_menu_bindings)
            
            # 設定からキー遅延時間を読み込み
            self._load_key_delay_config()
            
            # フォーカス監視開始
            self.focus_manager.start_monitoring()
            
            # ボタン設定管理ウィンドウを自動で開く（コメントアウト）
            # self.root.after(1000, self._auto_open_button_manager)
            
            logger.info("Floating keyboard window created and displayed")
            
        except Exception as e:
            logger.error(f"Failed to create floating window: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _setup_context_menu_bindings(self):
        """右クリックコンテキストメニューのバインド設定"""
        try:
            if hasattr(self.floating_keyboard, 'setup_context_menu_bindings'):
                self.floating_keyboard.setup_context_menu_bindings()
                logger.info("Context menu bindings setup completed")
        except Exception as e:
            logger.error(f"Failed to setup context menu bindings: {e}")
    
    def _load_key_delay_config(self):
        """遅延時間を3秒固定で設定"""
        try:
            # 3秒（3000ms）固定で設定
            fixed_delay = 3000
            self.floating_keyboard.set_key_delay(fixed_delay)
            logger.info(f"Key delay set to fixed value: {fixed_delay}ms (3 seconds)")
        except Exception as e:
            logger.error(f"Failed to set fixed key delay: {e}")
            # エラーの場合でも3秒で設定を試行
            try:
                self.floating_keyboard.set_key_delay(3000)
            except:
                pass
    
    def _show_context_menu(self, event):
        """右クリックコンテキストメニューの表示"""
        try:
            logger.info(f"Main context menu called from {event.widget}")
            # コンテキストメニューの作成
            context_menu = tk.Menu(self.root, tearoff=0)
            
            # ボタン固有のメニュー項目を最初に追加（利用可能な場合）
            if hasattr(event, 'button_key') and hasattr(event, 'button_label'):
                context_menu.add_command(
                    label=f"このボタンの設定 ({event.button_key})",
                    command=lambda: self.floating_keyboard._open_button_config(event.button_key, event.button_label)
                )
                
                context_menu.add_separator()
                
                # ボタン移動メニューを追加（レイアウトに応じて表記を変更）
                current_layout = self.config_manager.config.get('floatingWindow', {}).get('layoutDirection', 'horizontal')
                if current_layout == "vertical":
                    # 縦レイアウトの場合は上下移動
                    context_menu.add_command(
                        label="▲ 上に移動",
                        command=lambda: self._move_button(event.button_key, -1)
                    )
                    context_menu.add_command(
                        label="▼ 下に移動",
                        command=lambda: self._move_button(event.button_key, 1)
                    )
                else:
                    # 横レイアウトの場合は左右移動
                    context_menu.add_command(
                        label="◀ 左に移動",
                        command=lambda: self._move_button(event.button_key, -1)
                    )
                    context_menu.add_command(
                        label="▶ 右に移動",
                        command=lambda: self._move_button(event.button_key, 1)
                    )
                context_menu.add_separator()
            
            context_menu.add_command(
                label="ボタン管理",
                command=self._show_button_manager
            )
            
            context_menu.add_separator()
            
            # 遅延入力モードのトグル（チェック式）
            if hasattr(self.floating_keyboard, 'delay_input_mode'):
                delay_label = "✓ 遅延入力モード" if self.floating_keyboard.delay_input_mode else "遅延入力モード"
                
                # 遅延入力モードがONの時は背景色を変える
                if self.floating_keyboard.delay_input_mode:
                    context_menu.add_command(
                        label=delay_label,
                        command=self._toggle_delay_input_mode,
                        background="#90caf9",  # 青色背景（濃いめ）
                        activebackground="#64b5f6"  # ホバー時はさらに濃い青色
                    )
                else:
                    context_menu.add_command(
                        label=delay_label,
                        command=self._toggle_delay_input_mode
                    )
            
            
            context_menu.add_separator()
            
            # ライト・ダークモード切り替え
            # フローティングキーボードのdark_mode状態に基づいてメニューテキストを設定
            if hasattr(self, 'floating_keyboard') and hasattr(self.floating_keyboard, 'dark_mode'):
                mode_text = "ライトモードに切り替え" if self.floating_keyboard.dark_mode else "ダークモードに切り替え"
            else:
                mode_text = "ダークモードに切り替え"
            
            context_menu.add_command(
                label=mode_text,
                command=self._toggle_appearance_mode
            )
            
            # レイアウト切り替えメニュー
            current_layout = self.config_manager.config.get('floatingWindow', {}).get('layoutDirection', 'horizontal')
            layout_text = "縦並びに切り替え" if current_layout == "horizontal" else "横並びに切り替え"
            context_menu.add_command(
                label=layout_text,
                command=self._toggle_layout_direction
            )
            
            context_menu.add_separator()
            
            context_menu.add_command(
                label="終了",
                command=self._on_closing
            )
            
            # メニューを表示
            context_menu.tk_popup(event.x_root, event.y_root)
            
        except Exception as e:
            logger.error(f"Failed to show context menu: {e}")
            import traceback
            traceback.print_exc()
            
            # フォールバック：基本メニューのみ表示
            try:
                fallback_menu = tk.Menu(self.root, tearoff=0)
                fallback_menu.add_command(label="設定", command=self._show_keypad_config)
                fallback_menu.add_command(label="ボタン管理", command=self._show_button_manager)
                fallback_menu.add_separator()
                fallback_menu.add_command(label="終了", command=self._on_closing)
                fallback_menu.tk_popup(event.x_root, event.y_root)
                logger.info("Fallback context menu displayed")
            except Exception as fallback_error:
                logger.error(f"Fallback menu also failed: {fallback_error}")
        finally:
            try:
                if 'context_menu' in locals():
                    context_menu.grab_release()
            except:
                pass
    
    def _show_keypad_config(self):
        """キーパッド設定ダイアログの表示"""
        try:
            from virtual_keyboard.ui.dialogs import FloatingKeypadConfigDialog
            
            dialog = FloatingKeypadConfigDialog(
                self.floating_keyboard.window,
                self.config_manager,
                None  # callback
            )
            # FloatingKeypadConfigDialogは初期化時に自動表示される
            
        except Exception as e:
            logger.error(f"Failed to show keypad config: {e}")
            tk.messagebox.showerror("エラー", f"キーパッド設定の表示に失敗しました: {e}")
    
    def _show_button_manager(self):
        """ボタン設定管理ダイアログの表示"""
        try:
            from virtual_keyboard.ui.button_manager import ButtonManagerWindow
            
            button_manager = ButtonManagerWindow(
                self.root,
                self.config_manager,
                self._update_floating_keyboard_buttons,
                self.focus_manager  # FocusManagerの参照を渡す
            )
            
        except Exception as e:
            logger.error(f"Failed to show button manager: {e}")
            tk.messagebox.showerror("エラー", f"ボタン設定の表示に失敗しました: {e}")
    
    def _auto_open_button_manager(self):
        """起動時に自動でボタン設定管理ウィンドウを開く"""
        try:
            logger.info("Auto-opening button manager window")
            self._show_button_manager()
        except Exception as e:
            logger.error(f"Failed to auto-open button manager: {e}")
    
    
    def _move_button(self, button_key, direction):
        """ボタンを移動"""
        try:
            logger.info(f"Moving button {button_key} by {direction}")
            
            # 設定から現在のボタン配列を取得
            config = self.config_manager.config
            buttons = config.get('floatingWindow', {}).get('buttons', [])
            
            # 該当ボタンのインデックスを検索
            current_index = -1
            for i, button in enumerate(buttons):
                if button.get('key') == button_key:
                    current_index = i
                    break
            
            if current_index == -1:
                logger.warning(f"Button {button_key} not found")
                return
            
            # 新しいインデックスを計算
            new_index = current_index + direction
            
            # 範囲チェック
            if new_index < 0 or new_index >= len(buttons):
                logger.info(f"Cannot move button {button_key} - would go out of bounds")
                return
            
            # ボタンを移動
            buttons[current_index], buttons[new_index] = buttons[new_index], buttons[current_index]
            
            # 設定を保存
            config['floatingWindow']['buttons'] = buttons
            if self.config_manager.save_config(config):
                # フローティングキーボードを即座に更新
                self._update_floating_keyboard_buttons()
                direction_text = "左" if direction < 0 else "右"
                logger.info(f"Button {button_key} moved {direction_text} successfully")
            else:
                tk.messagebox.showerror("エラー", "設定の保存に失敗しました")
                
        except Exception as e:
            logger.error(f"Error moving button {button_key}: {e}")
            tk.messagebox.showerror("エラー", f"ボタンの移動に失敗しました: {e}")
    
    def _update_floating_keyboard_buttons(self):
        """フローティングキーボードのボタンを更新"""
        try:
            if hasattr(self, 'floating_keyboard') and self.floating_keyboard:
                # 設定を再読み込み
                self.floating_keyboard.config_manager.config = self.floating_keyboard.config_manager.load_config()
                # ボタンを再作成
                self.floating_keyboard.create_buttons()
                logger.info("Floating keyboard buttons updated after move")
        except Exception as e:
            logger.error(f"Error updating floating keyboard buttons: {e}")
    
    def _toggle_delay_input_mode(self):
        """遅延入力モードのトグル"""
        try:
            logger.info("Toggle delay input mode called")
            if hasattr(self.floating_keyboard, 'toggle_delay_input_mode'):
                self.floating_keyboard.toggle_delay_input_mode()
                mode_text = "ON" if self.floating_keyboard.delay_input_mode else "OFF"
                logger.info(f"Delay input mode toggled to {mode_text} from context menu")
            else:
                logger.warning("floating_keyboard does not have toggle_delay_input_mode method")
        except Exception as e:
            logger.error(f"Failed to toggle delay input mode: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_diagnostics(self):
        """診断機能の実行と表示"""
        try:
            from virtual_keyboard.services.key_diagnostics import KeySendDiagnostics
            
            diagnostics = KeySendDiagnostics()
            result = diagnostics.run_comprehensive_diagnosis()
            
            # 診断結果のサマリーを作成
            summary_lines = []
            summary_lines.append("=== システム診断結果 ===\n")
            
            # システム情報
            system = result.get("system_info", {})
            admin_status = system.get("admin_privileges", {}).get("status", "Unknown")
            summary_lines.append(f"管理者権限: {admin_status}")
            
            # テスト結果
            tests = result.get("key_send_tests", {})
            stats = tests.get("statistics", {})
            if stats:
                success_rate = stats.get("success_rate_percent", 0)
                avg_duration = stats.get("average_duration_ms", 0)
                summary_lines.append(f"キー送信成功率: {success_rate}%")
                summary_lines.append(f"平均応答時間: {avg_duration:.2f}ms")
            
            # 推奨事項
            recommendations = result.get("recommendations", [])
            if recommendations:
                summary_lines.append(f"\n推奨事項:")
                for rec in recommendations[:3]:  # 上位3つのみ表示
                    summary_lines.append(f"• {rec}")
            
            summary_text = "\n".join(summary_lines)
            
            # 結果表示
            tk.messagebox.showinfo("システム診断結果", summary_text)
            
        except Exception as e:
            logger.error(f"Failed to show diagnostics: {e}")
            tk.messagebox.showerror("エラー", f"診断の実行に失敗しました: {e}")
    
    def _toggle_appearance_mode(self):
        """ライト・ダークモード切り替え"""
        try:
            # フローティングキーボードの既存のtoggle_mode()を使用
            if hasattr(self, 'floating_keyboard') and self.floating_keyboard:
                self.floating_keyboard.toggle_mode()
                logger.info("Appearance mode toggled using floating keyboard toggle_mode")
            else:
                logger.error("Floating keyboard not available for mode toggle")
                tk.messagebox.showerror("エラー", "フローティングキーボードが利用できません")
            
        except Exception as e:
            logger.error(f"Failed to toggle appearance mode: {e}")
            tk.messagebox.showerror("エラー", f"モード切り替えに失敗しました: {e}")
    
    def _toggle_layout_direction(self):
        """レイアウト方向の切り替え（横並び ⇔ 縦並び）"""
        try:
            config = self.config_manager.config
            floating_config = config.get('floatingWindow', {})
            
            # 現在のレイアウトを取得
            current_layout = floating_config.get('layoutDirection', 'horizontal')
            
            # レイアウトを切り替え
            new_layout = 'vertical' if current_layout == 'horizontal' else 'horizontal'
            floating_config['layoutDirection'] = new_layout
            
            # 設定を保存
            self.config_manager.save_config()
            
            # フローティングキーボードを再作成して新しいレイアウトを適用
            if hasattr(self, 'floating_keyboard') and self.floating_keyboard:
                # 現在の状態を保存
                current_x = self.floating_keyboard.window.winfo_x()
                current_y = self.floating_keyboard.window.winfo_y()
                current_dark_mode = self.floating_keyboard.dark_mode
                
                # ウィンドウを破棄
                self.floating_keyboard.window.destroy()
                
                # 新しいレイアウトでフローティングキーボードを再作成
                self._create_floating_window()
                
                # 位置とダークモード状態を復元
                self.floating_keyboard.window.geometry(f"+{current_x}+{current_y}")
                
                # ダークモード状態が異なる場合は切り替え
                if self.floating_keyboard.dark_mode != current_dark_mode:
                    self.floating_keyboard.toggle_mode()
                
                # レイアウト切り替え後にタイトルを更新
                self.floating_keyboard._update_window_title()
                
                layout_name = "縦並び" if new_layout == "vertical" else "横並び"
                logger.info(f"Layout direction changed to {new_layout} ({layout_name})")
            else:
                logger.error("Floating keyboard not available for layout toggle")
                tk.messagebox.showerror("エラー", "フローティングキーボードが利用できません")
                
        except Exception as e:
            logger.error(f"Failed to toggle layout direction: {e}")
            tk.messagebox.showerror("エラー", f"レイアウト切り替えに失敗しました: {e}")
    
    def _on_closing(self):
        """アプリケーション終了時の処理"""
        try:
            logger.info("Application shutting down...")
            
            # 段階的な終了処理を実行
            self._graceful_shutdown()
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
            # グレースフル終了に失敗した場合は強制終了
            try:
                self._force_shutdown()
            except Exception as force_error:
                logger.error(f"Error during force shutdown: {force_error}")
    
    def _graceful_shutdown(self):
        """グレースフル終了処理"""
        import time
        
        # 1. フォーカス監視停止
        if hasattr(self, 'focus_manager') and self.focus_manager:
            try:
                logger.info("Stopping focus manager...")
                self.focus_manager.stop_monitoring()
                time.sleep(0.1)  # 停止完了を待機
            except Exception as e:
                logger.error(f"Error stopping focus manager: {e}")
        
        # 2. ホットキー管理停止
        if hasattr(self, 'hotkey_manager') and self.hotkey_manager:
            try:
                logger.info("Stopping hotkey manager...")
                self.hotkey_manager.stop_message_loop()
                time.sleep(0.1)  # 停止完了を待機
            except Exception as e:
                logger.error(f"Error stopping hotkey manager: {e}")
        
        # 3. フローティングウィンドウ終了
        if hasattr(self, 'floating_keyboard') and self.floating_keyboard:
            try:
                logger.info("Hiding floating keyboard...")
                if hasattr(self.floating_keyboard, 'window') and self.floating_keyboard.window:
                    self.floating_keyboard.hide()
                    # ウィンドウ破棄を確実に実行
                    self.floating_keyboard.window.destroy()
                    self.floating_keyboard.window = None
            except Exception as e:
                logger.error(f"Error hiding floating keyboard: {e}")
        
        # 4. 短時間待機してスレッド停止を確認
        time.sleep(0.5)
        
        # 5. メインウィンドウ終了
        try:
            logger.info("Stopping main window...")
            self.root.quit()
            self.root.destroy()
            logger.info("Application shutdown completed successfully")
        except Exception as e:
            logger.error(f"Error stopping main window: {e}")
            raise
    
    def _force_shutdown(self):
        """強制終了処理"""
        import os
        import sys
        
        logger.warning("Attempting force shutdown...")
        
        try:
            # 残存スレッドの強制終了を試行
            if hasattr(self, 'root') and self.root:
                self.root.quit()
        except:
            pass
        
        # 最終手段：プロセス強制終了
        try:
            logger.warning("Forcing process termination...")
            os._exit(0)
        except:
            sys.exit(1)
    
    def run(self):
        """アプリケーション実行"""
        try:
            logger.info("Starting floating keyboard application...")
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Application runtime error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """メイン関数"""
    try:
        app = FloatingKeyboardApp()
        app.run()
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        
        # エラーメッセージ表示
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", f"Failed to start application: {e}")
            root.destroy()
        except:
            print(f"Failed to start application: {e}")


if __name__ == "__main__":
    main()