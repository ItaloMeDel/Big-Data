@echo off
title MongoDB Compass y Servidor - Big Data UCSM
echo ========================================================
echo   Iniciando MongoDB Server y Compass
echo   Proyecto Integrador Big Data - Fase 2 (UCSM)
echo ========================================================

:: Verificar si mongod.exe ya esta ejecutandose
tasklist /FI "IMAGENAME eq mongod.exe" 2>NUL | find /I /N "mongod.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] El servidor MongoDB ya se encuentra en ejecucion en segundo plano.
) else (
    echo [INFO] Servidor MongoDB inactivo. Iniciando proceso mongod.exe en segundo plano...
    start "" /B "C:\UCSM\Semestre 10\Big Data\mongodb_dist\mongodb-win32-x86_64-windows-8.0.4\bin\mongod.exe" --config "C:\UCSM\Semestre 10\Big Data\mongod.cfg"
    echo [INFO] Esperando 3 segundos para la inicializacion del puerto 27017...
    timeout /t 3 /nobreak >NUL
)

echo [INFO] Lanzando MongoDB Compass...
start "" "C:\UCSM\Semestre 10\Big Data\compass_dist\MongoDBCompass.exe" mongodb://127.0.0.1:27017
echo ========================================================
echo [EXITO] Compass conectado a: mongodb://127.0.0.1:27017
echo Base de datos: era5_climate_db
echo ========================================================
timeout /t 2 >NUL
