@echo off
echo ========================================
echo CollabTrans 首次部署设置
echo ========================================

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python环境
    echo 请先安装Python 3.11或更高版本
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist ".venv" (
    echo 错误: 未找到虚拟环境
    echo 请先运行: uv venv && uv sync
    pause
    exit /b 1
)

REM 运行首次部署设置
echo 正在运行首次部署设置...
python setup_first_deploy.py

echo.
echo ========================================
echo 首次部署设置完成！
echo ========================================
echo.
echo 下一步操作：
echo 1. 安装Redis服务
echo 2. 编辑 local_secrets.json 设置API密钥
echo 3. 启动服务
echo.
echo 启动命令：
echo   .venv\Scripts\python.exe -m collabtrans.cli -i
echo.
echo 访问地址：http://127.0.0.1:8010
echo 默认登录：admin / admin123
echo.
pause
