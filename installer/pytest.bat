@echo off
setlocal
set "D=C:\SabrinaPyTest"
if exist "%D%" rmdir /s /q "%D%"
mkdir "%D%"
echo [test] downloading python-embed.zip
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%D%\py.zip'"
echo [test] zip size:
dir "%D%\py.zip" | find "py.zip"
echo [test] extracting with 7za
"D:\__dev\Persona\installer\7za.exe" x -y "-o%D%\py" "%D%\py.zip"
echo [test] python.exe present?
if exist "%D%\py\python.exe" (echo YES ) else (echo NO )
dir "%D%\py" | find "python"
echo [test] DONE
