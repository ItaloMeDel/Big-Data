@echo off
echo ========================================================
echo   Compilando documento IEEE con BibTeX
echo ========================================================
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
echo ========================================================
echo   Compilacion finalizada exitosamente: main.pdf
echo ========================================================
