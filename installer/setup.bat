@echo off
REM ===================================================================
REM  Sabrina - The Guarded Survivor : installer bootstrap
REM  Runs after the SFX extracts the bundle to a temp dir. It:
REM    1) copies the app to %LOCALAPPDATA%\Sabrina
REM    2) downloads + installs an embedded Python (no pre-installed Python needed)
REM    3) installs dependencies into the embedded Python (no venv needed)
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
set "P7EXE=%SRC%7za.exe"

if not exist "%DEST%" mkdir "%DEST%"
call :copy_files

REM ---- lightweight self-test path (set TEST=1 to skip the 2GB downloads) ----
if defined TEST (
  echo [sabrina-setup] TEST MODE: skipping model/Ollama downloads.
  call :need_python
  call :need_venv
  call :make_shortcuts
  echo {"ok":true,"test":true} > "%DEST%\install_state.json"
  echo [sabrina-setup] TEST MODE complete. Installed python+deps to %DEST%
  goto :eof
)

echo [sabrina-setup] Installing Sabrina to %DEST%
call :need_python
call :need_venv
call :need_xtts
call :need_ollama
call :make_shortcuts

echo {"ok":true} > "%DEST%\install_state.json"
echo [sabrina-setup] Launching Sabrina...
start "" "%DEST%\installer\launcher.vbs"
goto :eof


REM ===================== subroutines =====================

:copy_files
echo [sabrina-setup] Copying files...
if not exist "%DEST%" mkdir "%DEST%"
robocopy "%SRC%app"        "%DEST%\app"        /E /NFL /NDL /NJH /NJS >nul
copy /Y "%SRC%run.py"          "%DEST%\run.py"          >nul
copy /Y "%SRC%requirements.txt" "%DEST%\requirements.txt" >nul
copy /Y "%SRC%README.md"       "%DEST%\README.md"       >nul
copy /Y "%SRC%.env.example"    "%DEST%\.env.example"    >nul
if not exist "%DEST%\installer" mkdir "%DEST%\installer"
copy /Y "%SRC%launcher.py"     "%DEST%\installer\launcher.py"     >nul
copy /Y "%SRC%launcher.vbs"    "%DEST%\installer\launcher.vbs"    >nul
exit /b 0


:need_python
if exist "%DEST%\python\python.exe" (
  echo [sabrina-setup] embedded Python present
  exit /b 0
)
if exist "%DEST%\python" rmdir /s /q "%DEST%\python"
echo [sabrina-setup] downloading embedded Python...
curl.exe -L -s -o "%DEST%\python-embed.zip" "%PYURL%"
if not exist "%DEST%\python-embed.zip" (
  echo [sabrina-setup] download failed, retrying via powershell...
  powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PYURL%' -OutFile '%DEST%\python-embed.zip'"
)
echo [sabrina-setup] extracting Python with 7z...
"%P7EXE%" x -y "-o%DEST%\python" "%DEST%\python-embed.zip"
if not exist "%DEST%\python\python.exe" (
  echo [sabrina-setup] extraction failed, retrying...
  del /f /q "%DEST%\python-embed.zip"
  curl.exe -L -s -o "%DEST%\python-embed.zip" "%PYURL%"
  "%P7EXE%" x -y "-o%DEST%\python" "%DEST%\python-embed.zip"
)
echo [sabrina-setup] enabling import site...
powershell -NoProfile -Command "$p='%DEST%\python\python311._pth'; $t=Get-Content $p; if(-not($t -contains 'import site')){ Add-Content $p 'import site' }"
echo [sabrina-setup] installing pip...
curl.exe -L -s -o "%DEST%\python\get-pip.py" "%GETPIP%"
if not exist "%DEST%\python\get-pip.py" powershell -NoProfile -Command "Invoke-WebRequest -Uri '%GETPIP%' -OutFile '%DEST%\python\get-pip.py'"
"%DEST%\python\python.exe" "%DEST%\python\get-pip.py"
exit /b 0


