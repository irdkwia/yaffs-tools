@echo off
setlocal enabledelayedexpansion
 
set "target_folder=%~dp0\config"
 
echo Input File: "%~1"
echo;
 
echo Config List:
set /a count=0
for %%F in ("%target_folder%\*.*") do (
    set /a count+=1
    set "file[!count!]=%%~nxF"
    echo !count!: %%~nxF
)
 
set /p "choice=Select number: "
 
if not defined file[%choice%] (
    echo Invalid number.
    exit /b
)
echo;
 
echo Extraction started with "!file[%choice%]!".
 
python "%~dp0\extract.py" -m -u -s "%~1" "%~1_out" "%~dp0\config\!file[%choice%]!"
 
pause
