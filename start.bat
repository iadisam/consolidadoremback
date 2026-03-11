@echo off
echo ========================================
echo   API Backend - Consolidador REM
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no instalado
    echo Descargar desde: https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python encontrado
echo.

REM Verificar dependencias
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: No se pudieron instalar dependencias
        pause
        exit /b 1
    )
)

echo [OK] Dependencias instaladas
echo.

REM Verificar .env
if not exist .env (
    echo ADVERTENCIA: Archivo .env no encontrado
    echo Copiando .env.example a .env
    copy .env.example .env
    echo.
    echo IMPORTANTE: Editar .env con credenciales de SQL Server
    pause
)

REM Crear carpetas si no existen
if not exist uploads mkdir uploads
if not exist logs mkdir logs

echo.
echo ========================================
echo   Iniciando API en http://localhost:8000
echo   Documentacion: http://localhost:8000/docs
echo ========================================
echo.
echo Presiona Ctrl+C para detener
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
