@echo off
echo Instalando dependencias...
pip install -r requirements.txt
echo Gerando executavel ClearFiles...
pyinstaller --noconsole --onefile --collect-all customtkinter --icon=icon.ico --add-data "logo.png;." --add-data "icon.ico;." --name ClearFiles main.py
echo Concluido! O executavel esta na pasta 'dist'.
pause