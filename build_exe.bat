@echo off
chcp 65001 >nul
echo 正在打包 openNavy...

REM 检查字体文件
if not exist wqy-microhei.ttc (
    echo 错误：找不到 wqy-microhei.ttc
    echo 请将字体文件放入此目录后再试
    pause
    exit /b 1
)

REM 用 PyInstaller 打包（单文件 + 无控制台）
pyinstaller --clean --noconsole --onefile --add-data "wqy-microhei.ttc;." main.py

REM 重命名输出
if exist dist\main.exe (
    move /Y dist\main.exe dist\openNavy.exe >nul
    echo.
    echo 打包成功！exe 位于：dist\openNavy.exe
) else (
    echo 打包失败，请检查错误信息
)

pause
