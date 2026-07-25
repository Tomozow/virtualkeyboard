@echo off
REM Virtual Functions - プロセス緊急クリーンアップバッチファイル
REM 管理者権限で実行することを推奨

echo ========================================
echo Virtual Functions 緊急クリーンアップ
echo ========================================
echo.

REM Pythonの存在確認
python --version >nul 2>&1
if errorlevel 1 (
    echo エラー: Python が見つかりません。
    echo Python がインストールされ、PATH に追加されていることを確認してください。
    pause
    exit /b 1
)

REM 現在のディレクトリを表示
echo 実行ディレクトリ: %CD%
echo.

REM psutilの存在確認
python -c "import psutil" >nul 2>&1
if errorlevel 1 (
    echo 警告: psutil が見つかりません。インストールを試行中...
    pip install psutil
    if errorlevel 1 (
        echo エラー: psutil のインストールに失敗しました。
        echo 手動でインストールしてください: pip install psutil
        pause
        exit /b 1
    )
)

echo ✅ 依存関係の確認が完了しました。
echo.

REM メニュー表示
echo 実行モードを選択してください:
echo 1. 対話式クリーンアップ（推奨）
echo 2. 緊急自動クリーンアップ（強制終了）
echo 3. 単純なプロセス確認
echo.
set /p choice="選択 (1-3): "

if "%choice%"=="1" (
    echo.
    echo 📋 対話式クリーンアップを開始します...
    python cleanup_processes.py
) else if "%choice%"=="2" (
    echo.
    echo 🚨 緊急自動クリーンアップを開始します...
    echo 警告: すべての関連プロセスが強制終了されます。
    set /p confirm="続行しますか？ (y/N): "
    if /i "!confirm!"=="y" (
        python cleanup_processes.py --force
    ) else (
        echo キャンセルされました。
    )
) else if "%choice%"=="3" (
    echo.
    echo 🔍 プロセス確認のみ実行します...
    tasklist | findstr /i python
    echo.
    echo 上記がPythonプロセスの一覧です。
) else (
    echo 無効な選択です。
)

echo.
echo クリーンアップが完了しました。
pause