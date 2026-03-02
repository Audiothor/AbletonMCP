@echo off
title MonServeurClaude

echo 1. Fermeture de l'application Claude...
taskkill /F /IM Claude.exe /T 2>nul
taskkill /F /IM cowork-svc.exe /T 2>nul

echo 2. Fermeture du serveur Python (server.py)...
:: On tue tous les processus python qui ont ete lances par un script
:: Si vous avez d'autres scripts Python vitaux, dites-le moi, on affinera.
taskkill /F /FI "IMAGENAME eq python.exe" /T 2>nul

echo 3. Lancement du nouveau serveur...
:: On lance le serveur dans une NOUVELLE fenetre avec un titre precis pour l'identifier plus tard
start "SERVEUR_CLAUDE" ".\venv\Scripts\python.exe" server.py

echo 4. Pause de 3 secondes...
timeout /t 3 /nobreak >nul

echo 5. Lancement de Claude...
start claude:

echo Operation terminee !
exit