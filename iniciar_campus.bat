@echo off
title Plataforma EI-FII - Universidad de Guayaquil
echo ============================================================
echo  Iniciando Plataforma EI-FII (Emprendimiento e Innovacion)
echo  Facultad de Ingenieria Industrial - Universidad de Guayaquil
echo  Docente & Administrador: Econ. Janio Cerezo Piedrahita, Mgs.
echo ============================================================
start "" "http://localhost:8090"
python "%~dp0server.py"
pause
