# Ultimate Virtual Keyboard

Windowsでファンクションキー（F13-F24）を仮想的に送信するPython製ホットキーツール

## 概要

Ultimate Virtual Keyboardは、物理的に存在しないファンクションキー（F13-F24）を、F1-F6キーと修飾キーの組み合わせで送信できるツールです。フォーカス復帰機能により、ホットキー押下後に元のアプリケーションにフォーカスを戻すことができます。

## 主な機能

### ✨ **ホットキー機能**
- F1-F6 + 修飾キー組み合わせでF13-F24を送信
- 2つの独立したホットキーセット（Set1, Set2）
- Shift, Ctrl, Alt, Spaceキーの組み合わせサポート
- Windows APIによる確実なキー送信

### 🎯 **フォーカス復帰機能**  
- ホットキー実行後に元のウィンドウへ自動復帰
- 3つの復帰方式（Simple/Enhanced/Force）
- アプリケーション別最適化対応
- リアルタイムフォーカス監視

### ⚙️ **高度な設定機能**
- JSON形式の設定ファイル
- GUIベースの設定ダイアログ
- デバッグモードとログ機能
- 設定ファイルの自動バックアップ

### 🪟 **直感的なUI**
- 自動サイズ調整・センタリング対応
- 複数の設定ダイアログ
- リアルタイムデバッグウィンドウ
- フォーカステスト機能

## インストールと実行

### 必要な環境
- Windows 10/11
- Python 3.8以上
- 管理者権限（ホットキー登録のため）

### 依存関係

```bash
pip install -r requirements.txt
```

requirements.txt:
```
pywin32>=305
```

### 実行方法

#### 1. オリジナル版
```bash
python virtual_keyboard_fixed.py
```

#### 2. リファクタリング版（推奨）
```bash
python virtual_keyboard_refactored.py
```

## ファイル構成

```
virtualkeyboard/
├── virtual_keyboard_fixed.py      # オリジナル版メインファイル
├── virtual_keyboard_refactored.py # リファクタリング版メインファイル
├── config.json                    # 設定ファイル
├── debug_log.txt                  # デバッグログ
├── requirements.txt               # Python依存関係
├── backup/                        # バックアップディレクトリ
│   └── 20250825_1859/            # タイムスタンプ付きバックアップ
├── DEVELOPMENT_MANUAL.md          # 開発者マニュアル
├── API_REFERENCE.md               # APIリファレンス
└── README.md                      # このファイル
```

## 基本的な使用方法

### 1. アプリケーションの起動
1. 管理者権限でコマンドプロンプトまたはPowerShellを開く
2. `python virtual_keyboard_refactored.py` を実行
3. メインウィンドウが表示されます

### 2. ホットキーの設定
1. **「Hotkey Config」**ボタンをクリック
2. Set1またはSet2を有効化
3. 修飾キーを選択（Shift, Ctrl, Alt, Space）
4. **「Save & Apply」**で設定保存

### 3. フォーカス復帰の設定
1. **「Focus Config」**ボタンをクリック  
2. 復帰方法を選択：
   - **Simple**: 基本的な復帰
   - **Enhanced**: Alt+復帰（推奨）
   - **Force**: 強制復帰（複数手法組み合わせ）
3. 遅延時間を調整（10-1000ms）

### 4. テストとデバッグ
- **「Test Focus」**: フォーカス復帰のテスト
- **「Debug Info」**: システム情報表示
- **「Focus Debug」**: リアルタイム監視ウィンドウ

## 設定例

### 基本設定（Set1のみ使用）
```json
{
  "hotkeys": {
    "set1": {
      "targetKeys": ["F13", "F14", "F15", "F16", "F17", "F18"],
      "modifiers": {
        "shift": true,
        "ctrl": false, 
        "alt": true,
        "space": false
      },
      "enabled": true
    }
  }
}
```
→ Shift+Alt+F1でF13送信、Shift+Alt+F2でF14送信...

