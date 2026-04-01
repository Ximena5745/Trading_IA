param(
    [string]$Symbol = "EURUSD",
    [int]$Years = 2,
    [string]$Interval = "1h"
)

Write-Host "Descargando $Symbol $Years años $Interval..."

try {
    & python.exe scripts/download_forex.py --symbols $Symbol --years $Years --interval $Interval
    Write-Host "Descarga completada exitosamente."
} catch {
    Write-Host "Error durante la descarga: $_"
}