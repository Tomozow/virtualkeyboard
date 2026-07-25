# Ultimate Virtual Keyboard - API リファレンス

## 目次
1. [インターフェース一覧](#インターフェース一覧)
2. [データクラス](#データクラス)
3. [コア実装クラス](#コア実装クラス)
4. [設定管理](#設定管理)
5. [ユーティリティ](#ユーティリティ)

## インターフェース一覧

### IConfigManager
設定管理の基底インターフェース

```python
class IConfigManager(ABC):
    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        pass
    
    @abstractmethod
    def save_config(self, config: Dict[str, Any]) -> bool:
        """設定ファイルを保存"""
        pass
    
    @abstractmethod
    def get_hotkey_config(self, set_name: str) -> Optional[HotkeyConfig]:
        """ホットキー設定を取得"""
        pass
    
    @abstractmethod
    def get_focus_config(self) -> FocusConfig:
        """フォーカス復帰設定を取得"""
        pass
```

### IHotkeyManager
ホットキー管理の基底インターフェース

```python
class IHotkeyManager(ABC):
    @abstractmethod
    def register_hotkey(self, hotkey_id: int, modifiers: int, vk_code: int, description: str) -> bool:
        """ホットキーを登録
        
        Args:
            hotkey_id: ホットキーID (1000以上推奨)
            modifiers: 修飾キー (MOD_CTRL, MOD_ALT, MOD_SHIFT, MOD_WINの組み合わせ)
            vk_code: 仮想キーコード (VK_F1 = 0x70など)
            description: 説明文
        
        Returns:
            bool: 登録成功の場合True
        """
        pass
    
    @abstractmethod
    def unregister_hotkey(self, hotkey_id: int) -> bool:
        """ホットキーの登録解除"""
        pass
    
    @abstractmethod
    def unregister_all(self) -> None:
        """全ホットキーの登録解除"""
        pass
```

### IKeySender
キー送信の基底インターフェース

```python
class IKeySender(ABC):
    @abstractmethod
    def send_key(self, vk_code: int) -> bool:
        """仮想キーを送信
        
        Args:
            vk_code: 仮想キーコード
        
        Returns:
            bool: 送信成功の場合True
        """
        pass
    
    @staticmethod
    @abstractmethod
    def vk_code_to_name(vk_code: int) -> str:
        """VKコードをキー名に変換"""
        pass
```

### IFocusManager
フォーカス管理の基底インターフェース

```python
class IFocusManager(ABC):
    @abstractmethod
    def restore_focus(self, target_window: int) -> bool:
        """フォーカスを復帰
        
        Args:
            target_window: ターゲットウィンドウハンドル
        
        Returns:
            bool: 復帰成功の場合True
        """
        pass
    
    @abstractmethod
    def start_monitoring(self) -> None:
        """フォーカス監視を開始"""
        pass
    
    @abstractmethod
    def stop_monitoring(self) -> None:
        """フォーカス監視を停止"""
        pass
    
    @abstractmethod
    def get_last_focus_window(self) -> Optional[int]:
        """最後のフォーカスウィンドウを取得"""
        pass
```

## データクラス

### FocusRestoreMethod
フォーカス復帰方法の列挙型

```python
class FocusRestoreMethod(Enum):
    SIMPLE = "simple"      # シンプルなSetForegroundWindow
    ENHANCED = "enhanced"  # Alt+SetForegroundWindow（推奨）
    FORCE = "force"        # 複数方法の組み合わせ
```

### HotkeyConfig
ホットキー設定データクラス

```python
@dataclass
class HotkeyConfig:
    target_keys: List[str]           # ターゲットキーのリスト (["F13", "F14", ...])
    modifiers: Dict[str, bool]       # 修飾キー設定 ({"shift": True, "ctrl": False, ...})
    enabled: bool                    # 有効/無効フラグ
```

### FocusConfig
フォーカス復帰設定データクラス

```python
@dataclass
class FocusConfig:
    enabled: bool = True                                    # 有効/無効フラグ
    method: FocusRestoreMethod = FocusRestoreMethod.ENHANCED # 復帰方法
    delay: int = 50                                         # 復帰遅延時間(ms)
    debug: bool = False                                     # デバッグモード
```

### ButtonConfig
ボタン設定データクラス

```python
@dataclass
class ButtonConfig:
    key: str      # キー名 ("F13", "F14", etc.)
    label: str    # ボタンラベル
    icon: str     # アイコン絵文字
```

## コア実装クラス

### ConfigManager
設定管理の実装クラス

#### 主要メソッド

```python
def __init__(self, config_path: str = "config.json"):
    """初期化
    
    Args:
        config_path: 設定ファイルのパス
    """

def load_config(self) -> Dict[str, Any]:
    """設定ファイルを読み込み
    
    Returns:
        設定辞書。ファイルが存在しない場合はデフォルト設定を作成
    """

def save_config(self, config: Dict[str, Any] = None) -> bool:
    """設定ファイルを保存
    
    Args:
        config: 保存する設定辞書（Noneの場合は現在の設定）
    
    Returns:
        保存成功の場合True
    """

def get_hotkey_config(self, set_name: str) -> Optional[HotkeyConfig]:
    """ホットキー設定を取得
    
    Args:
        set_name: セット名 ("set1", "set2")
    
    Returns:
        HotkeyConfigオブジェクト、または存在しない場合None
    """

def get_focus_config(self) -> FocusConfig:
    """フォーカス設定を取得
    
    Returns:
        FocusConfigオブジェクト
    """

def get_modifiers_value(self, modifiers_dict: Dict[str, bool]) -> int:
    """修飾キー辞書からWindows API用の値を取得
    
    Args:
        modifiers_dict: 修飾キー設定辞書
    
    Returns:
        Windows API用の修飾キー値
    """

def key_name_to_vk(self, key_name: str) -> int:
    """キー名をVKコードに変換
    
    Args:
        key_name: キー名 ("F1", "F13", etc.)
    
    Returns:
        仮想キーコード
    """
```

#### 設定ファイル構造

```json
{
  "hotkeys": {
    "set1": {
      "targetKeys": ["F13", "F14", "F15", "F16", "F17", "F18"],
      "modifiers": {
        "shift": false,
        "ctrl": false,
        "alt": false,
        "space": false
      },
      "enabled": false
    },
    "set2": {
      "targetKeys": ["F19", "F20", "F21", "F22", "F23", "F24"],
      "modifiers": {
        "shift": false,
        "ctrl": false,
        "alt": false,
        "space": false
      },
      "enabled": false
    }
  },
  "triggerKeys": ["F1", "F2", "F3", "F4", "F5", "F6"],
  "focusRestore": {
    "enabled": true,
    "method": "enhanced",
    "delay": 50,
    "debug": false
  },
  "floatingWindow": {
    "enabled": true,
    "position": {"x": 100, "y": 100},
    "buttons": [
      {
        "key": "F13",
        "label": "F13",
        "icon": "🔴"
      }
    ]
  }
}
```

### HotkeyManager
ホットキー管理の実装クラス

#### 主要メソッド

```python
def __init__(self, callback: Optional[Callable] = None):
    """初期化
    
    Args:
        callback: ホットキー押下時のコールバック関数
                 callback(hotkey_id: int, hotkey_info: Dict[str, Any])
    """

def create_message_window(self) -> bool:
    """メッセージ受信用の隠しウィンドウを作成
    
    Returns:
        作成成功の場合True
    """

def register_hotkey(self, hotkey_id: int, modifiers: int, vk_code: int, description: str = "") -> bool:
    """ホットキーを登録
    
    Args:
        hotkey_id: 一意のホットキーID
        modifiers: 修飾キー（MOD_CTRL | MOD_ALTなど）
        vk_code: 仮想キーコード
        description: 説明文
    
    Returns:
        登録成功の場合True
        
    Note:
        同一IDのホットキーは自動的に上書きされます
    """

def set_target_key(self, hotkey_id: int, target_vk: int) -> None:
    """ターゲットキーを設定
    
    Args:
        hotkey_id: ホットキーID
        target_vk: 送信対象の仮想キーコード
    """

def start_message_loop(self) -> None:
    """メッセージループ開始（別スレッドで実行）"""

def stop_message_loop(self) -> None:
    """メッセージループ停止"""
```

#### コールバック関数の形式

```python
def hotkey_callback(hotkey_id: int, hotkey_info: Dict[str, Any]) -> None:
    """ホットキーコールバック関数
    
    Args:
        hotkey_id: 押下されたホットキーのID
        hotkey_info: ホットキー情報辞書
                    {
                        'modifiers': int,      # 修飾キー値
                        'vk_code': int,        # 仮想キーコード
                        'description': str,    # 説明文
                        'target_key': int      # ターゲットキー
                    }
    """
```

### KeySender
キー送信の実装クラス

#### 主要メソッド

```python
def send_key(self, vk_code: int) -> bool:
    """仮想キーコードを送信
    
    Args:
        vk_code: 送信する仮想キーコード
    
    Returns:
        送信成功の場合True
        
    Note:
        キー押下→50ms待機→キー解放の順で実行されます
    """

@staticmethod
def vk_code_to_name(vk_code: int) -> str:
    """VKコードをキー名に変換
    
    Args:
        vk_code: 仮想キーコード
    
    Returns:
        キー名文字列（例: "F1", "F13", "VK_41"）
    """
```

#### 仮想キーコード対応表

| 範囲 | キー | VKコード |
|------|------|----------|
| F1-F12 | F1-F12 | 0x70-0x7B |
| F13-F24 | F13-F24 | 0x7C-0x87 |

### FocusManager
フォーカス管理の実装クラス

#### 主要メソッド

```python
def __init__(self, config: FocusConfig):
    """初期化
    
    Args:
        config: フォーカス復帰設定
    """

def restore_focus_simple(self, target_window: int) -> bool:
    """シンプルなフォーカス復帰
    
    Args:
        target_window: ターゲットウィンドウハンドル
    
    Returns:
        復帰成功の場合True
        
    Note:
        SetForegroundWindow + BringWindowToTopを使用
    """

def restore_focus_enhanced(self, target_window: int) -> bool:
    """拡張フォーカス復帰（Alt+Tab方式）
    
    Args:
        target_window: ターゲットウィンドウハンドル
    
    Returns:
        復帰成功の場合True
        
    Note:
        Alt key + SetForegroundWindowを使用（推奨方式）
    """

def restore_focus_force(self, target_window: int) -> bool:
    """強制フォーカス復帰（複数方法の組み合わせ）
    
    Args:
        target_window: ターゲットウィンドウハンドル
    
    Returns:
        復帰成功の場合True
        
    Note:
        最小化復元 + AttachThreadInput + ShowWindow + SetFocusを順次実行
    """

def restore_focus(self, target_window: int) -> bool:
    """設定に基づいてフォーカスを復帰
    
    Args:
        target_window: ターゲットウィンドウハンドル
    
    Returns:
        復帰成功の場合True
        
    Note:
        設定されたmethodに基づいて適切な復帰方法を選択
        失敗時は自動的にフォールバック
    """

def start_monitoring(self) -> None:
    """フォーカス監視を開始
    
    Note:
        200msごとにアクティブウィンドウをチェック
        変更を検出すると last_focus_window を更新
    """
```

## 設定管理

### 設定の読み書き

```python
# 設定の読み込み
config_manager = ConfigManager()
config = config_manager.load_config()

# 特定設定の取得
hotkey_config = config_manager.get_hotkey_config("set1")
focus_config = config_manager.get_focus_config()

# 設定の保存
config["hotkeys"]["set1"]["enabled"] = True
config_manager.save_config(config)
```

### 設定の妥当性確認

```python
def validate_hotkey_config(config: HotkeyConfig) -> List[str]:
    """ホットキー設定の妥当性を確認
    
    Args:
        config: 確認するホットキー設定
    
    Returns:
        エラーメッセージのリスト（空の場合は問題なし）
    """
    errors = []
    
    if not config.target_keys:
        errors.append("ターゲットキーが設定されていません")
    
    if len(config.target_keys) > 6:
        errors.append("ターゲットキーは最大6個まで設定可能です")
    
    # F13-F24の範囲チェック
    for key in config.target_keys:
        if key.startswith("F"):
            try:
                f_num = int(key[1:])
                if not (13 <= f_num <= 24):
                    errors.append(f"無効なファンクションキー: {key}")
            except ValueError:
                errors.append(f"無効なキー名: {key}")
    
    # 修飾キーの確認
    if not any(config.modifiers.values()):
        errors.append("少なくとも一つの修飾キーを有効にする必要があります")
    
    return errors
```

## ユーティリティ

### Windows API ヘルパー

```python
class WindowsAPIHelper:
    """Windows API操作のヘルパークラス"""
    
    @staticmethod
    def get_window_info(hwnd: int) -> Dict[str, Any]:
        """ウィンドウ情報を取得
        
        Args:
            hwnd: ウィンドウハンドル
        
        Returns:
            ウィンドウ情報辞書
        """
        try:
            return {
                "title": win32gui.GetWindowText(hwnd),
                "class_name": win32gui.GetClassName(hwnd),
                "is_visible": win32gui.IsWindowVisible(hwnd),
                "is_iconic": win32gui.IsIconic(hwnd),
                "process_id": win32gui.GetWindowThreadProcessId(hwnd)[1],
                "rect": win32gui.GetWindowRect(hwnd)
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def enum_visible_windows() -> List[Dict[str, Any]]:
        """表示されているウィンドウを列挙
        
        Returns:
            ウィンドウ情報のリスト
        """
        windows = []
        
        def enum_callback(hwnd, param):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # タイトルがあるウィンドウのみ
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "class_name": win32gui.GetClassName(hwnd)
                    })
            return True
        
        win32gui.EnumWindows(enum_callback, 0)
        return windows
    
    @staticmethod
    def is_admin() -> bool:
        """管理者権限で実行されているかチェック
        
        Returns:
            管理者権限の場合True
        """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
```

### ログユーティリティ

```python
class LogUtils:
    """ログ関連のユーティリティ"""
    
    @staticmethod
    def setup_logger(name: str, log_file: str, level: str = "INFO") -> logging.Logger:
        """ロガーをセットアップ
        
        Args:
            name: ロガー名
            log_file: ログファイルパス
            level: ログレベル
        
        Returns:
            設定されたロガー
        """
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        
        # ファイルハンドラ
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # コンソールハンドラ
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(levelname)s - %(message)s'
        ))
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    @staticmethod
    def log_function_call(func):
        """関数呼び出しをログに記録するデコレータ
        
        Args:
            func: デコレート対象の関数
        
        Returns:
            デコレートされた関数
        """
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned: {result}")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised exception: {e}")
                raise
        return wrapper
```

### パフォーマンス測定

```python
class PerformanceTimer:
    """パフォーマンス測定用のコンテキストマネージャ"""
    
    def __init__(self, name: str, logger: logging.Logger = None):
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        duration = (end_time - self.start_time) * 1000  # ミリ秒
        self.logger.info(f"[PERF] {self.name}: {duration:.2f}ms")

# 使用例
with PerformanceTimer("Hotkey Registration"):
    hotkey_manager.register_hotkey(1001, MOD_CTRL | MOD_ALT, 0x7C, "Test")
```

---

このAPIリファレンスは、Ultimate Virtual Keyboardのプログラマティックな操作と拡張開発のための詳細な仕様書です。各クラスとメソッドの正確な使用方法を理解し、効果的な機能拡張を行うための参考として活用してください。