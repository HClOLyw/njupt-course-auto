@echo off
chcp 65001 >nul
rem ============================================
rem  南邮在线课堂自动化助手 - 一键打包脚本
rem  用法：双击运行，或命令行执行 build.bat
rem  （需要先安装 Python 与 PyInstaller）
rem ============================================
cd /d %~dp0

echo [1/3] 检查 Python...
python --version || (echo 未找到 Python，请先安装并加入 PATH & pause & exit /b 1)

echo [2/3] 安装/检查 PyInstaller...
python -m pip install pyinstaller -q || (echo PyInstaller 安装失败 & pause & exit /b 1)

echo [3/3] 生成 app_icon.ico...
if not exist app_icon.ico (
    python make_icon.py || echo 图标生成失败（不影响打包）
)

echo 开始打包（约 1-3 分钟）...
python -m PyInstaller -F -w -n "NJUPT课程助手" ^
    --icon app_icon.ico ^
    --add-data "config.json;." ^
    --add-data "exam_questions.json;." ^
    --add-data "njupt_api.py;." ^
    --add-data "njupt_lab_api.py;." ^
    --add-data "app_icon.ico;." ^
    njupt_gui.py

if exist "dist\NJUPT课程助手.exe" (
    echo.
    echo ============================================
    echo   打包成功！程序位于：dist\NJUPT课程助手.exe
    echo ============================================
) else (
    echo 打包失败，请查看上方错误信息
)
pause
