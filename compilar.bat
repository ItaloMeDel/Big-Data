@echo off
set "TARGET=%~n1"
if "%TARGET%"=="" set "TARGET=Formato_Simple-Latex"

if not exist "%TARGET%.tex" (
    echo Error: No se encuentra %TARGET%.tex
    exit /b 1
)

echo [1/3] Compilando %TARGET%.tex...
if not exist "build" mkdir "build"
pdflatex -aux-directory=build -interaction=nonstopmode "%TARGET%.tex" > nul

if exist "%TARGET%.bib" (
    echo [2/3] Procesando bibliografia con bibtex...
    bibtex "build\%TARGET%" > nul
    pdflatex -aux-directory=build -interaction=nonstopmode "%TARGET%.tex" > nul
    pdflatex -aux-directory=build -interaction=nonstopmode "%TARGET%.tex" > nul
) else if exist "referencias.bib" (
    echo [2/3] Procesando bibliografia con bibtex...
    bibtex "build\%TARGET%" > nul
    pdflatex -aux-directory=build -interaction=nonstopmode "%TARGET%.tex" > nul
    pdflatex -aux-directory=build -interaction=nonstopmode "%TARGET%.tex" > nul
) else (
    echo [2/3] Segunda pasada de pdflatex...
    pdflatex -aux-directory=build -interaction=nonstopmode "%TARGET%.tex" > nul
)

echo [3/3] Limpiando archivos residuales...
if exist "build" rmdir /s /q "build"
if exist "*.aux" del /f /q *.aux 2>nul
if exist "*.log" del /f /q *.log 2>nul
if exist "*.out" del /f /q *.out 2>nul
if exist "*.toc" del /f /q *.toc 2>nul
if exist "*.bbl" del /f /q *.bbl 2>nul
if exist "*.blg" del /f /q *.blg 2>nul
if exist "*.fls" del /f /q *.fls 2>nul
if exist "*.fdb_latexmk" del /f /q *.fdb_latexmk 2>nul
if exist "*.synctex.gz" del /f /q *.synctex.gz 2>nul
if exist "texput.log" del /f /q texput.log 2>nul

if exist "%TARGET%.pdf" (
    echo Exito: Generado %TARGET%.pdf sin residuos.
) else (
    echo Error al compilar %TARGET%.tex.
)
