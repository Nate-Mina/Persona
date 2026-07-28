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
<<<<<<< Updated upstream
if exist "%DEST%\venv\Scripts\pip.exe" (
  echo [sabrina-setup] venv present
  exit /b 0
)
echo [sabrina-setup] creating venv...
"%DEST%\python\python.exe" -m venv "%DEST%\venv"
echo [sabrina-setup] installing torch (CPU)...
"%DEST%\venv\Scripts\pip.exe" install torch==2.4.1+cpu torchaudio==2.4.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu
echo [sabrina-setup] installing requirements...
"%DEST%\venv\Scripts\pip.exe" install -r "%DEST%\requirements.txt"
echo [sabrina-setup] pinning gruut (no numpy<2)...
"%DEST%\venv\Scripts\pip.exe" install gruut==2.2.3 --no-deps
=======
if exist "%DEST%\python\deps_installed.marker" (
  if exist "%DEST%\python\python.exe" (
    if exist "%DEST%\python\Lib\site-packages\TTS" (
      echo [sabrina-setup] deps present
      exit /b 0
    )
  )
)
echo [sabrina-setup] installing torch (CPU)...
"%DEST%\python\Scripts\pip.exe" install torch==2.4.1+cpu torchaudio==2.4.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu
echo [sabrina-setup] installing TTS 0.22.0 (lets it pull its own pinned deps)...
"%DEST%\python\Scripts\pip.exe" install TTS==0.22.0
echo [sabrina-setup] forcing numpy-2-compatible stack on top (resolves TTS pandas<2 conflict)...
"%DEST%\python\Scripts\pip.exe" install "numpy==2.0.2" "scipy==1.14.1" "numba==0.60.0" "llvmlite==0.43.0" "scikit-learn==1.6.1" "spacy==3.8.4" "blis==1.0.1" "pandas==2.2.3" "matplotlib==3.9.2" "transformers==4.41.0" "tokenizers==0.19.1" "huggingface-hub==0.23.4"
echo [sabrina-setup] installing remaining deps (stt, server, search)...
"%DEST%\python\Scripts\pip.exe" install faster-whisper==1.2.1 "fastapi>=0.110" "uvicorn[standard]>=0.29" python-multipart>=0.0.9 requests>=2.31 ddgs>=9.0 python-dotenv>=1.2 soundfile==0.14.0 msgpack==1.2.1 resampy==0.4.3 joblib==1.5.3 pooch==1.9.0 pillow==12.3.0 pyparsing==3.3.2 babel==2.18.0 num2words==0.5.14 inflect==7.5.0 anyascii==0.3.3 regex==2026.7.19 sympy
echo [sabrina-setup] pinning gruut (must NOT pull numpy<2)...
"%DEST%\python\Scripts\pip.exe" install gruut==2.2.3 --no-deps
echo done > "%DEST%\python\deps_installed.marker"
>>>>>>> Stashed changes
exit /b 0

REM -------------------------------------------------------------------
:need_xtts
if exist "%DEST%\data\xtts_v2\model.pth" (
  echo [sabrina-setup] XTTS model present
  exit /b 0
)
echo [sabrina-setup] downloading XTTS v2 model (~2 GB, slow)...
"%DEST%\venv\Scripts\python.exe" -c "from huggingface_hub import snapshot_download; snapshot_download('coqui/XTTS-v2', local_dir=r'%DEST%\data\xtts_v2')"
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
