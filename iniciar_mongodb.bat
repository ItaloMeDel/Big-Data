@echo off
title Servidor MongoDB - Big Data UCSM
echo ========================================================
echo   Iniciando Servidor MongoDB (Puerto 27017)
echo   Ruta de datos: C:\UCSM\Semestre 10\Big Data\data_db
echo ========================================================
"C:\UCSM\Semestre 10\Big Data\mongodb_dist\mongodb-win32-x86_64-windows-8.0.4\bin\mongod.exe" --config "C:\UCSM\Semestre 10\Big Data\mongod.cfg"
pause
