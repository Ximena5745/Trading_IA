@echo off
echo Iniciando descarga de Forex...
python.exe scripts/download_forex.py --symbols EURUSD --years 2 --interval 1h
echo Descarga completada.
pause