# Ultimate Virtual Keyboard - 開発者マニュアル

## 目次
1. [アーキテクチャ概要](#アーキテクチャ概要)
2. [コア機能の拡張](#コア機能の拡張)
3. [UI機能の追加](#ui機能の追加)
4. [設定項目の追加](#設定項目の追加)
5. [デバッグとテスト](#デバッグとテスト)
6. [トラブルシューティング](#トラブルシューティング)

## アーキテクチャ概要

### 依存関係図
```
VirtualKeyboardApp (メインアプリケーション)
├── ConfigManager (設定管理)
├── HotkeyManager (ホットキー管理)
├── KeySender (キー送信)
├── FocusManager (フォーカス管理)
└── UI Components (各種ダイアログ)
    ├── tkinterdnd2 (改良されたドラッグ&ドロップ)
```

### レイヤー構造
- **Interface Layer (I*)**: 各機能のインターフェース定義
- **Implementation Layer**: 具体的な実装クラス
- **Application Layer**: メインアプリケーションロジック
- **Configuration Layer**: 設定管理とデータクラス

## コア機能の拡張

### 1. 新しいキー送信方法の追加

#### ステップ1: インターフェースの確認
```python
class IKeySender(ABC):
    @abstractmethod
    def send_key(self, vk_code: int) -> bool:
        pass
    
    # 新しいメソッドを追加する場合
    @abstractmethod
    def send_key_combination(self, keys: List[int]) -> bool:
        pass
```

#### ステップ2: 実装クラスの拡張
```python
class KeySender(IKeySender):
    def send_key_combination(self, keys: List[int]) -> bool:
        """複数キーの同時送信"""
        try:
            # すべてのキーを押下
            for vk_code in keys:
                user32.keybd_event(vk_code, 0, 0, 0)
            
            time.sleep(0.05)
            
            # すべてのキーをリリース（逆順）
            for vk_code in reversed(keys):
                user32.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            return True
        except Exception as e:
            logger.error(f"Failed to send key combination: {e}")
            return False
```

### 2. 新しいフォーカス復帰方法の追加

#### ステップ1: Enumの拡張
```python
class FocusRestoreMethod(Enum):
    SIMPLE = "simple"
    ENHANCED = "enhanced" 
    FORCE = "force"
    CUSTOM = "custom"  # 新しい方法を追加
```

#### ステップ2: FocusManagerの拡張
```python
class FocusManager(IFocusManager):
    def restore_focus_custom(self, target_window: int) -> bool:
        """カスタムフォーカス復帰方法"""
        try:
            # カスタム実装をここに記述
            # 例: 特定のアプリケーションに特化した方法
            
            window_class = win32gui.GetClassName(target_window)
            
            if "Chrome" in window_class:
                # Chrome専用の復帰方法
                return self._restore_chrome_focus(target_window)
            elif "Notepad" in window_class:
                # Notepad専用の復帰方法
                return self._restore_notepad_focus(target_window)
            else:
                # デフォルトの方法
                return self.restore_focus_enhanced(target_window)
                
        except Exception as e:
            logger.error(f"Custom focus restore error: {e}")
            return False
    
    def restore_focus(self, target_window: int) -> bool:
        """メインのrestore_focusメソッドに新しい方法を追加"""
        if self.config.method == FocusRestoreMethod.CUSTOM:
            success = self.restore_focus_custom(target_window)
            if not success:
                success = self.restore_focus_force(target_window)
        # ... 既存の実装
```

### 3. 新しいホットキータイプの追加

#### ステップ1: 設定データクラスの拡張
```python
@dataclass
class HotkeyConfig:
    target_keys: List[str]
    modifiers: Dict[str, bool]
    enabled: bool
    hotkey_type: str = "function_key"  # 新しいフィールド
    
@dataclass
class MouseHotkeyConfig:
    """マウスホットキー設定（新規）"""
    mouse_button: str  # "left", "right", "middle"
    modifiers: Dict[str, bool]
    target_action: str
    enabled: bool
```

#### ステップ2: ConfigManagerの拡張
```python
class ConfigManager(IConfigManager):
    def get_mouse_hotkey_config(self, set_name: str) -> Optional[MouseHotkeyConfig]:
        """マウスホットキー設定を取得"""
        try:
            mouse_data = self.config["mouseHotkeys"][set_name]
            return MouseHotkeyConfig(
                mouse_button=mouse_data["mouseButton"],
                modifiers=mouse_data["modifiers"],
                target_action=mouse_data["targetAction"],
                enabled=mouse_data["enabled"]
            )
        except KeyError:
            return None
```

## UI機能の追加

### 1. 新しいダイアログの追加

#### ステップ1: 基底ダイアログクラスの作成
```python
class BaseDialog:
    """ダイアログの基底クラス"""
    
    def __init__(self, parent, title: str, width: int = 400, height: int = 300):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.resizable(True, True)
        self.dialog.attributes('-topmost', True)
        
        # モーダルダイアログ設定
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.width = width
        self.height = height
        
    def center_dialog(self):
        """ダイアログを中央に配置"""
        self.dialog.update_idletasks()
        
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        x = (screen_width - self.width) // 2
        y = (screen_height - self.height) // 2
        
        self.dialog.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.dialog.minsize(self.width, self.height)
    
    def setup_buttons(self, buttons: List[Dict[str, Any]]):
        """標準ボタンの設定"""
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        for i, btn_config in enumerate(buttons):
            ttk.Button(
                button_frame,
                text=btn_config["text"],
                command=btn_config["command"]
            ).grid(row=0, column=i, padx=(0, 10) if i < len(buttons)-1 else 0, sticky="ew")
        
        for i in range(len(buttons)):
            button_frame.columnconfigure(i, weight=1)
```

#### ステップ2: 具体的なダイアログの実装
```python
class MouseHotkeyConfigDialog(BaseDialog):
    """マウスホットキー設定ダイアログ"""
    
    def __init__(self, parent, config_manager, callback=None):
        super().__init__(parent, "マウスホットキー設定", 500, 400)
        
        self.config_manager = config_manager
        self.callback = callback
        
        self.setup_ui()
        self.center_dialog()
    
    def setup_ui(self):
        """UI構築"""
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # マウスボタン選択
        mouse_frame = ttk.LabelFrame(main_frame, text="マウスボタン", padding="10")
        mouse_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.mouse_button_var = tk.StringVar(value="left")
        
        for i, (value, text) in enumerate([("left", "左クリック"), ("right", "右クリック"), ("middle", "中クリック")]):
            ttk.Radiobutton(
                mouse_frame,
                text=text,
                variable=self.mouse_button_var,
                value=value
            ).grid(row=0, column=i, padx=10)
        
        # 修飾キー選択
        mod_frame = ttk.LabelFrame(main_frame, text="修飾キー", padding="10")
        mod_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.modifiers = {}
        for i, mod_name in enumerate(["Shift", "Ctrl", "Alt"]):
            var = tk.BooleanVar()
            ttk.Checkbutton(
                mod_frame,
                text=mod_name,
                variable=var
            ).grid(row=0, column=i, padx=10)
            self.modifiers[mod_name.lower()] = var
        
        # ボタン設定
        buttons = [
            {"text": "保存", "command": self.save_config},
            {"text": "キャンセル", "command": self.dialog.destroy}
        ]
        self.setup_buttons(buttons)
    
    def save_config(self):
        """設定保存"""
        # 実装内容...
        messagebox.showinfo("保存", "マウスホットキー設定を保存しました")
        if self.callback:
            self.callback()
        self.dialog.destroy()
```

### 2. メインウィンドウへの統合

#### VirtualKeyboardAppクラスの拡張
```python
class VirtualKeyboardApp:
    def __init__(self):
        # ... 既存の初期化 ...
        
        # 新しいマネージャーを追加
        self.mouse_hotkey_manager = MouseHotkeyManager()  # 仮想的な例
    
    def open_mouse_hotkey_config_dialog(self):
        """マウスホットキー設定ダイアログを開く"""
        MouseHotkeyConfigDialog(
            self.root,
            self.config_manager,
            self.on_mouse_hotkey_config_changed
        )
    
    def on_mouse_hotkey_config_changed(self):
        """マウスホットキー設定変更時の処理"""
        # 設定を再読み込みして適用
        # ... 実装内容 ...
```

## 設定項目の追加

### 1. 新しい設定セクションの追加

#### ステップ1: デフォルト設定の拡張
```python
class ConfigManager(IConfigManager):
    def load_config(self) -> Dict[str, Any]:
        default_config = {
            # ... 既存の設定 ...
            
            # 新しい設定セクション
            "mouseHotkeys": {
                "enabled": False,
                "leftClick": {
                    "modifiers": {"shift": False, "ctrl": False, "alt": False},
                    "targetAction": "F13",
                    "enabled": False
                }
            },
            "appearance": {
                "theme": "system",  # "light", "dark", "system"
                "fontSize": 12,
                "language": "ja"
            },
            "advanced": {
                "logLevel": "INFO",
                "autoBackup": True,
                "backupInterval": 3600  # seconds
            }
        }
        # ... 既存の実装 ...
```

#### ステップ2: 設定アクセサーの追加
```python
@dataclass
class AppearanceConfig:
    """外観設定データクラス"""
    theme: str = "system"
    font_size: int = 12
    language: str = "ja"

@dataclass
class AdvancedConfig:
    """高度な設定データクラス"""
    log_level: str = "INFO"
    auto_backup: bool = True
    backup_interval: int = 3600

class ConfigManager(IConfigManager):
    def get_appearance_config(self) -> AppearanceConfig:
        """外観設定を取得"""
        try:
            appearance_data = self.config.get("appearance", {})
            return AppearanceConfig(
                theme=appearance_data.get("theme", "system"),
                font_size=appearance_data.get("fontSize", 12),
                language=appearance_data.get("language", "ja")
            )
        except (KeyError, ValueError):
            return AppearanceConfig()
    
    def save_appearance_config(self, config: AppearanceConfig) -> bool:
        """外観設定を保存"""
        try:
            self.config["appearance"] = {
                "theme": config.theme,
                "fontSize": config.font_size,
                "language": config.language
            }
            return self.save_config()
        except Exception as e:
            logger.error(f"Failed to save appearance config: {e}")
            return False
```

### 2. 動的設定の実装

#### 設定変更の監視と適用
```python
class ConfigWatcher:
    """設定ファイルの変更を監視するクラス"""
    
    def __init__(self, config_path: str, callback: Callable):
        self.config_path = config_path
        self.callback = callback
        self.last_modified = None
        self.watching = False
        self.watch_thread = None
    
    def start_watching(self):
        """監視を開始"""
        if self.watching:
            return
        
        self.watching = True
        self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.watch_thread.start()
        logger.info("Config file watching started")
    
    def _watch_loop(self):
        """監視ループ"""
        while self.watching:
            try:
                if os.path.exists(self.config_path):
                    current_modified = os.path.getmtime(self.config_path)
                    
                    if self.last_modified is not None and current_modified != self.last_modified:
                        logger.info("Config file changed, triggering callback")
                        self.callback()
                    
                    self.last_modified = current_modified
                
                time.sleep(1)  # 1秒ごとにチェック
            except Exception as e:
                logger.error(f"Config watch error: {e}")
                time.sleep(5)  # エラー時は5秒待機

# メインアプリケーションでの使用例
class VirtualKeyboardApp:
    def __init__(self):
        # ... 既存の初期化 ...
        
        # 設定監視の開始
        self.config_watcher = ConfigWatcher(
            self.config_manager.config_path,
            self.on_config_file_changed
        )
        self.config_watcher.start_watching()
    
    def on_config_file_changed(self):
        """設定ファイル変更時の処理"""
        logger.info("Reloading configuration due to file change")
        
        # 設定を再読み込み
        old_config = self.config_manager.config.copy()
        self.config_manager.config = self.config_manager.load_config()
        
        # 変更された設定に応じて処理を実行
        if old_config.get("focusRestore") != self.config_manager.config.get("focusRestore"):
            # フォーカス設定が変更された場合
            focus_config = self.config_manager.get_focus_config()
            self.focus_manager.config = focus_config
            logger.info("Focus configuration updated")
        
        if old_config.get("hotkeys") != self.config_manager.config.get("hotkeys"):
            # ホットキー設定が変更された場合
            self.apply_hotkey_config()
            logger.info("Hotkey configuration updated")
```

## デバッグとテスト

### 1. ログレベルの動的変更

```python
class DebugManager:
    """デバッグ機能管理クラス"""
    
    @staticmethod
    def set_log_level(level: str):
        """ログレベルを動的に変更"""
        numeric_level = getattr(logging, level.upper(), None)
        if isinstance(numeric_level, int):
            logging.getLogger().setLevel(numeric_level)
            logger.info(f"Log level changed to {level}")
        else:
            logger.error(f"Invalid log level: {level}")
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """システム情報を取得"""
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024,  # MB
            "cpu_percent": psutil.cpu_percent(),
            "active_windows": len([w for w in win32gui.EnumWindows() if win32gui.IsWindowVisible(w)])
        }
    
    @staticmethod
    def export_debug_report(config_manager, hotkey_manager, focus_manager) -> str:
        """デバッグレポートを出力"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": DebugManager.get_system_info(),
            "config": config_manager.config,
            "registered_hotkeys": len(hotkey_manager.hotkeys),
            "focus_monitoring": focus_manager.monitoring,
            "last_focus_window": focus_manager.get_last_focus_window()
        }
        
        report_path = f"debug_report_{int(time.time())}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_path
```

### 2. 単体テストの例

```python
import unittest
from unittest.mock import Mock, patch, MagicMock

class TestConfigManager(unittest.TestCase):
    """ConfigManagerのテストクラス"""
    
    def setUp(self):
        self.config_manager = ConfigManager("test_config.json")
    
    def test_load_default_config(self):
        """デフォルト設定の読み込みテスト"""
        config = self.config_manager.load_config()
        
        self.assertIn("hotkeys", config)
        self.assertIn("focusRestore", config)
        self.assertTrue(isinstance(config["hotkeys"]["set1"]["targetKeys"], list))
    
    def test_get_hotkey_config(self):
        """ホットキー設定取得テスト"""
        hotkey_config = self.config_manager.get_hotkey_config("set1")
        
        self.assertIsInstance(hotkey_config, HotkeyConfig)
        self.assertEqual(len(hotkey_config.target_keys), 6)
    
    def test_get_focus_config(self):
        """フォーカス設定取得テスト"""
        focus_config = self.config_manager.get_focus_config()
        
        self.assertIsInstance(focus_config, FocusConfig)
        self.assertIn(focus_config.method, [FocusRestoreMethod.SIMPLE, FocusRestoreMethod.ENHANCED, FocusRestoreMethod.FORCE])

class TestKeySender(unittest.TestCase):
    """KeySenderのテストクラス"""
    
    def setUp(self):
        self.key_sender = KeySender()
    
    @patch('win32con.KEYEVENTF_KEYUP', 2)
    @patch('ctypes.windll.user32.keybd_event')
    def test_send_key(self, mock_keybd_event):
        """キー送信テスト"""
        result = self.key_sender.send_key(0x7C)  # F13
        
        self.assertTrue(result)
        self.assertEqual(mock_keybd_event.call_count, 2)  # Key down + Key up
    
    def test_vk_code_to_name(self):
        """VKコード変換テスト"""
        self.assertEqual(KeySender.vk_code_to_name(0x70), "F1")
        self.assertEqual(KeySender.vk_code_to_name(0x7C), "F13")
        self.assertEqual(KeySender.vk_code_to_name(0x87), "F24")

# テスト実行例
if __name__ == '__main__':
    unittest.main()
```

## トラブルシューティング

### 1. よくある問題と解決方法

#### ホットキーが動作しない場合
```python
def diagnose_hotkey_issues(hotkey_manager: HotkeyManager) -> List[str]:
    """ホットキー関連の問題を診断"""
    issues = []
    
    # ウィンドウハンドルの確認
    if hotkey_manager.hwnd is None:
        issues.append("メッセージウィンドウが作成されていません")
    elif not win32gui.IsWindow(hotkey_manager.hwnd):
        issues.append("メッセージウィンドウが無効です")
    
    # 登録済みホットキーの確認
    if not hotkey_manager.hotkeys:
        issues.append("ホットキーが登録されていません")
    
    # メッセージループの確認
    if not hotkey_manager.running:
        issues.append("メッセージループが動作していません")
    
    # 管理者権限の確認
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            issues.append("管理者権限が必要な可能性があります")
    except:
        issues.append("管理者権限の確認に失敗しました")
    
    return issues
```

#### フォーカス復帰が失敗する場合
```python
def diagnose_focus_issues(focus_manager: FocusManager) -> Dict[str, Any]:
    """フォーカス関連の問題を診断"""
    diagnosis = {
        "last_focus_window": focus_manager.get_last_focus_window(),
        "monitoring_active": focus_manager.monitoring,
        "config": focus_manager.config,
        "issues": []
    }
    
    last_window = focus_manager.get_last_focus_window()
    
    if last_window is None:
        diagnosis["issues"].append("ターゲットウィンドウが記憶されていません")
    elif not win32gui.IsWindow(last_window):
        diagnosis["issues"].append("ターゲットウィンドウが無効または閉じられています")
    else:
        try:
            window_title = win32gui.GetWindowText(last_window)
            diagnosis["target_window_title"] = window_title
            
            # ウィンドウの状態確認
            if not win32gui.IsWindowVisible(last_window):
                diagnosis["issues"].append("ターゲットウィンドウが非表示状態です")
            
            if win32gui.IsIconic(last_window):
                diagnosis["issues"].append("ターゲットウィンドウが最小化されています")
                
        except Exception as e:
            diagnosis["issues"].append(f"ターゲットウィンドウの情報取得に失敗: {e}")
    
    return diagnosis
```

### 2. パフォーマンス監視

```python
class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def start_timing(self, operation: str):
        """操作の計時開始"""
        self.metrics[operation] = {"start": time.time()}
    
    def end_timing(self, operation: str):
        """操作の計時終了"""
        if operation in self.metrics:
            self.metrics[operation]["end"] = time.time()
            self.metrics[operation]["duration"] = (
                self.metrics[operation]["end"] - self.metrics[operation]["start"]
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """メトリクスを取得"""
        return {
            "uptime": time.time() - self.start_time,
            "operations": self.metrics,
            "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024
        }

# 使用例
performance_monitor = PerformanceMonitor()

def monitored_hotkey_callback(hotkey_id, hotkey_info):
    """パフォーマンス監視付きのホットキーコールバック"""
    performance_monitor.start_timing("hotkey_processing")
    
    try:
        # 実際の処理
        # ... 
        pass
    finally:
        performance_monitor.end_timing("hotkey_processing")
```

## 開発のベストプラクティス

### 1. コーディング規約
- **型ヒント**: すべての関数とメソッドに型ヒントを付ける
- **ドキュメント**: 複雑な処理には詳細なdocstringを記述
- **エラーハンドリング**: 適切な例外処理とログ出力
- **依存性注入**: インターフェースを通じた疎結合な設計

### 2. 設定管理
- **バリデーション**: 設定値の妥当性確認
- **マイグレーション**: 設定ファイル形式の変更対応
- **バックアップ**: 重要な設定変更前の自動バックアップ

### 3. テスト戦略
- **単体テスト**: 各コンポーネントの独立したテスト
- **結合テスト**: コンポーネント間の相互作用テスト
- **モックオブジェクト**: Windows APIのモック化

### 4. ログ戦略
- **構造化ログ**: JSON形式での詳細なログ出力
- **ログレベル**: 適切なレベル分け（DEBUG, INFO, WARNING, ERROR）
- **ログローテーション**: ファイルサイズ制限と自動圧縮

## 最新の改善

### tkinterdnd2によるドラッグ&ドロップ改善（2025-08-25）

キーパッド設定のボタンドラッグ操作を大幅に改善しました。

#### 主な変更点
1. **tkinterdnd2ライブラリの導入**
   - OSネイティブのドラッグ&ドロップ機能を使用
   - 滑らかで直感的なドラッグ操作を実現

2. **フォールバック機能**
   - tkinterdnd2が利用できない場合は従来のシステムに自動切り替え
   - 互換性を保持した段階的移行

3. **操作方法の変更**
   - **ドラッグ&ドロップ**: ボタンを長押ししてドラッグで並び替え
   - **編集**: ダブルクリックでボタン編集ダイアログを開く
   - **右クリックメニュー**: 従来通り利用可能（編集・複製・削除）

#### 技術的詳細
```python
# 新しいドラッグハンドラー
def handle_drag_init(self, event, index):
    return (tkdnd.COPY, DND_TEXT, f"button_index_{index}")

def handle_drop(self, event, target_index):
    source_index = int(event.data.split("_")[2])
    # ボタン位置を入れ替え
    self.button_configs[source_index], self.button_configs[target_index] = \
        self.button_configs[target_index], self.button_configs[source_index]
```

#### 依存関係
- `tkinterdnd2>=0.3.0` を `requirements.txt` に追加
- 自動的にフォールバック機能で互換性を保持

---

このマニュアルは、Ultimate Virtual Keyboardの機能拡張と保守を効率的に行うためのガイドラインです。新機能の追加や既存機能の改善を行う際の参考として活用してください。