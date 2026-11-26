Write-Host "Compilando documento IEEE con BibTeX..." -ForegroundColor Cyan
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
Write-Host "Compilación completada. Archivo generado: main.pdf" -ForegroundColor Green
