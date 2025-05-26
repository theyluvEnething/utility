@echo off
powershell -Command "Start-Process cmd.exe -ArgumentList '/s /k pushd . && cd /d %cd%' -Verb RunAs"
