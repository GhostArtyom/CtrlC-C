@echo off

@REM ===== Configuration Variables =====
set PY_FILE=ctrlcc.py
set EXE_FILE=ctrlcc.exe
set ICON_FILE=ctrlcc.ico

@REM ===== Check Python =====
where python >nul 2>&1
if %errorlevel% neq 0 (
  echo [ERROR] Python not found! Please install Python and add it to PATH.
  pause
  exit /b 1
)

@REM ===== Check PyInstaller =====
(pyinstaller -v || python -m pip show pyinstaller) >nul 2>&1
if %errorlevel% neq 0 (
  echo [ERROR] PyInstaller not found!
  echo [INFO] Check and activate virtual environment.
)

@REM ===== Check and Activate Virtual Environment =====
if exist "venv\Scripts\activate.bat" (
  call "venv\Scripts\activate.bat"
  ) else if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
  ) else (
  echo [ERROR] Virtual environment not found!
  pause
  exit /b 1
)

@REM ===== Check PyInstaller =====
(pyinstaller -v || python -m pip show pyinstaller) >nul 2>&1
if %errorlevel% neq 0 (
  echo [ERROR] PyInstaller not found!
  pause
  exit /b 1
)

@REM ===== Build Process =====
echo [INFO] Building %PY_FILE% to %EXE_FILE% . . .
pyinstaller -F -w --clean "%PY_FILE%" --add-data "%ICON_FILE%;." -i "%ICON_FILE%" --name "%EXE_FILE%"

if %errorlevel% equ 0 (
  @REM Move .exe file to current directory
  if exist "dist\%EXE_FILE%" (
    move /Y "dist\%EXE_FILE%" ".\"
    echo [INFO] Build successful! The .exe file is at %cd%\%EXE_FILE%
    ) else (
    echo [ERROR] Build failed! The .exe file was not found in dist\
  )
  @REM Clean up temporary files (build and dist directories)
  rd /s /q build dist 2>nul
  ) else (
  echo [ERROR] Clean build\ or dist\ failed!
)

pause
