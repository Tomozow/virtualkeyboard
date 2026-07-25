# Ultimate Virtual Keyboard - Python版

ホットキーコンフィグシステムのPython実装です。

## 機能

- **ホットキー設定**: F1~F6に修飾キーを組み合わせて、F13~F24を送信
- **2つのキーセット**: 
  - Set1: F13-F18
  - Set2: F19-F24
- **修飾キー**: Shift、Ctrl、Alt、Space（Win）
- **GUIダイアログ**: tkinterベースの設定画面
- **リアルタイムプレビュー**: 設定時にキー組み合わせを確認
- **アクティビティログ**: キー送信履歴を表示

## 必要環境

- Python 3.6以上
- Windows OS
- pywin32ライブラリ

## インストール・実行方法

### 方法1: バッチファイル使用
```
install_and_run.bat
```

### 方法2: 手動インストール
```bash
pip install pywin32
python virtual_keyboard.py
```

## 使用方法

1. **アプリケーション起動**
   - `virtual_keyboard.py`を実行
   - メインウィンドウが表示されます

2. **ホットキー設定**
   - 「Hotkey Config」ボタンをクリック
   - Set1/Set2を有効化
   - 修飾キーを選択
   - 「Save & Apply」で設定保存

3. **動作確認**
   - 設定したホットキーを押下
   - アクティビティログで動作確認

## 設定例

### Set1: Shift+Alt+F1→F13
```json
{
  "hotkeys": {
    "set1": {
      "enabled": true,
      "modifiers": {
        "shift": true,
        "alt": true,
        "ctrl": false,
        "space": false
      }
    }
  }
}
```

### 実際の動作
- `Shift+Alt+F1` → F13送信
- `Shift+Alt+F2` → F14送信
- `Shift+Alt+F3` → F15送信

## ファイル構成

- `virtual_keyboard.py` - メインプログラム
- `config.json` - 設定ファイル（自動生成）
- `requirements.txt` - Python依存関係
- `install_and_run.bat` - インストール・実行スクリプト

## トラブルシューティング

### pywin32が見つからない
```bash
pip install pywin32
```

### ホットキーが動作しない
1. 管理者権限で実行
2. 他のアプリケーションとの競合確認
3. アクティビティログで登録状況確認

### 設定が反映されない
1. 「Reload Config」ボタンクリック
2. アプリケーション再起動

## C#版との違い

- **言語**: Python（実行速度はC#より遅い）
- **GUI**: tkinter使用
- **依存関係**: pywin32が必要
- **配布**: ソースコード形式
- **デバッグ**: アクティビティログで詳細確認可能