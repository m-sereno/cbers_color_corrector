@echo off
set QGIS_PATH=D:\Program Files\QGIS 3.16\bin
call "%QGIS_PATH%\o4w_env.bat"
call "%QGIS_PATH%\qt5_env.bat"
call "%QGIS_PATH%\py3_env.bat"

@echo on
pyrcc5 -o resources.py resources.qrc