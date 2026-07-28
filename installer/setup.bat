@echo off
REM ===================================================================
REM  Sabrina — The Guarded Survivor : installer bootstrap
REM  Runs after the SFX extracts the bundle to a temp dir. It:
REM    1) copies the app to %LOCALAPPDATA%\Sabrina
REM    2) downloads + installs an embedded Python (no pre-installed Python needed)
REM    3) creates a venv + installs the exact pinned dependencies
REM    4) downloads the 2 GB XTTS v2 model (skipped if TEST=1)
REM    5) downloads Ollama (the brain) for Windows (skipped if TEST=1)
REM    6) creates Start Menu + Desktop shortcuts
REM    7) launches Sabrina
REM  Safe to re-run (skips what's already done via install_state.json).
REM ===================================================================

setlocal EnableDelayedExpansion
set "DEST=%LOCALAPPDATA%\Sabrina"
set "SRC=%~dp0"
set "PYURL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "GETPIP=https://bootstrap.pypa.io/get-pip.py"
set "OLLAMAURL=https://ollama.com/download/ollama-windows-amd64.zip"

REM ---- lightweight self-test path (set TEST=1 to skip the 2GB downloads) ----
if defined TEST (
  echo [sabrina-setup] TEST MODE: skipping model/Ollama downloads.
  call :need_python
  call :need_venv
  call :make_shortcuts
  echo {"ok":true,"test":true} > "%DEST%\install_state.json"
  echo [sabrina-setup] TEST MODE complete. Installed python+venv to %DEST%
  exit /b 0
)

echo [sabrina-setup] Installing Sabrina to %DEST%
if not exist "%DEST%" mkdir "%DEST%"

echo [sabrina-setup] Copying files...
robocopy "%SRC%app"        "%DEST%\app"        /E /NFL /NDL /NJH /NJS >nul
robocopy "%SRC%installer"  "%DEST%\installer"  /E /NFL /NDL /NJH /NJS >nul
copy /Y "%SRC%run.py"          "%DEST%\run.py"          >nul
copy /Y "%SRC%requirements.txt" "%DEST%\requirements.txt" >nul
copy /Y "%SRC%README.md"       "%DEST%\README.md"       >nul
copy /Y "%SRC%.env.example"    "%DEST%\.env.example"    >nul

call :need_python
call :need_venv
call :need_xtts
call :need_ollama
call :make_shortcuts

echo {"ok":true} > "%DEST%\install_state.json"

echo [sabrina-setup] Launching Sabrina...
start "" "%DEST%\installer\launcher.vbs"
exit /b 0

REM -------------------------------------------------------------------
:need_python
if exist "%DEST%\python\python.exe" (
  echo [sabrina-setup] embedded Python present
  exit /b 0
)
echo [sabrina-setup] downloading embedded Python...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PYURL%' -OutFile '%DEST%\python-embed.zip'"
echo [sabrina-setup] extracting Python...
powershell -NoProfile -Command "Expand-Archive -Force '%DEST%\python-embed.zip' '%DEST%\python'"
echo [sabrina-setup] enabling import site...
powershell -NoProfile -Command "$p='%DEST%\python\python311._pth'; $t=Get-Content $p; if(-not($t -contains 'import site')){ Add-Content $p 'import site' }"
echo [sabrina-setup] installing pip...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%GETPIP%' -OutFile '%DEST%\python\get-pip.py'"
"%DEST%\python\python.exe" "%DEST%\python\get-pip.py"
exit /b 0

REM -------------------------------------------------------------------
:need_venv
if exist "%DEST%\python\deps_installed.marker" (
  echo [sabrina-setup] deps present
  exit /b 0
)
echo [sabrina-setup] installing torch (CPU) into embedded Python...
"%DEST%\python\Scripts\pip.exe" install torch==2.4.1+cpu torchaudio==2.4.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu
echo [sabrina-setup] installing requirements...
"%DEST%\python\Scripts\pip.exe" install -r "%DEST%\requirements.txt"
echo [sabrina-setup] pinning gruut (no numpy<2)...
"%DEST%\python\Scripts\pip.exe" install gruut==2.2.3 --no-deps
echo done > "%DEST%\python\deps_installed.marker"
exit /b 0

REM -------------------------------------------------------------------
:need_xtts
if exist "%DEST%\data\xtts_v2\model.pth" (
  echo [sabrina-setup] XTTS model present
  exit /b 0
)
echo [sabrina-setup] downloading XTTS v2 model (~2 GB, slow)...
"%DEST%\python\python.exe" -c "from huggingface_hub import snapshot_download; snapshot_download('coqui/XTTS-v2', local_dir=r'%DEST%\data\xtts_v2')"
exit /b 0

REM -------------------------------------------------------------------
:need_ollama
if exist "%DEST%\ollama\ollama.exe" (
  echo [sabrina-setup] Ollama present
  exit /b 0
)
echo [sabrina-setup] downloading Ollama...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%OLLAMAURL%' -OutFile '%DEST%\ollama-windows.zip'"
powershell -NoProfile -Command "Expand-Archive -Force '%DEST%\ollama-windows.zip' '%DEST%\ollama'"
exit /b 0

REM -------------------------------------------------------------------
:make_shortcuts
set "SCH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Sabrina.lnk"
set "DSH=%USERPROFILE%\Desktop\Sabrina.lnk"
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut('%SCH%'); $s.TargetPath='%DEST%\installer\launcher.vbs'; $s.WorkingDirectory='%DEST%'; $s.Description='Sabrina - The Guarded Survivor'; $s.Save(); $d=$w.CreateShortcut('%DSH%'); $d.TargetPath='%DEST%\installer\launcher.vbs'; $d.WorkingDirectory='%DEST%'; $d.Description='Sabrina - The Guarded Survivor'; $d.Save();"
exit /b 0
