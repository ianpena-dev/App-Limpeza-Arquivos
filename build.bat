@echo off
echo Instalando dependencias...
pip install -r requirements.txt
echo Limpando pastas de build anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo Gerando executavel ClearFiles...
pyinstaller --noconsole --onefile --clean --collect-all customtkinter --icon=icon.ico --add-data "logo.png;." --add-data "icon.ico;." --name ClearFiles main.py
echo Concluido! O executavel esta na pasta 'dist'.
pause