:need_venv
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
echo [sabrina-setup] installing TTS 0.22.0, let it pull its own pinned deps...
"%DEST%\python\Scripts\pip.exe" install TTS==0.22.0
echo [sabrina-setup] forcing numpy-2 stack (except blis) so thinc/spacy pull numpy-2 wheels...
"%DEST%\python\Scripts\pip.exe" install "numpy==2.0.2" "scipy==1.14.1" "numba==0.60.0" "llvmlite==0.43.0" "scikit-learn==1.6.1" "pandas==2.2.3" "matplotlib==3.9.2" "transformers==4.41.0" "tokenizers==0.19.1" "huggingface-hub==0.23.4"
echo [sabrina-setup] installing spacy 3.8.4, thinc resolves against numpy 2...
"%DEST%\python\Scripts\pip.exe" install spacy==3.8.4
echo [sabrina-setup] swapping blis to 1.0.1 numpy-2 build, no-deps, matches dev venv...
"%DEST%\python\Scripts\pip.exe" install blis==1.0.1 --no-deps --force-reinstall
echo [sabrina-setup] installing remaining deps, stt server search...
echo [sabrina-setup] installing remaining deps, stt server search...
"%DEST%\python\Scripts\pip.exe" install faster-whisper==1.2.1 "fastapi>=0.110" "uvicorn[standard]>=0.29" python-multipart>=0.0.9 requests>=2.31 ddgs>=9.0 python-dotenv>=1.2 soundfile==0.14.0 msgpack==1.2.1 resampy==0.4.3 joblib==1.5.3 pooch==1.9.0 pillow==12.3.0 pyparsing==3.3.2 babel==2.18.0 num2words==0.5.14 inflect==7.5.0 anyascii==0.3.3 regex==2026.7.19 sympy
echo [sabrina-setup] pinning gruut, must not pull numpy-lessthan-2...
"%DEST%\python\Scripts\pip.exe" install gruut==2.2.3 --no-deps
echo done > "%DEST%\python\deps_installed.marker"
exit /b 0


:need_xtts
if exist "%DEST%\data\xtts_v2\model.pth" (
  echo [sabrina-setup] XTTS model present
  exit /b 0
)
echo [sabrina-setup] downloading XTTS v2 model, about 2 GB, this is slow...
"%DEST%\python\python.exe" -c "from huggingface_hub import snapshot_download; snapshot_download('coqui/XTTS-v2', local_dir=r'%DEST%\data\xtts_v2')"
exit /b 0


:need_ollama
if exist "%DEST%\ollama\ollama.exe" (
  echo [sabrina-setup] Ollama present
  exit /b 0
)
echo [sabrina-setup] downloading Ollama...
curl.exe -L -s -o "%DEST%\ollama-windows.zip" "%OLLAMAURL%"
if not exist "%DEST%\ollama-windows.zip" powershell -NoProfile -Command "Invoke-WebRequest -Uri '%OLLAMAURL%' -OutFile '%DEST%\ollama-windows.zip'"
"%P7EXE%" x -y "-o%DEST%\ollama" "%DEST%\ollama-windows.zip"
exit /b 0


:make_shortcuts
set "SCH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Sabrina.lnk"
set "DSH=%USERPROFILE%\OneDrive\Desktop\Sabrina.lnk"
if exist "%USERPROFILE%\Desktop" set "DSH=%USERPROFILE%\Desktop\Sabrina.lnk"
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut('%SCH%'); $s.TargetPath='%DEST%\installer\launcher.vbs'; $s.WorkingDirectory='%DEST%'; $s.Description='Sabrina - The Guarded Survivor'; $s.Save(); $d=$w.CreateShortcut('%DSH%'); $d.TargetPath='%DEST%\installer\launcher.vbs'; $d.WorkingDirectory='%DEST%'; $d.Description='Sabrina - The Guarded Survivor'; $d.Save();"
exit /b 0