### 応用設定（2セット使用）
```json
{
  "hotkeys": {
    "set1": {
      "targetKeys": ["F13", "F14", "F15", "F16", "F17", "F18"],
      "modifiers": {"shift": true, "ctrl": true, "alt": false, "space": false},
      "enabled": true
    },
    "set2": {
      "targetKeys": ["F19", "F20", "F21", "F22", "F23", "F24"], 
      "modifiers": {"shift": false, "ctrl": true, "alt": true, "space": false},
      "enabled": true
    }
  }
}
```
→ Shift+Ctrl+F1〜F6でF13〜F18、Ctrl+Alt+F1〜F6でF19〜F24

## アーキテクチャ

### リファクタリング版の構造

```
VirtualKeyboardApp
├── ConfigManager      # 設定管理
├── HotkeyManager      # ホットキー処理  
├── KeySender          # キー送信
├── FocusManager       # フォーカス制御
└── UI Components      # 各種ダイアログ
```

### 主要インターフェース
- `IConfigManager`: 設定管理インターフェース
- `IHotkeyManager`: ホットキー管理インターフェース  
- `IKeySender`: キー送信インターフェース
- `IFocusManager`: フォーカス管理インターフェース

## 開発者向け情報

### 機能拡張
新機能の追加方法については以下のドキュメントを参照：
- [開発者マニュアル](DEVELOPMENT_MANUAL.md)
- [APIリファレンス](API_REFERENCE.md)

### カスタマイズ例

#### 新しいフォーカス復帰方法の追加
```python
class FocusManager(IFocusManager):
    def restore_focus_custom(self, target_window: int) -> bool:
        # カスタム実装
        window_class = win32gui.GetClassName(target_window)
        if "Chrome" in window_class:
            return self._restore_chrome_focus(target_window)
        # ...
```

#### 新しいキー送信方式の追加  
```python
class KeySender(IKeySender):
    def send_key_combination(self, keys: List[int]) -> bool:
        # 複数キー同時送信
        for vk_code in keys:
            user32.keybd_event(vk_code, 0, 0, 0)
        # ...
```

## トラブルシューティング

### よくある問題

#### ホットキーが動作しない
1. **管理者権限で実行しているか確認**
2. 他のアプリケーションとの競合確認
3. Windows Defenderのリアルタイム保護を一時無効化
4. デバッグログ（debug_log.txt）を確認

#### フォーカス復帰が失敗する
1. **Focus Config**で復帰方法を"Force"に変更
2. 遅延時間を100ms以上に設定
3. **Debug Info**でターゲットウィンドウを確認
4. 特定アプリケーション向けカスタム実装を検討

### ログの確認
```bash
# リアルタイムでログを監視
tail -f debug_log.txt

# エラーレベルのログのみ抽出
grep "ERROR" debug_log.txt
```

### システム要件の確認
```python
# 管理者権限の確認
import ctypes
print("Admin:", ctypes.windll.shell32.IsUserAnAdmin())

# Python環境の確認
import sys
print("Python:", sys.version)

# 依存関係の確認
import win32gui, win32con, win32api
print("pywin32: OK")
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## バージョン履歴

### v2.0.0 (Refactored) - 2025/08/25
- アーキテクチャの完全リファクタリング
- インターフェース設計によるモジュール化
- 型ヒント対応とPython 3.8+サポート
- 包括的なドキュメント整備
- パフォーマンス向上とバグ修正

### v1.x (Original)
- 基本的なホットキー機能
- フォーカス復帰機能の実装
- GUI設定ダイアログ
- デバッグ機能の追加

## 貢献

プロジェクトへの貢献を歓迎します：

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

### 開発ガイドライン
- [開発者マニュアル](DEVELOPMENT_MANUAL.md)に従って開発
- 型ヒントとdocstringを必須とする
- 単体テストの追加推奨
- ログレベルに適したメッセージ出力

## サポート

問題や質問がある場合：

1. [Issues](https://github.com/your-repo/virtual-keyboard/issues)で既存の問題を検索
2. 新しいissueを作成（テンプレートに従って記入）
3. [Discussions](https://github.com/your-repo/virtual-keyboard/discussions)で質問・提案

---

**Ultimate Virtual Keyboard** - より効率的なキーボード操作を実現