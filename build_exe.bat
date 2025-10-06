@echo off
setlocal

REM Ensure we're in the project root (where main.py is)
cd /d "%~dp0"

REM Use existing venv if present; otherwise try system Python
set PYTHON=venv\Scripts\python.exe
if not exist %PYTHON% set PYTHON=python

REM Install PyInstaller if missing
%PYTHON% -c "import PyInstaller" 1>nul 2>nul
if errorlevel 1 (
  echo Installing PyInstaller...
  %PYTHON% -m pip install --upgrade pip
  %PYTHON% -m pip install pyinstaller
)

REM Clean previous build
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist DeepSearch.spec del /q DeepSearch.spec

REM Build portable single-file executable
%PYTHON% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --name DeepSearch ^
  --windowed ^
  --onefile ^
  --hidden-import darkdetect ^
  --hidden-import PIL._tkinter_finder ^
  --collect-all customtkinter ^
  --collect-all PIL ^
  --collect-all transformers ^
  --collect-all huggingface_hub ^
  --collect-all tokenizers ^
  --collect-all safetensors ^
  --collect-all torch ^
  main.py

REM Optionally include prebuilt cache/database if present
REM For onefile builds, bundling extra files isn't applicable; they won't persist inside the exe
REM If you need a default database on first run, we can add runtime extraction logic instead

echo.
echo Build complete. Launch: dist\DeepSearch.exe
endlocal
