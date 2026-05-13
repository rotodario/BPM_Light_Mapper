BeatScope brand assets

Files:
- beatscope_icon_1024_transparent.png : PNG real con canal alfa
- beatscope_icon_512_transparent.png  : PNG real con canal alfa
- beatscope_icon_256_transparent.png  : PNG real con canal alfa
- beatscope.ico                       : icono Windows para exe/ventana/instalador
- beatscope_logo_light_ui_transparent.png : logo para fondo claro
- beatscope_logo_dark_ui_transparent.png  : logo para fondo oscuro

Uso rápido:
Tkinter:
    root.iconbitmap("beatscope.ico")

PyInstaller:
    pyinstaller --onefile --windowed --icon=beatscope.ico app.py

Inno Setup:
    [Setup]
    SetupIconFile=beatscope.ico
