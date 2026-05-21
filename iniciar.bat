@echo off
echo.
echo  ==========================================
echo    Goticas de Aceite - Sistema Inventario
echo  ==========================================
echo.
echo  Instalando dependencias...
pip install -r requirements.txt --quiet
echo.
echo  Iniciando servidor...
echo  Abre tu navegador en: http://localhost:5000
echo.
python app.py
pause
