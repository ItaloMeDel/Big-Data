param(
    [string]$Target = "Formato_Simple-Latex"
)

$targetName = [System.IO.Path]::GetFileNameWithoutExtension($Target)
$texFile = "$targetName.tex"

if (-not (Test-Path $texFile)) {
    Write-Error "No se encontro el archivo $texFile"
    exit 1
}

Write-Host "[1/3] Compilando $texFile con pdflatex..." -ForegroundColor Cyan
if (-not (Test-Path "build")) { New-Item -ItemType Directory -Path "build" | Out-Null }
& pdflatex "-aux-directory=build" -interaction=nonstopmode $texFile | Out-Null

if ((Test-Path "$targetName.bib") -or (Test-Path "referencias.bib")) {
    Write-Host "[2/3] Procesando bibliografia con bibtex..." -ForegroundColor Cyan
    & bibtex "build/$targetName" | Out-Null
    & pdflatex "-aux-directory=build" -interaction=nonstopmode $texFile | Out-Null
    & pdflatex "-aux-directory=build" -interaction=nonstopmode $texFile | Out-Null
} else {
    Write-Host "[2/3] Segunda pasada de pdflatex..." -ForegroundColor Cyan
    & pdflatex "-aux-directory=build" -interaction=nonstopmode $texFile | Out-Null
}

Write-Host "[3/3] Limpiando archivos residuales..." -ForegroundColor Cyan
Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
Remove-Item -Path "*.aux", "*.log", "*.out", "*.toc", "*.bbl", "*.blg", "*.fls", "*.fdb_latexmk", "*.synctex.gz", "texput.log" -ErrorAction SilentlyContinue

if (Test-Path "$targetName.pdf") {
    Write-Host "Exito: Generado $targetName.pdf de forma limpia (sin archivos residuales)." -ForegroundColor Green
} else {
    Write-Host "Error al compilar $texFile." -ForegroundColor Red
}
