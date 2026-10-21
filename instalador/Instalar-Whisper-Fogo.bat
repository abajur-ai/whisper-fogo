@echo off
REM Instalador de um clique do Whisper Fogo para Windows.
REM Baixe este arquivo e dê dois cliques. Ele busca o instalador completo e roda.
REM
REM Este arquivo é UTF-8 sem BOM e a primeira coisa que ele faz é trocar a
REM codepage do console para 65001. Sem isso o console lê os bytes como CP850 e
REM a acentuação aparece quebrada na tela de quem está instalando.
chcp 65001 > nul

title Instalar o Whisper Fogo

REM Se o arquivo está dentro do repositório clonado, usa o script local.
REM Quando vem de fora, o script é gravado em disco e executado de lá.
set "INSTALADOR=%~dp0instalar.ps1"
if not exist "%INSTALADOR%" (
    echo Baixando o instalador...
    REM O curl vem no Windows 10 a partir da versão 1803. Antes disso, o
    REM PowerShell baixa, com TLS 1.2 ligado à mão.
    where curl.exe >nul 2>nul
    if errorlevel 1 (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/abajur-ai/whisper-fogo/main/instalador/instalar.ps1' -OutFile '%TEMP%\whisper-fogo-instalar.ps1'"
    ) else (
        curl.exe -fsSL -o "%TEMP%\whisper-fogo-instalar.ps1" "https://raw.githubusercontent.com/abajur-ai/whisper-fogo/main/instalador/instalar.ps1"
    )
    if errorlevel 1 (
        echo.
        echo Não consegui baixar o instalador. Confira a sua conexão com a internet.
        pause
        exit /b 1
    )
    set "INSTALADOR=%TEMP%\whisper-fogo-instalar.ps1"
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALADOR%"

if errorlevel 1 (
    echo.
    echo A instalação não terminou. Leia a mensagem acima.
    pause
)
