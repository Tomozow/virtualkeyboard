"""
Button Edit Dialog - ボタン個別設定ダイアログ
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

logger = logging.getLogger(__name__)


class ButtonEditDialog:
    """ボタン個別設定ダイアログ"""
    
    def __init__(self, parent, button_config, callback=None):
        self.button_config = button_config
        self.callback = callback
        
        # 絵文字キャッシュディレクトリを作成
        self.emoji_cache_dir = "emoji_cache"
        os.makedirs(self.emoji_cache_dir, exist_ok=True)
        
        # メモリキャッシュ
        self.emoji_image_cache = {}
        
        # ダイアログ作成
        self.create_dialog(parent)
    
    def _get_best_emoji_font(self):
        """最適な絵文字フォントを取得"""
        import platform
        import tkinter.font as tkFont
        system = platform.system()
        
        if system == "Windows":
            # Windows用カラー絵文字フォント候補
            candidates = [
                "Segoe UI Emoji",
                "Microsoft YaHei UI", 
                "Segoe UI Symbol",
                "Symbola",
                "DejaVu Sans"
            ]
        elif system == "Darwin":  # macOS
            candidates = ["Apple Color Emoji", "Helvetica"]
        else:  # Linux
            candidates = ["Noto Color Emoji", "DejaVu Sans"]
        
        # 利用可能なフォントを確認
        available_fonts = tkFont.families()
        for font in candidates:
            if font in available_fonts:
                return font
        
        return "TkDefaultFont"  # フォールバック
    
    def _preload_common_emojis(self):
        """よく使用される絵文字を事前にダウンロード"""
        import threading
        
        # よく使用される絵文字リスト
        common_emojis = [
            "🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚫", "⚪", "🔘",
            "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎",
            "🎨", "✨", "⭐", "🌟", "🔥", "💥", "💯", "✅", "❌",
            "😊", "😀", "😃", "😄", "😁", "🤣", "😂", "🥰", "😍",
            "👋", "👍", "👎", "👌", "✋", "🤚", "🖐️", "✌️", "🤞",
            "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐯",
            "🍎", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🥝", "🍅",
            "⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🏉", "🎱", "🏓",
            "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒",
            "📱", "💻", "⌨️", "🖥️", "🖨️", "📺", "📷", "📹", "🎮"
        ]
        
        def download_worker():
            """バックグラウンドダウンロードワーカー"""
            for emoji_char in common_emojis:
                try:
                    self._get_cached_emoji_image(emoji_char)
                    # 少し間隔を空けてCPU負荷軽減
                    time.sleep(0.01)
                except Exception as e:
                    logger.debug(f"Failed to preload {emoji_char}: {e}")
        
        # バックグラウンドスレッドで実行
        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()
    
    def _create_emoji_image(self, emoji_char, size=32):
        """絵文字をカラー画像として生成（ローカルキャッシュ優先）"""
        # キャッシュキーを生成
        cache_key = f"{emoji_char}_{size}"
        
        # メモリキャッシュから取得を試行
        if cache_key in self.emoji_image_cache:
            return self.emoji_image_cache[cache_key]
        
        try:
            # 方法1: ローカルキャッシュファイルから読み込み
            emoji_image = self._get_cached_emoji_image(emoji_char, size)
            if emoji_image:
                self.emoji_image_cache[cache_key] = emoji_image
                return emoji_image
            
            # 方法2: カラーフォールバック（形状ベース）
            emoji_image = self._create_color_emoji_fallback(emoji_char, size)
            if emoji_image:
                self.emoji_image_cache[cache_key] = emoji_image
                return emoji_image
                
            # フォールバック: テキスト表示用
            self.emoji_image_cache[cache_key] = None
            return None
            
        except Exception as e:
            logger.error(f"Error creating emoji image for {emoji_char}: {e}")
            self.emoji_image_cache[cache_key] = None
            return None
    
    def _get_cached_emoji_image(self, emoji_char, size=32):
        """ローカルキャッシュから絵文字画像を取得（存在しない場合はダウンロード）"""
        try:
            # キャッシュファイルパスを生成
            codepoint = self._get_emoji_codepoint(emoji_char)
            if not codepoint:
                return None
                
            cache_file = os.path.join(self.emoji_cache_dir, f"{codepoint}.png")
            
            # ローカルファイルが存在するかチェック
            if os.path.exists(cache_file):
                # ローカルファイルから読み込み
                try:
                    image = Image.open(cache_file)
                    if size != image.size[0]:  # リサイズが必要
                        image = image.resize((size, size), Image.Resampling.LANCZOS)
                    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
                except Exception as e:
                    logger.debug(f"Failed to load cached emoji {cache_file}: {e}")
                    # キャッシュファイルが破損している可能性があるので削除
                    try:
                        os.remove(cache_file)
                    except:
                        pass
            
            # キャッシュファイルが存在しない場合のみダウンロード
            return self._download_and_cache_emoji(emoji_char, codepoint, size)
            
        except Exception as e:
            logger.debug(f"Error getting cached emoji for {emoji_char}: {e}")
            return None
    
    def _download_and_cache_emoji(self, emoji_char, codepoint, size):
        """絵文字をダウンロードしてキャッシュに保存"""
        try:
            # TwemojiのCDNから画像をダウンロード
            twemoji_url = f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/{codepoint}.png"
            
            # タイムアウトを短めに設定
            response = requests.get(twemoji_url, timeout=3)
            if response.status_code == 200:
                # キャッシュファイルに保存
                cache_file = os.path.join(self.emoji_cache_dir, f"{codepoint}.png")
                
                with open(cache_file, 'wb') as f:
                    f.write(response.content)
                
                # 保存した画像を読み込んで返す
                image = Image.open(cache_file)
                if size != image.size[0]:
                    image = image.resize((size, size), Image.Resampling.LANCZOS)
                    
                logger.debug(f"Downloaded and cached emoji {emoji_char} -> {cache_file}")
                return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
                
        except Exception as e:
            logger.debug(f"Failed to download emoji {emoji_char}: {e}")
            
        return None
    
    
    def _get_emoji_codepoint(self, emoji_char):
        """絵文字のUnicodeコードポイントを取得"""
        try:
            # 基本的なUnicodeコードポイント変換
            codepoint = hex(ord(emoji_char[0]))[2:].lower()
            
            # 複合絵文字の処理（簡易版）
            if len(emoji_char) > 1:
                codepoints = []
                for char in emoji_char:
                    if ord(char) > 127:  # ASCII以外
                        codepoints.append(hex(ord(char))[2:].lower())
                if codepoints:
                    codepoint = "-".join(codepoints)
            
            return codepoint
            
        except Exception as e:
            logger.debug(f"Codepoint extraction failed for {emoji_char}: {e}")
            return None
    
    def _create_color_emoji_fallback(self, emoji_char, size):
        """カラー絵文字フォールバック（Unicode to Image）"""
        try:
            # シンプルなカラーアイコンマッピング
            color_map = {
                "🔴": "#FF0000", "🟠": "#FF8800", "🟡": "#FFFF00", "🟢": "#00FF00", 
                "🔵": "#0088FF", "🟣": "#8800FF", "🟤": "#8B4513", "⚫": "#000000", 
                "⚪": "#FFFFFF", "❤️": "#FF0000", "💛": "#FFFF00", "💚": "#00FF00",
                "💙": "#0088FF", "💜": "#8800FF", "🧡": "#FF8800", "🖤": "#000000",
                "🤍": "#FFFFFF", "🤎": "#8B4513", "🎨": "#FF6B9D", "✨": "#FFD700",
                "⭐": "#FFD700", "🌟": "#FFD700", "🔥": "#FF4500", "💥": "#FF0000"
            }
            
            if emoji_char in color_map:
                # 円形の色付きアイコンを作成
                img_size = (size, size)
                image = Image.new('RGBA', img_size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(image)
                
                # 円を描画
                margin = size // 8
                color = color_map[emoji_char]
                draw.ellipse([margin, margin, size-margin, size-margin], 
                           fill=color, outline="white", width=1)
                
                return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
                
        except Exception as e:
            logger.debug(f"Color fallback failed for {emoji_char}: {e}")
            
        return None
    
    def _create_system_emoji(self, emoji_char, size):
        """システムフォントでの絵文字描画"""
        try:
            import platform
            if platform.system() != "Windows":
                return None
                
            # Windows 10/11のカラー絵文字フォントパス
            emoji_font_paths = [
                "C:/Windows/Fonts/seguiemj.ttf",
                "C:/Windows/Fonts/NotoColorEmoji.ttf",
                "C:/Windows/Fonts/seguisym.ttf"
            ]
            
            img_size = (size, size)
            image = Image.new('RGBA', img_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            font_size = int(size * 0.8)
            
            for font_path in emoji_font_paths:
                try:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, font_size)
                        
                        # テキストを中央配置
                        bbox = draw.textbbox((0, 0), emoji_char, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        
                        x = (img_size[0] - text_width) // 2 - bbox[0]
                        y = (img_size[1] - text_height) // 2 - bbox[1]
                        
                        # 絵文字を描画（黒色で）
                        draw.text((x, y), emoji_char, font=font, fill=(0, 0, 0, 255))
                        
                        return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
                        
                except Exception as e:
                    logger.debug(f"Font {font_path} failed: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"System emoji creation failed: {e}")
            
        return None
    
    def create_dialog(self, parent):
        """ダイアログ作成"""
        # ダイアログ作成
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.configure(fg_color="#f8f9fa")
        self.dialog.title("Button Settings")
        self.dialog.attributes('-topmost', True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_dialog()
        self.load_config()
        
        # サイズ設定（記憶機能付き）
        self.setup_window_size()
    
    def setup_dialog(self):
        """ダイアログUI設定"""
        # メインフレーム（ウィンドウサイズにフィット）
        main_frame = ctk.CTkFrame(self.dialog, fg_color="#f8f9fa")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        
        # 2ペインレイアウト用のメインコンテナ
        content_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_container.pack(fill="both", expand=True, pady=(0, 15))
        
        # 左ペイン（Key & Basic Settings）
        left_pane = ctk.CTkFrame(content_container, fg_color="#ffffff", corner_radius=8)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        # 右ペイン（Appearance & Advanced）
        right_pane = ctk.CTkFrame(content_container, fg_color="#ffffff", corner_radius=8)
        right_pane.pack(side="right", fill="both", expand=True, padx=(8, 0))
        
        # 左ペインの設定
        self._setup_left_pane(left_pane)
        
        # 右ペインの設定
        self._setup_right_pane(right_pane)
        
        # フッターボタン
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")
        
        cancel_btn = ctk.CTkButton(button_frame, text="Cancel",
                                  font=ctk.CTkFont(size=11),
                                  height=32, width=80,
                                  fg_color="transparent",
                                  text_color="#666666",
                                  hover_color="#f0f0f0",
                                  border_width=1, border_color="#ddd",
                                  command=self.dialog.destroy)
        cancel_btn.pack(side="left")
        
        save_btn = ctk.CTkButton(button_frame, text="Save",
                                font=ctk.CTkFont(size=11, weight="bold"),
                                height=32, width=80,
                                fg_color="#3b82f6",
                                hover_color="#2563eb",
                                command=self.save_config)
        save_btn.pack(side="right")
    
    def _setup_left_pane(self, parent):
        """左ペイン（Key & Basic Settings）の設定"""
        # パディング付きコンテナ
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # キー入力セクション
        key_section = ctk.CTkFrame(container, fg_color="transparent")
        key_section.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(key_section, text="Key Input",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#333333").pack(anchor="w", pady=(0, 8))
        
        # 修飾キーチェックボックス
        modifier_frame = ctk.CTkFrame(key_section, fg_color="transparent")
        modifier_frame.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(modifier_frame, text="Modifiers:", 
                    font=ctk.CTkFont(size=10),
                    text_color="#666666").pack(anchor="w", pady=(0, 2))
        
        modifier_check_frame = ctk.CTkFrame(modifier_frame, fg_color="transparent")
        modifier_check_frame.pack(fill="x")
        
        self.ctrl_var = tk.BooleanVar()
        self.shift_var = tk.BooleanVar()
        self.alt_var = tk.BooleanVar()
        self.win_var = tk.BooleanVar()
        
        ctk.CTkCheckBox(modifier_check_frame, text="Ctrl", variable=self.ctrl_var,
                       font=ctk.CTkFont(size=10), width=50, text_color="#333333").pack(side="left", padx=(0, 8))
        ctk.CTkCheckBox(modifier_check_frame, text="Shift", variable=self.shift_var,
                       font=ctk.CTkFont(size=10), width=50, text_color="#333333").pack(side="left", padx=8)
        ctk.CTkCheckBox(modifier_check_frame, text="Alt", variable=self.alt_var,
                       font=ctk.CTkFont(size=10), width=50, text_color="#333333").pack(side="left", padx=8)
        ctk.CTkCheckBox(modifier_check_frame, text="Win", variable=self.win_var,
                       font=ctk.CTkFont(size=10), width=50, text_color="#333333").pack(side="left", padx=8)
        
        # メインキー入力
        main_key_frame = ctk.CTkFrame(key_section, fg_color="transparent")
        main_key_frame.pack(fill="x", pady=(8, 0))
        
        # キーバインディング入力（上部）
        text_input_frame = ctk.CTkFrame(main_key_frame, fg_color="transparent")
        text_input_frame.pack(fill="x", pady=(0, 5))
        
        input_row = ctk.CTkFrame(text_input_frame, fg_color="transparent")
        input_row.pack(fill="x")
        
        ctk.CTkLabel(input_row, text="Press a key:", 
                    font=ctk.CTkFont(size=10),
                    text_color="#666666").pack(side="left")
        
        self.key_var = tk.StringVar()
        self.key_entry = ctk.CTkEntry(input_row,
                                     textvariable=self.key_var,
                                     font=ctk.CTkFont(size=11, weight="bold"),
                                     width=60,
                                     height=28,
                                     justify="center",
                                     placeholder_text="Key")
        self.key_entry.pack(side="left", padx=(10, 10))
        
        # 1文字制限とキーバインディング機能を追加
        self.key_entry.bind('<KeyPress>', self.on_key_press)
        self.key_entry.bind('<Key>', self.validate_single_char)
        
        # クリア/リセットボタン
        clear_btn = ctk.CTkButton(input_row, text="Clear", 
                                 width=50, height=28,
                                 font=ctk.CTkFont(size=9),
                                 fg_color="#6b7280",
                                 hover_color="#4b5563",
                                 command=self.clear_key_input)
        clear_btn.pack(side="left")
        
        # 説明テキスト
        ctk.CTkLabel(text_input_frame, 
                    text="Click in the input field and press any key to capture it",
                    font=ctk.CTkFont(size=9),
                    text_color="#888888").pack(anchor="w", pady=(3, 0))
        
        # 特殊キープルダウン（下部）
        special_frame = ctk.CTkFrame(main_key_frame, fg_color="transparent")
        special_frame.pack(fill="x")
        
        ctk.CTkLabel(special_frame, text="Or select special key:", 
                    font=ctk.CTkFont(size=10),
                    text_color="#666666").pack(anchor="w")
        
        special_keys = [
            "", "F13", "F14", "F15", "F16", "F17", "F18", "F19", "F20", "F21", "F22", "F23", "F24",
            "Enter", "Space", "Backspace", "Delete", "Tab", "Escape",
            "Insert", "Home", "End", "PageUp", "PageDown",
            "Up", "Down", "Left", "Right",
            "CapsLock", "NumLock", "ScrollLock", "PrintScreen", "Pause",
            "Semicolon", "Equal", "Comma", "Minus", "Period", "Slash",
            "Grave", "LeftBracket", "Backslash", "RightBracket", "Quote",
            # 日本語IMEキー
            "Hankaku/Zenkaku", "半角/全角", "Kanji", 
            "Kana", "かな",
            "Convert", "変換", "Henkan",
            "NonConvert", "無変換", "Muhenkan",
            "IME_ON", "IME_OFF"
        ]
        
        self.special_combo = ctk.CTkComboBox(special_frame,
                                           values=special_keys,
                                           font=ctk.CTkFont(size=10),
                                           width=200,
                                           command=self.on_special_key_selected)
        self.special_combo.pack(fill="x")
        
        # ラベル入力セクション
        label_section = ctk.CTkFrame(container, fg_color="transparent")
        label_section.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(label_section, text="Display Label",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#333333").pack(anchor="w", pady=(0, 5))
        
        self.label_var = tk.StringVar()
        self.label_entry = ctk.CTkEntry(label_section,
                                       textvariable=self.label_var,
                                       font=ctk.CTkFont(size=11),
                                       placeholder_text="Button label")
        self.label_entry.pack(fill="x")
    
    def _setup_right_pane(self, parent):
        """右ペイン（Appearance & Advanced）の設定"""
        # パディング付きコンテナ
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # アイコン設定セクション
        icon_section = ctk.CTkFrame(container, fg_color="transparent")
        icon_section.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(icon_section, text="Icon",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#333333").pack(anchor="w", pady=(0, 5))
        
        icon_input_frame = ctk.CTkFrame(icon_section, fg_color="transparent")
        icon_input_frame.pack(fill="x", pady=(0, 5))
        
        # アイコンプレビュー（画像パス入力欄の代わり）
        self.preview_btn = ctk.CTkButton(icon_input_frame,
                                        text="No icon",
                                        width=120, height=28,
                                        font=ctk.CTkFont(size=9),
                                        fg_color="#f8f9fa",
                                        text_color="#999999",
                                        hover_color="#f0f0f0",
                                        border_width=1,
                                        border_color="#e0e0e0",
                                        state="disabled")  # クリック無効
        self.preview_btn.pack(side="left", padx=(0, 5))
        
        # 絵文字直接入力
        emoji_font_family = self._get_best_emoji_font()
        
        self.emoji_entry = ctk.CTkEntry(icon_input_frame, 
                                       width=80, height=28,
                                       font=ctk.CTkFont(family=emoji_font_family, size=18),
                                       placeholder_text="🎨")
        self.emoji_entry.pack(side="left", padx=(0, 5))
        self.emoji_entry.bind('<KeyRelease>', self._on_emoji_input_change)
        
        # ボタン群
        button_row = ctk.CTkFrame(icon_input_frame, fg_color="transparent")
        button_row.pack(side="left")
        
        # パレットボタン（軽量版）
        palette_btn = ctk.CTkButton(button_row, text="📋",
                                   width=25, height=28,
                                   font=ctk.CTkFont(family="Noto Color Emoji, Apple Color Emoji, Segoe UI Emoji", size=14),
                                   command=self.show_simple_emoji_picker)
        palette_btn.pack(side="left", padx=(0, 2))
        
        # アイコン画像選択ボタン
        browse_btn = ctk.CTkButton(button_row, text="Browse",
                                  width=60, height=28,
                                  font=ctk.CTkFont(size=10),
                                  fg_color="#3b82f6", hover_color="#2563eb",
                                  command=self.browse_icon_directory)
        browse_btn.pack(side="left")
        
        # 隠し変数（アイコン値保存用）
        self.icon_var = tk.StringVar()
        
        # 入力変更時のプレビュー更新をバインド
        self.icon_var.trace('w', self._update_icon_preview)
        self.emoji_entry.bind('<KeyRelease>', self._on_emoji_input_change)
        
        # 色設定セクション
        color_section = ctk.CTkFrame(container, fg_color="transparent")
        color_section.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(color_section, text="Button Color",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#333333").pack(anchor="w", pady=(0, 5))
        
        color_input_frame = ctk.CTkFrame(color_section, fg_color="transparent")
        color_input_frame.pack(fill="x")
        
        self.color_var = tk.StringVar()
        self.color_preview = ctk.CTkButton(color_input_frame,
                                          text="    ",
                                          width=40, height=28,
                                          command=self.pick_color)
        self.color_preview.pack(side="left", padx=(0, 10))
        
        # プリセット色（透明色と12色 + 無彩色3色）
        preset_colors = [
            # 透明色 + 有彩色12色
            "transparent", "#dc2626", "#ea580c", "#ca8a04", "#65a30d", "#16a34a", "#059669",
            "#0891b2", "#0284c7", "#2563eb", "#7c3aed", "#c026d3", "#e11d48",
            # 無彩色3色
            "#000000", "#4b5563", "#9ca3af"
        ]
        
        # 色ボタンを2行配置
        color_grid = ctk.CTkFrame(color_input_frame, fg_color="transparent")
        color_grid.pack(side="left")
        
        for i, color in enumerate(preset_colors):
            row = i // 8  # 8列で2行（透明+12色+3色=16色）
            col = i % 8
            
            if color == "transparent":
                # 透明色の場合は特別な表示（他と同じサイズ）
                btn = ctk.CTkButton(color_grid,
                                   text="",  # テキストなしで市松模様風
                                   width=20, height=20,
                                   fg_color="#f0f0f0",
                                   hover_color="#e0e0e0",
                                   border_width=1,
                                   border_color="#cccccc",
                                   command=lambda c=color: self.set_color(c))
            else:
                btn = ctk.CTkButton(color_grid,
                                   text="",
                                   width=20, height=20,
                                   fg_color=color,
                                   hover_color=color,
                                   command=lambda c=color: self.set_color(c))
            btn.grid(row=row, column=col, padx=1, pady=1)
        
        # トグル表示設定セクション
        toggle_section = ctk.CTkFrame(container, fg_color="transparent")
        toggle_section.pack(fill="x", pady=(15, 0))
        
        ctk.CTkLabel(toggle_section, text="Display Options",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#333333").pack(anchor="w", pady=(0, 8))
        
        self.toggle_highlight_var = tk.BooleanVar()
        toggle_checkbox = ctk.CTkCheckBox(toggle_section, 
                                        text="Enable toggle highlight",
                                        variable=self.toggle_highlight_var,
                                        font=ctk.CTkFont(size=11),
                                        text_color="#333333")
        toggle_checkbox.pack(anchor="w", pady=(0, 3))
        
        # 説明テキスト
        ctk.CTkLabel(toggle_section, 
                    text="When enabled, button stays highlighted after being pressed\nuntil pressed again (toggle on/off behavior)",
                    font=ctk.CTkFont(size=9),
                    text_color="#888888").pack(anchor="w", pady=(0, 10))
        
        # ハイライトカラー設定セクション
        highlight_section = ctk.CTkFrame(toggle_section, fg_color="transparent")
        highlight_section.pack(fill="x")
        
        ctk.CTkLabel(highlight_section, text="Highlight Color",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#555555").pack(anchor="w", pady=(0, 2))
        
        # 説明テキスト追加
        ctk.CTkLabel(highlight_section, 
                    text="Color used when toggle highlight is active",
                    font=ctk.CTkFont(size=9),
                    text_color="#888888").pack(anchor="w", pady=(0, 5))
        
        highlight_input_frame = ctk.CTkFrame(highlight_section, fg_color="transparent")
        highlight_input_frame.pack(fill="x")
        
        self.highlight_color_var = tk.StringVar()
        self.highlight_color_preview = ctk.CTkButton(highlight_input_frame,
                                                   text="    ",
                                                   width=40, height=28,
                                                   command=self.pick_highlight_color)
        self.highlight_color_preview.pack(side="left", padx=(0, 10))
        
        # ハイライトカラーのプリセット色（12色 + 無彩色2色）
        highlight_preset_colors = [
            "#fef3c7", "#fed7aa", "#fde68a", "#d9f99d", "#bbf7d0", "#a7f3d0",
            "#a5f3fc", "#bfdbfe", "#c7d2fe", "#e9d5ff", "#f3e8ff", "#fce7f3",
            "#f3f4f6", "#d1d5db"  # 無彩色2色（ライトグレー、グレー）
        ]
        
        # ハイライト色ボタンを2行配置
        highlight_color_grid = ctk.CTkFrame(highlight_input_frame, fg_color="transparent")
        highlight_color_grid.pack(side="left")
        
        for i, color in enumerate(highlight_preset_colors):
            row = i // 8  # 8列で2行（16色対応）
            col = i % 8
            
            # ライトグレーの色は文字を黒に
            text_color = "#000000" if color == "#f3f4f6" else "white"
            btn = ctk.CTkButton(highlight_color_grid,
                               text="",
                               width=20, height=20,
                               fg_color=color,
                               hover_color=color,
                               text_color=text_color,
                               command=lambda c=color: self.set_highlight_color(c))
            btn.grid(row=row, column=col, padx=1, pady=1)
    
    def on_special_key_selected(self, selected_key):
        """特殊キー選択時にテキストエリアに設定"""
        if selected_key and selected_key.strip():
            self.key_var.set(selected_key)
            self.special_combo.set("")  # プルダウンをクリア
    
    def on_key_press(self, event):
        """キープレス時の処理（バインディング用）"""
        try:
            # 特殊キーの名前マッピング
            special_key_names = {
                'Return': 'Enter',
                'BackSpace': 'Backspace', 
                'Tab': 'Tab',
                'Escape': 'Escape',
                'space': 'Space',
                'Up': 'Up',
                'Down': 'Down',
                'Left': 'Left',
                'Right': 'Right',
                'Delete': 'Delete',
                'Insert': 'Insert',
                'Home': 'Home',
                'End': 'End',
                'Prior': 'PageUp',  # Page Up
                'Next': 'PageDown',  # Page Down
                'F1': 'F1', 'F2': 'F2', 'F3': 'F3', 'F4': 'F4',
                'F5': 'F5', 'F6': 'F6', 'F7': 'F7', 'F8': 'F8',
                'F9': 'F9', 'F10': 'F10', 'F11': 'F11', 'F12': 'F12',
                'F13': 'F13', 'F14': 'F14', 'F15': 'F15', 'F16': 'F16',
                'F17': 'F17', 'F18': 'F18', 'F19': 'F19', 'F20': 'F20',
                'F21': 'F21', 'F22': 'F22', 'F23': 'F23', 'F24': 'F24',
                # 日本語IMEキーのTkinterキーシンボルからのマッピング
                'Kanji': 'Kanji',  # 半角/全角キー
                'Hiragana': 'Kana',  # かなキー
                'Henkan': 'Convert',  # 変換キー
                'Muhenkan': 'NonConvert'  # 無変換キー
            }
            
            key_name = event.keysym
            
            # 特殊キーの場合
            if key_name in special_key_names:
                self.key_var.set(special_key_names[key_name])
            # 通常の文字キーの場合（1文字）
            elif len(event.char) == 1 and event.char.isprintable():
                self.key_var.set(event.char.upper())
            # その他のキー
            elif key_name:
                self.key_var.set(key_name)
            
            # デフォルト動作を停止（入力フィールドへの文字入力を防ぐ）
            return "break"
            
        except Exception as e:
            logger.error(f"Error in key press handler: {e}")
            return "break"
    
    def validate_single_char(self, event):
        """1文字制限の入力検証"""
        # すべての文字入力をブロック（on_key_pressで処理するため）
        return "break"
    
    def clear_key_input(self):
        """キー入力をクリア"""
        self.key_var.set("")
        self.key_entry.focus()  # フォーカスを戻す
    
    def load_config(self):
        """現在の設定を読み込み"""
        key = self.button_config.get('key', 'F13')
        
        # 修飾キー情報を優先的に読み込み（新形式）
        modifiers_config = self.button_config.get('modifiers', {})
        if modifiers_config:
            self.ctrl_var.set(modifiers_config.get('ctrl', False))
            self.shift_var.set(modifiers_config.get('shift', False))
            self.alt_var.set(modifiers_config.get('alt', False))
            self.win_var.set(modifiers_config.get('win', False))
            
            # メインキーを抽出
            if '+' in key:
                main_key = key.split('+')[-1]
            else:
                main_key = key
        else:
            # 旧形式：キー文字列から修飾キーを解析
            if '+' in key:
                parts = key.split('+')
                modifiers = parts[:-1]
                main_key = parts[-1]
                
                # 修飾キーチェックボックスを設定
                self.ctrl_var.set('Ctrl' in modifiers)
                self.shift_var.set('Shift' in modifiers)
                self.alt_var.set('Alt' in modifiers)
                self.win_var.set('Win' in modifiers)
            else:
                # 単一キーの場合
                main_key = key
                self.ctrl_var.set(False)
                self.shift_var.set(False)
                self.alt_var.set(False)
                self.win_var.set(False)
        
        # メインキーを設定
        self.key_var.set(main_key)
        
        self.label_var.set(self.button_config.get('label', 'F13'))
        icon_value = self.button_config.get('icon', '🔘')
        self.icon_var.set(icon_value)
        
        # 絵文字入力フィールドも更新
        if hasattr(self, 'emoji_entry'):
            self.emoji_entry.delete(0, 'end')
            if icon_value and not icon_value.endswith(('.png', '.jpg', '.gif', '.bmp')):
                self.emoji_entry.insert(0, icon_value)
        
        self.set_color(self.button_config.get('color', 'transparent'))
        
        # ハイライトカラーを読み込み
        highlight_color = self.button_config.get('highlightColor', '#fef3c7')
        self.set_highlight_color(highlight_color)
        
        # ハイライトカラーが設定されていない場合、デフォルトを保存
        if 'highlightColor' not in self.button_config:
            self.button_config['highlightColor'] = '#fef3c7'
        
        # トグルハイライト設定を読み込み
        self.toggle_highlight_var.set(self.button_config.get('toggleHighlight', False))
        
        # アイコンプレビューを更新
        if hasattr(self, 'preview_btn'):
            self._update_icon_preview()
    
    def set_color(self, color):
        """色を設定"""
        self.color_var.set(color)
        
        if color == "transparent":
            # 透明色の場合は特別な表示
            self.color_preview.configure(
                fg_color="#f0f0f0",
                hover_color="#e0e0e0",
                text="⚪",
                text_color="#888888"
            )
        else:
            # 通常の色の場合
            self.color_preview.configure(
                fg_color=color,
                hover_color=color,
                text="    ",
                text_color="white"
            )
    
    def pick_color(self):
        """色選択ダイアログ"""
        try:
            color = colorchooser.askcolor(
                initialcolor=self.color_var.get(),
                title="Choose Button Color",
                parent=self.dialog
            )
            if color[1]:  # hex値がある場合
                self.set_color(color[1])
        except Exception as e:
            logger.error(f"Error picking color: {e}")
    
    def set_highlight_color(self, color):
        """ハイライト色を設定"""
        self.highlight_color_var.set(color)
        
        # 通常の色の場合
        self.highlight_color_preview.configure(
            fg_color=color,
            hover_color=color,
            text="    ",
            text_color="white"
        )
    
    def pick_highlight_color(self):
        """ハイライト色選択ダイアログ"""
        try:
            color = colorchooser.askcolor(
                initialcolor=self.highlight_color_var.get(),
                title="Choose Highlight Color",
                parent=self.dialog
            )
            if color[1]:  # hex値がある場合
                self.set_highlight_color(color[1])
        except Exception as e:
            logger.error(f"Error picking highlight color: {e}")
    
    def show_simple_emoji_picker(self):
        """簡単な絵文字ピッカー"""
        emoji_dialog = ctk.CTkToplevel(self.dialog)
        emoji_dialog.title("Select Emoji")
        emoji_dialog.geometry("550x500")
        emoji_dialog.attributes('-topmost', True)
        emoji_dialog.resizable(True, True)
        emoji_dialog.transient(self.dialog)
        
        # 高DPI対応
        try:
            emoji_dialog.tk.call('tk', 'scaling', 1.0)
        except:
            pass
        
        # Unicode絵文字データベース（主要なカテゴリ）
        emoji_categories = {
            "色付きアイコン": [
                # 色付き図形とアイコン
                "🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫", "⚪", "🟨",
                "🟧", "🟦", "🟪", "🟫", "⬛", "⬜", "🔶", "🔷", "🔸", "🔹",
                "🔺", "🔻", "🔳", "🔲", "▪️", "▫️", "◾", "◽", "◼️", "◻️",
                # 色付き記号
                "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔",
                "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "♥️",
                # カラフルな活動アイコン
                "🎨", "🌈", "⭐", "🌟", "✨", "💫", "🌠", "🔥", "💥", "💢",
                "💯", "✅", "❌", "⚠️", "🚨", "💡", "🔋", "⚡", "🔆", "🔅",
                # 色付きスポーツアイコン
                "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱",
                "🏓", "🏸", "🏒", "🏑", "🥍", "🏏", "⛳", "🎯", "🏹", "🎣",
                # 追加の色付きアイコン
                "🟰", "➕", "➖", "✖️", "➗", "🆚", "💰", "💸", "💳", "💎",
                "🏆", "🥇", "🥈", "🥉", "🏅", "🎖️", "🏵️", "🎗️", "🎀", "🎁"
            ],
            "顔・感情": [
                # スマイル
                "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "🥲", "😊",
                "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙",
                "😚", "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎",
                "🥸", "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁",
                "☹️", "😣", "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠",
                "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥",
                "😓", "🤗", "🤔", "🤭", "🤫", "🤥", "😶", "😐", "😑", "😬",
                "🙄", "😯", "😦", "😧", "😮", "😲", "🥱", "😴", "🤤", "😪",
                "😵", "🤐", "🥴", "🤢", "🤮", "🤧", "😷", "🤒", "🤕", "🤑",
                "🤠", "😈", "👿", "👹", "👺", "🤡", "💩", "👻", "💀", "☠️",
                "👽", "👾", "🤖", "🎃", "😺", "😸", "😹", "😻", "😼", "😽",
                "🙀", "😿", "😾"
            ],
            "手・身体": [
                "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞",
                "🤟", "🤘", "🤙", "👈", "👉", "👆", "🖕", "👇", "☝️", "👍",
                "👎", "✊", "👊", "🤛", "🤜", "👏", "🙌", "👐", "🤲", "🤝",
                "🙏", "✍️", "💅", "🤳", "💪", "🦾", "🦵", "🦿", "🦶", "👂",
                "🦻", "👃", "🧠", "🫀", "🫁", "🦷", "🦴", "👀", "👁️", "👅",
                "👄", "💋", "🩸"
            ],
            "動物・自然": [
                "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐻‍❄️", "🐨",
                "🐯", "🦁", "🐮", "🐷", "🐽", "🐸", "🐵", "🙈", "🙉", "🙊",
                "🐒", "🐔", "🐧", "🐦", "🐤", "🐣", "🐥", "🦆", "🦅", "🦉",
                "🦇", "🐺", "🐗", "🐴", "🦄", "🐝", "🪱", "🐛", "🦋", "🐌",
                "🐞", "🐜", "🪰", "🪲", "🪳", "🦟", "🦗", "🕷️", "🕸️", "🦂",
                "🐢", "🐍", "🦎", "🦖", "🦕", "🐙", "🦑", "🦐", "🦞", "🦀",
                "🐡", "🐠", "🐟", "🐬", "🐳", "🐋", "🦈", "🐊", "🐅", "🐆",
                "🦓", "🦍", "🦧", "🦣", "🐘", "🦛", "🦏", "🐪", "🐫", "🦒",
                "🦘", "🦬", "🐃", "🐂", "🐄", "🐎", "🐖", "🐏", "🐑", "🦙",
                "🐐", "🦌", "🐕", "🐩", "🦮", "🐕‍🦺", "🐈", "🐈‍⬛", "🪶", "🐓",
                "🦃", "🦤", "🦚", "🦜", "🦢", "🦩", "🕊️", "🐇", "🦝", "🦨",
                "🦡", "🦫", "🦦", "🦥", "🐁", "🐀", "🐿️", "🦔"
            ]
        }
        
        # タブフレーム（上部）
        tab_frame = ctk.CTkFrame(emoji_dialog, fg_color="transparent", height=50)
        tab_frame.pack(fill="x", padx=10, pady=(10, 0))
        tab_frame.pack_propagate(False)
        
        # コンテンツフレーム（下部）
        content_frame = ctk.CTkFrame(emoji_dialog, fg_color="#f8f9fa")
        content_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # 現在のカテゴリを管理
        self.current_category = tk.StringVar(value=list(emoji_categories.keys())[0])
        self.category_frames = {}
        self.tab_buttons = {}
        self.emoji_categories = emoji_categories  # カテゴリデータを保存
        self.content_frame = content_frame  # コンテンツフレーム参照を保存
        self.emoji_dialog = emoji_dialog  # ダイアログ参照を保存
        self._cached_emoji_font = None  # フォントキャッシュ
        
        # タブボタンを作成
        # タブ用の絵文字フォントを取得
        tab_emoji_font = self._get_best_emoji_font()
        
        for i, category_name in enumerate(emoji_categories.keys()):
            # カテゴリの代表アイコン
            category_icons = {
                "色付きアイコン": "🎨",
                "顔・感情": "😊",
                "手・身体": "👋",
                "動物・自然": "🐶"
            }
            
            icon = category_icons.get(category_name, "📋")
            # 短い名前
            short_names = {
                "色付きアイコン": "色",
                "顔・感情": "顔",
                "手・身体": "手",
                "動物・自然": "動物"
            }
            short_name = short_names.get(category_name, category_name[:2])
            
            # シンプルなテキストベースのタブボタン
            tab_btn = ctk.CTkButton(tab_frame, 
                                   text=f"{icon}",
                                   width=80, height=40,
                                   font=ctk.CTkFont(family=tab_emoji_font, size=20),
                                   command=lambda cat=category_name: self.switch_category(cat))
            tab_btn.pack(side="left", padx=3, pady=2)
            self.tab_buttons[category_name] = tab_btn
        
        # 最初のカテゴリを表示
        first_category = list(emoji_categories.keys())[0]
        logger.debug(f"Initializing emoji palette with first category: {first_category}")
        
        # 確実に最初のカテゴリを作成・表示
        try:
            self._create_category_frame(first_category)
            if first_category in self.category_frames:
                self.category_frames[first_category].pack(fill="both", expand=True)
                self.current_category.set(first_category)
                # タブボタンをアクティブ状態に
                if first_category in self.tab_buttons:
                    self.tab_buttons[first_category].configure(fg_color="#2563eb", hover_color="#1d4ed8")
                logger.debug(f"Successfully initialized emoji palette with category: {first_category}")
            else:
                logger.error(f"Failed to create initial category frame: {first_category}")
                # フォールバック：簡単なエラーメッセージを表示
                error_label = ctk.CTkLabel(content_frame, text="絵文字の読み込みに失敗しました")
                error_label.pack(expand=True)
        except Exception as e:
            logger.error(f"Critical error during emoji palette initialization: {e}")
            # フォールバック：エラーメッセージを表示
            error_label = ctk.CTkLabel(content_frame, text=f"エラー: {str(e)}")
            error_label.pack(expand=True)
        
        logger.debug(f"Initial emoji palette setup completed")
    
    def switch_category(self, category_name):
        """カテゴリを切り替え（遅延読み込み対応）"""
        logger.debug(f"Switching to emoji category: {category_name}")
        
        # 現在表示中のフレームを非表示
        for frame in self.category_frames.values():
            frame.pack_forget()
        
        # カテゴリがまだ作成されていない場合は作成
        if category_name not in self.category_frames:
            logger.debug(f"Creating new category frame for: {category_name}")
            self._create_category_frame(category_name)
        else:
            logger.debug(f"Using existing category frame for: {category_name}")
        
        # 新しいカテゴリを表示
        if category_name in self.category_frames:
            self.category_frames[category_name].pack(fill="both", expand=True)
            self.current_category.set(category_name)
            logger.debug(f"Successfully displayed category: {category_name}")
        else:
            logger.error(f"Failed to create or find category frame: {category_name}")
        
        # タブボタンの状態を更新
        for cat_name, btn in self.tab_buttons.items():
            if cat_name == category_name:
                btn.configure(fg_color="#2563eb", hover_color="#1d4ed8")  # アクティブ
            else:
                btn.configure(fg_color="#3b82f6", hover_color="#2563eb")  # 非アクティブ
    
    def _create_category_frame(self, category_name):
        """カテゴリフレームと絵文字ボタンを遅延作成（最適化済み）"""
        try:
            if category_name not in self.emoji_categories:
                logger.warning(f"Unknown emoji category: {category_name}")
                return
            
            emojis = self.emoji_categories[category_name]
            logger.debug(f"Creating emoji category '{category_name}' with {len(emojis)} emojis")
            
            # カテゴリフレーム作成
            category_frame = ctk.CTkScrollableFrame(self.content_frame)
            self.category_frames[category_name] = category_frame
            
            # 絵文字ボタンを配置（最適化済み）
            cols = 12  # 列数調整
            
            # フォントキャッシュを使用（パフォーマンス改善）
            if self._cached_emoji_font is None:
                self._cached_emoji_font = self._get_best_emoji_font()
            
            emoji_font = ctk.CTkFont(family=self._cached_emoji_font, size=16)
            
            # バッチでボタンを作成（UIスレッドでの処理時間を短縮）
            for i, emoji in enumerate(emojis):
                row = i // cols
                col = i % cols
                
                # シンプルなテキストベースの絵文字ボタン
                btn = ctk.CTkButton(
                    category_frame, 
                    text=emoji,
                    width=35, 
                    height=35,
                    font=emoji_font,
                    anchor="center",
                    command=lambda e=emoji: self.select_emoji(e, self.emoji_dialog)
                )
                
                btn.grid(row=row, column=col, padx=2, pady=2, sticky="")
                
                # 大量のボタンを作成する際のUI応答性を維持
                if i % 20 == 19:  # 20個ごとにUI更新
                    self.emoji_dialog.update_idletasks()
            
            logger.debug(f"Successfully created {len(emojis)} emoji buttons for '{category_name}'")
            
        except Exception as e:
            logger.error(f"Error creating emoji category '{category_name}': {e}")
            # エラー時もフレームは作成しておく（再試行を防ぐため）
            if category_name not in self.category_frames:
                self.category_frames[category_name] = ctk.CTkScrollableFrame(self.content_frame)
    
    def _on_emoji_input_change(self, event=None):
        """絵文字直接入力の変更処理"""
        emoji_text = self.emoji_entry.get().strip()
        if emoji_text:
            self.icon_var.set(emoji_text)
    
    def _update_icon_preview(self, *args):
        """アイコンプレビューをボタンで更新（フローティングウィンドウのprocess_icon流用）"""
        try:
            icon_value = self.icon_var.get().strip()
            
            if not icon_value:
                # 空の場合
                self.preview_btn.configure(text="No icon",
                                         image=None,
                                         font=ctk.CTkFont(size=9),
                                         fg_color="#f8f9fa",
                                         text_color="#999999")
                return
            
            # process_icon風の処理（ミニボタンサイズ）
            processed_icon = self._process_preview_icon(icon_value, size=(20, 20))
            
            if isinstance(processed_icon, ctk.CTkImage):
                # 画像の場合
                self.preview_btn.configure(text="",
                                         image=processed_icon,
                                         fg_color="#f8f9fa")
            else:
                # テキスト/絵文字の場合 - フローティングウィンドウと同じ表示方式
                self.preview_btn.configure(text=str(processed_icon),
                                         image=None,
                                         font=ctk.CTkFont(size=10),  # フローティングウィンドウのミニボタンと同じ
                                         fg_color="#f8f9fa",
                                         text_color="#333333")
                
        except Exception as e:
            logger.error(f"Error updating icon preview: {e}")
            # エラー時のプレビュー
            self.preview_btn.configure(text="Error",
                                     image=None,
                                     font=ctk.CTkFont(size=9),
                                     fg_color="#f8f9fa",
                                     text_color="#ff6b6b")
    
    def _process_preview_icon(self, icon, size=(20, 20)):
        """アイコンを処理（フローティングウィンドウのprocess_iconを流用）"""
        # 画像ファイルかどうかチェック（file://付きまたは直接パス）
        is_file_path = (icon.startswith("file://") or 
                       (os.path.exists(icon) and os.path.isfile(icon)))
        
        if is_file_path:
            # 画像ファイルの場合、PILで読み込み
            try:
                file_path = icon.replace("file://", "") if icon.startswith("file://") else icon
                
                if os.path.exists(file_path):
                    # 画像を読み込み、リサイズ
                    img = Image.open(file_path)
                    # アスペクト比を保持してリサイズ
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                    
                    # 透明度対応
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    # CustomTkinter用のCTkImageを作成
                    return ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                else:
                    return "❓"
            except Exception as e:
                logger.error(f"Error loading preview image {icon}: {e}")
                return "🖼️"
        else:
            # テキスト/絵文字の場合はそのまま
            return icon
    
    def select_emoji(self, emoji, dialog):
        """絵文字を選択（パレットから）"""
        self.emoji_entry.delete(0, 'end')
        self.emoji_entry.insert(0, emoji)
        self.icon_var.set(emoji)
        dialog.destroy()
    
    def browse_icon_directory(self):
        """アイコン画像ファイルを選択"""
        try:
            # 画像ファイルを直接選択
            file_path = filedialog.askopenfilename(
                title="Select Icon Image",
                parent=self.dialog,
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.ico"),
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg *.jpeg"),
                    ("GIF files", "*.gif"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                logger.info(f"Selected image file: {file_path}")
                # ファイルパスをfile://形式に変換してアイコン入力欄に設定
                # 絶対パスの場合は直接、相対パスの場合はfile://を付与
                if os.path.isabs(file_path):
                    icon_path = f"file://{file_path}"
                else:
                    icon_path = file_path
                self.icon_var.set(icon_path)
                logger.info(f"Icon set to: {icon_path}")
                
        except Exception as e:
            logger.error(f"Error selecting icon file: {e}")
            messagebox.showerror("Error", f"Failed to select icon: {e}")
    
    def save_config(self):
        """設定を保存"""
        # 修飾キーとメインキーを組み合わせてキーストリングを構築
        modifiers = []
        if self.ctrl_var.get():
            modifiers.append('Ctrl')
        if self.shift_var.get():
            modifiers.append('Shift')
        if self.alt_var.get():
            modifiers.append('Alt')
        if self.win_var.get():
            modifiers.append('Win')
        
        main_key = self.key_var.get().strip()
        if not main_key:
            main_key = "F13"  # デフォルトキー
        
        # 最終的なキーストリングを構築
        if modifiers:
            key_string = '+'.join(modifiers) + '+' + main_key
        else:
            key_string = main_key
        
        # 設定を更新（従来形式と新形式の両方をサポート）
        self.button_config['key'] = key_string
        self.button_config['label'] = self.label_var.get()
        self.button_config['icon'] = self.icon_var.get()
        self.button_config['color'] = self.color_var.get()
        self.button_config['highlightColor'] = self.highlight_color_var.get()
        self.button_config['toggleHighlight'] = self.toggle_highlight_var.get()
        
        # 修飾キー情報を別途保存（後方互換性のため）
        self.button_config['modifiers'] = {
            'ctrl': self.ctrl_var.get(),
            'shift': self.shift_var.get(),
            'alt': self.alt_var.get(),
            'win': self.win_var.get()
        }
        
        logger.info(f"Button config saved: key='{key_string}', modifiers={self.button_config['modifiers']}")
        
        # コールバック実行
        if self.callback:
            self.callback()
        
        self.dialog.destroy()
    
    def setup_window_size(self):
        """ウィンドウサイズ設定（記憶機能付き）"""
        try:
            # 設定から前回のウィンドウサイズを取得
            # ButtonEditDialogはconfigManagerを持たないので、親から取得を試みる
            config = self._get_config_manager()
            
            if config and config.config:
                window_config = config.config.get('buttonConfigWindow', {})
            else:
                window_config = {}
            
            # デフォルトサイズ（2ペイン対応で横幅増加）
            default_width = 800  # 2ペイン対応で800pxに増加
            default_height = 500  # 2ペインで縦は少し減らす
            
            # 保存されたサイズを取得（なければデフォルト）
            width = window_config.get('width', default_width)
            height = window_config.get('height', default_height)
            
            # 最小サイズ制限
            min_width = 700  # 最小横幅も700pxに増加
            min_height = 450  # 最小高さは450pxに調整
            width = max(min_width, width)
            height = max(min_height, height)
            
            # ダイアログサイズを設定
            self.dialog.geometry(f"{width}x{height}")
            
            # 中央配置
            self.dialog.update_idletasks()
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            x = max(0, (screen_width - width) // 2)
            y = max(0, (screen_height - height) // 2)
            self.dialog.geometry(f"{width}x{height}+{x}+{y}")
            
            # リサイズを有効にする
            self.dialog.resizable(True, True)
            
            # ウィンドウ終了時にサイズを保存
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_closing)
            
        except Exception as e:
            # エラー時はデフォルトサイズを設定
            self.dialog.geometry("800x500")
            self.center_dialog()
    
    def _get_config_manager(self):
        """設定マネージャーの取得（親ダイアログから）"""
        try:
            # 親ウィンドウがFloatingKeypadConfigDialogの場合
            parent_widget = self.dialog.master
            while parent_widget:
                if hasattr(parent_widget, 'config_manager'):
                    return parent_widget.config_manager
                parent_widget = getattr(parent_widget, 'master', None)
            return None
        except:
            return None
    
    def _on_closing(self):
        """ウィンドウ終了時の処理（サイズ保存）"""
        try:
            # 現在のウィンドウサイズを取得して保存
            geometry = self.dialog.geometry()
            size_part = geometry.split('+')[0]
            width, height = map(int, size_part.split('x'))
            
            # 設定マネージャーを取得
            config_manager = self._get_config_manager()
            if config_manager and config_manager.config:
                config = config_manager.config
                
                if 'buttonConfigWindow' not in config:
                    config['buttonConfigWindow'] = {}
                
                config['buttonConfigWindow']['width'] = width
                config['buttonConfigWindow']['height'] = height
                
                # 設定を保存
                config_manager.save_config(config)
                logger.info(f"Saved button config window size: {width}x{height}")
            
        except Exception as e:
            logger.error(f"Error saving button config window size: {e}")
        
        # ダイアログを閉じる
        try:
            self.dialog.destroy()
        except:
            pass
    
    def center_dialog(self):
        """ダイアログを中央に配置"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")