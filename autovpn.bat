SET drive=D
SET apppath=D:\Other\autovpn

%drive%:
cd %apppath%

IF EXIST "logs\autovpn.log" (
del logs\autovpn.log
)
C:\Python27\python.exe python\autovpn.py

:: if exist dist\autovpn\autovpn.exe (
:: echo "Build exist, Executing windows build"
:: dist\autovpn\autovpn.exe
:: ) else (
:: echo "Build does not exist. Please install Python and requi::ents.
:: python src\autovpn.py
:: )