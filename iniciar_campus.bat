@echo off
title Campus Docente EI-FII - Universidad de Guayaquil
echo ============================================================
echo  Iniciando Campus Docente EI-FII (Emprendimiento e Innovacion)
echo  Facultad de Ingenieria Industrial - Universidad de Guayaquil
echo  Docente & Administrador: Econ. Janio Cerezo Piedrahita, Mgs.
echo ============================================================
start "" "http://localhost:8090"
python "%~dp0server.py"
pause
