# Virtual Functions v2.0

Windows 用フローティング仮想キーボード。物理キーボードに存在しない F13–F24 や日本語IMEキー(変換・無変換・かな・半角/全角)、修飾キー付きコンボ(Ctrl+C など)を、作業中のアプリからフォーカスを奪わずにワンクリックで送信します。

C#/.NET 10 + WPF による v2.0 全面書き直し版です(v1.x は Python/CustomTkinter 製 — `old/python_v1.2/` に参照用として保存)。

## 主な機能

- **フローティングキーストリップ** — 常に最前面・枠なし・半透明。`WS_EX_NOACTIVATE` によりクリックしてもフォーカスを奪わないため、キーは直前まで使っていたアプリへそのまま届きます
- **キー送信** — F1–F24 / 英数字 / ナビゲーション / 記号 / 日本語IMEキー。修飾キー(Ctrl/Shift/Alt/Win)の同時押しは 1 回の `SendInput` 呼び出しでアトミックに送信
- **プリセット** — ボタンセットを名前付きで保存・切替・インポート/エクスポート
- **アプリ連動 (app-binding)** — 前面ウィンドウ(タイトル / プロセス名 / クラス名)に応じてプリセットを自動切替。優先度付き・部分/完全一致対応。`SetWinEventHook` によるイベント駆動でポーリングなし
- **ボタンマネージャ** — ボタンの追加/編集/複製/並べ替え、キーキャプチャ、絵文字アイコン(Segoe UI Emoji ネイティブ描画・オフライン完結)、画像アイコン、色設定、トグルラッチ
- **遅延入力モード** — 設定した秒数のカウントダウン(⏱️ポップアップ)後にキーを送信
- **表示カスタマイズ** — 通常/ミニ表示、横/縦レイアウト、ライト/ダークテーマ、ツールチップ
- **ポータブル設定** — 設定は exe と同じフォルダの `settings.json` + `presets/*.json`(書き込み不可なら `%APPDATA%\VirtualFunctions` へ自動フォールバック)。保存はすべてアトミック書き込み

## 動作環境

- Windows 10 / 11 (64bit)
- 配布用単一 exe は自己完結型(.NET ランタイムのインストール不要)

## 使い方

1. `VirtualFunctions.exe` を任意のフォルダに置いて起動
2. ストリップをドラッグで移動(位置は自動保存)
3. 右クリックメニューから: ボタンマネージャ / 遅延入力モード / 表示モード / レイアウト / テーマ / 終了

### v1 (Python 版) からの移行

v1 の `config.json` と `presets/` を exe と同じフォルダに置いて初回起動すると、自動で v2 形式へ変換されます。v1 ファイルは変更されず、プリセットの原本は `presets/_v1_backup/` に保存されます。ボタン構成・ウィンドウ位置・テーマ・遅延時間が引き継がれます。

## 開発

### 必要なもの

- [.NET 10 SDK](https://dotnet.microsoft.com/download/dotnet/10.0)(`winget install Microsoft.DotNet.SDK.10`)

### コマンド

```bash
dotnet build                                  # ビルド
dotnet run --project src/VirtualFunctions.App # 実行(Debug時はv1移行を自動検証)
dotnet test                                   # 単体テスト
dotnet format                                 # コード整形
```

リリース用単一 exe の作成:

```bash
dotnet publish src/VirtualFunctions.App -c Release -r win-x64 --self-contained -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:EnableCompressionInSingleFile=true -p:DebugType=None -p:DebugSymbols=false -o publish
```

### プロジェクト構成

```
src/
├── VirtualFunctions.Core/   # UI・Win32 非依存(単体テスト対象)
│   ├── Models/              # 設定・プリセット・ボタンのデータモデル (schema v2)
│   ├── Input/               # KeyMap: キー名⇔VK 変換の唯一のテーブル、コンボ解析
│   ├── Binding/             # AppBindingMatcher: アプリ連動の純関数マッチング
│   └── Config/              # 設定/プリセットの永続化、v1 移行、アトミック保存
└── VirtualFunctions.App/    # WPF アプリ (net10.0-windows, x64)
    ├── Interop/             # CsWin32 による SendInput / WinEventHook / ウィンドウスタイル
    ├── Services/            # プリセット・アプリ連動・遅延送信・テーマ
    ├── ViewModels/          # CommunityToolkit.Mvvm ベースの VM
    └── Views/               # フローティングストリップ、ボタンマネージャ、各ダイアログ
tests/
└── VirtualFunctions.Core.Tests/  # xUnit(KeyMap / マッチャ / 移行 / アトミック保存)
```

設計上の要点:

- **フォーカスを奪わない**ことが本アプリの核。`WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_LAYERED` を `SourceInitialized` で適用し、透過は `SetLayeredWindowAttributes`(`AllowsTransparency` 不使用)
- Core は WPF / Win32 に一切依存しないため、キーマッピング・マッチング・移行ロジックはすべて高速な単体テストで検証
- P/Invoke は [CsWin32](https://github.com/microsoft/CsWin32) のソース生成(`NativeMethods.txt`)で、手書き struct 定義なし
- `Directory.Build.props` で全プロジェクトに nullable / TreatWarningsAsErrors / アナライザを強制

## トラブルシューティング

- **キーが届かない** — 送信先が管理者権限アプリの場合、UIPI により通常権限からの `SendInput` は無視されます。本アプリを管理者として実行してください
- **ログ** — exe 隣の `logs/app-*.log`(1MB×3 ローテーション)
- **設定が壊れた** — `settings.json` を削除すると既定値で再生成。壊れたファイルは `.corrupt` として保存されます

## ライセンス

MIT License — [LICENSE](LICENSE)
