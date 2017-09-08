SET drive=D
SET apppath=D:\Other\autovpn

%drive%:
cd %apppath%

del logs\autovpn.log
python src\autovpn.py

:: if exist dist\autovpn\autovpn.exe (
:: echo "Build exist, Executing windows build"
:: dist\autovpn\autovpn.exe
:: ) else (
:: echo "Build does not exist. Please install Python and requi::ents.
:: python src\autovpn.py
:: )