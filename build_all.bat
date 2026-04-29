@echo off
echo ==========================================
echo ClearFiles - Multi-Build Script
echo ==========================================

echo [1/4] Instalando dependencias...
pip install -r requirements.txt --silent

echo [2/4] Limpando pastas de build anteriores...
powershell -Command "Stop-Process -Name ClearFiles* -Force -ErrorAction SilentlyContinue"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/4] Gerando executavel ClearFiles.exe (MODO ADMINISTRADOR)...
pyinstaller --noconsole --onefile --clean --collect-all customtkinter --icon=icon.ico --add-data "logo.png;." --add-data "icon.ico;." --uac-admin --name ClearFiles main.py

echo [4/4] Gerando executavel ClearFiles_User.exe (MODO USUARIO)...
pyinstaller --noconsole --onefile --clean --collect-all customtkinter --icon=icon.ico --add-data "logo.png;." --add-data "icon.ico;." --name ClearFiles_User main.py

echo ==========================================
echo Concluido! 
echo - ClearFiles.exe (Pede Admin ao abrir)
echo - ClearFiles_User.exe (Abre direto)
echo Ambos estao na pasta 'dist'.
echo ==========================================
pause
