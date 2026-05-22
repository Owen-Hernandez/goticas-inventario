@echo off
echo.
echo  ==========================================
echo    Goticas de Aceite - Sistema Inventario
echo  ==========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python no esta instalado en este equipo.
    echo  Por favor instale Python desde https://www.python.org
    echo.
    pause
    exit /b
)

echo  Instalando dependencias...
pip install -r requirements.txt --quiet
echo.
echo  Iniciando sistema...
echo  Abra su navegador en: http://localhost:5000
echo  Para cerrar el sistema presione Ctrl+C
echo.
start "" http://localhost:5000
python app.py
pause
